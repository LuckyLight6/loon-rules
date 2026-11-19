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
ROY = 'https://raw.githubusercontent.com/geekdada/surge-list/master/surgio-snippet/apple.tpl'
APPLE_DOCS = ('https://support.apple.com/en-us/101555', 'https://support.apple.com/en-sg/101555')
ALIBABA = 'https://www.alibabacloud.com/help/en/model-studio/regions-and-endpoints'
ALIBABA_COMPAT = 'https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope'
ALIBABA_SOURCES = (ALIBABA, ALIBABA_COMPAT)
# These are purpose boundaries, not wholesale imports. Unapproved exact
# scopes and broad parent domains never enter the Apple or overseas AI sets.
STORE = re.compile(r'(?:bag|se(?:-edge)?[0-9]*|su|upp)\.itunes\.apple\.com|'
                   r'(?:amp-)?api(?:-[a-z0-9-]+)?\.apps\.apple\.com')
ALI_INTL = re.compile(r'(?:dashscope-(?:intl|us|eu|apac)|coding-intl\.dashscope|'
                      r'(?:cn-hongkong|ap-[a-z0-9-]+|eu-[a-z0-9-]+|us-[a-z0-9-]+)\.dashscope)'
                      r'\.aliyuncs\.com')
OPENAI_ROOTS = {'openai.com','chatgpt.com','oaistatic.com','oaiusercontent.com',
                'oaistatsig.com','sora.com','chatgpt.livekit.cloud'}
OPENAI_HOSTS = {
    'cdn.openaimerge.com', 'chat.openai.com.cdn.cloudflare.net', 'openai-api.arkoselabs.com',
    'openaicom-api-bdcpf8c6d2e9atf6.z01.azurefd.net', 'openaicomproductionae4b.blob.core.windows.net',
    'production-openaicom-storage.azureedge.net', 'openaiapi-site.azureedge.net', 'openaicom.imgix.net',
}
GOOGLE_AI_ROOTS = {'aistudio.google.com','bard.google.com','deepmind.com','deepmind.google',
                   'gemini.google.com','generativeai.google','gemini.gstatic.com','makersuite.google.com',
                   'generativelanguage.googleapis.com','robinfrontend-pa.googleapis.com',
                   'proactivebackend-pa.googleapis.com'}
GOOGLE_AI_HOSTS = {
    'ai.google.dev', 'webchannel-robinfrontend-pa.googleapis.com', 'geminiweb-pa.googleapis.com',
    'cloudcode-pa.googleapis.com','daily-cloudcode-pa.googleapis.com','cloudaicompanion.googleapis.com',
    'alkalimakersuite-pa.clients6.google.com',
}


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


def blocks_added(rule):
    """New broad entries must be reviewed, even if an upstream adds them."""
    kind, key, *_ = rule.split(',')
    if kind == 'DOMAIN-SUFFIX' and '.' not in key:
        return True
    if kind in ('IP-CIDR','IP-CIDR6') and ip_network(key, strict=False).prefixlen <= (8 if kind=='IP-CIDR' else 16):
        return True
    if (kind, key.lower()) in {
        ('IP-CIDR','17.0.0.0/8'), ('IP-ASN','714'), ('DOMAIN-SUFFIX','akadns.net'),
        ('DOMAIN-SUFFIX','cloudflare.com'), ('DOMAIN-SUFFIX','googleapis.com'),
        ('DOMAIN-SUFFIX','amazonaws.com'), ('DOMAIN-SUFFIX','aliyuncs.com'),
        ('DOMAIN-SUFFIX','blob.core.windows.net'), ('DOMAIN-SUFFIX','livekit.cloud'),
        ('DOMAIN-SUFFIX','apple.com'), ('DOMAIN-SUFFIX','itunes.apple.com'),
    }:
        return True
    return kind in ('DOMAIN-KEYWORD','DOMAIN-WILDCARD','URL-REGEX','GEOIP')


def ip_options(rows):
    modes = defaultdict(set)
    for row in rows:
        kind, _, value = row.partition(',')
        if kind in IP_TYPES:
            key, *flags = value.split(',')
            modes[f'{kind},{key}'].add('no-resolve' in flags)
    return modes


def verify_ip_options(entry, modes):
    for field, expected in (('literal_ips',{True}), ('dns_required',{False})):
        for rule in entry.get(field, ()):
            if modes.get(rule) != expected:
                raise Invalid(f'{entry["id"]} 的 IP 匹配约定不符（{field}）：{rule}')


