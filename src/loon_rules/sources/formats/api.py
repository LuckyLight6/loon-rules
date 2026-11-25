"""Public-source readers: api. Read data without executing source code."""
import ast
import json
import re
import shlex
from urllib.parse import urlsplit
from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid, valid_host
from .common import within, PurposeFragments
from . import python_maps


def literal_code_tokens(text):
    tokens = re.findall(
        r'''(?s)/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[A-Za-z_]\w*|[^\s]''',
        text,
    )
    return [token for token in tokens if not token.startswith(('//', '/*'))]


def literal_object_hosts(recipe, text):
    key = recipe.get('object-key')
    fields = recipe.get('fields')
    if (not isinstance(key, str) or not re.fullmatch(r'[A-Za-z_]\w*', key)
            or not isinstance(fields, list) or not fields
            or any(not isinstance(field, str) or not re.fullmatch(r'[A-Za-z_]\w*', field) for field in fields)
            or len(set(fields)) != len(fields)):
        raise Invalid('SDK 对象缺少明确的环境与 URL 用途字段')
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_javascript
    except ImportError as error:
        raise Invalid('读取 JavaScript SDK 需要安装项目依赖：python3 -m pip install --editable .') from error
    from .structured import service_url_host
    from .common import public_domain_pattern
    tree = Parser(Language(tree_sitter_javascript.language())).parse(text.encode('utf-8'))
    if tree.root_node.has_error:
        raise Invalid('SDK JavaScript 语法变化，不能按部分解析结果更新')

    def string(node):
        if node is None or node.type != 'string':
            raise Invalid('SDK 环境 URL 不再是单个静态字面值')
        value = node.text.decode('utf-8')
        try:
            return json.loads(value) if value.startswith('"') else ast.literal_eval(value)
        except (ValueError, SyntaxError) as error:
            raise Invalid('SDK 字符串不能按静态字面值读取') from error

    def property_name(node):
        if node.type == 'property_identifier':
            return node.text.decode('utf-8')
        if node.type == 'string':
            return string(node)
        return None

    objects = []
    pending = [tree.root_node]
    while pending:
        node = pending.pop()
        if node.type == 'pair':
            name = node.child_by_field_name('key')
            value = node.child_by_field_name('value')
            if property_name(name) == key and value.type == 'object':
                objects.append(value)
        pending.extend(node.named_children)
    if len(objects) != 1 or objects[0].type != 'object':
        raise Invalid('SDK 环境对象缺失或重复')
    result = {}
    for member in objects[0].named_children:
        if member.type == 'comment':
            continue
        if member.type != 'pair':
            raise Invalid('SDK 环境对象包含计算、展开或未确认的字段')
        name = member.child_by_field_name('key')
        field = property_name(name)
        if field not in fields or field in result:
            raise Invalid('SDK 环境对象的用途字段变化、重复或无法识别')
        row = public_domain_pattern(service_url_host(string(member.child_by_field_name('value'))))
        if row is None:
            raise Invalid('SDK 环境 URL 指向无法独立归属的共用主机')
        result[field] = row
    if set(result) != set(fields):
        raise Invalid('SDK 环境对象的用途字段不完整')
    return result


def literal_object_urls(recipe, text):
    return set(literal_object_hosts(recipe, text).values())


def c_function_url(recipe, text):
    function = recipe.get('function', '')
    if not re.fullmatch(r'[A-Za-z_]\w*', function):
        raise Invalid('C 端点来源缺少函数名')
    tokens = literal_code_tokens(text)
    bodies = []
    for index, token in enumerate(tokens):
        if token != function:
            continue
        tail = tokens[index + 1:]
        if tail[:3] == ['(', ')', '{']:
            start = 3
        elif tail[:4] == ['(', 'void', ')', '{']:
            start = 4
        else:
            continue
        try:
            end = tail.index('}', start)
        except ValueError as error:
            raise Invalid('C 端点函数缺少结束符') from error
        bodies.append(tail[start:end])
    if len(bodies) != 1:
        raise Invalid('C 端点函数缺失或重复')
    body = bodies[0]
    if len(body) == 4 and body[1] == '@':
        body = [body[0], *body[2:]]
    if (len(body) != 3 or body[0] != 'return' or body[-1] != ';'
            or not re.fullmatch(r'"[^"\\]+"', body[1])):
        raise Invalid('C 端点函数不是单个字面 URL 返回')
    url = urlsplit(body[1][1:-1])
    if (url.scheme != 'https' or not url.hostname or url.username is not None
            or url.query or url.fragment):
        raise Invalid('C 端点函数没有公开 HTTPS 地址')
    return {'DOMAIN,' + domain_scope.public_host(url.hostname)}


