"""Loon 公共规则匹配、输入检查和本机更新。"""
from collections import defaultdict
from fnmatch import fnmatchcase
from ipaddress import ip_network
import re

IP_TYPES = {'IP-CIDR', 'IP-CIDR6', 'IP-ASN', 'GEOIP'}
TYPES = {
    'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-WILDCARD', 'DOMAIN-KEYWORD',
    'USER-AGENT', 'URL-REGEX', 'PROCESS-NAME',
} | IP_TYPES
FLAGS = {'no-resolve', 'extended-matching'}
HOST = re.compile(r'(?=.{1,253}\Z)(?:[a-zA-Z0-9_](?:[a-zA-Z0-9_-]{0,61}[a-zA-Z0-9_])?\.)+[a-zA-Z0-9_-]{1,63}')
class Invalid(ValueError):
    pass


def valid_host(value):
    try:
        return HOST.fullmatch(value.encode('idna').decode('ascii'))
    except UnicodeError:
        return False


def read_rules(text, kinds=TYPES, flags=FLAGS):
    result = []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip().lstrip('\ufeff')
        if not line or line.startswith(('#',';','//')):
            continue
        line = re.split(r'\s+//\s', line, maxsplit=1)[0].rstrip()
        kind, sep, value = line.partition(',')
        kind, value = kind.strip(), value.strip()
        if not sep or kind not in kinds or not value or any(ord(c) < 32 for c in line):
            raise Invalid(f'第 {n} 行不是已认可的 Loon 规则类型')
        if kind in ('USER-AGENT','URL-REGEX','PROCESS-NAME'):
            # These rule values can contain commas. Do not rewrite regex delimiters.
            if any(x in value for x in ('[Remote Proxy]', '[Mitm]', 'ca-passphrase')):
                raise Invalid(f'第 {n} 行不是规则内容')
            result.append(f'{kind},{value}')
            continue
        arg, *extra = [v.strip() for v in value.split(',')]
        if not arg or any(v not in flags for v in extra):
            raise Invalid(f'第 {n} 行有策略或未认可的参数')
        if kind in ('DOMAIN','DOMAIN-SUFFIX'):
            if not (valid_host(arg) or (kind == 'DOMAIN-SUFFIX' and
                    re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?',arg))):
                raise Invalid(f'第 {n} 行域名无效')
        if kind in ('DOMAIN-KEYWORD','DOMAIN-WILDCARD') and not re.fullmatch(r'[A-Za-z0-9_.?*\[\]-]+',arg):
            raise Invalid(f'第 {n} 行域名匹配表达式无效')
        if kind in ('IP-CIDR','IP-CIDR6'):
            try:
                net = ip_network(arg, strict=False)
            except ValueError as exc:
                raise Invalid(f'第 {n} 行网段无效') from exc
            if '/' not in arg or (net.version == 4) != (kind == 'IP-CIDR'):
                raise Invalid(f'第 {n} 行网段与类型不符')
        if kind == 'IP-ASN' and (not arg.isdecimal() or not (1 <= int(arg) <= 4294967295)):
            raise Invalid(f'第 {n} 行 ASN 无效')
        if kind == 'GEOIP' and not re.fullmatch(r'[A-Za-z]{2}',arg):
            raise Invalid(f'第 {n} 行 GEOIP 国家代码无效')
        result.append(','.join((kind,arg,*extra)))
    if not result:
        raise Invalid('没有规则正文')
    return list(dict.fromkeys(result))


def aligned_network(row):
    kind,value,*_=row.split(',')
    if kind not in ('IP-CIDR','IP-CIDR6'):
        return True
    try:
        ip_network(value,strict=True)
        return True
    except ValueError:
        return False


def ip_options(rows):
    modes = defaultdict(set)
    for row in rows:
        kind, _, value = row.partition(',')
        if kind in IP_TYPES:
            key, *flags = value.split(',')
            modes[f'{kind},{key}'].add('no-resolve' in flags)
    return modes


def verify_ip_options(entry, modes, *, complete=False):
    intent=entry.get('ip-match')
    name=entry.get('id','规则表')
    if intent in ('target-ip','allow-dns'):
        if not modes:
            raise Invalid(f'{name} 声明了 IP 匹配用途，但没有地址规则')
        for rule,actual in modes.items():
            if actual!={intent=='target-ip'}:
                raise Invalid(f'{name} 的 IP 匹配与 {intent} 不符：{rule}')
    elif intent=='per-rule':
        declared=set(entry.get('literal_ips',()))|set(entry.get('dns_required',()))
        if missing:=modes.keys()-declared:
            raise Invalid(f'{name} 的 IP 匹配未声明：{min(missing)}')
    elif intent is not None:
        raise Invalid(f'{name} 的 IP 匹配用途无效：{intent}')
    elif complete and modes:
        if entry.get('mode')!='view':
            raise Invalid(f'{name} 有地址规则，须先声明 IP 匹配用途')
        if conflicted:=next((rule for rule,options in modes.items() if len(options)!=1),None):
            raise Invalid(f'{name} 的合集成员不一致：{conflicted}')
    for field, expected in (('literal_ips',{True}), ('dns_required',{False})):
        for rule in entry.get(field, ()):
            if modes.get(rule) != expected:
                raise Invalid(f'{name} 的 IP 匹配约定不符（{field}）：{rule}')


def reverse_dns_rules(entry):
    """Derive PTR zones from the same address policy; never keep a second subnet list."""
    enabled=entry.get('reverse-dns',False)
    if type(enabled) is not bool:
        raise Invalid('反向解析派生开关须为布尔值')
    if not enabled:return []
    if entry.get('mode')!='compiled' or entry.get('ip-match')!='per-rule':
        raise Invalid('反向解析须使用逐条声明用途的地址范围')
    networks=[*entry.get('dns_required',()),*entry.get('literal_ips',())]
    if not networks:raise Invalid('反向解析没有可派生的地址范围')
    rows=set()
    for row in networks:
        parts=row.split(',')
        if len(parts)!=2 or parts[0] not in ('IP-CIDR','IP-CIDR6'):
            raise Invalid('反向解析只能从无额外参数的网段声明生成')
        try:network=ip_network(parts[1],strict=True)
        except ValueError as exc:raise Invalid('反向解析的网段不是规范前缀') from exc
        if network.prefixlen==0 or (network.version==4)!=(parts[0]=='IP-CIDR'):
            raise Invalid('反向解析不能覆盖全部地址，且地址类型须对应')
        width=8 if network.version==4 else 4
        prefix=((network.prefixlen+width-1)//width)*width
        subnets=network.subnets(new_prefix=prefix) if prefix!=network.prefixlen else [network]
        free=(network.max_prefixlen-prefix)//width
        for subnet in subnets:
            zone='.'.join(subnet.network_address.reverse_pointer.split('.')[free:])
            rows.add('DOMAIN-SUFFIX,'+zone)
    return sorted(rows)








def match_domain(host, row):
    k,p,*_ = row.split(',',2)
    p=p.casefold()
    if k=='DOMAIN':
        return host==p
    if k=='DOMAIN-SUFFIX':
        return host==p or host.endswith('.'+p)
    if k=='DOMAIN-KEYWORD':
        return p in host
    if k=='DOMAIN-WILDCARD':
        return fnmatchcase(host,p)
    return False


def first_policy(host, data):
    for policy, rows in data:
        if any(match_domain(host.casefold(), row) for row in rows):
            return policy
    return None






def verify_routes(data, required, boundaries=()):
    for host,want in required.items():
        got=first_policy(host,data)
        if got!=want:
            raise Invalid(f'路由合同不符: {host} 得到 {got!r}，预期 {want!r}')
    for boundary in boundaries:
        for host in boundary['hosts']:
            got=first_policy(host,data)
            if got in boundary['forbid']:
                raise Invalid(f'共享或无关域名 {host} 被 {got} 误匹配')
