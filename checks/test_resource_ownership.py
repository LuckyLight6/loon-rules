"""Regressions from the independent image/CSP ownership review."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from checks.source_fixtures import PublicSourceExamples, prepare_workspace
from checks import test_image_resources as image_cases
from loon_rules.exports import publish
from loon_rules.generation import pipeline
from loon_rules.generation.reporting import audit_inventory, verify_inventories
from loon_rules.matching import RuleIndex
from loon_rules.rules import Invalid


class ImageOwnershipReview(PublicSourceExamples):
    def fixture(self):
        return image_cases.SiteImageResources('test_source_host_can_remain_with_the_original_product')

    def config(self):
        config = self.fixture().config()
        config['entries'][2]['extract'][0].pop('exclude-source-host')
        config['entries'][2]['extract'][0]['respect-existing-owners'] = True
        config['source-inventories'][0]['recipe']['respect-existing-owners'] = True
        config['source-inventories'][0]['resource-owner'] = 'images'
        config['sections'].append({'id': 'vendors', 'title': '供应商'})
        config['entries'].append({'id': 'supplier', 'mode': 'compiled', 'priority': 30,
            'section': 'vendors', 'description': '图片供应商', 'boundary': '已核实的供应商空间',
            'sources': [self.fixture().recipe()['source']],
            'include': ['DOMAIN-SUFFIX,supplier.example']})
        config['entries'].append({'id': 'remainder', 'mode': 'compiled', 'priority': 40,
            'section': 'vendors', 'description': '补充范围', 'boundary': '已有补充来源',
            'sources': [self.fixture().recipe()['source']], 'fallback': True, 'domain-remainder': True,
            'include': ['DOMAIN-SUFFIX,video.example', 'DOMAIN-SUFFIX,images.vendor.example',
                        'DOMAIN-SUFFIX,new-supplier.example']})
        return config

    def test_images_keep_existing_product_and_supplier_owners_and_can_move_to_a_new_supplier(self):
        fixture = self.fixture()
        config = self.config()
        source = fixture.recipe()['source']
        inputs = {source: fixture.page()}
        with TemporaryDirectory() as temporary, patch.object(pipeline, 'ROOT', prepare_workspace(temporary)), redirect_stdout(StringIO()):
            root = prepare_workspace(temporary)
            (root / 'rules/loon').mkdir(parents=True)
            entries = pipeline.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'config/endpoint-contracts.json').write_text('[]')
            (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
            for key, entry in entries.items():
                rows = {'product': ['DOMAIN-SUFFIX,video.example'],
                        'supplier': ['DOMAIN-SUFFIX,supplier.example']}.get(key, ['DOMAIN,images.vendor.example'])
                (root / 'rules/loon' / pipeline.rule_filename(entry)).write_text(pipeline.decorate(
                    entry, rows, None, '2026-11-26T00:00:00Z'))
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                inputs[source] = fixture.page('<img src="https://preview.unlisted.supplier.example/a.jpg">'
                    '<img src="https://images.video.example/a.jpg">'
                    '<img src="https://runtime.new-supplier.example/a.jpg">')
                pipeline.run()
                publish(root)
                data = {key: pipeline.rules.read_rules((root / 'rules/loon' / pipeline.rule_filename(entry)).read_text())
                        for key, entry in entries.items()}
                order = pipeline.route_order(config, entries)
                index = RuleIndex(data, order)
                self.assertEqual(index.route('preview.unlisted.supplier.example', order), 'supplier')
                self.assertEqual(index.route('images.video.example', order), 'product')
                self.assertEqual(index.route('runtime.new-supplier.example', order), 'images')
                self.assertNotIn('DOMAIN,preview.unlisted.supplier.example', data['media-all'])
                self.assertNotIn('DOMAIN,images.video.example', data['images'])
                # A later verified supplier namespace must safely take over an old image endpoint.
                next(entry for entry in config['entries'] if entry['id'] == 'supplier')['include'].append('DOMAIN-SUFFIX,new-supplier.example')
                (root / 'config/catalog.json').write_text(json.dumps(config))
                pipeline.run()
                publish(root)
                image_path = root / 'rules/loon' / pipeline.rule_filename(entries['images'])
                self.assertNotIn('runtime.new-supplier.example', image_path.read_text())
                for app in ('loon', 'surge', 'mihomo', 'stash', 'egern', 'surfboard', 'shadowrocket', 'quantumult-x', 'sing-box', 'v2ray'):
                    body = next((root / 'rules' / app).glob('030-supplier.*')).read_text()
                    self.assertIn('new-supplier.example', body)

    def test_complete_image_inventory_rejects_taking_a_known_supplier_namespace(self):
        config = self.config()
        entries = pipeline.validate_declarations(config)
        source = self.fixture().recipe()['source']
        text = self.fixture().page('<img src="https://preview.unlisted.supplier.example/a.jpg">')
        data = {'product': ['DOMAIN-SUFFIX,video.example'],
                'images': ['DOMAIN,images.vendor.example', 'DOMAIN,preview.unlisted.supplier.example'],
                'supplier': ['DOMAIN-SUFFIX,supplier.example'], 'media-all': []}
        spec = config['source-inventories'][0]
        state = audit_inventory(spec, {source: text}, data, order=pipeline.route_order(config, entries), entries=entries)
        self.assertEqual(state['state'], 'review')
        with self.assertRaises(Invalid):
            verify_inventories([spec], {spec['id']: state}, data=data, order=pipeline.route_order(config, entries))

    def test_complete_mux_csp_detects_an_unlisted_network_worker_dependency(self):
        catalog = json.loads((pipeline.ROOT / 'config/catalog.json').read_text())
        spec = next(item for item in catalog['source-inventories'] if item['id'] == 'mux-complete-csp')
        text = ''.join('<h2 id="' + section + '">CSP</h2><pre><code>'
                       'connect-src https://*.mux.com https://*.litix.io;\n'
                       'worker-src blob: https://runtime.worker.example;'
                       '</code></pre>' for section in ('granular-csp-configuration', 'upload-and-media-handling', 'complete-example'))
        data = {'mux-data-analytics': ['DOMAIN-SUFFIX,litix.io'],
                'mux-video-platform': ['DOMAIN-SUFFIX,mux.com']}
        state = audit_inventory(spec, {spec['source']: text}, data)
        self.assertEqual(state['state'], 'review')
        with self.assertRaises(Invalid):
            verify_inventories([spec], {spec['id']: state})
