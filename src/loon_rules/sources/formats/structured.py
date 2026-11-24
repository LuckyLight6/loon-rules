"""Read vendor-published domain lists and service discovery documents."""
import json
import plistlib
import re
from urllib.parse import urlsplit
from xml.parsers.expat import ExpatError

from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid
from loon_rules.sources.pages import PageData
from .common import public_domain_pattern


def brand_domain_list(recipe, text):
    result = set()
    for raw in text.splitlines():
        if not raw.strip():
            continue
        host = domain_scope.public_host(raw.strip().removeprefix('.'))
        if (host.split('.')[0] != recipe['brand-label']
                or domain_scope.current().registrable(host) != host):
            raise Invalid('官方域名清单超出品牌注册域范围')
        result.add('DOMAIN-SUFFIX,' + host)
    if not result:
        raise Invalid('官方品牌域名清单为空')
    return result


def derp_map(recipe, text):
    document = json.loads(text)
    regions = document.get('Regions')
    if not isinstance(regions, dict) or not regions:
        raise Invalid('中继发现文档缺少地区表')
    result = set()
    for key, region in regions.items():
        if (not key.isdecimal() or region.get('RegionID') != int(key)
                or not isinstance(region.get('Nodes'), list) or not region['Nodes']):
            raise Invalid('中继地区标识或节点表变化')
        for node in region['Nodes']:
            if node.get('RegionID') != int(key) or not node.get('HostName'):
                raise Invalid('中继节点缺少所属地区或公开主机名')
            result.add('DOMAIN,' + domain_scope.public_host(node['HostName']))
    return result


def api_discovery(recipe, text):
    document = json.loads(text)
    if (document.get('kind') != 'discovery#restDescription'
            or document.get('discoveryVersion') != 'v1'
            or document.get('name') != recipe['name']
            or document.get('version') != recipe['version']):
        raise Invalid('API 发现文档的产品或版本不符')
    result = set()
    for field in ('rootUrl', 'baseUrl', 'mtlsRootUrl', 'mtlsBaseUrl'):
        if field not in document:
            continue
        url = urlsplit(document[field])
        if (url.scheme != 'https' or not url.hostname or url.username is not None
                or url.query or url.fragment):
            raise Invalid('API 服务字段不是公开 HTTPS 入口')
        result.add('DOMAIN,' + domain_scope.public_host(url.hostname))
    if not result:
        raise Invalid('API 发现文档缺少服务入口')
    return result


def service_domain_groups(recipe,text):
    document=json.loads(text)
    for field in recipe['path']:
        if not isinstance(document,dict) or field not in document:
            raise Invalid('官方服务清单缺少域名字段')
        document=document[field]
    result=set()
    for group in recipe['groups']:
        values=document.get(group) if isinstance(document,dict) else None
        if not isinstance(values,list) or not values:
            raise Invalid('官方服务清单缺少已选业务：'+group)
        for value in values:
            if row:=public_domain_pattern(value):result.add(row)
    if not result:raise Invalid('官方服务清单没有可归属的域名')
    return result


def json_values(node,path,*,mappings=False):
    if not path:return [node]
    field,*tail=path
    if field=='*':
        if mappings and isinstance(node,dict):node=list(node.values())
        if not isinstance(node,list) or not node:raise Invalid('服务元数据的文件清单为空或类型变化')
        return [value for member in node for value in json_values(member,tail,mappings=mappings)]
    if not isinstance(node,dict) or field not in node:raise Invalid('服务元数据缺少用途字段：'+str(field))
    return json_values(node[field],tail,mappings=mappings)


def json_record(recipe,text):
    try:document=json.loads(text)
    except ValueError as exc:raise Invalid('服务元数据不是 JSON') from exc
    if not isinstance(document,dict):raise Invalid('服务元数据不是对象')
    for identity in recipe.get('identity',()):
        if json_values(document,identity['path'])!=[identity['equals']]:
            raise Invalid('服务元数据的产品身份不符')
    return document


def document_body(recipe,text):
    values=json_values(json_record(recipe,text),recipe['body-path'])
    if len(values)!=1 or not isinstance(values[0],str) or not values[0].strip():
        raise Invalid('资料正文不是非空文本字段')
    return values[0]


