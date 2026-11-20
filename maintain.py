"""Loon 公共规则匹配、输入检查和本机更新。"""
from collections import defaultdict
from fnmatch import fnmatchcase
from html.parser import HTMLParser
from ipaddress import ip_network
import re
import subprocess
from urllib.parse import urlsplit

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


class HostTables(HTMLParser):
    """Consume host/role cells without preserving editorial text."""
    def __init__(self):
        super().__init__()
        self.section = ''
        self.rows = defaultdict(list)
        self.row = self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag=='br' and self.cell is not None:
            self.cell.append(' ')
        if tag=='h2':
            self.section=dict(attrs).get('id') or ''
        elif tag=='tr':
            self.row=[]
        elif self.row is not None and tag in ('td','th'):
            self.cell=[]

    def handle_data(self, value):
        if self.cell is not None:
            self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(''.join(self.cell).strip())
            self.cell=None
        if tag=='tr' and self.row is not None:
            if self.row:
                self.record(self.row)
            self.row=None


    def record(self,row):
        self.rows[self.section].append(row)


class AppleTables(HostTables):
    def record(self,row):
        if len(row)>=5:
            self.rows[self.section].append((row[0],row[4]))


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


def download(url):
    parts=urlsplit(url)
    if parts.scheme!='https' or not parts.hostname or parts.username or parts.query or parts.fragment:
        raise Invalid('只读取公开 HTTPS 源')
    result=subprocess.run(
        ('curl','-q','-fsSL','--compressed','--proto','=https','--proto-redir','=https','--max-redirs','3',
         '--connect-timeout','8','--max-time','25','--retry','2','--retry-all-errors',
         '--retry-max-time','40','--max-filesize','18000000',
         '-A','Loon/991 CFNetwork/3896.100.1.1.1 Darwin/27.0.0',url),
        capture_output=True,
    )
    if result.returncode:
        raise Invalid(f'上游下载失败（curl {result.returncode}）')
    try:
        return result.stdout.decode('utf-8-sig')
    except UnicodeError as exc:
        raise Invalid('上游正文不是 UTF-8 文本') from exc


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



if __name__=='__main__':
    from library import main
    raise SystemExit(main())
