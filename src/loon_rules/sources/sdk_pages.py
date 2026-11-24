"""Follow an explicitly selected public SDK, then read its production URL object."""
from copy import deepcopy
import json

from loon_rules import domains
from loon_rules.rules import Invalid
from loon_rules.sources.pages import PageData, public_url
from loon_rules.sources.formats.api import literal_object_hosts
from loon_rules.sources.formats.structured import json_record, json_values


METHOD = 'next-sdk'
FIELDS = ('asset-roots', 'config', 'document', 'max-documents')


def selection(spec):
    return deepcopy({field: spec[field] for field in FIELDS})


def validate(spec):
    public_url(spec['source'])
    if (type(spec.get('max-documents')) is not int or spec['max-documents'] != 1 or not isinstance(spec.get('asset-roots'), list)
            or not spec['asset-roots'] or not isinstance(spec.get('config'), dict)
            or not isinstance(spec['config'].get('identity'), list) or not spec['config']['identity']
            or not isinstance(spec['config'].get('paths'), list) or not spec['config']['paths']
            or not isinstance(spec.get('document'), dict)
            or spec['document'].get('format') != 'literal-object-urls'):
        raise Invalid('页面 SDK 缺少产品身份、URL 字段、资源范围或读取上限')
    for root in spec['asset-roots']:
        domains.public_host(root)
    for path in spec['config']['paths']:
        if not isinstance(path, list) or not path or any(not isinstance(field, str) or not field for field in path):
            raise Invalid('页面 SDK 缺少明确的 URL 字段路径')


def sdk_url(spec, value):
    if not isinstance(value, str) or value != value.strip():
        raise Invalid('页面 SDK 地址不是有效字符串')
    url = public_url(value)
    if not any(url.hostname == root or url.hostname.endswith('.' + root) for root in spec['asset-roots']):
        raise Invalid('页面 SDK 地址不属于已确认的资源厂商')
    return url.geturl()


def plan(spec, text):
    validate(spec)
    page = PageData(); page.feed(text); page.close()
    if page.content is not None or len(page.initial) != 1:
        raise Invalid('页面 SDK 的产品数据缺失、重复或不完整')
    document = json_record(spec['config'], json.dumps(page.initial[0]))
    urls = {sdk_url(spec, value) for path in spec['config']['paths'] for value in json_values(document, path)}
    if len(urls) != 1:
        raise Invalid('页面 SDK 没有唯一的公开脚本地址')
    return {'method': METHOD, 'selection': selection(spec),
            'documents': [{'source': next(iter(urls))}]}


def read(spec, record, inputs, shared_hosts):
    doc = record['documents'][0]
    roles = literal_object_hosts(spec['document'], inputs[doc['source']])
    asset = 'DOMAIN,' + public_url(doc['source']).hostname
    rows = set(roles.values()) | {asset}
    if rows != set(domains.exclude_shared_scopes(rows, shared_hosts)):
        raise Invalid('页面 SDK 的用途字段指向共用主机，不能静默忽略')
    return sorted(rows), {**record, 'directory': spec['source'], 'documents': [{
        **doc, 'roles': roles, 'asset-row': asset, 'rows': sorted(rows), 'shared-rows': []}]}


def verify(spec, record):
    validate(spec)
    docs = record.get('documents', [])
    if (record.get('method') != METHOD or record.get('directory') != spec['source']
            or record.get('selection') != selection(spec) or len(docs) != 1):
        raise Invalid('页面 SDK 报告的产品、来源或用途选择不符')
    doc = docs[0]
    if sdk_url(spec, doc['source']) != doc['source'] or doc.get('shared-rows') != []:
        raise Invalid('页面 SDK 报告的脚本来源或共用范围不符')
    asset = 'DOMAIN,' + public_url(doc['source']).hostname
    roles = doc.get('roles', {})
    if (not isinstance(roles, dict) or set(roles) != set(spec['document']['fields'])
            or doc.get('asset-row') != asset or set(doc['rows']) != set(roles.values()) | {asset}):
        raise Invalid('页面 SDK 报告缺少生产用途或含有额外主机')
