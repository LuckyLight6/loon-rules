"""Read typed endpoint fields throughout a Python client family without executing it."""
import ast
from ipaddress import ip_network
import re
from urllib.parse import urlsplit

from loon_rules.rules import Invalid, valid_host
from .common import public_domain_pattern


SCOPE_FIELDS = ('classes', 'class-prefixes', 'fields', 'dictionary-host-fields',
                'dictionary-required-fields', 'dictionary-metadata-fields',
                'nullable-class-defaults', 'bare-hosts', 'scalar-host-fields', 'non-network-fields')
OPTIONS = ('class-prefixes', 'dictionary-host-fields', 'dictionary-required-fields',
           'dictionary-metadata-fields', 'nullable-class-defaults', 'scalar-host-fields', 'non-network-fields')
NETWORK_MARKERS = {'API', 'HOST', 'HOSTS', 'URL', 'URLS', 'SERVER', 'SERVERS', 'ENDPOINT', 'ENDPOINTS',
                   'ASN', 'ASNS', 'CIDR', 'CIDRS', 'ADDRESS', 'ADDRESSES', 'PROCESS', 'PROCESSES'}


def names(recipe, field, *, required=False):
    values = recipe.get(field, [])
    if (not isinstance(values, list) or required and not values
            or any(not isinstance(value, str) or not re.fullmatch(r'[A-Za-z_]\w*', value) for value in values)
            or len(values) != len(set(values))):
        raise Invalid('SDK 缺少明确且不重复的客户端或字段用途：' + field)
    return set(values)


def static_text(value):
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        raw = value.value
    elif isinstance(value, ast.JoinedStr) and all(isinstance(part, ast.Constant) and isinstance(part.value, str)
                                                 for part in value.values):
        raw = ''.join(part.value for part in value.values)
    else:
        raise Invalid('SDK 的服务字典主机不是静态字符串')
    if raw != raw.strip() or any(ord(char) < 32 for char in raw):
        raise Invalid('SDK 的服务字典主机含空白或控制字符')
    return raw


def endpoint(value, *, bare):
    raw = static_text(value)
    if bare and '://' not in raw:
        raw = 'https://' + raw
    try:
        url = urlsplit(raw)
        port = url.port
    except ValueError as exc:
        raise Invalid('SDK 的服务字典地址或端口格式无效') from exc
    if (url.scheme != 'https' or not url.hostname or url.username is not None
            or url.query or url.fragment or port == 0):
        raise Invalid('SDK 的服务字典缺少公开 HTTPS 主机')
    row = public_domain_pattern(url.hostname)
    if row is None or not row.startswith('DOMAIN,'):
        raise Invalid('SDK 的服务字典不能认领整家共享平台')
    return row


def network_hint(value):
    if value is None:
        return False
    for node in ast.walk(value):
        if isinstance(node, ast.JoinedStr) and any(isinstance(part, ast.Constant)
                and isinstance(part.value, str) and '://' in part.value for part in node.values):
            return True
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        text = node.value.strip()
        if text.casefold().startswith(('https?://', 'http?://')):
            return True
        if re.match(r'[A-Za-z][A-Za-z0-9+.-]*://', text):
            try:
                if urlsplit(text).hostname:
                    return True
            except ValueError:
                return True
        try:
            ip_network(text, strict=False)
            return True
        except ValueError:
            pass
        if re.fullmatch(r'AS\d+', text, re.I):
            return True
        if '.' in text:
            try:
                public_domain_pattern(text.lstrip('.'))
                return True
            except Invalid:
                pass
    return False


def non_network_fields(recipe):
    specs = recipe.get('non-network-fields', {})
    if not isinstance(specs, dict):
        raise Invalid('SDK 的非网络字段须逐项说明用途')
    for field, spec in specs.items():
        if (not isinstance(field, str) or not re.fullmatch(r'[A-Za-z_]\w*', field)
                or not isinstance(spec, dict) or set(spec) != {'kind', 'reason'}
                or spec['kind'] not in ('test-cases', 'input-url-pattern')
                or not isinstance(spec['reason'], str) or not spec['reason'].strip()):
            raise Invalid('SDK 的非网络字段缺少已核实的用途或处理依据')
    return specs


