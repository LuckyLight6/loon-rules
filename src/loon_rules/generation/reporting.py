"""Build audit statistics from validated data."""
from loon_rules import rules
from loon_rules.domains import covers
from loon_rules.matching import RuleIndex
from loon_rules.sources.inputs import extract_rows
from loon_rules.sources.coverage import domain_lines
from loon_rules.sources import geosite
from loon_rules.sources import security_programs
from loon_rules.generation.ordering import route_order,shadowed_domains



def audit_inventory(spec, downloaded, data, *, order=None, entries=None):
    """Look outside the publishing filters for unassigned domain scopes. Never export candidates."""
    if spec['source'] not in downloaded: return {'state':'unavailable'}
    other_lines=0
    source_details={}
    delegated_domains={}
    try:
        text=downloaded[spec['source']]
        if spec.get('recipe'):
            recipe = dict(spec['recipe'])
            if recipe.get('source', spec['source']) != spec['source']:
                raise rules.Invalid('来源清单的读取器不能改换资料身份')
            recipe['source'] = spec['source']
            if spec['recipe'].get('format') == geosite.FORMAT:
                record = geosite.parse(spec['recipe'], text)
                other_lines = (len(record['includes']) + sum(record['omitted-types'].values())
                               + sum(record['omitted-comment-blocks'].values())
                               + record['unselected-domain-scopes'])
                source_details = {'delegated-includes': record['includes'],
                                  'omitted-rule-types': record['omitted-types'],
                                  'omitted-comment-blocks': record['omitted-comment-blocks'],
                                  'unselected-domain-scopes': record['unselected-domain-scopes'],
                                  'delegated-domain-scopes': record['delegated-scopes'],
                                  'reading-policy': geosite.scope_options(spec['recipe'])}
                delegated_domains=record['delegated-scopes']
            if recipe.get('format') == security_programs.FORMAT:
                source_details['program-assets'] = security_programs.audit(recipe, text)
            rows=sorted(extract_rows(recipe,text))
            rows.extend(delegated_domains)
        elif spec.get('domain-lines-only'):
            rows,other_lines=domain_lines(text)
        else:
            rows=rules.read_rules(text)
    except rules.Invalid:
        return {'state':'invalid'}
    domains=[r for r in rows if r.startswith(('DOMAIN,','DOMAIN-SUFFIX,','DOMAIN-WILDCARD,')) and r.count(',')==1]
    order=list(data if order is None else order)
    index=RuleIndex(data,order)
    reviewed=set(spec.get('shared',{}))|set(spec.get('reviewed-outside',{}))
    other=0
    for row in domains:
        if row in reviewed: continue
        if row in delegated_domains:
            wanted={delegated_domains[row]}
        elif row in spec.get('other-owners',{}):
            wanted={spec['other-owners'][row]}
        else:
            wanted=set(spec['owners'])
        if collector := spec.get('resource-owner'):
            if entries is None or collector not in entries:
                raise rules.Invalid('网页图片清单缺少可核对的产品范围')
            matching = index.scope_bits(row)
            existing = next((key for key in order if key != collector
                             and entries[key].get('policy-hint') != 'reject'
                             and not entries[key].get('fallback') and not entries[key].get('domain-remainder')
                             and matching & index.bits[key]), None)
            wanted = {existing or collector}
        if entries is not None:
            wanted.update(member for key in tuple(wanted) for member in entries[key].get('members',()))
        matching=index.scope_bits(row)
        owner=next((key for key in order if matching&index.bits[key]),None)
        if owner not in wanted: other+=1
    report={'state':'review' if other else 'current','domain-scopes':len(domains),
            'outside-scope':other,'other-rules':other_lines+len(rows)-len(domains),**source_details}
    if spec.get('reviewed-outside'):
        report['reviewed-outside']=len(set(domains)&set(spec['reviewed-outside']))
    return report


def verify_inventories(specs, report, *, data=None, order=None):
    expected={spec['id'] for spec in specs}
    if set(report)!=expected:
        raise rules.Invalid('服务来源清单的检查结果缺失或多出')
    for spec in specs:
        name=spec['id'];state=report[name]
        if (state.get('state')!='current' or state.get('outside-scope')!=0
                or type(state.get('domain-scopes')) is not int or state['domain-scopes']<=0
                or type(state.get('other-rules')) is not int or state['other-rules']<0):
            raise rules.Invalid('服务来源清单未完整归属，停止发布：'+name)
        if spec.get('recipe', {}).get('format') == security_programs.FORMAT:
            security_programs.verify(spec['recipe'], state.get('program-assets'))
        if spec.get('recipe', {}).get('format') == geosite.FORMAT:
            omitted=state.get('omitted-rule-types')
            delegated=state.get('delegated-includes')
            blocks=state.get('omitted-comment-blocks')
            unselected=state.get('unselected-domain-scopes',0)
            excluded_blocks=set(spec['recipe'].get('excluded-comment-blocks',{}))
            if (not isinstance(omitted,dict)
                    or not set(omitted)<=set(spec['recipe'].get('omit-types',{}))
                    or any(type(count) is not int or count<=0 for count in omitted.values())
                    or delegated!=sorted(spec['recipe'].get('delegated-includes',{}))
                    or not isinstance(blocks,dict) or not set(blocks)<=excluded_blocks
                    or any(type(count) is not int or count<=0 for count in blocks.values())
                    or type(unselected) is not int or unselected<0
                    or unselected and not spec['recipe'].get('include-comment-blocks')
                    or state.get('reading-policy')!=geosite.scope_options(spec['recipe'])
                    or state['other-rules']!=len(delegated)+sum(omitted.values())+sum(blocks.values())+unselected):
                raise rules.Invalid('上游分类的省略类型或子分类记录不完整：'+name)
            delegated_domains=state.get('delegated-domain-scopes')
            assignments=spec['recipe'].get('delegated-scopes',{})
            if not isinstance(delegated_domains,dict) or not set(assignments)<=set(delegated_domains):
                raise rules.Invalid('上游分类的共享范围分配记录不完整：'+name)
            for row,owner in delegated_domains.items():
                if rules.read_rules(row)!=[row] or row.count(',')!=1:
                    raise rules.Invalid('上游共享范围的记录含无效规则：'+name)
                wanted={target['owner'] for scope,target in assignments.items() if covers(scope,row)}
                if wanted!={owner}:
                    raise rules.Invalid('上游共享范围的记录与产品分配不一致：'+name)
            if data is not None and delegated_domains:
                index=RuleIndex(data,order)
                for row,owner in delegated_domains.items():
                    matching=index.scope_bits(row)
                    actual=next((key for key in index.order if matching&index.bits[key]),None)
                    if actual!=owner:
                        raise rules.Invalid('上游共享范围没有由目标产品完整承接：'+name)


