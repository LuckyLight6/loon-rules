"""Read product-labelled assets, not arbitrary links in security-program prose."""
import json
import re
from ipaddress import ip_network
from urllib.parse import urlsplit

from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid
from loon_rules.sources.formats.common import public_domain_pattern


FORMAT = 'security-program-domains'
NON_NETWORK_TYPES = {'SOURCE_CODE', 'DOWNLOADABLE_EXECUTABLES', 'APPLE_STORE_APP_ID', 'GOOGLE_PLAY_APP_ID'}


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Invalid('安全资产资料含重复 JSON 字段')
        result[key] = value
    return result


def program(recipe, text):
    identity = recipe.get('program')
    if (not isinstance(identity, dict) or set(identity) != {'handle', 'name', 'url'}
            or any(not isinstance(value, str) or not value.strip() for value in identity.values())
            or not re.fullmatch(r'[a-z0-9_-]+', identity['handle'])
            or identity['url'] != 'https://hackerone.com/' + identity['handle']):
        raise Invalid('安全资产资料需要明确的项目身份')
    try:
        document = json.loads(text, object_pairs_hook=unique_fields)
    except ValueError as exc:
        raise Invalid('安全资产目录不是完整 JSON') from exc
    if not isinstance(document, list) or not document:
        raise Invalid('安全资产目录缺少项目列表')
    candidates = [record for record in document if isinstance(record, dict)
                  and record.get('handle') == identity['handle']]
    if len(candidates) != 1 or any(candidates[0].get(key) != value for key, value in identity.items()):
        raise Invalid('安全资产项目缺失、重复或身份不符')
    targets = candidates[0].get('targets')
    if (not isinstance(targets, dict) or set(targets) != {'in_scope', 'out_of_scope'}
            or not isinstance(targets['in_scope'], list) or not targets['in_scope']
            or not isinstance(targets['out_of_scope'], list)):
        raise Invalid('安全资产项目缺少完整范围')
    seen = set()
    for scope, assets in targets.items():
        for asset in assets:
            if (not isinstance(asset, dict) or not isinstance(asset.get('asset_type'), str)
                    or not isinstance(asset.get('asset_identifier'), str) or not asset['asset_identifier'].strip()
                    or asset.get('instruction') is not None and not isinstance(asset['instruction'], str)
                    or type(asset.get('eligible_for_submission')) is not bool
                    or asset['eligible_for_submission'] != (scope == 'in_scope')):
                raise Invalid('安全资产的类型、用途或范围标识无效')
            key = (asset['asset_type'], asset['asset_identifier'])
            if key in seen:
                raise Invalid('安全资产项目含重复或相互矛盾的目标')
            seen.add(key)
    return targets


def markdown(text):
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:
        raise Invalid('读取安全资产说明需要先安装项目依赖') from exc
    return MarkdownIt('commonmark').parse(text)


def normalized_purpose(text):
    return ' '.join(re.sub(r'[*_`]', '', text).split()).casefold()


def listed_domain(value):
    if value != value.strip() or not value or any(char.isspace() for char in value) or '://' in value:
        raise Invalid('安全资产域名列表混入了地址以外的内容')
    row = public_domain_pattern(value)
    if row is None:
        raise Invalid('安全资产域名列表含共享平台范围')
    kind, host = row.split(',')
    if (kind == 'DOMAIN' and not domain_scope.current().suffix(host)[1]
            and domain_scope.current().registrable(host) == host):
        row = 'DOMAIN-SUFFIX,' + host
    return row


def identifier(asset):
    value = asset['asset_identifier']
    kind = asset['asset_type']
    if kind == 'WILDCARD':
        row = listed_domain(value)
        if not value.startswith('*.') or row.split(',')[0] != 'DOMAIN-WILDCARD':
            raise Invalid('安全资产通配范围发生变化')
        return row
    if kind not in {'URL', 'API'}:
        raise Invalid('该资产类型不能当成网络主机')
    try:
        url = urlsplit(value if '://' in value else 'https://' + value)
        if (url.scheme not in ('http', 'https') or not url.hostname or url.username is not None
                or url.password is not None or url.port not in (None, 80, 443) or url.query or url.fragment):
            raise Invalid('安全资产不是公开网站或 API 地址')
        row = public_domain_pattern(url.hostname)
    except ValueError as exc:
        raise Invalid('安全资产 URL 格式无效') from exc
    if row is None or not row.startswith('DOMAIN,'):
        raise Invalid('安全资产 URL 指向共享平台或无效主机')
    return row


