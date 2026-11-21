"""Combine a vendor-published host template with its published regional domains."""
import re
from urllib.parse import urlsplit

from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid
from loon_rules.sources.formats.common import DestinationTables
from loon_rules.sources.formats.structured import brand_domain_list


FIELDS=('source','registry-source','brand-label','placeholder','purposes','ports')


def validate(spec):
    for field in ('source','registry-source'):
        value=spec.get(field)
        if not isinstance(value,str):raise Invalid('地区模板的公开资料地址必须是文本')
        url=urlsplit(value)
        if (url.scheme!='https' or not url.hostname or url.username is not None or url.query or url.fragment
                or url.port not in (None,443)):
            raise Invalid('地区主机模板需要公开的 HTTPS 资料和域名清单')
        domain_scope.public_host(url.hostname)
    if (not isinstance(spec.get('brand-label'),str)
            or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',spec['brand-label'])
            or not isinstance(spec.get('placeholder'),str)
            or not re.fullmatch(r'\[[a-z]+(?:-[a-z]+)*\]',spec['placeholder'])
            or not isinstance(spec.get('purposes'),list) or not spec['purposes']
            or any(not isinstance(p,str) or not p.strip() for p in spec['purposes'])
            or not isinstance(spec.get('ports'),str) or not spec['ports'].strip()
            or type(spec.get('max-documents')) is not int or spec['max-documents']!=1):
        raise Invalid('地区主机模板缺少品牌、占位字段、用途、端口或请求上限')


def materialize(spec,templates,literals,registry):
    roots={row.split(',')[1] for row in brand_domain_list(spec,registry)}
    if any(domain_scope.current().suffix(root)[1] for root in roots):
        raise Invalid('地区注册域清单不能使用共享托管租户')
    marker=spec['placeholder'];brand=spec['brand-label']
    if not templates or not literals:raise Invalid('地区资料缺少明确主机或发布的模板')
    hosts=set()
    for template in templates:
        if not isinstance(template,str) or template.count(marker)!=1 or not template.endswith('.'+marker):
            raise Invalid('地区模板的占位字段或位置变化')
        labels=template[:-len(marker)-1].split('.')
        if len(labels)<2 or labels[-1]!=brand or any(not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',p) for p in labels):
            raise Invalid('地区模板超出发布的品牌命名空间')
        prefix='.'.join(labels[:-1])
        hosts.update(domain_scope.public_host(prefix+'.'+root) for root in roots)
    for host in literals:
        if domain_scope.public_host(host)!=host or host not in hosts:
            raise Invalid('地区模板与同一用途下的明确主机不对应')
    return {'DOMAIN,'+host for host in hosts},sorted(roots)


def plan(spec,text):
    validate(spec);table=DestinationTables();table.feed(text)
    templates=set();literals=set();seen=set()
    for rows in table.rows.values():
        for hosts,ports,purpose in rows:
            if ports.strip()!=spec['ports']:continue
            selected=[p for p in spec['purposes'] if re.match(re.escape(p.casefold())+r'(?:\s|$)',purpose.casefold())]
            if not selected:continue
            seen.update(selected)
            for value in re.split(r'[,\s]+',hosts.casefold().strip()):
                if spec['placeholder'] in value:templates.add(value)
                else:literals.add(domain_scope.public_host(value))
    if not table.matched or seen!=set(spec['purposes']) or not templates or not literals:
        raise Invalid('地区端点表缺少已声明用途及其主机模板')
    return {'method':'host-templates','templates':sorted(templates),'literal-hosts':sorted(literals),
            'documents':[{'source':spec['registry-source'],'kind':'domain-registry'}]}


def read(spec,record,inputs,shared_hosts):
    doc=record['documents'][0]
    rows,roots=materialize(spec,record['templates'],record['literal-hosts'],inputs[doc['source']])
    shared={row for row in rows if row.split(',')[1] in shared_hosts}
    return sorted(rows-shared),{**record,'directory':spec['source'],'registry-domains':roots,
            'documents':[{**doc,'rows':sorted(rows-shared),'shared-rows':sorted(shared)}]}


def verify(spec,record):
    validate(spec);docs=record.get('documents',[])
    if (record.get('method')!='host-templates' or record.get('directory')!=spec['source'] or len(docs)!=1
            or docs[0].get('source')!=spec['registry-source'] or docs[0].get('kind')!='domain-registry'):
        raise Invalid('地区模板报告的来源或清单不符')
    roots=record.get('registry-domains',[])
    if not isinstance(roots,list) or any(not isinstance(root,str) for root in roots):
        raise Invalid('地区模板报告没有完整的品牌域名清单')
    rows,_=materialize(spec,record.get('templates',[]),record.get('literal-hosts',[]),'\n'.join(roots))
    if set(docs[0]['rows'])|set(docs[0]['shared-rows'])!=rows:
        raise Invalid('地区模板报告的主机与发布范围不符')
