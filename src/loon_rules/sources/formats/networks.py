"""Public-source readers: networks. Read data without executing source code."""
from ipaddress import ip_address, ip_network
import json
import re
from loon_rules.sources.formats.html import HostTables
from loon_rules.rules import Invalid, valid_host
from .common import within, LabelledLists, HeadingSectionText, PurposeFragments


def rdap_entity_autnums(recipe, text):
    identity = recipe.get('registrant-id')
    name = recipe.get('registrant-name')
    if not isinstance(identity, str) or not identity.strip() or not isinstance(name, str) or not name.strip():
        raise Invalid('ASN 组织来源缺少注册身份')
    try:
        record = json.loads(text)
    except ValueError as error:
        raise Invalid('ASN 组织记录不是有效 JSON') from error
    if not isinstance(record, dict) or record.get('objectClassName') != 'entity' or record.get('handle') != identity:
        raise Invalid('ASN 组织记录身份与声明不符')
    card = record.get('vcardArray')
    if not isinstance(card, list) or len(card) != 2 or card[0] != 'vcard' or not isinstance(card[1], list):
        raise Invalid('ASN 组织记录缺少注册名称')
    names = [field[3] for field in card[1] if isinstance(field, list) and len(field) == 4
             and field[0] == 'fn' and isinstance(field[3], str)]
    if len(names) != 1 or ' '.join(names[0].split()).casefold() != ' '.join(name.split()).casefold():
        raise Invalid('ASN 组织注册名称与声明不符')
    notices = json.dumps(record.get('notices', []), ensure_ascii=False).casefold()
    if 'truncat' in notices or any(link.get('rel') == 'next' for link in record.get('links', []) if isinstance(link, dict)):
        raise Invalid('ASN 组织记录不完整，不能按部分结果更新')
    autnums = record.get('autnums')
    if not isinstance(autnums, list) or not autnums:
        raise Invalid('ASN 组织记录缺少完整的自治系统列表')
    result = set()
    for item in autnums:
        if not isinstance(item, dict):
            raise Invalid('ASN 组织记录含有无效成员')
        number = item.get('startAutnum')
        if (type(number) is not int or not 1 <= number < 4294967295
                or number == 23456 or 64512 <= number <= 65535 or number >= 4200000000
                or type(item.get('endAutnum')) is not int or item['endAutnum'] != number or item.get('objectClassName') != 'autnum'
                or item.get('handle') != 'AS'+str(number) or item.get('status') != ['active']):
            raise Invalid('ASN 组织列表含有范围、保留编号或非活动记录')
        row = 'IP-ASN,'+str(number)+',no-resolve'
        if row in result:
            raise Invalid('ASN 组织列表包含重复成员')
        result.add(row)
    return result


def rdap_autnum(recipe, text):
    asn = recipe.get('asn')
    owners = recipe.get('registrant-ids')
    name = recipe.get('registrant-name')
    if (type(asn) is not int or not 1 <= asn <= 4294967295
            or not isinstance(owners, list) or not owners
            or any(not isinstance(owner, str) or not owner.strip() for owner in owners)
            or not isinstance(name, str) or not name.strip()):
        raise Invalid('ASN 来源声明缺少编号或注册持有人')
    try:
        record = json.loads(text)
    except ValueError as error:
        raise Invalid('ASN 记录不是有效 JSON') from error
    if (not isinstance(record, dict) or record.get('objectClassName') != 'autnum'
            or any(type(record.get(field)) is not int or record[field] != asn
                   for field in ('startAutnum', 'endAutnum'))
            or record.get('handle') != 'AS' + str(asn)):
        raise Invalid('ASN 记录身份与声明不符')
    entities = record.get('entities')
    if isinstance(entities, list):
        for entity in entities:
            if not isinstance(entity, dict) or entity.get('handle') not in owners:
                continue
            roles = entity.get('roles')
            if not isinstance(roles, list) or 'registrant' not in roles:
                continue
            card = entity.get('vcardArray')
            if (not isinstance(card, list) or len(card) != 2 or card[0] != 'vcard'
                    or not isinstance(card[1], list)):
                continue
            names = [field[3] for field in card[1] if isinstance(field, list) and len(field) == 4
                     and field[0] == 'fn' and isinstance(field[3], str)]
            if any(' '.join(value.split()).casefold() == ' '.join(name.split()).casefold()
                   for value in names):
                return {'IP-ASN,' + str(asn) + ',no-resolve'}
    raise Invalid('ASN 注册持有人与声明不符')


