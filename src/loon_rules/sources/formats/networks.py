"""Public-source readers: networks. Read data without executing source code."""
from ipaddress import ip_network
import json
import re
from loon_rules.sources.formats.html import HostTables
from loon_rules.rules import Invalid, valid_host
from .common import within, LabelledLists, HeadingSectionText

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
        raise Invalid('媒体地址不是对齐的 CIDR') from exc
    if not net.is_global or net.prefixlen < recipe['min-prefix'][str(net.version)]:
        raise Invalid('媒体地址超过已确认范围')
    return (('IP-CIDR,' if net.version == 4 else 'IP-CIDR6,') + str(net) + ',no-resolve', net.version)

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
