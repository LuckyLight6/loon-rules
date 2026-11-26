"""Compare complete public community files, retaining unresolved inputs and their lineage."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from ipaddress import ip_network
import json
from pathlib import Path
import re
import subprocess
import time
from tempfile import NamedTemporaryFile, TemporaryDirectory
from urllib.parse import quote, urlencode

from loon_rules import community, rules
from loon_rules.domains import covers as rules_scope_covers
from loon_rules.generation import pipeline
from loon_rules.matching import RuleIndex


def api(path):
    result = subprocess.run(['gh', 'api', path], capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise rules.Invalid('GitHub 公开元数据读取失败')
    return json.loads(result.stdout)


def resolve(repository, ref):
    doc = api('repos/' + repository + '/commits/' + quote(ref, safe=''))
    revision = doc.get('sha', '')
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise rules.Invalid('来源没有完整提交身份')
    return {'revision': revision, 'committed-at': doc['commit']['committer']['date']}


def download(url):
    result = subprocess.run(['curl', '-q', '-fsSL', '--proto', '=https', '--proto-redir', '=https',
        '--max-redirs', '2', '--connect-timeout', '8', '--max-time', '30', '--retry', '1',
        '--max-filesize', '18000000', url], capture_output=True, timeout=75)
    if result.returncode:
        raise rules.Invalid('完整社区规则文件下载失败')
    return result.stdout


def validate(spec, entries):
    if spec.get('schema-version') != 1 or not isinstance(spec.get('inputs'), list) or not spec['inputs']:
        raise rules.Invalid('社区来源登记表为空或版本无效')
    seen = set()
    for item in spec['inputs']:
        if (not re.fullmatch(r'[a-z0-9-]+', item.get('id', '')) or item['id'] in seen
                or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', item.get('repository', ''))
                or not isinstance(item.get('ref'), str) or not item['ref']
                or not isinstance(item.get('path'), str) or not item['path']
                or item['path'].startswith('/') or '..' in Path(item['path']).parts
                or not isinstance(item.get('products'), list) or not set(item['products']) <= entries.keys()
                or item.get('format') not in community.FORMATS | {'sing-box-binary', 'unverified'}):
            raise rules.Invalid('社区来源缺少公开身份、格式或有效产品线索')
        if 'upstream-inputs' in item:
            proof=item.get('lineage-proof')
            if (not isinstance(proof,dict) or not isinstance(proof.get('path'),str) or not proof['path']
                    or proof['path'].startswith('/') or '..' in Path(proof['path']).parts
                    or not re.fullmatch('[0-9a-f]{64}',proof.get('sha256',''))):
                raise rules.Invalid('来源继承声明缺少已核对的构建定义指纹')
        if 'upstream-revisions' in item or 'lineage-output-revision' in item:
            consumed=item.get('upstream-revisions')
            if (not isinstance(consumed,dict) or set(consumed)!=set(item.get('upstream-inputs',()))
                    or not re.fullmatch('[0-9a-f]{40}',item.get('lineage-output-revision',''))
                    or any(not isinstance(value,str) or not re.fullmatch('[0-9a-f]{40}',value) for value in consumed.values())):
                raise rules.Invalid('来源贡献缺少对应下游成品与实际消耗的上游提交')
        seen.add(item['id'])
    for item in spec['inputs']:
        if set(item.get('upstream-inputs', ())) - seen or item['id'] in item.get('upstream-inputs', ()):
            raise rules.Invalid('来源继承关系引用缺失或自身')
    ordered = []
    remaining = {item['id']: item for item in spec['inputs']}
    while remaining:
        ready = [item for item in remaining.values() if not set(item.get('upstream-inputs', ())) & remaining.keys()]
        if not ready:
            raise rules.Invalid('来源继承关系存在循环')
        ordered.extend(ready)
        for item in ready:
            del remaining[item['id']]
    return ordered


def source_url(item, revision):
    return 'https://raw.githubusercontent.com/' + item['repository'] + '/' + revision + '/' + quote(item['path'])


def read_body(item, body, folder, sing_box):
    form = item['format']
    if form == 'sing-box-binary':
        if sing_box is None:
            raise rules.Invalid('二进制 SRS 需要已验证的本机 sing-box 核心')
        with TemporaryDirectory(prefix='community-srs-', dir=folder) as temporary:
            source = Path(temporary) / 'input.srs'
            target = Path(temporary) / 'output.json'
            source.write_bytes(body)
            result = subprocess.run([str(sing_box), 'rule-set', 'decompile', '--output', str(target), str(source)],
                                    capture_output=True, timeout=25)
            if result.returncode or not target.is_file():
                raise rules.Invalid('官方核心无法完整解码 SRS，保留此前记录')
            body = target.read_bytes()
            form = 'sing-box'
    return community.normalize(form, body.decode('utf-8-sig'))


def compare(rows, products, entries, data, index):
    outcomes = Counter()
    findings = []
    targets=set()
    pending=list(products)
    while pending:
        key=pending.pop()
        if key in targets:continue
        targets.add(key)
        if entries[key].get('mode')=='view':pending.extend(entries[key]['members'])
    for row in rows:
        kind, value, *flags = row.split(',')
        matching = intersections = 0
        if kind in ('DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-WILDCARD'):
            matching = index.scope_bits(row)
            intersections = index.scope_intersection_bits(row)
        elif kind in ('IP-CIDR', 'IP-CIDR6'):
            literal = index.network_bits(value,literal=True)
            resolved = index.network_bits(value,literal=False)
            matching = literal
            intersections = index.network_intersection_bits(value,literal=True)
            if literal != resolved:
                outcomes['address-resolution-mode-needs-context'] += 1
        elif kind in ('IP-ASN', 'PROCESS-NAME', 'PROCESS-PATH', 'USER-AGENT', 'GEOIP'):
            for key in index.order:
                if any(candidate.split(',')[:2] == [kind, value] for candidate in data[key]):
                    matching |= index.bits[key]
            outcomes['runtime-or-device-dependent'] += 1
            intersections=matching
        else:
            outcomes['condition-needs-purpose-review'] += 1
            findings.append({'rule': row, 'state': 'condition-needs-purpose-review'})
            continue
        owner = next((key for key in index.order if matching & index.bits[key]), None)
        earlier=[]
        for key in index.order:
            if key==owner:break
            if intersections&index.bits[key]:earlier.append(key)
        dependency_views=[key for key in targets if entries[key].get('mode')=='view'
            and any(rules_scope_covers(scope,row) for scope in entries[key].get('_dependency-scopes',()))]
        state = ('mixed-or-unverified-first-ownership' if earlier else
            'unassigned-whole-scope' if owner is None else
            'privacy-owner' if entries[owner].get('policy-hint') == 'reject' else
            'supplement-owner' if entries[owner].get('fallback') or entries[owner].get('domain-remainder') else
            'candidate-product-owner' if owner in targets else
            'documented-shared-dependency-owner' if dependency_views else 'other-product-or-shared-owner')
        outcomes[state] += 1
        if state != 'candidate-product-owner':
            finding={'rule': row, 'state': state, 'actual-first-owner':None if earlier else owner}
            if earlier:
                finding.update({'whole-scope-covering-owner':owner,'earlier-intersections':earlier,
                    'complex-intersections-need-review':True})
            if dependency_views:finding['documented-dependency-views']=sorted(dependency_views)
            findings.append(finding)
    return {'outcomes': dict(outcomes), 'findings': findings}


def search_candidates(queries):
    results = []
    next_query_at = 0.0
    for query in queries:
        # Authenticated GitHub repository search allows 30 requests per minute.
        delay = next_query_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        next_query_at = time.monotonic() + 2.1
        try:
            doc = api('search/repositories?' + urlencode({'q': query, 'sort': 'updated', 'per_page': 30}))
            if doc.get('incomplete_results'):
                raise rules.Invalid('GitHub 搜索声明结果不完整')
            results.append({'query': query, 'total': doc['total_count'],
                'repositories': [item['full_name'] for item in doc['items']], 'state': 'current'})
        except (rules.Invalid, OSError, ValueError, KeyError, subprocess.TimeoutExpired):
            results.append({'query': query, 'state': 'unavailable'})
    return results


def run(root, *, sing_box=None, search=True):
    root = Path(root)
    spec = json.loads((root / 'config/community-sources.json').read_text())
    config = json.loads((root / 'config/catalog.json').read_text())
    entries = pipeline.validate_declarations(config)
    inputs = validate(spec, entries)
    data = {item['id']: rules.read_rules((root / 'rules/loon' / pipeline.rule_filename(entries[item['id']])).read_text())
            for item in config['entries']}
    if any(entry.get('dependency-inputs') for entry in entries.values()):
        from loon_rules.generation import dependencies
        maintenance=json.loads((root/'data/maintenance-state.json').read_text())
        dependencies.attach(config,entries,data,maintenance.get('service-dependencies',{}))
    order = pipeline.route_order(config, entries)
    index = RuleIndex(data, order)
    index.network_bits('0.0.0.0/0',literal=True)
    folder = root / 'build/community-review'
    folder.mkdir(parents=True, exist_ok=True)
    cache = folder / 'source-cache'
    cache.mkdir(exist_ok=True)
    def body_at(url):
        path = cache / hashlib.sha256(url.encode()).hexdigest()
        if path.is_file():
            return path.read_bytes()
        body = download(url)
        with NamedTemporaryFile(dir=cache,prefix=path.name+'.',delete=False) as output:
            output.write(body)
            temporary=Path(output.name)
        temporary.replace(path)
        return body
    state_path = root / 'data/community-state.json'
    prior_state=json.loads(state_path.read_text()) if state_path.exists() else {}
    previous=prior_state.get('inputs',{})
    resolved = {}
    identities = sorted({(item['repository'], item['ref']) for item in inputs})
    def get_revision(identity):
        try:
            return identity, resolve(*identity)
        except (rules.Invalid, OSError, ValueError, KeyError, subprocess.TimeoutExpired):
            return identity, None
    with ThreadPoolExecutor(max_workers=4) as pool:
        resolved.update(pool.map(get_revision, identities))
    def fetch(item):
        record = {'id': item['id'], 'repository': item['repository'], 'ref': item['ref'], 'path': item['path'],
                  'format': item['format'], 'products': item['products']}
        try:
            identity = resolved[item['repository'], item['ref']]
            if identity is None:
                raise rules.Invalid('发布分支提交身份尚未完整读取')
            record.update(identity)
            url = source_url(item, identity['revision'])
            body = body_at(url)
            digest = hashlib.sha256(body).hexdigest()
            normalized = read_body(item, body, folder, sing_box)
            # Keep raw public source snapshots local. Public state contains hashes and counts only.
            (folder / (digest + '.source')).write_bytes(body)
            if 'upstream-inputs' in item:
                proof=item['lineage-proof']
                proof_url=source_url({**item,'path':proof['path']},identity['revision'])
                definition=body_at(proof_url)
                if hashlib.sha256(definition).hexdigest()!=proof['sha256']:
                    raise rules.Invalid('下游构建定义已变化，保留旧继承记录，重新核对实际输入')
                record['lineage-proof']={**proof,'source':proof_url}
            old = previous.get(item['id'])
            changes = {'state': 'initial-complete-input'}
            if old and old.get('sha256') != digest:
                old_body = body_at(source_url(item, old['revision']))
                if hashlib.sha256(old_body).hexdigest() != old['sha256']:
                    raise rules.Invalid('上一完整来源的提交或正文指纹不一致')
                baseline = read_body(item, old_body, folder, sing_box)
                changes = {'state': 'changed', 'added': sorted(set(normalized['rules']) - set(baseline['rules'])),
                    'removed': sorted(set(baseline['rules']) - set(normalized['rules'])),
                    'conditions-changed': normalized['conditions'] != baseline['conditions'],
                    'policies-changed': normalized['policies'] != baseline['policies']}
            elif old:
                changes = {'state': 'unchanged'}
            record.update(state='normalized-for-review', url=url, sha256=digest, bytes=len(body),
                normalized=normalized, changes=changes,
                **compare(normalized['rules'], item['products'], entries, data, index))
        except (rules.Invalid, OSError, ValueError, KeyError, UnicodeError, subprocess.TimeoutExpired) as error:
            record.update(state='held', reason=str(error), previous_complete_retained=item['id'] in previous)
        return record
    records = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for number,record in enumerate(pool.map(fetch, inputs),1):
            records.append(record)
            if number%200==0:
                print('Complete community inputs:',number,'/',len(inputs),flush=True)
    by_id = {record['id']: record for record in records}
    accepted = dict(previous)
    for item in inputs:
        record = by_id[item['id']]
        if record['state'] == 'held':
            continue
        parents = item.get('upstream-inputs')
        if parents and any(by_id[key]['state'] == 'held' for key in parents):
            record.update(state='held', reason='声明的上游未完整读取，无法确认下游贡献',
                          previous_complete_retained=item['id'] in previous)
            continue
        upstreams=None if parents is None else {}
        consumed=item.get('upstream-revisions',{})
        pinned=record['revision']==item.get('lineage-output-revision') and set(consumed)==set(parents or ())
        if parents and not pinned:
            upstreams=None
            record['lineage-reason']='实际消耗的上游提交未确认；当前上游差异不能归功于下游'
        elif parents:
            try:
                for key in parents:
                    parent=next(candidate for candidate in inputs if candidate['id']==key)
                    version=consumed[key]
                    body=body_at(source_url(parent,version))
                    upstreams[key]={**read_body(parent,body,folder,sing_box),'products':parent['products']}
                record['consumed-upstreams']=dict(consumed)
            except (rules.Invalid,OSError,ValueError,KeyError,UnicodeError,subprocess.TimeoutExpired):
                record.update(state='held',reason='已声明的实际上游提交未完整读取，保留旧贡献记录',
                              previous_complete_retained=item['id'] in previous)
                continue
        record['lineage'] = community.contributions(item['id'],
            {**record['normalized'], 'products': item['products']}, upstreams)
        accepted[item['id']] = {key: record[key] for key in ('repository', 'ref', 'path', 'format', 'revision',
                                                           'committed-at', 'sha256', 'bytes')}
        if 'lineage-proof' in record:accepted[item['id']]['lineage-proof']=record['lineage-proof']
        accepted[item['id']]['lineage-status']=record['lineage']['independence']
        if 'consumed-upstreams' in record:accepted[item['id']]['consumed-upstreams']=record['consumed-upstreams']
        accepted[item['id']].update(rules=len(record['normalized']['rules']),
            conditional_rules=len(record['normalized']['conditions']), products=item['products'])
    from loon_rules.community_web import watch
    websites,web_state=watch(spec.get('source-websites',()),prior_state.get('websites',{}),folder)
    for website in websites:
        for artifact in website.get('artifacts',()):
            if artifact.get('state')=='normalized-for-review':
                artifact.update(compare(artifact['normalized']['rules'],artifact['products'],entries,data,index))
    queries = search_candidates(spec.get('queries', ())) if search else []
    summary = {'inputs-expected': len(inputs), 'inputs-observed': len(records),
        'inputs-normalized': sum(record['state'] == 'normalized-for-review' for record in records),
        'inputs-held': sum(record['state'] == 'held' for record in records),
        'inputs-with-changes': sum(record.get('changes', {}).get('state') == 'changed' for record in records),
        'repository-branches': len(identities), 'products-with-file-candidates': len({key for item in inputs for key in item['products']}),
        'searches-held': sum(query['state'] != 'current' for query in queries),
        'hosted-sources-checked':len(websites),'hosted-sources-held':sum(website['state']=='held' for website in websites)}
    now = datetime.now(timezone.utc).isoformat()
    report = {'checked-at': now, **summary, 'inputs': records, 'searches': queries, 'websites':websites,
              'source-labels-are-not-ownership-proof': True, 'native-runtime-and-device-acceptance': 'not-performed'}
    # No files under rules/ are modified by comparison. Only the existing purpose-verified generator publishes rules.
    output = {'schema-version': 1, 'checked-at': now, 'summary': summary, 'inputs': accepted, 'websites':web_state}
    for path, value in [(folder / 'report.json', report), (state_path, output)]:
        temporary = path.with_suffix('.new')
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(path)
    lines = ['# 社区完整来源对照', '',
        f"完整登记 {summary['inputs-expected']} 份输入，本轮读取并规范化 {summary['inputs-normalized']} 份，"
        f"保留待核状态 {summary['inputs-held']} 份；{summary['inputs-with-changes']} 份正文发生变化。", '',
        '逐项核对完整输入、规则类型、原始条件、归属和首条命中。来源标签、数量和格式检查不能代替业务用途核实；'
        '这些比较不会把社区差异直接写入订阅。声明的继承、下游增删、收窄及分类修改分别记录，未知继承不计作独立证据。', '',
        f"对照涉及 {summary['repository-branches']} 个仓库分支、{summary['products-with-file-candidates']} 个产品的文件线索。"
        '本机细项保存在 build/community-review；定时运行的逐条公开来源报告由 Actions 工件留存90天，原始下载正文不上传，也不进入公开提交。', '',
        f"托管来源核对 {len(websites)} 处，整批保留待核 {summary['hosted-sources-held']} 处；构建元数据与每份文件的版本必须一致。", '']
    (folder / 'summary.md').write_text('\n'.join(lines))
    return summary
