"""Validate product declarations and derived catalogue fields."""
from loon_rules import rules
from loon_rules.sources import policy as source_policy
from loon_rules.sources import transport as source_transport
from loon_rules.sources import expansion as source_expansion
from loon_rules.sources import geosite
from loon_rules.sources.coverage import same_business_family
from loon_rules import catalog as catalog_schema
from loon_rules.generation import inventories as service_inventory
from loon_rules.generation import directory as service_directory
from loon_rules.policy import SHARED_PARENT,SLUG
from loon_rules.generation.feeds import calibration_urls
from loon_rules.generation.ordering import subscription_order, view_replacements



def section_for(config, rank):
    matches=[item['id'] for item in config['sections']
             if item.get('from',1000)<=rank<=item.get('through',0) or rank in item.get('numbers',())]
    if len(matches)!=1:
        label=catalog_schema.priority_label({'priority':rank},width=catalog_schema.priority_width(config))
        raise rules.Invalid(f'优先级 {label} 没有唯一分区')
    return matches[0]


def validate_declarations(config):
    catalog_schema.materialize(config)
    width=catalog_schema.priority_width(config)
    entries={}
    priorities=set()
    components={e['id'] for e in config.get('source-components',())}
    for e in [*config['entries'],*config.get('source-components',())]:
        name=e['id']
        if not SLUG.fullmatch(name) or name in entries:
            raise rules.Invalid('重复或不合规的名称：'+name)
        if e['mode'] not in ('compiled','managed','view') or not e['description'] or not e['boundary'] or (e['mode']!='view' and not e.get('sources')):
            raise rules.Invalid('元数据未达成：'+name)
        if name.endswith('-all')!=(e['mode']=='view'):
            raise rules.Invalid('合集名称须以 -all 结尾，细分表不能使用此后缀：'+name)
        if name in components:
            if e['mode']!='managed' or any(field in e for field in ('priority','section','selection')):
                raise rules.Invalid('来源比对输入不能声明订阅编号或业务分区：'+name)
        else:
            rank=e['priority']
            if type(rank) is not int or not 1<=rank<10**width or rank in priorities or e['section']!=section_for(config,rank):
                raise rules.Invalid('重复或不合规的编号：'+name)
            priorities.add(rank)
            if width!=3:e=dict(e,**{'priority-width':width})
        entries[name]=e
    subscription_order(config,entries)
    names=[*config['detailed'],*config['general']]
    if len(set(names))!=len(names) or any(entries[k]['mode']=='view' for k in names):
        raise rules.Invalid('细分或通用视图误启用合并表')
    modes=names+config['views']+config['alternatives']+config['optional']
    if len(modes)!=len(entries)-len(components) or set(modes)!=set(entries)-components:
        raise rules.Invalid('分区必须包含每个条目且只出现一次')
    if any(not k.endswith(('-alt','-compat')) for k in config['alternatives']):
        raise rules.Invalid('替代或兼容订阅须以 -alt 或 -compat 结尾')
    if not set(config.get('recommended-views',()))<=set(config['views']):
        raise rules.Invalid('推荐合集不在合并视图清单中')
    for key,entry in list(entries.items()):
        if spec:=entry.get('member-selection'):
            if entry['mode']!='view' or spec['section']!=entry['section']:
                raise rules.Invalid('合集筛选须属于同一业务分区：'+key)
            if 'groups' in spec and (not isinstance(spec['groups'],list) or not spec['groups']
                    or not set(spec['groups'])<={group['id'] for band in config.get('routing-bands',())
                                                 for group in band.get('groups',())}):
                raise rules.Invalid('合集引用了不存在的业务子类：'+key)
            selected=[k for k in subscription_order(config,entries) if k in names
                      and entries[k]['section']==spec['section']
                      and (not spec.get('groups') or entries[k].get('routing-group') in spec['groups'])
                      and k not in spec.get('exclude',())
                      and (not spec.get('policies') or entries[k].get('policy-hint') in spec['policies'])
                      and entries[k].get('policy-hint') not in spec.get('exclude-policies',())]
            entries[key]=dict(entry,members=selected)
    for e in entries.values():
        if 'protect-site-scopes' in e and (type(e['protect-site-scopes']) is not bool
                or e['id'] not in config['optional'] or e['mode']!='managed'
                or e.get('policy-hint')!='reject' or not e.get('domain-remainder')):
            raise rules.Invalid('网站范围保护只用于可选的扩展拦截：'+e['id'])
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
        for field in ('tenant-scope-inputs','official-inputs'):
            if inputs:=e.get(field):
                if e['mode']!='managed' or any(r['source'] not in e['sources'] for r in inputs):
                    raise rules.Invalid('托管范围和官方端点必须声明来源：'+e['id'])
                if field=='official-inputs' and not e.get('official-hosts'):
                    raise rules.Invalid('官方端点输入须声明独立补全：'+e['id'])
        if owners:=e.get('confirm-additions-with'):
            if (e['mode']!='managed' or set(e['kinds'])!={'DOMAIN','DOMAIN-SUFFIX'}
                or any(k not in entries or entries[k]['mode']!='compiled' or entries[k].get('merge-domains')
                       or entries[k]['policy-hint'] not in ('ai-cn','domestic') for k in owners)):
                raise rules.Invalid('新增国内域名须有独立国内业务依据：'+e['id'])
        if spec:=e.get('calibration'):
            retain=spec.get('retain-published',False)
            if type(retain) is not bool or retain and spec['method']!='domain-ad-consensus':
                raise rules.Invalid('已审基线保留只适用于广告域名交叉核对：'+e['id'])
            ad_types=set(source_policy.publication_kinds(e)) if retain else set(e['kinds'])
            ad_allowed={'DOMAIN','DOMAIN-SUFFIX'}
            if retain:ad_allowed.update(('IP-CIDR','IP-CIDR6'))
            if (e['mode']!='managed' or not set(calibration_urls(spec))<=set(e['sources'])
                    or not e.get('feed-sources') or ('reconcile' in e)
                    or (spec['method']=='domain-ad-consensus' and (e.get('policy-hint')!='reject'
                        or not {'DOMAIN','DOMAIN-SUFFIX'}<=ad_types
                        or ad_types-ad_allowed))
                    or (spec['method']=='asn-allocation-consensus' and set(e['kinds'])!={'IP-ASN'})
                    or (spec['method']=='allocation-and-routing' and (e.get('ip-match')!='allow-dns' or set(e['kinds'])!={'IP-CIDR','IP-CIDR6'}))):
                raise rules.Invalid('交叉核对与订阅用途不符：'+e['id'])
        if 'reconcile' in e and (e['mode']!='managed' or
                e['reconcile'] not in ('ad-withdrawals','confirmed-withdrawals') or
                (e['reconcile']=='ad-withdrawals' and e.get('policy-hint')!='reject')):
            raise rules.Invalid('自动撤回不适用于该订阅：'+e['id'])
        if set(e.get('flags',()))-{'no-resolve'}:
            raise rules.Invalid('来源含未确认的 Loon 参数：'+e['id'])
        if 'reverse-dns' in e:
            rules.reverse_dns_rules(e)
        if e['mode']=='compiled' and not any(e.get(field) for field in
                ('include','extract','projection','cidr-source','merge-domains','refine','literal_ips','dns_required','expand')):
            raise rules.Invalid('缺少生成来源：'+e['id'])
        for recipe in e.get('extract',()):
            if recipe['source'] not in e['sources']:
                raise rules.Invalid('提取来源未列入文件说明：'+e['id'])
            if recipe.get('format') in ('domain-scope-list', geosite.FORMAT):
                options = geosite.SCOPE_OPTIONS
                inventories = [spec for spec in config.get('source-inventories', ())
                               if spec['source'] == recipe['source'] and e['id'] in spec['owners']]
                if not any((spec.get('recipe', {}).get('format') == recipe['format']
                            and geosite.scope_options(spec['recipe']) == geosite.scope_options(recipe))
                           or not spec.get('recipe') and recipe['format'] == 'domain-scope-list'
                           and not any(recipe.get(option) for option in options)
                           for spec in inventories):
                    raise rules.Invalid('完整产品清单缺少同范围的独立归属核对：' + e['id'])
            if recipe.get('check-sharing') and (e['mode']!='compiled'
                    or recipe.get('format')!='exclusive-purpose-table' or recipe.get('part')=='shared'):
                raise rules.Invalid('共享用途必须由产品的同一官方用途表核对：'+e['id'])
        for part in e.get('projection',()):
            if 'require-domain-closure' in part and type(part['require-domain-closure']) is not bool:
                raise rules.Invalid('来源完整性要求必须为布尔值：'+e['id'])
            if 'exact-from-extract' in part and (type(part['exact-from-extract']) is not bool
                    or part['exact-from-extract'] and (not e.get('extract') or part.get('all-domains'))):
                raise rules.Invalid('动态精确筛选须有用途字段，不能用于整份域名来源：'+e['id'])
            if 'all-domains' in part and (type(part['all-domains']) is not bool or part['all-domains'] and (
                    part.get('roots') or part.get('exact')
                    or not any(spec['source']==part['source'] and e['id'] in spec['owners']
                               for spec in config.get('source-inventories',())))):
                raise rules.Invalid('完整域名来源需要独立完整性检查，不能同时局部筛选：'+e['id'])
            if part['source'] not in e['sources'] or not (part.get('roots') or part.get('exact') or part.get('all-domains') or part.get('exact-from-extract')):
                raise rules.Invalid('筛选缺少来源或服务边界：'+e['id'])
            if part.get('parent-domains-source') and (part['parent-domains-source'] not in e['sources']
                    or not part.get('brand-label') or not part.get('prefix-label')):
                raise rules.Invalid('地区产品缺少官方域名清单或产品标签：'+e['id'])
        if merge:=e.get('merge-domains'):
            if (e['mode']!='compiled' or e['id'] not in names or not merge.get('include')
                or any(key not in entries or entries[key]['mode']!='managed'
                       for key in merge['include']+merge.get('protect',[]))):
                raise rules.Invalid('域名兜底必须使用已审核的输入和例外：'+e['id'])
            preferred=merge.get('prefer',[])
            if (not isinstance(preferred,list) or len(preferred)!=len(set(preferred))
                    or not set(preferred)<=set(merge['include'])
                    or set(preferred)&set(merge.get('protect',()))):
                raise rules.Invalid('域名兜底的优先来源必须来自合并输入且不能同时作为保护来源：'+e['id'])
        if e['mode']=='view':
            if (e['id'] not in config['views'] or not e['members']
                or len(e['members'])!=len(set(e['members']))
                or not set(e['members'])<=set(names)
                or any(e['section']!=entries[k]['section']
                       for k in e['members'])):
                raise rules.Invalid('合并视图包含未归类成员：'+e['id'])
    owners=service_directory.validate(config,entries)
    for key,owner in owners.items():
        entries[key]=dict(entries[key],vendor=owner)
    for key,e in entries.items():
        if parents:=e.get('separates'):
            if (not isinstance(parents,list) or len(parents)!=len(set(parents))
                    or e['mode']!='compiled' or e.get('fallback') or e.get('domain-remainder')
                    or any(parent not in entries or parent==key
                           or not same_business_family(entries[parent],e)
                           or entries[parent]['mode']=='view'
                           or not set(e['sources'])&set(entries[parent]['sources']) for parent in parents)):
                raise rules.Invalid('业务细分必须有相同用途或厂商，以及共同来源：'+key)
        if part:=e.get('refine'):
            parent=entries.get(part['from'],{})
            if parent.get('mode') not in ('compiled','managed') or parent.get('refine') or parent.get('merge-domains') or not (part.get('roots') or part.get('literal-ip-copy')):
                raise rules.Invalid('产品没有可核对的上级来源：'+key)
    for key in config['views']:
        view=entries[key]
        entries[key]=dict(view,sources=list(dict.fromkeys(
            url for member in view['members'] for url in entries[member]['sources'])),
            **{'allowed-shared':sorted(set(view.get('allowed-shared',()))|{
                host for member in view['members'] for host in entries[member].get('allowed-shared',())})})
    catalog_schema.subscription_aliases(config)
    for section in config['sections']:
        for ref in section.get('related',()):
            if ref['id'] not in entries or entries[ref['id']]['section']==section['id'] or not ref['note']:
                raise rules.Invalid('跨区引用无效：'+ref['id'])
    view_replacements(config,entries,config.get('recommended-views',()))
    for spec in config.get('source-inventories',[]):
        owners=set(spec['owners'])|set(spec.get('other-owners',{}).values())
        if not spec['owners'] or not owners<=set(entries) or not any(
                spec['source'] in e['sources'] for e in entries.values()):
            raise rules.Invalid('来源核对缺少归属或出处：'+spec['id'])
        if any(not reason.strip() or not row.startswith(('DOMAIN,','DOMAIN-SUFFIX,'))
               for row,reason in spec.get('reviewed-outside',{}).items()):
            raise rules.Invalid('来源范围排除须说明公开用途：'+spec['id'])
    source_policy.validate(config,entries)
    source_transport.validate(config)
    source_expansion.validate(config,entries)
    geosite.validate_references(entries)
    service_inventory.validate(entries)
    return entries
