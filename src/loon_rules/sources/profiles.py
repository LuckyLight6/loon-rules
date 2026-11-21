"""Read iOS client configurations for the versions and models Apple currently publishes."""
from copy import deepcopy
from datetime import date,datetime,timezone
import json
import re
from urllib.parse import urlencode,urlsplit

from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid
from loon_rules.sources.transport import source_url
from loon_rules.sources.inputs import extract_rows


METHOD='ios-client-config'
FIELDS=('source','config-source','max-documents','document','protect-from-reject')
DEVICE=re.compile(r'(?:iPhone|iPad|iPod)\d{1,3},\d{1,3}\Z')
VERSION=re.compile(r'\d{1,3}(?:\.\d{1,3}){0,3}\Z')


def validate(spec):
    if spec.get('method')!=METHOD or set(spec)-{'method',*FIELDS}:
        raise Invalid('客户端配置的来源声明含未知字段或类型')
    for field in ('source','config-source'):
        value=spec.get(field)
        if not isinstance(value,str):raise Invalid('客户端配置需要明确的公开资料地址')
        source_url(value);parts=urlsplit(value)
        domain_scope.public_host(parts.hostname)
        if parts.port not in (None,443):raise Invalid('客户端配置来源须使用标准 HTTPS 端口')
    if (type(spec.get('max-documents')) is not int or spec['max-documents']<1
            or not isinstance(spec.get('document'),dict)
            or spec['document'].get('format')!='plist-service-fields' or 'source' in spec['document']
            or 'protect-from-reject' in spec and type(spec['protect-from-reject']) is not bool):
        raise Invalid('客户端配置缺少用途读取方式或请求上限')


def request_url(spec,version,device):
    return source_url(spec['config-source']+'?'+urlencode(
        {'os':'ios','os_version':version,'hardware':device}),public_profile=True)


def normalize(records):
    if not isinstance(records,list) or not records:raise Invalid('公开客户端目录缺少版本与机型')
    result={}
    for record in records:
        if (not isinstance(record,dict) or set(record)!={'version','posted','expires','devices'}
                or not isinstance(record['version'],str) or not VERSION.fullmatch(record['version'])
                or not isinstance(record['devices'],list) or not record['devices']
                or any(not isinstance(device,str) or not DEVICE.fullmatch(device) for device in record['devices'])):
            raise Invalid('公开客户端目录的版本或机型无效')
        try:
            posted=date.fromisoformat(record['posted']);expires=date.fromisoformat(record['expires'])
        except (ValueError,TypeError) as exc:raise Invalid('公开客户端目录的有效期无效') from exc
        if str(posted)!=record['posted'] or str(expires)!=record['expires'] or posted>expires:
            raise Invalid('客户端版本的日期格式或有效期不符')
        devices=sorted(set(record['devices']))
        key=(tuple(map(int,record['version'].split('.'))),record['posted'],record['expires'],tuple(devices))
        result[key]={**record,'devices':devices}
    return [result[key] for key in sorted(result)]


def documents(spec,records,as_of):
    pairs={(record['version'],device) for record in records
           if record['posted']<=as_of<=record['expires'] for device in record['devices']}
    if not pairs or len(pairs)>spec['max-documents']:
        raise Invalid('当前公开客户端配置为空或超过请求上限')
    return [{'source':request_url(spec,version,device),'kind':METHOD,'version':version,'device':device}
            for version,device in sorted(pairs,key=lambda pair:(tuple(map(int,pair[0].split('.'))),pair[1]))]


def plan(spec,text):
    validate(spec)
    try:catalog=json.loads(text)
    except ValueError as exc:raise Invalid('客户端软件目录不是 JSON') from exc
    public=catalog.get('PublicAssetSets') if isinstance(catalog,dict) else None
    releases=public.get('iOS') if isinstance(public,dict) else None
    if not isinstance(releases,list) or not releases:raise Invalid('软件目录缺少公开移动系统版本')
    records=[]
    for release in releases:
        models=release.get('SupportedDevices') if isinstance(release,dict) else None
        if not isinstance(models,list) or not models or any(not isinstance(model,str) for model in models):
            raise Invalid('公开软件版本缺少支持机型')
        chosen=[]
        for model in models:
            if model.startswith(('iPhone','iPad','iPod')):
                if not DEVICE.fullmatch(model):raise Invalid('公开软件目录含无效的 iOS 机型')
                chosen.append(model)
        if chosen:records.append({'version':release.get('ProductVersion'),'posted':release.get('PostingDate'),
                                  'expires':release.get('ExpirationDate'),'devices':chosen})
    records=normalize(records);as_of=str(datetime.now(timezone.utc).date())
    return {'method':METHOD,'directory':spec['source'],'configuration':spec['config-source'],'as-of':as_of,
            'selection':deepcopy({field:spec[field] for field in FIELDS if field in spec}),'catalog-records':records,
            'documents':documents(spec,records,as_of)}


def read(spec,record,inputs,shared_hosts):
    confirmed=[];accepted=set()
    for doc in record['documents']:
        rows=extract_rows({**spec['document'],'source':doc['source']},inputs[doc['source']])
        shared={row for row in rows if row.split(',')[1] in shared_hosts}
        rows-=shared;accepted.update(rows)
        confirmed.append({**doc,'rows':sorted(rows),'shared-rows':sorted(shared)})
    report={**record,'documents':confirmed};verify(spec,report)
    if not accepted:raise Invalid('客户端配置没有可按用途归属的端点')
    return sorted(accepted),report


def verify(spec,record):
    validate(spec)
    if (set(record)!={'method','directory','configuration','as-of','selection','catalog-records','documents'}
            or record['method']!=METHOD or record['directory']!=spec['source']
            or record['configuration']!=spec['config-source']
            or record['selection']!={field:spec[field] for field in FIELDS if field in spec}):
        raise Invalid('客户端配置报告的来源或用途选择不符')
    try:as_of=str(date.fromisoformat(record['as-of']))
    except (ValueError,TypeError) as exc:raise Invalid('客户端配置报告缺少检查日期') from exc
    if as_of!=record['as-of']:raise Invalid('客户端配置的检查日期格式不符')
    records=normalize(record['catalog-records'])
    if records!=record['catalog-records']:raise Invalid('客户端目录记录重复或未按版本归并')
    expected={doc['source']:doc for doc in documents(spec,records,as_of)}
    seen=set()
    for doc in record['documents']:
        source=doc.get('source');descriptor={field:doc.get(field) for field in ('source','kind','version','device')}
        if (set(doc)!={'source','kind','version','device','rows','shared-rows'} or source in seen
                or expected.get(source)!=descriptor or not doc['rows'] and not doc['shared-rows']):
            raise Invalid('客户端配置报告的版本、机型或请求不完整')
        seen.add(source)
        for field in ('rows','shared-rows'):
            rows=doc[field]
            if not isinstance(rows,list) or rows!=sorted(set(rows)):raise Invalid('客户端端点记录重复或无效')
            for row in rows:
                parts=row.split(',')
                if len(parts)!=2 or parts[0]!='DOMAIN' or domain_scope.public_host(parts[1])!=parts[1]:
                    raise Invalid('客户端配置只能采用精确的公开服务主机')
    if seen!=set(expected):raise Invalid('客户端配置没有覆盖目录中的全部当前版本和机型')
