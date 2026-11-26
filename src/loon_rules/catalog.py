"""从产品声明生成兼容清单；旧格式的独立调用仍按原约定读取。"""
from copy import deepcopy
import re

from loon_rules.rules import Invalid


SELECTIONS={'general':'general','detailed':'detailed','optional':'optional','alternative':'alternatives'}
GENERATED=(*SELECTIONS.values(),'views')


def priority_width(config):
    width=config.get('priority-width',3)
    if type(width) is not int or width not in (3,4):
        raise Invalid('编号位数须为 3 或 4')
    return width


def materialize(config):
    width=priority_width(config)
    version=config.get('schema-version',1)
    if version==1:return
    if version!=2:raise Invalid('不支持的规则清单格式版本')
    sections={s['id']:s for s in config['sections']}
    if len(sections)!=len(config['sections']):raise Invalid('业务分区名称重复')
    selected={field:[] for field in GENERATED}
    numbers={key:[] for key in sections}
    ordered=sorted(config['entries'],key=lambda e:e['priority'])
    for entry in ordered:
        key=entry['id'];section=entry['section']
        if section not in sections:raise Invalid('未知业务分区：'+key)
        if entry['mode']=='view':
            if 'selection' in entry:raise Invalid('合集不能重复声明订阅类型：'+key)
            field='views'
        else:
            selection=entry.get('selection','general')
            if selection not in SELECTIONS:raise Invalid('未知订阅类型：'+key)
            field=SELECTIONS[selection]
        selected[field].append(key)
        numbers[section].append(entry['priority'])
    config.update(selected)
    for key,section in sections.items():
        section.pop('from',None);section.pop('through',None)
        section['numbers']=numbers[key]
    bands=config.get('routing-bands',())
    if any('start' in band for band in bands):
        starts=[band.get('start') for band in bands]
        if (any(type(start) is not int or not 1<=start<10**width for start in starts)
                or starts!=sorted(set(starts))):
            raise Invalid('执行分区须按唯一递增的起始编号声明')
        if ordered and ordered[0]['priority']<starts[0]:
            raise Invalid('产品编号在所有执行分区之前')
        for i,band in enumerate(bands):
            end=starts[i+1] if i+1<len(starts) else 10**width
            band['ids']=[e['id'] for e in ordered if starts[i]<=e['priority']<end]
    by_id={entry['id']:entry for entry in ordered}
    seen_groups=set()
    for i,band in enumerate(bands):
        if not (groups:=band.get('groups')):continue
        starts=[group.get('start') for group in groups]
        end=bands[i+1]['start'] if i+1<len(bands) else 10**width
        if (any(type(start) is not int for start in starts) or starts!=sorted(set(starts))
                or starts[0]!=band['start'] or starts[-1]>=end):
            raise Invalid('业务子类须按实际执行编号连续划分')
        subtitles={}
        for position,group in enumerate(groups):
            key=group.get('id')
            if not key or key in seen_groups or not group.get('title') or group.get('section') not in sections:
                raise Invalid('业务子类缺少唯一标识、标题或分区')
            seen_groups.add(key)
            stop=starts[position+1] if position+1<len(starts) else end
            members=[by_id[key] for key in band['ids'] if group['start']<=by_id[key]['priority']<stop]
            if not members:raise Invalid('业务子类没有实际规则：'+key)
            for entry in members:
                if (entry.get('routing-group')!=key or entry['section']!=group['section']
                        or group.get('policies') and entry.get('policy-hint') not in group['policies']):
                    raise Invalid('规则的分类与优先级位置不一致：'+entry['id'])
            products=[entry for entry in members if entry['mode']!='view']
            combined=any(entry['mode']=='view' for entry in members)
            if products and (combined or len(groups)>1):
                subtitles[products[0]['id']]=group.get('detail-title',group['title']+(' · 产品细分' if combined else ''))
        band['subheadings']=subtitles


def verify(config):
    if config.get('schema-version',1)==1:return
    expected=deepcopy(config)
    materialize(expected)
    if (any(config.get(field)!=expected[field] for field in GENERATED)
            or config['sections']!=expected['sections']
            or config.get('routing-bands')!=expected.get('routing-bands')):
        raise Invalid('清单的生成字段未同步（maintain.py --render-index）')


def priority_label(entry, *, width=None):
    width=priority_width(entry) if width is None else width
    return f'{entry["priority"]:0{width}d}'


def rule_filename(entry, *, width=None):
    return f'{priority_label(entry,width=width)}-{entry["id"]}.lsr'


def subscription_aliases(config):
    aliases = config.get('subscription-aliases', {})
    if not isinstance(aliases, dict):
        raise Invalid('兼容下载地址必须按名称声明')
    if not aliases:
        return {}
    entries = {entry['id']: entry for entry in config['entries']}
    width = priority_width(config)
    canonical = {rule_filename(entry, width=width).removesuffix('.lsr') for entry in entries.values()}
    result = {}
    for name, declaration in aliases.items():
        identifier=declaration
        member=None
        if isinstance(declaration,dict):
            if set(declaration)!={'target','member'}:
                raise Invalid('完整服务兼容入口须明确目标合集与原产品')
            identifier=declaration['target'];member=declaration['member']
            if (not isinstance(identifier,str) or identifier not in entries
                    or not isinstance(member,str) or member not in entries
                    or entries[identifier]['mode']!='view' or entries[member]['mode']=='view'
                    or member not in entries[identifier].get('members',())):
                raise Invalid('兼容合集必须完整包含原产品成员')
        if (not isinstance(name, str) or not re.fullmatch(r'[0-9]{3,4}-[a-z0-9]+(?:-[a-z0-9]+)*', name)
                or not isinstance(identifier, str) or identifier not in entries
                or name.partition('-')[2] != (member or identifier) or name in canonical):
            raise Invalid('兼容下载地址不能越过目录、覆盖其他产品或代替当前地址')
        entry = entries[identifier]
        if type(entry['priority']) is not int or not 1 <= entry['priority'] < 10 ** width:
            raise Invalid('兼容下载地址的目标编号无效')
        result[name] = rule_filename(entry, width=width).removesuffix('.lsr')
    return result
