"""从公开资料提取规则。具体产品、地区和用途由 catalog.json 声明。"""
from html.parser import HTMLParser
from ipaddress import ip_network
import re
from urllib.parse import urlsplit

from maintain import HostTables, AppleTables, Invalid, read_rules, valid_host


def within(host, roots):
    return any(host == root or host.endswith('.'+root) for root in roots)


def host_table(text, recipe):
    parser = AppleTables()
    parser.feed(text)
    for section in recipe['sections']:
        records = parser.rows.get(section)
        if not records:
            raise Invalid('来源缺少端点表：'+section)
        for raw, purpose in records:
            host = raw.strip().casefold()
            wildcard = host.startswith('*.')
            host = host[2:] if wildcard else host
            if not valid_host(host):
                continue
            for scope in recipe['select']:
                if wildcard != scope.get('wildcards', False) or within(host, scope.get('exclude', ())):
                    continue
                if host not in scope.get('exact', ()) and not within(host, scope.get('roots', ())):
                    continue
                desc = purpose.strip().casefold()
                if 'role' in scope and desc not in {s.casefold() for s in scope['role']}:
                    continue
                if 'purpose-contains' in scope and not any(s.casefold() in desc for s in scope['purpose-contains']):
                    continue
                yield ('DOMAIN-SUFFIX,' if wildcard else 'DOMAIN,')+host
                break


class LabelledLists(HTMLParser):
    """Collect the list immediately following a named paragraph, not addresses elsewhere."""
    def __init__(self, labels):
        super().__init__()
        self.labels=labels
        self.paragraph=self.item=self.pending=self.active=None
        self.rows={}
    def handle_starttag(self,tag,attrs):
        if self.pending:
            if tag=='ul':
                self.active=self.pending
                if self.active in self.rows:
                    raise Invalid('重复的地址清单：'+self.active)
                self.rows[self.active]=[]
            self.pending=None
        if tag=='p' and self.active is None: self.paragraph=[]
        if tag=='li' and self.active is not None: self.item=[]
    def handle_data(self,text):
        if self.item is not None: self.item.append(text)
        elif self.paragraph is not None: self.paragraph.append(text)
    def handle_endtag(self,tag):
        if tag=='p' and self.paragraph is not None:
            title=''.join(self.paragraph).strip()
            self.pending=title if title in self.labels else None
            self.paragraph=None
        elif tag=='li' and self.item is not None:
            self.rows[self.active].append(''.join(self.item).strip())
            self.item=None
        elif tag=='ul': self.active=None


def labelled_networks(recipe,text):
    parser=LabelledLists(recipe['lists'])
    parser.feed(text)
    for title,bounds in recipe['lists'].items():
        if not parser.rows.get(title): raise Invalid('缺少地址清单：'+title)
        parents=[ip_network(p) for p in bounds['parents']]
        for value in parser.rows[title]:
            try: net=ip_network(value)
            except ValueError as exc: raise Invalid('地址格式变化：'+title) from exc
            if ('/' not in value or net.version!=bounds['family'] or not net.is_global
                or net.prefixlen<bounds['min-prefix'] or not any(net.subnet_of(p) for p in parents)):
                raise Invalid('地址超出已确认的发布范围：'+title)
            yield ('IP-CIDR,' if net.version==4 else 'IP-CIDR6,')+str(net)+',no-resolve'


def endpoint_sets(recipe,text):
    parser=HostTables()
    parser.feed(text)
    found=set()
    for section in recipe['sections']:
        for cells in parser.rows[section]:
            if not cells[0].isdigit() or (key:=int(cells[0])) not in recipe['sets']:
                continue
            if len(cells)!=5: raise Invalid('端点表的列发生变化：'+section)
            found.add(key)
            for value in re.split(r'[,\s]+',cells[3].strip().casefold()):
                wildcard=value.startswith('*.')
                host=value[2:] if wildcard else value
                if not valid_host(host): continue
                if within(host,recipe.get('roots',())):
                    yield ('DOMAIN-WILDCARD,' if wildcard else 'DOMAIN,')+value
                elif not wildcard and host in recipe.get('exact',()):
                    yield 'DOMAIN,'+host
    if found!=set(recipe['sets']): raise Invalid('端点表缺少已订阅的行：'+str(sorted(set(recipe['sets'])-found)))