def service_address_table(recipe, text):
    class AddressTables(HostTables):
        def handle_starttag(self, tag, attrs):
            if tag == 'br' and self.cell is not None and not self.hidden:
                self.cell.append(' ')
            super().handle_starttag(tag, attrs)

    table = AddressTables()
    table.feed(text)
    rows = table.rows.get(recipe['section'], [])
    columns = recipe['columns']
    if (not rows or rows[0] != list(columns) or len(rows) < 2
            or set(columns.values()) != {4, 6}):
        raise Invalid('服务地址表缺少指定章节、列头或地址族')
    result = set()
    families = set()
    for row in rows[1:]:
        if len(row) != len(columns):
            raise Invalid('服务地址表的列数变化')
        for value, family in zip(row, columns.values()):
            for field in value.split():
                try:
                    address = ip_address(field)
                except ValueError as exc:
                    raise Invalid('服务地址字段不是单个 IP') from exc
                if address.version != family or not address.is_global:
                    raise Invalid('服务地址不是对应地址族的公网 IP')
                kind = 'IP-CIDR' if family == 4 else 'IP-CIDR6'
                result.add(f'{kind},{address}/{address.max_prefixlen},no-resolve')
                families.add(family)
    if families != {4, 6}:
        raise Invalid('服务地址表缺少完整地址族')
    return result

def labelled_networks(recipe, text):
    parser = LabelledLists(recipe['lists'])
    parser.feed(text)
    for title, bounds in recipe['lists'].items():
        if not parser.rows.get(title):
            raise Invalid('缺少地址清单：' + title)
        parents = [ip_network(p) for p in bounds['parents']]
        for value in parser.rows[title]:
            try:
                net = ip_network(value)
            except ValueError as exc:
                raise Invalid('地址格式变化：' + title) from exc
            if '/' not in value or net.version != bounds['family'] or (not net.is_global) or (net.prefixlen < bounds['min-prefix']) or (not any((net.subnet_of(p) for p in parents))):
                raise Invalid('地址超出已确认的发布范围：' + title)
            yield (('IP-CIDR,' if net.version == 4 else 'IP-CIDR6,') + str(net) + ',no-resolve')

def public_media_network(value, recipe):
    try:
        net = ip_network(value, strict=True)
    except ValueError as exc:
        raise Invalid('服务地址不是对齐的 CIDR') from exc
    if not net.is_global or net.prefixlen < recipe['min-prefix'][str(net.version)]:
        raise Invalid('服务地址超过已确认范围')
    return (('IP-CIDR,' if net.version == 4 else 'IP-CIDR6,') + str(net) + ',no-resolve', net.version)


def section_network_blocks(recipe, text):
    families = recipe.get('families')
    if (not isinstance(families, list) or not families
            or any(type(family) is not int or family not in (4, 6) for family in families)
            or len(set(families)) != len(families)):
        raise Invalid('地址章节缺少明确的地址族')
    section = HeadingSectionText(recipe['section'])
    section.feed(text)
    if section.found != 1 or not section.examples:
        raise Invalid('地址章节缺失、重复或没有 CIDR 字段')
    result = set()
    observed = set()
    for block in section.examples:
        for value in block.split():
            if '/' not in value:
                raise Invalid('地址章节包含未声明掩码的字段')
            row, family = public_media_network(value, recipe)
            result.add(row)
            observed.add(family)
    if observed != set(families):
        raise Invalid('地址章节的地址族与声明不符')
    return result


