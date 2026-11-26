"""Coordinate source collection, generation, verification and output writes."""
from loon_rules.sources import transport, dns as source_dns, policy as source_policy, expansion as source_expansion, coverage as source_coverage, aliases as source_aliases, security_programs
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from loon_rules import rules, domains as domain_scope, catalog as catalog_schema
from loon_rules.generation import contracts as endpoint_contracts, discovery, inventories as service_inventory, config_history
from loon_rules.generation import directory as service_directory
from loon_rules.sources.aliases import alias_patterns, cname_tenant
from loon_rules.domains import covers
from loon_rules.project import ROOT
from loon_rules.policy import SHARED_PARENT, overbroad
from loon_rules.catalog import rule_filename
from loon_rules.generation.compilation import apply_source_aliases, compile_entry, guard_coverage, shared_service_transfers, verify_shared_service_transfers
from loon_rules.generation.declarations import validate_declarations, section_for
from loon_rules.generation.feeds import calibration_urls, refresh_reviewed_feed, reviewed_input
from loon_rules.generation.membership import compact, domain_rows, merge_conflicts, merge_view, product_rows, stable_order, project_domains, outside_tenant_scopes, uncovered_count, overlapping_rules, without_protected, outside_domain_scopes, merge_domain_sources
from loon_rules.generation.ordering import route_order, ordered_route, subscription_order, shadowed_domains, verify_domain_order, verify_ip_order, ordered_ip_route
from loon_rules.generation.ownership import apply_domain_ownership, derive_domain_merges, restore_assigned_rules, assign_resource_owners
from loon_rules.generation.protection import extract_rows, functional_hostnames, protected_hosts, retained_functional_hostnames, shared_hostnames
from loon_rules.generation.rendering import decorate, metadata, render_index, render_review, verify_file
from loon_rules.generation.reporting import audit_inventory, verify_inventories, ip_summary, maintenance_audit, maintenance_method, subscription_audit
from loon_rules.generation.validation import lint_content, verify_cases, verify_products, verify_combinations


def new_outputs(paths, entries, present, known, *, refresh):
    missing={k for k,path in paths.items() if path not in present}
    if present-set(paths.values()) or (missing and (not refresh or missing & known
                                          or any(entries[k]['mode']=='managed' for k in missing))):
        raise rules.Invalid('规则文件与清单不一致；缺失的已发布订阅不能重新初始化')
    return missing


