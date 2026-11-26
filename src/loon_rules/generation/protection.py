"""Shared host boundaries and required service endpoint protection."""
from loon_rules import rules
from loon_rules import domains as domain_scope
from loon_rules.sources.inputs import extract_rows as read_source_rows
from loon_rules.policy import SCOPE_POLICY,SHARED_PARENT



def shared_hostnames(config):
    return set(config.get('shared-negatives',()))|set(SCOPE_POLICY.get('shared-hostnames',()))


def extract_rows(recipe,text,*,shared_hosts=()):
    return read_source_rows(recipe,text,shared_hosts=set(shared_hosts)|set(SCOPE_POLICY.get('shared-hostnames',())))


def protected_hosts(entry,config,entries,contracts,functional=()):
    if entry.get('policy-hint')!='reject':
        return set()
    normal={host for host,owners in config['critical'].items()
            if all(entries[k].get('policy-hint')!='reject' for k in owners)}
    for contract in contracts:
        normal.update(host for owner,hosts in contract['routes'].items()
                      if entries[owner].get('policy-hint')!='reject' for host in hosts if '*' not in host)
    return normal|set(functional)|{host for host,forbidden in config.get('scope-negatives',{}).items() if entry['id'] in forbidden}


def functional_hostnames(entries,downloaded,*,aliases=None,dns_evidence=None,shared_hosts=()):
    hosts=set()
    for key,entry in entries.items():
        selected=[recipe for field in ('extract','official-inputs') for recipe in entry.get(field,())
                  if recipe.get('protect-from-reject')]
        selected.extend({**source['recipe'],'source':source['source']} for source in
                        entry.get('discovery',{}).get('inputs',()) if source.get('authority') and source.get('recipe'))
        for recipe in entry.get('dependency-inputs',()):
            if not recipe.get('protect-from-reject') or recipe['source'] not in downloaded:continue
            for row in read_source_rows(recipe,downloaded[recipe['source']]):
                kind,host,*_=row.split(',')
                if kind in ('DOMAIN','DOMAIN-SUFFIX'):
                    if host in SHARED_PARENT:raise rules.Invalid('服务依赖不能放行整个共享云平台')
                    hosts.add(domain_scope.public_host(host))
        for recipe in selected:
            if recipe['source'] not in downloaded:continue
            try:rows=extract_rows(recipe,downloaded[recipe['source']],shared_hosts=shared_hosts)
            except (rules.Invalid,ValueError,SyntaxError):continue
            for row in rows:
                kind,host,*_=row.split(',')
                if kind not in ('DOMAIN','DOMAIN-SUFFIX'):continue
                host=domain_scope.public_host(host)
                if host in SHARED_PARENT:
                    raise rules.Invalid('必需端点不能放行整个共享服务或无效名称')
                hosts.add(host)
        if entry.get('aliases',{}).get('protect-from-reject'):
            for row in [*(aliases or {}).get(key,()),*(dns_evidence or {}).get(key,{})]:
                kind,host,*flags=row.split(',')
                if flags or kind not in ('DOMAIN','DOMAIN-SUFFIX') or host in SHARED_PARENT:
                    raise rules.Invalid('必需服务别名不是有限的公开主机范围')
                hosts.add(domain_scope.public_host(host))
    return hosts


def retained_functional_hostnames(rows, previous, excluded=()):
    """Keep earlier required hosts only while their published service scope is held."""
    hosts=set()
    for host in previous:
        if domain_scope.public_host(host)!=host or host in SHARED_PARENT:
            raise rules.Invalid('此前的必需入口不是有限的公开主机')
        if (any(rules.match_domain(host,row) for row in rows)
                and not any(rules.match_domain(host,row) for row in excluded)):
            hosts.add(host)
    return hosts
