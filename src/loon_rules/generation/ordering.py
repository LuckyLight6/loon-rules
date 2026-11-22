"""Execution order and first-match comparisons."""
from ipaddress import ip_address, ip_network
import re
from loon_rules import rules



def ordered_route(host, ordered_ids, data):
    for key in ordered_ids:
        if any(rules.match_domain(host.lower(), row) for row in data.get(key, ())):
            return key
    return None


def subscription_order(config, entries):
    public=set(entries)-{entry['id'] for entry in config.get('source-components',())}
    bands=config.get('routing-bands')
    if bands is None:  # Legacy catalog schema and standalone library callers
        return sorted(public,key=lambda key:entries[key]['priority'])
    order=[key for band in bands for key in band['ids']]
    if len(order)!=len(set(order)) or set(order)!=public:
        raise rules.Invalid('订阅顺序必须为每份规则安排唯一位置')
    return order


def view_replacements(config, entries, views):
    replacements={}
    seen=set()
    for key in views:
        if key not in config.get('views',()) or key in seen:
            raise rules.Invalid('未知或重复的合集选择：'+key)
        seen.add(key)
        for member in entries[key]['members']:
            if member in replacements:
                raise rules.Invalid('合集不能同时订阅：'+replacements[member]+' / '+key+'；共同成员 '+member)
            replacements[member]=key
    return replacements


def view_selections(config, entries, *, maximal=False):
    members={key:set(entries[key]['members']) for key in config['views']}
    choices=[((),set())]
    for key,owned in members.items():
        choices.extend([(selected+(key,),used|owned) for selected,used in choices
                        if not used&owned])
    for selected,used in choices:
        if not maximal or all(key in selected or used&owned for key,owned in members.items()):
            yield selected


def route_order(config, entries, views=()):
    replacements=view_replacements(config,entries,views)
    active=set(config['detailed']+config['general'])
    active.difference_update(replacements)
    active.update(replacements.values())
    return [key for key in subscription_order(config,entries) if key in active]


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
            if kind not in ('DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD'):
                continue
            labels=host.split('.')
            fixed=[]
            for label in reversed(labels):
                if re.search(r'[*?\[\]]',label):break
                fixed.insert(0,label)
            tail='.'.join(fixed) if kind=='DOMAIN-WILDCARD' else host
            if not tail:continue
            labels=tail.split('.')
            parents=('.'.join(labels[i:]) for i in range(len(labels)))
            owners=[suffix[p] for p in parents if p in suffix]
            if kind=='DOMAIN' or (kind=='DOMAIN-WILDCARD' and tail==host):
                if host in exact:
                    owners.append(exact[host])
                owners.extend((name,pattern) for name,pattern in patterns
                              if rules.match_domain(host,pattern))
            else:
                for name,pattern in patterns:
                    p_kind,p_value=pattern.split(',')[:2]
                    if p_kind!='DOMAIN-WILDCARD' or not p_value.startswith('*.'):continue
                    root=p_value[2:]
                    if re.search(r'[*?\[\]]',root):continue
                    if tail.endswith('.'+root) or (kind=='DOMAIN-WILDCARD' and tail==root):
                        owners.append((name,pattern))
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


def verify_ip_order(order, entries, data):
    previous=[]
    for key in order:
        networks=[ip_network(row.split(',')[1]) for row in data[key]
                  if row.startswith(('IP-CIDR,','IP-CIDR6,'))]
        if not entries[key].get('fallback'):
            for network in networks:
                for owner,prior in previous:
                    if network.version==prior.version and network.overlaps(prior):
                        raise rules.Invalid(f'专项地址与更早的规则相交：{key} {network} ← {owner} {prior}')
        previous.extend((key,network) for network in networks)


def ordered_ip_route(target, ordered_ids, data, *, literal):
    address=ip_address(target)
    for key in ordered_ids:
        for row in data.get(key, ()):
            kind, value, *flags=row.split(',')
            if kind in ('IP-CIDR','IP-CIDR6') and (literal or 'no-resolve' not in flags):
                if address in ip_network(value,strict=False):
                    return key
    return None
