"""维护公共规则集；只读公开来源，不读取配置，也没有上传或部署动作。"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from ipaddress import collapse_addresses, ip_address, ip_network
import json
from pathlib import Path
import re
import sys

import maintain as rules
import endpoint_contracts
import calibration
from rule_inputs import extract_rows

ROOT = Path(__file__).resolve().parent
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')


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
    wild={r.removeprefix('DOMAIN-WILDCARD,*.') for r in rows if r.startswith('DOMAIN-WILDCARD,*.')
          and not re.search(r'[?*\[\],]',r.split('*.')[1]) and r.count('*')==1}
    kept=[]
    for r in rows:
        k,p,*f=r.split(',')
        if k=='DOMAIN-WILDCARD' and not f and p.startswith('*.') and p[2:] in wild:
            labs=p[2:].split('.')
            chain=['.'.join(labs[i:]) for i in range(len(labs))]
            if any(x in suffixes for x in chain) or any(x in wild for x in chain[1:]):
                continue
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
            if row in excluded or kind not in allowed or overbroad(kind,value,permitted):
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


def protected_hosts(entry,config,entries,contracts):
    if entry.get('policy-hint')!='reject':
        return set()
    normal={host for host,owners in config['critical'].items()
            if all(entries[k].get('policy-hint')!='reject' for k in owners)}
    for contract in contracts:
        normal.update(host for owner,hosts in contract['routes'].items()
                      if entries[owner].get('policy-hint')!='reject' for host in hosts if '*' not in host)
    return normal|{host for host,forbidden in config.get('scope-negatives',{}).items() if entry['id'] in forbidden}


def without_protected(rows,hosts):
    if not hosts: return rows
    hosts={host.casefold() for host in hosts}
    parents={'.'.join(bits[i:]) for host in hosts for bits in [host.split('.')] for i in range(len(bits))}
    def conflicts(row):
        kind,value,*_=row.split(',')
        if kind=='DOMAIN': return value.casefold() in hosts
        if kind=='DOMAIN-SUFFIX': return value.casefold() in parents
        return kind in ('DOMAIN-KEYWORD','DOMAIN-WILDCARD') and any(rules.match_domain(h,row) for h in hosts)
    return [row for row in rows if not conflicts(row)]


def outside_domain_scopes(rows,reserved):
    """Keep domain rules disjoint in both directions, including parent suffixes."""
    if not reserved: return rows
    def lineage(host):
        labels=host.split('.')
        return ('.'.join(labels[i:]) for i in range(len(labels)))
    exact=set(); suffix=set(); ancestors=set()
    for row in reserved:
        kind,host,*flags=row.casefold().split(',')
        if flags or kind not in ('domain','domain-suffix'):
            raise rules.Invalid('预留范围只能使用域名或域名后缀')
        exact.add(host); ancestors.update(lineage(host))
        if kind=='domain-suffix': suffix.add(host)
    def keep(row):
        kind,host,*flags=row.casefold().split(',')
        if flags or kind not in ('domain','domain-suffix'):
            raise rules.Invalid('域名隔离不能用于混合匹配规则')
        return host not in exact and not any(p in suffix for p in lineage(host)) and not (
            kind=='domain-suffix' and host in ancestors)
    return [r for r in rows if keep(r)]


def calibration_urls(spec):
    if not spec:return []
    if spec['method']=='allocation-and-routing':return [spec['allocation'],spec['routes']]
    if spec['method']=='domain-ad-consensus':return [*spec['filter-lists'],spec['dns-list']]
    raise rules.Invalid('未知校准方式')


def refresh_reviewed_feed(entry, last, downloaded, *, protected=(), reserved=(), corroborated=(), adopt_ads=False):
    """Report arbitrary source drift without publishing candidate names or addresses."""
    excluded=set(entry.get('excluded-rules',()))
    last=outside_domain_scopes(without_protected([r for r in last if r not in excluded],protected),reserved)
    if not last: raise rules.Invalid('排除业务端点后无法生成非空订阅：'+entry['id'])
    urls=entry.get('feed-sources',entry['sources'])
    spec=entry.get('calibration',{})
    if any(url not in downloaded for url in [*urls,*calibration_urls(spec)]):
        return last,{'state':'unavailable'}
    try:
        now=without_protected(reviewed_input(entry,downloaded),protected)
        rules.verify_ip_options(entry,rules.ip_options(now))
    except rules.Invalid:
        return last,{'state':'invalid'}
    outside={}
    if reserved:
        scoped=outside_domain_scopes(now,reserved)
        if len(now)!=len(scoped): outside['reserved-scopes']=len(now)-len(scoped)
        now=scoped
    if roots:=entry.get('exclude-tenant-roots'):
        # A tenant name establishes a hosting provider, not a product or a region.
        def tenant(row):
            kind,host,*_=row.split(',')
            return kind in ('DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD') and any(
                host.casefold().endswith('.'+root) for root in roots)
        scoped=[row for row in now if not tenant(row)]
        if len(scoped)!=len(now): outside['outside-purpose']=len(now)-len(scoped)
        now=scoped
    if spec:
        if spec['method']=='allocation-and-routing':
            try:
                result,stats=calibration.networks(last,now,downloaded[spec['allocation']],downloaded[spec['routes']])
            except (ValueError,rules.Invalid):
                return last,{'state':'invalid'}
            return result,{'state':'current',**stats}
        sources=['\n'.join(downloaded[u] for u in spec['filter-lists']),downloaded[spec['dns-list']]]
        result=calibration.confirmed_ads(now,sources)
        lost=uncovered_count(last,result); gain=uncovered_count(result,last)
        if not result or (not adopt_ads and 20*max(gain,lost)>len(last)):
            return last,{'state':'review','new-matches':gain,'missing-rules':lost}
        return stable_order(result,last),{'state':'current','not-whole-host-consensus':len(now)-len(result),
                                          'admitted-rules':gain,'retired-rules':lost}
    if entry.get('confirm-additions-with'):
        def index(rows):
            exact=set(rows); suffix={r.split(',')[1] for r in exact if r.startswith('DOMAIN-SUFFIX,')}
            def includes(row):
                parts=row.split(',')[1].split('.')
                return row in exact or any('.'.join(parts[i:]) in suffix for i in range(len(parts)))
            return includes
        published=index(last); backed=index(corroborated)
        admitted=[r for r in now if published(r) or backed(r)]
        outside['unconfirmed-domains']=len(now)-len(admitted)
        # A large or empty upstream withdrawal requires review, not a baseline reset.
        lost=uncovered_count(last,admitted); gain=uncovered_count(admitted,last)
        if not admitted or max(lost,gain)>max(1,len(last)//20):
            return last,{'state':'review','new-matches':gain,'missing-rules':lost,**outside}
        return stable_order(admitted,last),{'state':'current',**outside}
    added=uncovered_count(now,last)
    removed=uncovered_count(last,now)
    if entry.get('reconcile')=='ad-withdrawals' and removed and removed<=len(last)//20:
        # Trust an upstream withdrawal to narrow blocking, never to expand it.
        # Leave non-domain decisions (IP flags, keywords) for explicit review.
        old_set=set(last)
        old_domains=[r for r in last if r.startswith(('DOMAIN,','DOMAIN-SUFFIX,'))]
        new_domains=[r for r in now if r.startswith(('DOMAIN,','DOMAIN-SUFFIX,'))]
        def index(rows):
            return set(rows),{r.split(',')[1] for r in rows if r.startswith('DOMAIN-SUFFIX,')}
        def present(row,idx):
            exact,suffix=idx; parts=row.split(',')[1].split('.')
            return row in exact or any('.'.join(parts[i:]) in suffix for i in range(len(parts)))
        before,after=index(old_domains),index(new_domains)
        revised=[r for r in last if r not in before[0] or present(r,after)]
        revised+= [r for r in new_domains if r not in old_set and present(r,before)]
        revised=compact(revised)
        if revised and revised!=last:
            last=revised
            added=uncovered_count(now,last)
            removed=uncovered_count(last,now)
    if added or removed:
        return last,{'state':'review','new-matches':added,'missing-rules':removed,**outside}
    return last,{'state':'current',**outside}


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


def verify_file(entry, rows, text, *, refresh=False):
    times=metadata(text)
    try:
        created=datetime.strptime(times['created-at'],'%Y-%m-%dT%H:%M:%SZ')
        updated=datetime.strptime(times['updated-at'],'%Y-%m-%dT%H:%M:%SZ')
    except (ValueError,KeyError) as exc:
        raise rules.Invalid('时间元数据不是 UTC：'+entry['id']) from exc
    expected=decorate(entry,rows,text,times['updated-at'])
    if refresh:
        generated=('# source: ', '# description: ', '# boundary: ', '# section: ')
        def durable(content):
            return [line for line in content.splitlines() if not line.startswith(generated)]
        same=durable(text)==durable(expected)
    else:
        same=text==expected
    if updated<created or not same:
        raise rules.Invalid('规则头部或正文不符合清单：'+entry['id'])


def compile_entry(entry, downloaded):
    """Build membership from declared inputs only; yesterday's output is not a source."""
    included = entry.get('include', [])
    rows = rules.read_rules('\n'.join(included)) if included else []
    if entry.get('ip-match') == 'per-rule':
        if any(row.split(',')[0] in rules.IP_TYPES for row in rows):
            raise rules.Invalid('混合用途的地址只在 DNS 用途清单里填写：'+entry['id'])
        rows.extend(entry.get('dns_required', ()))
        rows.extend(row+',no-resolve' for row in entry.get('literal_ips', ()))
    for part in entry.get('projection', ()):
        found=project_domains(rules.read_rules(downloaded[part['source']]), part)
        if not found:
            raise rules.Invalid('上游没有符合用途的域名：'+entry['id'])
        rows.extend(found)
    for recipe in entry.get('extract', ()):
        found=extract_rows(recipe, downloaded[recipe['source']])
        if not found:
            raise rules.Invalid('来源没有符合用途的端点：'+entry['id']+' '+recipe['source'])
        rows.extend(sorted(found))
    if source:=entry.get('cidr-source'):
        nets=[ip_network(line.strip()) for line in downloaded[source].splitlines() if line.strip()]
        if not nets or any(n.prefixlen<(16 if n.version==4 else 24) or not n.is_global for n in nets):
            raise rules.Invalid('厂商 CIDR 越界：'+entry['id'])
        rows.extend(('IP-CIDR,' if n.version==4 else 'IP-CIDR6,')+str(n)+',no-resolve' for n in nets)
    return compact(rules.read_rules('\n'.join(rows)))


