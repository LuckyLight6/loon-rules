"""Public-source readers: documents. Read data without executing source code."""
from html.parser import HTMLParser
import json
import re
from urllib.parse import urlsplit
from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid, valid_host
from .common import within, LabelledLists, PurposeFragments, product_host, https_product_host, HeadingSectionText, public_domain_pattern

class BrandRegionLinks(HTMLParser):

    def __init__(self, recipe):
        super().__init__()
        brand = recipe['brand-label']
        if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', brand):
            raise Invalid('地区链接缺少有效品牌')
        self.pattern = re.compile(re.escape(brand) + '\\.(?:com|net|[a-z]{2}|(?:co|com)\\.[a-z]{2})\\Z')
        self.excluded = set(recipe.get('excluded-tlds', ()))
        self.rows = set()

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        href = dict(attrs).get('href')
        if not href:
            return
        url = urlsplit(href)
        if url.scheme not in ('http', 'https', '') or not url.hostname or url.username is not None:
            return
        root = url.hostname.removeprefix('www.')
        if self.pattern.fullmatch(root) and root.rsplit('.', 1)[-1] not in self.excluded:
            self.rows.add('DOMAIN-SUFFIX,' + root)

def parse_help_center_domains(recipe, text):
    articles = json.loads(text).get('articles')
    result = set()
    if not isinstance(articles, list) or not articles:
        raise Invalid('官方帮助中心文章索引为空')
    for article in articles:
        url = urlsplit(article.get('html_url', ''))
        if url.scheme != 'https' or not url.hostname or url.username is not None:
            continue
        host = domain_scope.public_host(url.hostname)
        root = domain_scope.current().registrable(host)
        if root and root.split('.')[0] == recipe['root-brand']:
            result.add('DOMAIN-SUFFIX,' + root)
    if not result:
        raise Invalid('帮助中心没有所声明品牌的自营站点')
    return result

def parse_purpose_domain_lists(recipe, text):
    for field in ('labels','nested-subdomain-labels','item-purpose-prefixes','item-purpose-contains'):
        if field!='labels' and field not in recipe:continue
        values=recipe.get(field)
        if not isinstance(values,list) or not values or any(not isinstance(value,str) or not value.strip() for value in values):
            raise Invalid('用途清单的 '+field+' 必须是非空文字数组')
    if 'allow-identical-duplicates' in recipe and type(recipe['allow-identical-duplicates']) is not bool:
        raise Invalid('用途清单的重复项开关必须为布尔值')
    style=recipe.get('item-purpose-style','colon')
    if style not in ('colon','parentheses'):raise Invalid('用途清单的条目格式无效')
    parser = LabelledLists(recipe['labels'], contains=True, allow_identical=recipe.get('allow-identical-duplicates', False),
                           subdomain_labels=recipe.get('nested-subdomain-labels',()))
    parser.feed(text)
    result = set()
    for label in recipe['labels']:
        if not parser.rows.get(label):
            raise Invalid('官方网络资料缺少用途清单：' + label)
        for item in parser.rows[label]:
            field,separator,purpose=item.partition('(' if style=='parentheses' else ':')
            if required:=recipe.get('item-purpose-prefixes'):
                if not any(purpose.strip().casefold().startswith(prefix.casefold()) for prefix in required):continue
            if required:=recipe.get('item-purpose-contains'):
                if not any(phrase.casefold() in purpose.casefold() for phrase in required):continue
            if style=='parentheses' and (not separator or not purpose.rstrip().endswith(')')):
                raise Invalid('用途清单缺少完整的括号说明')
            for host in re.split('[,\\s]+', field.strip()):
                if row:=public_domain_pattern(host):
                    result.add(row)
    if not result:
        raise Invalid('网络用途清单没有可独立归属的公开主机')
    return result

