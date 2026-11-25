"""Public-source readers: common. Read data without executing source code."""
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit
from loon_rules import domains as domain_scope
from loon_rules.sources.formats.html import HostTables, HIDDEN_HTML
from loon_rules.rules import Invalid, read_rules
HIDDEN=HIDDEN_HTML

def within(host, roots):
    return any((host == root or host.endswith('.' + root) for root in roots))


def public_domain_pattern(value, *, platforms=()):
    if not isinstance(value,str):raise Invalid('服务域名字段不是字符串')
    try:value=value.removesuffix('.').encode('idna').decode('ascii').casefold()
    except UnicodeError as exc:raise Invalid('服务域名编码无效') from exc
    pattern=bool(re.search(r'[*?\[\]]',value))
    row=read_rules(('DOMAIN-WILDCARD,' if pattern else 'DOMAIN,')+value)[0]
    tail=domain_scope.public_host(domain_scope.fixed_tail(value))
    suffix,private=domain_scope.current().suffix(tail)
    if private and (pattern or tail==suffix) and not within(tail, platforms):
        return None  # A private hosting pattern can cross tenants even below a regional label.
    return row

class DestinationTables(HostTables):
    """Only read rows below the vendor's host, port and purpose headings."""

    def __init__(self):
        super().__init__()
        self.matched = False
        self.heading = False

    def handle_starttag(self, tag, attrs):
        if tag in HIDDEN or self.hidden:
            super().handle_starttag(tag,attrs);return
        if tag == 'table':
            self.heading = False
        if tag in ('li', 'p') and self.cell is not None:
            self.cell.append(' ')
        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in HIDDEN or self.hidden:
            super().handle_endtag(tag);return
        super().handle_endtag(tag)
        if tag == 'table':
            self.heading = False

    def record(self, row):
        if [c.casefold() for c in row] == ['destination host', 'ports', 'purpose']:
            self.matched = self.heading = True
        elif self.heading and len(row) == 3:
            super().record(row)

class LabelledLists(HTMLParser):
    """Collect the list immediately following a named paragraph, not addresses elsewhere."""

    def __init__(self, labels, *, contains=False, allow_identical=False, subdomain_labels=()):
        super().__init__()
        self.labels = labels
        self.contains = contains
        self.allow_identical = allow_identical
        self.capture = None
        self.paragraph = self.item = self.pending = self.active = None
        self.rows = {}
        self.hidden = 0
        self.subdomain_labels = tuple(label.casefold() for label in subdomain_labels)
        self.parents = []

    def handle_starttag(self, tag, attrs):
        if tag in HIDDEN:
            self.hidden += 1
        if self.hidden:
            return
        if tag == 'ul' and self.active is not None:
            text=''.join(self.item or ()).strip()
            if not self.subdomain_labels or not any(text.casefold().endswith(label) for label in self.subdomain_labels):
                raise Invalid('用途域名清单出现未确认的嵌套列表')
            field=text.partition(':')[0].strip()
            parent=public_domain_pattern(field)
            if parent is None or not parent.startswith('DOMAIN,'):
                raise Invalid('子域清单的上级不是单个公开主机')
            self.parents.append((self.item,parent.split(',')[1]))
            self.item=None
            return
        if self.pending:
            if tag == 'ul':
                self.active = self.pending
                if self.active in self.rows and (not self.allow_identical):
                    raise Invalid('重复的地址清单：' + self.active)
                self.capture = []
            if tag != 'div':
                self.pending = None
        if tag == 'p' and self.active is None:
            self.paragraph = []
        if tag == 'li' and self.active is not None:
            self.item = []

    def handle_data(self, text):
        if self.hidden:
            return
        if self.pending and text.strip():
            self.pending = None
        if self.item is not None:
            self.item.append(text)
        elif self.paragraph is not None:
            self.paragraph.append(text)

    def handle_endtag(self, tag):
        if tag in HIDDEN:
            self.hidden = max(0, self.hidden - 1)
            return
        if self.hidden:
            return
        if tag == 'p' and self.paragraph is not None:
            title = ''.join(self.paragraph).strip()
            self.pending = next((label for label in self.labels if label.casefold() in title.casefold()), None) if self.contains else title if title in self.labels else None
            self.paragraph = None
        elif tag == 'li' and self.item is not None:
            value=''.join(self.item).strip()
            if self.parents:
                for host in re.split(r'[,\s]+',value.partition(':')[0]):
                    row=public_domain_pattern(host)
                    if row is None or not domain_scope.covers('DOMAIN-SUFFIX,'+self.parents[-1][1],row):
                        raise Invalid('嵌套主机不属于声明的上级子域')
            self.capture.append(value)
            self.item = None
        elif tag == 'ul' and self.active is not None:
            if self.parents:
                self.item,_=self.parents.pop()
                return
            if self.active in self.rows and set(self.rows[self.active]) != set(self.capture):
                raise Invalid('同一用途的重复清单内容不同：' + self.active)
            self.rows.setdefault(self.active, self.capture)
            self.active = None
            self.capture = None