def guard_coverage(name, previous, candidate, *, official_networks=False, excluded_hosts=()):
    waived={'DOMAIN,'+host for host in excluded_hosts}
    previous=[row for row in previous if row not in waived]
    if official_networks:
        # A complete vendor list can retire addresses. Count actual address space,
        # not CIDR lines: splitting one prefix in two is not growth or removal.
        for kind in ('IP-CIDR','IP-CIDR6'):
            def nets(rows):
                return list(collapse_addresses(ip_network(row.split(',')[1])
                            for row in rows if row.startswith(kind+',')))
            old,new=nets(previous),nets(candidate)
            if old==new: continue
            size=sum(n.num_addresses for n in old)
            next_size=sum(n.num_addresses for n in new)
            common=sum(min(a.num_addresses,b.num_addresses) for a in old for b in new if a.overlaps(b))
            if not size or not next_size or 4*max(size-common,next_size-common)>size:
                raise rules.Invalid(f'{name} 的官方 {kind} 地址空间变动超过四分之一')
        previous=[r for r in previous if not r.startswith(('IP-CIDR,','IP-CIDR6,'))]

    # Compare scopes, not net counts: unrelated additions cannot compensate for a lost endpoint.
    if uncovered_count(previous, candidate):
        lost=next(r for r in previous if uncovered_count([r],candidate))
        raise rules.Invalid(f'{name} 的数据源不再覆盖已发布范围：{lost}')