def qt_host_predicate(recipe, text):
    """Read a direct OR of exact host comparisons from one QUrl predicate."""
    function = recipe.get('function', '')
    if not re.fullmatch(r'[A-Za-z_]\w*', function):
        raise Invalid('Qt 主机来源缺少明确的用途函数')
    tokens = literal_code_tokens(text)
    signature = ['(', 'const', 'QUrl', '&', 'url', ')', '{']
    bodies = []
    for index, token in enumerate(tokens):
        if index == 0 or token != function or tokens[index - 1] != 'bool':
            continue
        tail = tokens[index + 1:]
        if tail[:len(signature)] != signature:
            raise Invalid('Qt 主机函数的 URL 参数或结构变化')
        try:
            end = tail.index('}', len(signature))
        except ValueError as error:
            raise Invalid('Qt 主机函数不完整') from error
        bodies.append(tail[len(signature):end])
    if len(bodies) != 1:
        raise Invalid('Qt 主机用途函数缺失或重复')
    body = bodies[0]
    prefix = literal_code_tokens('const auto host = url.host().toLower(); return')
    if body[:len(prefix)] != prefix or body[-1:] != [';']:
        raise Invalid('Qt 主机函数不再直接判断规范化主机')
    expression = body[len(prefix):-1]
    result = set()
    while expression:
        clause = expression[:8]
        if (len(clause) != 8 or clause[:5] != ['(', 'host', '=', '=', 'u']
                or clause[6:] != ['_q', ')']
                or not re.fullmatch(r'"[A-Za-z0-9][A-Za-z0-9.-]*"', clause[5])):
            raise Invalid('Qt 主机用途不再是精确域名比较')
        result.add('DOMAIN,' + domain_scope.public_host(clause[5][1:-1]))
        expression = expression[8:]
        if not expression:
            break
        if expression[:2] != ['|', '|'] or len(expression) == 2:
            raise Invalid('Qt 主机用途不再是直接的域名并集')
        expression = expression[2:]
    if not result:
        raise Invalid('Qt 主机用途函数没有域名')
    return result


