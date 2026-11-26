"""Every supported app gets real rule files below the same publication root."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from loon_rules.exports import publish
from loon_rules.rules import Invalid


class ClientDirectories(unittest.TestCase):
    def test_all_apps_receive_own_files_and_legacy_publication_paths_are_removed(self):
        clients = {'loon': 'lsr', 'surge': 'list', 'mihomo': 'yaml', 'stash': 'yaml',
                   'egern': 'yaml', 'shadowrocket': 'list', 'surfboard': 'list',
                   'quantumult-x': 'list', 'sing-box': 'json', 'v2ray': 'json'}
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / 'rules/loon/1010-product.lsr'
            canonical.parent.mkdir(parents=True)
            text = '# name: product\nDOMAIN,api.product.example\n'
            canonical.write_text(text)
            (root / 'rules/1010-product.lsr').write_text(text)
            legacy = root / 'dist/surge-compatible/1010-product.list'
            legacy.parent.mkdir(parents=True)
            legacy.write_text('DOMAIN,previous.product.example\n')
            publish(root)
            for client, extension in clients.items():
                with self.subTest(client=client):
                    output = root / 'rules' / client / ('1010-product.' + extension)
                    self.assertTrue(output.is_file(), str(output))
                    self.assertIn('api.product.example', output.read_text())
                    self.assertTrue((output.parent / 'README.md').is_file())
                    index = (output.parent / 'README.md').read_text()
                    self.assertIn('main/rules/' + client + '/1010-product.' + extension, index)
            self.assertTrue((root / 'rules/surge/1010-product.list').is_file())
            self.assertEqual(canonical.read_bytes(), (root / 'rules/surge/1010-product.list').read_bytes())
            self.assertFalse(list((root / 'rules').glob('*.lsr')))
            self.assertFalse(list((root / 'rules').glob('*.list')))
            self.assertFalse(any(path.is_file() for path in (root / 'dist').rglob('*')))
            manifest = json.loads((root / 'rules/manifest.json').read_text())
            self.assertEqual(set(manifest['clients']), set(clients))
            for client in clients:
                self.assertEqual(manifest['clients'][client]['directory'], 'rules/' + client)
            self.assertEqual(publish(root, check=True), 0)

    def test_relocating_outputs_still_rejects_an_unsupported_previously_available_format(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / 'rules/loon/1010-product.lsr'
            canonical.parent.mkdir(parents=True)
            text = '# name: product\nDOMAIN,api.product.example\nIP-ASN,399358,no-resolve\n'
            canonical.write_text(text)
            (root / 'rules/1010-product.lsr').write_text(text)
            old_manifest = root / 'dist/manifest.json'
            old_manifest.parent.mkdir()
            old_manifest.write_text(json.dumps({'schema-version': 1, 'formats': {
                'sing-box': {'rules': {'1010-product': {'status': 'available',
                                                      'path': 'dist/sing-box/1010-product.json'}}}}}))
            before = {path: path.read_bytes() for path in root.rglob('*') if path.is_file()}
            with self.assertRaisesRegex(Invalid, '不能自动删减'):
                publish(root)
            self.assertEqual(before, {path: path.read_bytes() for path in root.rglob('*') if path.is_file()})

    def test_retired_flat_files_are_not_used_as_the_canonical_corpus(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'rules').mkdir()
            (root / 'rules/1010-product.lsr').write_text('DOMAIN,api.product.example\n')
            with self.assertRaises(Invalid):
                publish(root)