def stable_order(candidate, previous):
    # Membership comes exclusively from the recipe. Keep surviving rows in subscription order.
    remaining=set(candidate)
    known=set(previous)
    return [r for r in previous if r in remaining] + [r for r in candidate if r not in known]


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
        if e['mode'] not in ('compiled','managed','view') or not e['description'] or not e['boundary'] or (e['mode']!='view' and not e.get('sources')):
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
    if not set(config.get('recommended-views',()))<=set(config['views']):
        raise rules.Invalid('推荐合集不在合并视图清单中')
    for e in entries.values():
        if e['mode']=='managed' and (not e.get('kinds') or not e.get('license') or
                                    not set(e.get('feed-sources',()))<=set(e['sources'])):
            raise rules.Invalid('自管来源缺少语法或许可：'+e['id'])
        if 'reserve-domains-for' in e and (e['mode']!='managed' or
                set(e.get('publish-kinds',e.get('kinds',())))-{'DOMAIN','DOMAIN-SUFFIX'} or
                any(k not in entries or entries[k]['mode']!='compiled' or entries[k].get('merge-domains')
                    for k in e['reserve-domains-for'])):
            raise rules.Invalid('域名让位关系必须指向独立生成的专项：'+e['id'])
        if 'exclude-tenant-roots' in e and (e['mode']!='managed' or
                not set(e['exclude-tenant-roots'])<=SHARED_PARENT):
            raise rules.Invalid('租户排除只能用于已知的共享基础设施：'+e['id'])
        if owners:=e.get('confirm-additions-with'):
            if (e['mode']!='managed' or set(e['kinds'])!={'DOMAIN','DOMAIN-SUFFIX'}
                or any(k not in entries or entries[k]['mode']!='compiled' or entries[k].get('merge-domains')
                       or entries[k]['policy-hint'] not in ('ai-cn','domestic') for k in owners)):
                raise rules.Invalid('新增国内域名须有独立国内业务依据：'+e['id'])
        if spec:=e.get('calibration'):
            if (e['mode']!='managed' or not set(calibration_urls(spec))<=set(e['sources'])
                    or not e.get('feed-sources') or ('reconcile' in e)
                    or (spec['method']=='domain-ad-consensus' and (e.get('policy-hint')!='reject' or set(e['kinds'])!={'DOMAIN','DOMAIN-SUFFIX'}))
                    or (spec['method']=='allocation-and-routing' and (e.get('ip-match')!='allow-dns' or set(e['kinds'])!={'IP-CIDR','IP-CIDR6'}))):
                raise rules.Invalid('交叉核对与订阅用途不符：'+e['id'])
        if 'reconcile' in e and (e['reconcile']!='ad-withdrawals' or e['mode']!='managed'
                                   or e.get('policy-hint')!='reject'):
            raise rules.Invalid('自动撤销只适用于订阅广告拦截表：'+e['id'])
        if set(e.get('flags',()))-{'no-resolve'}:
            raise rules.Invalid('来源含未确认的 Loon 参数：'+e['id'])
        if e['mode']=='compiled' and not any(e.get(field) for field in
                ('include','extract','projection','cidr-source','merge-domains','literal_ips','dns_required')):
            raise rules.Invalid('缺少生成来源：'+e['id'])
        for recipe in e.get('extract',()):
            if recipe['source'] not in e['sources']:
                raise rules.Invalid('提取来源未列入文件说明：'+e['id'])
        for part in e.get('projection',()):
            if part['source'] not in e['sources'] or not (part.get('roots') or part.get('exact')):
                raise rules.Invalid('筛选缺少来源或服务边界：'+e['id'])
        if merge:=e.get('merge-domains'):
            if (e['mode']!='compiled' or e['id'] not in names or not merge.get('include')
                or any(key not in entries or entries[key]['mode']!='managed'
                       for key in merge['include']+merge.get('protect',[]))):
                raise rules.Invalid('域名兜底必须使用已审核的输入和例外：'+e['id'])
        if e['mode']=='view':
            if (e['id'] not in config['views'] or not e['members']
                or not set(e['members'])<=set(names)
                or any(e['priority']>=entries[k]['priority'] or e['section']!=entries[k]['section']
                       for k in e['members'])):
                raise rules.Invalid('合并视图包含未归类成员：'+e['id'])
    for key in config['views']:
        view=entries[key]
        entries[key]=dict(view,sources=list(dict.fromkeys(
            url for member in view['members'] for url in entries[member]['sources'])))
    for section in config['sections']:
        if any(k not in set(config['alternatives']+config['optional']) or entries[k]['section']!=section['id']
               for k in section.get('selectable',())):
            raise rules.Invalid('独立选项与分区不符：'+section['id'])
        for ref in section.get('related',()):
            if ref['id'] not in entries or entries[ref['id']]['section']==section['id'] or not ref['note']:
                raise rules.Invalid('跨区引用无效：'+ref['id'])
    members=[k for view in config['views'] for k in entries[view]['members']]
    if len(members)!=len(set(members)):
        raise rules.Invalid('合集之间含相同成员')
    for spec in config.get('source-inventories',[]):
        owners=set(spec['owners'])|set(spec.get('other-owners',{}).values())
        if not spec['owners'] or not owners<=set(entries) or not any(
                spec['source'] in e['sources'] for e in entries.values()):
            raise rules.Invalid('来源核对缺少归属或出处：'+spec['id'])
    return entries


