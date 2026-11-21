"""Public-source readers: api. Read data without executing source code."""
import ast
import re
import shlex
from urllib.parse import urlsplit
from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid, valid_host
from .common import within, PurposeFragments

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
    for example in code_examples(recipe, text):
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
