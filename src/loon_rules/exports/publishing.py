"""Publish every supported app's files below rules/<app>."""
import json
from pathlib import Path

from loon_rules.rules import Invalid, read_rules
from loon_rules.catalog import subscription_aliases
from .formats import Unsupported, convert, yaml_text


BASE = 'https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/'
FORMATS = {
    'loon': ('lsr', 'Loon'), 'surge': ('list', 'Surge'),
    'clash-classical': ('yaml', 'Mihomo / Stash'), 'egern': ('yaml', 'Egern'),
    'surfboard': ('list', 'Surfboard'), 'shadowrocket': ('list', 'Shadowrocket'),
    'quantumult-x': ('list', 'Quantumult X'), 'sing-box': ('json', 'sing-box'),
    'v2ray': ('json', 'V2Ray'),
}
CLIENTS = {
    'loon': {'format': 'loon', 'entry': 'remote-rule'},
    'surge': {'format': 'surge', 'entry': 'rule-set'},
    'mihomo': {'format': 'clash-classical', 'entry': 'rule-provider'},
    'stash': {'format': 'clash-classical', 'entry': 'rule-provider'},
    'egern': {'format': 'egern', 'entry': 'rule-set'},
    'surfboard': {'format': 'surfboard', 'entry': 'rule-set'},
    'shadowrocket': {'format': 'shadowrocket', 'entry': 'rule-set',
                     'verification': 'compatibility-profile-not-device-tested'},
    'quantumult-x': {'format': 'quantumult-x', 'entry': 'filter-remote', 'requires': 'force-policy'},
    'sing-box': {'format': 'sing-box', 'entry': 'remote-source-rule-set'},
    'v2ray': {'format': 'v2ray', 'entry': 'routing-config-fragment',
              'requires': 'replace-PROXY-and-merge-routing-rules'},
}
LEGACY_FOLDERS = {'surfboard': 'surge-compatible', 'shadowrocket': 'surge-compatible'}


def condition_count(value):
    if isinstance(value, list):
        return sum(1 if isinstance(item, str) else condition_count(item) for item in value)
    if isinstance(value, dict):
        return sum(condition_count(item) for item in value.values())
    return 0


def build(root):
    expected = {}
    profiles = {client: {**profile, 'directory': 'rules/' + client,
                         'extension': FORMATS[profile['format']][0]}
                for client, profile in CLIENTS.items()}
    manifest = {'schema-version': 2, 'clients': profiles, 'formats': {}}
    config_path = root / 'config/catalog.json'
    aliases = subscription_aliases(json.loads(config_path.read_text())) if config_path.is_file() else {}
    paths = sorted(path for path in (root / 'rules/loon').glob('*.lsr') if path.stem not in aliases)
    if not paths:
        raise Invalid('没有可转换的客户端规则：rules/loon')
    canonical = {path.stem: (path, path.read_text(), read_rules(path.read_text())) for path in paths}
    if not set(aliases.values()) <= canonical.keys():
        raise Invalid('兼容下载地址缺少当前规则成品')
    if aliases:
        manifest['aliases'] = aliases
    navigation = ['# 规则下载', '', '选择正在使用的代理应用；各目录都包含该应用的实际规则文件。', '',
                  '分组与执行顺序见[规则清单](../docs/rules.md)，格式限制见[客户端说明](../docs/clients.md)。', '',
                  '| 代理应用 | 下载目录 |', '|---|---|']
    for target, (extension, label) in FORMATS.items():
        clients = [client for client, profile in CLIENTS.items() if profile['format'] == target]
        indexes = {}
        for client in clients:
            title = {'mihomo': 'Mihomo', 'stash': 'Stash'}.get(client, label)
            navigation.append(f'| {title} | [{client}]({client}/README.md) |')
            indexes[client] = ['# ' + title + ' 规则', '',
                '编号和选择顺序与[主清单](../../docs/rules.md)一致。合集与成员二选一。', '',
                '使用前阅读[客户端格式与限制](../../docs/clients.md)。标为无法转换的组不提供删减版订阅。', '',
                '| 序号 | 英文名称 | 中文名称 | 订阅 / 状态 |', '|---|---|---|---|']
        items = {}
        for name, (path, text, rows) in canonical.items():
            header = [line for line in text.splitlines() if line.startswith('# ')]
            attributes = dict(line.removeprefix('# ').split(': ', 1) for line in header if ': ' in line)
            description = attributes.get('description', name)
            number, _, identifier = name.partition('-')
            item = {'source': path.relative_to(root).as_posix(), 'rule-count': len(rows),
                    **{key: attributes[key] for key in ('description', 'created-at', 'updated-at') if key in attributes}}
            try:
                converted = convert(target, rows)
            except Unsupported as error:
                item.update(status='unsupported', reason=str(error))
                statuses = {client: str(error) for client in clients}
            else:
                item['output-rule-count'] = condition_count(converted)
                if target in ('loon', 'surge'):
                    content = text
                elif extension == 'json':
                    content = json.dumps(converted, ensure_ascii=False, indent=2) + '\n'
                else:
                    body = yaml_text(converted) if extension == 'yaml' else '\n'.join(converted)
                    converted_header = [line for line in header if not line.startswith('# rule-count: ')]
                    content = '\n'.join(converted_header + [
                        '# canonical-rule-count: ' + str(len(rows)),
                        '# rule-count: ' + str(item['output-rule-count']),
                        f'# format: {target}', '# canonical: ' + item['source'], '', body, '',
                    ])
                outputs = {client: f'rules/{client}/{name}.{extension}' for client in clients}
                for output in outputs.values():
                    expected[output] = content
                item.update(status='available', path=outputs[clients[0]], paths=outputs)
                statuses = {client: '[订阅](' + BASE + output + ')' for client, output in outputs.items()}
            items[name] = item
            for client in clients:
                indexes[client].append(f'| {number} | {identifier} | {description} | {statuses[client]} |')
        manifest['formats'][target] = {'rules': items,
            'available': sum(item['status'] == 'available' for item in items.values()),
            'unsupported': sum(item['status'] == 'unsupported' for item in items.values())}
        for alias, name in aliases.items():
            item = items[name]
            if item['status'] == 'available':
                for output in item['paths'].values():
                    alias_path = Path(output).with_name(alias + '.' + extension).as_posix()
                    expected[alias_path] = expected[output]
        for client, index in indexes.items():
            expected[f'rules/{client}/README.md'] = '\n'.join(index) + '\n'
    expected['rules/README.md'] = '\n'.join(navigation) + '\n'
    expected['rules/manifest.json'] = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    return expected


