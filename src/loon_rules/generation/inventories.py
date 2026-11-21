"""Track current service endpoints separately from hosts used by published artifacts."""
import json
from loon_rules.sources import templates as source_templates
from loon_rules.rules import Invalid
from loon_rules.domains import covers, exclude_shared_scopes
from loon_rules.sources.inputs import extract_rows
from loon_rules.sources.formats.common import public_domain_pattern
from loon_rules.matching import merge_cases


WAIT_SECONDS=20*3600
MAX_GAP_SECONDS=3*86400
INVENTORY_FIELDS={'service-domain-groups':('path','groups'),
                  'json-service-urls':('paths','identity','revision-path'),
                  'plist-service-fields':('host-paths','url-paths','identity','records','data-path'),
                  'section-code-domains':('sections',),
                  'json-document':('body-path','identity','document'),
                  'purpose-domain-lists':('labels','allow-identical-duplicates','nested-subdomain-labels',
                                          'item-purpose-prefixes','item-purpose-contains','item-purpose-style')}


def recipes(entry):
    field='official-inputs' if entry.get('mode')=='managed' else 'extract'
    return [r for r in entry.get(field,()) if r.get('format') in INVENTORY_FIELDS]


def directory(entry):
    return entry.get('expand',{}).get('method')=='api-directory'


def complete_expansion(entry):
    return entry.get('expand',{}).get('method') in ('api-directory','host-templates')


def inputs(entry):
    result=[{field:r[field] for field in ('source','format',*INVENTORY_FIELDS[r['format']]) if field in r}
            for r in recipes(entry)]
    if directory(entry):
        spec=entry['expand']
        result.append({'format':'api-directory',**{field:spec[field] for field in
                      ('source','title-prefixes','exclude-title-prefixes','documents-base','max-documents','versions') if field in spec}})
    elif entry.get('expand',{}).get('method')=='host-templates':
        result.append({'format':'host-templates',**{field:entry['expand'][field] for field in source_templates.FIELDS}})
    return result


def validate(entries):
    for key,entry in entries.items():
        if 'inventory-retention' in entry and not entry.get('inventory-refresh'):
            raise Invalid('端点保留方式需要启用清单维护：'+key)
        if 'inventory-refresh' not in entry:continue
        if type(entry['inventory-refresh']) is not bool:
            raise Invalid('清单轮换开关必须为布尔值：'+key)
        supported=entry['mode']=='compiled' or entry['mode']=='managed' and entry.get('official-hosts') and recipes(entry)
        if entry['inventory-refresh'] and (not supported or not (recipes(entry) or complete_expansion(entry))
                or any(entry.get(field) for field in ('refine','merge-domains','fallback'))):
            raise Invalid('清单轮换需要明确的完整服务域名来源：'+key)
        if entry['inventory-refresh'] and directory(entry) and entry['expand'].get('versions')!='published':
            raise Invalid('API 端点撤回须核对所有仍公开的版本：'+key)
        retention=entry.get('inventory-retention','service')
        if retention not in ('service','published-artifacts'):
            raise Invalid('端点保留方式无效：'+key)
        if retention=='published-artifacts':
            if complete_expansion(entry) or len(recipes(entry))!=1:raise Invalid('发布文件主机必须对应单份版本元数据：'+key)
            recipe=recipes(entry)[0];path=recipe.get('revision-path',())
            if (recipe['format']!='json-service-urls' or not path
                    or any(not isinstance(field,str) or not field or field=='*' for field in path)):
                raise Invalid('已发布文件的主机需要明确的版本字段：'+key)


def revision(recipe,text):
    value=json.loads(text)
    for field in recipe['revision-path']:
        if not isinstance(value,dict) or field not in value:raise Invalid('文件元数据缺少版本字段')
        value=value[field]
    if not isinstance(value,str) or not value or len(value)>128 or value!=value.strip() or any(ord(c)<32 for c in value):
        raise Invalid('文件元数据的版本字段无效')
    return value


def expanded_hosts(key,expanded_rows,shared_hosts):
    if expanded_rows is None or not expanded_rows.get(key):raise Invalid('完整服务清单缺少本轮发现主机：'+key)
    rows=set(expanded_rows[key])
    for row in rows:
        parts=row.split(',') if isinstance(row,str) else []
        if len(parts)!=2 or parts[0]!='DOMAIN' or public_domain_pattern(parts[1])!=row:
            raise Invalid('服务清单只能包含公开的精确主机：'+key)
    if rows!=set(exclude_shared_scopes(rows,shared_hosts)):
        raise Invalid('服务清单不能认领共用请求入口：'+key)
    return rows


