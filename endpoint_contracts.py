"""Verify independently reviewed public endpoint ownership before publishing."""
from copy import deepcopy
from html import unescape
from rule_inputs import extract_rows, within
import re

import maintain as rules


def _host(name):
    host=name.strip().casefold()
    if host.count('*')>1 or not rules.valid_host(host.replace('*','coverage',1)):
        raise rules.Invalid('不能识别公开端点格式：'+name)
    return host


def apple_table_hosts(text, sections):
    parser=rules.AppleTables()
    parser.feed(text)
    hosts=set()
    for section in sections:
        names={_host(host) for host,_ in parser.rows[section]
               if host.strip().casefold() not in ('host','hosts')}
        if not names:
            raise rules.Invalid('Apple 端点表缺少章节：'+section)
        hosts.update(names)
    return hosts


def claude_table_hosts(text):
    section=re.search(r'(?ms)^## Network access requirements\s*\n(.*?)(?=^## |\Z)',text)
    if not section:
        raise rules.Invalid('没有找到 Claude Code 网络端点表')
    rows=re.search(r'(?m)^\| URL \| Required for \|[^\n]*\n\|[ \t|:-]+\|[^\n]*\n((?:\|[^\n]*\n?)+)',section[1])
    if not rows:
        raise rules.Invalid('Claude Code 端点表格式变了')
    return {_host(line.split('|',2)[1].strip().strip('`')) for line in rows[1].splitlines()}


def declared_hosts(contract):
    required={_host(h) for hosts in contract['routes'].values() for h in hosts}
    shared={_host(h) for h in contract.get('shared',())}
    if not required or sum(map(len,contract['routes'].values()))!=len(required) or required&shared:
        raise rules.Invalid('端点归属为空或重复：'+contract['id'])
    return required,shared


def _mentioned(text, host):
    return re.search(r'(?<![\w.*-])'+re.escape(host)+r'(?![\w.-]*[\w-])',text) is not None


def resolve_additions(contracts, entries, downloaded):
    """Assign new official table entries only when product evidence identifies exactly one owner."""
    resolved = deepcopy(contracts)
    for spec in resolved:
        if not (discover := spec.get('discover')):
            continue
        text = downloaded[spec['source']]
        if spec['format']=='apple-host-table':
            actual=apple_table_hosts(text,spec['sections'])
        elif spec['format']=='claude-code-table':
            actual=claude_table_hosts(text)
        else:
            raise rules.Invalid('只有完整端点表可以自动识别新增主机：'+spec['id'])
        known, shared = declared_hosts(spec)
        extra=actual-known-shared
        assigned={host:owner for owner,hosts in spec['routes'].items() for host in hosts}
        matches={host:set() for host in extra}
        for owner, policy in discover.items():
            if policy=='extract':
                # Only this official document may support the assignment.
                rows=set().union(*(extract_rows(r,text) for r in entries[owner].get('extract',())
                                   if r['source']==spec['source']))
                for row in rows:
                    kind,host=row.split(',',1)
                    if kind!='DOMAIN': continue
                    if host in shared or (host in assigned and assigned[host]!=owner):
                        raise rules.Invalid(f'{host} 官方用途变化：原归属 {assigned.get(host,"共享")}，现符合 {owner}')
                for host in extra:
                    if 'DOMAIN,'+host in rows:
                        matches[host].add(owner)
            else:
                for host in extra:
                    if '*' not in host and within(host,policy['roots']):
                        matches[host].add(owner)
        for host,owners in sorted(matches.items()):
            if len(owners)!=1:
                raise rules.Invalid(spec['id']+' 新端点待归属：'+host)
            spec['routes'][owners.pop()].append(host)
    return resolved


def verify_sources(contracts, downloaded):
    summary={}
    for contract in contracts:
        name=contract['id']
        required,shared=declared_hosts(contract)
        expected=required|shared
        text=downloaded[contract['source']]
        form=contract['format']
        if form=='apple-host-table':
            actual=apple_table_hosts(text,contract['sections'])
        elif form=='claude-code-table':
            actual=claude_table_hosts(text)
        elif form=='named-endpoints':
            body=unescape(text).casefold()
            actual={host for host in expected if _mentioned(body,host)}
        else:
            raise rules.Invalid('未知的端点核对方式：'+form)
        extra=actual-expected
        missing=expected-actual
        if extra or missing:
            detail=[]
            if extra:
                detail.append('待归属：'+', '.join(sorted(extra)))
            if missing:
                detail.append('官方来源已不列出：'+', '.join(sorted(missing)))
            raise rules.Invalid(f'{name} 公开端点变化；'+ '；'.join(detail))
        summary[name]={'mode':'table' if form!='named-endpoints' else 'named',
                       'assigned':len(required),'shared':len(shared)}
    return summary


def _whole_pattern_owner(host, order, data):
    if '*' not in host:
        return rules.first_policy(host,((key,data[key]) for key in order))
    # An exact probe cannot establish coverage of a wildcard. Match the literal
    # wildcard itself or a suffix covering all labels following its wildcard.
    suffix=host.split('*',1)[-1].partition('.')[2]
    for key in order:
        for row in data[key]:
            t,arg,*flags=row.split(',')
            if flags:
                continue
            arg=arg.casefold()
            if (t=='DOMAIN-WILDCARD' and arg==host) or (
                    t=='DOMAIN-SUFFIX' and (suffix==arg or suffix.endswith('.'+arg))):
                return key
    return None


def verify_routes(contracts, entries, order, data, replacements=None):
    replacements=replacements or {}
    for contract in contracts:
        declared_hosts(contract)
        name=contract['id']
        for owner,hosts in contract['routes'].items():
            want=replacements.get(owner,owner)
            for h in hosts:
                actual=_whole_pattern_owner(_host(h),order,data)
                if actual!=want:
                    raise rules.Invalid(f'{name} {h} 应由 {want} 处理，实际：{actual or "未匹配"}')
        guarded=[key for key in order if entries[key]['section'] in contract.get('guard-sections',())]
        for h,reason in contract.get('shared',{}).items():
            if not reason or not guarded:
                raise rules.Invalid(f'{name} 的共享例外缺少理由或限制范围：{h}')
            if owner:=_whole_pattern_owner(_host(h),guarded,data):
                raise rules.Invalid(f'{name} 共享端点 {h} 被专项 {owner} 整段接管')
