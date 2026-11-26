"""Follow Netflix's published connection instructions without claiming unrelated hosts."""
import copy
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from checks.source_fixtures import PublicSourceExamples, prepare_workspace
from loon_rules.generation import pipeline
from loon_rules.rules import Invalid


class NetflixSources(PublicSourceExamples):
    def config(self):
        current = json.loads((Path(__file__).resolve().parents[1] / 'config/catalog.json').read_text())
        identifiers = ['netflix-video-and-delivery', 'netflix-connection-tests']
        children = [copy.deepcopy(entry) for entry in current['entries'] if entry['id'] in identifiers]
        self.assertEqual({entry['id'] for entry in children}, set(identifiers))
        combined = {'id': 'overseas-media-all', 'mode': 'view', 'priority': 3800, 'section': 'media',
                    'description': '海外影音', 'boundary': '替代两项细分', 'members': identifiers}
        specs = [copy.deepcopy(spec) for spec in current['source-inventories']
                 if spec['id'] in ('netflix-official-network-addresses', 'netflix-direct-measurement-service')]
        return {'schema-version': 2, 'priority-width': 4, 'entries': [combined, *children],
                'sections': [{'id': 'media', 'title': '海外影音'}], 'shared-negatives': [],
                'critical': {host: [entry['id']] for entry in children for host in entry['product-probes']},
                'source-inventories': specs}

    def document(self, names=(), *, extra_list=()):
        hosts = ['secure.netflix.com', 'appboot.netflix.com', 'uiboot.netflix.com', 'fast.com', *names, *extra_list]
        return ('<ul><li><p>Make sure your device is able to connect to these Netflix addresses:</p><ul>'
                + ''.join('<li><p>' + host + '</p></li>' for host in hosts) + '</ul></li></ul>'
                + '<p>Using a web browser, go to ' + ' or '.join(['fast.com', *names])
                + ' to test your internet speed and connection directly to Netflix.</p>')

    def test_new_owned_measurement_names_reach_the_fine_group_bundle_and_all_client_outputs(self):
        from loon_rules.exports import publish
        config = self.config()
        source = config['source-inventories'][0]['source']
        product = next(entry for entry in config['entries'] if entry['id'] == 'netflix-video-and-delivery')
        inputs = {source: self.document(), product['projection'][0]['source']: 'DOMAIN-SUFFIX,netflix.com'}
        with TemporaryDirectory() as tmp, patch.object(pipeline, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            (root / 'rules' / 'loon').mkdir(parents=True, exist_ok=True)
            (root / 'config/endpoint-contracts.json').write_text('[]')
            entries = pipeline.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
            for key, entry in entries.items():
                rows = ['DOMAIN-SUFFIX,netflix.com'] if key == 'netflix-video-and-delivery' else ['DOMAIN-SUFFIX,fast.com']
                if key == 'overseas-media-all': rows += ['DOMAIN-SUFFIX,netflix.com']
                (root / 'rules' / 'loon' / pipeline.rule_filename(entry)).write_text(
                    pipeline.decorate(entry, rows, None, '2026-11-20T00:00:00Z'))
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                names = []
                for host in ('first-unprefilled.example', 'second-unprefilled.example'):
                    names.append(host)
                    inputs[source] = self.document(names)
                    pipeline.run()
                    publish(root)
                    for stem in ('3825-netflix-connection-tests', '3800-overseas-media-all'):
                        path = root / 'rules' / 'loon' / (stem + '.lsr')
                        self.assertIn('DOMAIN-SUFFIX,' + host, path.read_text())
                        self.assertEqual(path.read_bytes(), (path.parent.with_name('surge') / path.with_suffix('.list').name).read_bytes())
                        for client in ('sing-box', 'mihomo', 'v2ray'):
                            self.assertTrue(any(host in file.read_text() for file in (root / 'rules' / client).rglob('*') if file.is_file()))
                    self.assertNotIn(host, (root / 'rules/loon/3820-netflix-video-and-delivery.lsr').read_text())
                    self.assertEqual(pipeline.run(offline=True), 0)
                for change in ('missing-purpose', 'unowned-entry', 'shared-suffix', 'shared-host', 'address-type'):
                    before = {file: file.read_bytes() for folder in ('rules', 'dist', 'data')
                              for file in (root / folder).rglob('*') if file.is_file()}
                    inputs[source] = self.document(names)
                    if change == 'missing-purpose': inputs[source] = inputs[source].replace('connection directly to Netflix', 'ordinary information')
                    if change == 'unowned-entry': inputs[source] = self.document(names, extra_list=['unowned.other-provider.example'])
                    if change == 'shared-suffix': inputs[source] = self.document(names, extra_list=['github.io'])
                    if change == 'shared-host': inputs[source] = self.document(names, extra_list=['storage.googleapis.com'])
                    if change == 'address-type': inputs[source] = self.document(names, extra_list=['8.8.8.8'])
                    with self.subTest(change=change), self.assertRaises(Invalid): pipeline.run()
                    self.assertEqual(before, {file: file.read_bytes() for folder in ('rules', 'dist', 'data')
                                              for file in (root / folder).rglob('*') if file.is_file()})
