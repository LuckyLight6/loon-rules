"""Resolve public AWS coding-service network context from purpose-specific documents."""
import hashlib
import re
import unicodedata

from markdown_it import MarkdownIt

from loon_rules import domains
from loon_rules.rules import Invalid, read_rules
from loon_rules.sources.formats.structured import json_object
from loon_rules.sources.transport import source_url


def region_name(value):
    return ' '.join(''.join(character for character in unicodedata.normalize('NFKD', value).casefold()
                            if not unicodedata.combining(character)).split())


def markdown_regions(text, heading):
    if not isinstance(text, str):
        raise Invalid('产品地区说明不是文本')
    tokens = MarkdownIt().parse(text)
    headings = [(index, int(token.tag[1:])) for index, token in enumerate(tokens)
                if token.type == 'heading_open' and tokens[index + 1].content == heading]
    if len(headings) != 1:
        raise Invalid('产品地区说明的用途章节缺失或重复：' + heading)
    start, level = headings[0]
    end = next((index for index in range(start + 3, len(tokens))
                if tokens[index].type == 'heading_open' and int(tokens[index].tag[1:]) <= level), len(tokens))
    section = tokens[start + 3:end]
    if any(token.type in ('heading_open', 'ordered_list_open') for token in section):
        raise Invalid('地区用途章节出现未确认的子章节或有序列表')
    if sum(token.type == 'bullet_list_open' for token in section) != 1:
        raise Invalid('地区用途章节须包含一份完整地区列表')
    for token in section:
        if token.type in ('fence', 'code_block'):
            raise Invalid('地区用途章节出现尚未处理的代码块')
        if token.type == 'html_block' and not re.fullmatch(r'<a (?:name|id)="[a-z0-9_-]+"></a>\s*', token.content):
            raise Invalid('地区用途章节出现尚未处理的HTML结构')
        if token.type == 'inline':
            children = token.children or []
            anchor = False
            for child in children:
                if child.type == 'html_inline':
                    if not anchor and re.fullmatch(r'<a (?:name|id)="[a-z0-9_-]+">', child.content):
                        anchor = True
                    elif anchor and child.content == '</a>':
                        anchor = False
                    else:
                        raise Invalid('地区用途章节含未确认的内联HTML')
                elif child.type in ('code_inline', 'image') or anchor and child.content.strip():
                    raise Invalid('地区用途章节含未处理的地区字段或非空结构锚点')
            if anchor:
                raise Invalid('地区用途章节的结构锚点未闭合')
    names = []
    for index, token in enumerate(section):
        if token.type != 'list_item_open':
            continue
        closing = next((position for position in range(index + 1, len(section))
                        if section[position].type == 'list_item_close'), None)
        fields = [item for item in section[index + 1:closing] if item.type == 'inline']
        if closing is None or len(fields) != 1 or not fields[0].children:
            raise Invalid('地区条目不是单个完整名称')
        children = fields[0].children
        if any(child.type not in ('text', 'em_open', 'em_close', 'strong_open', 'strong_close') for child in children):
            raise Invalid('地区名称包含尚未确认的链接、代码或隐藏字段')
        name = ''.join(child.content for child in children if child.type == 'text').strip()
        if not name or any(ord(character) < 32 for character in name):
            raise Invalid('地区条目缺少规范名称')
        names.append(region_name(name))
    if not names or len(names) != len(set(names)):
        raise Invalid('产品地区列表为空或包含重复名称')
    return names


