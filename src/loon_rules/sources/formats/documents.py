"""Public-source readers: documents. Read data without executing source code."""
from html.parser import HTMLParser
import json
import re
from urllib.parse import urljoin, urlsplit
from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid, valid_host
from .common import within, LabelledLists, PurposeFragments, product_host, https_product_host, HeadingSectionText, public_domain_pattern
from .resources import image_hosts

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
    if type(recipe.get('require-complete',False)) is not bool:
        raise Invalid('用途清单的完整读取开关必须为布尔值')
    if 'allow-identical-duplicates' in recipe and type(recipe['allow-identical-duplicates']) is not bool:
        raise Invalid('用途清单的重复项开关必须为布尔值')
    if 'item-separator-required' in recipe and type(recipe['item-separator-required']) is not bool:
        raise Invalid('用途清单的字段分隔要求必须为布尔值')
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
            if recipe.get('item-separator-required') and not separator:continue
            if required:=recipe.get('item-purpose-prefixes'):
                if not any(purpose.strip().casefold().startswith(prefix.casefold()) for prefix in required):continue
            if required:=recipe.get('item-purpose-contains'):
                if not any(phrase.casefold() in purpose.casefold() for phrase in required):continue
            if style=='parentheses' and (not separator or not purpose.rstrip().endswith(')')):
                raise Invalid('用途清单缺少完整的括号说明')
            for host in re.split('[,\\s]+', field.strip()):
                row=public_domain_pattern(host)
                if row is None and recipe.get('require-complete'):
                    raise Invalid('完整用途清单包含共享托管范围，不能静默省略')
                if row:result.add(row)
    if select:=recipe.get('select'):
        if (not isinstance(select,dict) or set(select)-{'roots','exact'}
                or not any(select.get(field) for field in ('roots','exact'))):
            raise Invalid('用途清单的产品范围筛选无效')
        result={row for row in result
                if within(domain_scope.fixed_tail(row.split(',')[1]),select.get('roots',()))
                or row.startswith('DOMAIN,') and row.split(',')[1] in select.get('exact',())}
    if not result:
        raise Invalid('网络用途清单没有可独立归属的公开主机')
    return result

def parse_product_domain_statements(recipe, text):
    guide = PurposeFragments()
    guide.feed(text)
    result = set()
    scope = recipe.get('domain-scope', 'listed')
    include_items = recipe.get('include-list-items', False)
    if (scope not in ('listed', 'private-platform') or type(include_items) is not bool
            or scope == 'private-platform' and recipe.get('code-only')):
        raise Invalid('用途说明的域名范围或列表选择无效')
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
    statements = guide.paragraphs + (guide.items if include_items else [])
    for paragraph in statements:
        if not all((phrase.casefold() in paragraph.casefold() for phrase in recipe['paragraph-contains'])):
            continue
        for host in re.findall('(?<![\\w@./-])(?:'+protocol+')?([a-z0-9][a-z0-9.-]*\\.[a-z]{2,})(?![\\w@-]|\\.[\\w-])', paragraph.casefold()):
            result.add(product_host(host))
    if not result:
        raise Invalid('官方资料缺少已选产品用途的域名说明')
    if scope == 'private-platform':
        platforms = set()
        for row in result:
            host = row.split(',')[1]
            suffix, private = domain_scope.current().suffix(host)
            if host != suffix or not private:
                raise Invalid('平台用途说明没有指向明确的私有托管命名空间')
            platforms.add('DOMAIN-SUFFIX,' + host)
        return platforms
    return result

def parse_product_role_links(recipe, text):
    guide = PurposeFragments()
    guide.feed(text)
    result = {https_product_host(urljoin(recipe.get('source', ''), url))
              for url, label in guide.links if label in recipe['labels']}
    if not result:
        raise Invalid('官方资料缺少指定用途的产品入口')
    return result