def parse_section_media_networks(recipe, text):
    section = HeadingSectionText(recipe['section'])
    section.feed(text)
    if section.found != 1:
        raise Invalid('媒体地址章节缺失或重复')
    result = set()
    families = set()
    snis = set()
    for line in ''.join(section.text).splitlines():
        if (m := re.fullmatch('\\s*IPv([46]):\\s*(.+?)\\s*', line)):
            for value in re.split('[,\\s]+', m[2]):
                row, family = public_media_network(value, recipe)
                if family != int(m[1]):
                    raise Invalid('媒体地址与标注的地址族不符')
                result.add(row)
                families.add(family)
        elif (m := re.fullmatch('\\s*SNI:\\s*(.+?)\\s*', line)):
            for host in re.split('[,\\s]+', m[1]):
                if not valid_host(host) or not within(host, recipe['sni-roots']):
                    raise Invalid('媒体 SNI 超过已确认范围')
                snis.add('DOMAIN,' + host)
    if families != {4, 6} or not snis:
        raise Invalid('媒体章节缺少地址族或 SNI')
    return result | snis

def parse_endpoint_network_sets(recipe, text):
    table = HostTables()
    table.feed(text)
    seen = set()
    families = set()
    result = set()
    for section in recipe['sections']:
        for row in table.rows.get(section, []):
            if not row[0].isdigit() or int(row[0]) not in recipe['sets']:
                continue
            if len(row) != 5 or row[1] != recipe['category'] or 'UDP:' not in row[4] or (not re.search('(?<!\\d)' + str(recipe['udp-port']) + '(?!\\d)', row[4])):
                raise Invalid('通信地址的分类或端口发生变化')
            seen.add(int(row[0]))
            for value in re.split('[,\\s]+', row[3].strip()):
                if '/' not in value:
                    continue
                rule, family = public_media_network(value, recipe)
                result.add(rule)
                families.add(family)
    if seen != set(recipe['sets']) or families != {4, 6}:
        raise Invalid('通信地址表缺少行或地址族')
    return result

def parse_ip_prefix_json(recipe, text):
    doc = json.loads(text)
    records = doc.get('prefixes') if isinstance(doc, dict) else None
    fields = recipe['fields']
    if not isinstance(records, list) or not records:
        raise Invalid('官方地址清单为空或格式变化')
    result = set()
    for record in records:
        if not isinstance(record, dict) or len(record) != 1 or (not set(record) <= fields.keys()):
            raise Invalid('官方地址字段变化')
        field, value = next(iter(record.items()))
        try:
            if not isinstance(value, str) or '/' not in value:
                raise ValueError()
            net = ip_network(value, strict=True)
        except ValueError as exc:
            raise Invalid('官方地址格式无效') from exc
        if net.version != fields[field] or not net.is_global or net.prefixlen != net.max_prefixlen:
            raise Invalid('官方单地址清单出现其他地址族、非公网地址或宽网段')
        result.add(('IP-CIDR,' if net.version == 4 else 'IP-CIDR6,') + str(net) + ',no-resolve')
    return result

def parse_labelled_networks(recipe, text):
    return set(labelled_networks(recipe, text))


def ip_network_map(recipe,text):
    fields=recipe.get('fields')
    limits=recipe.get('min-prefix')
    if (not isinstance(fields,dict) or not fields or not isinstance(limits,dict)
            or any(not isinstance(name,str) or not name or type(family) is not int or family not in (4,6)
                   for name,family in fields.items())
            or any(type(limits.get(str(family))) is not int or not 1<=limits[str(family)]<=(32 if family==4 else 128)
                   for family in fields.values())):
        raise Invalid('网段映射缺少明确的字段、地址族或最小前缀')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise Invalid('网段映射包含重复字段')
            result[key]=value
        return result
    document=json.loads(text,object_pairs_hook=unique)
    if not isinstance(document,dict) or set(document)!=set(fields):
        raise Invalid('网段映射的字段缺失或变化')
    result=set()
    for field,family in fields.items():
        values=document[field]
        if not isinstance(values,list) or not values or any(not isinstance(value,str) for value in values):
            raise Invalid('网段映射的地址族列表为空或无效')
        for value in values:
            row,version=public_media_network(value,recipe)
            if version!=family:raise Invalid('网段映射的地址族与字段不符')
            if row in result:raise Invalid('网段映射包含重复范围')
            result.add(row)
    return result


