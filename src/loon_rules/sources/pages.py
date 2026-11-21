"""Read a product page's declared assets and adjacent, labelled API examples without executing JS."""
from html.parser import HTMLParser
import json
import re
from urllib.parse import urlsplit

from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid


STRING=r'"(?:[^"\\]|\\.)*"'
EXAMPLE=re.compile(r'\(\s*0\s*,\s*[\w$]+\.jsx\s*\)\(\s*"h[1-6]"\s*,\s*\{children:('+STRING+
    r')\}\),\s*\(\s*0\s*,\s*[\w$]+\.jsx\s*\)\(\s*[\w$]+\s*,\s*\{value:('+STRING+r')[,}]')


def public_url(value):
    url=urlsplit(value)
    if (url.scheme!='https' or not url.hostname or url.username is not None or url.query or url.fragment
            or url.port not in (None,443)):
        raise Invalid('产品页面入口不是公开 HTTPS 地址')
    host=domain_scope.public_host(url.hostname)
    return url._replace(netloc=host+(':443' if url.port==443 else ''))


def validate(spec):
    source=public_url(spec['source'])
    if (source.path!=spec.get('page') or not re.fullmatch(r'/[A-Za-z0-9_/-]+',spec['page'])
            or not spec.get('asset-roots') or not spec.get('request-labels')
            or len(set(spec['request-labels']))!=len(spec['request-labels'])
            or spec.get('max-documents')!=1):
        raise Invalid('产品页面缺少路径、资源范围、用途标签或请求上限')
    for root in spec['asset-roots']:domain_scope.public_host(root)


class PageData(HTMLParser):
    def __init__(self):
        super().__init__();self.scripts=[];self.initial=[];self.content=None

    def handle_starttag(self,tag,attrs):
        if tag!='script':return
        attrs=dict(attrs)
        if source:=attrs.get('src'):self.scripts.append(source)
        if attrs.get('id')=='__NEXT_DATA__':
            if attrs.get('type')!='application/json':raise Invalid('产品页面数据类型变化')
            self.content=[]

    def handle_data(self,data):
        if self.content is not None:self.content.append(data)

    def handle_endtag(self,tag):
        if tag=='script' and self.content is not None:
            self.initial.append(json.loads(''.join(self.content)));self.content=None


def document_matches(spec,prefix,source):
    return bool(re.fullmatch(re.escape(prefix.rstrip('/')+'/_next/static/chunks/pages'+spec['page'])+
                             r'-[A-Za-z0-9_-]+\.js',source))


def plan(spec,text):
    validate(spec)
    parser=PageData();parser.feed(text)
    if len(parser.initial)!=1 or parser.initial[0].get('page')!=spec['page']:
        raise Invalid('产品页面身份或初始数据变化')
    initial=parser.initial[0];prefix=initial.get('assetPrefix','')
    asset=public_url(prefix)
    if not any(asset.hostname==root or asset.hostname.endswith('.'+root) for root in spec['asset-roots']):
        raise Invalid('产品页面资源超出已声明的厂商范围')
    sources=[url for url in parser.scripts if document_matches(spec,prefix,url)]
    if len(sources)!=1:raise Invalid('产品页面没有唯一的专用路由文件')
    return {'method':'next-page','page':spec['page'],'asset-prefix':prefix,
            'documents':[{'source':sources[0]}]}


def read(spec,record,inputs,shared_hosts):
    doc=record['documents'][0]
    roles={label:set() for label in spec['request-labels']}
    for match in EXAMPLE.finditer(inputs[doc['source']]):
        label,value=(json.loads(part) for part in match.groups())
        if label in roles:roles[label].add('DOMAIN,'+public_url(value).hostname)
    if any(not found for found in roles.values()):raise Invalid('产品页面的请求示例用途缺失或格式变化')
    asset_row='DOMAIN,'+public_url(record['asset-prefix']).hostname
    rows={asset_row}|set().union(*roles.values())
    shared={row for row in rows if row.split(',')[1] in shared_hosts}
    return sorted(rows-shared),{**record,'directory':spec['source'],'asset-row':asset_row,
        'documents':[{**doc,'roles':{k:sorted(v) for k,v in roles.items()},
                      'rows':sorted(rows-shared),'shared-rows':sorted(shared)}]}


def verify(spec,record):
    docs=record.get('documents',[])
    if (record.get('method')!='next-page' or record.get('directory')!=spec['source'] or record.get('page')!=spec['page'] or len(docs)!=1
            or not document_matches(spec,record.get('asset-prefix',''),docs[0]['source'])):
        raise Invalid('产品页面报告的身份或路由文件不符')
    asset=public_url(record['asset-prefix'])
    if (record.get('asset-row')!='DOMAIN,'+asset.hostname
            or not any(asset.hostname==r or asset.hostname.endswith('.'+r) for r in spec['asset-roots'])):
        raise Invalid('产品页面报告的资源用途不符')
    roles=docs[0].get('roles',{})
    if set(roles)!=set(spec['request-labels']) or any(not rows for rows in roles.values()):
        raise Invalid('产品页面报告缺少请求用途')
    if set(docs[0]['rows'])|set(docs[0]['shared-rows'])!={record['asset-row']}|{r for rows in roles.values() for r in rows}:
        raise Invalid('产品页面报告的入口缺少用途依据')
