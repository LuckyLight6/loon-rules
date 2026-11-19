"""维护公共规则集；只读公开来源，不读取配置，也没有上传或部署动作。"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from ipaddress import ip_address, ip_network
import json
from pathlib import Path
import re
import sys

import maintain as rules
import endpoint_contracts

ROOT = Path(__file__).resolve().parent
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
PUBLIC_APPLE = rules.APPLE_DOCS[0]
PUBLIC_MAAS = 'https://www.alibabacloud.com/help/en/model-studio/base-url'
PUBLIC_TOKEN = 'https://cloud.tencent.com/document/api/1823/132282'
APPLE_REGIONAL = 'https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/classical/apple-cn.list'
APPLE_DOWNLOAD_ALIASES = {
    'DOMAIN,is-ssl.mzstatic.com-cn-lb.itunes-apple.com.akadns.net',
}


def ordered_route(host, ordered_ids, data):
    for key in ordered_ids:
        if any(rules.match_domain(host.lower(), row) for row in data.get(key, ())):
            return key
    return None


def rule_filename(entry):
    return f'{entry["priority"]:03d}-{entry["id"]}.lsr'


def route_order(config, entries, views=()):
    active=set(config['detailed']+config['general'])
    for key in views:
        active.difference_update(entries[key]['members'])
        active.add(key)
    return sorted(active,key=lambda key:entries[key]['priority'])


def shadowed_domains(order, data):
    """Yield a later domain rule whose entire scope has an earlier owner."""
    ranks={k:i for i,k in enumerate(order)}
    exact,suffix,patterns={},{},[]
    for key in order:
        local=[]
        for row in data[key]:
            kind,value,*flags=row.split(',')
            if flags or kind not in ('DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD','DOMAIN-KEYWORD'):
                continue
            host=value.casefold()
            local.append((kind,host,row))
            if kind not in ('DOMAIN','DOMAIN-SUFFIX'):
                continue
            labels=host.split('.')
            parents=('.'.join(labels[i:]) for i in range(len(labels)))
            owners=[suffix[p] for p in parents if p in suffix]
            if kind=='DOMAIN':
                if host in exact:
                    owners.append(exact[host])
                owners.extend((name,pattern) for name,pattern in patterns
                              if rules.match_domain(host,pattern))
            if owners:
                owner,by=min(owners,key=lambda x:ranks[x[0]])
                yield key,row,owner,by
        for kind,host,row in local:
            if kind in ('DOMAIN','DOMAIN-SUFFIX'):
                (exact if kind=='DOMAIN' else suffix).setdefault(host,(key,row))
            else:
                patterns.append((key,row))


def verify_domain_order(order, entries, data):
    for key,row,owner,by in shadowed_domains(order,data):
        if not entries[key].get('fallback'):
            raise rules.Invalid(f'专项被更早的规则整条覆盖：{key} {row} ← {owner} {by}')


def ordered_ip_route(target, ordered_ids, data, *, literal):
    address=ip_address(target)
    for key in ordered_ids:
        for row in data.get(key, ()):
            kind, value, *flags=row.split(',')
            if kind in ('IP-CIDR','IP-CIDR6') and (literal or 'no-resolve' not in flags):
                if address in ip_network(value,strict=False):
                    return key
    return None


def project_domains(rows, scope):
    """Use documented product roots and exact aliases, not shared vendors."""
    def within(host, roots):
        return any(host==root or host.endswith('.'+root) for root in roots)

    kept=[]
    for row in rows:
        kind,host,*flags=row.split(',')
        if kind not in ('DOMAIN','DOMAIN-SUFFIX') or flags:
            continue
        host=host.casefold()
        if within(host,scope.get('exclude',())):
            continue
        if within(host,scope.get('roots',())):
            kept.append(kind+','+host)
        elif host in scope.get('exact',()):
            # Shared services may be selected by exact hostname only.
            kept.append('DOMAIN,'+host)
    return kept


def covers(parent, child):
    if parent==child:
        return True
    a,b,*af=parent.split(',')
    c,d,*cf=child.split(',')
    return (not af and not cf and a=='DOMAIN-SUFFIX' and c in ('DOMAIN','DOMAIN-SUFFIX')
            and (b==d or d.endswith('.'+b)))


def compact(rows):
    rows=list(dict.fromkeys(rows))
    suffixes={r.split(',')[1] for r in rows if r.startswith('DOMAIN-SUFFIX,') and r.count(',')==1}
    kept=[]
    for r in rows:
        k,p,*f=r.split(',')
        labels=p.split('.')
        if not f and k in ('DOMAIN','DOMAIN-SUFFIX'):
            # 只合并单一用途或同一视图内的等价域名。IP 参数不参与归并。
            if any('.'.join(labels[i:]) in suffixes for i in range(k=='DOMAIN-SUFFIX',len(labels))):
                continue
        kept.append(r)
    return kept


def reviewed_input(entry, downloaded):
    """Parse licensed source material, keeping only the rule kinds we publish."""
    allowed=set(entry.get('publish-kinds',entry['kinds']))
    permitted=set(entry.get('allowed-shared',()))
    excluded=set(entry.get('excluded-rules',()))
    current=[]
    for url in entry['sources'] if 'feed-sources' not in entry else entry['feed-sources']:
        for row in rules.read_rules(downloaded[url],set(entry['kinds']),set(entry['flags'])):
            kind,value,*_=row.split(',')
            if row in excluded or kind not in allowed or (kind=='IP-CIDR' and value=='17.0.0.0/8'):
                continue
            if kind=='DOMAIN-SUFFIX' and (value.casefold() in SHARED_PARENT or '.' not in value) and value not in permitted:
                continue
            current.append(row)
    if not current:
        raise rules.Invalid('筛选后没有可用规则：'+entry['id'])
    if include:=entry.get('include'):
        current.extend(rules.read_rules('\n'.join(include),allowed,set(entry['flags'])))
    return compact(current)


def uncovered_count(rows, baseline):
    existing=set(baseline)
    suffixes={r.split(',')[1] for r in existing if r.startswith('DOMAIN-SUFFIX,') and r.count(',')==1}
    count=0
    for row in rows:
        if row in existing:
            continue
        kind,value,*flags=row.split(',')
        if kind in ('DOMAIN','DOMAIN-SUFFIX') and not flags:
            parts=value.split('.')
            if any('.'.join(parts[i:]) in suffixes for i in range(len(parts))):
                continue
        count+=1
    return count


def overlapping_rules(left,right):
    """Find shared rows or domain suffix containment in either direction."""
    def normalized(rows):
        for row in rows:
            kind,sep,value=row.partition(',')
            yield kind+sep+value.casefold() if kind in ('DOMAIN','DOMAIN-SUFFIX') else row
    a,b=list(normalized(left)),list(normalized(right))
    return uncovered_count(a,b)<len(a) or uncovered_count(b,a)<len(b)


def refresh_reviewed_feed(entry, last, downloaded):
    """Report arbitrary source drift without publishing candidate names or addresses."""
    urls=entry.get('feed-sources',entry['sources'])
    if any(url not in downloaded for url in urls):
        return last,{'state':'unavailable'}
    try:
        now=reviewed_input(entry,downloaded)
        rules.verify_ip_options(entry,rules.ip_options(now))
    except rules.Invalid:
        return last,{'state':'invalid'}
    added=uncovered_count(now,last)
    removed=uncovered_count(last,now)
    if added or removed:
        return last,{'state':'review','new-matches':added,'missing-rules':removed}
    return last,{'state':'current'}


def metadata(text):
    return dict(re.findall(r'(?m)^# ((?:created|updated)-at): ([^\n]+)$',text or ''))


def decorate(entry, rows, old, now):
    times=metadata(old)
    unchanged=old is not None and rules.read_rules(old)==rows
    lines=[
        '# name: '+entry['id'],
        '# description: '+entry['description'],
        '# boundary: '+entry['boundary'],
        '# created-at: '+times.get('created-at', now),
        '# updated-at: '+(times.get('updated-at',now) if unchanged else now),
        '# rule-count: '+str(len(rows)),
    ]
    if 'priority' in entry:
        lines[1:1]=[f'# priority: {entry["priority"]:03d}', '# section: '+entry['section']]
    lines.extend('# source: '+u for u in dict.fromkeys(entry['sources']))
    return '\n'.join(lines+['']+rows)+'\n'


def verify_file(entry, rows, text):
    times=metadata(text)
    try:
        created=datetime.strptime(times['created-at'],'%Y-%m-%dT%H:%M:%SZ')
        updated=datetime.strptime(times['updated-at'],'%Y-%m-%dT%H:%M:%SZ')
    except (ValueError,KeyError) as exc:
        raise rules.Invalid('时间元数据不是 UTC：'+entry['id']) from exc
    if updated<created or text!=decorate(entry,rows,text,times['updated-at']):
        raise rules.Invalid('规则头部或正文不符合清单：'+entry['id'])


CN_MAAS = {'cn-beijing','cn-shanghai','cn-shenzhen','cn-hangzhou','cn-zhangjiakou','cn-chengdu',
           'cn-wulanchabu','cn-nanjing','cn-qingdao','cn-heyuan','cn-guangzhou','cn-huhehaote'}
INTL_MAAS = {'cn-hongkong','ap-southeast-1','ap-northeast-1','eu-central-1','us-east-1','us-west-1'}
CN_ENDPOINTS = {'dashscope.aliyuncs.com','coding.dashscope.aliyuncs.com'}
INTL_ENDPOINTS = {'dashscope-intl.aliyuncs.com','dashscope-us.aliyuncs.com',
                 'cn-hongkong.dashscope.aliyuncs.com','coding-intl.dashscope.aliyuncs.com'}
MAAS_HOST = re.compile(r'(?:[a-z0-9-]+\.)?([a-z0-9-]+)\.maas\.aliyuncs\.com\Z')
TOKEN_HOST = re.compile(r'(?<![a-z0-9.-])tokenhub(?:\.([a-z0-9-]+))?\.tencentcloudapi\.com(?![a-z0-9.-])')
CN_TOKEN = {'ap-guangzhou','ap-shanghai','ap-nanjing','ap-beijing','ap-chengdu','ap-chongqing',
            'ap-shanghai-fsi','ap-shenzhen-fsi'}
INTL_TOKEN = {'ap-hongkong','ap-singapore','ap-jakarta','ap-bangkok','ap-seoul','ap-tokyo',
              'na-ashburn','na-siliconvalley','sa-saopaulo','eu-frankfurt'}


def regional_workspaces(doc, international):
    answer=set()
    doc=doc.replace('{WorkspaceId}.','').replace('{workspace-id}.','')
    for host in re.findall(r'https://([A-Za-z0-9.-]+)',doc):
        host=host.lower().rstrip('.')
        if host in (INTL_ENDPOINTS if international else CN_ENDPOINTS):
            answer.add('DOMAIN,'+host)
        match=MAAS_HOST.fullmatch(host)
        if match and match[1] in (INTL_MAAS if international else CN_MAAS):
            answer.add('DOMAIN-SUFFIX,'+match[1]+'.maas.aliyuncs.com')
    return answer


def tokenhub(doc, international):
    return {'DOMAIN,'+m[0] for m in TOKEN_HOST.finditer(doc)
            if m[1] in (INTL_TOKEN if international else CN_TOKEN|{None})}


def apple_table(doc, purpose, aliases=()):
    parser=rules.AppleTables()
    parser.feed(doc)
    rows=set()
    for section in purpose:
        for host,_ in parser.rows[section]:
            host=host.lower().strip()
            if rules.valid_host(host) and (host.endswith('.apple.com') or host in aliases):
                rows.add('DOMAIN,'+host)
    return rows


OTA_PAYLOAD={
    'appldnld.apple.com','appldnld.apple.com.akadns.net','appldnld.apple.com.mwcname.com',
    'appldnld.apple.com.edgesuite.net','appldnld.g.aaplimg.com',
    'oscdn.apple.com','swcdn.apple.com','swdownload.apple.com',
    'updates.cdn-apple.com','updates-http.cdn-apple.com',
}


def ota_payload_host(host):
    return any(host==base or host.endswith('.'+base) for base in OTA_PAYLOAD)


ICLOUD_CONTENT = 'DOMAIN-SUFFIX,icloud-content.com'
ICLOUD_MAINLAND = {'DOMAIN-SUFFIX,apzones.com','DOMAIN-SUFFIX,icloud.com.cn',
                   'DOMAIN-SUFFIX,icloud-content.com.cn'}
PCC_SHARED_HOSTS = {'apple-relay.cloudflare.com','apple-relay.fastly-edge.com','cp4.cloudflare.com'}


def apple_intelligence_hosts(doc):
    parser=rules.AppleTables()
    parser.feed(doc)
    return {'DOMAIN,'+host for host,purpose in parser.rows['aisirisearch']
            if (purpose.casefold() in ('private cloud compute','apple intelligence extensions')
                and (host in PCC_SHARED_HOSTS or host.endswith('.apple.com'))
                and rules.valid_host(host))}


def selected(rows_by_url, name):
    if name=='apple-account':
        result=rules.apple_endpoints(rows_by_url[PUBLIC_APPLE],'apple-auth')
    elif name=='apple-cloud':
        result=rules.apple_endpoints(rows_by_url[PUBLIC_APPLE],'icloud')
        result-=ICLOUD_MAINLAND|{ICLOUD_CONTENT,'DOMAIN-SUFFIX,cdn-apple.com','DOMAIN,metrics.icloud.com'}
    elif name=='apple-cloud-content':
        result=rules.apple_endpoints(rows_by_url[PUBLIC_APPLE],'icloud')&{ICLOUD_CONTENT}
    elif name=='apple-cloud-mainland':
        result=rules.apple_endpoints(rows_by_url[PUBLIC_APPLE],'icloud')&ICLOUD_MAINLAND
    elif name=='apple-intelligence':
        result=apple_intelligence_hosts(rows_by_url[PUBLIC_APPLE])
    elif name=='apple-store':
        result=rules.app_store_rules(rows_by_url[rules.ROY])
    elif name=='apple-mainland-download-aliases':
        result=set(rules.read_rules(rows_by_url[APPLE_REGIONAL]))&APPLE_DOWNLOAD_ALIASES
    elif name in ('apple-update','apple-update-downloads'):
        result=apple_table(rows_by_url[PUBLIC_APPLE],('software','carrier','caching','beta'),
                           OTA_PAYLOAD|{'itunes.com'})
        # This exact host also serves the store; preserve its one declared owner.
        result.discard('DOMAIN,itunes.apple.com')
        result={row for row in result if ota_payload_host(row.split(',')[1])==(name=='apple-update-downloads')}
    elif name=='apple-certificate':
        result=apple_table(rows_by_url[PUBLIC_APPLE],('certificate',))
    elif name=='apple-schoolwork-handouts':
        parser=rules.AppleTables()
        parser.feed(rows_by_url[PUBLIC_APPLE])
        result={'DOMAIN,'+host for host,purpose in parser.rows['classschool']
                if 'schoolwork handout' in purpose.casefold() and host.endswith('.apple.com')
                and rules.valid_host(host)}
    elif name in ('ai-cn','ai-cn-international'):
        intl=name=='ai-cn-international'
        region=regional_workspaces(rows_by_url[PUBLIC_MAAS],intl)
        token=tokenhub(rows_by_url[PUBLIC_TOKEN],intl)
        if not region or not token:
            raise rules.Invalid('地域文档未能提取入口')
        result=region|token
    else:
        raise rules.Invalid('未知筛选器：'+name)
    if not result:
        raise rules.Invalid('未能提取必要入口：'+name)
    return result


def selector_urls(name):
    if name=='apple-store':
        return (rules.ROY,)
    if name=='apple-mainland-download-aliases':
        return (APPLE_REGIONAL,)
    if name.startswith('apple-'):
        return (PUBLIC_APPLE,)
    if name in ('ai-cn','ai-cn-international'):
        return PUBLIC_MAAS,PUBLIC_TOKEN
    raise rules.Invalid('未知筛选器：'+name)


def section_for(config, rank):
    matches=[item['id'] for item in config['sections'] if item['from']<=rank<=item['through']]
    if len(matches)!=1:
        raise rules.Invalid(f'优先级 {rank:03d} 没有唯一分区')
    return matches[0]


def validate_declarations(config):
    entries={}
    priorities=set()
    for e in config['entries']:
        name=e['id']
        if not SLUG.fullmatch(name) or name in entries:
            raise rules.Invalid('重复或不合规的名称：'+name)
        if e['mode'] not in ('compiled','managed','view') or not e['description'] or not e['boundary'] or not e['sources']:
            raise rules.Invalid('元数据未达成：'+name)
        rank=e['priority']
        if not isinstance(rank,int) or not 1<=rank<=999 or rank in priorities or e['section']!=section_for(config,rank):
            raise rules.Invalid('重复或不合规的编号：'+name)
        priorities.add(rank)
        entries[name]=e
    names=[*config['detailed'],*config['general']]
    if len(set(names))!=len(names) or any(entries[k]['mode']=='view' for k in names):
        raise rules.Invalid('细分或通用视图误启用合并表')
    modes=names+config['views']+config['alternatives']+config['optional']
    if len(modes)!=len(entries) or set(modes)!=set(entries):
        raise rules.Invalid('分区必须包含每个条目且只出现一次')
    for e in entries.values():
        if e['mode']=='managed' and (not e.get('kinds') or not e.get('license') or
                                    not set(e.get('feed-sources',()))<=set(e['sources'])):
            raise rules.Invalid('自管来源缺少语法或许可：'+e['id'])
        if set(e.get('flags',()))-{'no-resolve'}:
            raise rules.Invalid('来源含未确认的 Loon 参数：'+e['id'])
        for part in e.get('projection',()):
            if part['source'] not in e['sources'] or not (part.get('roots') or part.get('exact')):
                raise rules.Invalid('筛选缺少来源或服务边界：'+e['id'])
        if e['mode']=='view':
            if (e['id'] not in config['views'] or not e['members']
                or not set(e['members'])<=set(names)
                or any(e['priority']>=entries[k]['priority'] or e['section']!=entries[k]['section']
                       for k in e['members'])):
                raise rules.Invalid('合并视图包含未归类成员：'+e['id'])
    for section in config['sections']:
        for ref in section.get('related',()):
            if ref['id'] not in entries or entries[ref['id']]['section']==section['id'] or not ref['note']:
                raise rules.Invalid('跨区引用无效：'+ref['id'])
    members=[k for view in config['views'] for k in entries[view]['members']]
    if len(members)!=len(set(members)):
        raise rules.Invalid('合集之间含相同成员')
    return entries


def render_index(config, entries):
    sizes={'compiled':'按用途整理','managed':'审核后发布','view':'合集'}
    roles={k:'备选' for k in config['alternatives']}|{k:'可选' for k in config['optional']}
    lines=['# 规则订阅清单','',
           '按需要选规则，放进 Loon 的订阅列表。**常规**按编号从小到大排；选合集就不用再订阅它的成员。'
           '**备选**用来替换同用途的规则，不是额外补充。编号只决定同一来源、同一匹配阶段内的顺序。',
           '', '打开规则后点 **Raw** 复制订阅地址。来源和更新时间在文件开头；[status.json](status.json)记录最近检查及待复核的变化。']
    for section in config['sections']:
        lines += ['',f'## {section["from"]:03d}–{section["through"]:03d} {section["title"]}','',
                  '| 编号 · 规则 | 用途 | 来源方式 | 范围 |','|---|---|---|---|']
        for e in sorted(entries.values(),key=lambda e:e['priority']):
            if e['section']!=section['id']:
                continue
            key=e['id']
            url='rules/'+rule_filename(e)
            role=roles.get(key,'替换成员' if e['mode']=='view' else '常规')
            lines.append(f'| [{e["priority"]:03d}-{key}]({url}) | {e["description"]} | {role} · {sizes[e["mode"]]} | {e["boundary"]} |')
        for e in sorted(entries.values(),key=lambda e:e['priority']):
            if e['section']==section['id'] and e['mode']=='view':
                numbers='、'.join(f'{entries[k]["priority"]:03d}' for k in sorted(e['members'],key=lambda k:entries[k]['priority']))
                lines += ['',f'**{e["priority"]:03d} 合集替换：** {numbers}。']
        if section.get('related'):
            lines+=['','**相关专项（沿用同一份规则）：**']
            for ref in section['related']:
                e=entries[ref['id']]
                name=rule_filename(e)
                lines.append(f'- [{name[:-4]}](rules/{name})：{ref["note"]}')
    return '\n'.join(lines)+'\n'


SHARED_PARENT = {'apple.com','cdn-apple.com','akadns.net','googleapis.com',
                 'google.com','cloudflare.com','amazonaws.com','aliyuncs.com','maas.aliyuncs.com',
                 'tencentcloudapi.com','volces.com','livekit.cloud','blob.core.windows.net','azureedge.net',
                 'githubusercontent.com','x.com','auth0.com','azurefd.net','azurewebsites.net',
                 'cloudapp.net','trafficmanager.net','edgesuite.net','edgekey.net',
                 'akamaihd.net','akamaized.net'}


def lint_content(name, rows, allowed_shared=()):
    for r in rows:
        t,p,*_=r.split(',')
        if t=='DOMAIN-SUFFIX' and p.casefold() not in allowed_shared and (p.casefold() in SHARED_PARENT or '.' not in p):
            raise rules.Invalid('整段共享后缀：'+name+' '+r)
        if t in ('IP-CIDR','IP-CIDR6') and p=='17.0.0.0/8':
            raise rules.Invalid('整个 Apple IPv4 段不属于专项：'+name)
    if list(rows)!=compact(rows):
        raise rules.Invalid('存在等价条目：'+name)


def verify_cases(config, entries, data, online, contracts=()):
    order=route_order(config,entries)
    for host,wanted in config['critical'].items():
        got=ordered_route(host,order,data)
        if got not in wanted:
            raise rules.Invalid(f'{host}: 首条命中 {got!r}，应为 {", ".join(wanted)}')
    protected=config.get('protected-sections', ['apple','ai'])
    specialties=[k for k in order if entries[k]['section'] in protected]
    for host in config['shared-negatives']:
        if ordered_route(host,specialties,data):
            raise rules.Invalid('共享端点被专项覆盖：'+host)
    for host,forbidden in config.get('scope-negatives',{}).items():
        if hit:=ordered_route(host,forbidden,data):
            raise rules.Invalid(f'{host}: 非本业务的域名被 {hit} 接管')
    for host,wanted in config.get('view-cases',{}).items():
        got={k for k in config['views'] if any(rules.match_domain(host,row) for row in data.get(k,[]))}
        if got!=set(wanted):
            raise rules.Invalid('合并命中不同：'+host+': '+','.join(sorted(got)))
    for host in config['shared-negatives']:
        if any(rules.match_domain(host,r) for k in config['views'] if not entries[k].get('fallback')
               for r in data.get(k,[])):
            raise rules.Invalid('合并视图劫持共享端点：'+host)
    for k,blocks in config.get('no-overlap',{}).items():
        for block in blocks:
            if overlapping_rules(data[k],data[block]):
                raise rules.Invalid('跨业务规则重叠：'+k+' / '+block)
    for case in config.get('ip-cases',()):
        want=case['rule']
        got=ordered_ip_route(case['target'],order,data,literal=case['literal'])
        if got!=want:
            raise rules.Invalid(f'{case["target"]}: IP 阶段命中 {got!r}，应为 {want}')
    if online:
        verify_domain_order(order,entries,data)
        endpoint_contracts.verify_routes(contracts,entries,order,data)
        scenarios=[[view] for view in config['views']]+[config['views']]
        for views in scenarios:
            replacements={k:view for view in views for k in entries[view]['members']}
            combined=route_order(config,entries,views)
            verify_domain_order(combined,entries,data)
            endpoint_contracts.verify_routes(contracts,entries,combined,data,replacements)
            scenario='+'.join(views)
            for host,wanted in config['critical'].items():
                expected={replacements.get(k,k) for k in wanted}
                got=ordered_route(host,combined,data)
                if got not in expected:
                    raise rules.Invalid(f'{scenario}: {host} 首条命中 {got!r}，应为 {sorted(expected)}')
            for case in config.get('ip-cases',()):
                expected=replacements.get(case['rule'],case['rule'])
                got=ordered_ip_route(case['target'],combined,data,literal=case['literal'])
                if got!=expected:
                    raise rules.Invalid(f'{scenario}: {case["target"]} IP 阶段命中 {got!r}，应为 {expected}')
        for keys in config.get('exclusive-domains',()):
            for i,key in enumerate(keys):
                for other in keys[:i]:
                    for row in data[key]:
                        if any(covers(row,b) or covers(b,row) for b in data[other]):
                            raise rules.Invalid(f'专项重复匹配范围：{other} / {key}：{row}')
        owned={}
        for key in order:
            if entries[key].get('fallback'):
                continue
            for row in data[key]:
                old=owned.setdefault(row,key)
                if old!=key:
                    raise rules.Invalid(f'条目重复：{old} / {key}：{row}')


def merge_view(entry, data):
    excluded=set(entry.get('exclude',[]))
    return compact(row for member in entry['members'] for row in data[member] if row not in excluded)


def run(check=False, offline=False):
    config=json.loads((ROOT/'catalog.json').read_text())
    contracts=json.loads((ROOT/'endpoint-contracts.json').read_text())
    entries=validate_declarations(config)
    file_entries=entries
    paths={k:ROOT/'rules'/rule_filename(e) for k,e in file_entries.items()}
    if set((ROOT/'rules').glob('*.lsr'))!=set(paths.values()):
        raise rules.Invalid('规则文件与清单不一致')
    if (ROOT/'INDEX.md').read_text()!=render_index(config,entries):
        raise rules.Invalid('编号索引未更新（maintain.py --render-index）')
    old={k:p.read_text() for k,p in paths.items()}
    data={k:rules.read_rules(t) for k,t in old.items()}
    for k,rows in data.items():
        lint_content(k,rows,entries[k].get('allowed-shared',()))
        verify_file(entries[k],rows,old[k])
        rules.verify_ip_options(entries[k],rules.ip_options(rows))
    if offline:
        for key in config['views']:
            if data[key]!=merge_view(entries[key],data):
                raise rules.Invalid('合集与专项不一致：'+key)
        verify_cases(config,entries,data,True,contracts)
        print(f'{len(file_entries)} 份本地规则的范围、元数据和合并模式通过离线检查。')
        return 0

    reviewed={k:e for k,e in entries.items() if e['mode']=='managed'}
    watched={u for e in reviewed.values() for u in e.get('feed-sources',e['sources'])}
    urls={contract['source'] for contract in contracts}
    for e in file_entries.values():
        sel=e.get('selector')
        if sel: urls.update(selector_urls(sel))
        urls.update(s['source'] for s in e.get('projection',()))
        if e.get('cidr-source'):
            urls.add(e['cidr-source'])
    def fetch(url):
        try:
            return rules.download(url)
        except (rules.Invalid,OSError) as exc:
            if url not in urls:
                return None  # A reviewed feed still has its own last good output.
            raise rules.Invalid(f'{url}：{exc}') from exc
    requested=sorted(urls|watched)
    with ThreadPoolExecutor(max_workers=8) as pool:
        downloaded={u:t for u,t in zip(requested,pool.map(fetch,requested)) if t is not None}
    contract_status=endpoint_contracts.verify_sources(contracts,downloaded)
    source_status={}
    for k,e in reviewed.items():
        data[k],source_status[k]=refresh_reviewed_feed(e,data[k],downloaded)
    for k,e in file_entries.items():
        if e['mode']!='compiled':
            continue
        if e.get('projection'):
            projected=[]
            for part in e['projection']:
                rows=project_domains(rules.read_rules(downloaded[part['source']]),part)
                if not rows:
                    raise rules.Invalid('上游没有符合用途的域名：'+k)
                projected.extend(rows)
            data[k]=compact(e.get('include',[])+projected)
        if source:=e.get('cidr-source'):
            networks=[ip_network(line.strip()) for line in downloaded[source].splitlines() if line.strip()]
            if not networks or any(n.prefixlen<(16 if n.version==4 else 24) or not n.is_global for n in networks):
                raise rules.Invalid('厂商 CIDR 越界：'+k)
            data[k]=compact(data[k]+[('IP-CIDR,' if n.version==4 else 'IP-CIDR6,')+str(n)+',no-resolve' for n in networks])
        if e.get('selector'):
            data[k]=compact(data[k]+sorted(selected(downloaded,e['selector'])-set(data[k])))
        lint_content(k,data[k],e.get('allowed-shared',()))
        rules.verify_ip_options(e,rules.ip_options(data[k]))
        if e.get('projection') and len(rules.read_rules(old[k]))-len(data[k])>max(2,len(data[k])//6):
            raise rules.Invalid('上游筛选范围明显缩水：'+k)
    for key in config['views']:
        e=entries[key]
        data[key]=merge_view(e,data)
        lint_content(key,data[key],e.get('allowed-shared',()))
    verify_cases(config,entries,data,True,contracts)
    now=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    changed=[]
    for key,e in file_entries.items():
        rendered=decorate(e,data[key],old[key],now)
        if rendered==old[key]:
            continue
        changed.append(key)
        if not check:
            tmp=paths[key].with_suffix('.new')
            tmp.write_text(rendered)
            tmp.replace(paths[key])
    if not check:
        (ROOT/'status.json').write_text(json.dumps({
            'checked-at':now,'inputs-read':len(downloaded),'critical':len(config['critical']),
            'inputs-requested':len(requested),'reviewed-inputs':source_status,
            'official-endpoints':contract_status,
            'shared-negatives':len(config['shared-negatives']), 'changed':changed,
            'scope-negatives':len(config.get('scope-negatives',{})),
            'ip-cases':len(config.get('ip-cases',())),
            'rules':{k:len(data[k]) for k in sorted(data,key=lambda k:entries[k]['priority'])},
        },ensure_ascii=False,indent=2)+'\n')
    negatives=len(config['shared-negatives'])+len(config.get('scope-negatives',{}))
    print(f'{len(config["critical"])} 个业务域名、{negatives} 个反例、{len(config.get("ip-cases",()))} 个 IP 用例、'
          f'{len(config["views"])} 种合并视图通过；{len(changed)} 份正文或元数据变化。')
    print('官方端点核对：'+', '.join(f'{name} {s["assigned"]} 项归属 / {s["shared"]} 项共享'
                                   for name,s in contract_status.items()))
    attention={k:v['state'] for k,v in source_status.items() if v['state']!='current'}
    if attention:
        print('保留已审正文的来源：'+', '.join(f'{k}={s}' for k,s in attention.items()))
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--verify-files',action='store_true',help='本地离线校验')
    group.add_argument('--check',action='store_true',help='联网核对，但不写入本地')
    group.add_argument('--refresh',action='store_true',help='联网校验和更新本地规则；不触发推送')
    group.add_argument('--render-index',action='store_true',help='按清单重建带编号的规则索引')
    args=p.parse_args()
    try:
        if args.render_index:
            config=json.loads((ROOT/'catalog.json').read_text())
            (ROOT/'INDEX.md').write_text(render_index(config,validate_declarations(config)))
            return 0
        # 默认只验证，显式 --refresh 才修改规则。
        return run(check=args.check,offline=args.verify_files or not (args.check or args.refresh))
    except (rules.Invalid,OSError,ValueError,KeyError) as error:
        print('保留上一版本：'+str(error),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