class HeadingSectionText(HTMLParser):

    def __init__(self, section):
        super().__init__()
        self.section = section
        self.active = False
        self.level = 0
        self.found = 0
        self.text = []
        self.hidden = 0
        self.examples = []
        self.code = None

    def handle_starttag(self, tag, attrs):
        if tag in HIDDEN:
            self.hidden += 1
        if self.hidden:
            return
        if re.fullmatch('h[1-6]', tag):
            level = int(tag[1])
            if self.active and level <= self.level:
                self.active = False
            if dict(attrs).get('id') == self.section:
                self.active = True
                self.level = level
                self.found += 1
        if self.active and tag in ('p', 'li', 'br'):
            self.text.append('\n')
        if self.active and tag=='code':self.code=[]

    def handle_endtag(self, tag):
        if tag in HIDDEN:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag=='code' and self.code is not None:
            self.examples.append(''.join(self.code));self.code=None
        elif self.active and tag in ('p', 'li'):
            self.text.append('\n')

    def handle_data(self, value):
        if self.active and (not self.hidden):
            self.text.append(value)
            if self.code is not None:self.code.append(value)

class PurposeFragments(HTMLParser):
    """Read visible examples, links and list items, excluding page scripts."""

    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.code = None
        self.link = None
        self.examples = []
        self.links = []
        self.href = ''
        self.item = None
        self.depth = 0
        self.items = []
        self.paragraph = None
        self.paragraphs = []
        self.paragraph_fields = []
        self.inline_code = None
        self.inline_fields = []
        self.metadata = {}
        self.canonical = []
        self.titles = []
        self.document_title = None
        self.broken_title = False

    def handle_starttag(self, tag, attrs):
        if tag in HIDDEN:
            self.hidden += 1
        if self.hidden:
            return
        attrs = dict(attrs)
        if tag == 'title':
            if self.document_title is not None:
                self.broken_title = True
            self.document_title = []
        if tag == 'meta' and (name := attrs.get('property')):
            self.metadata.setdefault(name, []).append(attrs.get('content', ''))
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical.append(attrs.get('href', ''))
        if tag == 'p':
            self.paragraph = []
            self.inline_fields=[]
        if tag=='code' and self.paragraph is not None:self.inline_code=[]
        if tag == 'pre':
            self.code = []
        elif tag == 'a':
            self.link = []
            self.href = attrs.get('href', '')
        elif tag == 'br' and self.code is not None:
            self.code.append('\n')
        elif tag == 'li':
            if self.item is None:
                self.item = []
            self.depth += 1

    def handle_data(self, value):
        if self.hidden:
            return
        if self.document_title is not None:
            self.document_title.append(value)
        if self.code is not None:
            self.code.append(value)
        if self.link is not None:
            self.link.append(value)
        if self.item is not None:
            self.item.append(value)
        if self.paragraph is not None:
            self.paragraph.append(value)
            if self.inline_code is not None:self.inline_code.append(value)

    def handle_endtag(self, tag):
        if tag in HIDDEN:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden:
            if tag == 'title' and self.document_title is not None:
                self.titles.append(' '.join(''.join(self.document_title).split()))
                self.document_title = None
            if tag == 'p' and self.paragraph is not None:
                self.paragraphs.append(' '.join(''.join(self.paragraph).split()))
                self.paragraph_fields.append((''.join(self.paragraph),self.inline_fields))
                self.paragraph = None
                self.inline_code=None;self.inline_fields=[]
            if tag=='code' and self.inline_code is not None and self.paragraph is not None:
                self.inline_fields.append((''.join(self.inline_code),len(''.join(self.paragraph))))
                self.inline_code=None
            if tag == 'pre' and self.code is not None:
                self.examples.append(''.join(self.code))
                self.code = None
            elif tag == 'a' and self.link is not None:
                self.links.append((self.href, ' '.join(''.join(self.link).split())))
                self.link = None
            elif tag == 'li' and self.item is not None:
                self.depth -= 1
                if not self.depth:
                    self.items.append(' '.join(''.join(self.item).split()))
                    self.item = None

def product_host(host):
    host = domain_scope.public_host(host)
    suffixes = domain_scope.current()
    root = suffixes.registrable(host)
    if root is None and (not suffixes.suffix(host)[1]):
        raise Invalid('不能把公共注册后缀归给产品')
    return ('DOMAIN-SUFFIX,' if host == root else 'DOMAIN,') + host

def https_product_host(value):
    url = urlsplit(value)
    if url.scheme != 'https' or not url.hostname or url.username is not None:
        raise Invalid('产品入口不是公开 HTTPS 名称')
    return product_host(url.hostname)