def audit_inventory(spec, downloaded, data):
    """Look outside the publishing filters for unassigned domain scopes. Never export candidates."""
    if spec['source'] not in downloaded: return {'state':'unavailable'}
    try:
        rows=rules.read_rules(downloaded[spec['source']])
    except rules.Invalid:
        return {'state':'invalid'}
    domains=[r for r in rows if r.startswith(('DOMAIN,','DOMAIN-SUFFIX,')) and r.count(',')==1]
    owned=[r for owner in spec['owners'] for r in data[owner]]
    reviewed=set(spec.get('shared',{}))
    other=0
    for row in domains:
        if row in reviewed: continue
        if other_owner:=spec.get('other-owners',{}).get(row):
            if not any(covers(r,row) for r in data[other_owner]): other+=1
            continue
        kind,host=row.split(',')
        if kind=='DOMAIN':
            known=any(rules.match_domain(host.casefold(),target) for target in owned)
        else: known=any(covers(target,row) for target in owned)
        if not known: other+=1
    return {'state':'review' if other else 'current','domain-scopes':len(domains),
            'outside-scope':other,'other-rules':len(rows)-len(domains)}


def maintenance_method(entry):
    if entry['mode']=='view' or entry.get('merge-domains'):
        return '组合生成'
    if entry.get('confirm-additions-with'):return '新增域名与国内业务表交叉核对'
    if spec:=entry.get('calibration'):
        return '整域拦截交叉核对' if spec['method']=='domain-ad-consensus' else '分配与路由交叉核对'
    if entry['mode']=='managed':
        return '随来源缩小拦截' if entry.get('reconcile')=='ad-withdrawals' else '比较上游，保留已审范围'
    if any(entry.get(k) for k in ('extract','projection','cidr-source')):
        return '按来源筛选'
    return '已核清单'


