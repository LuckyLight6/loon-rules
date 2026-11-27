"""Read complete public access metadata without treating server egress as destinations."""
from ipaddress import ip_address
import re
from urllib.parse import urlsplit

from loon_rules import domains
from loon_rules.rules import Invalid
from loon_rules.sources.transport import source_url
from .common import public_domain_pattern
from .structured import json_object


def domain_pattern(value):
    if not isinstance(value, str) or value != value.strip() or value != value.lower():
        raise Invalid('公开网络元数据的域名必须是规范的小写名称')
    tail = value.removeprefix('*.')
    if any(character in tail for character in '*?[]') or value.endswith('.'):
        raise Invalid('公开网络元数据只支持精确域名或开头的*.通配符')
    row = public_domain_pattern(value)
    if row is None or row.split(',')[1] != value:
        raise Invalid('公开网络元数据包含未确认的托管范围或非规范域名')
    return row


def read(recipe, text):
    allowed = {'format', 'source', 'brand-label', 'shared-patterns', 'all-patterns', 'protect-from-reject'}
    if set(recipe) - allowed or any(type(recipe.get(field, False)) is not bool
                                   for field in ('all-patterns', 'protect-from-reject')):
        raise Invalid('公开网络元数据的用途声明或选项无效')
    brand = recipe.get('brand-label')
    source = recipe.get('source')
    if not isinstance(brand, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', brand):
        raise Invalid('公开网络元数据缺少规范的产品品牌标签')
    if not isinstance(source, str):
        raise Invalid('公开网络元数据缺少官方来源地址')
    source_url(source)
    host = domains.public_host(urlsplit(source).hostname)
    suffixes = domains.current()
    registrable = suffixes.registrable(host)
    if suffixes.suffix(host)[1] or not registrable or registrable.split('.')[0] != brand:
        raise Invalid('公开网络元数据的来源注册域与产品品牌不符')

    def owned(value):
        tail = value.removeprefix('*.')
        root = suffixes.registrable(tail)
        return not suffixes.suffix(tail)[1] and root and root.split('.')[0] == brand

    shared = recipe.get('shared-patterns')
    if (not isinstance(shared, list) or any(not isinstance(value, str) for value in shared)
            or len(shared) != len(set(shared))):
        raise Invalid('公开网络元数据的共享范围声明必须是不重复的数组')
    for value in shared:
        domain_pattern(value)
        if owned(value):
            raise Invalid('产品自有命名空间不能声明为共享排除范围')

    document = json_object(text)
    if set(document) != {'domains', 'egressIps'}:
        raise Invalid('公开网络元数据的完整字段范围变化')
    for field in ('domains', 'egressIps'):
        if not isinstance(document[field], list) or not document[field]:
            raise Invalid('公开网络元数据缺少完整的域名或出站地址数组')

    seen_addresses = set()
    for record in document['egressIps']:
        if (not isinstance(record, dict) or set(record) != {'ip', 'ipVersion'}
                or not isinstance(record['ip'], str)):
            raise Invalid('服务端出站地址记录字段或类型变化')
        try:
            address = ip_address(record['ip'])
        except ValueError as error:
            raise Invalid('服务端出站地址不是单个IP') from error
        if (not address.is_global or address.is_multicast or str(address) != record['ip']
                or record['ipVersion'] != 'IPv' + str(address.version)
                or address in seen_addresses):
            raise Invalid('服务端出站地址不是规范公网IP、地址族错误或出现重复')
        seen_addresses.add(address)

    rows = set()
    owned_rows = set()
    observed_shared = set()
    for record in document['domains']:
        if (not isinstance(record, dict) or 'pattern' not in record
                or set(record) - {'pattern', 'details'}):
            raise Invalid('公开网络元数据的域名记录字段变化')
        value = record['pattern']
        row = domain_pattern(value)
        if row in rows:
            raise Invalid('公开网络元数据包含重复的粗粒度范围')
        is_owned = owned(value)
        if not is_owned:
            observed_shared.add(value)
        if not is_owned and value not in shared:
            raise Invalid('公开网络元数据出现尚未确认用途的共享范围：' + value)
        if 'details' in record:
            details = record['details']
            if not isinstance(details, list) or not details:
                raise Invalid('公开网络元数据的详细用途数组无效')
            seen_details = set()
            for detail in details:
                if (not isinstance(detail, dict) or 'domain' not in detail
                        or set(detail) - {'domain', 'purpose'}):
                    raise Invalid('公开网络元数据的详细用途字段变化')
                name = detail['domain']
                domain_pattern(name)
                tail = value.removeprefix('*.')
                detail_tail = name.removeprefix('*.')
                inside = (detail_tail == tail or detail_tail.endswith('.' + tail)) if value.startswith('*.') else name == value
                if not inside or name in seen_details:
                    raise Invalid('详细域名越出其粗粒度范围或出现重复')
                if 'purpose' in detail:
                    purpose = detail['purpose']
                    if (not isinstance(purpose, str) or not purpose or purpose != purpose.strip()
                            or any(ord(character) < 32 or ord(character) == 127 for character in purpose)):
                        raise Invalid('公开网络元数据的用途说明不是规范文本')
                seen_details.add(name)
        rows.add(row)
        if is_owned:
            owned_rows.add(row)
    if observed_shared != set(shared):
        raise Invalid('公开网络元数据缺少已声明的共享范围，须先核实撤回或来源完整性')
    if not owned_rows:
        raise Invalid('公开网络元数据没有已确认的产品自有命名空间')
    # Details are optional examples; only coarse patterns define published scope.
    # Egress addresses are validated above and never emitted as client destinations.
    return rows if recipe.get('all-patterns', False) else owned_rows
