"""Render companies and products from the same subscription declarations."""
import re

from loon_rules.catalog import priority_label, rule_filename
from loon_rules.rules import Invalid


def validate(config, entries):
    spec = config.get('service-directory')
    if spec is None:
        return {}
    public = {entry['id'] for entry in config['entries'] if entry['mode'] != 'view'}
    common = spec.get('common', [])
    if not isinstance(common, list) or len(common) != len(set(common)) or not set(common) <= public:
        raise Invalid('厂商目录的公共规则重复或不存在')
    vendors = spec.get('vendors')
    if not isinstance(vendors, list) or not vendors:
        raise Invalid('厂商目录缺少厂商')
    seen = set()
    owners = {}
    for vendor in vendors:
        key = vendor.get('id', '')
        if (not isinstance(key, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', key)
                or key in seen or not vendor.get('name') or not vendor.get('products')):
            raise Invalid('厂商名称、标识或产品清单无效：' + str(key))
        seen.add(key)
        names = set()
        for product in vendor['products']:
            name = product.get('name')
            selected = product.get('rules')
            if (not isinstance(name, str) or not name.strip() or name in names
                    or not isinstance(selected, list) or not selected or len(selected) != len(set(selected))):
                raise Invalid('产品缺少名称或实际细分规则：' + key)
            names.add(name)
            for rule in selected:
                if rule not in public or rule in common:
                    raise Invalid('厂商产品引用未知、公共或合集规则：' + str(rule))
                if rule in owners and owners[rule] != key:
                    raise Invalid('同一细分规则归入不同厂商：' + rule)
                owners[rule] = key
    missing = public - set(owners) - set(common)
    if missing:
        raise Invalid('订阅没有厂商或公共用途归属：' + ', '.join(sorted(missing)))
    return owners


def render(config, entries):
    if 'service-directory' not in config:
        return None
    owners = validate(config, entries)
    spec = config['service-directory']

    def first(product):
        return min(entries[key]['priority'] for key in product['rules'])

    def link(key):
        entry = entries[key]
        return f"[{priority_label(entry)} {entry['description']}](../rules/{rule_filename(entry)})"

    def links(keys):
        return '、'.join(link(key) for key in sorted(keys, key=lambda key: entries[key]['priority']))

    vendor_views = {}
    shared_views = []
    common_views = []
    for key in config['views']:
        members = entries[key]['members']
        companies = {owners.get(member) for member in members}
        if len(companies) == 1 and None not in companies:
            vendor_views.setdefault(next(iter(companies)), []).append(key)
        elif companies == {None}:
            common_views.append(key)
        else:
            shared_views.append(key)
    product_count = sum(len(vendor['products']) for vendor in spec['vendors'])
    lines = ['# 按厂商查产品与服务', '',
             f"这里列出 {len(spec['vendors'])} 个厂商或项目、{product_count} 项产品与服务，均链接到现有细分规则。"
             '同一连接范围服务多个产品时可以共用一份表，无法可靠区分的部分合并说明。', '',
             '厂商按首份规则编号排列，产品按规则编号排列。[订阅的实际执行顺序](rules.md)仍由同一份分类声明生成；'
             '从这里找到产品后，按规则清单的位置订阅。合集替代所列成员，细分表继续保留。', '']
    if shared_views:
        lines += ['## 跨厂商合集', '', '| 用途 | 合集 | 成员数量 |', '|---|---|---:|']
        for key in sorted(shared_views, key=lambda key: entries[key]['priority']):
            entry = entries[key]
            lines.append(f"| {entry['description']} | {link(key)} | {len(entry['members'])} |")
        lines.append('')
    for vendor in sorted(spec['vendors'], key=lambda item: min(first(p) for p in item['products'])):
        lines += ['## ' + vendor['name'], '']
        if selected := vendor_views.get(vendor['id']):
            lines += ['可用合集：' + links(selected), '']
        lines += ['| 产品或服务 | 对应规则 |', '|---|---|']
        for product in sorted(vendor['products'], key=first):
            lines.append(f"| {product['name']} | {links(product['rules'])} |")
        lines.append('')
    common = sorted([*spec['common'], *common_views], key=lambda key: entries[key]['priority'])
    lines += ['## 网络与公共规则', '', '| 用途 | 对应规则 |', '|---|---|']
    for key in common:
        lines.append(f"| {entries[key]['description']} | {link(key)} |")
    return '\n'.join(lines) + '\n'
