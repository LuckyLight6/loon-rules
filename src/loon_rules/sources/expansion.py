"""Discover service documents from a vendor directory, then read their published endpoints."""
from concurrent.futures import ThreadPoolExecutor
import json
import re
from urllib.parse import urlsplit

from loon_rules import domains as domain_scope
from loon_rules.sources import pages as source_pages
from loon_rules.sources import sdk_pages as source_sdk_pages
from loon_rules.sources import templates as source_templates
from loon_rules.sources import profiles as source_profiles
from loon_rules.sources import bags as source_bags
from loon_rules.sources import network_agreement as source_networks
from loon_rules.rules import Invalid
from loon_rules.matching import merge_cases
from loon_rules.sources.inputs import extract_rows


IDENTIFIER = re.compile(r'[A-Za-z][A-Za-z0-9]*\Z')
VERSION = re.compile(r'[A-Za-z][A-Za-z0-9._-]*\Z')


def selected(spec, title):
    title = title.casefold()
    return (any(title.startswith(value.casefold()) for value in spec['title-prefixes'])
            and not any(title.startswith(value.casefold()) for value in spec.get('exclude-title-prefixes', ())))


def document_url(spec, name, version):
    if not IDENTIFIER.fullmatch(name) or not VERSION.fullmatch(version):
        raise Invalid('API 目录的产品或版本标识无效')
    return spec['documents-base'] + name + '.' + version + '.json'


def version_policy(spec):
    policy=spec.get('versions','preferred')
    if policy not in ('preferred','published'):raise Invalid('API 目录的版本选择无效')
    return policy


def validate(config, entries):
    for key, entry in entries.items():
        if not (spec := entry.get('expand')):
            continue
        if spec.get('method')==source_networks.METHOD:
            source_networks.validate(spec)
            if entry['mode']!='compiled' or not {item['source'] for item in spec['inputs']}<=set(entry['sources']):
                raise Invalid('网段核对来源未列入生成声明：'+key)
            continue
        if spec.get('method')==source_bags.METHOD:
            source_bags.validate(spec)
            if entry['mode']!='compiled' or spec['source'] not in entry['sources']:
                raise Invalid('公开服务配置来源未列入生成声明：'+key)
            continue
        if spec.get('method')==source_profiles.METHOD:
            if entry['mode']!='compiled' or not {spec['source'],spec['config-source']}<=set(entry['sources']):
                raise Invalid('客户端版本目录与配置来源未列入生成声明：'+key)
            source_profiles.validate(spec)
            continue
        if spec.get('method') in ('next-page', source_sdk_pages.METHOD):
            if entry['mode']!='compiled' or spec['source'] not in entry['sources']:
                raise Invalid('产品页面来源未列入生成声明：'+key)
            (source_sdk_pages if spec['method'] == source_sdk_pages.METHOD else source_pages).validate(spec)
            continue
        if spec.get('method')=='host-templates':
            if entry['mode']!='compiled' or not {spec['source'],spec['registry-source']}<=set(entry['sources']):
                raise Invalid('地区模板来源未列入生成声明：'+key)
            source_templates.validate(spec)
            continue
        version_policy(spec)
        base = urlsplit(spec.get('documents-base', ''))
        if (entry['mode'] != 'compiled' or spec.get('method') != 'api-directory'
                or spec.get('source') not in entry['sources'] or not spec.get('title-prefixes')
                or base.scheme != 'https' or not base.hostname or base.username is not None
                or base.query or base.fragment or not base.path.endswith('/')
                or type(spec.get('max-documents')) is not int or spec['max-documents'] < 1):
            raise Invalid('API 目录缺少产品范围、来源模板或请求上限：' + key)