def go_host_switch(recipe,text):
    """Read literal host cases that return one named service's trust policy."""
    function=recipe.get('function','');callee=recipe.get('return-call','')
    if not all(re.fullmatch(r'[A-Za-z_]\w*',name) for name in (function,callee)):
        raise Invalid('Go 服务主机缺少明确的函数与用途分支')
    tokens=re.findall(r'(?s)/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|`[^`]*`|[A-Za-z_]\w*|[^\s]',text)
    tokens=[token for token in tokens if not token.startswith(('//','/*'))]
    starts=[i for i in range(len(tokens)-2) if tokens[i:i+3]==['func',function,'(']]
    if len(starts)!=1:raise Invalid('Go 服务主机函数缺失或重复')

    def closing(start):
        depth=0
        for index in range(start,len(tokens)):
            if tokens[index]=='{':depth+=1
            elif tokens[index]=='}':
                depth-=1
                if depth==0:return index
        raise Invalid('Go 服务主机函数的代码块不完整')

    try:start=tokens.index('{',starts[0]+3)
    except ValueError as error:raise Invalid('Go 服务主机缺少函数体') from error
    end=closing(start);body=tokens[start+1:end]
    if not body or body[0]!='switch':raise Invalid('Go 服务主机不再是直接用途分支')
    try:switch=tokens.index('{',start+1)
    except ValueError as error:raise Invalid('Go 服务主机缺少 switch 分支') from error
    if closing(switch)!=end-1:raise Invalid('Go 服务主机包含分支之外的逻辑')
    arms=tokens[switch+1:end-1]
    if any(token in ('{','}') for token in arms):raise Invalid('Go 服务主机包含嵌套条件，不能推断完整范围')
    result=set();position=0
    while position<len(arms):
        kind=arms[position];position+=1;hosts=[]
        if kind=='case':
            while position<len(arms):
                literal=arms[position]
                if not re.fullmatch(r'"[^"\\\r\n]+"',literal):
                    raise Invalid('Go 服务主机分支不是字面主机名')
                hosts.append(literal[1:-1]);position+=1
                if position<len(arms) and arms[position]==',':position+=1
                else:break
        elif kind!='default':raise Invalid('Go 服务主机分支格式变化')
        if position>=len(arms) or arms[position]!=':':raise Invalid('Go 服务主机分支缺少冒号')
        position+=1;begin=position
        while position<len(arms) and arms[position] not in ('case','default'):position+=1
        action=arms[begin:position]
        if action and action[-1]==';':action=action[:-1]
        if not action or action[0]!='return':raise Invalid('Go 服务主机分支不是直接返回')
        if callee not in action:continue
        if not hosts or action!=['return',callee,'(',')']:
            raise Invalid('Go 服务主机的用途返回方式变化')
        hosts=[domain_scope.public_host(host) for host in hosts]
        if recipe.get('roots') and any(not within(host,recipe['roots']) for host in hosts):
            raise Invalid('Go 服务主机超出声明的厂商范围')
        result.update('DOMAIN,'+host for host in hosts)
    if not result:raise Invalid('Go 客户端没有该用途的字面主机分支')
    return result


def azure_cloud_metadata(recipe, text):
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise Invalid('Azure 云定义格式变化') from exc
    wanted = set(recipe['clouds'])
    seen = set()
    result = set()
    part = recipe['part']
    fields = set(recipe.get('fields', ()))
    if part not in ('suffixes', 'endpoints') or (part == 'endpoints' and (not fields)):
        raise Invalid('Azure 云定义需要明确用途和端点字段')
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = {t.id for t in node.targets if isinstance(t, ast.Name)} & wanted
        if not names:
            continue
        if names & seen or not isinstance(node.value, ast.Call):
            raise Invalid('Azure 云定义重复或无效')
        seen.update(names)
        call = next((kw.value for kw in node.value.keywords if kw.arg == part), None)
        expected = 'CloudSuffixes' if part == 'suffixes' else 'CloudEndpoints'
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != expected:
            raise Invalid('Azure 云定义缺少 ' + part)
        values = {kw.arg: kw.value for kw in call.keywords if not fields or kw.arg in fields}
        if fields - set(values):
            raise Invalid('Azure 云定义缺少已选字段')
        for value in values.values():
            if not isinstance(value, ast.Constant):
                raise Invalid('Azure 云定义不是静态数据')
            if value.value is None:
                continue
            if not isinstance(value.value, str):
                raise Invalid('Azure 云定义字段不是字符串')
            if part == 'suffixes':
                host = value.value.lstrip('.').casefold()
                kind = 'DOMAIN-SUFFIX'
            else:
                url = urlsplit(value.value)
                if url.scheme != 'https' or not url.hostname or url.username is not None:
                    raise Invalid('Azure 控制端点不是公开 HTTPS 名称')
                host = url.hostname
                kind = 'DOMAIN'
            if not valid_host(host):
                raise Invalid('Azure 云定义缺少有效主机名')
            result.add(kind + ',' + host)
    if seen != wanted or not result:
        raise Invalid('Azure 云定义缺少已选云环境')
    return result

def sdk_client_endpoints(recipe, text):
    guide = PurposeFragments()
    guide.feed(text)

    def owned_host(value):
        url = urlsplit(value)
        if url.scheme != 'https' or not url.hostname or url.username is not None or (not valid_host(url.hostname)) or (url.hostname in recipe['roots']) or (not within(url.hostname, recipe['roots'])):
            return None
        return 'DOMAIN,' + url.hostname
    fields = '|'.join((re.escape(field) for field in recipe['api-fields']))
    pattern = re.compile('(?<![\\w.])(?:' + fields + ')\\s*[:=]\\s*["\'](https://[^"\'\\s]+)["\']')
    api = {host for example in guide.examples for value in pattern.findall(example) if (host := owned_host(value))}
    console = {host for url, label in guide.links if label in recipe['console-labels'] and (host := owned_host(url))}
    if not api or not console:
        raise Invalid('SDK 指南缺少指定地区的 API 配置或控制台入口')
    return api | console