def http_provider_hosts(recipe, text):
    """Read only the HTTP discovery lists, never DNS resolvers or update URLs."""
    sections=set(recipe['sections'])
    hits={}
    active=None
    for line in text.splitlines():
        if line and not line.startswith(' '):
            header=re.match(r'^- `([A-Z0-9_]+)` ',line)
            active=header[1] if header and header[1] in sections else None
            if active:
                if active in hits: raise Invalid('重复的 HTTP 出口查询清单：'+active)
                hits[active]=set()
        if not active: continue
        item=re.fullmatch(r'  - `([a-z0-9-]+)` using \[[^\]]+\]\((https://[^\s()]+)\)\s*',line)
        if not item or not (scope:=recipe['providers'].get(item[1])): continue
        url=urlsplit(item[2])
        host=url.hostname or ''
        if (url.netloc!=host or not valid_host(host) or url.query or url.fragment
                or (url.path or '/') not in scope['paths']): continue
        if host in scope.get('exact',()) or within(host,scope.get('roots',())):
            hits[active].add('DOMAIN,'+host)
    if set(hits)!=sections or not all(hits.values()):
        raise Invalid('HTTP 出口查询清单缺失或为空')
    return set.union(*hits.values())


def extract_rows(recipe, text):
    form = recipe['format']
    if form == 'http-provider-lists':
        return http_provider_hosts(recipe,text)
    if form == 'service-default-host':
        # Scope the option to the named service, not comments, other APIs or example URLs.
        source=re.sub(r'/\*.*?\*/','',text,flags=re.S)
        source=re.sub(r'(?m)^\s*//[^\n]*','',source)
        block=re.search(r'(?ms)^service\s+'+re.escape(recipe['service'])+r'\s*\{(.*?)^\}',source)
        found=re.findall(r'(?m)^\s*option\s+\(google\.api\.default_host\)\s*=\s*"([^"]+)"\s*;',block[1] if block else '')
        if len(found)!=1 or not valid_host(found[0]) or not within(found[0],recipe['roots']) or found[0] in recipe['roots']:
            raise Invalid('服务定义缺少可信的默认 API 主机：'+recipe['service'])
        return {'DOMAIN,'+found[0]}
    if form == 'labelled-networks':
        return set(labelled_networks(recipe,text))
    if form == 'endpoint-sets':
        return set(endpoint_sets(recipe,text))
    if form == 'host-table':
        return set(host_table(text, recipe))
    if form == 'rules':
        exact = set(recipe['exact'])
        return {f'DOMAIN,{host}' for row in read_rules(text)
                for kind, host, *flags in [row.split(',')]
                if kind in ('DOMAIN','DOMAIN-SUFFIX') and not flags and host in exact}
    if form == 'annotated-domains':
        pattern = re.compile(recipe['host-pattern'])
        return {'DOMAIN,'+parts[1] for line in text.splitlines()
                for parts in [[v.strip() for v in line.split(',')]]
                if len(parts)==3 and parts[0]=='DOMAIN' and parts[2]==recipe['tag']
                and valid_host(parts[1]) and pattern.fullmatch(parts[1])}
    if form == 'https-hosts':
        # URL authority only; a domain in a path, username or lookalike suffix is not evidence.
        roots=set(recipe.get('workspace-roots', ()))
        exact=set(recipe.get('exact', ()))
        found=set()
        for match in re.finditer(r"""https://([^/\s"'<>?#\\]+)""",text):
            authority=match[1]
            if '@' in authority:
                continue
            host=urlsplit('https://'+authority).hostname
            if not host:
                continue
            if host in exact:
                found.add('DOMAIN,'+host)
            # Documented workspace placeholder or a single real workspace label.
            parts=host.split('.',1)
            for root in (host, parts[1] if len(parts)>1 else ''):
                if root in roots and (host==root or valid_host(host) or
                                      parts[0] in ('{workspaceid}','{workspace-id}')):
                    found.add('DOMAIN-SUFFIX,'+root)
        return found
    if form == 'named-hosts':
        return {'DOMAIN,'+host for host in recipe['exact']
                if re.search(r'(?<![\w.-])'+re.escape(host)+r'(?![\w-]|\.[\w-])',text,re.I)}
    raise Invalid('未知端点资料格式：'+form)