def json_service_urls(recipe,text,*,strict=False):
    """Read explicit server or download fields, excluding links in other metadata."""
    document=json_record(recipe,text)
    paths=recipe.get('paths',())
    if (not paths and not recipe.get('url-fields')
            or any(not path or any(not isinstance(p,str) or not p for p in path) for path in paths)):
        raise Invalid('服务元数据没有明确的 URL 字段路径')
    result=set()
    for path in paths:
        for value in json_values(document,path):
            row = public_domain_pattern(service_url_host(value))
            if row: result.add(row)
            elif strict: raise Invalid('产品用途字段指向无法独立归属的共用主机')
    result.update(json_url_fields(recipe, document, strict=strict))
    if not result:raise Invalid('服务 URL 没有可独立归属的公开主机')
    return result


def json_url_fields(recipe, document, *, strict=False):
    """Read named resource fields inside a declared document tree, not every URL."""
    specs = recipe.get('url-fields', [])
    if not isinstance(specs, list):
        raise Invalid('服务 URL 的用途字段清单不是数组')
    result = set()
    for spec in specs:
        if (not isinstance(spec, dict) or set(spec) - {'path', 'fields', 'allow-query'}
                or not {'path', 'fields'} <= set(spec)
                or not isinstance(spec['path'], list) or not spec['path']
                or any(not isinstance(part, str) or not part for part in spec['path'])
                or not isinstance(spec['fields'], list) or not spec['fields']
                or any(not isinstance(field, str) or not field or field == '*' for field in spec['fields'])
                or len(set(spec['fields'])) != len(spec['fields'])
                or type(spec.get('allow-query', False)) is not bool):
            raise Invalid('服务 URL 缺少明确的正文范围或资源用途字段')
        seen = set()
        def visit(node):
            if isinstance(node, dict):
                for field, value in node.items():
                    if field in spec['fields']:
                        seen.add(field)
                        row = public_domain_pattern(service_url_host(value, allow_query=spec.get('allow-query', False)))
                        if row: result.add(row)
                        elif strict: raise Invalid('产品资源字段指向无法独立归属的共用主机')
                    else:
                        visit(value)
            elif isinstance(node, list):
                for child in node:
                    visit(child)
        for node in json_values(document, spec['path']):
            visit(node)
        if seen != set(spec['fields']):
            raise Invalid('服务 URL 正文缺少必需的资源用途字段')
    return result


def next_service_urls(recipe, text):
    if not isinstance(recipe.get('identity'), list) or not recipe['identity']:
        raise Invalid('产品页面数据缺少明确的产品身份条件')
    page = PageData()
    page.feed(text)
    page.close()
    if page.content is not None or len(page.initial) != 1:
        raise Invalid('产品页面数据缺失、重复或不完整')
    return json_service_urls(recipe, json.dumps(page.initial[0]), strict=True)


def service_url_host(value, *, allow_query=False):
    if not isinstance(value,str) or value!=value.strip() or any(ord(c)<32 for c in value):
        raise Invalid('服务 URL 字段不是有效字符串')
    url=urlsplit(value)
    if (url.scheme != 'https' or not url.hostname or url.username is not None
            or url.fragment or (url.query and not allow_query)):
        raise Invalid('服务 URL 字段不是无凭据的 HTTPS 入口')
    return domain_scope.public_host(url.hostname)


class UniquePlistKeys(dict):
    def __setitem__(self,key,value):
        if key in self:raise Invalid('服务 plist 含有重复字段')
        super().__setitem__(key,value)


def plist_record(data):
    try:document=plistlib.loads(data,dict_type=UniquePlistKeys)
    except (ValueError,TypeError,ExpatError,plistlib.InvalidFileException) as exc:
        raise Invalid('服务元数据不是有效 plist') from exc
    if not isinstance(document,dict):raise Invalid('服务 plist 不是对象')
    return document


