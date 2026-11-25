"""Read finite input-host branches and their explicit client request construction."""
import ast
import re

from loon_rules.rules import Invalid
from .common import public_domain_pattern
from .python_maps import network_field, network_hint, non_network_fields, verify_non_network


IDENTITY_FIELDS = ('class', 'field', 'path-field', 'origin-group', 'branch-group', 'function',
                   'origin-variable', 'server-variable', 'request-method')
SCOPE_FIELDS = (*IDENTITY_FIELDS, 'server-argument', 'non-network-fields', 'pattern-groups', 'other-branch-groups')
MAX_HOSTS = 128


def finite(pattern):
    values = {('', frozenset())}
    for operation, argument in pattern:
        kind = str(operation)
        if kind == 'LITERAL':
            parts = {(chr(argument), frozenset())}
        elif kind == 'SUBPATTERN':
            number, added, removed, children = argument
            if added or removed:
                raise Invalid('地区主机模式改变了组内匹配条件')
            parts = {(text, groups | ({number} if number else set())) for text, groups in finite(children)}
        elif kind == 'BRANCH':
            parts = set().union(*(finite(branch) for branch in argument[1]))
        elif kind == 'MAX_REPEAT' and argument[0:2] == (0, 1):
            parts = {('', frozenset())} | finite(argument[2])
        elif kind == 'IN' and all(str(op) == 'LITERAL' for op, value in argument):
            parts = {(chr(value), frozenset()) for op, value in argument}
        else:
            raise Invalid('地区主机不是可完整枚举的有限字面范围')
        if len(parts) > MAX_HOSTS or len(values) * len(parts) > MAX_HOSTS:
            raise Invalid('地区主机范围超过已核对的读取上限')
        values = {(head + tail, first | second) for head, first in values for tail, second in parts}
    return values


def assignment(body, name):
    matches = [node for node in ast.walk(body) if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    if len(matches) != 1 or len(matches[0].targets) != 1 or matches[0] not in body.body:
        raise Invalid('地区客户端缺少唯一的直接用途字段：' + name)
    return matches[0].value


def literal(node):
    if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
        raise Invalid('地区客户端的主机关系不再是字面值')
    return node.value


def named(node, name):
    return isinstance(node, ast.Name) and node.id == name


def match_group(node, group):
    if (not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute)
            or not isinstance(node.func.value, ast.Name) or node.func.attr != 'group'
            or len(node.args) != 1 or node.keywords or literal(node.args[0]) != group):
        raise Invalid('地区客户端的来源主机不再取自声明的匹配组')
    return node.func.value.id