def parse_product_domain_statements(recipe, text):
    guide = PurposeFragments()
    guide.feed(text)
    result = set()
    if recipe.get('code-only'):
        marker=recipe.get('annotation');part=recipe.get('part','all');annotated_count=0
        if part not in ('all','annotated','other') or (part!='all' and not marker):
            raise Invalid('域名注释的选择方式无效')
        for paragraph,fields in guide.paragraph_fields:
            if not all(phrase.casefold() in paragraph.casefold() for phrase in recipe['paragraph-contains']):continue
            start=0
            if label:=recipe.get('value-after'):
                positions=list(re.finditer(re.escape(label),paragraph,re.I))
                if len(positions)!=1:raise Invalid('域名说明的字段标签缺失或重复')
                start=positions[0].end()
            for raw,end in fields:
                if end-len(raw)<start:continue
                annotated=bool(marker and re.match(r'\s*'+re.escape(marker)+r'(?!\w)',paragraph[end:],re.I))
                annotated_count+=annotated
                if part=='annotated' and not annotated or part=='other' and annotated:continue
                value=raw.strip()
                if '://' in value:
                    url=urlsplit(value)
                    if url.scheme not in ('https','wss') or not url.hostname or url.username is not None or url.query or url.fragment:
                        raise Invalid('说明中的代码字段不是公开服务器入口')
                    value=url.hostname
                if row:=public_domain_pattern(value):result.add(row)
        if marker and not annotated_count:raise Invalid('域名说明缺少要求的地区注释')
        if not result:raise Invalid('官方说明没有所选的代码域名字段')
        return result
    if recipe.get('annotation'):raise Invalid('地区注释必须来自明确的代码字段')
    schemes=recipe.get('reference-schemes',['https'])
    if (not isinstance(schemes,list) or not schemes
            or any(scheme not in ('http','https') for scheme in schemes)):
        raise Invalid('产品参考链接的协议声明无效')
    protocol='(?:'+ '|'.join(re.escape(scheme) for scheme in schemes)+')://'
    for paragraph in guide.paragraphs:
        if not all((phrase.casefold() in paragraph.casefold() for phrase in recipe['paragraph-contains'])):
            continue
        for host in re.findall('(?<![\\w@./-])(?:'+protocol+')?([a-z0-9][a-z0-9.-]*\\.[a-z]{2,})(?![\\w@-]|\\.[\\w-])', paragraph.casefold()):
            result.add(product_host(host))
    if not result:
        raise Invalid('官方资料缺少已选产品用途的域名说明')
    return result

def parse_product_role_links(recipe, text):
    guide = PurposeFragments()
    guide.feed(text)
    result = {https_product_host(url) for url, label in guide.links if label in recipe['labels']}
    if not result:
        raise Invalid('官方资料缺少指定用途的产品入口')
    return result

def parse_site_identity(recipe, text):
    guide = PurposeFragments()
    guide.feed(text)
    scope=recipe.get('scope','canonical')
    if scope=='source-root':
        field=recipe.get('brand-field','og:site_name');match=recipe.get('brand-match','exact')
        if field not in ('og:site_name','og:title') or match not in ('exact','word'):
            raise Invalid('产品站点的品牌字段或匹配方式无效')
        identity=guide.metadata.get(field,[])
        if len(identity)!=1 or len(guide.canonical)!=1 or len(guide.metadata.get('og:url',[]))>1:
            raise Invalid('产品站点身份或入口数量变化')
        brand=recipe['brand'].casefold();value=identity[0].casefold()
        if not (value==brand if match=='exact' else re.search(r'(?<!\w)'+re.escape(brand)+r'(?!\w)',value)):
            raise Invalid('产品站点的品牌标识不符')
        def root(value):
            url=urlsplit(value)
            if url.scheme!='https' or not url.hostname or url.username is not None or url.query or url.fragment:
                raise Invalid('产品站点身份不是无凭据的 HTTPS 入口')
            host=domain_scope.public_host(url.hostname);suffixes=domain_scope.current()
            if suffixes.suffix(host)[1]:raise Invalid('共享托管站点不能认领整个产品根域')
            return suffixes.registrable(host)
        source=root(recipe['source'])
        if not source or any(root(url)!=source for url in guide.canonical+guide.metadata.get('og:url',[])):
            raise Invalid('产品站点的来源与身份 URL 不属于同一注册域')
        return {'DOMAIN-SUFFIX,'+source}
    if scope!='canonical':raise Invalid('产品站点的归属范围无效')
    if guide.metadata.get('og:site_name') != [recipe['brand']] or len(guide.canonical) != 1 or len(guide.metadata.get('og:url', [])) != 1:
        raise Invalid('产品站点身份或入口数量变化')
    canonical = https_product_host(guide.canonical[0])
    graph = https_product_host(guide.metadata['og:url'][0])
    if canonical != graph:
        raise Invalid('产品站点的 canonical 与 Open Graph 不一致')
    return {canonical}


