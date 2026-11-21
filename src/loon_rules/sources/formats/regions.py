"""Read regional API endpoints from labelled vendor tables."""
import re
from urllib.parse import urlsplit
from loon_rules import domains as domain_scope
from loon_rules.sources.formats.html import HostTables
from loon_rules.rules import Invalid

def extract(recipe, text):
    table = HostTables()
    table.feed(text)
    headers = recipe['headers']
    classifiers = {key: re.compile(pattern) for key, pattern in recipe['regions'].items()}
    found_headers = set()
    result = set()
    for rows in table.rows.values():
        width = None
        for cells in rows:
            if cells in headers:
                width = len(cells)
                found_headers.add(tuple(cells))
                continue
            if width is None or len(cells) != width:
                continue
            region = cells[0].strip()
            owners = [key for key, pattern in classifiers.items() if pattern.fullmatch(region)]
            if len(owners) != 1:
                raise Invalid('API 地区未归类或归类重叠：' + region)
            for field in cells[1:]:
                value = field.strip()
                if recipe.get('bare-hosts'):
                    value = 'https://' + value
                url = urlsplit(value)
                if url.scheme != 'https' or not url.hostname or url.username is not None:
                    raise Invalid('地区表的 API 字段不是公开 HTTPS 地址')
                host = url.hostname
                parent = recipe.get('workspace-parent')
                if parent and host.endswith('.' + parent):
                    labels = host[:-len(parent) - 1].split('.')
                    if len(labels) != 2 or labels[0] not in recipe['workspace-prefixes']:
                        raise Invalid('工作空间 API 的占位符或用途前缀变化')
                    row = 'DOMAIN-SUFFIX,' + domain_scope.public_host(labels[1] + '.' + parent)
                else:
                    host = domain_scope.public_host(host)
                    if not any((host == root or host.endswith('.' + root) for root in recipe['roots'])):
                        raise Invalid('地区 API 越过已声明的厂商服务范围')
                    if recipe.get('host-pattern') and (not re.fullmatch(recipe['host-pattern'], host)):
                        raise Invalid('地区 API 不是所选产品的服务标签')
                    row = 'DOMAIN,' + host
                if owners[0] == recipe['region']:
                    result.add(row)
    if found_headers != {tuple(h) for h in headers} or not result:
        raise Invalid('地区 API 表缺少标题或所选地区')
    return result