def fences(rule, text):
    purpose = rule.get('purpose')
    if purpose is not None and (not isinstance(purpose, str) or not purpose.strip()):
        raise Invalid('安全资产列表缺少明确用途')
    excluded = rule.get('excluded-purposes', {})
    if (not isinstance(excluded, dict) or any(not isinstance(key, str) or not key.strip()
            or not isinstance(reason, str) or not reason.strip() for key, reason in excluded.items())):
        raise Invalid('安全资产排除段需要说明用途')
    context = None
    result = set()
    found = 0
    for token in markdown(text):
        if token.type == 'inline':
            context = normalized_purpose(token.content)
        elif token.type in ('fence', 'code_block'):
            if context in {normalized_purpose(key) for key in excluded}:
                context = None
                continue
            if (purpose is not None and not (context or '').endswith(normalized_purpose(purpose))
                    or purpose is None and context and re.search(r'\bnot\b|\bno longer\b', context)):
                raise Invalid('安全资产代码列表没有对应已确认的用途')
            if token.info.strip():
                raise Invalid('安全资产代码列表的格式发生变化')
            rows = {listed_domain(line) for line in token.content.splitlines() if line.strip()}
            if not rows:
                raise Invalid('安全资产代码列表为空')
            found += 1
            result.update(rows)
            context = None
    if found != 1:
        raise Invalid('安全资产用途列表缺失或重复')
    return result


def matches(rule, asset, wildcards):
    if rule['type'] != asset['asset_type']:
        return False
    if 'label' in rule and rule['label'] != asset['asset_identifier']:
        return False
    text = normalized_purpose(asset.get('instruction') or '')
    if 'purpose-prefix' in rule and not text.startswith(normalized_purpose(rule['purpose-prefix'])):
        return False
    if 'purpose-contains' in rule and normalized_purpose(rule['purpose-contains']) not in text:
        return False
    if rule.get('within-wildcards'):
        row = identifier(asset)
        if not any(domain_scope.covers(parent, row) for parent in wildcards):
            return False
    return True