def network_field(name, value):
    return network_hint(value) or bool(name and set(name.upper().split('_')) & NETWORK_MARKERS)


def verify_non_network(spec, value):
    allowed = (ast.List, ast.Tuple, ast.Dict) if spec['kind'] == 'test-cases' else (
        ast.Constant, ast.JoinedStr, ast.Attribute, ast.BinOp)
    if not isinstance(value, allowed) or isinstance(value, ast.Constant) and not isinstance(value.value, str):
        raise Invalid('SDK 的非网络字段类型发生变化')
    if isinstance(value, ast.BinOp) and not isinstance(value.op, (ast.Add, ast.Mod)):
        raise Invalid('SDK 的输入链接模式出现未确认的组合方式')


def function_depth(node, parents, client):
    scope = parents.get(node)
    count = 0
    while scope is not None and scope is not client and not isinstance(scope, ast.ClassDef):
        count += isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef))
        scope = parents.get(scope)
    return count if scope is client else None


def template_field(node, scalar_values):
    parts = list(node.values)
    if not parts or not isinstance(parts[0], ast.FormattedValue):
        return None
    part = parts[0]
    field = part.value
    if (part.conversion != -1 or part.format_spec is not None or not isinstance(field, ast.Attribute)
            or not isinstance(field.value, ast.Name) or field.value.id != 'self' or field.attr not in scalar_values):
        return None
    # A known value must already establish the authority. Appending to an origin
    # without a path separator could instead construct a different hostname.
    suffix = parts[1].value if len(parts) > 1 and isinstance(parts[1], ast.Constant) else ''
    for raw in scalar_values[field.attr]:
        url = urlsplit(raw)
        if url.scheme != 'https' or not url.hostname or not (url.path or suffix.startswith('/')):
            return None
    return field.attr


def dictionary_rows(value, host_fields, required, metadata, *, bare):
    if not isinstance(value, ast.Dict):
        raise Invalid('SDK 的服务字段不再是字面字典')
    keys = [key.value if isinstance(key, ast.Constant) and isinstance(key.value, str) else None for key in value.keys]
    if (None in keys or len(keys) != len(set(keys)) or not required <= set(keys)
            or set(keys) - host_fields - metadata):
        raise Invalid('SDK 服务字典的必需字段、用途或范围发生变化')
    result = set()
    for field, item in zip(keys, value.values):
        if field in host_fields:
            result.add(endpoint(item, bare=bare))
        elif isinstance(item, ast.Constant) and isinstance(item.value, str):
            text = item.value
            if network_hint(item) or ':' in text or '.' in text and valid_host(text):
                raise Invalid('SDK 非网络元数据出现未处理的主机或地址')
        elif not isinstance(item, ast.Name):
            raise Invalid('SDK 服务字典的非网络元数据类型变化')
    return result