def region_bindings(spec, documents):
    sources = ('profile-source', 'sso-source', 'sdk-source')
    fields = {*sources, 'profile-heading', 'sso-heading', 'partition', 'dns-suffix'}
    if (not isinstance(spec, dict) or set(spec) != fields
            or any(not isinstance(spec[field], str) or not spec[field]
                   or spec[field] != spec[field].strip() for field in fields)):
        raise Invalid('AWS编程服务地区声明缺少用途、来源或分区')
    for field in sources:
        source_url(spec[field])
        if spec[field] not in documents:
            raise Invalid('AWS编程服务地区说明尚未完整读取：' + field)
    if (not re.fullmatch(r'[a-z][a-z0-9-]+', spec['partition'])
            or domains.public_host(spec['dns-suffix']) != spec['dns-suffix']):
        raise Invalid('AWS编程服务分区或DNS后缀无效')
    metadata = json_object(documents[spec['sdk-source']])
    if (set(metadata) != {'version', 'partitions'} or type(metadata['version']) is not int
            or metadata['version'] != 3 or not isinstance(metadata['partitions'], list)
            or not metadata['partitions']):
        raise Invalid('AWS SDK地区元数据的版本或完整结构变化')
    partitions = {}
    for record in metadata['partitions']:
        if (not isinstance(record, dict) or not isinstance(record.get('partition'), str)
                or not record['partition'] or record['partition'] in partitions):
            raise Invalid('AWS SDK分区缺失或重复')
        partitions[record['partition']] = record
    selected = partitions.get(spec['partition'])
    if (selected is None or selected.get('dnsSuffix') != spec['dns-suffix']
            or not isinstance(selected.get('regions'), dict) or not selected['regions']):
        raise Invalid('AWS SDK缺少指定分区、DNS后缀或完整地区元数据')
    regions = {}
    for code, record in selected['regions'].items():
        if (not re.fullmatch(r'[a-z]{2,5}(?:-[a-z]+)+-\d{1,2}', code)
                or not isinstance(record, dict) or set(record) != {'description'}
                or not isinstance(record['description'], str) or not record['description'].strip()
                or record['description'] != record['description'].strip()
                or any(ord(character) < 32 for character in record['description'])):
            raise Invalid('AWS SDK地区标识、名称或元数据字段变化')
        name = region_name(record['description'])
        if name in regions:
            raise Invalid('AWS SDK地区名称不唯一，不能猜测产品地区代码')
        regions[name] = code
    result = {'dns-suffix': spec['dns-suffix'], 'sdk-partition': spec['partition'],
              'sdk-regions': sorted(selected['regions'])}
    for kind in ('profile', 'sso'):
        names = markdown_regions(documents[spec[kind + '-source']], spec[kind + '-heading'])
        if any(name not in regions for name in names):
            raise Invalid('产品地区名称未在官方SDK的指定分区中对应：' + kind)
        result[kind + '-regions'] = sorted(regions[name] for name in names)
    return result


GENERAL_PURPOSES = {
    'Authentication': 'authentication',
    'Amazon Q Developer features': 'features',
    'Amazon Q Developer in the IDE, configuration': 'ide-configuration',
    'Amazon Q Developer in the IDE, endpoints': 'ide-endpoints',
    'Amazon Q Developer in the IDE, language processing': 'language-processing',
    'Amazon Q Developer in the IDE, telemetry': 'telemetry',
}
NETWORK_VARIABLES = {'idc-directory-id-or-alias', 'sso-region', 'profile-region'}


