"""Check business routes, IPs and subscription combinations."""
from loon_rules import rules
from loon_rules.generation.dependencies import documented,permits_shadow
from loon_rules.generation import contracts as endpoint_contracts
from loon_rules.domains import covers
from loon_rules.matching import RuleIndex
from loon_rules.generation.membership import compact,overlapping_rules,without_protected
from loon_rules.generation.ordering import ordered_route,route_order,subscription_order,verify_domain_order,verify_ip_order,view_replacements,view_selections
from loon_rules.policy import overbroad
from loon_rules.generation.protection import protected_hosts
from loon_rules.generation.choices import ChoiceModel
from ipaddress import ip_network



def lint_content(name, rows, allowed_shared=()):
    for r in rows:
        if not rules.aligned_network(r):
            raise rules.Invalid('网段的 IP 与掩码未对齐：'+name+' '+r)
        t,p,*_=r.split(',')
        if overbroad(t,p,allowed_shared):
            raise rules.Invalid('规则覆盖整个共享服务或受保护的地址段：'+name+' '+r)
    if list(rows)!=compact(rows):
        raise rules.Invalid('存在等价条目：'+name)


def verify_products(config,entries,data):
    for key,e in entries.items():
        for host in e.get('product-probes',()):
            if not ordered_route(host,[key],data):
                raise rules.Invalid(f'产品缺少已确认入口：{key} {host}')
            if config['critical'].get(host)!=[key]:
                raise rules.Invalid(f'产品入口未纳入完整分流测试：{key} {host}')
        for host in e.get('product-negatives',()):
            if ordered_route(host,[key],data):
                raise rules.Invalid(f'产品包含无关主机：{key} {host}')


def verify_combinations(config,entries,data,*,index=None):
    order=subscription_order(config,entries)
    index=index or RuleIndex(data,order)
    if index.order!=tuple(order):
        raise rules.Invalid('匹配索引与订阅顺序不一致')
    bits=index.bits
    names={v:k for k,v in bits.items()}
    active=set(config['detailed']+config['general'])
    extras=[k for k in config.get('optional',()) if entries[k].get('domain-remainder')]
    relevant=active|set(config['views'])|set(extras)
    row_owners={}
    for key in relevant:
        bit=bits[key]
        for identity in index.identities[key]:
            row_owners[identity]=row_owners.get(identity,0)|bit
    domains=[(host,index.domain_bits(host),wanted) for host,wanted in config['critical'].items()]
    addresses=[(case['target'],index.ip_bits(case['target'],literal=case['literal']),
                [case['rule']] if case['rule'] else []) for case in config.get('ip-cases',())]
    acceptable={key:bit for key,bit in bits.items()}
    for view in config['views']:
        for member in entries[view]['members']:
            acceptable[member]|=bits[view]
    cases={}
    for target,matching,wanted in domains+addresses:
        expected=0
        for key in wanted:expected|=acceptable[key]
        if target in config['critical']:
            for view in config['views']:
                if any(permits_shadow(entries,view,'DOMAIN,'+target,key) for key in wanted):
                    expected|=bits[view]
        # 相同的匹配集合和预期归属在所有组合中等价；保留全部组合与不同预期。
        cases.setdefault((matching,expected),target)
    repeated={}
    for row,owners in row_owners.items():
        if owners.bit_count()>1:repeated.setdefault(owners,row)
    model=ChoiceModel(config,entries,bits)
    for owners,row in repeated.items():
        for selected in model.selections(owners):
            together=owners&selected
            if not together&(together-1):continue
            first=names[together&-together]
            other=[key for key,bit in bits.items() if key!=first and bit&together]
            ad_override=(first in extras and entries[first].get('policy-hint')=='reject'
                         and all(entries[key].get('fallback') and entries[key].get('policy-hint')!='reject' for key in other))
            dependency_override=all(permits_shadow(entries,first,','.join([row[0],row[1],*row[2]]),key) for key in other)
            if not ad_override and not dependency_override:raise rules.Invalid(f'存在合法订阅组合含重复规则：{row[0]},{row[1]}')
    for (matching,expected),target in cases.items():
        for selected in model.selections(matching):
            candidates=matching&selected;first=candidates&-candidates
            if (first and not first&expected) or (not first and expected):
                raise rules.Invalid(f'存在合法订阅组合使 {target} 命中 {names.get(first)!r}，与业务用例不符')
    return model.count()


