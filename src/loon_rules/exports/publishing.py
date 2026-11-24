"""Generate native files and an index; never publish an incomplete group as usable."""
import json
from pathlib import Path

from loon_rules.rules import Invalid, read_rules
from .formats import Unsupported, convert, yaml_text


BASE = 'https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/'
FORMATS = {
    'loon': ('lsr', 'Loon'),
    'surge': ('list', 'Surge'),
    'clash-classical': ('yaml', 'Mihomo / Stash'),
    'egern': ('yaml', 'Egern'),
    'surfboard': ('list', 'Surfboard'),
    'shadowrocket': ('list', 'Shadowrocket'),
    'quantumult-x': ('list', 'Quantumult X'),
    'sing-box': ('json', 'sing-box'),
    'v2ray': ('json', 'V2Ray'),
}
OUTPUT_FOLDERS = {'surfboard': 'surge-compatible', 'shadowrocket': 'surge-compatible'}
CLIENTS = {
    'loon': {'format': 'loon', 'entry': 'remote-rule'},
    'surge': {'format': 'surge', 'entry': 'rule-set'},
    'mihomo': {'format': 'clash-classical', 'entry': 'rule-provider'},
    'stash': {'format': 'clash-classical', 'entry': 'rule-provider'},
    'egern': {'format': 'egern', 'entry': 'rule-set'},
    'surfboard': {'format': 'surfboard', 'entry': 'rule-set'},
    'shadowrocket': {'format': 'shadowrocket', 'entry': 'rule-set',
                     'verification': 'compatibility-profile-not-device-tested'},
    'quantumult-x': {'format': 'quantumult-x', 'entry': 'filter-remote',
                     'requires': 'force-policy'},
    'sing-box': {'format': 'sing-box', 'entry': 'remote-source-rule-set'},
    'v2ray': {'format': 'v2ray', 'entry': 'routing-config-fragment',
              'requires': 'replace-PROXY-and-merge-routing-rules'},
}


def condition_count(value):
    if isinstance(value, list):
        return sum(1 if isinstance(item, str) else condition_count(item) for item in value)
    if isinstance(value, dict):
        return sum(condition_count(item) for item in value.values())
    return 0


def build(root):
    expected = {}
    manifest = {'schema-version': 1, 'clients': CLIENTS, 'formats': {}}
    paths = sorted((root / 'rules').glob('*.lsr'))
    if not paths:
        raise Invalid('没有可转换的客户端规则')
    canonical = {path.stem: (path, path.read_text(), read_rules(path.read_text())) for path in paths}
    for target, (extension, label) in FORMATS.items():
        items = {}
        index = ['# ' + label + ' 规则', '',
                 '从同一份规则生成，编号和选择顺序与[主清单](../../docs/rules.md)一致。合集与成员二选一', '',
                 '使用前阅读[客户端格式与限制](../../docs/clients.md)。标为无法转换的组不提供删减版订阅', '',
                 '| 序号 | 英文名称 | 中文名称 | 订阅 / 状态 |', '|---|---|---|---|']
        for name, (path, text, rows) in canonical.items():
            header = [line for line in text.splitlines() if line.startswith('# ')]
            attributes = dict(line.removeprefix('# ').split(': ', 1) for line in header if ': ' in line)
            description = next((line.removeprefix('# description: ') for line in header
                                if line.startswith('# description: ')), name)
            number, _, identifier = name.partition('-')
            item = {'source': path.relative_to(root).as_posix(), 'rule-count': len(rows),
                    **{key: attributes[key] for key in ('description', 'created-at', 'updated-at') if key in attributes}}
            try:
                converted = convert(target, rows)
            except Unsupported as error:
                item.update(status='unsupported', reason=str(error))
                status = str(error)
            else:
                item['output-rule-count'] = condition_count(converted)
                if target == 'loon':
                    output = path.relative_to(root).as_posix()
                elif target == 'surge':
                    output = path.with_suffix('.list').relative_to(root).as_posix()
                    expected[output] = text
                else:
                    folder = OUTPUT_FOLDERS.get(target, target)
                    output = f'dist/{folder}/{name}.{extension}'
                    if extension == 'json':
                        content = json.dumps(converted, ensure_ascii=False, indent=2) + '\n'
                    else:
                        body = yaml_text(converted) if extension == 'yaml' else '\n'.join(converted)
                        converted_header = [line for line in header if not line.startswith('# rule-count: ')]
                        content = '\n'.join(converted_header + [
                            '# canonical-rule-count: ' + str(len(rows)),
                            '# rule-count: ' + str(item['output-rule-count']),
                            f'# format: {folder}', '# canonical: ' + item['source'], '', body, '',
                        ])
                    expected[output] = content
                item.update(status='available', path=output)
                status = '[订阅](' + BASE + output + ')'
            items[name] = item
            index.append(f'| {number} | {identifier} | {description} | {status} |')
        manifest['formats'][target] = {'rules': items,
                                      'available': sum(item['status'] == 'available' for item in items.values()),
                                      'unsupported': sum(item['status'] == 'unsupported' for item in items.values())}
        expected[f'dist/{target}/README.md'] = '\n'.join(index) + '\n'
    expected['dist/manifest.json'] = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    return expected


def publish(root, *, check=False):
    root = Path(root)
    expected = build(root)
    manifest_path = root / 'dist/manifest.json'
    if manifest_path.is_file():
        previous = json.loads(manifest_path.read_text())
        current = json.loads(expected['dist/manifest.json'])
        for target, group in previous['formats'].items():
            for name, item in group['rules'].items():
                updated = current['formats'].get(target, {}).get('rules', {}).get(name)
                if item['status'] == 'available' and updated and updated['status'] != 'available':
                    raise Invalid('已发布客户端订阅不能自动删减：' + target + '/' + name + '；' + updated['reason'])
    present = {p.relative_to(root).as_posix() for target, (extension, _) in FORMATS.items()
               for folder in {target, OUTPUT_FOLDERS.get(target, target)}
               for pattern in ('*.' + extension, 'README.md') for p in (root / 'dist' / folder).glob(pattern)}
    present.update(p.relative_to(root).as_posix() for p in (root / 'rules').glob('*.list'))
    if manifest_path.is_file():
        present.add('dist/manifest.json')
    stale = present - expected.keys()
    changed = {name: content for name, content in expected.items()
               if not (root / name).is_file() or (root / name).read_text() != content}
    if check:
        if changed or stale:
            raise Invalid('客户端成品未同步：' + min(set(changed) | stale))
        return 0
    # All source parsing and conversions finish before any published file changes.
    for name, content in changed.items():
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + '.new')
        temporary.write_text(content)
        temporary.replace(destination)
    for name in stale:
        (root / name).unlink()
    return len(changed) + len(stale)
