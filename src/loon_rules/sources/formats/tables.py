"""Public-source readers: tables. Read data without executing source code."""
import re
from ipaddress import ip_address
from urllib.parse import urlsplit
from loon_rules import domains as domain_scope
from loon_rules.sources.formats.html import HostTables, AppleTables
from loon_rules.rules import Invalid, valid_host
from .common import within, DestinationTables, public_domain_pattern


def domain_column_table(recipe, text):
    headers = recipe['headers']
    column = recipe['column']
    scope = recipe.get('domain-scope', 'listed')
    if (not isinstance(headers, list) or not headers or len(set(headers)) != len(headers)
            or column not in headers or scope not in ('listed', 'domain-and-subdomains')):
        raise Invalid('域名表缺少明确的列和匹配范围')
    table = HostTables()
    table.feed(text)
    rows = table.rows.get(recipe['section'], [])
    if rows.count(headers) != 1:
        raise Invalid('域名表的章节或标题列缺失、重复')
    result = set()
    for cells in rows:
        if cells == headers:
            continue
        if len(cells) != len(headers):
            raise Invalid('域名表的列数发生变化')
        value = cells[headers.index(column)].strip()
        row = public_domain_pattern(value)
        if row is None:
            continue
        if scope == 'domain-and-subdomains':
            if not row.startswith('DOMAIN,'):
                raise Invalid('域名列的整域匹配不接受通配符')
            row = 'DOMAIN-SUFFIX,' + row.split(',')[1]
        result.add(row)
    if not result:
        raise Invalid('域名表没有可归属的公开名称')
    return result


def host_table(text, recipe):
    parser = AppleTables()
    parser.feed(text)
    for section in recipe['sections']:
        records = parser.rows.get(section)
        if not records:
            raise Invalid('来源缺少端点表：' + section)
        for raw, purpose in records:
            host = raw.strip().casefold()
            wildcard = host.startswith('*.')
            host = host[2:] if wildcard else host
            if not valid_host(host):
                continue
            for scope in recipe['select']:
                if wildcard != scope.get('wildcards', False) or within(host, scope.get('exclude', ())):
                    continue
                if not (scope.get('all-exact') and (not wildcard)) and host not in scope.get('exact', ()) and (not within(host, scope.get('roots', ()))):
                    continue
                if scope.get('subdomains-only') and host in scope.get('roots', ()):
                    continue
                desc = purpose.strip().casefold()
                if 'role' in scope and desc not in {s.casefold() for s in scope['role']}:
                    continue
                if 'purpose-contains' in scope and (not any((s.casefold() in desc for s in scope['purpose-contains']))):
                    continue
                yield (('DOMAIN-SUFFIX,' if wildcard else 'DOMAIN,') + host)
                break

def endpoint_sets(recipe, text):
    all_hosts=recipe.get('all-hosts',False)
    if type(all_hosts) is not bool or all_hosts and (recipe.get('roots') or recipe.get('exact')):
        raise Invalid('端点行的全部主机模式须为布尔值，且不能混用名称筛选')
    parser = HostTables()
    parser.feed(text)
    found = set()
    for section in recipe['sections']:
        for cells in parser.rows[section]:
            if not cells[0].isdigit() or (key := int(cells[0])) not in recipe['sets']:
                continue
            if len(cells) != 5:
                raise Invalid('端点表的列发生变化：' + section)
            found.add(key)
            for value in re.split('[,\\s]+', cells[3].strip().casefold()):
                wildcard = value.startswith('*.')
                host = value[2:] if wildcard else value
                if not valid_host(host):
                    continue
                if all_hosts:
                    try:ip_address(host)
                    except ValueError:
                        if row:=public_domain_pattern(value):yield row
                    continue
                if within(host, recipe.get('roots', ())):
                    yield (('DOMAIN-WILDCARD,' if wildcard else 'DOMAIN,') + value)
                elif not wildcard and host in recipe.get('exact', ()):
                    yield ('DOMAIN,' + host)
    if found != set(recipe['sets']):
        raise Invalid('端点表缺少已订阅的行：' + str(sorted(set(recipe['sets']) - found)))

def parse_purpose_host_table(recipe, text):
    table = HostTables()
    table.feed(text)
    rows = table.rows.get(recipe['section'], [])
    if recipe['headers'] not in rows:
        raise Invalid('业务端点表缺少标题列')
    wanted = {s.casefold() for s in recipe['purposes']}
    seen = set()
    result = set()
    for row in rows:
        if len(row) != 2 or row[1].casefold() not in wanted:
            continue
        seen.add(row[1].casefold())
        url = urlsplit(row[0])
        if url.scheme != 'https' or not url.hostname or url.username is not None:
            raise Invalid('业务端点不是公开 HTTPS 名称')
        if valid_host(url.hostname) and within(url.hostname, recipe['roots']):
            result.add('DOMAIN,' + url.hostname)
    if seen != wanted or not result:
        raise Invalid('业务端点表缺少已选用途')
    return result

