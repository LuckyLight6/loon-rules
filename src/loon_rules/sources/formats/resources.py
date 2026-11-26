"""Read declared HTML image requests without executing page scripts."""
from html.parser import HTMLParser
import math
import re
from urllib.parse import urljoin

from loon_rules.rules import Invalid
from .common import public_domain_pattern
from .html import HIDDEN_HTML
from .structured import service_url_host


SPACE = ' \t\n\r\f'
IMAGE_ATTRIBUTES = {'src', 'srcset', 'data-src', 'data-srcset'}


def srcset_urls(value):
    urls = []
    position = 0
    while position < len(value):
        while position < len(value) and value[position] in SPACE + ',':
            position += 1
        start = position
        while position < len(value) and value[position] not in SPACE:
            position += 1
        url = value[start:position]
        if not url:
            continue
        if url.endswith(','):
            urls.append(url.rstrip(','))
            continue
        start = position
        while position < len(value) and value[position] != ',':
            position += 1
        descriptors = value[start:position].split()
        if len(descriptors) > 1:
            raise Invalid('响应式图片包含无法确认的多个描述符')
        if descriptors:
            descriptor = descriptors[0]
            width = re.fullmatch(r'[1-9][0-9]*w', descriptor)
            density = re.fullmatch(r'(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?x', descriptor)
            if not width and not density:
                raise Invalid('响应式图片的宽度或像素密度格式无效')
            if density:
                number = float(descriptor[:-1])
                if not math.isfinite(number) or number <= 0:
                    raise Invalid('响应式图片的像素密度必须是正有限数')
        urls.append(url)
    return urls


class ImageSources(HTMLParser):
    def __init__(self, attributes):
        super().__init__()
        self.attributes = set(attributes)
        self.hidden = 0
        self.urls = []
        self.bases = []
        self.pictures = 0

    def handle_starttag(self, tag, attrs):
        if tag in HIDDEN_HTML:
            self.hidden += 1
        if self.hidden:
            return
        if tag == 'base':
            bases = [value for name, value in attrs if name == 'href']
            if len(bases) > 1 or bases and (not isinstance(bases[0], str) or not bases[0].strip()):
                raise Invalid('网页图片的基准地址缺失或重复')
            self.bases.extend(bases)
        if tag == 'picture':
            self.pictures += 1
        if tag not in ('img', 'source') or tag == 'source' and not self.pictures:
            return
        selected = [(name, value) for name, value in attrs if name in self.attributes
                    and (tag == 'img' or name.endswith('srcset'))]
        if len({name for name, _ in selected}) != len(selected):
            raise Invalid('图片的网络来源属性重复')
        for name, value in selected:
            if not isinstance(value, str):
                raise Invalid('图片来源属性缺少地址')
            value = value.strip()
            if not value:
                continue
            self.urls.extend(srcset_urls(value) if name.endswith('srcset') else [value])

    def handle_endtag(self, tag):
        if tag in HIDDEN_HTML:
            self.hidden = max(0, self.hidden - 1)
            return
        if not self.hidden and tag == 'picture':
            self.pictures = max(0, self.pictures - 1)


def image_hosts(source, text, attributes):
    if (not isinstance(attributes, list) or not attributes
            or any(not isinstance(name, str) or name not in IMAGE_ATTRIBUTES for name in attributes)
            or len(attributes) != len(set(attributes))):
        raise Invalid('网页图片缺少明确且不重复的来源属性')
    parser = ImageSources(attributes)
    parser.feed(text)
    parser.close()
    if len(parser.bases) > 1:
        raise Invalid('网页图片存在多个基准地址，不能确认请求主机')
    base = urljoin(source, parser.bases[0]) if parser.bases else source
    service_url_host(base, allow_query=True)
    result = set()
    for value in parser.urls:
        if value.casefold().startswith(('data:', 'blob:')):
            continue
        host = service_url_host(urljoin(base, value), allow_query=True)
        if public_domain_pattern(host) is None:
            raise Invalid('网页图片包含未确认归属的共享主机')
        result.add('DOMAIN,' + host)
    return result