def section_code_domains(recipe,text):
    result=set()
    for name in recipe['sections']:
        section=HeadingSectionText(name);section.feed(text)
        if section.found!=1 or not section.examples:raise Invalid('主机代码清单缺少指定章节：'+name)
        found=set()
        for example in section.examples:
            for value in example.splitlines():
                if value.strip() and (row:=public_domain_pattern(value.strip())):found.add(row)
        if not found:raise Invalid('主机代码清单没有可归属的端点：'+name)
        result.update(found)
    return result

def parse_product_entrypoints(recipe, text):
    guide = PurposeFragments()
    guide.feed(text)
    result = set()
    prefix = recipe['item-prefix'].casefold()
    for item in guide.items:
        if not item.casefold().startswith(prefix):
            continue
        for host in re.findall('(?<![\\w@./-])(?:https://)?([a-z0-9][a-z0-9.-]*\\.[a-z]{2,})(?![\\w@.-])', item[len(prefix):].casefold()):
            labels = host.split('.')
            if not valid_host(host) or labels[0] != recipe['brand-label'] or labels[-1] in ('local', 'internal', 'test', 'invalid', 'onion') or (len(labels) > 2 and (not within(host, recipe['owned-parents']))):
                raise Invalid('官方产品入口出现未确认的品牌或托管范围')
            result.add('DOMAIN,' + host)
    if not result:
        raise Invalid('官方资料缺少产品入口清单')
    return result

def parse_article_domain_list(recipe, text):
    body = json.loads(text)
    for key in recipe['body-path']:
        body = body[key]
    if not isinstance(body, str):
        raise Invalid('官方文章缺少正文')
    label = recipe['label-contains']
    parser = LabelledLists([label], contains=True)
    parser.feed(body)
    values = parser.rows.get(label, [])
    result = set()
    for host in values:
        host = host.casefold()
        labels = host.split('.')
        if not valid_host(host) or len(labels) != 2 or labels[0] != recipe['brand-label'] or (labels[-1] in ('local', 'internal', 'test', 'invalid', 'onion')):
            raise Invalid('官方清单出现尚未确认归属的域名')
        result.add('DOMAIN-SUFFIX,' + host)
    if not result:
        raise Invalid('官方域名清单缺失或为空')
    return result

def parse_brand_region_links(recipe, text):
    parser = BrandRegionLinks(recipe)
    parser.feed(text)
    return parser.rows


def host_purpose_list(recipe,text):
    section=HeadingSectionText(recipe['section']);section.feed(text)
    if section.found!=1:raise Invalid('主机用途清单的章节缺失或重复')
    wanted=[p.casefold() for p in recipe['purpose-prefixes']]
    rejected=[p.casefold() for p in recipe.get('exclude-purpose-contains',())]
    result=set();seen=set()
    for line in ''.join(section.text).splitlines():
        host,sep,purpose=line.strip().partition(' - ');purpose=purpose.casefold()
        if not sep or not any(purpose.startswith(p) for p in wanted) or any(p in purpose for p in rejected):continue
        seen.add(purpose)
        if (row:=public_domain_pattern(host)) and (not recipe.get('exact-only') or row.startswith('DOMAIN,')):
            result.add(row)
    if not result or any(not any(p.startswith(required.casefold()) for p in seen)
                         for required in recipe.get('required-prefixes',())):
        raise Invalid('主机用途清单缺少必需业务')
    return result
