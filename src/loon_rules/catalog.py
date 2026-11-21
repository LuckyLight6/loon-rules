"""从产品声明生成兼容清单；旧格式的独立调用仍按原约定读取。"""
from copy import deepcopy

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
