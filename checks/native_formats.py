"""Check generated files with optional, isolated official client binaries."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from loon_rules.project import ROOT


def command(arguments, *, timeout=30):
    result = subprocess.run([str(value) for value in arguments], capture_output=True,
                            text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(' '.join(str(value) for value in arguments[:3]) + '\n' +
                           result.stdout + result.stderr)
    return result.stdout + result.stderr


def files(target):
    manifest = json.loads((ROOT / 'dist/manifest.json').read_text())
    return [ROOT / item['path'] for item in manifest['formats'][target]['rules'].values()
            if item['status'] == 'available']


def mihomo(binary):
    sources = files('clash-classical')
    with TemporaryDirectory(prefix='native-mihomo-') as temporary:
        folder = Path(temporary)
        (folder / 'providers').mkdir()
        providers = {}
        for source in sources:
            shutil.copyfile(source, folder / 'providers' / source.name)
            providers[source.stem] = {'type': 'file', 'behavior': 'classical',
                                      'format': 'yaml', 'path': 'providers/' + source.name}
        config = {'mode': 'rule', 'log-level': 'warning',
                  'rule-providers': providers,
                  'rules': ['RULE-SET,' + name + ',DIRECT' for name in providers] + ['MATCH,DIRECT']}
        profile = folder / 'config.yaml'
        profile.write_text(json.dumps(config))
        output = command([binary, '-t', '-d', folder, '-f', profile], timeout=180)
        if 'successful' not in output:
            raise RuntimeError('Mihomo 没有确认配置解析成功：' + output)
    return {'files': len(sources), 'version': command([binary, '-v']).strip()}


def singbox(binary):
    sources = files('sing-box')
    with TemporaryDirectory(prefix='native-sing-box-') as temporary:
        folder = Path(temporary)
        def compile_one(source):
            command([binary, 'rule-set', 'compile', '--output', folder / (source.stem + '.srs'), source])
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(compile_one, sources))
    return {'files': len(sources), 'version': command([binary, 'version']).strip()}


def v2ray(binary):
    sources = files('v2ray')
    with TemporaryDirectory(prefix='native-v2ray-') as temporary:
        base = Path(temporary) / 'base.json'
        base.write_text(json.dumps({'outbounds': [{'tag': 'PROXY', 'protocol': 'freedom', 'settings': {}}]}))
        def check_one(source):
            output = command([binary, 'test', '-c', base, '-c', source])
            if 'Configuration OK.' not in output:
                raise RuntimeError('V2Ray 没有确认规则解析成功：' + str(source) + '\n' + output)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(check_one, sources))
    return {'files': len(sources), 'version': command([binary, 'version']).strip()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mihomo', type=Path)
    parser.add_argument('--sing-box', type=Path)
    parser.add_argument('--v2ray', type=Path)
    options = parser.parse_args()
    report = {}
    for name, binary, verify in [('mihomo', options.mihomo, mihomo),
                                 ('sing-box', options.sing_box, singbox),
                                 ('v2ray', options.v2ray, v2ray)]:
        if binary:
            report[name] = verify(binary.resolve())
            print(f'{name}: {report[name]["files"]} 份文件通过原生格式检查', flush=True)
    if not report:
        parser.error('至少指定一个官方客户端程序路径')
    (ROOT / 'build').mkdir(exist_ok=True)
    path = ROOT / 'build/native-formats-report.json'
    previous = json.loads(path.read_text()) if path.is_file() else {}
    path.write_text(json.dumps({**previous, **report}, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