def endpoints(recipe, tree):
    if any(recipe.get(field) for field in ('functions', 'module-level', 'dictionary-values', 'field-prefixes')):
        raise Invalid('SDK 服务字典不能与其他字段扫描方式混用')
    explicit = names(recipe, 'classes')
    prefixes = names(recipe, 'class-prefixes')
    fields = names(recipe, 'fields', required=True)
    hosts = names(recipe, 'dictionary-host-fields', required=True)
    required = names(recipe, 'dictionary-required-fields', required=True)
    metadata = names(recipe, 'dictionary-metadata-fields')
    scalars = names(recipe, 'scalar-host-fields')
    ignored = non_network_fields(recipe)
    if (not explicit and not prefixes or required - hosts or hosts & metadata
            or fields & scalars or (fields | scalars) & ignored.keys()):
        raise Invalid('SDK 服务字典的产品范围或字段用途不一致')
    nullable = recipe.get('nullable-class-defaults', False)
    bare = recipe.get('bare-hosts', False)
    if type(nullable) is not bool or type(bare) is not bool:
        raise Invalid('SDK 服务字典的开关必须是布尔值')
    top = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    classes = {node.name: node for node in top}
    if len(classes) != len(top) or not explicit <= classes.keys():
        raise Invalid('SDK 客户端类缺失或重复')
    for prefix in prefixes:
        if not any(name.startswith(prefix) for name in classes):
            raise Invalid('SDK 客户端家族不再存在')
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and any(node.name.startswith(prefix) for prefix in prefixes) and node not in top:
            raise Invalid('SDK 客户端家族移入未确认的动态作用域')
    selected = [node for name, node in classes.items() if name in explicit or any(name.startswith(prefix) for prefix in prefixes)]
    result = set()
    covered = {}
    scalar_values = {}
    for client in selected:
        placeholders = set()
        dictionaries = set()
        parents = {child: parent for parent in ast.walk(client) for child in ast.iter_child_nodes(parent)}
        claimed = set()
        scalar_seen = set()
        for node in ast.walk(client):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            functions = function_depth(node, parents, client)
            if functions is None:
                continue
            for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                name = target.id if isinstance(target, ast.Name) else target.attr if isinstance(target, ast.Attribute) else None
                if isinstance(target, ast.Name) and node not in client.body:
                    if network_hint(node.value):
                        raise Invalid('SDK 客户端出现未归属的局部网络字段：' + str(name))
                    continue
                if name in ignored and isinstance(target, ast.Name):
                    verify_non_network(ignored[name], node.value)
                    claimed.update(ast.walk(node.value))
                    continue
                if name not in fields | scalars:
                    if network_field(name, node.value):
                        raise Invalid('SDK 客户端出现未归属的网络字段：' + str(name))
                    continue
                if isinstance(target, ast.Attribute) and not (isinstance(target.value, ast.Name) and target.value.id == 'self'):
                    raise Invalid('SDK 服务字典写入了未确认的外部对象')
                if isinstance(target, ast.Attribute) and functions != 1:
                    raise Invalid('SDK 服务字典写入了未确认的嵌套函数作用域')
                if (nullable and node in client.body and isinstance(target, ast.Name)
                        and isinstance(node.value, ast.Constant) and node.value.value is None):
                    placeholders.add(name)
                    continue
                if name in scalars:
                    result.add(endpoint(node.value, bare=bare))
                    scalar_values.setdefault(name, set()).add(static_text(node.value))
                    scalar_seen.add(name)
                else:
                    result.update(dictionary_rows(node.value, hosts, required, metadata, bare=bare))
                claimed.update(ast.walk(node.value))
                dictionaries.add(name)
        if placeholders - dictionaries:
            raise Invalid('SDK 客户端只剩空默认值，缺少可核实的服务字典')
        if scalar_seen and scalar_seen != scalars:
            raise Invalid('SDK 客户端的成组服务字段不完整')
        covered[client] = (parents, claimed)
    for client, (parents, claimed) in covered.items():
        for node in ast.walk(client):
            if node in claimed or function_depth(node, parents, client) is None:
                continue
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and isinstance(parents.get(node), ast.Expr):
                continue
            if isinstance(node, ast.JoinedStr):
                field = template_field(node, scalar_values)
                if field:
                    claimed.update(ast.walk(node))
                    continue
                if any(isinstance(part, ast.Attribute) and isinstance(part.value, ast.Name)
                       and part.value.id == 'self' and part.attr in scalars for part in ast.walk(node)):
                    raise Invalid('SDK 的请求模板改变主机或缺少可核实的服务默认值')
            if isinstance(node, (ast.Constant, ast.JoinedStr)) and network_hint(node):
                raise Invalid('SDK 客户端仍有未归属的网络信息')
    if not result:
        raise Invalid('SDK 客户端家族缺少可核实的服务主机')
    return result
