"""Try declared public mirrors without changing a source's evidence identity."""
from datetime import datetime, timezone
import re,subprocess
from urllib.parse import parse_qsl,urlsplit

from loon_rules.rules import Invalid


def validate(config):
    for primary, spec in config.get('source-mirrors', {}).items():
        urls = [primary, *spec.get('urls', ())]
        if len(urls) < 2 or len(set(urls)) != len(urls):
            raise Invalid('备用来源缺少地址或与主来源重复')
        for url in urls:
            parts = urlsplit(url)
            if (parts.scheme != 'https' or not parts.hostname or parts.username
                    or parts.query or parts.fragment):
                raise Invalid('备用来源只能使用无凭据的公开 HTTPS 地址')
        if spec.get('format') != 'rir-delegated' or not spec.get('registry'):
            raise Invalid('备用来源需要明确的资料格式与发布机构')


def delegated(text, spec):
    lines = [line.split('|') for line in text.splitlines() if line and not line.startswith('#')]
    if not lines or len(lines[0]) != 7 or lines[0][:2] != ['2', spec['registry']]:
        raise Invalid('备用分配资料缺少发布机构和版本头')
    header = lines[0]
    try:
        end = datetime.strptime(header[5], '%Y%m%d').date()
        age = (datetime.now(timezone.utc).date() - end).days
        count = int(header[3])
    except ValueError as exc:
        raise Invalid('分配资料日期或记录数格式变化') from exc
    rows = [row for row in lines[1:] if row[-1] != 'summary']
    if (age < -1 or age > spec.get('max-age-days', 7) or count != len(rows)
            or any(len(row) < 7 or row[0] != spec['registry'] for row in rows)
            or {row[2] for row in rows} != {'asn', 'ipv4', 'ipv6'}):
        raise Invalid('分配资料过期、记录不完整或缺少资源类别')


def fetch(primary, mirrors, download, *, public_bag=False):
    spec = mirrors.get(primary, {})
    for url in [primary, *spec.get('urls', ())]:
        try:
            text = download(url,public_bag=True) if public_bag else download(url)
            if spec:
                delegated(text, spec)
            return text, url
        except (Invalid, OSError):
            continue
    raise Invalid('公开来源及已声明备用地址均未读到有效资料：' + primary)


def source_url(url,*,public_profile=False,public_bag=False):
    parts=urlsplit(url)
    if (type(public_profile) is not bool or type(public_bag) is not bool or public_profile and public_bag
            or parts.scheme!='https' or not parts.hostname or parts.username is not None or parts.fragment
            or parts.query and not (public_profile or public_bag)):
        raise Invalid('只读取公开 HTTPS 源')
    if public_profile:
        try:parameters=parse_qsl(parts.query,keep_blank_values=True,strict_parsing=True,max_num_fields=3)
        except ValueError as exc:raise Invalid('公开客户端配置的请求参数无效') from exc
        values=dict(parameters)
        if (len(parameters)!=3 or set(values)!={'os','os_version','hardware'} or values['os']!='ios'
                or not re.fullmatch(r'\d{1,3}(?:\.\d{1,3}){0,3}',values['os_version'])
                or not re.fullmatch(r'(?:iPhone|iPad|iPod)\d{1,3},\d{1,3}',values['hardware'])):
            raise Invalid('客户端配置只允许公开的 iOS 版本与机型参数')
    if public_bag:
        try:parameters=parse_qsl(parts.query,keep_blank_values=True,strict_parsing=True,max_num_fields=1)
        except ValueError as exc:raise Invalid('公开服务配置的索引参数无效') from exc
        if len(parameters)!=1 or parameters[0][0]!='ix' or not re.fullmatch(r'[1-9]\d{0,2}',parameters[0][1]):
            raise Invalid('公开服务配置只允许数字索引参数')
    return url


def download(url,*,public_profile=False,public_bag=False):
    url=source_url(url,public_profile=public_profile,public_bag=public_bag)
    result=subprocess.run(
        ('curl','-q','-fsSL','--compressed','--proto','=https','--proto-redir','=https','--max-redirs','3',
         '--connect-timeout','8','--max-time','25','--retry','2','--retry-all-errors',
         '--retry-max-time','40','--max-filesize','18000000',
         '-A','Loon/991 CFNetwork/3896.100.1.1.1 Darwin/27.0.0',url),
        capture_output=True,
    )
    if result.returncode:
        raise Invalid(f'上游下载失败（curl {result.returncode}）')
    try:
        return result.stdout.decode('utf-8-sig')
    except UnicodeError as exc:
        raise Invalid('上游正文不是 UTF-8 文本') from exc
