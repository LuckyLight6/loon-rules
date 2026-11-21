"""Read a public service bag by its non-personal, numeric configuration index."""
from copy import deepcopy
from urllib.parse import urlsplit

from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid
from loon_rules.sources.transport import source_url
from loon_rules.sources.inputs import extract_rows


METHOD='public-plist-bag'
FIELDS=('source','document','protect-from-reject')


def validate(spec):
    if (spec.get('method')!=METHOD or set(spec)-{'method',*FIELDS}
            or not isinstance(spec.get('source'),str)
            or not isinstance(spec.get('document'),dict)
            or spec['document'].get('format')!='plist-service-fields'
            or not spec['document'].get('data-path') or 'source' in spec['document']
            or 'protect-from-reject' in spec and type(spec['protect-from-reject']) is not bool):
        raise Invalid('公开服务配置缺少索引、内层数据或用途读取方式')
    source_url(spec['source'],public_bag=True)
    parts=urlsplit(spec['source']);domain_scope.public_host(parts.hostname)
    try:port=parts.port
    except ValueError as exc:raise Invalid('公开服务配置的 HTTPS 端口无效') from exc
    if port not in (None,443):raise Invalid('公开服务配置须使用标准 HTTPS 端口')


def plan(spec):
    validate(spec)
    return {'method':METHOD,'directory':spec['source'],
            'selection':deepcopy({field:spec[field] for field in FIELDS if field in spec}),
            'documents':[{'source':spec['source'],'kind':METHOD}]}


def read(spec,record,inputs,shared_hosts):
    rows=extract_rows({**spec['document'],'source':spec['source']},inputs[spec['source']])
    shared={row for row in rows if row.split(',')[1] in shared_hosts}
    rows-=shared
    report={**record,'documents':[{**record['documents'][0],'rows':sorted(rows),'shared-rows':sorted(shared)}]}
    verify(spec,report)
    if not rows:raise Invalid('公开服务配置没有可按用途归属的端点')
    return sorted(rows),report


def verify(spec,record):
    validate(spec)
    if (set(record)!={'method','directory','selection','documents'} or record['method']!=METHOD
            or record['directory']!=spec['source']
            or record['selection']!={field:spec[field] for field in FIELDS if field in spec}
            or not isinstance(record['documents'],list) or len(record['documents'])!=1):
        raise Invalid('公开服务配置报告的来源或用途选择不符')
    doc=record['documents'][0]
    if (not isinstance(doc,dict) or set(doc)!={'source','kind','rows','shared-rows'}
            or doc['source']!=spec['source'] or doc['kind']!=METHOD or not doc['rows'] and not doc['shared-rows']):
        raise Invalid('公开服务配置报告缺少对应的用途端点')
    for field in ('rows','shared-rows'):
        rows=doc[field]
        if not isinstance(rows,list) or rows!=sorted(set(rows)):raise Invalid('公开服务端点记录重复或无效')
        for row in rows:
            parts=row.split(',')
            if len(parts)!=2 or parts[0]!='DOMAIN' or domain_scope.public_host(parts[1])!=parts[1]:
                raise Invalid('公开服务配置只能采用精确的公开主机')