def run(check=False, offline=False, adopt_ads=False):
    config=json.loads((ROOT/'config/catalog.json').read_text())
    shared_hosts=shared_hostnames(config)
    contracts=json.loads((ROOT/'config/endpoint-contracts.json').read_text())
    catalog_schema.verify(config)
    entries=validate_declarations(config)
    projection_owners=source_coverage.inventory_owners(config.get('source-inventories',()),entries)
    public={entry['id'] for entry in config['entries']}
    file_entries={key:entry for key,entry in entries.items() if key in public}
    components=set(entries)-public
    state_path=ROOT/'data/maintenance-state.json'
    previous_state=json.loads(state_path.read_text()) if state_path.is_file() else {}
    paths={k:ROOT/'rules'/'loon'/rule_filename(e) for k,e in file_entries.items()}
    download_aliases=catalog_schema.subscription_aliases(config)
    alias_paths={ROOT/'rules'/'loon'/(name+'.lsr') for name in download_aliases}
    present=set((ROOT/'rules'/'loon').glob('*.lsr'))-alias_paths
    known=set()
    if not offline and set(paths.values())-present:
        known=set(json.loads((ROOT/'data/maintenance-state.json').read_text())['rules'])
    missing=new_outputs(paths,entries,present,known,refresh=not offline)
    if (ROOT/'docs/rules.md').read_text()!=render_index(config,entries):
        raise rules.Invalid('编号索引未更新（maintain.py --render-index）')
    if directory:=service_directory.render(config,entries):
        path=ROOT/'docs/services.md'
        if not path.is_file() or path.read_text()!=directory:
            raise rules.Invalid('厂商与产品目录未更新（maintain.py --render-index）')
    old={k:(None if k in missing else p.read_text()) for k,p in paths.items()}
    names={path.stem:key for key,path in paths.items()}
    for alias,canonical in download_aliases.items():
        path=ROOT/'rules'/'loon'/(alias+'.lsr')
        if path.is_file() and '# name: '+names[canonical] not in path.read_text().splitlines():
            raise rules.Invalid('兼容下载地址不能覆盖其他产品：'+alias)
        if offline and (not path.is_file() or path.read_bytes()!=(ROOT/'rules'/'loon'/(canonical+'.lsr')).read_bytes()):
            raise rules.Invalid('兼容下载地址与当前成品不同步：'+alias)
    for key in components:
        rows=previous_state.get('component-rules',{}).get(key)
        if not isinstance(rows,list) or not rows:raise rules.Invalid('来源比对基线缺失：'+key)
        times=previous_state.get('component-metadata',{}).get(key,{})
        old[key]='\n'.join(['# '+name+': '+value for name,value in times.items()]+rows)+'\n'
    data={k:([] if t is None else rules.read_rules(t)) for k,t in old.items()}
    for k,rows in data.items():
        if k in missing: continue
        if offline:lint_content(k,rows,entries[k].get('allowed-shared',()))
        if k in file_entries:verify_file(entries[k],rows,old[k],refresh=not offline)
        if offline or entries[k]['mode']!='compiled':
            rules.verify_ip_options(entries[k],rules.ip_options(rows),complete=True)
    if offline:
        report=json.loads((ROOT/'data/maintenance-state.json').read_text())
        security_programs.verify_state_version(config.get('source-inventories', ()), report)
        if report.get('ip-matching')!=ip_summary(file_entries,data):
            raise rules.Invalid('IP 用途报告与正文不一致')
        if report.get('subscription-audit')!=subscription_audit(config,entries,data):
            raise rules.Invalid('订阅去重报告与正文不一致')
        if report.get('maintenance-audit')!=maintenance_audit(file_entries,contracts):
            raise rules.Invalid('固定声明与维护方式报告不一致')
        source_coverage.verify_report(entries,report.get('projection-coverage',{}),order=route_order(config,entries),
            inventory_owners=projection_owners)
        verify_inventories(config.get('source-inventories',()),report.get('source-inventories',{}),
                           data=data,order=route_order(config,entries))
        source_coverage.verify_reassignments(entries,data,report.get('projection-reassignments',{}),order=route_order(config,entries))
        source_aliases.verify_evidence(entries,data,report.get('cname-alias-evidence',{}),
            config.get('source-alias-policies',{}),order=route_order(config,entries),
            aliases=report.get('source-aliases',{}) if 'cname-alias-evidence' in report else None)
        discovery.verify_report(entries,data,report.get('discovery',{}))
        service_inventory.verify_report(entries,data,report.get('service-inventories',{}),
            shared_hosts=shared_hosts,expanded_rows=source_expansion.inventory_rows(report.get('expanded-inputs',{})))
        verify_shared_service_transfers(entries,data,report.get('shared-service-transfers',{}))
        source_expansion.verify_report(entries,data,report.get('expanded-inputs',{}),
            shared_hosts=shared_hosts)
        config_history.verify_report(entries,data,report.get('expanded-inputs',{}),
            report.get('config-endpoint-history',{}),checked_at=report['checked-at'],shared_hosts=shared_hosts,
            negatives=config.get('scope-negatives',{}),order=route_order(config,entries))
        for key,rows in report.get('source-aliases',{}).items():
            if key not in entries or any(not any(covers(actual,row) for actual in data[key]) for row in rows):
                raise rules.Invalid('服务别名报告没有对应到规则正文：'+key)
        restored=dict(data)
        for key,e in entries.items():
            if e.get('domain-remainder'):
                restored[key]=restore_assigned_rules(data[key],report.get('assigned-rules',{}).get(key,{}))
        assignments=apply_domain_ownership(config,entries,restored)
        if assignments!=report.get('assigned-rules',{}) or restored!=data:
            raise rules.Invalid('补充表与专项归属记录不一致')
        for k,e in entries.items():
            if e['mode']=='compiled' and not any(e.get(x) for x in ('projection','extract','cidr-source','merge-domains','refine','aliases','discovery','expand')):
                if set(data[k]) != set(compile_entry(e, {})):
                    raise rules.Invalid('正文与已审清单不一致：'+k)
        for k,e in entries.items():
            if e.get('refine') and data[k]!=product_rows(e,data):raise rules.Invalid('产品与上级来源不一致：'+k)
        for key,rows in derive_domain_merges(config,entries,data).items():
            if data[key]!=rows:
                raise rules.Invalid('域名兜底与已审来源或前置专项不一致：'+key)
        for key in config['views']:
            if data[key]!=merge_view(entries[key],data):
                raise rules.Invalid('合集与专项不一致：'+key)
        runtime,cases=service_inventory.with_cases(config,data,report.get('service-inventories',{}))
        if report.get('inventory-domain-cases',0)!=cases:raise rules.Invalid('服务资产命中用例与正文不符')
        if 'expanded-domain-cases' in report:
            runtime,expanded_cases=source_expansion.with_cases(runtime,data,report.get('expanded-inputs',{}))
            if report['expanded-domain-cases']!=expanded_cases:raise rules.Invalid('发现资料命中用例与正文不符')
        elif any(entry.get('expand',{}).get('method') in ('ios-client-config','public-plist-bag') for entry in entries.values()):
            raise rules.Invalid('公开配置缺少来源主机命中检查')
        runtime,history_cases=config_history.with_cases(runtime,data,report.get('config-endpoint-history',{}))
        if report.get('config-history-domain-cases',0)!=history_cases:
            raise rules.Invalid('配置历史命中用例与保留依据不符')
        if 'business-domain-cases' in report and report['business-domain-cases']!=len(runtime['critical']):
            raise rules.Invalid('业务主机去重数量与实际用例不符')
        profiles=verify_cases(runtime,entries,data,True,contracts,report.get('functional-hosts',()))
        count=len(file_entries)+len(download_aliases)
        aliases_note=(f'（{len(file_entries)} 个规则组，{len(download_aliases)} 份同文兼容入口）'
                      if download_aliases else '')
        print(f'{count} 份本地规则的范围、元数据和合并模式通过离线检查{aliases_note}；{profiles} 种细分与合集组合通过。')
        return 0

    reviewed={k:e for k,e in entries.items() if e['mode']=='managed'}
    watched={u for e in reviewed.values() for u in source_policy.rule_feeds(e)}
    watched.update(u for e in reviewed.values() for u in calibration_urls(e.get('calibration')))
    watched.update(spec['source'] for spec in config.get('source-inventories',()))
    watched.update(source['source'] for entry in file_entries.values()
                   for source in entry.get('discovery',{}).get('inputs',()))
    urls={contract['source'] for contract in contracts}
    if source:=config.get('public-suffix-source'):urls.add(source)
    for e in file_entries.values():
        urls.update(s['source'] for field in ('extract','projection','tenant-scope-inputs','official-inputs') for s in e.get(field,()))
        urls.update(p['parent-domains-source'] for p in e.get('projection',()) if p.get('parent-domains-source'))
        if e.get('cidr-source'):
            urls.add(e['cidr-source'])
        urls.update(e.get('aliases',{}).get('sources',()))
        if e.get('expand'):urls.add(e['expand']['source'])
    bag_sources={e['expand']['source'] for e in entries.values()
                 if e.get('expand',{}).get('method')=='public-plist-bag'}
    def fetch(url):
        try:
            return transport.fetch(url,config.get('source-mirrors',{}),transport.download,public_bag=url in bag_sources)
        except (rules.Invalid,OSError) as exc:
            if url not in urls:
                return None  # A reviewed feed still has its own last good output.
            raise rules.Invalid(f'{url}：{exc}') from exc
    requested=sorted(urls|watched)
    with ThreadPoolExecutor(max_workers=8) as pool:
        fetched={u:t for u,t in zip(requested,pool.map(fetch,requested)) if t is not None}
    downloaded={u:value[0] for u,value in fetched.items()}
    used_mirrors={u:value[1] for u,value in fetched.items() if value[1]!=u}
    active_suffixes=None;suffix_state={}
    if source:=config.get('public-suffix-source'):
        try:
            active_suffixes,suffix_state=domain_scope.select_list(downloaded[source],domain_scope.DATA.read_text() if domain_scope.DATA.exists() else '')
            domain_scope.use(active_suffixes)
        except ValueError as exc:raise rules.Invalid(str(exc)) from exc
    security_programs.verify_history(config.get('source-inventories', ()), downloaded,
                                     previous_state)
    expanded_rows,expansion_status,child_inputs=source_expansion.collect(entries,downloaded,transport.download,
        shared_hosts=shared_hosts)
    downloaded.update(child_inputs)
    requested=sorted(set(requested)|set(child_inputs))
    contracts=endpoint_contracts.resolve_additions(contracts,entries,downloaded,
        shared_hosts=SHARED_PARENT|shared_hosts)
    contract_status=endpoint_contracts.verify_sources(contracts,downloaded)
    source_status={}
    compiled={};projection_inputs={};resource_inputs={}
    for k,e in file_entries.items():
        if e['mode']!='compiled' or e.get('merge-domains') or e.get('refine'):
            continue
        compiled[k]=data[k]
        projected={}
        shared_scopes=([host for contract in contracts
                        if e['section'] in contract.get('guard-sections',())
                        for host in contract.get('shared',())]
                       if e.get('domain-remainder') and not e.get('fallback') else ())
        reserved_rows=[('DOMAIN-WILDCARD,' if '*' in host else 'DOMAIN,')+host
                       for contract in contracts for owner,hosts in contract.get('routes',{}).items()
                       if owner!=k for host in hosts] if e.get('domain-remainder') else ()
        data[k]=compile_entry(e, downloaded,shared_scopes=shared_scopes,reserved_rows=reserved_rows,
                              extra_rows=expanded_rows.get(k,()),shared_hosts=shared_hosts,projection_rows=projected,resource_rows=resource_inputs)
        if projected:projection_inputs[k]=projected
    resource_transfers=assign_resource_owners(entries,data,resource_inputs,route_order(config,entries))
    dns_names={row.split(',')[1] for key,entry in entries.items() if entry.get('aliases',{}).get('resolve-cname')
               for row in data[key] if row.startswith(('DOMAIN,','DOMAIN-SUFFIX,')) and row.count(',')==1}
    dns_patterns={host:[pattern for e in entries.values() if e.get('aliases',{}).get('resolve-cname')
                        for pattern in alias_patterns(host,config['source-alias-policies'][e['aliases']['policy']])]
                  for host in dns_names}
    cname_records,cname_status=source_dns.collect(dns_names,
        follow=lambda root,name:any(pattern.fullmatch(name) for pattern in dns_patterns[root])
            or any(cname_tenant(root,name,config['source-alias-policies'][e['aliases']['policy']])
                   for e in entries.values() if e.get('aliases',{}).get('resolve-cname')))
    prior_report=previous_state
    alias_evidence={}
    aliases=apply_source_aliases(config,entries,data,downloaded,dns_records=cname_records,dns_evidence=alias_evidence)
    retained_aliases=source_aliases.reconcile(entries,data,alias_evidence,
        prior_report.get('cname-alias-evidence',{}),compiled,config.get('source-alias-policies',{}),
        queried=dns_names,records=cname_records,incomplete=cname_status.get('incomplete-hosts',()),
        order=route_order(config,entries))
    for key,rows in retained_aliases.items():aliases[key]=compact(aliases.get(key,[])+rows)
    proposals,discovery_status=discovery.propose(entries,data,downloaded,
        active=route_order(config,entries),shared=SHARED_PARENT,
        shared_hosts=shared_hosts,
        protected_sections=config.get('protected-sections',['apple','ai']))
    for key,rows in proposals.items():
        if entries[key]['mode']=='compiled':data[key]=compact(data[key]+rows)
    epoch=int(datetime.now(timezone.utc).timestamp())
    inventory_previous=dict(compiled);inventory_candidates=dict(data)
    for key,entry in reviewed.items():
        if not entry.get('inventory-refresh'):continue
        inventory_previous[key]=list(data[key])
        official=[row for recipe in service_inventory.recipes(entry)
                  for row in extract_rows(recipe,downloaded[recipe['source']],shared_hosts=shared_hosts)]
        inventory_candidates[key]=compact(reviewed_input(entry,downloaded)+official+
            list(discovery_status.get(key,{}).get('proofs',{})))
    retained,inventory_status=service_inventory.reconcile(entries,inventory_previous,inventory_candidates,downloaded,
        prior_report.get('service-inventories',{}),epoch,shared_hosts=shared_hosts,expanded_rows=expanded_rows)
    for key,entry in reviewed.items():
        retired=set(inventory_status.get(key,{}).get('retired',()))
        if retired:data[key]=[row for row in data[key] if row not in retired]
    for key,rows in retained.items():data[key]=compact(data[key]+rows)
    retained,history_status=config_history.reconcile(entries,compiled,data,expansion_status,prior_report,
        checked_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),shared_hosts=shared_hosts,
        negatives=config.get('scope-negatives',{}))
    for key,rows in retained.items():data[key]=compact(data[key]+rows)
    shared_transfers=shared_service_transfers(entries,compiled,data,downloaded,route_order(config,entries))
    projection_transfers=source_coverage.reassignments(entries,compiled,data,
        selected=projection_inputs,order=route_order(config,entries))
    for k,previous in compiled.items():
        e=entries[k];candidate=data[k]
        if any(e.get(x) for x in ('projection','extract','cidr-source','aliases','discovery','expand')):
            transferred=[row for owner,rows in aliases.items() if owner!=k for row in rows]
            transferred.extend(row for row,owner in shared_transfers.get(k,{}).items() if owner is not None)
            transferred.extend(projection_transfers.get(k,{}))
            transferred.extend(resource_transfers.get(k,{}))
            if e.get('domain-remainder'):
                transferred.extend(row for owner in route_order(config,entries) if owner!=k
                    and not entries[owner].get('fallback') and not entries[owner].get('domain-remainder')
                    and entries[owner].get('policy-hint')!='reject' for row in data[owner])
            retired=set(inventory_status.get(k,{}).get('retired',()))
            guard_coverage(k, [row for row in previous if row not in retired], candidate,
                reassigned=transferred,
                official_autnums=any(r['format']=='rdap-entity-autnums' for r in e.get('extract',())),
                excluded_hosts=[host for host,owners in config.get('scope-negatives',{}).items() if k in owners],
                official_networks=bool(e.get('cidr-source')
                or any(r['format'] in ('labelled-networks','ip-prefix-json','section-media-networks','section-network-blocks','endpoint-network-sets','service-address-table')
                       for r in e.get('extract',()))))
        data[k]=stable_order(candidate,previous)
        lint_content(k,data[k],e.get('allowed-shared',()))
        rules.verify_ip_options(e,rules.ip_options(data[k]),complete=True)
    functional=functional_hostnames(entries,downloaded,aliases=aliases,dns_evidence=alias_evidence,shared_hosts=shared_hosts)
    functional.update(row.split(',')[1] for key,rows in expanded_rows.items()
                      if entries[key]['expand'].get('protect-from-reject') for row in rows)
    functional.update(row.split(',')[1] for key,state in history_status.items()
                      if entries[key]['expand'].get('protect-from-reject') for row in state['retained'])
    functional.update(row.split(',')[1] for key,state in inventory_status.items()
                      if any(r.get('protect-from-reject') for r in service_inventory.recipes(entries[key]))
                      or entries[key].get('expand',{}).get('protect-from-reject')
                      for row in state['retained']+list(state.get('artifact-hosts',{})))
    for k in sorted(reviewed,key=lambda key:reviewed[key].get('policy-hint')=='reject'):
        e=reviewed[k]
        reserved=[row for owner in e.get('reserve-domains-for',()) for row in data[owner]
                  if row.split(',')[0] in ('DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD')]
        tenant_rows={r for recipe in e.get('tenant-scope-inputs',()) for r in extract_rows(recipe,downloaded[recipe['source']],shared_hosts=shared_hosts)}
        official_rows={r for recipe in e.get('official-inputs',()) for r in extract_rows(recipe,downloaded[recipe['source']],shared_hosts=shared_hosts)}
        if any(not r.startswith('DOMAIN-SUFFIX,') for r in tenant_rows) or any(not r.startswith('DOMAIN,') for r in official_rows):
            raise rules.Invalid('托管后缀或官方精确主机的输入类型错误：'+k)
        previous=data[k]
        if e.get('domain-remainder'):
            previous=restore_assigned_rules(previous,prior_report.get('assigned-rules',{}).get(k,{}))
        data[k],source_status[k]=refresh_reviewed_feed(e,previous,downloaded,
            protected=protected_hosts(e,config,entries,contracts,functional),reserved=reserved,adopt_ads=adopt_ads,
            admitted=discovery_status.get(k,{}).get('proofs',{}),
            discovery_state=discovery_status.get(k,{}).get('state'),
            corroborated=domain_rows(data,e.get('confirm-additions-with',())),
            tenant_roots=[r.split(',')[1] for r in tenant_rows],
            observation=prior_report.get('reviewed-inputs',{}).get(k,{}).get('withdrawal-observation'),
            revision=metadata(old[k]).get('updated-at') if old[k] else None,epoch=epoch,
            official=[h for contract in contracts for h in contract['routes'].get(k,())]+[r.split(',')[1] for r in official_rows])
        if source_status[k].get('discovery-held'):
            functional.update(retained_functional_hostnames(data[k],prior_report.get('functional-hosts',()),
                                                           e.get('excluded-rules',())))
    for k,e in entries.items():
        if e.get('refine'):data[k]=product_rows(e,data)
    for key,rows in derive_domain_merges(config,entries,data).items():
        data[key]=rows
        lint_content(key,rows,entries[key].get('allowed-shared',()))
        rules.verify_ip_options(entries[key],rules.ip_options(rows),complete=True)
    assignments=apply_domain_ownership(config,entries,data)
    for key in config['views']:
        e=entries[key]
        data[key]=merge_view(e,data)
        lint_content(key,data[key],e.get('allowed-shared',()))
        rules.verify_ip_options(e,rules.ip_options(data[key]),complete=True)
    for key,e in entries.items():
        lint_content(key,data[key],e.get('allowed-shared',()))
        rules.verify_ip_options(e,rules.ip_options(data[key]),complete=True)
    service_inventory.verify_report(entries,data,inventory_status,shared_hosts=shared_hosts,expanded_rows=expanded_rows)
    runtime,inventory_cases=service_inventory.with_cases(config,data,inventory_status)
    runtime,expanded_cases=source_expansion.with_cases(runtime,data,expansion_status)
    runtime,history_cases=config_history.with_cases(runtime,data,history_status)
    profiles=verify_cases(runtime,entries,data,True,contracts,functional)
    discovery.verify_report(entries,data,discovery_status)
    verify_shared_service_transfers(entries,data,shared_transfers)
    source_coverage.verify_reassignments(entries,data,projection_transfers,order=route_order(config,entries))
    source_expansion.verify_report(entries,data,expansion_status,shared_hosts=shared_hosts)
    config_history.verify_report(entries,data,expansion_status,history_status,
        checked_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),shared_hosts=shared_hosts,
        negatives=config.get('scope-negatives',{}),order=route_order(config,entries))
    projection_coverage=source_coverage.audit(entries,data,downloaded,order=route_order(config,entries),
        selected=projection_inputs,shared_suffixes=SHARED_PARENT,shared_hosts=shared_hosts,
        exemptions=source_coverage.declared_exclusions(config),inventory_owners=projection_owners)
    source_aliases.verify_evidence(entries,data,alias_evidence,config.get('source-alias-policies',{}),
        order=route_order(config,entries),aliases=aliases)
    now=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    inventories={spec['id']:audit_inventory(spec,downloaded,data,order=route_order(config,entries),entries=entries)
                 for spec in config.get('source-inventories',())}
    verify_inventories(config.get('source-inventories',()),inventories,
                       data=data,order=route_order(config,entries))
    changed=[]
    methods={}
    for k,e in file_entries.items():
        methods.setdefault(maintenance_method(e),[]).append(e['priority'])
    for key,e in file_entries.items():
        rendered=decorate(e,data[key],old[key],now)
        if rendered==old[key]:
            continue
        changed.append(key)
        if not check:
            tmp=paths[key].with_suffix('.new')
            tmp.write_text(rendered)
            tmp.replace(paths[key])
    if not check:
        for alias,canonical in download_aliases.items():
            source=ROOT/'rules'/'loon'/(canonical+'.lsr')
            destination=ROOT/'rules'/'loon'/(alias+'.lsr')
            text=source.read_text()
            if not destination.is_file() or destination.read_text()!=text:
                temporary=destination.with_suffix('.new')
                temporary.write_text(text)
                temporary.replace(destination)
        if source:=config.get('public-suffix-source'):
            domain_scope.DATA.write_text(active_suffixes)
        report={
            'checked-at':now,'inputs-read':len(downloaded),'critical':len(config['critical']),
            'inputs-requested':len(requested),'profiles-checked':profiles,'assigned-rules':assignments,
            'subscription-audit':subscription_audit(config,entries,data),
            'maintenance-audit':maintenance_audit(file_entries,contracts),
            'projection-coverage':projection_coverage,
            'projection-reassignments':projection_transfers,
            'source-aliases':aliases,
            'cname-alias-evidence':alias_evidence,
            'discovery':discovery_status,
            'cname-discovery':cname_status,
            'source-mirrors-used':used_mirrors,
            'public-suffix-state':suffix_state,
            'shared-service-transfers':shared_transfers,
            'expanded-inputs':expansion_status,
            'maintenance':methods,'reviewed-inputs':source_status,
            'official-endpoints':contract_status,'source-inventories':inventories,
            security_programs.HISTORY_VERSION_FIELD: 1,
            'functional-hosts':sorted(functional),'service-inventories':inventory_status,
            'inventory-domain-cases':inventory_cases,
            'expanded-domain-cases':expanded_cases,
            'config-endpoint-history':history_status,'config-history-domain-cases':history_cases,
            'business-domain-cases':len(runtime['critical']),
            'fallback-conflicts':merge_conflicts(entries,data),
            'shared-negatives':len(config['shared-negatives']), 'changed':changed,
            'scope-negatives':len(config.get('scope-negatives',{})),
            'ip-cases':len(config.get('ip-cases',())),
            'ip-matching':ip_summary(file_entries,data),
            'rules':{k:len(data[k]) for k in sorted(file_entries,key=lambda k:entries[k]['priority'])},
            'component-rules':{key:data[key] for key in sorted(components)},
            'component-metadata':{key:metadata(decorate(entries[key],data[key],old[key],now))
                                  for key in sorted(components)},
        }
        (ROOT/'data/maintenance-state.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        (ROOT/'build').mkdir(exist_ok=True)
        (ROOT/'build/verification.md').write_text(render_review(report,entries))
    negatives=len(config['shared-negatives'])+len(config.get('scope-negatives',{}))
    if suffix_state.get('state')=='retained-newer':
        print(f'公共后缀来源版本 {suffix_state["source-version"]} 较旧，保留已发布版本 {suffix_state["active-version"]}。')
    print(f'{len(runtime["critical"])} 个业务域名、{negatives} 个反例、{len(config.get("ip-cases",()))} 个 IP 用例、'
          f'{len(config["views"])} 种合并视图通过；{len(changed)} 份正文或元数据变化。')
    print(f'产品筛选来源 {len(projection_coverage)} 份；已选范围缺少承接 '
          f'{sum(state["selected-uncovered"] for state in projection_coverage.values())} 项；'
          f'筛选外未完整覆盖 {sum(state["outside-selection"] for state in projection_coverage.values())} 项。')
    print('官方端点核对：'+', '.join(f'{name} {s["assigned"]} 项归属 / {s["shared"]} 项共享'
                                   for name,s in contract_status.items()))
    attention={k:v['state'] for k,v in source_status.items() if v['state']!='current'}
    if attention:
        print('保留已审正文的来源：'+', '.join(f'{k}={s}' for k,s in attention.items()))
    return 0
