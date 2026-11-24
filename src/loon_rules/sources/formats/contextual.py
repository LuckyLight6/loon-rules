"""Read endpoints only inside declared domain sections, nested instructions or server fields."""
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit

from loon_rules import domains as domain_scope
from loon_rules.sources.formats.html import HostTables
from loon_rules.rules import Invalid
from .common import public_domain_pattern,HIDDEN


class SectionTables(HostTables):
    def __init__(self,sections):
        super().__init__();self.sections=set(sections);self.found={s:0 for s in sections}
        self.active=None;self.level=0;self.hidden=0

    def handle_starttag(self,tag,attrs):
        if tag in HIDDEN:self.hidden+=1
        if self.hidden:return
        if re.fullmatch(r'h[1-6]',tag):
            level=int(tag[1]);section=dict(attrs).get('id')
            if self.active and level<=self.level:self.active=None
            if section in self.sections:
                self.active=section;self.level=level;self.found[section]+=1
        if self.cell is not None and tag in ('p','li','br'):self.cell.append(' ')
        super().handle_starttag(tag,attrs)

    def handle_endtag(self,tag):
        if tag in HIDDEN:self.hidden=max(0,self.hidden-1);return
        if self.hidden:return
        if self.cell is not None and tag in ('p','li','code'):self.cell.append(' ')
        super().handle_endtag(tag)

    def handle_data(self,data):
        if not self.hidden:super().handle_data(data)

    def record(self,row):
        if self.active:self.rows[self.active].append(row)


def purpose_domain_table(recipe,text):
    table=SectionTables(recipe['sections']);table.feed(text)
    scope=recipe.get('domain-scope','listed')
    if scope not in ('listed','domain-and-subdomains'):raise Invalid('自营域名表的子域匹配约定无效')
    wanted=[s.casefold() for s in recipe.get('purpose-prefixes',())]
    result=set()
    for section in recipe['sections']:
        rows=table.rows[section]
        if table.found[section]!=1 or recipe['headers'] not in rows:
            raise Invalid('自营域名表缺少章节或标题列：'+section)
        for cells in rows:
            if cells==recipe['headers'] or len(cells)!=2:continue
            if wanted and not any(cells[1].casefold().startswith(p) for p in wanted):continue
            for value in re.split(r'[,\s]+',cells[0].strip()):
                if not value:continue
                row=public_domain_pattern(value)
                if row is None:continue
                if scope=='domain-and-subdomains':
                    base=value.removeprefix('*.')
                    if re.search(r'[*?\[\]]',base):raise Invalid('整域匹配约定不能用于租户或主机前缀通配符')
                    row='DOMAIN-SUFFIX,'+domain_scope.public_host(base)
                result.add(row)
    if not result:raise Invalid('自营域名表缺少所选用途')
    return result


class NestedInstructions(HTMLParser):
    def __init__(self):
        super().__init__();self.stack=[];self.nodes=[];self.hidden=0;self.code=None

    def handle_starttag(self,tag,attrs):
        if tag in HIDDEN:self.hidden+=1
        if self.hidden:return
        if tag=='li':
            node={'text':[],'children':[],'fields':[]}
            if self.stack:self.stack[-1]['children'].append(node)
            self.stack.append(node);self.nodes.append(node)
        elif tag=='br' and self.stack:self.stack[-1]['text'].append(' ')
        elif tag=='code' and self.stack:
            node=self.stack[-1];self.code=(node,[],''.join(node['text']).casefold())

    def handle_endtag(self,tag):
        if tag in HIDDEN:self.hidden=max(0,self.hidden-1);return
        if self.hidden:return
        if tag=='li' and self.stack:self.stack.pop()
        elif tag=='code' and self.stack:
            if self.code:
                node,value,preceding=self.code;node['fields'].append((''.join(value).strip(),preceding));self.code=None
            self.stack[-1]['text'].append(' ')

    def handle_data(self,data):
        if self.stack and not self.hidden:
            self.stack[-1]['text'].append(data)
            if self.code:self.code[1].append(data)


def nested_purpose_domains(recipe,text):
    parser=NestedInstructions();parser.feed(text);result=set();matched=0
    for node in parser.nodes:
        if recipe['parent-contains'].casefold() not in ''.join(node['text']).casefold():continue
        matched+=1
        if marker:=recipe.get('value-after'):
            _,sep,tail=''.join(node['text']).casefold().partition(marker.casefold())
            if not sep:raise Invalid('网络说明缺少已声明的主机字段标签')
            values=re.split(r'[,\s]+',tail.strip()) if tail.strip() else []
        else:
            values=[value for value,before in node['fields'] if recipe['parent-contains'].casefold() in before]
            for child in node['children']:
                if child['children']:raise Invalid('网络主机清单出现未确认的嵌套用途')
                values.extend(re.split(r'[,\s]+',''.join(child['text']).strip()))
        if not values:raise Invalid('网络说明缺少其下的主机字段')
        for value in values:
            row = public_domain_pattern(value)
            if row is None:
                raise Invalid('网络主机清单含共享平台范围，不能静默跳过')
            result.add(row)
    if not matched or not result:raise Invalid('网络说明缺少指定用途及其主机')
    return result


