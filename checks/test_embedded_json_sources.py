"""Read explicitly encoded service records without guessing hosts from page prose."""
import copy
import json

from checks.source_fixtures import PublicSourceExamples, prepare_workspace
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class EmbeddedJSONServices(PublicSourceExamples):
    def recipe(self):
        return {
            'source': 'https://video.vendor.example/', 'format': 'next-service-urls',
            'decode-json': [['config', 'pageData']],
            'identity': [
                {'path': ['config', 'brand'], 'equals': 'Video'},
                {'path': ['config', 'environment'], 'equals': 'prd'},
                {'path': ['config', 'published'], 'equals': True},
                {'path': ['config', 'pageData', 'dataSources', '*', 'type'], 'each-equals': 'graphql'},
                {'path': ['config', 'pageData', 'dataSources', '*', 'httpMethod'], 'each-equals': 'post'},
                {'path': ['config', 'pageData', 'dataSources', '*'],
                 'each-keys': ['id', 'type', 'url', 'body', 'data', 'httpMethod', 'variables']},
            ],
            'paths': [['config', 'flagsUrl'], ['config', 'pageData', 'dataSources', '*', 'url']],
        }

    def record(self, host='api.platform.example'):
        return {'id': '1', 'type': 'graphql', 'url': 'https://' + host + '/graphql',
                'body': 'query CurrentProduct { title }', 'data': {}, 'httpMethod': 'post', 'variables': '[]'}

    def document(self, records=None):
        return {'config': {'brand': 'Video', 'environment': 'prd', 'published': True,
                           'flagsUrl': 'https://feature.platform.example/labs',
                           'pageData': json.dumps({'dataSources': records or [self.record()]})},
                'otherProduct': {'url': 'https://unrelated.vendor.example/'}}

    def html(self, document):
        return '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(document) + '</script>'

    def test_encoded_records_follow_new_urls_without_scanning_unrelated_fields(self):
        document = self.document([self.record(), self.record('brand-new.other-provider.example')])
        self.assertEqual(extract_rows(self.recipe(), self.html(document)), {
            'DOMAIN,api.platform.example', 'DOMAIN,feature.platform.example',
            'DOMAIN,brand-new.other-provider.example'})

    def test_record_role_shape_and_encoded_json_changes_stop_partial_updates(self):
        for changed in ('type', 'method', 'extra-field', 'missing-field', 'missing-records',
                        'already-decoded', 'truncated', 'duplicate-url', 'non-json-number'):
            document = self.document()
            body = json.loads(document['config']['pageData'])
            if changed == 'type': body['dataSources'][0]['type'] = 'other-product'
            if changed == 'method': body['dataSources'][0]['httpMethod'] = 'get'
            if changed == 'extra-field': body['dataSources'][0]['backupUrl'] = 'https://unknown.other.example/'
            if changed == 'missing-field': del body['dataSources'][0]['url']
            if changed == 'missing-records': body['dataSources'] = []
            document['config']['pageData'] = json.dumps(body)
            if changed == 'already-decoded': document['config']['pageData'] = body
            if changed == 'truncated': document['config']['pageData'] = document['config']['pageData'][:-1]
            if changed == 'duplicate-url':
                document['config']['pageData'] = document['config']['pageData'].replace(
                    '"url":', '"url":"https://unknown.other.example/","url":', 1)
            if changed == 'non-json-number':
                document['config']['pageData'] = document['config']['pageData'].replace('"data": {}', '"data": NaN')
            with self.subTest(changed=changed), self.assertRaises(Invalid):
                extract_rows(self.recipe(), self.html(document))

    def test_json_identity_rejects_duplicate_fields_and_boolean_integer_substitution(self):
        recipe = {'format': 'json-service-urls', 'paths': [['api']],
                  'identity': [{'path': ['published'], 'equals': True}]}
        for text in ('{"published":1,"api":"https://api.vendor.example"}',
                     '{"published":false,"published":true,"api":"https://api.vendor.example"}'):
            with self.subTest(text=text), self.assertRaises(Invalid): extract_rows(recipe, text)

    def test_decode_paths_and_identity_modes_are_explicit_and_unambiguous(self):
        for value in (True, ['config'], [[]], [['config', '*']],
                      [['config', 'pageData'], ['config', 'pageData']]):
            with self.subTest(value=value), self.assertRaises(Invalid):
                extract_rows({**self.recipe(), 'decode-json': value}, self.html(self.document()))
        for bad in ({'equals': 'graphql', 'each-equals': 'graphql'}, {'each-keys': []}, {'unknown': True}):
            recipe = self.recipe()
            recipe['identity'][-1] = {'path': ['config', 'pageData', 'dataSources', '*'], **bad}
            with self.subTest(bad=bad), self.assertRaises(Invalid):
                extract_rows(recipe, self.html(self.document()))

    def config(self):
        recipe = self.recipe()
        entry = {'id': 'platform', 'mode': 'compiled', 'priority': 20, 'section': 'vendors',
                 'description': '共用平台', 'boundary': '已核实的产品共用 API',
                 'policy-hint': 'global', 'sources': [recipe['source']], 'extract': [recipe]}
        combined = {'id': 'platforms-all', 'mode': 'view', 'priority': 10, 'section': 'vendors',
                    'description': '共用平台合集', 'boundary': '替代细分', 'members': ['platform']}
        return {'schema-version': 2, 'entries': [combined, entry],
                'sections': [{'id': 'vendors', 'title': '共用平台'}],
                'critical': {'api.platform.example': ['platform']},
                'shared-negatives': ['storage.googleapis.com'],
                'source-inventories': [{'id': 'complete-page-records', 'source': recipe['source'],
                    'recipe': {key: value for key, value in recipe.items() if key != 'source'},
                    'owners': ['platform']}]}

    def test_source_inventory_must_decode_the_same_records_as_the_product(self):
        from loon_rules.generation import pipeline
        config = self.config()
        config['source-inventories'][0]['recipe'].pop('decode-json')
        with self.assertRaises(Invalid): pipeline.validate_declarations(config)

    def test_unprefilled_record_urls_reach_fine_aggregate_and_exports_and_bad_inputs_write_nothing(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline
        from loon_rules.exports import publish

        config = self.config()
        source = self.recipe()['source']
        records = [self.record()]
        inputs = {source: self.html(self.document(records))}
        with TemporaryDirectory() as tmp, patch.object(pipeline, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            (root / 'rules').mkdir()
            entries = pipeline.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'config/endpoint-contracts.json').write_text('[]')
            (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
            for entry in entries.values():
                (root / 'rules' / pipeline.rule_filename(entry)).write_text(pipeline.decorate(
                    entry, ['DOMAIN,api.platform.example', 'DOMAIN,feature.platform.example'], None, '2026-11-20T00:00:00Z'))
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                for host in ('first-unprefilled.other.example', 'second-unprefilled.other.example'):
                    records.append(self.record(host))
                    inputs[source] = self.html(self.document(records))
                    pipeline.run()
                    publish(root)
                    for stem in ('020-platform', '010-platforms-all'):
                        file = root / 'rules' / (stem + '.lsr')
                        self.assertIn('DOMAIN,' + host, file.read_text())
                        self.assertEqual(file.read_bytes(), file.with_suffix('.list').read_bytes())
                        for client in ('sing-box', 'v2ray', 'clash-classical'):
                            self.assertTrue(any(host in p.read_text() for p in (root / 'dist' / client).rglob('*') if p.is_file()))
                    self.assertEqual(pipeline.run(offline=True), 0)
                for changed in ('identity', 'role', 'shared-host', 'truncated-body'):
                    before = {p: p.read_bytes() for folder in ('rules', 'dist', 'data')
                              for p in (root / folder).rglob('*') if p.is_file()}
                    document = self.document(copy.deepcopy(records))
                    body = json.loads(document['config']['pageData'])
                    if changed == 'identity': document['config']['brand'] = 'Another product'
                    if changed == 'role': body['dataSources'][-1]['type'] = 'other-product'
                    if changed == 'shared-host': body['dataSources'][-1]['url'] = 'https://storage.googleapis.com/vendor/file'
                    document['config']['pageData'] = json.dumps(body)
                    if changed == 'truncated-body': document['config']['pageData'] = document['config']['pageData'][:-1]
                    inputs[source] = self.html(document)
                    with self.subTest(changed=changed), self.assertRaises(Invalid): pipeline.run()
                    self.assertEqual(before, {p: p.read_bytes() for folder in ('rules', 'dist', 'data')
                                             for p in (root / folder).rglob('*') if p.is_file()})