def plan(spec, text):
    versions=version_policy(spec)
    directory = json.loads(text)
    if (directory.get('kind') != 'discovery#directoryList'
            or directory.get('discoveryVersion') != 'v1' or not isinstance(directory.get('items'), list)):
        raise Invalid('API 目录格式变化')
    documents = []
    names = set()
    for item in directory['items']:
        if (versions=='preferred' and not item.get('preferred')) or not selected(spec, item.get('title', '')):
            continue
        name, version = item['name'], item['version']
        source = document_url(spec, name, version)
        identity=name if versions=='preferred' else (name,version)
        if (item.get('kind') != 'discovery#directoryItem' or item.get('id') != name + ':' + version
                or identity in names):
            raise Invalid('API 目录的版本重复或产品标识不符')
        names.add(identity)
        documents.append({'name': name, 'version': version, 'title': item['title'], 'source': source})
    if not documents or len(documents) > spec['max-documents']:
        raise Invalid('API 目录未选到产品或超过已声明的请求上限')
    return documents


def collect(entries, downloaded, download, *, shared_hosts=()):
    plans = {}
    jobs = {}
    for key, entry in entries.items():
        if not (spec := entry.get('expand')):
            continue
        if spec.get('method')==source_networks.METHOD:
            plans[key]=source_networks.plan(spec)
        elif spec.get('method')==source_bags.METHOD:
            plans[key]=source_bags.plan(spec)
        elif spec.get('method')==source_profiles.METHOD:
            plans[key]=source_profiles.plan(spec,downloaded[spec['source']])
        elif spec.get('method')=='next-page':
            plans[key]=source_pages.plan(spec,downloaded[spec['source']])
        elif spec.get('method')==source_sdk_pages.METHOD:
            plans[key]=source_sdk_pages.plan(spec,downloaded[spec['source']])
        elif spec.get('method')=='host-templates':
            plans[key]=source_templates.plan(spec,downloaded[spec['source']])
        else:
            plans[key]={'documents':plan(spec, downloaded[spec['source']])}
        for doc in plans[key]['documents']:
            if doc['source'] in jobs:
                if (doc.get('kind') not in ('domain-registry',source_profiles.METHOD,source_bags.METHOD,source_networks.METHOD)
                        or jobs[doc['source']].get('kind')!=doc.get('kind')):
                    raise Invalid('API 目录的产品归属重叠：' + key)
            jobs[doc['source']] = doc
    def read(url):
        try:
            if url in downloaded:return downloaded[url]
            return download(url,public_profile=True) if jobs[url].get('kind')==source_profiles.METHOD else download(url)
        except (Invalid, OSError) as exc:
            raise Invalid('API 发现文档未读到：' + url + '：' + str(exc)) from exc
    with ThreadPoolExecutor(max_workers=4) as pool:
        inputs = dict(zip(jobs, pool.map(read, jobs)))
    rows = {}
    report = {}
    for key, record in plans.items():
        if record.get('method')==source_networks.METHOD:
            rows[key],report[key]=source_networks.read(entries[key]['expand'],record,inputs)
            continue
        if record.get('method')==source_bags.METHOD:
            rows[key],report[key]=source_bags.read(entries[key]['expand'],record,inputs,shared_hosts)
            continue
        if record.get('method')==source_profiles.METHOD:
            rows[key],report[key]=source_profiles.read(entries[key]['expand'],record,inputs,shared_hosts)
            continue
        if record.get('method')=='next-page':
            rows[key],report[key]=source_pages.read(entries[key]['expand'],record,inputs,shared_hosts)
            continue
        if record.get('method')==source_sdk_pages.METHOD:
            rows[key],report[key]=source_sdk_pages.read(entries[key]['expand'],record,inputs,shared_hosts)
            continue
        if record.get('method')=='host-templates':
            rows[key],report[key]=source_templates.read(entries[key]['expand'],record,inputs,shared_hosts)
            continue
        accepted = set()
        confirmed = []
        for doc in record['documents']:
            found = extract_rows({'format': 'api-discovery', 'name': doc['name'], 'version': doc['version']},
                                 inputs[doc['source']])
            shared = {row for row in found if row.split(',')[1] in shared_hosts}
            found -= shared
            accepted.update(found)
            confirmed.append({**doc, 'rows': sorted(found), 'shared-rows': sorted(shared)})
        rows[key] = sorted(accepted)
        report[key] = {'directory': entries[key]['expand']['source'], 'documents': confirmed}
    return rows, report, {url: text for url, text in inputs.items() if url not in downloaded}