class LabelledServers(HTMLParser):
    def __init__(self):
        super().__init__();self.divs=[];self.hidden=0;self.code=None;self.paragraph=None;self.pairs=[]

    def handle_starttag(self,tag,attrs):
        if tag in HIDDEN:self.hidden+=1
        if self.hidden:return
        if tag=='div':self.divs.append({'code':None})
        if self.divs and tag=='code':self.code=(len(self.divs),[])
        if self.divs and tag=='p':self.paragraph=(len(self.divs),[])

    def handle_data(self,data):
        if self.hidden:return
        if self.code:self.code[1].append(data)
        if self.paragraph:self.paragraph[1].append(data)

    def handle_endtag(self,tag):
        if tag in HIDDEN:self.hidden=max(0,self.hidden-1);return
        if self.hidden:return
        if tag=='code' and self.code:
            depth,value=self.code
            if depth==len(self.divs):self.divs[-1]['code']=''.join(value).strip()
            self.code=None
        if tag=='p' and self.paragraph:
            depth,purpose=self.paragraph
            if depth==len(self.divs) and self.divs[-1]['code'] is not None:
                self.pairs.append((self.divs[-1]['code'],''.join(purpose).strip()))
                self.divs[-1]['code']=None
            self.paragraph=None
        if tag=='div' and self.divs:self.divs.pop()


def labelled_url_pairs(recipe,text):
    parser=LabelledServers();parser.feed(text);result=set();seen=set()
    wanted=[s.casefold() for s in recipe['purpose-prefixes']]
    scope=recipe.get('scope','exact')
    if scope not in ('exact','source-root'):raise Invalid('服务器字段的归属范围无效')
    source=urlsplit(recipe['source'])
    root=domain_scope.current().registrable(domain_scope.public_host(source.hostname or ''))
    if scope=='source-root' and not root:raise Invalid('服务器资料没有可确认的提供方注册域')
    for value,purpose in parser.pairs:
        if not any(purpose.casefold().startswith(p) for p in wanted):continue
        seen.add(purpose.casefold());url=urlsplit(value)
        if url.scheme not in ('https','wss') or not url.hostname or url.username is not None or url.query or url.fragment:
            raise Invalid('服务器用途字段不是公开 HTTPS 或 WSS 入口')
        host=domain_scope.public_host(url.hostname)
        if scope=='source-root' and domain_scope.current().registrable(host)==root:
            result.add('DOMAIN-SUFFIX,'+root)
        else:result.add('DOMAIN,'+host)
    if not result or any(not any(p.startswith(r.casefold()) for p in seen) for r in recipe.get('required-prefixes',())):
        raise Invalid('服务器资料缺少必需的用途字段')
    return result


def markdown_purpose_endpoints(recipe,text):
    """Read formatted server URLs in labelled list items, inside one named section."""
    text=re.sub(r'(?s)<!--.*?-->','',text)
    for tag in HIDDEN:
        text=re.sub(r'(?is)<'+tag+r'\b[^>]*>.*?</'+tag+r'\s*>','',text)
    active=0;found=0;fence=None;blocks=[];block=[]
    for line in text.splitlines():
        if marker:=re.match(r'^\s*(`{3,}|~{3,})',line):
            token=marker[1]
            if fence is None:
                if block:blocks.append(' '.join(block));block=[]
                fence=token
            elif token[0]==fence[0] and len(token)>=len(fence):fence=None
            continue
        if fence:continue
        if heading:=re.match(r'^(#{1,6})\s+(.+?)\s*#*\s*$',line):
            level=len(heading[1])
            if active and level<=active:
                if block:blocks.append(' '.join(block));block=[]
                active=0
            if heading[2].casefold()==recipe['section'].casefold():
                active=level;found+=1
            continue
        if not active:continue
        if re.match(r'^[-*+]\s+',line) or not line.strip():
            if block:blocks.append(' '.join(block));block=[]
            if line.strip():block=[line]
        elif block:block.append(line.strip())
    if block:blocks.append(' '.join(block))
    if found!=1:raise Invalid('端点说明的用途章节缺失或重复')
    schemes=set(recipe.get('schemes',('https','wss')))
    if not schemes or schemes-{'https','wss'}:raise Invalid('端点说明的连接协议无效')
    result=set()
    formatted=re.compile(r'\*\*([a-zA-Z][a-zA-Z0-9+.-]*://[^\s*<>]+)\*\*|`([a-zA-Z][a-zA-Z0-9+.-]*://[^\s`<>]+)`')
    for block in blocks:
        if recipe['label-contains'].casefold() not in block.casefold():continue
        for values in formatted.findall(block):
            value=next(v for v in values if v);url=urlsplit(value)
            if url.scheme not in schemes or not url.hostname or url.username is not None or url.query or url.fragment:
                raise Invalid('端点字段含未确认的协议、凭据或参数')
            result.add('DOMAIN,'+domain_scope.public_host(url.hostname))
    if not result:raise Invalid('用途章节没有格式明确的服务器入口')
    return result
