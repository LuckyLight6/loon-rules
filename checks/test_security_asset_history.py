"""Other sources must not hide changed types or missing source assets."""
import copy
import json
from contextlib import redirect_stdout
from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from checks.source_fixtures import PublicSourceExamples, prepare_workspace
from loon_rules.generation import pipeline
from loon_rules.rules import Invalid


class SecurityAssetHistory(PublicSourceExamples):
    def recipe(self):
        return {
            'format': 'security-program-domains', 'complete': True,
            'program': {'handle': 'vendor', 'name': 'Vendor', 'url': 'https://hackerone.com/vendor'},
            'assets': [{'type': 'URL', 'read': 'identifier', 'purpose-prefix': 'Product API.'}],
            'non-network-types': {'SOURCE_CODE': '源码项目不是应用服务入口'},
        }

    def asset(self, host):
        return {'asset_type': 'URL', 'asset_identifier': 'https://' + host + '/v1',
                'instruction': 'Product API.', 'eligible_for_submission': True}

    def document(self):
        return [{**self.recipe()['program'], 'targets': {
            'in_scope': [self.asset('api-one.product.example'), self.asset('api-two.product.example'),
                         {'asset_type': 'SOURCE_CODE', 'asset_identifier': 'https://repo.product.example/sdk',
                          'instruction': 'SDK sources', 'eligible_for_submission': True}],
            'out_of_scope': []}}]

    def config(self):
        source = 'https://publisher.example/program.json'
        corroborating = 'https://publisher.example/product-domains.txt'
        recipe = self.recipe()
        child = {'id': 'product', 'priority': 20, 'section': 'products', 'mode': 'compiled',
                 'description': '产品', 'boundary': '两份独立来源核对', 'policy-hint': 'global',
                 'sources': [source, corroborating],
                 'extract': [{**recipe, 'source': source},
                             {'format': 'domain-scope-list', 'source': corroborating}]}
        combined = {'id': 'products-all', 'priority': 10, 'section': 'products', 'mode': 'view',
                    'description': '合集', 'boundary': '替代产品细分', 'members': ['product']}
        return {'schema-version': 2, 'sections': [{'id': 'products', 'title': '产品'}],
                'entries': [combined, child], 'shared-negatives': [],
                'critical': {'api-one.product.example': ['product'], 'api-two.product.example': ['product']},
                'source-inventories': [
                    {'id': 'complete-program', 'source': source, 'owners': ['product'], 'recipe': recipe},
                    {'id': 'domain-source', 'source': corroborating, 'owners': ['product'],
                     'recipe': {'format': 'domain-scope-list'}}]}

    def workspace(self, root, config):
        (root / 'rules' / 'loon').mkdir(parents=True, exist_ok=True)
        (root / 'config/endpoint-contracts.json').write_text('[]')
        entries = pipeline.validate_declarations(config)
        (root / 'config/catalog.json').write_text(json.dumps(config))
        (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
        for entry in entries.values():
            (root / 'rules' / 'loon' / pipeline.rule_filename(entry)).write_text(
                pipeline.decorate(entry, ['DOMAIN-SUFFIX,product.example'], None, '2026-11-20T00:00:00Z'))

    def outputs(self, root):
        return {file: file.read_bytes() for folder in ('rules', 'data', 'dist')
                for file in (root / folder).rglob('*') if file.is_file()}

    def test_other_source_coverage_does_not_hide_retyping_removal_or_an_inventory_rename(self):
        from loon_rules.exports import publish
        config = self.config()
        source, corroborating = config['entries'][1]['sources']
        initial = self.document()
        inputs = {source: json.dumps(initial), corroborating: 'DOMAIN-SUFFIX,product.example'}
        with TemporaryDirectory() as tmp, patch.object(pipeline, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            self.workspace(root, config)
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                publish(root)
                accepted = self.outputs(root)
                for change in ('type', 'same-total', 'host-case', 'missing', 'renamed-inventory'):
                    document = copy.deepcopy(initial)
                    if change != 'missing':
                        document[0]['targets']['in_scope'][1]['asset_type'] = 'SOURCE_CODE'
                    if change == 'same-total':
                        from collections import Counter
                        document[0]['targets']['in_scope'][2]['asset_type'] = 'URL'
                        document[0]['targets']['in_scope'][2]['instruction'] = 'Product API.'
                        self.assertEqual(Counter(asset['asset_type'] for asset in initial[0]['targets']['in_scope']),
                                         Counter(asset['asset_type'] for asset in document[0]['targets']['in_scope']))
                    if change == 'host-case':
                        document[0]['targets']['in_scope'][1]['asset_identifier'] = 'https://API-TWO.PRODUCT.EXAMPLE/v1'
                    if change == 'missing': document[0]['targets']['in_scope'].pop(1)
                    changed_config = copy.deepcopy(config)
                    if change == 'renamed-inventory': changed_config['source-inventories'][0]['id'] = 'renamed-program'
                    (root / 'config/catalog.json').write_text(json.dumps(changed_config))
                    inputs[source] = json.dumps(document)
                    with self.subTest(change=change), self.assertRaisesRegex(Invalid, '类型|资产|目标'):
                        pipeline.run()
                    self.assertEqual(accepted, self.outputs(root))

    def test_security_scope_movement_is_not_a_type_change_or_permission_to_remove_network_coverage(self):
        config = self.config()
        source, corroborating = config['entries'][1]['sources']
        document = self.document()
        inputs = {source: json.dumps(document), corroborating: 'DOMAIN-SUFFIX,product.example'}
        with TemporaryDirectory() as tmp, patch.object(pipeline, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            self.workspace(root, config)
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                withdrawn = document[0]['targets']['in_scope'].pop(1)
                withdrawn['eligible_for_submission'] = False
                document[0]['targets']['out_of_scope'].append(withdrawn)
                document[0]['targets']['in_scope'].pop()  # Removing an SDK listing does not retire an API.
                inputs[source] = json.dumps(document)
                self.assertEqual(pipeline.run(), 0)
                self.assertIn('DOMAIN-SUFFIX,product.example', (root / 'rules/loon/020-product.lsr').read_text())
                before = self.outputs(root)
                document[0]['targets']['out_of_scope'][0]['asset_type'] = 'SOURCE_CODE'
                inputs[source] = json.dumps(document)
                with self.assertRaisesRegex(Invalid, '类型'): pipeline.run()
                self.assertEqual(before, self.outputs(root))

    def test_regular_updates_cannot_drop_the_history_version_or_asset_records(self):
        config = self.config()
        source, corroborating = config['entries'][1]['sources']
        document = self.document()
        inputs = {source: json.dumps(document), corroborating: 'DOMAIN-SUFFIX,product.example'}
        with TemporaryDirectory() as tmp, patch.object(pipeline, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            self.workspace(root, config)
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                path = root / 'data/maintenance-state.json'
                original = json.loads(path.read_text())
                self.assertEqual(original.get('security-program-history-version'), 1)
                for change in ('version', 'schema', 'both'):
                    state = copy.deepcopy(original)
                    if change in ('version', 'both'): state.pop('security-program-history-version')
                    if change in ('schema', 'both'):
                        state['source-inventories']['complete-program']['program-assets'].pop('asset-schema')
                    path.write_text(json.dumps(state))
                    before = self.outputs(root)
                    with self.subTest(change=change), self.assertRaisesRegex(Invalid, '历史|记录|版本'):
                        pipeline.run()
                    self.assertEqual(before, self.outputs(root))