def network_table(text, heading, headers):
    """Keep code fields and reject extra Markdown cells before rendering can lose them."""
    if not isinstance(text, str):
        raise Invalid('AWS网络说明不是文本')
    tokens = MarkdownIt().enable('table').parse(text)
    headings = [(index, int(token.tag[1:])) for index, token in enumerate(tokens)
                if token.type == 'heading_open' and tokens[index + 1].content == heading]
    if len(headings) != 1:
        raise Invalid('AWS网络用途章节缺失或重复：' + heading)
    start, level = headings[0]
    end = next((index for index in range(start + 3, len(tokens))
                if tokens[index].type == 'heading_open' and int(tokens[index].tag[1:]) <= level), len(tokens))
    lines = text.splitlines()
    first_line = tokens[start].map[1]
    last_line = tokens[end].map[0] if end < len(tokens) else len(lines)
    raw_scope = '\n'.join(lines[first_line:last_line])
    section = tokens[start + 3:end]
    for token in section:
        if token.type != 'table_open':
            continue
        for line in lines[token.map[0]:token.map[1]]:
            value = line.strip()
            separators = []
            for position, character in enumerate(value):
                if character != '|':
                    continue
                before = position - 1
                while before >= 0 and value[before] == '\\':
                    before -= 1
                if (position - before - 1) % 2 == 0:
                    separators.append(position)
            columns = len(separators) + 1
            if separators and separators[0] == 0:
                columns -= 1
            if separators and separators[-1] == len(value) - 1:
                columns -= 1
            if columns != len(headers):
                raise Invalid('AWS网络表原始Markdown含有缺列或多余列')
    if (sum(token.type == 'table_open' for token in section) != 1
            or any(token.type in ('heading_open', 'fence', 'code_block') for token in section)):
        raise Invalid('AWS网络章节须有一份完整用途表，不能含未知子章节或代码块')
    rows = []
    current_row = None
    cell = None
    inside = False
    network_text = re.compile(r'https?://|(?:[a-z0-9-]+\.)+[a-z]{2,63}\b|(?:\d{1,3}\.){3}\d{1,3}', re.I)
    for token in section:
        if token.type == 'html_block':
            if not re.fullmatch(r'<a (?:name|id)="[a-z0-9_-]+"></a>\s*', token.content):
                raise Invalid('AWS网络章节出现尚未处理的HTML块')
        elif token.type == 'table_open':
            inside = True
        elif token.type == 'table_close':
            inside = False
        elif token.type == 'tr_open':
            current_row = []
        elif token.type == 'tr_close':
            if current_row is None or len(current_row) != len(headers):
                raise Invalid('AWS网络用途表的列数变化')
            rows.append(current_row)
            current_row = None
        elif token.type in ('td_open', 'th_open'):
            cell = {'text': '', 'codes': [], 'plain': ''}
        elif token.type in ('td_close', 'th_close'):
            if cell is None or current_row is None:
                raise Invalid('AWS网络用途表结构不完整')
            current_row.append(cell)
            cell = None
        elif token.type == 'inline':
            children = token.children or []
            visible = ''
            codes = []
            plain = ''
            metadata_anchor = False
            for child in children:
                if child.type in ('text', 'code_inline'):
                    if metadata_anchor and child.content.strip():
                        raise Invalid('AWS网络章节的结构锚点含有未处理正文')
                    visible += child.content
                    if child.type == 'code_inline':
                        codes.append(child.content.strip())
                    else:
                        plain += child.content
                elif child.type in ('softbreak', 'hardbreak'):
                    visible += ' '
                    plain += ' '
                elif child.type == 'html_inline':
                    if not inside and re.fullmatch(r'<a (?:name|id)="[a-z0-9_-]+">', child.content):
                        if metadata_anchor:
                            raise Invalid('AWS网络章节含嵌套结构锚点')
                        metadata_anchor = True
                    elif not inside and child.content == '</a>' and metadata_anchor:
                        metadata_anchor = False
                    elif child.content.lower() in ('<br>', '<br/>', '<br />'):
                        visible += ' '
                        plain += ' '
                    else:
                        raise Invalid('AWS网络字段含有尚未处理的HTML')
                elif child.type not in ('link_open', 'link_close', 'em_open', 'em_close', 'strong_open', 'strong_close'):
                    raise Invalid('AWS网络字段含有尚未处理的内联结构')
            if metadata_anchor:
                raise Invalid('AWS网络章节的结构锚点未闭合')
            if inside:
                if cell is None:
                    raise Invalid('AWS网络表字段不在单元格中')
                cell.update(text=' '.join(visible.split()), codes=codes, plain=plain.strip())
            elif (network_text.search(visible)
                  or any(value not in {'{{' + name + '}}' for name in NETWORK_VARIABLES} for value in codes)):
                raise Invalid('AWS网络章节出现未归入用途表的网络字段')
    if (inside or current_row is not None or cell is not None or len(rows) < 2
            or [item['text'] for item in rows[0]] != headers):
        raise Invalid('AWS网络用途表缺少完整标题或正文')
    return rows[1:], raw_scope


