"""Read domain-list-community records and verify delegated product categories."""
from collections import Counter
import re
from urllib.parse import urlsplit

from loon_rules.rules import Invalid, read_rules
from loon_rules import domains


FORMAT = 'geosite-domain-list'
IDENTIFIER = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
SCOPE_OPTIONS = ('subdomains-as-hosts', 'attributes', 'omit-types', 'delegated-includes',
                 'excluded-comment-blocks', 'delegated-scopes', 'include-comment-blocks')


def scope_options(recipe):
    return {field: recipe.get(field, False if field == 'subdomains-as-hosts' else {})
            for field in SCOPE_OPTIONS}


def policies(recipe):
    attributes = recipe.get('attributes', {})
    omitted = recipe.get('omit-types', {})
    delegated = recipe.get('delegated-includes', {})
    blocks = recipe.get('excluded-comment-blocks', {})
    assigned = recipe.get('delegated-scopes', {})
    selected = recipe.get('include-comment-blocks', {})
    for names in (attributes, omitted):
        if (not isinstance(names, dict)
                or any(not isinstance(name, str) or not IDENTIFIER.fullmatch(name)
                       or not isinstance(reason, str) or not reason.strip()
                       for name, reason in names.items())):
            raise Invalid('上游属性或省略类型缺少明确的用途说明')
    if not set(omitted) <= {'keyword', 'regexp'}:
        raise Invalid('未识别的来源类型不能通过省略声明跳过')
    if (not isinstance(delegated, dict)
            or any(not isinstance(name, str) or not IDENTIFIER.fullmatch(name)
                   or not isinstance(target, dict) or set(target) != {'owner', 'reason'}
                   or not isinstance(target['owner'], str)
                   or not IDENTIFIER.fullmatch(target['owner'])
                   or not isinstance(target['reason'], str) or not target['reason'].strip()
                   for name, target in delegated.items())):
        raise Invalid('上游子分类缺少明确的产品归属和说明')
    for labels in (blocks, selected):
        if (not isinstance(labels, dict)
                or any(not isinstance(name, str) or not name.strip() or '\n' in name
                       or not isinstance(reason, str) or not reason.strip()
                       for name, reason in labels.items())):
            raise Invalid('上游产品块缺少用途说明')
    if set(blocks) & set(selected):
        raise Invalid('同一上游产品块不能同时采用和排除')
    if not isinstance(assigned, dict):
        raise Invalid('上游共享范围的产品分配无效')
    for row, target in assigned.items():
        parts = row.split(',') if isinstance(row, str) else []
        if (len(parts) != 2 or parts[0] not in ('DOMAIN', 'DOMAIN-SUFFIX')
                or read_rules(row) != [row]
                or not isinstance(target, dict) or set(target) != {'owner', 'source', 'reason'}
                or not isinstance(target['owner'], str) or not IDENTIFIER.fullmatch(target['owner'])
                or not isinstance(target['source'], str)
                or not isinstance(target['reason'], str) or not target['reason'].strip()):
            raise Invalid('上游共享范围缺少精确边界、产品或用途依据')
        domains.public_host(parts[1])
        source = urlsplit(target['source'])
        if (source.scheme != 'https' or not source.hostname or source.username is not None
                or source.query or source.fragment):
            raise Invalid('共享范围的用途依据必须是公开 HTTPS 资料')
    return attributes, omitted, delegated, blocks, assigned, selected