def csp_origins(recipe, text):
    directives = {
        'default-src', 'script-src', 'script-src-elem', 'script-src-attr',
        'style-src', 'style-src-elem', 'style-src-attr', 'img-src', 'font-src',
        'connect-src', 'media-src', 'object-src', 'frame-src', 'child-src',
        'worker-src', 'manifest-src', 'base-uri', 'form-action', 'frame-ancestors',
    }
    wanted = recipe.get('directives', [])
    scope = recipe.get('domain-scope', 'listed')
    if not wanted or not set(wanted) <= directives or scope not in ('listed', 'domain-and-subdomains'):
        raise Invalid('CSP 来源缺少明确的指令和匹配范围')
    examples = []
    if sections := recipe.get('sections'):
        for name in sections:
            section = HeadingSectionText(name)
            section.feed(text)
            if section.found != 1:
                raise Invalid('CSP 来源的章节缺失或重复')
            examples.extend(section.examples)
    else:
        page = PurposeFragments()
        page.feed(text)
        examples = page.examples
    pattern = re.compile(r'(?m)(?:^|[;\n])[ \t]*(' + '|'.join(sorted(directives))
                         + r')(?::[ \t]*|[ \t]+|$)')
    result = set()
    for example in examples:
        matches = list(pattern.finditer(example))
        for index, match in enumerate(matches):
            if match[1] not in wanted:
                continue
            end = matches[index + 1].start() if index + 1 < len(matches) else len(example)
            for token in example[match.end():end].replace(';', ' ').split():
                if token.startswith("'") or token in ('*', 'data:', 'blob:', 'https:', 'http:'):
                    continue
                url = urlsplit(token if '://' in token else 'https://' + token)
                if (url.scheme not in ('https', 'wss') or not url.hostname
                        or url.username is not None or url.query or url.fragment):
                    raise Invalid('CSP 来源包含无效或带凭据的连接地址')
                host = url.hostname
                row = public_domain_pattern(host)
                if row is None:
                    raise Invalid('CSP 包含未确认归属的共享托管范围，不能静默忽略')
                tail = domain_scope.fixed_tail(host)
                if prefixes := recipe.get('brand-prefixes'):
                    root = domain_scope.current().registrable(tail)
                    if not root or not any(root.split('.')[0].startswith(prefix) for prefix in prefixes):
                        continue
                if scope == 'domain-and-subdomains':
                    base = host.removeprefix('*.')
                    if re.search(r'[*?\[\]]', base):
                        raise Invalid('CSP 的整域匹配不接受主机前缀通配符')
                    row = 'DOMAIN-SUFFIX,' + base
                result.add(row)
    if not result:
        raise Invalid('CSP 来源没有所选用途的公开连接地址')
    return result


