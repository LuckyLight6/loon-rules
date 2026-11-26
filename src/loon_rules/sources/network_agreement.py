"""Require complete destination-network sources to agree on the same ranges."""
from hashlib import sha256
from ipaddress import collapse_addresses,ip_network
import re
from urllib.parse import urlsplit

from loon_rules import domains,rules
from loon_rules.matching import RuleIndex
from loon_rules.sources.inputs import extract_rows
from loon_rules.sources.formats.networks import network_column_details,network_table_options

METHOD='network-source-agreement'
FORMATS={'section-network-blocks','ip-network-map','network-column-tables'}
RETIRED_FORMATS={'paragraph-network-list'}


def validate(spec):
    inputs=spec.get('inputs')
    maximum=spec.get('max-documents')
    if (spec.get('method')!=METHOD or not isinstance(inputs,list) or not 2<=len(inputs)<=8
            or type(maximum) is not int or not len(inputs)<=maximum<=8):
        raise rules.Invalid('网段交叉核对需要至少两份完整资料和明确请求上限')
    seen=set()
    for item in inputs:
        if (not isinstance(item,dict) or not {'source','recipes'}<=set(item)
                or set(item)-{'source','recipes','retired-recipes'}):
            raise rules.Invalid('网段核对输入缺少来源和用途读取方式')
        source=item['source']
        if not isinstance(source,str):raise rules.Invalid('网段核对来源不是URL文字')
        url=urlsplit(source)
        if (url.scheme!='https' or not url.hostname or url.username is not None or url.query or url.fragment
                or url.port not in (None,443) or domains.public_host(url.hostname)!=url.hostname or source in seen):
            raise rules.Invalid('网段核对输入不是唯一的公开HTTPS来源')
        recipes=item['recipes']
        if not isinstance(recipes,list) or not recipes or any(not isinstance(recipe,dict) or recipe.get('format') not in FORMATS for recipe in recipes):
            raise rules.Invalid('网段核对只接受完整的目的地址用途资料')
        if 'retired-recipes' in item:
            retired=item['retired-recipes']
            if not isinstance(retired,list) or not retired or any(not isinstance(recipe,dict) or recipe.get('format') not in RETIRED_FORMATS for recipe in retired):
                raise rules.Invalid('撤回范围缺少明确的地址用途资料')
        seen.add(source)
    recipes=[recipe for item in inputs for recipe in item['recipes']]
    if any(recipe['format']=='network-column-tables' for recipe in recipes):
        if any(recipe['format']!='network-column-tables' for recipe in recipes):
            raise rules.Invalid('用途列核对须由各份完整资料提供相同的全部用途')
        signatures=set()
        for recipe in recipes:
            _,headers,column,_,_,_=network_table_options(recipe)
            signatures.add((tuple(headers),column))
        if len(signatures)!=1:raise rules.Invalid('完整用途资料的标题或目标方向不一致')
    if spec.get('source')!=inputs[0]['source']:
        raise rules.Invalid('网段核对的主来源与输入顺序不符')


def plan(spec):
    validate(spec)
    return {'method':METHOD,'directory':spec['source'],
            'documents':[{**item,'kind':METHOD} for item in spec['inputs']]}


def canonical(rows):
    networks={4:[],6:[]}
    for row in rows:
        kind,value,*flags=row.split(',')
        if kind not in ('IP-CIDR','IP-CIDR6') or flags!=['no-resolve']:
            raise rules.Invalid('网段核对包含其他规则类型或DNS匹配语义')
        network=ip_network(value,strict=True)
        if not network.is_global or (kind=='IP-CIDR6')!=(network.version==6):
            raise rules.Invalid('网段核对包含非公网范围或错误地址族')
        networks[network.version].append(network)
    if not any(networks.values()):raise rules.Invalid('网段核对输入为空')
    return [('IP-CIDR,' if family==4 else 'IP-CIDR6,')+str(network)+',no-resolve'
            for family in (4,6) for network in collapse_addresses(networks[family])]


def read(spec,record,inputs):
    documents=[]
    for document in record['documents']:
        text=inputs[document['source']]
        rows=set();purposes={};regions={}
        for recipe in document['recipes']:
            if recipe['format']=='network-column-tables':
                scopes,regional_scopes=network_column_details(recipe,text)
                rows.update(scopes[recipe['column']])
                for label,values in scopes.items():purposes.setdefault(label,set()).update(values)
                for name,regional in regional_scopes.items():
                    target=regions.setdefault(name,{})
                    for label,values in regional.items():target.setdefault(label,set()).update(values)
            else:rows.update(extract_rows(recipe,text))
        retired=set()
        for recipe in document.get('retired-recipes',()):retired.update(extract_rows(recipe,text))
        document_record={**document,'rows':canonical(rows),'shared-rows':[],
                'retired-rows':canonical(retired) if retired else [],'sha256':sha256(text.encode()).hexdigest()}
        if purposes:document_record['purpose-rows']={label:canonical(values) for label,values in purposes.items()}
        if regions:
            document_record['region-rows']={name:{label:canonical(values) for label,values in regional.items()}
                                           for name,regional in regions.items()}
        documents.append(document_record)
    report={**record,'documents':documents}
    verify(spec,report)
    return documents[0]['rows'],report


