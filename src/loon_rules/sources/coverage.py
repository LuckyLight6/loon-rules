"""Audit every active product projection without publishing unselected source names."""
from collections import defaultdict

from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid, read_rules, TYPES
from loon_rules.matching import RuleIndex


DOMAIN_TYPES=('DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD')
COUNTS=('domain-scopes','selected-scopes','narrowed-scopes','selected-uncovered',
        'product-scopes','fallback-scopes','privacy-scopes','shared-scopes',
        'declared-exclusions','outside-selection','other-lines')
PROJECTION_FIELDS=('roots','exact','exclude','all-domains','domain-lines-only','parent-domains-source',
                   'brand-label','prefix-label','require-domain-closure','exact-from-extract')
OTHER_TYPES=(TYPES-set(DOMAIN_TYPES))|{'domain-options','unsupported'}
FIELDS={'state','products','filters','other-products','other-rule-types',*COUNTS}


def same_business_family(first, second):
    return (first.get('section')==second.get('section')
            or bool(first.get('vendor')) and first['vendor']==second.get('vendor'))


def groups(entries,order=None):
    active=set(entries if order is None else order);result=defaultdict(list)
    for key in sorted(active,key=lambda key:entries[key]['priority']):
        for source in dict.fromkeys(part['source'] for part in entries[key].get('projection',())):
            result[source].append(key)
    return dict(result)


def filters(entries,source,products):
    return {key:[{field:part[field] for field in PROJECTION_FIELDS if field in part}
                 for part in entries[key].get('projection',()) if part['source']==source] for key in products}


def declared_exclusions(config):
    result=defaultdict(set)
    for spec in config.get('source-inventories',()):
        result[spec['source']].update(spec.get('shared',{}))
        result[spec['source']].update(spec.get('reviewed-outside',{}))
    return dict(result)


def inventory_owners(specs, entries):
    """Use independently declared source purposes, including fine members of bundles."""
    result = defaultdict(set)
    for spec in specs:
        owners = set(spec['owners']) | set(spec.get('other-owners', {}).values())
        for owner in tuple(owners):
            owners.update(entries[owner].get('members', ()))
        result[spec['source']].update(owners)
    return dict(result)


def shared_scope(row,parents,hosts):
    kind,value=row.split(',');tail=domain_scope.fixed_tail(value)
    suffix,private=domain_scope.current().suffix(tail)
    if tail in parents or tail==suffix:return True
    if private and kind!='DOMAIN':return True
    return any(domain_scope.covers(row,('DOMAIN-WILDCARD,' if '*' in host else 'DOMAIN,')+host) for host in hosts)


def domain_lines(text):
    normalized=(line.strip().lstrip('\ufeff').strip() for line in text.splitlines())
    lines=[line for line in normalized if line and not line.startswith(('#',';','//'))]
    source=[line for line in lines if line.partition(',')[0].strip() in DOMAIN_TYPES]
    rows=read_rules('\n'.join(source))
    return [row for row in rows if row.count(',')==1],len(lines)-len(source)+sum(row.count(',')!=1 for row in rows)


def other_rule_types(text):
    counts=defaultdict(int)
    options=set()
    for line in text.splitlines():
        line=line.strip().lstrip('\ufeff').strip()
        if not line or line.startswith(('#',';','//')):continue
        kind=line.partition(',')[0].strip()
        if kind in DOMAIN_TYPES:
            row=read_rules(line)[0]
            if row.count(',')!=1:options.add(row)
            continue
        if kind in TYPES:read_rules(line)
        counts[kind if kind in TYPES else 'unsupported']+=1
    if options:counts['domain-options']=len(options)
    return dict(counts)