def python_sdk_endpoints(recipe, text):
    tree = ast.parse(text)
    if any(field in recipe for field in python_maps.OPTIONS):
        return python_maps.endpoints(recipe, tree)
    classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    functions = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if not set(recipe.get('classes', ())) <= classes.keys() or not set(recipe.get('functions', ())) <= functions.keys():
        raise Invalid('SDK 缺少已选客户端、函数或环境定义')
    result = set()

    def selected(name):
        return name in recipe.get('fields', ()) or any((name.startswith(p) for p in recipe.get('field-prefixes', ())))

    def collect(name, value):
        if not selected(name):
            return
        if isinstance(value, ast.Dict) and recipe.get('dictionary-values'):
            if not all((isinstance(v, ast.Constant) and isinstance(v.value, str) for v in value.values)):
                raise Invalid('SDK 服务器表不是静态地址数据')
            for item in value.values:
                collect(name, item)
            return
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            raw = value.value
        elif isinstance(value, ast.JoinedStr) and all((isinstance(v, ast.Constant) and isinstance(v.value, str) for v in value.values)):
            raw = ''.join((v.value for v in value.values))
        else:
            return
        if recipe.get('bare-hosts') and '://' not in raw:
            raw = 'https://' + raw
        url = urlsplit(raw)
        if url.scheme != 'https' or not url.hostname or url.username is not None or (not valid_host(url.hostname)):
            raise Invalid('SDK 默认连接不是公开 HTTPS 名称')
        result.add('DOMAIN,' + domain_scope.public_host(url.hostname))
    selected_nodes = [classes[name] for name in recipe.get('classes', ())] + [functions[name] for name in recipe.get('functions', ())]
    if recipe.get('module-level'):
        selected_nodes.extend((n for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign))))
    for selected_node in selected_nodes:
        for node in ast.walk(selected_node):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                    if isinstance(target, ast.Name):
                        collect(target.id, node.value)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args.posonlyargs + node.args.args
                defaults = list(zip(args[len(args) - len(node.args.defaults):], node.args.defaults))
                defaults += list(zip(node.args.kwonlyargs, node.args.kw_defaults))
                for arg, value in defaults:
                    collect(arg.arg, value)
    if not result:
        raise Invalid('SDK 中没有可静态确认的默认 API 主机')
    return result

def code_examples(recipe, text):
    if recipe.get('markup') == 'markdown':
        return re.findall('(?ms)^```[^\\n]*\\n(.*?)^```[ \\t]*$', text)
    guide = PurposeFragments()
    guide.feed(text)
    return guide.examples

def code_api_endpoints(recipe, text):
    fields = '|'.join((re.escape(field) for field in recipe['api-fields']))
    pattern = re.compile('(?<![\\w.])(?:' + fields + ')\\s*[:=]\\s*["\'](https://[^"\'\\s]+)["\']')
    result = set()
    examples = code_examples(recipe, text)
    if recipe.get('markup') == 'source':
        examples = []
        tokens = literal_code_tokens(text)
        for index, token in enumerate(tokens):
            if (token not in recipe['api-fields'] or tokens[index + 1:index + 2] != ['=']
                    or index and tokens[index - 1] == '.'):
                continue
            value = tokens[index + 2:index + 3]
            if (not value or not re.fullmatch(r'''["'][^"'\\]+["']''', value[0])
                    or tokens[index + 3:index + 4] not in ([], [';'])):
                raise Invalid('SDK API 字段不再是单个字面地址')
            examples.append(token + '=' + value[0])
    for example in examples:
        for value in pattern.findall(example):
            url = urlsplit(value)
            if url.scheme == 'https' and url.hostname and (url.username is None) and valid_host(url.hostname):
                result.add('DOMAIN,' + domain_scope.public_host(url.hostname))
    if not result:
        raise Invalid('官方示例缺少 SDK API 配置')
    return result