def verify_report(entries, data, report, *, shared_hosts=()):
    if set(report) != {key for key, entry in entries.items() if entry.get('expand')}:
        raise Invalid('API 目录报告与产品声明不一致')
    for key, record in report.items():
        spec = entries[key]['expand']
        docs = record.get('documents', [])
        for doc in docs:
            if set(doc['rows'])&set(doc['shared-rows']):raise Invalid('发现文档同时声明专用与共用端点')
            for row in doc['shared-rows']:
                kind,host,*flags=row.split(',')
                if kind!='DOMAIN' or flags or domain_scope.public_host(host)!=host or host not in shared_hosts:
                    raise Invalid('发现文档的共用端点没有对应的范围依据：'+key)
        if spec.get('method')==source_networks.METHOD:
            source_networks.verify(spec,record)
            source_networks.verify_coverage(key,data,record)
            continue
        if spec.get('method')==source_bags.METHOD:
            source_bags.verify(spec,record)
            for doc in docs:verify_rows(key,doc['rows'],data)
            continue
        if spec.get('method')==source_profiles.METHOD:
            source_profiles.verify(spec,record)
            for doc in docs:verify_rows(key,doc['rows'],data)
            continue
        if spec.get('method')=='next-page':
            source_pages.verify(spec,record)
            for doc in docs:
                verify_rows(key,doc['rows'],data)
            continue
        if spec.get('method')==source_sdk_pages.METHOD:
            source_sdk_pages.verify(spec,record)
            source_sdk_pages.verify_inventory(spec,record,data[key])
            for doc in docs:verify_rows(key,doc['rows'],data)
            continue
        if spec.get('method')=='host-templates':
            source_templates.verify(spec,record)
            for doc in docs:verify_rows(key,doc['rows'],data)
            continue
        if record.get('method','api-directory')!='api-directory':raise Invalid('API 发现报告的资料类型不符')
        if record.get('directory') != spec['source'] or not docs or len(docs) > spec['max-documents']:
            raise Invalid('API 目录报告缺少来源或产品文档')
        names = set()
        versions=version_policy(spec)
        for doc in docs:
            identity=doc['name'] if versions=='preferred' else (doc['name'],doc['version'])
            if (doc['source'] != document_url(spec, doc['name'], doc['version'])
                    or not selected(spec, doc['title']) or identity in names):
                raise Invalid('API 目录报告的产品、版本或来源不符')
            names.add(identity)
            verify_rows(key,doc['rows'],data)


def verify_rows(key,rows,data):
    for row in rows:
        kind,host,*flags=row.split(',')
        if kind!='DOMAIN' or flags or domain_scope.public_host(host)!=host or not any(
                domain_scope.covers(actual,row) for actual in data[key]):
            raise Invalid('发现文档报告没有对应的产品规则正文：'+key)


def inventory_rows(report):
    """Expose complete API server fields without treating page examples as full lists."""
    return {key:sorted({row for doc in record['documents'] for row in doc['rows']})
            for key,record in report.items() if record.get('method','api-directory') in ('api-directory','host-templates')}


def with_cases(config,data,report):
    cases={}
    for key,record in report.items():
        if record.get('method')==source_networks.METHOD:continue
        for doc in record['documents']:
            verify_rows(key,doc['rows'],data)
            for row in doc['rows']:
                host=row.split(',')[1]
                if host in cases and cases[host]!=[key]:raise Invalid('发现资料中的服务主机归属冲突：'+host)
                cases[host]=[key]
    return merge_cases(config,cases,'发现资料')