def audit(entries,data,downloaded,*,order,selected,shared_suffixes=(),shared_hosts=(),exemptions=None,inventory_owners=None):
    order=list(order);declared=groups(entries,order)
    domains={key:[row for row in data[key] if row.split(',')[0] in DOMAIN_TYPES or row.startswith('DOMAIN-KEYWORD,')]
             for key in order}
    index=RuleIndex(domains,order);report={};exemptions=exemptions or {}
    qualified=sum(index.bits[key] for key in order if not entries[key].get('fallback') or entries[key].get('policy-hint')=='reject')
    for source,products in declared.items():
        state={'state':'current','products':products,'filters':filters(entries,source,products),
               'other-products':{},**dict.fromkeys(COUNTS,0)}
        if source not in downloaded:
            raise Invalid('产品来源覆盖检查缺少已声明输入：'+source)
        try:
            rows,other=domain_lines(downloaded[source])
            state['other-rule-types']=other_rule_types(downloaded[source])
        except Invalid as exc:
            raise Invalid('产品来源的规则格式变化，不能确认完整覆盖：'+source) from exc
        state['domain-scopes']=len(rows);state['other-lines']=other
        kept=set().union(*(selected.get(key,{}).get(source,set()) for key in products))
        product_bits=sum(index.bits[key] for key in products)
        for row in rows:
            kind,host=row.split(',');lookup=row
            chosen=row in kept
            if not chosen and kind=='DOMAIN-SUFFIX' and 'DOMAIN,'+host in kept:
                chosen=True;lookup='DOMAIN,'+host;state['narrowed-scopes']+=1
            selected_products={key for key in products
                               if lookup in selected.get(key,{}).get(source,())}
            expected_products={key for key in selected_products if not entries[key].get('fallback')}
            expected_products=expected_products or selected_products
            state['selected-scopes']+=int(chosen)
            if row in exemptions.get(source,()):state['declared-exclusions']+=1;continue
            if shared_scope(row,shared_suffixes,shared_hosts):state['shared-scopes']+=1;continue
            bits=index.scope_bits(lookup)
            owner=next((key for key in order if bits&index.bits[key]),None)
            split=(owner is not None and source in entries[owner].get('sources',())
                   and any(parent in expected_products for parent in entries[owner].get('separates',())))
            if (chosen and owner is not None and owner not in expected_products
                    and entries[owner].get('policy-hint')!='reject'
                    and not split
                    and not all(entries[key].get('fallback') for key in expected_products)):
                raise Invalid('已选产品来源的归属被其他服务抢先匹配：'+source+' '+row+' → '+owner)
            if chosen and (not bits&(qualified|product_bits)
                    or owner not in products and owner is not None and entries[owner].get('fallback')
                    and entries[owner].get('policy-hint')!='reject'):
                state['selected-uncovered']+=1
            if owner is None:state['outside-selection']+=1
            elif entries[owner].get('policy-hint')=='reject':state['privacy-scopes']+=1
            elif owner in products:state['product-scopes']+=1
            elif entries[owner].get('fallback'):state['fallback-scopes']+=1
            else:state['other-products'][owner]=state['other-products'].get(owner,0)+1
        if state['selected-uncovered']:raise Invalid('产品来源中的已选范围被遗漏或被兜底抢先匹配：'+source)
        report[source]=state
    verify_report(entries,report,order=order,inventory_owners=inventory_owners)
    return report


def verify_report(entries,report,*,order=None,inventory_owners=None):
    expected=groups(entries,order)
    inventory_owners=inventory_owners or {}
    if set(report)!=set(expected):raise Invalid('产品来源覆盖报告与当前筛选来源不一致')
    for source,state in report.items():
        types=state.get('other-rule-types',{})
        if (set(state)!=FIELDS or state['products']!=expected[source] or state['filters']!=filters(entries,source,expected[source])
                or state['state']!='current'
                or not isinstance(types,dict) or not set(types)<=OTHER_TYPES
                or any(type(count) is not int or count<=0 for count in types.values())
                or sum(types.values())!=state['other-lines']
                or any(type(state[field]) is not int or state[field]<0 for field in COUNTS)
                or not isinstance(state['other-products'],dict)
                or any(key not in entries or key in state['products'] or type(count) is not int or count<=0
                       or entries[key].get('fallback') or entries[key].get('policy-hint')=='reject'
                       for key,count in state['other-products'].items())):
            raise Invalid('产品来源覆盖报告含有无效字段或归属')
        covered=sum(state[field] for field in ('product-scopes','fallback-scopes','privacy-scopes',
                    'shared-scopes','declared-exclusions','outside-selection'))+sum(state['other-products'].values())
        if (covered!=state['domain-scopes'] or state['selected-scopes']>state['domain-scopes']
                or state['narrowed-scopes']>state['selected-scopes'] or state['selected-uncovered']):
            raise Invalid('产品来源覆盖计数不一致或已选范围没有完整覆盖')
        closed=any(part.get('require-domain-closure') for key in expected[source]
                   for part in entries[key].get('projection',()) if part['source']==source)
        if closed and any(state[field] for field in ('outside-selection','fallback-scopes','privacy-scopes')):
            raise Invalid('完整产品来源仍含未处理范围，不能由补充或拦截规则代替归属：'+source)
        if closed and set(state['other-products'])-inventory_owners.get(source,set()):
            raise Invalid('完整产品来源的范围由未声明归属的其他产品承接：'+source)