def reconcile(entries,previous,candidate,downloaded,prior_report,now,*,shared_hosts=(),expanded_rows=None):
    validate(entries)
    retained={};report={}
    for key,entry in entries.items():
        if not entry.get('inventory-refresh'):continue
        observed=set().union(*(extract_rows(r,downloaded[r['source']],shared_hosts=shared_hosts) for r in recipes(entry)))
        if complete_expansion(entry):observed.update(expanded_hosts(key,expanded_rows,shared_hosts))
        before=prior_report.get(key,{})
        retention=entry.get('inventory-retention','service')
        same=before.get('inputs')==inputs(entry) and before.get('retention','service')==retention
        if retention=='published-artifacts':
            history=dict(before.get('artifact-hosts',{})) if same else {}
            if set(history)!=set(exclude_shared_scopes(history,shared_hosts)):
                raise Invalid('文件主机依据与共享入口边界冲突：'+key)
            if any(not any(covers(actual,row) for actual in previous[key]) for row in history):
                raise Invalid('文件主机依据没有对应到此前规则：'+key)
            recipe=recipes(entry)[0];version=revision(recipe,downloaded[recipe['source']])
            for row in observed:
                history.setdefault(row,{'source':recipe['source'],'revision':version,'first-seen':now})
            retained[key]=sorted(row for row in history if not any(covers(actual,row) for actual in candidate[key]))
            report[key]={'inputs':inputs(entry),'observed':sorted(observed),'retained':[],'retired':[],
                         'first-absent':{},'last-read':now,'state':'current','retention':retention,
                         'artifact-hosts':dict(sorted(history.items()))}
            continue
        known=set(before.get('observed',()))|set(before.get('retained',())) if same else set()
        missing={row for row in previous[key] if row.startswith('DOMAIN,') and row in known
                 and not any(covers(actual,row) for actual in candidate[key])}
        continuous=same and 0<=now-before.get('last-read',-MAX_GAP_SECONDS-1)<=MAX_GAP_SECONDS
        first=before.get('first-absent',{}) if continuous else {}
        since={row:first.get(row,now) for row in missing}
        retired={row for row in missing if now-since[row]>=WAIT_SECONDS}
        held=missing-retired
        retained[key]=sorted(held)
        report[key]={'inputs':inputs(entry),'observed':sorted(observed),'retained':sorted(held),
                     'retired':sorted(retired),'first-absent':{r:since[r] for r in sorted(missing)},
                     'last-read':now,'state':'observing' if held else 'current'}
    return retained,report


def verify_report(entries,data,report,*,shared_hosts=(),expanded_rows=None):
    expected={key for key,entry in entries.items() if entry.get('inventory-refresh')}
    if set(report)!=expected:raise Invalid('服务清单轮换报告与声明不一致')
    for key,state in report.items():
        observed=set(state['observed']);held=set(state['retained']);retired=set(state['retired'])
        if complete_expansion(entries[key]):
            actual=expanded_hosts(key,expanded_rows,shared_hosts)
            if not actual<=observed or not recipes(entries[key]) and actual!=observed:
                raise Invalid('当前服务主机与发现资料不符：'+key)
        if (state['inputs']!=inputs(entries[key]) or not observed or observed&held or observed&retired or held&retired
                or set(state['first-absent'])!=held|retired or type(state['last-read']) is not int
                or state['state']!=('observing' if held else 'current')):
            raise Invalid('服务清单轮换的来源或状态不符：'+key)
        retention=entries[key].get('inventory-retention','service')
        if state.get('retention','service')!=retention:
            raise Invalid('服务清单的端点保留方式不符：'+key)
        artifacts=state.get('artifact-hosts',{})
        if set(artifacts)!=set(exclude_shared_scopes(artifacts,shared_hosts)):
            raise Invalid('文件主机依据不能认领共享入口：'+key)
        if retention=='published-artifacts':
            source=recipes(entries[key])[0]['source']
            if not artifacts or held or retired or not observed<=artifacts.keys():
                raise Invalid('文件主机依据缺失或被误作当前服务撤回：'+key)
            for row,proof in artifacts.items():
                kind,host,*flags=row.split(',')
                if (kind!='DOMAIN' or flags or public_domain_pattern(host)!=row
                        or set(proof)!={'source','revision','first-seen'} or proof['source']!=source
                        or not isinstance(proof['revision'],str) or not proof['revision'] or len(proof['revision'])>128
                        or type(proof['first-seen']) is not int or not 0<=proof['first-seen']<=state['last-read']
                        or not any(covers(actual,row) for actual in data[key])):
                    raise Invalid('文件主机的公开版本依据或规则正文不符：'+key)
        elif artifacts:
            raise Invalid('当前服务清单不能混入文件版本依据：'+key)
        for row in observed|held|retired:
            kind,host,*flags=row.split(',')
            if (flags or kind not in ('DOMAIN','DOMAIN-WILDCARD') or public_domain_pattern(host)!=row
                    or (row in held|retired and kind!='DOMAIN')):
                raise Invalid('服务清单轮换包含无效范围：'+key)
        for row in observed|held:
            if not any(covers(actual,row) for actual in data[key]):
                raise Invalid('服务清单的当前或观察中端点没有对应正文：'+key)
        if any(any(covers(actual,row) for actual in data[key]) for row in retired):
            raise Invalid('已撤回的服务端点仍在规则正文中：'+key)
        if any(type(first) is not int or not 0<=first<=state['last-read']
               for first in state['first-absent'].values()):
            raise Invalid('服务清单的撤回观察时间无效：'+key)
        if (any(state['last-read']-state['first-absent'][r]<WAIT_SECONDS for r in retired)
                or any(state['last-read']-state['first-absent'][r]>=WAIT_SECONDS for r in held)):
            raise Invalid('服务清单的撤回尚未满足观察间隔：'+key)


def routing_cases(data,report):
    cases={}
    for key,state in report.items():
        for row in set(state['observed']+state['retained'])|state.get('artifact-hosts',{}).keys():
            if not row.startswith('DOMAIN,') or not any(covers(actual,row) for actual in data[key]):continue
            host=row.split(',')[1]
            if host in cases and cases[host]!=[key]:raise Invalid('服务资产的归属冲突：'+host)
            cases[host]=[key]
    return cases


def with_cases(config,data,report):
    return merge_cases(config,routing_cases(data,report),'服务清单')
