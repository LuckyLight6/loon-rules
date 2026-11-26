"""Domain scope selection, compaction and set operations."""
import re
from loon_rules import rules
from loon_rules import domains as domain_scope
from loon_rules.domains import covers



def project_domains(rows, scope):
    """Use documented product roots and exact aliases, not shared vendors."""
    if 'all-domains' in scope and type(scope['all-domains']) is not bool:
        raise rules.Invalid('完整域名来源开关必须为布尔值')
    if scope.get('all-domains') and any(scope.get(field) for field in ('roots', 'exact')):
        raise rules.Invalid('完整域名来源不能同时填写部分域名筛选')
    def within(host, roots):
        return any(host==root or host.endswith('.'+root) for root in roots)

    kept=[]
    for row in rows:
        kind,host,*flags=row.split(',')
        if flags or kind not in ('DOMAIN','DOMAIN-SUFFIX') and not (
                scope.get('all-domains') and kind=='DOMAIN-WILDCARD'):
            continue
        host=host.casefold()
        if within(host,scope.get('exclude',())):
            continue
        if scope.get('all-domains') or within(host,scope.get('roots',())):
            kept.append(kind+','+host)
        elif host in scope.get('exact',()):
            # Shared services may be selected by exact hostname only.
            kept.append('DOMAIN,'+host)
    return kept


def compact(rows):
    rows=list(dict.fromkeys(rows))
    suffixes={r.split(',')[1] for r in rows if r.startswith('DOMAIN-SUFFIX,') and r.count(',')==1}
    wild={r.removeprefix('DOMAIN-WILDCARD,*.') for r in rows if r.startswith('DOMAIN-WILDCARD,*.')
          and not re.search(r'[?*\[\],]',r.split('*.')[1]) and r.count('*')==1}
    kept=[]
    for r in rows:
        k,p,*f=r.split(',')
        if k=='DOMAIN-WILDCARD' and not f:
            tail=domain_scope.fixed_tail(p)
            if any('.'.join(tail.split('.')[i:]) in suffixes for i in range(len(tail.split('.')))):
                continue
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
            if any('.'.join(labels[i:]) in wild for i in range(1,len(labels))):
                continue
        kept.append(r)
    return kept


def outside_tenant_scopes(rows,roots,official=()):
    if not roots:return rows
    roots={r.casefold() for r in roots};official={h.casefold() for h in official}
    def keep(row):
        kind,host,*_=row.split(',');host=host.casefold()
        if kind=='DOMAIN' and host in official:return True
        if kind in ('DOMAIN','DOMAIN-SUFFIX'):
            return not any(host==r or host.endswith('.'+r) or
                           (kind=='DOMAIN-SUFFIX' and r.endswith('.'+host)) for r in roots)
        if kind in ('DOMAIN-WILDCARD','DOMAIN-KEYWORD'):
            return not any(host.endswith('.'+r) or rules.match_domain(r,row)
                           or rules.match_domain('tenant.'+r,row) for r in roots)
        return True
    return [r for r in rows if keep(r)]


def uncovered_count(rows, baseline):
    existing=set(baseline)
    suffixes={r.split(',')[1] for r in existing if r.startswith('DOMAIN-SUFFIX,') and r.count(',')==1}
    wildcards=[r for r in existing if r.startswith('DOMAIN-WILDCARD,') and r.count(',')==1]
    count=0
    for row in rows:
        if row in existing:
            continue
        kind,value,*flags=row.split(',')
        if kind in ('DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD') and not flags:
            parts=(domain_scope.fixed_tail(value) if kind=='DOMAIN-WILDCARD' else value).split('.')
            if any('.'.join(parts[i:]) in suffixes for i in range(len(parts))):
                continue
            if any(covers(parent,row) for parent in wildcards):continue
            if (kind=='DOMAIN-SUFFIX' and 'DOMAIN,'+value in existing
                    and any(covers(parent,'DOMAIN-WILDCARD,*.'+value) for parent in wildcards)):continue
        count+=1
    return count


def overlapping_rules(left,right):
    """Find identical or fully contained domain scopes in either direction."""
    def normalized(rows):
        for row in rows:
            kind,sep,value=row.partition(',')
            yield kind+sep+value.casefold() if kind in ('DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD') else row
    a,b=list(normalized(left)),list(normalized(right))
    return uncovered_count(a,b)<len(a) or uncovered_count(b,a)<len(b)


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
    exact=set(); suffix=set(); ancestors=set(); wild=set(); patterns=[]
    for row in reserved:
        kind,host,*flags=row.casefold().split(',')
        if not flags and kind=='domain-wildcard' and host.startswith('*.') and not re.search(r'[*?\[\]]',host[2:]):
            wild.add(host[2:]);ancestors.update(lineage(host[2:]));continue
        if not flags and kind=='domain-wildcard':
            bounded=re.fullmatch(r'([a-z0-9][a-z0-9-]*)\*([a-z0-9-]*)\.([a-z0-9.-]+)',host)
            if bounded:
                tail=bounded[3];patterns.append((row,tail,bounded[2]))
                ancestors.update(lineage(tail));continue
        if flags or kind not in ('domain','domain-suffix'):
            raise rules.Invalid('预留范围只能使用域名、后缀、子域或有限租户前缀通配符')
        exact.add(host); ancestors.update(lineage(host))
        if kind=='domain-suffix': suffix.add(host)
    def keep(row):
        kind,host,*flags=row.casefold().split(',')
        if flags or kind not in ('domain','domain-suffix'):
            raise rules.Invalid('域名隔离不能用于混合匹配规则')
        if any(rules.match_domain(host,pattern) or kind=='domain-suffix' and host.endswith('.'+tail)
               and (not ending or host.endswith(ending+'.'+tail)) for pattern,tail,ending in patterns):
            return False
        return host not in exact and not any(p in suffix for p in lineage(host)) and not any(
            p in wild for p in list(lineage(host))[1:]) and not (
            kind=='domain-suffix' and host in ancestors)
    return [r for r in rows if keep(r)]


def stable_order(candidate, previous):
    # Membership comes exclusively from the recipe. Keep surviving rows in subscription order.
    remaining=set(candidate)
    known=set(previous)
    return [r for r in previous if r in remaining] + [r for r in candidate if r not in known]


def product_rows(e,data):
    part=e['refine']
    if part.get('literal-ip-copy'):
        return [row+',no-resolve' if row.split(',')[0] in rules.IP_TYPES and 'no-resolve' not in row.split(',')[2:] else row for row in data[part['from']]]
    rows=compact(project_domains(data[part['from']],part))
    if not rows:raise rules.Invalid('来源已无该产品的域名：'+e['id'])
    return rows


def merge_view(entry, data):
    excluded=set(entry.get('exclude',[]))
    return compact([row for member in entry['members'] for row in data[member] if row not in excluded]
                   +list(entry.get('_dependency-scopes',())))


def domain_rows(data,keys):
    return {row.split(',',1)[0]+','+row.split(',')[1].casefold()
            for key in keys for row in data[key]
            if row.startswith(('DOMAIN,','DOMAIN-SUFFIX,')) and row.count(',')==1}


def merge_domain_sources(entry, data):
    """Combine reviewed inputs, applying declared source precedence before compaction."""
    scope=entry['merge-domains']
    protected=domain_rows(data,scope.get('protect',()))
    excluded=set(entry.get('excluded-rules',()))
    preferred=domain_rows(data,scope.get('prefer',()))-excluded
    ordinary=domain_rows(data,scope['include'])-preferred-excluded
    kept=set(outside_domain_scopes(sorted(ordinary),protected))|preferred
    return compact(sorted(kept))


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
