"""Public-source readers: feeds. Read data without executing source code."""
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit
from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid, read_rules, valid_host
from .common import within


def domain_scope_list(recipe, text):
    narrow = recipe.get('subdomains-as-hosts', False)
    if type(narrow) is not bool:
        raise Invalid('产品主机清单的范围选择必须为布尔值')
    result = set()
    for row in read_rules(text):
        kind, host, *flags = row.split(',')
        if flags or kind not in ('DOMAIN', 'DOMAIN-SUFFIX'):
            raise Invalid('产品域名清单包含未经声明的规则类型或参数')
        host = domain_scope.public_host(host)
        suffixes = domain_scope.current()
        suffix, private = suffixes.suffix(host)
        if host == suffix:
            raise Invalid('公共后缀或共享托管后缀不能作为产品域名')
        if narrow and kind == 'DOMAIN-SUFFIX' and (private or host != suffixes.registrable(host)):
            kind = 'DOMAIN'
        result.add(kind + ',' + host)
    if not result:
        raise Invalid('产品域名清单为空')
    return result


def http_provider_hosts(recipe, text):
    """Read only the HTTP discovery lists, never DNS resolvers or update URLs."""
    sections = set(recipe['sections'])
    hits = {}
    active = None
    for line in text.splitlines():
        if line and (not line.startswith(' ')):
            header = re.match('^- `([A-Z0-9_]+)` ', line)
            active = header[1] if header and header[1] in sections else None
            if active:
                if active in hits:
                    raise Invalid('重复的 HTTP 出口查询清单：' + active)
                hits[active] = set()
        if not active:
            continue
        item = re.fullmatch('  - `([a-z0-9-]+)` using \\[[^\\]]+\\]\\((https://[^\\s()]+)\\)\\s*', line)
        if not item or not (scope := recipe['providers'].get(item[1])):
            continue
        url = urlsplit(item[2])
        host = url.hostname or ''
        if url.netloc != host or not valid_host(host) or url.query or url.fragment or ((url.path or '/') not in scope['paths']):
            continue
        if host in scope.get('exact', ()) or within(host, scope.get('roots', ())):
            hits[active].add('DOMAIN,' + host)
    if set(hits) != sections or not all(hits.values()):
        raise Invalid('HTTP 出口查询清单缺失或为空')
    return set.union(*hits.values())

def parse_openid_discovery(recipe, text):
    doc = json.loads(text)
    if doc.get('issuer') != recipe['issuer']:
        raise Invalid('OpenID 签发方发生变化')
    found = set()
    for field in recipe['fields']:
        url = urlsplit(doc.get(field, ''))
        if url.scheme != 'https' or not url.hostname or url.username is not None:
            raise Invalid('OpenID 端点无效：' + field)
        if within(url.hostname, recipe['roots']) and url.hostname not in recipe['exclude']:
            found.add('DOMAIN,' + url.hostname)
    return found

def parse_mail_autoconfig(recipe, text):
    found = set()
    for provider in ET.fromstring(text).findall('emailProvider'):
        if recipe['domain'] not in [x.text for x in provider.findall('domain')]:
            continue
        for role, proto in [('incomingServer', 'imap'), ('incomingServer', 'pop3'), ('outgoingServer', 'smtp')]:
            for server in provider.findall(role):
                host = server.findtext('hostname', '').strip().lower()
                if server.get('type') == proto and valid_host(host) and within(host, recipe['roots']):
                    found.add('DOMAIN,' + host)
    return found

def parse_http_provider_lists(recipe, text):
    return http_provider_hosts(recipe, text)

def parse_rules(recipe, text):
    exact = set(recipe['exact'])
    return {f'DOMAIN,{host}' for row in read_rules(text) for kind, host, *flags in [row.split(',')] if kind in ('DOMAIN', 'DOMAIN-SUFFIX') and (not flags) and (host in exact)}

def parse_annotated_domains(recipe, text):
    pattern = re.compile(recipe['host-pattern'])
    return {'DOMAIN,' + parts[1] for line in text.splitlines() for parts in [[v.strip() for v in line.split(',')]] if len(parts) == 3 and parts[0] == 'DOMAIN' and (parts[2] == recipe['tag']) and valid_host(parts[1]) and pattern.fullmatch(parts[1])}

def parse_https_hosts(recipe, text):
    roots = set(recipe.get('workspace-roots', ()))
    exact = set(recipe.get('exact', ()))
    found = set()
    for match in re.finditer('https://([^/\\s"\'<>?#\\\\]+)', text):
        authority = match[1]
        if '@' in authority:
            continue
        try:
            host = urlsplit('https://' + authority).hostname
        except ValueError:
            continue
        if not host:
            continue
        if host in exact:
            found.add('DOMAIN,' + host)
        parts = host.split('.', 1)
        for root in (host, parts[1] if len(parts) > 1 else ''):
            if root in roots and (host == root or valid_host(host) or parts[0] in ('{workspaceid}', '{workspace-id}')):
                found.add('DOMAIN-SUFFIX,' + root)
    return found

def parse_named_hosts(recipe, text):
    return {'DOMAIN,' + host for host in recipe['exact'] if re.search('(?<![\\w.-])' + re.escape(host) + '(?![\\w-]|\\.[\\w-])', text, re.I)}