def render_review(status,entries):
    states=status['reviewed-inputs']
    lines=['# 最近一次来源检查','',
           f"检查时间：{status['checked-at']}（UTC）。成功读取 {status['inputs-read']} / {status['inputs-requested']} 个来源。",
           '', '## 需要处理','',
           '新增、撤回指上游与订阅范围的差异，数字是规则条数，不是设备请求数。这里的差异尚未改动订阅。','']
    ordered=sorted(states,key=lambda k:entries[k]['priority'])
    labels={'unavailable':'来源无法读取','invalid':'格式或参数不符合预期','review':'范围有变化'}
    pending=[k for k in ordered if states[k]['state']!='current']
    for k in pending:
        e=entries[k]; state=states[k]; filename=rule_filename(e)
        counts=(f"：新增 {state['new-matches']}，撤回 {state['missing-rules']}"
                if state['state']=='review' else '')
        lines.append(f"- [{e['priority']:03d} {e['description']}](rules/{filename})："
                     +labels[state['state']]+counts)
    inventories={k:v for k,v in status['source-inventories'].items() if v['state']!='current'}
    for k,v in inventories.items():
        lines.append(f"- 来源覆盖核对 {k}："+labels[v['state']]+
                     (f"：{v['outside-scope']} 条未归类" if 'outside-scope' in v else ''))
    if not (pending or inventories): lines.append('本次没有需要处理的差异。')
    checked=[k for k in ordered if 'unconfirmed-prefixes' in states[k] or 'not-whole-host-consensus' in states[k] or 'unconfirmed-domains' in states[k]]
    if checked:
        lines+=['','## 已校准的范围','']
        for k in checked:
            v=states[k]; tag=f"{entries[k]['priority']:03d}"
            if 'unconfirmed-domains' in v:
                lines.append(f"- {tag}：{v['unconfirmed-domains']} 条新增范围没有独立的国内业务依据，不纳入订阅。")
            elif 'unconfirmed-prefixes' in v:
                lines.append(f"- {tag}：新增 {v['accepted-prefixes']} 个已核网段，撤回 {v['retired-prefixes']} 个；缺少分配或路由依据的 {v['unconfirmed-prefixes']} 个没有加入。")
            else:
                lines.append(f"- {tag}：新增 {v['admitted-rules']} 条，撤回 {v['retired-rules']} 条；源表有 {v['not-whole-host-consensus']} 条不符合整域交叉核对条件。")
    outside=[k for k in ordered if states[k].get('outside-purpose') or states[k].get('reserved-scopes')]
    if outside:
        lines+=['','## 范围外，不进通用表','',
                '共享 CDN 和云平台可托管不同产品。租户主机不作为地区或通用业务的证据。国内表还要让出国际版 AI 的域名，包括会吞掉这些域名的父后缀。','']
        for k in outside:
            reason='、'.join(f'{v} 条{label}' for field,label in [('outside-purpose','共享托管主机'),('reserved-scopes','与国际版 AI 重叠')] if (v:=states[k].get(field)))
            lines.append(f"- {entries[k]['priority']:03d}：{reason}")
    if conflicts:=status.get('fallback-conflicts'):
        lines+=['','## 海外和国内来源意见不一致','',
                '这些域名没有并入海外兜底。它们仍可能命中服务专项或国内规则；两个来源意见不合，不代表其中一方一定正确。同一范围可能出现在多份输入，不能把条数相加当成网站数。','']
        for dest,counts in conflicts.items():
            lines.append(f"- {entries[dest]['priority']:03d}："+'；'.join(
                f"{entries[k]['priority']:03d} 有 {v} 条相交" for k,v in counts.items()))
    return '\n'.join(lines)+'\n'