def read(recipe, text):
    for field in IDENTITY_FIELDS:
        if not isinstance(recipe.get(field), str) or not re.fullmatch(r'[A-Za-z_]\w*', recipe[field]):
            raise Invalid('地区客户端缺少用途选择：' + field)
    position = recipe.get('server-argument')
    if type(position) is not int or position < 0:
        raise Invalid('地区客户端缺少服务器参数位置')
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        raise Invalid('地区客户端源码不是完整的 Python') from error
    clients = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == recipe['class']]
    if len(clients) != 1:
        raise Invalid('地区客户端类缺失或重复')
    client = clients[0]
    pattern = assignment(client, recipe['field'])
    if (not isinstance(pattern, ast.BinOp) or not isinstance(pattern.op, ast.Add)
            or not isinstance(pattern.right, ast.Attribute) or pattern.right.attr != recipe['path-field']
            or not isinstance(pattern.right.value, ast.Name)):
        raise Invalid('地区链接模式不再使用已核对的主机与路径分界')
    owners = [node for node in tree.body if isinstance(node, ast.ClassDef)
              and node.name == pattern.right.value.id]
    if len(owners) != 1:
        raise Invalid('地区链接模式缺少可核对的路径定义')
    path_pattern = literal(assignment(owners[0], recipe['path-field']))
    try:
        try:
            from re import _parser as regex_parser
        except ImportError:
            import sre_parse as regex_parser
        parsed = regex_parser.parse(literal(pattern.left) + path_pattern, 0)
    except (re.error, ValueError, OverflowError, RecursionError) as error:
        raise Invalid('地区链接模式无法完整解析') from error
    if parsed.state.flags & ~(re.UNICODE | re.VERBOSE):
        raise Invalid('地区链接模式的整体匹配条件发生变化')
    origin_id = parsed.state.groupdict.get(recipe['origin-group'])
    branch_id = parsed.state.groupdict.get(recipe['branch-group'])
    for field in ('pattern-groups', 'other-branch-groups'):
        names = recipe.get(field)
        if (not isinstance(names, list) or field == 'pattern-groups' and not names or len(names) != len(set(names))
                or any(not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_]\w*', name) for name in names)):
            raise Invalid('地区模式缺少完整的组名与分支用途：' + field)
    if (set(parsed.state.groupdict) != set(recipe['pattern-groups'])
            or not set(recipe['other-branch-groups']) <= set(recipe['pattern-groups'])
            or recipe['branch-group'] in recipe['other-branch-groups']):
        raise Invalid('地区模式的分支与捕获字段发生变化')
    positions = [i for i, (op, value) in enumerate(parsed) if str(op) == 'SUBPATTERN' and value[0] == origin_id]
    if origin_id is None or branch_id is None or len(positions) != 1:
        raise Invalid('地区模式缺少唯一的来源主机与产品分支')
    cut = positions[0]
    if {value for value, groups in finite(parsed[:cut])} not in ({'https://'}, {'https://', 'http://'}):
        raise Invalid('地区模式的主机前还有其他网络范围')
    if cut + 1 >= len(parsed) or str(parsed[cut + 1][0]) != 'LITERAL' or parsed[cut + 1][1] != ord('/'):
        raise Invalid('地区主机没有明确的路径分界')
    values = finite([parsed[cut]])
    other_ids = {parsed.state.groupdict[name] for name in recipe['other-branch-groups']}
    for value, groups in values:
        row = public_domain_pattern(value)
        if row is None or not row.startswith('DOMAIN,'):
            raise Invalid('地区来源模式含无法归属的共享或非主机范围')
        if (branch_id in groups and groups & other_ids
                or branch_id not in groups and len(groups & other_ids) != 1):
            raise Invalid('地区模式出现未确认用途或相互混合的产品分支')
    origins = {value for value, groups in values if branch_id in groups}
    if not origins:
        raise Invalid('地区模式没有选中产品入口')

    functions = [node for node in client.body if isinstance(node, ast.FunctionDef) and node.name == recipe['function']]
    if len(functions) != 1:
        raise Invalid('地区客户端缺少唯一的请求方法')
    function = functions[0]
    if any(not isinstance(node, (ast.Assign, ast.Return)) for node in function.body):
        raise Invalid('地区客户端请求方法的控制流程发生变化')
    origin = assignment(function, recipe['origin-variable'])
    if (not isinstance(origin, ast.Call) or not named(origin.func, 'remove_start')
            or len(origin.args) != 2 or origin.keywords):
        raise Invalid('地区来源主机的规范化方式变化')
    match_name = match_group(origin.args[0], recipe['origin-group'])
    removed = literal(origin.args[1])
    matched = assignment(function, match_name)
    if (not isinstance(matched, ast.Call) or not isinstance(matched.func, ast.Attribute)
            or not named(matched.func.value, 'self') or matched.func.attr != '_match_valid_url'
            or len(matched.args) != 1 or not isinstance(matched.args[0], ast.Name) or matched.keywords):
        raise Invalid('地区入口不是从客户端输入匹配取得')
    server = assignment(function, recipe['server-variable'])
    if (not isinstance(server, ast.IfExp) or not isinstance(server.test, ast.Compare)
            or len(server.test.ops) != 1 or not isinstance(server.test.ops[0], ast.Eq)
            or len(server.test.comparators) != 1 or not isinstance(server.test.left, ast.Subscript)
            or not named(server.test.left.value, recipe['origin-variable'])
            or not isinstance(server.test.left.slice, ast.Constant) or server.test.left.slice.value != 0
            or not isinstance(server.body, ast.BinOp) or not isinstance(server.body.op, ast.Add)
            or not named(server.body.right, recipe['origin-variable'])):
        raise Invalid('地区 API 的请求构造或用途分支变化')
    first = literal(server.test.comparators[0])
    prefix = literal(server.body.left)
    literal(server.orelse)
    returns = [node for node in function.body if isinstance(node, ast.Return)]
    if (len(returns) != 1 or returns[0] is not function.body[-1] or not isinstance(returns[0].value, ast.Call)):
        raise Invalid('地区客户端没有唯一的最终请求')
    call = returns[0].value
    if (not isinstance(call.func, ast.Attribute) or not named(call.func.value, 'self')
            or call.func.attr != recipe['request-method'] or len(call.args) <= position
            or not named(call.args[position], recipe['server-variable'])):
        raise Invalid('地区服务器没有传入已核对的请求用途')
    allowed_calls = {('self', '_match_valid_url'), ('self', recipe['request-method']), (match_name, 'group')}
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        if named(callee, 'remove_start'):
            continue
        if not (isinstance(callee, ast.Attribute) and isinstance(callee.value, ast.Name)
                and (callee.value.id, callee.attr) in allowed_calls):
            raise Invalid('地区客户端出现未归属的调用用途')

    ignored = non_network_fields(recipe)
    claimed = set(ast.walk(pattern)) | set(ast.walk(server)) | set(ast.walk(origin))
    for node in client.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ignored:
                    verify_non_network(ignored[target.id], node.value)
                    claimed.update(ast.walk(node.value))
    parents = {child: parent for parent in ast.walk(client) for child in ast.iter_child_nodes(parent)}
    for node in ast.walk(client):
        if node in claimed:
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value not in claimed:
            for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                name = target.id if isinstance(target, ast.Name) else target.attr if isinstance(target, ast.Attribute) else None
                if network_field(name, node.value):
                    raise Invalid('地区客户端出现未归属的网络字段：' + str(name))
        if isinstance(node, ast.Constant) and isinstance(parents.get(node), ast.Expr):
            continue
        if isinstance(node, (ast.Constant, ast.JoinedStr)) and network_hint(node):
            raise Invalid('地区客户端仍有未归属的网络信息')
    rows = set()
    for host in origins:
        bare = host.removeprefix(removed)
        if len(first) != 1 or not bare or bare[0] != first:
            raise Invalid('产品地区入口转入尚未核对的其他 API 分支')
        for value in (host, prefix + bare):
            row = public_domain_pattern(value)
            if row is None or not row.startswith('DOMAIN,'):
                raise Invalid('地区客户端不能认领共享平台或非主机范围')
            rows.add(row)
    return rows
