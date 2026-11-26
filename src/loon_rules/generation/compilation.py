"""Compile declared sources and guard published coverage."""
from ipaddress import collapse_addresses, ip_network
from loon_rules import rules
from loon_rules import domains as domain_scope
from loon_rules.sources import aliases as source_aliases
from loon_rules.sources.aliases import alias_patterns, cname_tenant
from loon_rules.domains import covers
from loon_rules.policy import SLUG
from loon_rules.generation.membership import compact,project_domains,uncovered_count
from loon_rules.generation.ordering import ordered_route,route_order
from loon_rules.generation.protection import extract_rows



def compile_entry(entry, downloaded, *, shared_scopes=(), reserved_rows=(), extra_rows=(),shared_hosts=(),projection_rows=None,resource_rows=None):
    """Build membership from declared inputs only; yesterday's output is not a source."""
    included = entry.get('include', [])
    rows = list(extra_rows)
    rows.extend(rules.read_rules('\n'.join(included)) if included else [])
    if entry.get('ip-match') == 'per-rule':
        if any(row.split(',')[0] in rules.IP_TYPES for row in rows):
            raise rules.Invalid('混合用途的地址只在 DNS 用途清单里填写：'+entry['id'])
        rows.extend(entry.get('dns_required', ()))
        rows.extend(row+',no-resolve' for row in entry.get('literal_ips', ()))
    rows.extend(rules.reverse_dns_rules(entry))
    extracted = []
    for recipe in entry.get('extract', ()):
        found = extract_rows(recipe, downloaded[recipe['source']], shared_hosts=shared_hosts)
        if not found:
            raise rules.Invalid('来源没有符合用途的端点：'+entry['id']+' '+recipe['source'])
        if recipe.get('respect-existing-owners'):
            if resource_rows is None:
                raise rules.Invalid('网页图片需要完整产品范围才能核对已有归属')
            resource_rows.setdefault(entry['id'], set()).update(found)
        else:
            extracted.extend(sorted(found))
    if any(part.get('exact-from-extract') for part in entry.get('projection', ())):
        extracted = domain_scope.exclude_shared_scopes(extracted, shared_hosts)
    for part in entry.get('projection', ()):
        source=downloaded[part['source']]
        if part.get('domain-lines-only'):
            lines=(line.strip().lstrip('\ufeff').strip() for line in source.splitlines())
            source='\n'.join(line for line in lines if line.partition(',')[0].strip() in ('DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD'))
        scope=dict(part)
        if part.get('exact-from-extract'):
            hosts = {row.split(',')[1] for row in extracted
                     if row.startswith('DOMAIN,') and row.count(',') == 1}
            if not hosts:
                raise rules.Invalid('来源精确主机筛选缺少本轮用途字段：'+entry['id'])
            scope['exact'] = sorted(set(scope.get('exact', ())) | hosts)
        if parent_source:=part.get('parent-domains-source'):
            parents={h.strip().removeprefix('.') for h in downloaded[parent_source].splitlines() if h.strip()}
            brand=part['brand-label'];label=part['prefix-label']
            if (not parents or not SLUG.fullmatch(brand) or not SLUG.fullmatch(label)
                    or any(not rules.valid_host(h) or h.split('.')[0]!=brand for h in parents)):
                raise rules.Invalid('官方域名清单含未确认的品牌或格式：'+entry['id'])
            scope['roots']=[*part.get('roots',()),*(label+'.'+h for h in sorted(parents))]
        found=project_domains(rules.read_rules(source), scope)
        if not found:
            raise rules.Invalid('上游没有符合用途的域名：'+entry['id'])
        if projection_rows is not None:projection_rows.setdefault(part['source'],set()).update(found)
        rows.extend(found)
    rows.extend(extracted)
    if source:=entry.get('cidr-source'):
        nets=[ip_network(line.strip()) for line in downloaded[source].splitlines() if line.strip()]
        if not nets or any(n.prefixlen<(16 if n.version==4 else 24) or not n.is_global for n in nets):
            raise rules.Invalid('厂商 CIDR 越界：'+entry['id'])
        rows.extend(('IP-CIDR,' if n.version==4 else 'IP-CIDR6,')+str(n)+',no-resolve' for n in nets)
    rows=domain_scope.exclude_shared_scopes(rows,shared_scopes)
    rows=[row for row in rows if not any(covers(other,row) for other in reserved_rows)]
    if not rows and resource_rows and entry['id'] in resource_rows:
        return []  # Ownership is resolved after all products have compiled.
    return compact(rules.read_rules('\n'.join(rows)))