def parse(recipe, text):
    targets = program(recipe, text)
    selectors = recipe.get('assets')
    non_network = recipe.get('non-network-types', {})
    if (not isinstance(selectors, list) or not selectors
            or not isinstance(non_network, dict) or not set(non_network) <= NON_NETWORK_TYPES
            or any(not isinstance(reason, str) or not reason.strip() for reason in non_network.values())
            or 'complete' in recipe and type(recipe['complete']) is not bool):
        raise Invalid('安全资产缺少用途选择或非网络类型依据')
    for rule in selectors:
        if (not isinstance(rule, dict) or not isinstance(rule.get('type'), str)
                or set(rule) - {'type', 'label', 'purpose-prefix', 'purpose-contains', 'read', 'purpose',
                                'excluded-purposes', 'within-wildcards', 'reason'}
                or rule.get('read') not in ('identifier', 'fenced-domains', 'no-network-target', 'negative-fence')
                or rule.get('read') in ('no-network-target', 'negative-fence') and not rule.get('reason')
                or any(key in rule and (not isinstance(rule[key], str) or not rule[key].strip())
                       for key in ('label', 'purpose-prefix', 'purpose-contains'))
                or 'within-wildcards' in rule and type(rule['within-wildcards']) is not bool):
            raise Invalid('安全资产用途读取方式无效')
        if (rule['read'] == 'identifier' and rule['type'] not in {'URL', 'API', 'WILDCARD'}
                or rule['read'] == 'identifier' and rule['type'] != 'WILDCARD'
                and not any(rule.get(field) for field in ('label', 'purpose-prefix', 'purpose-contains'))
                or rule['read'] != 'identifier' and rule['type'] not in {'OTHER', 'URL'}
                or rule['read'] != 'identifier' and not any(rule.get(field) for field in ('label', 'purpose-prefix', 'purpose-contains'))):
            raise Invalid('安全资产用途选择范围过宽或类型不符')
    assets = targets['in_scope']
    wildcards = {identifier(asset) for asset in assets if asset['asset_type'] == 'WILDCARD'}
    selected = [0] * len(selectors)
    result = set()
    ignored = 0
    unselected = 0
    types = {}
    for asset in assets:
        kind = asset['asset_type']
        types[kind] = types.get(kind, 0) + 1
        chosen = [i for i, rule in enumerate(selectors) if matches(rule, asset, wildcards)]
        if len(chosen) > 1:
            raise Invalid('同一安全资产被多个用途选择，不能确认归属')
        if not chosen:
            if kind in non_network:
                ignored += 1
            elif recipe.get('complete'):
                raise Invalid('完整安全资产项目仍有未归属目标：' + kind + ' ' + asset['asset_identifier'])
            else:
                unselected += 1
            continue
        index = chosen[0]
        selected[index] += 1
        rule = selectors[index]
        method = rule['read']
        if method == 'identifier':
            result.add(identifier(asset))
        elif method in ('fenced-domains', 'negative-fence'):
            rows = fences(rule, asset.get('instruction') or '')
            if method == 'fenced-domains':
                result.update(rows)
            else:
                ignored += 1
        else:
            instruction = asset.get('instruction') or ''
            tokens = markdown(instruction)
            if any(token.type in ('fence', 'code_block') for token in tokens):
                raise Invalid('原无网络目标的资产新增了列表，须先确认用途')
            possible_hosts = re.findall(r'(?<![\w.-])[a-z0-9](?:[a-z0-9-]*\.)+[a-z]{2,}(?![\w.-])',
                                        instruction, re.IGNORECASE)
            for host in possible_hosts:
                row = public_domain_pattern(host)
                if row is None or not any(domain_scope.covers(parent, row) for parent in wildcards):
                    raise Invalid('原无网络目标的资产新增了未归属主机，须先确认用途')
            for value in re.findall(r'[0-9a-fA-F:.]+(?:/\d+)?', instruction):
                if ':' not in value and value.count('.') != 3:
                    continue
                try:
                    ip_network(value.rstrip('.'), strict=False)
                except ValueError:
                    continue
                raise Invalid('原无网络目标的资产新增了 IP 地址或网段，须先确认用途')
            if re.search(r'\bAS[1-9]\d{0,9}\b', instruction, re.IGNORECASE):
                raise Invalid('原无网络目标的资产新增了 ASN，须先确认用途')
            ignored += 1
    if any(count == 0 for count in selected) or not result:
        raise Invalid('安全资产的已声明产品缺失或为空')
    return {'rows': result, 'asset-types': dict(sorted(types.items())), 'assets': len(assets),
            'selected-assets': sum(selected), 'non-network-assets': ignored,
            'unselected-assets': unselected,
            'out-of-scope-assets': len(targets['out_of_scope'])}


def extract(recipe, text):
    return parse(recipe, text)['rows']


def audit(recipe, text):
    record = parse(recipe, text)
    del record['rows']
    return {**record, 'reading-policy': {field: recipe[field] for field in
            ('program', 'assets', 'complete', 'non-network-types') if field in recipe}}


def verify(recipe, record):
    counts = ('assets', 'selected-assets', 'non-network-assets', 'unselected-assets', 'out-of-scope-assets')
    policy = {field: recipe[field] for field in ('program', 'assets', 'complete', 'non-network-types') if field in recipe}
    if (not isinstance(record, dict) or set(record) != {*counts, 'asset-types', 'reading-policy'}
            or record['reading-policy'] != policy
            or any(type(record[field]) is not int or record[field] < 0 for field in counts)
            or not isinstance(record['asset-types'], dict)
            or any(not isinstance(kind, str) or type(count) is not int or count <= 0
                   for kind, count in record['asset-types'].items())
            or sum(record['asset-types'].values()) != record['assets']
            or not 0 < record['selected-assets'] <= record['assets']
            or record['non-network-assets'] > record['assets']
            or record['unselected-assets'] > record['assets']
            or recipe.get('complete') and record['unselected-assets']):
        raise Invalid('安全资产来源的完整范围、类型或读取依据不一致')