def network_endpoint(value, purpose, context):
    from urllib.parse import urlsplit
    from loon_rules.sources.formats.common import public_domain_pattern

    variables = set(re.findall(r'\{\{([^{}]+)\}\}', value))
    if variables - NETWORK_VARIABLES or len(variables) > 1:
        raise Invalid('AWS端点含有尚未确认的模板变量')
    for variable in NETWORK_VARIABLES:
        if variable in value and '{{' + variable + '}}' not in value:
            raise Invalid('AWS端点模板失去明确的占位标记')
    if 'profile-region' in variables and purpose != 'features':
        raise Invalid('模型配置地区模板出现在其他用途')
    if variables & {'sso-region', 'idc-directory-id-or-alias'} and purpose != 'authentication':
        raise Invalid('身份地区或目录模板出现在其他用途')
    if 'idc-directory-id-or-alias' in variables and value != '{{idc-directory-id-or-alias}}.awsapps.com':
        raise Invalid('目录ID模板越出已确认的AWS身份命名空间')
    if variables and not value.removeprefix('https://').removeprefix('wss://').split('/')[0].endswith(
            ('.' + context['dns-suffix'], '.api.aws', '.awsapps.com')):
        raise Invalid('AWS地区模板越出已确认的服务命名空间')
    values = [value]
    for variable in variables:
        choices = ['*'] if variable == 'idc-directory-id-or-alias' else context[variable.replace('-region', '-regions')]
        marker = '{{' + variable + '}}'
        if value.count(marker) != 1:
            raise Invalid('AWS端点包含重复的模板占位字段')
        values = [value.replace(marker, choice) for choice in choices]
    result = set()
    for candidate in values:
        if '://' in candidate:
            try:
                address = urlsplit(candidate)
                port = address.port
            except ValueError as error:
                raise Invalid('AWS网络URL结构或端口变化') from error
            if (address.scheme not in ('https', 'wss') or not address.hostname or address.username is not None
                    or address.query or address.fragment or port not in (None, 443)):
                raise Invalid('AWS网络字段不是无凭据的公开HTTPS/WSS地址')
            candidate = address.hostname
        candidate = candidate.strip()
        tail = domains.fixed_tail(candidate)
        if ((purpose == 'features' or purpose == 'ide-endpoints'
             and candidate.split('.')[0].startswith('q-developer-'))
                and not tail.endswith(('.' + context['dns-suffix'], '.api.aws'))):
            raise Invalid('AWS业务API用途越出已确认的服务命名空间')
        if candidate.startswith('*.') and tail in (context['dns-suffix'], 'api.aws'):
            raise Invalid('AWS网络字段扩大成整个共享云平台')
        platforms = ()
        if purpose == 'authentication' and candidate.startswith('*.'):
            identity_namespaces = {'awsapps.com'} | {
                service + '.' + region + '.' + context['dns-suffix']
                for service in ('sso', 'sso-portal') for region in context['sso-regions']}
            if tail in identity_namespaces:
                platforms = (tail,)
        row = public_domain_pattern(candidate, platforms=platforms)
        if row is None:
            raise Invalid('AWS网络字段是尚未确认的共享托管范围')
        result.add(row)
    return result, variables