def publish(root, *, check=False):
    root = Path(root)
    expected = build(root)
    current = json.loads(expected['rules/manifest.json'])
    manifest_path = root / 'rules/manifest.json'
    previous_path = manifest_path if manifest_path.is_file() else root / 'dist/manifest.json'
    if previous_path.is_file():
        previous = json.loads(previous_path.read_text())
        # The v1 -> v2 directory migration explicitly retires the old public URLs.
        if previous.get('schema-version', 1) >= 2 and not set(previous.get('aliases', {})) <= set(current.get('aliases', {})):
            raise Invalid('已发布的兼容下载地址不能静默撤销')
        for target, group in previous['formats'].items():
            for name, item in group['rules'].items():
                canonical = current.get('aliases', {}).get(name, name)
                updated = current['formats'].get(target, {}).get('rules', {}).get(canonical)
                if item['status'] == 'available' and updated and updated['status'] != 'available':
                    raise Invalid('已发布客户端订阅不能自动删减：' + target + '/' + name + '；' + updated['reason'])
    present = {path.relative_to(root).as_posix() for client in CLIENTS
               for path in (root / 'rules' / client).glob('*') if path.is_file()}
    present.update(path.relative_to(root).as_posix() for pattern in ('*.lsr', '*.list', 'README.md', 'manifest.json')
                   for path in (root / 'rules').glob(pattern) if path.is_file())
    present.update(path.relative_to(root).as_posix() for target, (extension, _) in FORMATS.items()
                   for folder in {target, LEGACY_FOLDERS.get(target, target)}
                   for pattern in ('*.' + extension, 'README.md')
                   for path in (root / 'dist' / folder).glob(pattern) if path.is_file())
    if (root / 'dist/manifest.json').is_file():
        present.add('dist/manifest.json')
    stale = present - expected.keys()
    changed = {name: content for name, content in expected.items()
               if not (root / name).is_file() or (root / name).read_text() != content}
    if check:
        if changed or stale:
            raise Invalid('客户端成品未同步：' + min(set(changed) | stale))
        return 0
    # Parse and convert the entire candidate before changing any published output.
    for name, content in changed.items():
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + '.new')
        temporary.write_text(content)
        temporary.replace(destination)
    directories = set()
    for name in stale:
        destination = root / name
        destination.unlink()
        parent = destination.parent
        while parent != root:
            directories.add(parent)
            parent = parent.parent
    for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass
    return len(changed) + len(stale)
