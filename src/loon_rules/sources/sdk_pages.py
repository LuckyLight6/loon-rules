"""Follow the current public dependency SDK and verify its complete production scope."""
from copy import deepcopy
import hashlib
import json
import re

from loon_rules import domains
from loon_rules.rules import Invalid,read_rules
from loon_rules.sources.pages import PageData,public_url
from loon_rules.sources.formats.api import literal_object_hosts
from loon_rules.sources.formats.javascript import environment_values
from loon_rules.sources.inputs import extract_rows
from loon_rules.sources.formats.structured import json_record,json_values


METHOD = 'next-sdk'
FIELDS = ('asset-roots', 'config', 'document', 'max-documents')


def selection(spec):
    return deepcopy({field: spec[field] for field in (*FIELDS,'source-format','inventory','reviewed-outside') if field in spec})


def validate(spec):
    public_url(spec['source'])
    form=spec.get('source-format','next-page')
    if (type(spec.get('max-documents')) is not int or spec['max-documents']!=1
            or not isinstance(spec.get('asset-roots'),list) or not spec['asset-roots']
            or not isinstance(spec.get('config'),dict) or not isinstance(spec.get('document'),dict)
            or form not in ('next-page','javascript-environment')):
        raise Invalid('SDK 缺少明确的入口、资源范围或读取上限')
    for root in spec['asset-roots']:
        domains.public_host(root)
    if form=='javascript-environment':
        config=spec['config']
        if (not isinstance(config.get('fields'),list) or config.get('script-field') not in config['fields']
                or spec['document'].get('format')!='javascript-method-urls'
                or spec.get('inventory')!={'format':'javascript-url-literals'}):
            raise Invalid('发布 SDK 缺少生产脚本字段、用途方法或完整字面地址清单')
        outside=spec.get('reviewed-outside',{})
        if (not isinstance(outside,dict) or any(not row.startswith('DOMAIN,') or read_rules(row)!=[row]
                or not isinstance(reason,str) or not reason.strip() for row,reason in outside.items())):
            raise Invalid('SDK 未选环境须有明确主机和用途依据')
        return
    if (not isinstance(spec['config'].get('identity'),list) or not spec['config']['identity']
            or not isinstance(spec['config'].get('paths'),list) or not spec['config']['paths']
            or spec['document'].get('format')!='literal-object-urls'):
        raise Invalid('页面 SDK 缺少产品身份、URL 字段或完整环境读取器')
    for path in spec['config']['paths']:
        if not isinstance(path,list) or not path or any(not isinstance(field,str) or not field for field in path):
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
    if spec.get('source-format')=='javascript-environment':
        fields=environment_values(spec['config'],text)
        source=sdk_url(spec,fields[spec['config']['script-field']])
        return {'method':METHOD,'selection':selection(spec),'source-sha256':hashlib.sha256(text.encode()).hexdigest(),
                'script-fields':fields,'documents':[{'source':source}]}
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
    if spec.get('source-format')=='javascript-environment':
        text=inputs[doc['source']]
        purpose=sorted(extract_rows(spec['document'],text))
        inventory=sorted(extract_rows(spec['inventory'],text))
        asset='DOMAIN,'+public_url(doc['source']).hostname
        rows=sorted(set(purpose)|{asset})
        if set(rows)!=set(domains.exclude_shared_scopes(rows,shared_hosts)):
            raise Invalid('SDK 当前脚本的生产接口指向未确认的共享主机')
        return rows,{**record,'directory':spec['source'],'documents':[{**doc,'purpose-rows':purpose,
            'literal-rows':inventory,'sha256':hashlib.sha256(text.encode()).hexdigest(),
            'asset-row':asset,'rows':rows,'shared-rows':[]}]}
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
    if spec.get('source-format')=='javascript-environment':
        fields=record.get('script-fields',{})
        if (set(fields)!=set(spec['config']['fields']) or not re.fullmatch('[0-9a-f]{64}',record.get('source-sha256',''))
                or not re.fullmatch('[0-9a-f]{64}',doc.get('sha256',''))
                or sdk_url(spec,fields[spec['config']['script-field']])!=doc['source']):
            raise Invalid('当前 SDK 的生产字段、脚本来源或指纹不一致')
        for field in ('purpose-rows','literal-rows'):
            rows=doc.get(field)
            if not isinstance(rows,list) or not rows or read_rules('\n'.join(rows))!=rows:
                raise Invalid('SDK 依赖脚本缺少完整用途或字面地址清单')
        if doc.get('asset-row')!=asset or set(doc['rows'])!=set(doc['purpose-rows'])|{asset}:
            raise Invalid('SDK 依赖脚本的实际主机与用途记录不一致')
        return
    roles = doc.get('roles', {})
    if (not isinstance(roles, dict) or set(roles) != set(spec['document']['fields'])
            or doc.get('asset-row') != asset or set(doc['rows']) != set(roles.values()) | {asset}):
        raise Invalid('页面 SDK 报告缺少生产用途或含有额外主机')


def verify_inventory(spec,record,rows):
    if spec.get('source-format')!='javascript-environment':return
    outside=spec.get('reviewed-outside',{})
    for doc in record['documents']:
        for row in doc['literal-rows']:
            if row not in outside and not any(domains.covers(actual,row) for actual in rows):
                raise Invalid('SDK 完整字面地址清单出现未归属的新接口：'+row)