def network_records(spec, documents):
    from urllib.parse import urlsplit

    if (not isinstance(spec, dict) or set(spec) != {'source', 'kiro-source', 'region-context'}
            or not isinstance(spec['region-context'], dict)):
        raise Invalid('AWS编程网络缺少完整来源和地区上下文')
    for field, host, prefix in (('source', 'docs.aws.amazon.com', '/amazonq/'),
                                ('kiro-source', 'kiro.dev', '/docs/')):
        source_url(spec[field])
        address = urlsplit(spec[field])
        if address.hostname != host or not address.path.startswith(prefix) or spec[field] not in documents:
            raise Invalid('AWS编程网络资料的发布者或用途路径不符')
    context_spec = spec['region-context']
    for field in ('profile-source', 'sso-source'):
        address = urlsplit(context_spec.get(field, ''))
        if address.hostname != 'docs.aws.amazon.com' or not address.path.startswith('/amazonq/'):
            raise Invalid('产品地区说明的发布者或路径不符')
    sdk = urlsplit(context_spec.get('sdk-source', ''))
    if (sdk.hostname != 'raw.githubusercontent.com' or not sdk.path.startswith('/boto/botocore/')
            or not sdk.path.endswith('/botocore/data/endpoints.json')
            or context_spec.get('partition') != 'aws' or context_spec.get('dns-suffix') != 'amazonaws.com'):
        raise Invalid('AWS SDK来源或标准分区身份不符')
    if (context_spec.get('profile-heading') != 'Supported Regions for the Q Developer console and Q Developer profile'
            or context_spec.get('sso-heading') != 'Supported Regions (enabled by default)'
            or not urlsplit(context_spec['profile-source']).path.endswith('/q-admin-setup-subscribe-regions.md')
            or not urlsplit(context_spec['sso-source']).path.endswith('/regions.md')):
        raise Invalid('AWS网络变量未绑定对应的profile与默认SSO用途说明')
    context = region_bindings(context_spec, documents)
    text = documents[spec['source']]
    tokens = MarkdownIt().parse(text)
    titles = [tokens[index + 1].content for index, token in enumerate(tokens)
              if token.type == 'heading_open' and token.tag == 'h1']
    if len(titles) != 1 or 'Amazon Q Developer' not in titles[0]:
        raise Invalid('AWS网络说明的产品身份不符')
    general_rows, raw_scope = network_table(text, 'General URLs to allowlist', ['URL', 'Purpose'])
    declared = set(re.findall(r'\{\{([^{}]+)\}\}', raw_scope))
    if declared != NETWORK_VARIABLES:
        raise Invalid('AWS网络说明的完整模板变量发生变化')
    general = {kind: set() for kind in GENERAL_PURPOSES.values()}
    seen = set()
    used_variables = set()
    for endpoint, label in general_rows:
        purpose = GENERAL_PURPOSES.get(label['text'])
        if purpose is None or label['codes'] or len(endpoint['codes']) != 1 or endpoint['plain']:
            raise Invalid('AWS网络表出现未知用途或尚未处理的端点字段')
        value = endpoint['codes'][0]
        identity = (value, purpose)
        if identity in seen:
            raise Invalid('AWS网络表含有重复的用途端点记录')
        seen.add(identity)
        rows, variables = network_endpoint(value, purpose, context)
        general[purpose].update(rows)
        used_variables.update(variables)
    if used_variables != NETWORK_VARIABLES or any(not rows for rows in general.values()):
        raise Invalid('AWS完整网络表缺少已声明的用途或模板')
    storage_rows, _ = network_table(text, 'Amazon S3 bucket URLs and ARNs to allowlist',
                                    ['Amazon S3 bucket URL and ARN', 'Purpose'])
    storage = {'code-reviews': set(), 'code-transformations': set()}
    for addresses, label in storage_rows:
        purpose = {
            'An Amazon S3 bucket used to upload artifacts for Amazon Q code reviews': 'code-reviews',
            'An Amazon S3 bucket used to upload artifacts for Amazon Q code transformations': 'code-transformations',
        }.get(label['text'])
        if purpose is None or label['codes']:
            raise Invalid('AWS业务桶表出现未知用途')
        if re.search(r'https?://|(?:[a-z0-9-]+\.)+[a-z]{2,63}\b|arn:', addresses['plain'], re.I):
            raise Invalid('AWS业务桶地址出现在未处理的表格字段中')
        urls = {}
        arns = set()
        for value in addresses['codes']:
            if value.startswith('https://'):
                address = urlsplit(value)
                match = re.fullmatch(r'([a-z0-9][a-z0-9.-]+)\.s3(?:\.([a-z0-9-]+))?\.amazonaws\.com', address.hostname or '')
                if (match is None or address.username is not None or address.port not in (None, 443)
                        or address.query or address.fragment or address.path not in ('', '/')
                        or match[2] and match[2] not in context['sdk-regions']):
                    raise Invalid('AWS业务桶URL不是指定分区的完整虚拟主机地址')
                row = 'DOMAIN,' + domains.public_host(address.hostname)
                if match[1] in urls:
                    raise Invalid('AWS业务桶表含重复URL')
                urls[match[1]] = row
            else:
                match = re.fullmatch(r'arn:aws:s3:::([a-z0-9][a-z0-9.-]+)', value)
                if match is None or match[1] in arns:
                    raise Invalid('AWS业务桶ARN结构、分区或唯一性变化')
                arns.add(match[1])
        if not urls or set(urls) != arns:
            raise Invalid('AWS业务桶URL与ARN没有完整对应')
        storage[purpose].update(urls.values())
    if any(not rows for rows in storage.values()):
        raise Invalid('AWS业务桶表缺少已声明的用途')
    from loon_rules.sources.formats.html import HostTables
    from loon_rules.sources.formats.common import public_domain_pattern

    table = HostTables()
    table.feed(documents[spec['kiro-source']])
    if table._table_stack or table.row is not None or table.cell is not None or table.hidden:
        raise Invalid('Kiro完整网络用途表的HTML结构未闭合')
    core_tables = table.tables.get('core-urls', [])
    if not core_tables:
        raise Invalid('Kiro完整网络说明缺少Core用途表')
    kiro = set()
    for current in core_tables:
        values = current['rows']
        if current['nested'] or len(values) < 2 or values[0] != ['URL', 'Purpose']:
            raise Invalid('Kiro完整Core章节出现未知或不完整用途表')
        for cells in values[1:]:
            if len(cells) != 2 or not cells[1].strip() or cells == values[0]:
                raise Invalid('Kiro完整Core用途表的列数或用途变化')
            row = public_domain_pattern(cells[0])
            if row is None or not row.startswith('DOMAIN,') or row in kiro:
                raise Invalid('Kiro完整Core用途表的主机无效或重复')
            kiro.add(row)
    return {'regions': context, 'general-records': len(general_rows), 'storage-records': len(storage_rows),
            'general-purposes': {kind: sorted(rows) for kind, rows in general.items()},
            'storage-purposes': {kind: sorted(rows) for kind, rows in storage.items()},
            'kiro-core-services': sorted(kiro), 'shared-services': sorted(business_apis(general) & kiro)}


