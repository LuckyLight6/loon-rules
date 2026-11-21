"""Assign shared coverage and fallback membership."""
from loon_rules import rules
from loon_rules.generation.membership import compact,merge_domain_sources,stable_order
from loon_rules.generation.ordering import route_order,shadowed_domains,subscription_order



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


def restore_assigned_rules(rows,assigned):
    if not assigned:
        return rows
    approved=rules.read_rules('\n'.join(assigned))
    if any(r.split(',')[0] not in ('DOMAIN','DOMAIN-SUFFIX') for r in approved):
        raise rules.Invalid('归属记录只能包含已核对的域名规则')
    return stable_order(compact([*rows,*approved]),rows)


def apply_domain_ownership(config,entries,data):
    normal=route_order(config,entries)
    normal_set=set(normal)
    optional=[k for k in config.get('optional',()) if entries[k].get('domain-remainder')]
    scenarios=[(normal,{k for k in normal if entries[k].get('domain-remainder')})]
    for key in optional:
        active=normal_set|{key}
        scenarios.append(([k for k in subscription_order(config,entries) if k in active],{key}))
    assigned={}
    for order,targets in scenarios:
        covered={}
        for key,row,owner,_ in shadowed_domains(order,data):
            if key in targets:covered.setdefault(key,{})[row]=owner
        for key,ownership in covered.items():
            data[key]=[r for r in data[key] if r not in ownership]
            if not data[key]:raise rules.Invalid('补充表已无独立范围，应合并或删除：'+key)
            assigned[key]=ownership
    for key in optional:
        if not entries[key].get('protect-site-scopes'):continue
        sites=[owner for owner in normal if entries[owner].get('policy-hint')!='reject']
        protected={}
        for owner,row,prior,by in shadowed_domains([key,*sites],data):
            if prior==key:protected.setdefault(by,owner)
        named={}
        for owner in sites:
            for row in data[owner]:
                kind,host,*flags=row.split(',')
                if not flags and kind in ('DOMAIN','DOMAIN-SUFFIX'):named.setdefault(host,owner)
        for row in data[key]:
            kind,host,*flags=row.split(',')
            if not flags and kind=='DOMAIN' and host in named:protected.setdefault(row,named[host])
        if protected:
            data[key]=[row for row in data[key] if row not in protected]
            if not data[key]:raise rules.Invalid('扩展拦截没有独立范围，应合并或删除：'+key)
            assigned.setdefault(key,{}).update(protected)
    return assigned
