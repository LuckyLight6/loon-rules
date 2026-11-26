"""Add officially documented shared scopes to alternative service bundles."""
import hashlib
import re

from loon_rules import domains, rules
from loon_rules.matching import RuleIndex
from loon_rules.sources.inputs import extract_rows
from loon_rules.sources.transport import source_url
from loon_rules.generation.membership import compact
from loon_rules.policy import SHARED_PARENT,overbroad


def validate(entries):
    for key,entry in entries.items():
        if 'dependency-inputs' not in entry:
            continue
        recipes=entry['dependency-inputs']
        if entry['mode']!='view' or not isinstance(recipes,list) or not recipes:
            raise rules.Invalid('官方共享依赖只能用于明确的替代合集：'+key)
        for recipe in recipes:
            if (not isinstance(recipe,dict) or recipe.get('format') not in
                    ('purpose-domain-lists','purpose-url-table')
                    or type(recipe.get('protect-from-reject',False)) is not bool):
                raise rules.Invalid('服务依赖缺少官方用途清单：'+key)
            source_url(recipe['source'])


def read(entries,downloaded):
    report={}
    for key,entry in entries.items():
        if not entry.get('dependency-inputs'):
            continue
        records=[]
        for recipe in entry['dependency-inputs']:
            text=downloaded[recipe['source']]
            rows=sorted(extract_rows({**recipe,'require-complete':True},text))
            records.append({'recipe':recipe,'complete':True,'sha256':hashlib.sha256(text.encode()).hexdigest(),'rules':rows})
        report[key]={'inputs':records}
    return report


def attach(config,entries,data,report):
    expected={key for key,entry in entries.items() if entry.get('dependency-inputs')}
    if set(report)!=expected:
        raise rules.Invalid('服务依赖记录缺失或多出')
    from loon_rules.generation.ordering import route_order
    order=route_order(config,entries)
    index=RuleIndex(data,order)
    for key in expected:
        entry=entries[key];record=report[key]
        inputs=record.get('inputs')
        if not isinstance(inputs,list) or [item.get('recipe') for item in inputs]!=entry['dependency-inputs']:
            raise rules.Invalid('服务依赖的来源用途与声明不一致：'+key)
        rows=[];sources={}
        for item in inputs:
            if (item.get('complete') is not True or not re.fullmatch('[0-9a-f]{64}',item.get('sha256',''))
                    or not isinstance(item.get('rules'),list) or not item['rules']
                    or rules.read_rules('\n'.join(item['rules']))!=item['rules']):
                raise rules.Invalid('服务依赖缺少完整正文范围或指纹：'+key)
            for row in item['rules']:
                kind,host,*flags=row.split(',')
                if (flags or kind not in ('DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD')
                        or host in SHARED_PARENT or overbroad(kind,host,set())):
                    raise rules.Invalid('服务依赖包含未确认类型或整个共享平台：'+key)
                sources.setdefault(row,[]).append(item['recipe']['source'])
            rows.extend(item['rules'])
        owners={}
        for row in rows:
            matching=index.scope_bits(row)
            owner=next((candidate for candidate in order if matching&index.bits[candidate]),None)
            if owner is not None and entries[owner].get('policy-hint')=='reject':
                raise rules.Invalid('官方共享依赖仍被常规拒绝表覆盖：'+key+' '+row)
            owners[row]=owner
        entries[key]=dict(entry,**{'_dependency-scopes':compact(rows),
            '_dependency-owners':owners,'_dependency-sources':sources})


def permits_shadow(entries,view,row,owner):
    entry=entries[view]
    targets={owner}|set(entries[owner].get('members',()))
    return entry.get('mode')=='view' and any(target in targets and domains.covers(scope,row)
        for scope,target in entry.get('_dependency-owners',{}).items())


def documented(entry,row,*,source=None):
    return any((source is None or source in sources) and domains.covers(scope,row)
               for scope,sources in entry.get('_dependency-sources',{}).items())


def outside(rows,required):
    if not required:
        return rows
    return [row for row in rows if not any(domains.covers(row,scope) or domains.covers(scope,row)
                                          for scope in required)]