def plist_service_fields(recipe,text):
    """Read only named service fields, never every link in a configuration bag."""
    document=plist_record(text.encode('utf-8'))
    if 'data-path' in recipe:
        path=recipe['data-path']
        if not isinstance(path,list) or not path or any(not isinstance(field,str) or not field or field=='*' for field in path):
            raise Invalid('服务 plist 缺少明确的内层数据路径')
        values=json_values(document,path)
        if len(values)!=1 or not isinstance(values[0],bytes):raise Invalid('服务 plist 内层数据不是二进制字段')
        document=plist_record(values[0])
    identities=recipe.get('identity')
    if not isinstance(identities,list) or not identities:raise Invalid('服务 plist 缺少产品身份条件')
    for identity in identities:
        if (not isinstance(identity,dict) or set(identity) not in ({'path','equals'},{'path','contains-keys'})
                or not isinstance(identity['path'],list) or not identity['path']
                or any(not isinstance(field,str) or not field or field=='*' for field in identity['path'])):
            raise Invalid('服务 plist 的产品身份不符')
        values=json_values(document,identity['path'])
        if 'equals' in identity:
            if values!=[identity['equals']]:raise Invalid('服务 plist 的产品身份不符')
        else:
            keys=identity['contains-keys']
            if (not isinstance(keys,list) or not keys or any(not isinstance(key,str) or not key or key=='*' for key in keys)
                    or len(values)!=1 or not isinstance(values[0],dict) or not set(keys)<=values[0].keys()):
                raise Invalid('服务 plist 缺少声明的对象或字段')
    result=set();selected=False
    for field in ('host-paths','url-paths'):
        paths=recipe.get(field,[])
        if (not isinstance(paths,list) or any(not isinstance(path,list) or not path
                or any(not isinstance(part,str) or not part for part in path) for path in paths)):
            raise Invalid('服务 plist 缺少明确的字段路径')
        selected|=bool(paths)
        for path in paths:
            for value in json_values(document,path,mappings=True):
                if field=='url-paths':host=service_url_host(value)
                else:
                    if not isinstance(value,str) or value!=value.strip():raise Invalid('服务主机字段不是有效字符串')
                    host=domain_scope.public_host(value)
                if row:=public_domain_pattern(host):result.add(row)
    if 'records' in recipe:
        result.update(plist_record_urls(document,recipe['records']));selected=True
    if not selected or not result:raise Invalid('服务 plist 没有可独立归属的公开主机')
    return result


def plist_record_urls(document,spec):
    if (not isinstance(spec,dict) or set(spec)-{'paths','url-fields','url-patterns','typed-url-patterns','required-fields','allow-query'}
            or not isinstance(spec.get('paths'),list) or not spec['paths']):
        raise Invalid('服务配置缺少明确的记录选择')
    allow_query = spec.get('allow-query', False)
    if not isinstance(allow_query, bool):
        raise Invalid('服务配置的 allow-query 必须是布尔值')
    for field in ('url-fields','url-patterns','typed-url-patterns','required-fields'):
        values=spec.get(field,[])
        if not isinstance(values,list) or any(not isinstance(value,str) or not value for value in values):
            raise Invalid('服务配置的字段选择必须是文本数组')
    fields=set(spec.get('url-fields',()))
    try:
        patterns=[re.compile(value) for value in spec.get('url-patterns',())]
        typed=[re.compile(value) for value in spec.get('typed-url-patterns',())]
    except re.error as exc:raise Invalid('服务字段模式无效') from exc
    required=set(spec.get('required-fields',()))
    def named(field,choices):return any(pattern.fullmatch(field) for pattern in choices)
    if not (fields or patterns or typed) or any(field not in fields and not named(field,patterns+typed) for field in required):
        raise Invalid('服务配置的必需字段没有对应的用途选择')
    rows=set();seen=set()
    for path in spec['paths']:
        if not isinstance(path,list) or any(not isinstance(part,str) or not part for part in path):
            raise Invalid('服务配置的记录路径无效')
        for record in json_values(document,path,mappings=True):
            if not isinstance(record,dict):raise Invalid('服务配置的地区记录不是对象')
            for field,value in record.items():
                typed_url=(named(field,typed) and isinstance(value,str) and re.match(r'[A-Za-z][A-Za-z0-9+.-]*://',value))
                if field in fields or field in required or named(field,patterns) or typed_url:
                    seen.add(field)
                    rows.add('DOMAIN,' + service_url_host(value, allow_query=allow_query))
    if not set(spec.get('required-fields',()))<=seen:raise Invalid('服务配置缺少必需的用途字段')
    return rows