def update_feed(entry, old, text):
    current = read_rules(text, set(entry['kinds']), set(entry['flags']))
    if entry.get('partition'):
        current = ai_partition(current, entry['partition'])
        if not current:
            raise Invalid('专项过滤后没有规则，保留上次通过的版本')
    literal = set(entry.get('literal_ips', ()))
    if literal:
        # The allowlist contains exact, reviewed IP rules, never a whole rule type.
        current = list(dict.fromkeys(
            row+',no-resolve' if ','.join(row.split(',',2)[:2]) in literal
            and 'no-resolve' not in row.split(',')[2:] else row
            for row in current
        ))
    prior_opts, next_opts = ip_options(old), ip_options(current)
    verify_ip_options(entry, next_opts)
    for key in prior_opts.keys() & next_opts.keys():
        if prior_opts[key] != next_opts[key]:
            raise Invalid('上游改变已有规则的 IP 匹配方式，保留旧版：'+key)
    old_rules = set(old)
    new_rules = set(current)
    # Preserve the reviewed file after a gross removal, empty page or big expansion.
    # Real moves/renames can be reviewed and approved without mixing policies.
    if len(old_rules-new_rules) > min(len(old_rules)-1, int(len(old_rules)*0.15)):
        raise Invalid('删除超过 15%，保留上次通过的版本')
    if len(new_rules-old_rules) > max(20, len(old_rules)//4):
        raise Invalid('新增超过常规范围，保留上次通过的版本')
    if any(blocks_added(x) for x in new_rules-old_rules):
        raise Invalid('新增过宽或需人工审查的匹配方式，保留旧版')
    return current


def ai_partition(rows, policy):
    def belongs(host, roots):
        return any(host==root or host.endswith('.'+root) for root in roots)

    result = []
    for row in rows:
        kind, host, *_ = row.split(',')
        target = 'AI-Foreign'
        if kind in ('DOMAIN','DOMAIN-SUFFIX'):
            host = host.casefold()
            exact = kind == 'DOMAIN'
            if belongs(host, OPENAI_ROOTS) or (exact and host in OPENAI_HOSTS):
                target = 'OpenAI'
            elif belongs(host, GOOGLE_AI_ROOTS) or (exact and host in GOOGLE_AI_HOSTS):
                target = 'Gemini'
        if target == policy:
            result.append(row)
    return result


def app_store_rules(text):
    result = set()
    for line in text.splitlines():
        bits = [x.strip() for x in line.split(',')]
        if len(bits) == 3 and bits[0] == 'DOMAIN' and bits[2] == '{{ api_rule }}' and STORE.fullmatch(bits[1]):
            result.add('DOMAIN,'+bits[1])
    if not result:
        raise Invalid('商店模板没有符合审核范围的 API')
    return result


def regional_endpoints(text):
    # Read URL hosts only. Do not match a cloud suffix inside an unrelated host.
    result = set()
    for match in re.finditer(r'https://([a-zA-Z0-9.-]+)',text):
        if ALI_INTL.fullmatch(match[1].lower()):
            result.add('DOMAIN,'+match[1].lower())
    if not result:
        raise Invalid('官方端点文档未给出可识别的国际 API')
    return result


class AppleTables(HTMLParser):
    """Consume host/role cells without preserving editorial text."""
    def __init__(self):
        super().__init__()
        self.section = ''
        self.rows = defaultdict(list)
        self.row = self.cell = None

    def handle_starttag(self, tag, attrs):
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
            if len(self.row)>=5:
                self.rows[self.section].append((self.row[0], self.row[4]))
            self.row=None


def apple_endpoints(text, role):
    parser=AppleTables()
    parser.feed(text)
    bits=set()
    target='appleaccount' if role=='apple-auth' else 'icloud'
    for host, purpose in parser.rows[target]:
        host=host.casefold()
        desc=purpose.casefold()
        if role=='apple-auth':
            if 'apple account authentication' in desc and host.endswith(('.apple.com','.cdn-apple.com')) and valid_host(host):
                bits.add('DOMAIN,'+host)
        elif (desc.startswith('icloud services') or desc=='iwork documents') and host.startswith('*.') and valid_host(host[2:]):
            if re.search(r'(^|\.)(?:icloud(?:-content)?\.com(?:\.cn)?|apzones\.com|apple-cloudkit\.com|apple-livephotoskit\.com|cdn-apple\.com|(?:gc|icloud|iwork)\.apple\.com)$',host[2:]):
                bits.add('DOMAIN-SUFFIX,'+host[2:])
        elif role=='icloud' and host in ('probe.icloud.com','pong.icloud.com','metrics.icloud.com'):
            bits.add('DOMAIN,'+host)
    if not bits:
        raise Invalid('Apple 官方网络说明没有符合审核范围的端点')
    return bits


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