def parse_site_identity(recipe, text):
    guide = PurposeFragments()
    guide.feed(text)
    scope=recipe.get('scope','canonical')
    if scope == 'source-host':
        field = recipe.get('brand-field', 'og:site_name')
        if field not in ('og:site_name', 'og:title') or guide.metadata.get(field) != [recipe['brand']]:
            raise Invalid('产品来源主机缺少唯一且匹配的品牌标识')
        source = urlsplit(recipe.get('source', ''))
        if (source.scheme != 'https' or not source.hostname or source.username is not None
                or source.query or source.fragment or source.path not in ('', '/')
                or source.port not in (None, 443)):
            raise Invalid('产品来源主机必须是公开 HTTPS 根入口')
        row = public_domain_pattern(source.hostname)
        if row is None or len(guide.canonical) > 1 or len(guide.metadata.get('og:url', [])) > 1:
            raise Invalid('产品来源主机不能认领共享平台或重复身份')
        if any(https_product_host(url) != row for url in guide.canonical + guide.metadata.get('og:url', [])):
            raise Invalid('产品来源主机与页面身份不一致')
        return {row}
    if scope=='source-root':
        field=recipe.get('brand-field','og:site_name');match=recipe.get('brand-match','exact')
        if field not in ('og:site_name','og:title','html:title') or match not in ('exact','word'):
            raise Invalid('产品站点的品牌字段或匹配方式无效')
        html_title = field == 'html:title'
        identity = guide.titles if html_title else guide.metadata.get(field, [])
        if (len(identity)!=1 or (len(guide.canonical)>1 if html_title else len(guide.canonical)!=1)
                or len(guide.metadata.get('og:url',[]))>1
                or html_title and (guide.document_title is not None or guide.broken_title)):
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
        if html_title:
            origin = urlsplit(recipe['source'])
            if origin.path not in ('', '/') or origin.hostname not in (source, 'www.' + source):
                raise Invalid('HTML 标题身份只适用于独立产品的根网站')
        if not source or any(root(url)!=source for url in guide.canonical+guide.metadata.get('og:url',[])):
            raise Invalid('产品站点的来源与身份 URL 不属于同一注册域')
        return {'DOMAIN-SUFFIX,'+source}
    if scope!='canonical':raise Invalid('产品站点的归属范围无效')
    include_alias=recipe.get('include-source-alias',False)
    if type(include_alias) is not bool:
        raise Invalid('来源别名开关必须为布尔值')
    if (guide.metadata.get('og:site_name') != [recipe['brand']]
            or len(guide.metadata.get('og:url', [])) != 1 or len(guide.canonical)>1
            or not include_alias and not guide.canonical):
        raise Invalid('产品站点身份或入口数量变化')
    graph = https_product_host(guide.metadata['og:url'][0])
    canonical = https_product_host(guide.canonical[0]) if guide.canonical else graph
    if canonical != graph:
        raise Invalid('产品站点的 canonical 与 Open Graph 不一致')
    result={canonical}
    if include_alias:
        parents=recipe.get('canonical-parents')
        if (not isinstance(parents,list) or not parents
                or any(not isinstance(parent,str) or not valid_host(parent)
                       or domain_scope.current().registrable(parent) is None for parent in parents)):
            raise Invalid('网站别名缺少已核实的官方命名空间')
        identities=[urlsplit(value) for value in guide.canonical+guide.metadata['og:url']]
        if any(not within(identity.hostname,parents) for identity in identities):
            raise Invalid('网站别名的最终身份不属于已核实的官方命名空间')
        source=urlsplit(recipe.get('source',''))
        if (source.scheme!='https' or not source.hostname or source.username is not None
                or source.query or source.fragment or source.path not in ('','/')):
            raise Invalid('网站别名必须来自不带凭据和参数的 HTTPS 根入口')
        host=domain_scope.public_host(source.hostname)
        root=domain_scope.current().registrable(host)
        if not root or domain_scope.current().suffix(host)[1] or host not in (root,'www.'+root):
            raise Invalid('共享托管或业务子域不能扩大为网站别名根域')
        result.add('DOMAIN-SUFFIX,'+root)
    return result


def site_resource_hosts(recipe, text):
    identity = recipe.get('identity')
    properties = recipe.get('properties', [])
    if (not isinstance(identity, dict) or not identity
            or not isinstance(properties, list)
            or any(not isinstance(field, str) for field in properties)
            or not properties and 'image-attributes' not in recipe
            or len(properties) != len(set(properties))
            or not set(properties) <= {'og:image', 'og:video', 'og:audio'}):
        raise Invalid('网站资源缺少品牌身份或明确的资源属性')
    if (type(recipe.get('exclude-source-host', False)) is not bool
            or recipe.get('exclude-source-host') and 'image-attributes' not in recipe):
        raise Invalid('网站资源的原站主机划分需要明确的图片属性')
    if (type(recipe.get('respect-existing-owners', False)) is not bool
            or recipe.get('respect-existing-owners') and 'image-attributes' not in recipe):
        raise Invalid('网页图片的已有归属选择须为明确布尔值')
    if 'source' in identity and identity['source'] != recipe['source']:
        raise Invalid('网站资源不能改变身份来源')
    parse_site_identity({**identity, 'source': recipe['source']}, text)
    guide = PurposeFragments()
    guide.feed(text)
    result = set()
    for field in properties:
        if not guide.metadata.get(field):
            raise Invalid('网站缺少所选资源属性：' + field)
        for value in guide.metadata[field]:
            result.add('DOMAIN,' + https_product_host(value).split(',')[1])
    if 'image-attributes' in recipe:
        result.update(image_hosts(recipe['source'], text, recipe['image-attributes']))
    if recipe.get('exclude-source-host'):
        origin = urlsplit(recipe['source']).hostname
        result = {row for row in result if row.split(',')[1] != origin}
    if not result:
        raise Invalid('网站资源没有可核实的网络主机')
    return result


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