def curl_api_endpoints(recipe, text):
    result = set()
    values = {'-X', '--request', '-H', '--header', '-d', '--data', '--data-raw', '--data-binary', '--data-urlencode', '-u', '--user', '-o', '--output', '-e', '--referer', '-x', '--proxy', '--connect-timeout', '--max-time', '--config', '-K', '--resolve', '--connect-to', '--cacert', '--cert', '--key', '--write-out', '-w'}
    switches = {'--silent', '--show-error', '--fail', '--location', '--location-trusted', '--include', '--head', '--compressed', '--insecure', '--verbose', '--no-buffer', '--http1.1', '--http2', '--http3'}
    for example in code_examples(recipe, text):
        try:
            tokens = shlex.split(example.replace('\\\n', ' '))
        except ValueError:
            continue
        if not tokens or tokens[0] != 'curl':
            continue
        skip = False
        for token in tokens[1:]:
            if skip:
                skip = False
                continue
            if token in values:
                skip = True
                continue
            if token.startswith(('|', '&', ';', '>')):
                break
            if token in switches or (token.startswith('-') and (not token.startswith('--')) and (set(token[1:]) <= set('fsSLIikvN'))):
                continue
            if any((token.startswith(flag + '=') for flag in values if flag.startswith('--'))):
                continue
            if len(token) > 2 and token[:2] in values:
                continue
            if token.startswith('-') and token != '--url' and (not token.startswith('--url=')):
                raise Invalid('curl 示例包含尚未识别的参数，不能推断请求目标')
            if token.startswith('--url='):
                token = token[6:]
            if not token.startswith('https://'):
                continue
            url = urlsplit(token)
            if url.hostname and url.username is None and valid_host(url.hostname):
                result.add('DOMAIN,' + domain_scope.public_host(url.hostname))
    if not result:
        raise Invalid('官方示例缺少 curl 请求目标')
    return result

def parse_vim_config_defaults(recipe, text):
    source = re.sub('(?m)^\\s*"[^\\n]*', '', text)
    fields = '|'.join((re.escape(f) for f in recipe['fields']))
    values = re.findall('get\\(\\s*[^,()]+,\\s*["\'](?:' + fields + ')["\']\\s*,\\s*["\'](https://[^"\'\\s]+)["\']\\s*\\)', source)
    result = set()
    for value in values:
        url = urlsplit(value)
        if url.hostname and url.username is None and valid_host(url.hostname):
            result.add('DOMAIN,' + domain_scope.public_host(url.hostname))
    if not result:
        raise Invalid('客户端源码缺少指定 API 设置的公开默认地址')
    return result

def parse_code_api_endpoints(recipe, text):
    return code_api_endpoints(recipe, text)

def parse_curl_api_endpoints(recipe, text):
    return curl_api_endpoints(recipe, text)

def parse_python_sdk_endpoints(recipe, text):
    return python_sdk_endpoints(recipe, text)

def parse_sdk_client_endpoints(recipe, text):
    return sdk_client_endpoints(recipe, text)

def parse_azure_cloud_metadata(recipe, text):
    return azure_cloud_metadata(recipe, text)

def parse_service_default_host(recipe, text):
    source = re.sub('/\\*.*?\\*/', '', text, flags=re.S)
    source = re.sub('(?m)^\\s*//[^\\n]*', '', source)
    block = re.search('(?ms)^service\\s+' + re.escape(recipe['service']) + '\\s*\\{(.*?)^\\}', source)
    found = re.findall('(?m)^\\s*option\\s+\\(google\\.api\\.default_host\\)\\s*=\\s*"([^"]+)"\\s*;', block[1] if block else '')
    if len(found) != 1 or not valid_host(found[0]) or (not within(found[0], recipe['roots'])) or (found[0] in recipe['roots']):
        raise Invalid('服务定义缺少可信的默认 API 主机：' + recipe['service'])
    return {'DOMAIN,' + found[0]}