def render_index(config, entries):
    roles={k:'备选' for k in config['alternatives']}|{k:'可选' for k in config['optional']}
    recommended=set(config.get('recommended-views',()))
    split={member for key in recommended for member in entries[key]['members']}
    def table(items):
        rows=['| 编号 · 规则 | 用途 | 选择方式 | 范围 |','|---|---|---|---|']
        for e in items:
            key=e['id']
            role=('推荐合用' if key in recommended else '分开订阅' if key in split
                  else roles.get(key,'替换成员' if e['mode']=='view' else '常规'))
            name=rule_filename(e)
            rows.append(f'| [{name[:-4]}](rules/{name}) | {e["description"]} | {role} · {maintenance_method(e)} | {e["boundary"]} |')
        return rows

    lines=['# 规则订阅清单','',
           '按用途选规则。同一来源和匹配阶段内按编号排；选合集就不用再订阅它的成员。'
           '备选与可选项按表里的使用条件启用，不默认叠加。',
           '', '打开规则后点 **Raw** 复制订阅地址。来源和更新时间在文件开头；[最近的检查](REVIEW.md)只列实际差异和未能读取的来源。']
    ordered=sorted(entries.values(),key=lambda e:e['priority'])
    for section in config['sections']:
        group=[e for e in ordered if e['section']==section['id']]
        lines += ['',f'## {section["from"]:03d}–{section["through"]:03d} {section["title"]}','']
        if section.get('compact-index'):
            lines+=table(e for e in group if e['id'] not in roles and e['id'] not in split)
            for title,keys in (('需要分开控制时：选合集成员',split),
                               ('有明确需要时再选',set(section.get('selectable',())))):
                items=[e for e in group if e['id'] in keys]
                if items:
                    lines+=['','<details>',f'<summary>{title}</summary>','',*table(items),'','</details>']
            lines+=['','其余输入和兼容订阅不在日常清单里。[逐份看用途和文件](COVERAGE.md#哪些整表不该默认打开)']
        else:
            lines+=table(group)
        for e in group:
            if e['mode']=='view':
                numbers='、'.join(f'{entries[k]["priority"]:03d}' for k in sorted(e['members'],key=lambda k:entries[k]['priority']))
                lines += ['',f'**{e["priority"]:03d} 与 {numbers} 二选一。**']
        if section.get('related'):
            lines+=['','**相关专项（沿用同一份规则）：**']
            for ref in section['related']:
                e=entries[ref['id']]
                name=rule_filename(e)
                lines.append(f'- [{name[:-4]}](rules/{name})：{ref["note"]}')
    return '\n'.join(lines)+'\n'


_scope_policy=json.loads((ROOT/'scope-policy.json').read_text())
SHARED_PARENT=frozenset(_scope_policy['shared-suffixes'])
PROTECTED_NETWORKS=tuple(map(ip_network,_scope_policy['protected-networks']))


def overbroad(kind, value, allowed):
    value=value.casefold()
    if kind=='DOMAIN-SUFFIX':
        return (value in SHARED_PARENT or '.' not in value) and value not in allowed
    if kind=='DOMAIN-WILDCARD':
        # A subdomain glob does not include the apex but still claims every tenant.
        base=value.removeprefix('*.')
        if (base in SHARED_PARENT or '.' not in base) and base not in allowed: return True
        return any(rules.match_domain('scope-probe.'+root,kind+','+value)
                   for root in SHARED_PARENT if root not in allowed)
    if kind in ('IP-CIDR','IP-CIDR6'):
        net=ip_network(value,strict=False)
        return any(n.version==net.version and n.subnet_of(net) for n in PROTECTED_NETWORKS)
    return False