def paragraph_network_list(recipe,text):
    prefix=recipe.get('prefix');until=recipe.get('until')
    if not isinstance(prefix,str) or not prefix.strip() or not isinstance(until,str) or not until.strip():
        raise Invalid('地址用途说明缺少明确的起止文字')
    parser=PurposeFragments();parser.feed(text)
    result=set();found=0
    for raw in parser.paragraphs:
        paragraph=' '.join(raw.split())
        if not paragraph.casefold().startswith(prefix.casefold()):continue
        field,separator,_=paragraph[len(prefix):].partition(until)
        if not separator:raise Invalid('地址用途说明的字段结束标记缺失')
        values=re.split(r'[,\s]+',field.strip().removesuffix('.'))
        if not values:raise Invalid('地址用途说明没有完整地址')
        for value in values:
            if '/' not in value:raise Invalid('地址用途说明包含未知字段或无掩码地址')
            row,_=public_media_network(value,recipe)
            result.add(row)
        found+=1
    if not found or not result:raise Invalid('明确的地址用途说明缺失')
    return result


def network_table_options(recipe):
    section=recipe.get('section');headers=recipe.get('headers');column=recipe.get('column')
    families=recipe.get('families');limits=recipe.get('min-prefix')
    form=recipe.get('document-format','html');heading=recipe.get('section-heading')
    if (not isinstance(section,str) or not re.fullmatch(r'[a-z][a-z0-9-]*',section)
            or not isinstance(headers,list) or not headers
            or any(not isinstance(value,str) or not value.strip() for value in headers)
            or len(headers)!=len(set(headers))
            or column not in headers or form not in ('html','markdown')
            or not isinstance(families,list) or not families
            or any(type(family) is not int or family not in (4,6) for family in families)
            or len(set(families))!=len(families) or not isinstance(limits,dict)):
        raise Invalid('用途网段表缺少明确章节、列或地址族')
    for family in families:
        if type(limits.get(str(family))) is not int or not 1<=limits[str(family)]<=(32 if family==4 else 128):
            raise Invalid('用途网段表缺少对应地址族的最宽前缀')
    if form=='markdown' and (not isinstance(heading,str) or not heading.strip()):
        raise Invalid('原始文档的用途网段表缺少明确标题')
    if form=='html' and heading is not None:
        raise Invalid('HTML用途网段表须使用章节身份')
    return section,headers,column,families,form,heading


class NetworkRegionTables(HostTables):
    """Keep every declared region and reject addresses outside its tables."""
    def __init__(self, section):
        super().__init__(ignore_controls=True)
        self.target_section = section
        self.regions = {}
        self.region = None
        self.heading = None
        self.outside = []

    def handle_starttag(self, tag, attrs):
        if not self.hidden and self.section == self.target_section:
            if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                if self.heading is not None or self._table_stack:
                    raise Invalid('用途地区标题未闭合或嵌入网段表')
                if tag in ('h4', 'h5', 'h6'):
                    raise Invalid('用途地区的标题层级尚未确认')
            if tag in ('h1', 'h2'):
                self.region = None
        if tag == 'h1' and not self.hidden:
            self.section = ''
        super().handle_starttag(tag, attrs)
        if self.hidden or self.section != self.target_section:
            return
        if tag == 'h3':
            self.heading = []
        elif tag == 'table':
            if self.heading is not None or self.region is None:
                raise Invalid('用途网段表没有完整地区标题')
            self.regions[self.region].append(self._table_stack[-1])

    def handle_data(self, value):
        super().handle_data(value)
        if self.hidden or self.section != self.target_section:
            return
        if self.heading is not None:
            self.heading.append(value)
        elif not self._table_stack:
            self.outside.append(value)

    def handle_endtag(self, tag):
        if tag == 'h3' and not self.hidden and self.section == self.target_section:
            if self.heading is None:
                raise Invalid('用途地区标题结构不完整')
            name = ' '.join(''.join(self.heading).split()).casefold()
            if not name or name in self.regions:
                raise Invalid('用途地区名称缺失或重复')
            self.regions[name] = []
            self.region = name
            self.outside.extend(self.heading)
            self.heading = None
        super().handle_endtag(tag)

    def complete(self):
        if (self._table_stack or self.row is not None or self.cell is not None
                or self.hidden or self.heading is not None):
            raise Invalid('用途网段表的HTML结构未闭合')
        if not self.regions or any(not tables for tables in self.regions.values()):
            raise Invalid('用途章节含没有完整网段表的地区')
        outside = ''.join(self.outside)
        if re.search(r'(?:\d{1,3}\.){3}\d{1,3}|(?:[0-9a-f]{0,4}:){2,}[0-9a-f:.]*|/\d{1,3}', outside, re.I):
            raise Invalid('用途章节的表格外出现未完整处理的地址')