def verify_selection_order(config, entries, data, index):
    """Check complete domain scopes and overlapping addresses in every legal selection."""
    model=ChoiceModel(config,entries,index.bits)
    names={bit:key for key,bit in index.bits.items()}
    networks={}
    for key in index.order:
        for row in data[key]:
            if row.startswith(('IP-CIDR,','IP-CIDR6,')):
                network=ip_network(row.split(',')[1])
                networks[network]=networks.get(network,0)|index.bits[key]
    for key in index.order:
        if entries[key].get('fallback'):continue
        bit=index.bits[key];earlier=bit-1
        for row in data[key]:
            if row.startswith(('DOMAIN,','DOMAIN-SUFFIX,','DOMAIN-WILDCARD,')):
                covers=index.scope_bits(row)&earlier
            elif row.startswith(('IP-CIDR,','IP-CIDR6,')):
                network=ip_network(row.split(',')[1]);covers=0
                for candidate,owners in networks.items():
                    if owners&earlier and network.version==candidate.version and network.overlaps(candidate):
                        covers|=owners&earlier
            else:continue
            while covers:
                prior=covers&-covers;covers^=prior
                if model.together(bit|prior) and not permits_shadow(entries,names[prior],row,key):
                    raise rules.Invalid(f'存在合法订阅组合使 {key} 的范围被 {names[prior]} 提前覆盖：{row}')


def verify_cases(config, entries, data, online, contracts=(), functional=()):
    verify_products(config,entries,data)
    index=RuleIndex(data,subscription_order(config,entries))
    order=route_order(config,entries)
    normal_types={'DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD','IP-CIDR','IP-CIDR6','IP-ASN'}
    for key in order:
        if not entries[key].get('fallback') and any(r.split(',')[0] not in normal_types for r in data[key]):
            raise rules.Invalid('常规服务表不能用客户端或 URL 代替业务域名：'+key)
    for host,wanted in config['critical'].items():
        got=index.route(host,order)
        if got not in wanted:
            raise rules.Invalid(f'{host}: 首条命中 {got!r}，应为 {", ".join(wanted)}')
    protected=config.get('protected-sections', ['apple','ai'])
    specialties=[k for k in order if entries[k]['section'] in protected]
    for host in config['shared-negatives']:
        if index.route(host,specialties):
            raise rules.Invalid('共享端点被专项覆盖：'+host)
    for host,forbidden in config.get('scope-negatives',{}).items():
        if hit:=index.route(host,forbidden):
            raise rules.Invalid(f'{host}: 非本业务的域名被 {hit} 接管')
    for host,wanted in config.get('view-cases',{}).items():
        got={k for k in config['views'] if any(rules.match_domain(host,row) for row in data.get(k,[]))}
        if got!=set(wanted):
            raise rules.Invalid('合并命中不同：'+host+': '+','.join(sorted(got)))
    for host in config['shared-negatives']:
        if any(rules.match_domain(host,r) for k in config['views']
               if entries[k]['section'] in protected and not entries[k].get('fallback')
               and not documented(entries[k],'DOMAIN,'+host)
               for r in data.get(k,[])):
            raise rules.Invalid('合并视图劫持共享端点：'+host)
    for k,blocks in config.get('no-overlap',{}).items():
        for block in blocks:
            rows=[row for row in data[k] if not any(owner is not None and owner not in entries[k].get('members',())
                  and covers(scope,row)
                  for scope,owner in entries[k].get('_dependency-owners',{}).items())]
            if overlapping_rules(rows,data[block]):
                raise rules.Invalid('跨业务规则重叠：'+k+' / '+block)
    for case in config.get('ip-cases',()):
        want=case['rule']
        got=index.ip_route(case['target'],order,literal=case['literal'])
        if got!=want:
            raise rules.Invalid(f'{case["target"]}: IP 阶段命中 {got!r}，应为 {want}')
    if online:
        for key,e in entries.items():
            protected=protected_hosts(e,config,entries,contracts,functional)
            if protected and without_protected(data[key],protected)!=data[key]:
                raise rules.Invalid(f'{key} 单独订阅会拦截业务端点')
        verify_domain_order(order,entries,data)
        verify_ip_order(order,entries,data)
        verify_selection_order(config,entries,data,index)
        endpoint_contracts.verify_routes(contracts,entries,order,data)
        scenarios=list(dict.fromkeys([(view,) for view in config['views']]+
                                     list(view_selections(config,entries,maximal=True))))
        for views in scenarios:
            replacements=view_replacements(config,entries,views)
            combined=route_order(config,entries,views)
            verify_domain_order(combined,entries,data)
            verify_ip_order(combined,entries,data)
            endpoint_contracts.verify_routes(contracts,entries,combined,data,replacements)
            scenario='+'.join(views)
            for host,wanted in config['critical'].items():
                expected={replacements.get(k,k) for k in wanted}
                got=index.route(host,combined)
                if got not in expected and not (got is not None and any(permits_shadow(entries,got,'DOMAIN,'+host,key) for key in wanted)):
                    raise rules.Invalid(f'{scenario}: {host} 首条命中 {got!r}，应为 {sorted(expected)}')
            for case in config.get('ip-cases',()):
                expected=replacements.get(case['rule'],case['rule'])
                got=index.ip_route(case['target'],combined,literal=case['literal'])
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
    return verify_combinations(config,entries,data,index=index)