def maintenance_method(entry):
    if entry['mode']=='view' or entry.get('merge-domains'):
        return '组合生成'
    if entry.get('refine'):return '随已核对的产品来源生成'
    if entry.get('reverse-dns'):return '反查名称随地址声明生成'
    if entry.get('inventory-refresh'):
        return ('随发布文件发现主机，保留版本依据' if entry.get('inventory-retention')=='published-artifacts'
                else '随完整服务清单补入，间隔确认后撤回')
    if spec:=entry.get('expand'):
        if spec['method']=='aws-coding-network':return '跟随完整官方网络用途表与地区定义，核对共用API和业务桶'
        if spec['method']=='next-sdk':return ('从发布 SDK 的生产字段跟随当前依赖脚本'
            if spec.get('source-format')=='javascript-environment' else '跟随产品页面的当前 SDK，读取生产配置')
        return ('从产品页面的资源字段和请求示例读取入口' if spec['method']=='next-page'
                else '从官方目录发现产品与版本，再读取服务端点')
    if entry.get('discovery'):return '按用途与来源家族自动补全'
    if entry.get('reconcile')=='confirmed-withdrawals':return '连续两次确认撤回'
    if entry.get('calibration',{}).get('method')=='asn-allocation-consensus':return 'ASN 来源与注册记录交叉核对'
    if entry.get('official-hosts'):return '官方业务端点自动补入'
    if entry.get('confirm-additions-with'):return '新增域名与国内业务表交叉核对'
    if spec:=entry.get('calibration'):
        return '整域拦截交叉核对' if spec['method']=='domain-ad-consensus' else '分配与路由交叉核对'
    if entry['mode']=='managed':
        return '随来源缩小拦截' if entry.get('reconcile')=='ad-withdrawals' else '比较上游，保留已审范围'
    if any(entry.get(k) for k in ('extract','projection','cidr-source','aliases','expand')):
        return '按来源筛选'
    return '已核清单'


def maintenance_audit(entries,contracts):
    """Separate fixed declarations, source extraction and approved output baselines."""
    ordered=sorted(entries,key=lambda k:entries[k]['priority'])
    fixed={k:sum(len(entries[k].get(field,())) for field in ('include','literal_ips','dns_required'))
           for k in ordered if entries[k]['mode']!='view'}
    fixed={k:n for k,n in fixed.items() if n}
    verified={k:{host for contract in contracts for host in contract.get('routes',{}).get(k,())}
              for k in fixed}
    def exact_count(value):
        if isinstance(value,dict):
            return sum(len(part) if field=='exact' else exact_count(part) for field,part in value.items())
        if isinstance(value,list):return sum(exact_count(part) for part in value)
        return 0
    selectors={k:exact_count(entries[k]) for k in ordered if entries[k]['mode']!='view'}
    return {
        'fixed-declarations':fixed,
        'fixed-only':[k for k in ordered if entries[k]['mode']=='compiled' and not any(
            entries[k].get(field) for field in ('projection','extract','cidr-source','merge-domains','refine','aliases','discovery','expand'))],
        'baseline-managed':[k for k in ordered if entries[k]['mode']=='managed'],
        'source-scoped':[k for k in ordered if entries[k]['mode']=='compiled'
                         and (entries[k].get('projection') or entries[k].get('extract') or entries[k].get('expand'))],
        'official-checks':{k:len(hosts) for k,hosts in verified.items() if hosts},
        'exact-selectors':{k:n for k,n in selectors.items() if n},
        'automatic-discovery':[k for k in ordered if entries[k].get('discovery')],
        'address-derived':{k:len(rules.reverse_dns_rules(entries[k])) for k in ordered
                           if entries[k].get('reverse-dns')},
    }


def ip_summary(entries,data):
    report={}
    for key,e in entries.items():
        if e['mode']=='view':continue
        options=rules.ip_options(data[key])
        if not options:continue
        report[key]={'intent':e['ip-match'],
                     'no-resolve':sum(v=={True} for v in options.values()),
                     'resolve-for-match':sum(v=={False} for v in options.values())}
    return report


def subscription_audit(config,entries,data):
    order=route_order(config,entries)
    owners={}
    for key in order:
        for row in data[key]:
            owners.setdefault(row,[]).append(key)
    optional={}
    for key in config.get('optional',()):
        counts={}
        for row in data[key]:
            if row in owners:
                first=owners[row][0]
                counts[first]=counts.get(first,0)+1
        if counts:optional[key]=counts
    return {'routine-tables':len(order),
            'duplicate-rules':sum(len(v)>1 for v in owners.values()),
            'shadowed-domain-rules':sum(1 for _ in shadowed_domains(order,data)),
            'optional-overlaps':optional}