def lint_content(name, rows, allowed_shared=()):
    for r in rows:
        t,p,*_=r.split(',')
        if overbroad(t,p,allowed_shared):
            raise rules.Invalid('规则覆盖整个共享服务或受保护的地址段：'+name+' '+r)
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
        for key,e in entries.items():
            functional=protected_hosts(e,config,entries,contracts)
            if functional and without_protected(data[key],functional)!=data[key]:
                raise rules.Invalid(f'{key} 单独订阅会拦截业务端点')
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


def domain_rows(data,keys):
    return {row.split(',',1)[0]+','+row.split(',')[1].casefold()
            for key in keys for row in data[key]
            if row.startswith(('DOMAIN,','DOMAIN-SUFFIX,')) and row.count(',')==1}


def merge_domain_sources(entry, data):
    """Combine reviewed domain rows without claiming a protected scope."""
    scope=entry['merge-domains']
    protected=domain_rows(data,scope.get('protect',()))
    combined=domain_rows(data,scope['include'])-set(entry.get('excluded-rules',()))
    return compact(outside_domain_scopes(sorted(combined),protected))


def merge_conflicts(entries,data):
    report={}
    for k,e in entries.items():
        scope=e.get('merge-domains',{})
        if not scope.get('protect'): continue
        reserved=domain_rows(data,scope['protect'])
        counts={}
        for source in scope['include']:
            rows=domain_rows(data,[source])
            counts[source]=len(rows)-len(outside_domain_scopes(rows,reserved))
        report[k]=counts
    return report


def derive_domain_merges(config, entries, data):
    """Subtract complete matches already handled by a preceding routine subscription."""
    order=route_order(config,entries)
    outputs={}
    effective=dict(data)
    for i,key in enumerate(order):
        if not (scope:=entries[key].get('merge-domains')):
            continue
        effective[key]=merge_domain_sources(entries[key],effective)
        if scope.get('subtract-prior'):
            covered={row for owner,row,_,_ in shadowed_domains(order[:i+1],effective) if owner==key}
            effective[key]=[row for row in effective[key] if row not in covered]
        if not effective[key]:
            raise rules.Invalid('合并后没有剩余域名：'+key)
        outputs[key]=effective[key]
    return outputs


def new_outputs(paths, entries, present, known, *, refresh):
    missing={k for k,path in paths.items() if path not in present}
    if present-set(paths.values()) or (missing and (not refresh or missing & known
                                          or any(entries[k]['mode']=='managed' for k in missing))):
        raise rules.Invalid('规则文件与清单不一致；缺失的已发布订阅不能重新初始化')
    return missing