def apply_source_aliases(config,entries,data,downloaded,*,dns_records=None,dns_evidence=None):
    """Assign source-listed service aliases to the owner of their canonical host."""
    order=route_order(config,entries);base={k:list(v) for k,v in data.items()}
    report={};claimed={}
    for key,e in entries.items():
        if not (spec:=e.get('aliases')):continue
        policy=config['source-alias-policies'][spec['policy']]
        patterns=[];canonical=set()
        for row in base[key]:
            kind,host,*flags=row.split(',')
            if flags or kind not in ('DOMAIN','DOMAIN-SUFFIX') or ordered_route(host,order,base)!=key:continue
            canonical.add(host)
            patterns.extend(alias_patterns(host,policy))
        found=[]
        tenants={name for host in canonical for name in (dns_records or {}).get(host,())
                 if cname_tenant(host,name,policy)}
        sources=[rules.read_rules(downloaded[url]) for url in spec['sources']]
        sources.append(['DOMAIN,'+name for host in canonical for name in (dns_records or {}).get(host,())])
        for source in sources:
            for row in source:
                kind,host,*flags=row.split(',')
                if flags or kind not in ('DOMAIN','DOMAIN-SUFFIX'):continue
                if (host not in canonical and not any(p.fullmatch(host) for p in patterns)
                        and not (kind=='DOMAIN' and host in tenants)):continue
                if host in claimed and claimed[host]!=key:
                    raise rules.Invalid('来源别名对应多个业务：'+host)
                claimed[host]=key
                if not any(covers(r,row) for r in base[key]):found.append(row)
        if found:
            report[key]=compact(found)
            data[key]=compact(data[key]+found)
        if dns_evidence is not None and spec.get('resolve-cname'):
            witnesses={}
            for host in sorted(canonical):
                for alias in (dns_records or {}).get(host,()):
                    row='DOMAIN,'+alias
                    if (any(covers(actual,row) for actual in data[key])
                            and source_aliases.permits(host,alias,policy)):
                        witnesses.setdefault(row,[]).append(host)
            if witnesses:dns_evidence[key]={row:{'canonical-hosts':sorted(set(names)),'state':'current'}
                                           for row,names in witnesses.items()}
    return report


def shared_service_transfers(entries,previous,data,downloaded,order):
    """Release a service scope only when the source proves sharing and another table covers it."""
    transfers={}
    for key,entry in entries.items():
        recipes=[dict(recipe,part='shared') for recipe in entry.get('extract',()) if recipe.get('check-sharing')]
        if not recipes:continue
        shared=set().union(*(extract_rows(recipe,downloaded[recipe['source']]) for recipe in recipes))
        owners={}
        for row in sorted(shared):
            if any(covers(actual,row) for actual in data[key]):
                raise rules.Invalid('共享用途仍被产品专表认领：'+key+' '+row)
            owner=next((other for other in order if other!=key
                        and entries[other].get('policy-hint')!='reject'
                        and any(covers(actual,row) for actual in data[other])),None)
            if owner is None and any(covers(row,old) for old in previous.get(key,())):
                raise rules.Invalid('共享用途撤出产品表后没有可确认的归属：'+key+' '+row)
            owners[row]=owner
        transfers[key]=owners
    return transfers


def verify_shared_service_transfers(entries,data,transfers):
    expected={key for key,entry in entries.items() if any(
        recipe.get('check-sharing') for recipe in entry.get('extract',()))}
    if set(transfers)!=expected:
        raise rules.Invalid('共享用途报告与来源声明不一致')
    for key,rows in transfers.items():
        for row,owner in rows.items():
            if any(covers(actual,row) for actual in data[key]):
                raise rules.Invalid('共享用途报告仍由产品专表覆盖：'+key)
            if owner is not None and (owner not in entries or owner==key
                    or entries[owner].get('policy-hint')=='reject'
                    or not any(covers(actual,row) for actual in data[owner])):
                raise rules.Invalid('共享用途报告的目标归属未覆盖正文：'+key)


def guard_coverage(name, previous, candidate, *, official_networks=False, official_autnums=False, excluded_hosts=(), reassigned=()):
    waived={'DOMAIN,'+host for host in excluded_hosts}
    previous=[row for row in previous if row not in waived
              and not any(covers(target,row) for target in reassigned)]
    if official_autnums:
        if not any(row.startswith('IP-ASN,') for row in candidate):
            raise rules.Invalid(name+' 的注册组织没有可用 ASN，保留上一版')
        previous=[row for row in previous if not row.startswith('IP-ASN,')]
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
            if not size:
                continue
            if not next_size or 4*max(size-common,next_size-common)>size:
                raise rules.Invalid(f'{name} 的官方 {kind} 地址空间变动超过四分之一')
        previous=[r for r in previous if not r.startswith(('IP-CIDR,','IP-CIDR6,'))]

    # Compare scopes, not net counts: unrelated additions cannot compensate for a lost endpoint.
    if uncovered_count(previous, candidate):
        lost=next(r for r in previous if uncovered_count([r],candidate))
        raise rules.Invalid(f'{name} 的数据源不再覆盖已发布范围：{lost}')