def network_column_details(recipe, text):
    """Validate every region and purpose before selecting a destination role."""
    section, headers, column, families, form, heading = network_table_options(recipe)
    if form == 'markdown':
        from markdown_it import MarkdownIt
        parser = MarkdownIt('commonmark').enable('table')
        tokens = parser.parse(text)
        matches = [index for index, token in enumerate(tokens)
                   if token.type == 'heading_open' and token.tag == 'h2' and index + 2 < len(tokens)
                   and tokens[index + 1].type == 'inline' and tokens[index + 1].content == heading
                   and tokens[index + 2].type == 'heading_close']
        if len(matches) != 1:
            raise Invalid('原始文档的用途章节缺失或重复')
        start = matches[0] + 3
        end = next((index for index in range(start, len(tokens))
                    if tokens[index].type == 'heading_open' and tokens[index].tag in ('h1', 'h2')), len(tokens))
        lines = text.splitlines()
        for token in tokens[start:end]:
            if token.type != 'table_open':
                continue
            # Markdown rendering pads short rows and drops excess cells. Validate
            # the source rows first so an unknown address column cannot disappear.
            for number in range(*token.map):
                raw = lines[number].strip()
                if '\\' in raw:
                    raise Invalid('用途Markdown表含尚未确认的转义')
                cells = raw.split('|')
                if not cells[0].strip():
                    cells = cells[1:]
                if cells and not cells[-1].strip():
                    cells = cells[:-1]
                if len(cells) != len(headers):
                    raise Invalid('用途Markdown表的原始列数变化')
        text = '<h2 id="' + section + '"></h2>' + parser.renderer.render(tokens[start:end], parser.options, {})
    identity = HeadingSectionText(section)
    identity.feed(text)
    if identity.found != 1:
        raise Invalid('用途网段章节缺失或重复')
    parser = NetworkRegionTables(section)
    parser.feed(text)
    parser.complete()
    scopes = {header: set() for header in headers}
    regions = {}
    for name, tables in parser.regions.items():
        regional_scopes = {header: set() for header in headers}
        for table in tables:
            rows = table['rows']
            if table['nested'] or len(rows) < 2 or rows[0] != headers:
                raise Invalid('用途章节出现空表、嵌套表或未知标题列')
            for cells in rows[1:]:
                if len(cells) != len(headers):
                    raise Invalid('用途网段表的数据列数变化')
                for label, value in zip(headers, cells):
                    if '/' not in value:
                        raise Invalid('用途网段字段缺少明确CIDR掩码')
                    row, family = public_media_network(value, recipe)
                    if family not in families:
                        raise Invalid('用途网段表出现未声明地址族')
                    scopes[label].add(row)
                    regional_scopes[label].add(row)
        if any(not rows for rows in regional_scopes.values()):
            raise Invalid('用途地区含空用途范围')
        regions[name] = regional_scopes
    return scopes, regions


def network_column_scopes(recipe, text):
    return network_column_details(recipe, text)[0]


def network_column_tables(recipe, text):
    return network_column_scopes(recipe, text)[recipe['column']]
