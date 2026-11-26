"""Public-source readers: tables. Read data without executing source code."""
import re
from ipaddress import ip_address
from urllib.parse import urlsplit
from loon_rules import domains as domain_scope
from loon_rules.sources.formats.html import HostTables, AppleTables
from loon_rules import rules
from loon_rules.rules import Invalid, valid_host
from .common import within, DestinationTables, public_domain_pattern


def domain_column_table(recipe, text):
    headers = recipe['headers']
    if ('column' in recipe) == ('columns' in recipe):
        raise Invalid('域名表须选择单列或多列，不能混用')
    columns = [recipe['column']] if 'column' in recipe else recipe['columns']
    scope = recipe.get('domain-scope', 'listed')
    value_format = recipe.get('value-format', 'domain')
    split_values = recipe.get('split-values', False)
    groups = recipe.get('group-rows', [])
    escaped=recipe.get('decode-escaped-wildcards',False)
    tenant_wildcards=recipe.get('allow-tenant-wildcards',False)
    select=recipe.get('select')
    controls=recipe.get('ignore-controls',False)
    bare_addresses=recipe.get('allow-bare-addresses',False)
    other_headers=recipe.get('other-table-headers')
    if (not isinstance(headers, list) or not headers
            or any(not isinstance(value, str) or not value.strip() for value in headers)
            or len(set(headers)) != len(headers)
            or not isinstance(columns, list) or not columns
            or any(not isinstance(value, str) or value not in headers for value in columns)
            or len(set(columns)) != len(columns)
            or not isinstance(groups, list)
            or any(not isinstance(value, str) or not value.strip() for value in groups)
            or len(set(groups)) != len(groups)
            or type(split_values) is not bool
            or scope not in ('listed', 'domain-and-subdomains')
            or type(escaped) is not bool or type(tenant_wildcards) is not bool
            or type(controls) is not bool or type(bare_addresses) is not bool
            or bare_addresses and value_format!='domain-or-url'
            or value_format not in ('domain', 'url', 'domain-or-url')
            or value_format == 'url' and (scope != 'listed' or split_values)):
        raise Invalid('域名表缺少明确的列和匹配范围')
    if select is not None:
        if not isinstance(select,dict) or set(select)-{'roots','exact','purpose-column','purpose-prefixes'}:
            raise Invalid('域名表的产品范围筛选无效')
        for field in ('roots','exact'):
            if field not in select:continue
            values=select[field]
            if (not isinstance(values,list) or any(not isinstance(value,str) or domain_scope.public_host(value)!=value for value in values)):
                raise Invalid('域名表的产品名称筛选无效')
        if 'purpose-prefixes' in select or 'purpose-column' in select:
            prefixes=select.get('purpose-prefixes')
            if (select.get('purpose-column') not in headers or not isinstance(prefixes,list) or not prefixes
                    or any(not isinstance(value,str) or not value.strip() for value in prefixes)):
                raise Invalid('域名表的用途选择缺少标题列或明确前缀')
        if not any(select.get(field) for field in ('roots','exact','purpose-prefixes')):
            raise Invalid('域名表没有实际产品范围选择')
    if other_headers is not None:
        if (not isinstance(other_headers,list) or any(not isinstance(value,list) or not value
                or any(not isinstance(cell,str) or not cell.strip() for cell in value) for value in other_headers)
                or headers in other_headers or len({tuple(value) for value in other_headers})!=len(other_headers)):
            raise Invalid('同章节的其他表格须列出明确且不重复的标题列')
    table = HostTables(ignore_controls=controls)
    table.feed(text)
    if table._table_stack or table.row is not None or table.cell is not None or table.hidden:
        raise Invalid('完整域名表的HTML结构未闭合')
    rows = table.rows.get(recipe['section'], [])
    if other_headers is not None:
        selected=[]
        declared={tuple(value) for value in [headers,*other_headers]}
        seen=set()
        for current in table.tables.get(recipe['section'],[]):
            values=current['rows']
            if current['nested'] or len(values)<2:raise Invalid('完整章节含嵌套表或空表')
            identity=tuple(values[0])
            if identity not in declared or identity in seen:
                raise Invalid('完整章节出现未知或重复用途表格')
            seen.add(identity)
            for cells in values[1:]:
                if values[0]==headers and len(cells)==1 and cells[0] in groups:
                    continue
                if len(cells)!=len(identity) or tuple(cells)==identity:
                    raise Invalid('已声明用途表格的数据列数变化或重复标题')
            if values[0]==headers:selected.append(values)
        if seen!=declared or len(selected)!=1:
            raise Invalid('已声明的完整用途表格缺失或重复')
        rows=selected[0]
    if rows.count(headers) != 1:
        raise Invalid('域名表的章节或标题列缺失、重复')
    result = set()
    purposes={}
    for cells in rows:
        if cells == headers or len(cells) == 1 and cells[0] in groups:
            continue
        if len(cells) != len(headers):
            raise Invalid('域名表的列数发生变化')
        for column in columns:
            cell = cells[headers.index(column)].strip()
            values = re.split(r'[,|\s]+', cell) if split_values else [cell]
            for value in values:
                if escaped and value.startswith('\\*.'):value=value[1:]
                bare=bare_addresses and '://' not in value
                if value_format == 'url' or value_format=='domain-or-url' and ('://' in value or bare):
                    url = urlsplit('//'+value if bare else value)
                    try:port=url.port
                    except ValueError as error:raise Invalid('端点表的端口字段无效') from error
                    if (not bare and url.scheme not in ('https', 'wss') or not url.hostname or url.username is not None
                            or url.query or url.fragment or port is not None and not 1<=port<=65535):
                        raise Invalid('域名表的地址列不是公开主机或 HTTPS/WSS 连接')
                    value = url.hostname
                elif value_format=='domain-or-url':
                    value=value.removesuffix('/')
                row = public_domain_pattern(value)
                if row is None and tenant_wildcards and value.startswith('*.') and value.count('*')==1:
                    tail=domain_scope.public_host(value[2:])
                    suffix,private=domain_scope.current().suffix(tail)
                    if private and tail!=suffix:row='DOMAIN-WILDCARD,*.'+tail
                if row is None:
                    raise Invalid('域名表包含未确认归属的共享托管范围')
                if scope == 'domain-and-subdomains':
                    if not row.startswith('DOMAIN,'):
                        raise Invalid('域名列的整域匹配不接受通配符')
                    row = 'DOMAIN-SUFFIX,' + row.split(',')[1]
                result.add(row)
                if select is not None and select.get('purpose-prefixes'):
                    purpose=' '.join(cells[headers.index(select['purpose-column'])].split()).casefold()
                    purposes.setdefault(row,set()).add(purpose)
    if select is not None:
        result={row for row in result
                if within(domain_scope.fixed_tail(row.split(',')[1]),select.get('roots',()))
                or row.startswith('DOMAIN,') and row.split(',')[1] in select.get('exact',())
                or any(purpose.startswith(prefix.casefold()) for purpose in purposes.get(row,())
                       for prefix in select.get('purpose-prefixes',()))}
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
    purposes = recipe.get('purposes', [])
    prefixes = recipe.get('purpose-prefixes', [])
    if (bool(purposes) == bool(prefixes) or not isinstance(purposes, list)
            or not isinstance(prefixes, list)
            or any(not isinstance(value, str) or not value.strip() for value in purposes + prefixes)):
        raise Invalid('业务端点表需要一组明确用途或用途前缀')
    value_format = recipe.get('value-format', 'url')
    all_exact = recipe.get('all-exact', False)
    if (value_format not in ('url', 'domain') or type(all_exact) is not bool
            or all_exact and recipe.get('roots') or not all_exact and not recipe.get('roots')):
        raise Invalid('业务端点表的主机格式或范围选择无效')
    wanted = {s.casefold() for s in purposes or prefixes}
    seen = set()
    result = set()
    for row in rows:
        if row == recipe['headers']:
            continue
        if len(row) != 2:
            raise Invalid('业务端点表的列数发生变化')
        purpose = row[1].casefold()
        matches = {value for value in wanted if purpose == value or prefixes and
                   re.match(re.escape(value) + r'(?:\s|[:(])', purpose)}
        if not matches:
            continue
        seen.update(matches)
        if value_format == 'url':
            url = urlsplit(row[0])
            if url.scheme != 'https' or not url.hostname or url.username is not None:
                raise Invalid('业务端点不是公开 HTTPS 名称')
            host = url.hostname
        else:
            host = domain_scope.public_host(row[0].strip())
        if valid_host(host) and (all_exact or within(host, recipe['roots'])):
            result.add('DOMAIN,' + host)
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
    complete=recipe.get('require-complete',False)
    all_purposes=recipe.get('all-purposes',False)
    if type(complete) is not bool or type(all_purposes) is not bool:
        raise Invalid('用途表的完整读取开关必须为布尔值')
    tenant_prefixes=recipe.get('allow-tenant-prefixes',False)
    if type(tenant_prefixes) is not bool:raise Invalid('租户前缀开关必须为布尔值')
    result=set();seen=set()
    wanted=[p.casefold() for p in recipe.get('purpose-prefixes',())]
    if not wanted and not all_purposes:raise Invalid('用途表缺少明确的用途选择')
    for cells in rows:
        if cells==recipe['headers']:continue
        if len(cells)!=len(recipe['headers']):
            if complete or all_purposes:raise Invalid('完整用途表出现缺列或额外列')
            continue
        purpose=cells[1].casefold()
        if not all_purposes and not any(purpose.startswith(p) for p in wanted):continue
        seen.add(purpose)
        url=urlsplit(cells[0])
        if (url.scheme not in ('https','wss') or not url.hostname or url.username is not None
                or url.query or url.fragment):raise Invalid('所选用途的地址不是公开 HTTPS 或 WSS 连接')
        row=public_domain_pattern(url.hostname)
        if row is None and tenant_prefixes:
            from loon_rules import domains
            label,separator,parent=url.hostname.partition('.')
            suffix,private=domains.current().suffix(domains.fixed_tail(url.hostname))
            if (separator and private and re.fullmatch(r'[a-z0-9][a-z0-9-]*\*[a-z0-9-]*',label)
                    and rules.valid_host(parent)):
                row='DOMAIN-WILDCARD,'+url.hostname
        if row is None and (complete or all_purposes):
            raise Invalid('完整用途表包含整个共享托管范围，不能静默省略')
        if row:result.add(row)
    if not result or any(not any(p.startswith(required.casefold()) for p in seen)
                         for required in recipe.get('required-prefixes',())):
        raise Invalid('用途 URL 表缺少必需的业务')
    return result