METHOD = 'aws-coding-network'
DEPENDENCY_FORMAT = 'aws-coding-dependencies'
NETWORK_FIELDS = {'source', 'kiro-source', 'region-context'}
SCOPES = {'api', 'shared', 'reviews', 'transformations', 'kiro'}


def network_spec(spec):
    return {key: spec[key] for key in NETWORK_FIELDS}


def source_urls(spec):
    context = spec['region-context']
    return list(dict.fromkeys([spec['source'], spec['kiro-source'],
                              *(context[field] for field in ('profile-source', 'sso-source', 'sdk-source'))]))


def validate(spec, *, dependency=False):
    fields = NETWORK_FIELDS | ({'format', 'service', 'protect-from-reject', 'require-complete'}
                              if dependency else {'method', 'scope'})
    if (not isinstance(spec, dict) or set(spec) - fields or not NETWORK_FIELDS <= set(spec)
            or not isinstance(spec['region-context'], dict)
            or set(spec['region-context']) != {'profile-source', 'profile-heading', 'sso-source',
                'sso-heading', 'sdk-source', 'partition', 'dns-suffix'}):
        raise Invalid('AWS编程服务声明缺少完整来源用途或出现未知选项')
    if dependency:
        if spec.get('format') != DEPENDENCY_FORMAT or spec.get('service', 'q') not in ('q', 'kiro-core'):
            raise Invalid('AWS服务依赖没有明确的产品用途')
    elif spec.get('method') != METHOD or spec.get('scope') not in SCOPES:
        raise Invalid('AWS网络展开仅支持已确认的业务细分')
    for url in source_urls(spec):
        source_url(url)


