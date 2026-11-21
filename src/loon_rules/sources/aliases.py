"""Keep CNAME adoption evidence separate from DNS availability and rule membership."""
import re

from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid, read_rules
from loon_rules.matching import RuleIndex


def alias_patterns(host,policy):
    patterns=[]
    modifiers='|'.join(re.escape(s) for s in policy['label-modifiers'])
    for parent,aliases in policy['parents'].items():
        for suffix in [parent,*aliases]:
            if not host.endswith('.'+suffix):continue
            stem=host[:-len(suffix)-1]
            patterns.append(re.compile(re.escape(stem)+r'(?:-(?:'+modifiers+r'))?\.(?:'+
                                       '|'.join(re.escape(s) for s in aliases)+r')\Z'))
    return patterns


def cname_tenant(host,alias,policy):
    return (domain_scope.current().registrable(alias)==alias and any(
        host.endswith('.'+parent) and alias.endswith('.'+suffix)
        for parent,suffixes in policy.get('cname-tenants',{}).items() for suffix in suffixes))


def permits(host,alias,policy):
    return cname_tenant(host,alias,policy) or any(pattern.fullmatch(alias) for pattern in alias_patterns(host,policy))


def witness(row,proof):
    if (not isinstance(row,str) or not row.startswith('DOMAIN,') or row.count(',')!=1
            or read_rules(row)!=[row] or not isinstance(proof,dict)
            or set(proof)!={'canonical-hosts','state'} or proof['state'] not in ('current','retained')):
        raise Invalid('CNAME 别名依据的范围或字段无效')
    names=proof['canonical-hosts']
    if (not isinstance(names,list) or not names or any(not isinstance(name,str) for name in names)
            or names!=sorted(set(names))):raise Invalid('CNAME 别名依据缺少明确的原服务主机')
    alias=domain_scope.public_host(row.split(',')[1])
    for host in names:domain_scope.public_host(host)
    return alias,names


def verify_evidence(entries,data,evidence,policies,*,order,aliases=None):
    index=RuleIndex(data,order)
    for key,rows in evidence.items():
        spec=entries.get(key,{}).get('aliases',{})
        if key not in index.bits or not spec.get('resolve-cname') or not isinstance(rows,dict) or not rows:
            raise Invalid('CNAME 别名依据没有启用查询的业务归属')
        policy=policies[spec['policy']]
        for row,proof in rows.items():
            alias,names=witness(row,proof)
            if (index.route(alias,order)!=key or any(index.route(host,order)!=key
                    or not permits(host,alias,policy) for host in names)):
                raise Invalid('CNAME 别名依据与当前服务或别名范围不一致：'+key)
    for key,rows in (aliases or {}).items():
        spec=entries.get(key,{}).get('aliases',{})
        if not spec:raise Invalid('服务别名报告没有对应的业务声明')
        policy=policies[spec['policy']]
        canonical=[row.split(',')[1] for row in data[key] if row.startswith(('DOMAIN,','DOMAIN-SUFFIX,'))
                   and row.count(',')==1 and index.route(row.split(',')[1],order)==key]
        for row in rows:
            alias=row.split(',')[1]
            if (any(cname_tenant(host,alias,policy) for host in canonical)
                    and not any(pattern.fullmatch(alias) for host in canonical for pattern in alias_patterns(host,policy))
                    and row not in evidence.get(key,{})):
                raise Invalid('独立租户别名缺少实际 CNAME 采用依据：'+key)


def reconcile(entries,data,current,previous,published,policies,*,queried,records,order,incomplete=()):
    """Preserve published exact aliases only while their own live query is unavailable."""
    index=RuleIndex(data,order);retained={}
    for key,rows in previous.items():
        spec=entries.get(key,{}).get('aliases',{})
        if key not in index.bits or not spec.get('resolve-cname'):continue
        policy=policies[spec['policy']]
        for row,proof in rows.items():
            alias,names=witness(row,proof)
            if row in current.get(key,{}):continue
            if not any(domain_scope.covers(actual,row) for actual in published.get(key,())):
                raise Invalid('CNAME 历史依据没有对应的已发布范围：'+key)
            failed=[host for host in names if host in queried and (host not in records or host in incomplete)
                    and index.route(host,order)==key and permits(host,alias,policy)]
            if not failed:continue
            current.setdefault(key,{})[row]={'canonical-hosts':failed,'state':'retained'}
            if not index.scope_bits(row)&index.bits[key]:retained.setdefault(key,[]).append(row)
    for key,rows in retained.items():data[key]=list(dict.fromkeys(data[key]+rows))
    verify_evidence(entries,data,current,policies,order=order)
    return retained