def parse_service_domain_table(recipe, text):
    table = HostTables()
    table.feed(text)
    wanted = {s.casefold() for s in recipe['services']}
    seen = set()
    result = set()
    rows = [r for section in table.rows.values() for r in section]
    if ['Service', 'Subdomain'] not in rows:
        raise Invalid('服务域名表缺少标题列')
    for row in rows:
        if len(row) != 2 or row[0].casefold() not in wanted:
            continue
        seen.add(row[0].casefold())
        for value in re.split('[,\\s]+', row[1].strip()):
            if not value.startswith('*.') or not valid_host(value[2:]):
                raise Invalid('服务域名表不是已确认的托管后缀')
            result.add('DOMAIN-SUFFIX,' + value[2:].casefold())
    if seen != wanted or not result:
        raise Invalid('服务域名表缺少已选服务')
    return result

def parse_destination_table(recipe, text):
    table = DestinationTables()
    table.feed(text)
    if not table.matched:
        raise Invalid('来源缺少主机、端口和用途列')
    return {'DOMAIN,' + host for rows in table.rows.values() for hosts, ports, purpose in rows if recipe['purpose'] in purpose.casefold() and recipe['ports'] == ports.strip() for host in hosts.lower().split() if valid_host(host) and within(host, recipe['roots'])}

def parse_windows_purpose(recipe, text):
    table = HostTables()
    table.feed(text)
    product = purpose = ''
    result = set()
    for cells in table.rows.get(recipe['section'], ()):
        if len(cells) != 4:
            continue
        topic, reason, protocol, host = cells
        if topic:
            product = topic.strip()
            purpose = ''
        if reason:
            purpose = reason.strip().casefold()
        host = host.strip().casefold()
        if product != recipe['product'] or not protocol.strip():
            continue
        if not any((term in purpose for term in recipe['purpose'])):
            continue
        if valid_host(host) and within(host, recipe['roots']):
            result.add('DOMAIN,' + host)
        elif host in recipe.get('documented-wildcards', ()):
            result.add('DOMAIN-SUFFIX,' + host[2:])
    if not result:
        raise Invalid('Windows 官方端点表未找到该业务：' + recipe['product'])
    return result

def parse_endpoint_sets(recipe, text):
    return set(endpoint_sets(recipe, text))

def parse_host_table(recipe, text):
    return set(host_table(text, recipe))


def exclusive_purpose_table(recipe, text):
    table = HostTables()
    table.feed(text)
    wanted = {value.casefold() for value in recipe['purposes']}
    related = wanted | {value.casefold() for value in recipe.get('related-purposes', ())}
    candidates = set()
    associated = set()
    other_uses = set()
    header_seen = False
    for rows in table.rows.values():
        active = False
        for row in rows:
            if row == recipe['headers']:
                active = header_seen = True
                continue
            if not active or len(row) != 3:
                continue
            purpose = next((line.strip().casefold() for line in row[2].splitlines() if line.strip()), '')
            for value in re.split(r'[,\s]+', row[0].strip().casefold()):
                wildcard = value.startswith('*.')
                host = value[2:] if wildcard else value
                try:
                    host = domain_scope.public_host(host)
                except Invalid:
                    if purpose in wanted:
                        raise Invalid('所选业务的主机字段格式变化')
                    continue
                pattern = ('DOMAIN-WILDCARD,' if wildcard else 'DOMAIN,') + (value if wildcard else host)
                if purpose in wanted:
                    candidates.add(pattern)
                elif purpose not in related:
                    other_uses.add(pattern)
                if purpose in related:
                    associated.add(pattern)
    if not header_seen or not candidates:
        raise Invalid('用途表缺少主机列或指定业务')
    if recipe.get('part') == 'shared':
        return {row for row in associated if any(
            domain_scope.covers(other, row) or domain_scope.covers(row, other)
            for other in other_uses)}
    return {row for row in candidates if not any(
        domain_scope.covers(other, row) or domain_scope.covers(row, other)
        for other in other_uses)}


def purpose_url_table(recipe,text):
    parser=HostTables();parser.feed(text)
    rows=parser.rows.get(recipe['section'],[])
    if recipe['headers'] not in rows:raise Invalid('用途 URL 表缺少章节或标题列')
    result=set();seen=set()
    wanted=[p.casefold() for p in recipe['purpose-prefixes']]
    for cells in rows:
        if len(cells)!=len(recipe['headers']):continue
        purpose=cells[1].casefold()
        if not any(purpose.startswith(p) for p in wanted):continue
        seen.add(purpose)
        url=urlsplit(cells[0])
        if (url.scheme not in ('https','wss') or not url.hostname or url.username is not None
                or url.query or url.fragment):raise Invalid('所选用途的地址不是公开 HTTPS 或 WSS 连接')
        if row:=public_domain_pattern(url.hostname):result.add(row)
    if not result or any(not any(p.startswith(required.casefold()) for p in seen)
                         for required in recipe.get('required-prefixes',())):
        raise Invalid('用途 URL 表缺少必需的业务')
    return result