def business_apis(general):
    return set(general['features']) | {row for row in general['ide-endpoints']
        if row.split(',')[1].split('.')[0].startswith('q-developer-')}


def scoped_rows(spec, facts):
    general = {kind: set(rows) for kind, rows in facts['general-purposes'].items()}
    shared = set(facts['shared-services'])
    api = business_apis(general) - shared
    from urllib.parse import urlsplit

    root = domains.current().registrable(urlsplit(spec['kiro-source']).hostname)
    own = {row for row in facts['kiro-core-services']
           if domains.current().registrable(row.split(',')[1]) == root}
    return {'api': api, 'shared': shared, 'kiro': own,
            'reviews': set(facts['storage-purposes']['code-reviews']),
            'transformations': set(facts['storage-purposes']['code-transformations'])}


def plan(spec):
    validate(spec)
    return {'method': METHOD, 'documents': [{'source': url, 'kind': METHOD} for url in source_urls(spec)]}


def read(spec, record, inputs):
    validate(spec)
    facts = network_records(network_spec(spec), inputs)
    rows = scoped_rows(spec, facts)[spec['scope']]
    if not rows:
        raise Invalid('AWS业务细分没有完整对应的端点，不能发布空结果')
    documents = []
    for doc in record['documents']:
        source_rows = set(facts['kiro-core-services']) if doc['source'] == spec['kiro-source'] else set()
        if doc['source'] == spec['source']:
            source_rows = {row for values in [*facts['general-purposes'].values(),
                           *facts['storage-purposes'].values()] for row in values}
        documents.append({**doc, 'sha256': hashlib.sha256(inputs[doc['source']].encode()).hexdigest(),
                          'rows': sorted(rows & source_rows), 'shared-rows': []})
    return sorted(rows), {'method': METHOD, 'directory': spec['source'], 'scope': spec['scope'],
                          'network-facts': facts, 'documents': documents}


def verify_network_facts(spec, facts):
    if (not isinstance(facts, dict) or set(facts) != {'regions', 'general-records', 'storage-records', 'general-purposes',
                       'storage-purposes', 'kiro-core-services', 'shared-services'}
            or not isinstance(facts.get('general-purposes'), dict)
            or not isinstance(facts.get('storage-purposes'), dict)
            or set(facts.get('general-purposes', {})) != set(GENERAL_PURPOSES.values())
            or set(facts.get('storage-purposes', {})) != {'code-reviews', 'code-transformations'}
            or any(type(facts.get(field)) is not int or facts[field] < 1
                   for field in ('general-records', 'storage-records'))):
        raise Invalid('AWS报告缺少完整的网络用途事实')
    for rows in [*facts['general-purposes'].values(), *facts['storage-purposes'].values(),
                 facts['kiro-core-services'], facts['shared-services']]:
        if (not isinstance(rows, list) or not rows or any(not isinstance(row, str) for row in rows)
                or rows != sorted(set(rows))
                or read_rules('\n'.join(rows)) != rows
                or any(row.count(',') != 1 or not row.startswith(('DOMAIN,', 'DOMAIN-WILDCARD,')) for row in rows)):
            raise Invalid('AWS报告中的完整用途范围无效')
    if set(facts['shared-services']) != business_apis(facts['general-purposes']) & set(facts['kiro-core-services']):
        raise Invalid('AWS共用服务没有同时出现在两份官方资料中')
    regions = facts['regions']
    context = spec['region-context']
    fields = {'dns-suffix', 'sdk-partition', 'sdk-regions', 'profile-regions', 'sso-regions'}
    if (not isinstance(regions, dict) or set(regions) != fields
            or regions['dns-suffix'] != context['dns-suffix']
            or regions['sdk-partition'] != context['partition']
            or regions['dns-suffix'] != 'amazonaws.com' or regions['sdk-partition'] != 'aws'):
        raise Invalid('AWS网络事实缺少对应的完整地区、分区或DNS依据')
    for field in ('sdk-regions', 'profile-regions', 'sso-regions'):
        values = regions[field]
        if (not isinstance(values, list) or not values
                or any(not isinstance(value, str) or not re.fullmatch(r'[a-z]{2,5}(?:-[a-z]+)+-\d{1,2}', value)
                       for value in values) or values != sorted(set(values))):
            raise Invalid('AWS网络事实中的地区用途清单不完整')
    if (not set(regions['profile-regions']) <= set(regions['sdk-regions'])
            or not set(regions['sso-regions']) <= set(regions['sdk-regions'])):
        raise Invalid('AWS产品地区事实没有在同一标准分区中对应')


