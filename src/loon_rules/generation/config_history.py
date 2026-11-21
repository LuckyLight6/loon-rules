"""Preserve proven publisher-owned endpoints from incomplete client configurations."""
from copy import deepcopy
from datetime import datetime,timezone
from urllib.parse import urlsplit

from loon_rules import domains
from loon_rules.matching import RuleIndex,merge_cases
from loon_rules.rules import Invalid,match_domain,read_rules
from loon_rules.sources import bags,profiles
from loon_rules.sources.transport import source_url


READERS={bags.METHOD:bags,profiles.METHOD:profiles}


def selection(spec):
    READERS[spec['method']].validate(spec)
    return deepcopy({field:spec[field] for field in ('method','source','config-source','document') if field in spec})


def observed(record):
    return {row:doc['source'] for doc in reversed(record['documents']) for row in doc['rows']}


def epoch(value):
    try:return int(datetime.strptime(value,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp())
    except (TypeError,ValueError) as error:raise Invalid('配置端点依据缺少有效的采纳时间') from error


def publisher(spec):
    return spec.get('config-source',spec['source'])


def owned(spec,row):
    kind,host,*flags=row.split(',')
    if kind!='DOMAIN' or flags or read_rules(row)!=[row] or domains.public_host(host)!=host:
        raise Invalid('配置历史只允许明确的公网主机')
    return domains.current().registrable(host)==domains.current().registrable(urlsplit(publisher(spec)).hostname)


def excluded(key,row,negatives):
    return any(key in owners and match_domain(host,row) for host,owners in negatives.items())


def witness(spec,row,proof,checked_at,shared_hosts):
    if not isinstance(proof,dict) or set(proof)!={'source','accepted-at'} or not owned(spec,row):
        raise Invalid('配置历史缺少发布方域名内的精确主机及用途依据')
    source=proof['source']
    if not isinstance(source,str):raise Invalid('配置历史缺少公开来源')
    if spec['method']==profiles.METHOD:
        source_url(source,public_profile=True)
        if urlsplit(source)._replace(query='').geturl()!=spec['config-source']:
            raise Invalid('历史客户端配置与当前发布入口不同')
    else:
        source_url(source,public_bag=True)
        if source!=spec['source']:raise Invalid('历史服务配置与当前公开索引不同')
    if not 0<=epoch(proof['accepted-at'])<=epoch(checked_at):raise Invalid('配置历史的采纳时间晚于本轮检查')
    for host in shared_hosts:
        ref=('DOMAIN-WILDCARD,' if any(c in host for c in '*?[') else 'DOMAIN,')+host
        if domains.covers(ref,row) or domains.covers(row,ref):raise Invalid('配置历史与当前共享主机边界冲突')


def reconcile(entries,published,current,expanded,previous,*,checked_at,shared_hosts=(),negatives=None):
    retained={};report={};negatives=negatives or {}
    for key,entry in entries.items():
        spec=entry.get('expand',{})
        if spec.get('method') not in READERS:continue
        before=previous.get('expanded-inputs',{}).get(key)
        history=previous.get('config-endpoint-history',{}).get(key,{})
        if not before:
            if history:raise Invalid('配置历史没有对应的上一轮来源快照')
            continue
        if before.get('method') not in READERS:continue
        old_spec={'method':before['method'],**before['selection']}
        READERS[old_spec['method']].verify(old_spec,before)
        if selection(old_spec)!=selection(spec):continue
        known={row:{'source':source,'accepted-at':previous['checked-at']} for row,source in observed(before).items()
               if owned(spec,row)}
        if history:
            if (not isinstance(history,dict) or set(history)!={'inputs','retained'}
                    or history['inputs']!=selection(spec) or not isinstance(history['retained'],dict)):
                raise Invalid('配置历史的用途选择与原来源不一致')
            if set(known)&set(history['retained']):raise Invalid('配置历史与上一轮当前主机重复')
            known.update(history['retained'])
        missing={}
        for row,proof in known.items():
            if excluded(key,row,negatives):continue
            witness(spec,row,proof,checked_at,shared_hosts)
            if not any(domains.covers(actual,row) for actual in published[key]):
                raise Invalid('配置历史没有对应的已发布范围：'+key)
            if row not in observed(expanded[key]):missing[row]=proof
        if missing:
            report[key]={'inputs':selection(spec),'retained':dict(sorted(missing.items()))}
            retained[key]=[row for row in missing if not any(domains.covers(actual,row) for actual in current[key])]
    return retained,report


def verify_report(entries,data,expanded,history,*,checked_at,shared_hosts=(),negatives=None,order):
    index=RuleIndex(data,order);negatives=negatives or {}
    if not isinstance(history,dict):raise Invalid('配置历史报告不是业务映射')
    for key,state in history.items():
        spec=entries.get(key,{}).get('expand',{})
        if (spec.get('method') not in READERS or key not in expanded or key not in index.bits
                or not isinstance(state,dict) or set(state)!={'inputs','retained'}
                or state['inputs']!=selection(spec) or not isinstance(state['retained'],dict) or not state['retained']):
            raise Invalid('配置历史报告与业务来源不一致')
        now=observed(expanded[key])
        for row,proof in state['retained'].items():
            witness(spec,row,proof,checked_at,shared_hosts)
            if row in now or excluded(key,row,negatives):raise Invalid('当前或已排除的主机不能列作历史保留')
            if (not any(domains.covers(actual,row) for actual in data[key])
                    or index.route(row.split(',')[1],order)!=key):
                raise Invalid('配置历史与当前正文或实际归属不一致：'+key)


def with_cases(config,data,history):
    cases={}
    for key,state in history.items():
        for row in state['retained']:
            if not any(domains.covers(actual,row) for actual in data[key]):raise Invalid('配置历史主机缺少对应正文')
            host=row.split(',')[1]
            if host in cases and cases[host]!=[key]:raise Invalid('配置历史存在跨产品归属冲突')
            cases[host]=[key]
    return merge_cases(config,cases,'配置历史')
