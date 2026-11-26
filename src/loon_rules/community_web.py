"""Keep a hosted rule publisher's build identity consistent across complete artifacts."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from loon_rules import community,rules
from loon_rules.sources.transport import source_url


def get(url):
    source_url(url)
    with TemporaryDirectory(prefix='public-community-web-') as temporary:
        folder=Path(temporary);body=folder/'body';headers=folder/'headers'
        result=subprocess.run(['curl','-q','-fsSL','--proto','=https','--proto-redir','=https','--max-redirs','2',
            '--connect-timeout','8','--max-time','30','--retry','1','--max-filesize','18000000',
            '-D',str(headers),'-o',str(body),url],capture_output=True,timeout=75)
        if result.returncode or not body.is_file():
            raise rules.Invalid('托管社区来源无法完整读取')
        blocks=[block for block in re.split(r'\r?\n\r?\n',headers.read_text()) if block.startswith('HTTP/')]
        versions=re.findall(r'(?im)^x-geosite-version:\s*(\d{14})\s*$',blocks[-1] if blocks else '')
        return body.read_bytes(),versions[0] if len(versions)==1 else None


def manifest(body):
    doc=json.loads(body)
    if (not isinstance(doc,dict) or doc.get('schema')!=2 or not isinstance(doc.get('tag'),str)
            or not re.fullmatch(r'\d{14}',doc['tag'])
            or not isinstance(doc.get('lists'),list) or not doc['lists']
            or not isinstance(doc.get('stats'),dict) or type(doc['stats'].get('lists')) is not int
            or doc['stats']['lists']!=len(doc['lists'])):
        raise rules.Invalid('托管社区清单的构建身份或完整列表无效')
    return doc['tag']


def watch(specs,previous,folder):
    accepted=dict(previous);reports=[]
    for spec in specs:
        record={'id':spec['id'],'url':spec['url'],'artifacts':[]}
        try:
            origin=urlsplit(source_url(spec['url'])).hostname
            urls=[spec['metadata'],*(item['url'] for item in spec['artifacts'])]
            if (not spec['artifacts'] or len({item['id'] for item in spec['artifacts']})!=len(spec['artifacts'])
                    or any(urlsplit(source_url(url)).hostname!=origin for url in urls)):
                raise rules.Invalid('托管来源缺少完整文件或改换了发布身份')
            tag=manifest(get(spec['metadata'])[0]);record['expected-version']=tag
            if spec['id'] in previous and tag<previous[spec['id']]['version']:
                raise rules.Invalid('托管元数据回退到较旧构建')
            def artifact(item):
                value={'id':item['id'],'url':item['url'],'format':item['format'],'products':item['products']}
                try:
                    body,version=get(item['url']);value['version']=version
                    if version!=tag:raise rules.Invalid('文件版本与本轮元数据构建不一致')
                    normalized=community.normalize(item['format'],body.decode('utf-8-sig'))
                    digest=hashlib.sha256(body).hexdigest()
                    (folder/(digest+'.source')).write_bytes(body)
                    value.update(state='normalized-for-review',sha256=digest,bytes=len(body),normalized=normalized)
                except (rules.Invalid,OSError,ValueError,KeyError,UnicodeError,subprocess.TimeoutExpired) as error:
                    value.update(state='held',reason=str(error))
                return value
            with ThreadPoolExecutor(max_workers=4) as pool:
                record['artifacts']=list(pool.map(artifact,spec['artifacts']))
            if any(item['state']=='held' for item in record['artifacts']):
                raise rules.Invalid('托管构建存在版本混用或未完整读取的文件')
            if manifest(get(spec['metadata'])[0])!=tag:
                raise rules.Invalid('读取期间托管元数据构建变化')
            state={'version':tag,'artifacts':{item['id']:{key:item[key] for key in
                   ('url','format','version','sha256','bytes')} for item in record['artifacts']}}
            old=previous.get(spec['id'])
            if old and old['version']==tag and old['artifacts']!=state['artifacts']:
                raise rules.Invalid('同一构建的文件身份或正文指纹发生变化')
            record['state']='complete-build-for-review';accepted[spec['id']]=state
        except (rules.Invalid,OSError,ValueError,KeyError,UnicodeError,subprocess.TimeoutExpired) as error:
            record.update(state='held',reason=str(error),previous_complete_retained=spec['id'] in previous)
        reports.append(record)
    return reports,accepted