def verify(spec,record):
    expected=plan(spec)
    documents=record.get('documents',[])
    if record.get('method')!=METHOD or record.get('directory')!=spec['source'] or len(documents)!=len(expected['documents']):
        raise rules.Invalid('网段交叉核对报告与输入声明不符')
    common=None;withdrawn=[];common_purposes=None;common_regions=None
    for actual,wanted in zip(documents,expected['documents']):
        if (any(actual.get(key)!=value for key,value in wanted.items())
                or not re.fullmatch('[0-9a-f]{64}',actual.get('sha256',''))
                or not isinstance(actual.get('rows'),list) or actual.get('shared-rows')!=[]):
            raise rules.Invalid('网段核对缺少完整来源身份、指纹或用途范围')
        if actual.get('retired-recipes',[])!=wanted.get('retired-recipes',[]):
            raise rules.Invalid('撤回范围的读取方式与声明不符')
        retired=actual.get('retired-rows',[])
        if (not isinstance(retired,list) or wanted.get('retired-recipes') and not retired
                or not wanted.get('retired-recipes') and retired):
            raise rules.Invalid('撤回范围记录缺失或越过声明')
        if retired:
            if canonical(retired)!=retired:raise rules.Invalid('撤回网段记录不是完整规范范围')
            withdrawn.extend(ip_network(row.split(',')[1]) for row in retired)
        tables=[recipe for recipe in wanted['recipes'] if recipe['format']=='network-column-tables']
        if tables:
            _,headers,column,_,_,_=network_table_options(tables[0])
            purposes=actual.get('purpose-rows')
            if not isinstance(purposes,dict) or set(purposes)!=set(headers):
                raise rules.Invalid('完整用途网段记录缺少字段')
            for label,values in purposes.items():
                if not isinstance(values,list) or canonical(values)!=values:
                    raise rules.Invalid('完整用途网段记录不是规范范围')
            if purposes[column]!=actual['rows']:
                raise rules.Invalid('网段成品没有严格遵循已声明的目标方向')
            if common_purposes is not None and common_purposes!=purposes:
                raise rules.Invalid('完整资料的用途网段范围不一致，保留此前成品')
            common_purposes=purposes
            regions=actual.get('region-rows')
            if (not isinstance(regions,dict) or not regions
                    or any(not isinstance(name,str) or not name or name!=' '.join(name.split()).casefold()
                           for name in regions)):
                raise rules.Invalid('完整用途资料缺少明确的地区集合')
            regional_union={label:set() for label in headers}
            for regional in regions.values():
                if not isinstance(regional,dict) or set(regional)!=set(headers):
                    raise rules.Invalid('完整用途资料的地区用途字段不符')
                for label,values in regional.items():
                    if (not isinstance(values,list) or not values or any(not isinstance(row,str) for row in values)
                            or canonical(values)!=values):
                        raise rules.Invalid('地区用途网段记录不是完整规范范围')
                    regional_union[label].update(values)
            if any(canonical(values)!=purposes[label] for label,values in regional_union.items()):
                raise rules.Invalid('地区用途范围与完整用途记录不一致')
            if common_regions is not None and common_regions!=regions:
                raise rules.Invalid('完整资料的地区集合或地区用途不一致，保留此前成品')
            common_regions=regions
        elif 'purpose-rows' in actual or 'region-rows' in actual:
            raise rules.Invalid('无用途列的资料不能带入用途网段记录')
        ranges=canonical(actual['rows'])
        if ranges!=actual['rows']:raise rules.Invalid('网段核对报告的范围不规范')
        if common is not None and common!=ranges:
            raise rules.Invalid('完整资料的目的网段不一致，保留此前成品')
        common=ranges
    for row in common:
        network=ip_network(row.split(',')[1])
        if any(network.version==retired.version and network.overlaps(retired) for retired in withdrawn):
            raise rules.Invalid('当前目的网段与官方明确撤回范围相交，保留此前成品')


def verify_coverage(key,data,record):
    rows=[row for row in data[key] if row.split(',')[0] in ('IP-CIDR','IP-CIDR6') and row.split(',')[2:]==['no-resolve']]
    index=RuleIndex({key:rows})
    for row in record['documents'][0]['rows']:
        if not index.network_bits(row.split(',')[1],literal=True):
            raise rules.Invalid('独立资料的完整目的网段没有进入产品成品：'+key)