def verify(spec, record):
    validate(spec)
    docs = record.get('documents', [])
    if (record.get('method') != METHOD or record.get('directory') != spec['source']
            or record.get('scope') != spec['scope']
            or [doc.get('source') for doc in docs] != source_urls(spec)
            or any(doc.get('kind') != METHOD or not re.fullmatch('[0-9a-f]{64}', doc.get('sha256', ''))
                   or doc.get('shared-rows') != [] for doc in docs)):
        raise Invalid('AWS编程服务报告与完整来源或业务用途不符')
    facts = record.get('network-facts', {})
    verify_network_facts(spec, facts)
    expected = scoped_rows(spec, facts)[spec['scope']]
    actual = {row for doc in docs for row in doc['rows']}
    if actual != expected:
        raise Invalid('AWS报告正文与已确认的业务范围不符')


def dependency_rows(recipe, documents):
    validate(recipe, dependency=True)
    facts = network_records(network_spec(recipe), documents)
    return dependency_scopes(recipe, facts)


def dependency_scopes(recipe, facts):
    groups = scoped_rows(recipe, facts)
    if recipe.get('service', 'q') == 'kiro-core':
        return set(facts['kiro-core-services']) - groups['kiro']
    return {row for rows in facts['general-purposes'].values() for row in rows} - groups['api'] - groups['shared']



def verify_dependency(recipe, record):
    validate(recipe, dependency=True)
    context = record.get('context-sha256', {})
    if (not isinstance(context, dict) or set(context) != set(source_urls(recipe))
            or any(not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value)
                   for value in context.values())
            or context.get(recipe['source']) != record.get('sha256')):
        raise Invalid('AWS服务依赖报告缺少完整来源上下文指纹')
    facts = record.get('network-facts', {})
    verify_network_facts(recipe, facts)
    if record.get('rules') != sorted(dependency_scopes(recipe, facts)):
        raise Invalid('AWS依赖正文没有完整对应同一份用途事实')


def verify_contexts(entries, expanded, dependent):
    fingerprints = {}
    contexts = {}

    def observe(spec, facts, hashes):
        for url, value in hashes.items():
            if url in fingerprints and fingerprints[url] != value:
                raise Invalid('AWS同一来源在本批展开与依赖中的指纹不一致：' + url)
            fingerprints[url] = value
        identity = tuple(source_urls(spec))
        if identity in contexts and contexts[identity] != facts:
            raise Invalid('AWS同批完整上下文的用途或地区事实不一致')
        contexts[identity] = facts

    for key, entry in entries.items():
        spec = entry.get('expand', {})
        if spec.get('method') == METHOD:
            record = expanded.get(key, {})
            verify(spec, record)
            observe(spec, record['network-facts'], {doc['source']: doc['sha256'] for doc in record['documents']})
        recipes = entry.get('dependency-inputs', [])
        if not any(recipe.get('format') == DEPENDENCY_FORMAT for recipe in recipes):
            continue
        inputs = dependent.get(key, {}).get('inputs', [])
        if len(inputs) != len(recipes):
            raise Invalid('AWS依赖报告没有对应完整声明')
        for recipe, record in zip(recipes, inputs):
            if recipe.get('format') != DEPENDENCY_FORMAT:
                continue
            if record.get('recipe') != recipe:
                raise Invalid('AWS依赖报告与产品用途声明不一致')
            verify_dependency(recipe, record)
            observe(recipe, record['network-facts'], record['context-sha256'])