def run(check=False, offline=False, adopt_ads=False):
    config=json.loads((ROOT/'catalog.json').read_text())
    contracts=json.loads((ROOT/'endpoint-contracts.json').read_text())
    entries=validate_declarations(config)
    file_entries=entries
    paths={k:ROOT/'rules'/rule_filename(e) for k,e in file_entries.items()}
    present=set((ROOT/'rules').glob('*.lsr'))
    known=set()
    if not offline and set(paths.values())-present:
        known=set(json.loads((ROOT/'status.json').read_text())['rules'])
    missing=new_outputs(paths,entries,present,known,refresh=not offline)
    if (ROOT/'INDEX.md').read_text()!=render_index(config,entries):
        raise rules.Invalid('编号索引未更新（maintain.py --render-index）')
    old={k:(None if k in missing else p.read_text()) for k,p in paths.items()}
    data={k:([] if t is None else rules.read_rules(t)) for k,t in old.items()}
    for k,rows in data.items():
        if k in missing: continue
        lint_content(k,rows,entries[k].get('allowed-shared',()))
        verify_file(entries[k],rows,old[k],refresh=not offline)
        rules.verify_ip_options(entries[k],rules.ip_options(rows),complete=True)
    if offline:
        report=json.loads((ROOT/'status.json').read_text())
        if (ROOT/'REVIEW.md').read_text()!=render_review(report,entries):
            raise rules.Invalid('来源检查报告与 status.json 不一致')
        for k,e in entries.items():
            if e['mode']=='compiled' and not any(e.get(x) for x in ('projection','extract','cidr-source','merge-domains')):
                if set(data[k]) != set(compile_entry(e, {})):
                    raise rules.Invalid('正文与已审清单不一致：'+k)
        for key,rows in derive_domain_merges(config,entries,data).items():
            if data[key]!=rows:
                raise rules.Invalid('域名兜底与已审来源或前置专项不一致：'+key)
        for key in config['views']:
            if data[key]!=merge_view(entries[key],data):
                raise rules.Invalid('合集与专项不一致：'+key)
        verify_cases(config,entries,data,True,contracts)
        print(f'{len(file_entries)} 份本地规则的范围、元数据和合并模式通过离线检查。')
        return 0

    reviewed={k:e for k,e in entries.items() if e['mode']=='managed'}
    watched={u for e in reviewed.values() for u in e.get('feed-sources',e['sources'])}
    watched.update(u for e in reviewed.values() for u in calibration_urls(e.get('calibration')))
    watched.update(spec['source'] for spec in config.get('source-inventories',()))
    urls={contract['source'] for contract in contracts}
    for e in file_entries.values():
        urls.update(s['source'] for field in ('extract','projection') for s in e.get(field,()))
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
    contracts=endpoint_contracts.resolve_additions(contracts,entries,downloaded)
    contract_status=endpoint_contracts.verify_sources(contracts,downloaded)
    source_status={}
    for k,e in file_entries.items():
        if e['mode']!='compiled' or e.get('merge-domains'):
            continue
        previous=data[k]
        candidate=compile_entry(e, downloaded)
        if any(e.get(x) for x in ('projection','extract','cidr-source')):
            guard_coverage(k, previous, candidate,
                excluded_hosts=[host for host,owners in config.get('scope-negatives',{}).items() if k in owners],
                official_networks=bool(e.get('cidr-source')
                or any(r['format']=='labelled-networks' for r in e.get('extract',()))))
        data[k]=stable_order(candidate,previous)
        lint_content(k,data[k],e.get('allowed-shared',()))
        rules.verify_ip_options(e,rules.ip_options(data[k]),complete=True)
    for k,e in reviewed.items():
        reserved=[row for owner in e.get('reserve-domains-for',()) for row in data[owner]]
        data[k],source_status[k]=refresh_reviewed_feed(e,data[k],downloaded,
            protected=protected_hosts(e,config,entries,contracts),reserved=reserved,adopt_ads=adopt_ads,
            corroborated=domain_rows(data,e.get('confirm-additions-with',())))
    for key,rows in derive_domain_merges(config,entries,data).items():
        data[key]=rows
        lint_content(key,rows,entries[key].get('allowed-shared',()))
        rules.verify_ip_options(entries[key],rules.ip_options(rows),complete=True)
    for key in config['views']:
        e=entries[key]
        data[key]=merge_view(e,data)
        lint_content(key,data[key],e.get('allowed-shared',()))
        rules.verify_ip_options(e,rules.ip_options(data[key]),complete=True)
    verify_cases(config,entries,data,True,contracts)
    now=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    inventories={spec['id']:audit_inventory(spec,downloaded,data) for spec in config.get('source-inventories',())}
    changed=[]
    methods={}
    for k,e in entries.items():
        methods.setdefault(maintenance_method(e),[]).append(e['priority'])
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
        report={
            'checked-at':now,'inputs-read':len(downloaded),'critical':len(config['critical']),
            'inputs-requested':len(requested),'maintenance':methods,'reviewed-inputs':source_status,
            'official-endpoints':contract_status,'source-inventories':inventories,
            'fallback-conflicts':merge_conflicts(entries,data),
            'shared-negatives':len(config['shared-negatives']), 'changed':changed,
            'scope-negatives':len(config.get('scope-negatives',{})),
            'ip-cases':len(config.get('ip-cases',())),
            'rules':{k:len(data[k]) for k in sorted(data,key=lambda k:entries[k]['priority'])},
        }
        (ROOT/'status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        (ROOT/'REVIEW.md').write_text(render_review(report,entries))
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
    p.add_argument('--adopt-ad-scope',action='store_true',help='显式采纳扩展广告筛选范围的一次性大变更，不适用于定时任务')
    args=p.parse_args()
    if args.adopt_ad_scope and not args.refresh: p.error('采纳范围变更须与 --refresh 同用')
    try:
        if args.render_index:
            config=json.loads((ROOT/'catalog.json').read_text())
            (ROOT/'INDEX.md').write_text(render_index(config,validate_declarations(config)))
            return 0
        # 默认只验证，显式 --refresh 才修改规则。
        return run(check=args.check,adopt_ads=args.adopt_ad_scope,offline=args.verify_files or not (args.check or args.refresh))
    except (rules.Invalid,OSError,ValueError,KeyError) as error:
        print('保留上一版本：'+str(error),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