def parse(recipe, text):
    attributes, omitted, delegated, blocks, assigned, selected = policies(recipe)
    rows = set()
    includes = set()
    excluded = Counter()
    excluded_blocks = Counter()
    seen_blocks = set()
    selected_blocks = set()
    unselected = set()
    block = None
    for number, raw in enumerate(text.splitlines(), 1):
        if raw.strip().startswith('#'):
            label = raw.strip().removeprefix('#').strip()
            block = label if label in blocks or label in selected else None
            if block in blocks:
                if block in seen_blocks:
                    raise Invalid('上游候选块重复：' + block)
                seen_blocks.add(block)
            if block in selected:
                if block in selected_blocks:
                    raise Invalid('上游产品块重复：' + block)
                selected_blocks.add(block)
            continue
        line = raw.partition('#')[0].strip().lstrip('\ufeff').strip()
        if not line:
            block = None
            continue
        value, *tags = line.split()
        if any(not tag.startswith('@') or tag[1:] not in attributes for tag in tags):
            raise Invalid(f'上游第 {number} 行包含未说明用途的属性')
        kind, separator, host = value.partition(':')
        if not separator:
            kind, host = 'domain', value
        if not host:
            raise Invalid(f'上游第 {number} 行缺少规则内容')
        if kind == 'include':
            if tags or host not in delegated or host in includes or block is not None:
                raise Invalid('上游子分类引用变化、重复或含未处理的属性：' + host)
            includes.add(host)
        elif kind in omitted:
            excluded[kind] += 1
        elif kind in ('domain', 'full'):
            row = read_rules(('DOMAIN,' if kind == 'full' else 'DOMAIN-SUFFIX,') + host)[0]
            if row.count(',') != 1:
                raise Invalid('上游域名含有未认可的规则参数')
            if block in blocks:
                excluded_blocks[block] += 1
            elif selected and block not in selected:
                unselected.add(row)
            else:
                rows.add(row)
        else:
            raise Invalid(f'上游第 {number} 行含未认可的规则类型：{kind}')
    if includes != set(delegated):
        raise Invalid('已声明的上游子分类引用不再完整')
    if seen_blocks != set(blocks):
        raise Invalid('已声明的上游候选块不再完整')
    if selected_blocks != set(selected):
        raise Invalid('已声明的上游产品块不再完整')
    unselected -= rows
    if not set(assigned) <= rows:
        raise Invalid('已分配的共享范围不再由当前来源完整列出')
    assignments = {}
    for row in rows:
        owners = {target['owner'] for scope, target in assigned.items() if domains.covers(scope, row)}
        if len(owners) > 1:
            raise Invalid('同一上游范围被分配给多个产品')
        if owners:
            assignments[row] = next(iter(owners))
    rows -= assignments.keys()
    if not rows:
        raise Invalid('上游产品分类没有直接的域名范围')
    return {'rows': sorted(rows), 'includes': sorted(includes), 'omitted-types': dict(excluded),
            'omitted-comment-blocks': dict(excluded_blocks), 'delegated-scopes': assignments,
            'unselected-domain-scopes': len(unselected)}


def validate_references(entries):
    recipes = {(key, recipe['source']): recipe for key, entry in entries.items()
               for recipe in entry.get('extract', ()) if recipe.get('format') == FORMAT}
    graph = {}
    for identity, recipe in recipes.items():
        _, _, delegated, _, assigned, _ = policies(recipe)
        source = urlsplit(recipe['source'])
        if (source.scheme != 'https' or not source.hostname or source.username is not None
                or source.query or source.fragment or not source.path.rsplit('/', 1)[-1]):
            raise Invalid('上游产品分类必须使用公开 HTTPS 文件')
        base = recipe['source'].rsplit('/', 1)[0] + '/'
        targets = []
        for name, target in delegated.items():
            child = (target['owner'], base + name)
            if child not in recipes:
                raise Invalid('上游子分类没有对应的独立产品来源：' + name)
            targets.append(child)
        for target in assigned.values():
            entry = entries.get(target['owner'], {})
            if (entry.get('mode') != 'compiled' or entry.get('fallback')
                    or not any(proof['source'] == target['source'] and proof.get('format') != FORMAT
                               for proof in entry.get('extract', ()))):
                raise Invalid('共享范围缺少目标产品的独立用途来源：' + target['owner'])
        graph[identity] = targets
    visited = set()
    active = set()

    def visit(identity):
        if identity in active:
            raise Invalid('上游产品分类的引用形成循环')
        if identity in visited:
            return
        active.add(identity)
        for target in graph[identity]:
            visit(target)
        active.remove(identity)
        visited.add(identity)

    for identity in graph:
        visit(identity)