def concrete(entry):
    return (entry.get('mode')=='compiled' and not entry.get('fallback')
            and not entry.get('domain-remainder') and entry.get('policy-hint')!='reject')


def reassignments(entries,previous,data,*,selected,order):
    """Prove complete owner changes from source projections or declared service splits."""
    order=list(order);index=RuleIndex(data,order);proofs=defaultdict(dict)
    sources=groups(entries,order)
    indexes={source:RuleIndex({key:selected.get(key,{}).get(source,()) for key in products},products)
             for source,products in sources.items() if len(products)>1}
    for key in order:
        if not concrete(entries[key]):continue
        for row in previous.get(key,()):
            if row.partition(',')[0] not in DOMAIN_TYPES or row.count(',')!=1:continue
            covered=index.scope_bits(row)
            if covered&index.bits[key]:continue
            owners=defaultdict(list)
            for source,projected in indexes.items():
                if key not in projected.bits:continue
                selected_bits=projected.scope_bits(row)
                for owner in projected.order:
                    if (owner!=key and concrete(entries[owner]) and covered&index.bits[owner]
                            and selected_bits&projected.bits[owner]):
                        owners[owner].append(source)
            for owner in order:
                target=entries[owner]
                if (key not in target.get('separates',()) or not concrete(target)
                        or not same_business_family(target,entries[key])
                        or not covered&index.bits[owner]):
                    continue
                shared=set(entries[key].get('sources',()))&set(target.get('sources',()))
                if shared:owners[owner].extend(shared)
            if len(owners)>1:raise Invalid('撤出的范围对应多个产品，不能自动迁移：'+key+' '+row)
            if owners:
                owner=next(iter(owners))
                proofs[key][row]={'owner':owner,'sources':sorted(set(owners[owner]))}
    result=dict(proofs)
    verify_reassignments(entries,data,result,order=order)
    return result


def verify_reassignments(entries,data,report,*,order):
    index=RuleIndex(data,order)
    declared={key:{part['source'] for part in entry.get('projection',())} for key,entry in entries.items()}
    for key,rows in report.items():
        if key not in index.bits or not concrete(entries[key]) or not isinstance(rows,dict) or not rows:
            raise Invalid('来源范围迁移的原产品无效')
        for row,proof in rows.items():
            if (not isinstance(proof,dict) or set(proof)!={'owner','sources'}
                    or row.partition(',')[0] not in DOMAIN_TYPES or row.count(',')!=1 or read_rules(row)!=[row]):
                raise Invalid('来源范围迁移缺少有效的范围或依据')
            owner=proof['owner'];sources=proof['sources']
            allowed=declared[key]&declared.get(owner,set())
            target=entries.get(owner,{})
            if key in target.get('separates',()) and same_business_family(target,entries[key]):
                allowed|=set(entries[key].get('sources',()))&set(target.get('sources',()))
            if (owner not in index.bits or owner==key or not concrete(entries[owner])
                    or not isinstance(sources,list) or not sources or any(not isinstance(s,str) for s in sources)
                    or sources!=sorted(set(sources)) or not set(sources)<=allowed):
                raise Invalid('来源范围迁移必须对应同一来源的独立产品')
            covered=index.scope_bits(row)
            if covered&index.bits[key] or not covered&index.bits[owner]:
                raise Invalid('来源范围迁移与当前完整覆盖范围不一致')
