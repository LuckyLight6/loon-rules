"""Selected endpoint fields must not silently discard an unresolved platform scope."""
import json
import plistlib
import copy

from checks.source_fixtures import PublicSourceExamples
from loon_rules import domains
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class SelectedSourceScopes(PublicSourceExamples):
    def setUp(self):
        super().setUp()
        domains.current().exact['githubusercontent.com'] = True
        domains.current().exact['azurewebsites.net'] = True

    def cases(self, hosts):
        yield ({'format': 'service-domain-groups', 'path': ['domains'], 'groups': ['website']},
               json.dumps({'domains': {'website': hosts}}))
        yield ({'format': 'json-service-urls', 'paths': [['servers', '*']]},
               json.dumps({'servers': ['https://' + host + '/' for host in hosts]}))
        yield ({'format': 'plist-service-fields', 'host-paths': [['servers', '*']],
                'identity': [{'path': ['vendor'], 'equals': 'Vendor'}]},
               plistlib.dumps({'vendor': 'Vendor', 'servers': hosts}).decode())
        yield ({'format': 'purpose-domain-table', 'sections': ['service'],
                'headers': ['Domain', 'Purpose'], 'purpose-prefixes': ['Product service']},
               '<h2 id="service">Service</h2><table><tr><td>Domain</td><td>Purpose</td></tr>'
               + ''.join('<tr><td>' + host + '</td><td>Product service</td></tr>' for host in hosts)
               + '</table>')

    def test_a_valid_host_cannot_hide_an_unhandled_private_platform_or_shared_hostname(self):
        for bad in ('github.io', '*.github.io', 'storage.googleapis.com'):
            for recipe, text in self.cases(['service.vendor.example', bad]):
                with self.subTest(format=recipe['format'], bad=bad), self.assertRaises(Invalid):
                    extract_rows(recipe, text, shared_hosts=['storage.googleapis.com'])

    def test_unprefilled_dedicated_names_are_still_read_without_a_root_whitelist(self):
        for recipe, text in self.cases(['service.vendor.example', 'brand-new.other-provider.example']):
            with self.subTest(format=recipe['format']):
                self.assertEqual(extract_rows(recipe, text), {
                    'DOMAIN,service.vendor.example', 'DOMAIN,brand-new.other-provider.example'})

    def test_a_verified_hosting_platform_is_explicit_and_can_be_split_from_the_code_product(self):
        recipe = {'format': 'service-domain-groups', 'path': ['domains'], 'groups': ['website'],
                  'platform-domains': ['github.io', 'githubusercontent.com']}
        document = {'domains': {'website': ['*.github.com', '*.github.io',
                                            '*.actions.githubusercontent.com', 'new-api.other.example']}}
        text = json.dumps(document)
        expected = {'DOMAIN-WILDCARD,*.github.com', 'DOMAIN-WILDCARD,*.github.io',
                    'DOMAIN-WILDCARD,*.actions.githubusercontent.com', 'DOMAIN,new-api.other.example'}
        self.assertEqual(extract_rows(recipe, text), expected)
        pages = {**recipe, 'only-platforms': ['github.io']}
        code = {**recipe, 'exclude-platforms': ['github.io']}
        self.assertEqual(extract_rows(pages, text), {'DOMAIN-WILDCARD,*.github.io'})
        self.assertEqual(extract_rows(code, text), expected - {'DOMAIN-WILDCARD,*.github.io'})
        # A different private platform must be read and rejected before the product filter.
        document['domains']['website'].append('*.azurewebsites.net')
        with self.assertRaises(Invalid): extract_rows(pages, json.dumps(document))

    def test_platform_permission_cannot_be_a_registry_suffix_or_unchecked_filter(self):
        base = {'format': 'service-domain-groups', 'path': ['domains'], 'groups': ['website'],
                'platform-domains': ['github.io']}
        text = json.dumps({'domains': {'website': ['*.github.io', 'api.vendor.example']}})
        for changed in ({'platform-domains': ['com']}, {'platform-domains': 'github.io'},
                        {'platform-domains': ['github.io', 'github.io']},
                        {'only-platforms': ['azurewebsites.net']},
                        {'only-platforms': ['github.io'], 'exclude-platforms': ['github.io']}):
            with self.subTest(changed=changed), self.assertRaises(Invalid):
                extract_rows({**base, **changed}, text)

    def test_company_service_metadata_can_describe_its_own_namespace_without_claiming_other_providers(self):
        recipe = {'source': 'https://api.vendor.example/meta', 'format': 'service-domain-groups',
                  'path': ['domains'], 'groups': ['website']}
        document = {'domains': {'website': ['*.vendor.example', 'vendor.example']}}
        shared = ['vendor.example', 'api.vendor.example', 'storage.googleapis.com']
        self.assertEqual(extract_rows(recipe, json.dumps(document), shared_hosts=shared), {
            'DOMAIN-WILDCARD,*.vendor.example', 'DOMAIN,vendor.example'})
        document['domains']['website'].append('storage.googleapis.com')
        with self.assertRaises(Invalid): extract_rows(recipe, json.dumps(document), shared_hosts=shared)

    def config(self):
        source = 'https://api.vendor.example/meta'
        whole = {'format': 'service-domain-groups', 'path': ['domains'],
                 'groups': ['website', 'packages', 'actions'],
                 'platform-domains': ['github.io', 'githubusercontent.com']}
        code = {'id': 'code', 'mode': 'compiled', 'priority': 20, 'section': 'development',
                'description': '开发平台', 'boundary': '代码与软件包，不含托管网站',
                'sources': [source], 'allowed-shared': ['githubusercontent.com'],
                'extract': [{**whole, 'source': source, 'exclude-platforms': ['github.io']}],
                'policy-hint': 'global', 'inventory-refresh': True}
        pages = {'id': 'pages', 'mode': 'compiled', 'priority': 30, 'section': 'development',
                 'description': '网站托管', 'boundary': '平台默认域名，不认领自定义域',
                 'sources': [source], 'allowed-shared': ['github.io'],
                 'extract': [{**whole, 'source': source, 'only-platforms': ['github.io']}],
                 'policy-hint': 'global'}
        combined = {'id': 'development-all', 'mode': 'view', 'priority': 10, 'section': 'development',
                    'description': '开发合集', 'boundary': '替代两项细分', 'members': ['code', 'pages']}
        return {'schema-version': 2, 'entries': [combined, code, pages],
                'shared-negatives': ['storage.googleapis.com'],
                'sections': [{'id': 'development', 'title': '开发'}],
                'critical': {'api.github.com': ['code'], 'sample.github.io': ['pages']},
                'source-inventories': [{'id': 'complete-service-fields', 'source': source,
                                         'owners': ['code', 'pages'], 'recipe': whole}]}

    def test_product_splits_require_the_complete_service_fields_before_platform_selection(self):
        from loon_rules.generation import pipeline
        config = self.config()
        for changed in ('missing', 'already-filtered', 'missing-owner'):
            broken = copy.deepcopy(config)
            if changed == 'missing': broken['source-inventories'] = []
            if changed == 'already-filtered':
                broken['source-inventories'][0]['recipe']['only-platforms'] = ['github.io']
            if changed == 'missing-owner': broken['source-inventories'][0]['owners'] = ['pages']
            with self.subTest(changed=changed), self.assertRaises(Invalid):
                pipeline.validate_declarations(broken)

    def test_complete_service_data_reaches_products_aggregate_exports_and_rejects_unknown_scopes(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from checks.source_fixtures import prepare_workspace
        from loon_rules.generation import pipeline
        from loon_rules.exports import publish
        from loon_rules.matching import RuleIndex

        config = self.config()
        source = config['entries'][1]['sources'][0]
        document = {'domains': {
            'website': ['*.github.com', '*.github.io', '*.githubusercontent.com'],
            'packages': ['initial.asset-provider.example'],
            'actions': ['results.actions.githubusercontent.com']}}
        inputs = {source: json.dumps(document)}
        with TemporaryDirectory() as tmp, patch.object(pipeline, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            (root / 'rules' / 'loon').mkdir(parents=True, exist_ok=True)
            (root / 'config/endpoint-contracts.json').write_text('[]')
            entries = pipeline.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
            rows = {'code': ['DOMAIN-WILDCARD,*.github.com', 'DOMAIN-WILDCARD,*.githubusercontent.com',
                             'DOMAIN,initial.asset-provider.example'],
                    'pages': ['DOMAIN-WILDCARD,*.github.io']}
            rows['development-all'] = rows['code'] + rows['pages']
            for key, entry in entries.items():
                (root / 'rules' / 'loon' / pipeline.rule_filename(entry)).write_text(
                    pipeline.decorate(entry, rows[key], None, '2026-11-20T00:00:00Z'))
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                for host in ('first-unprefilled.other.example', 'second-unprefilled.other.example'):
                    document['domains']['packages'].append(host)
                    inputs[source] = json.dumps(document)
                    pipeline.run()
                    publish(root)
                    for name in ('020-code', '010-development-all'):
                        file = root / 'rules' / 'loon' / (name + '.lsr')
                        self.assertIn('DOMAIN,' + host, file.read_text())
                        self.assertEqual(file.read_bytes(), (file.parent.with_name('surge') / file.with_suffix('.list').name).read_bytes())
                        for client in ('sing-box', 'v2ray', 'mihomo'):
                            self.assertTrue(any(host in p.read_text() for p in (root / 'rules' / client).rglob('*') if p.is_file()))
                    self.assertNotIn(host, (root / 'rules/loon/030-pages.lsr').read_text())
                    self.assertEqual(pipeline.run(offline=True), 0)
                bodies = {key: pipeline.rules.read_rules((root / 'rules' / 'loon' / pipeline.rule_filename(entry)).read_text())
                          for key, entry in entries.items()}
                index = RuleIndex(bodies, ['code', 'pages'])
                self.assertEqual(index.route('site.github.io', ['code', 'pages']), 'pages')
                self.assertEqual(index.route('raw.githubusercontent.com', ['code', 'pages']), 'code')
                accepted = copy.deepcopy(document)
                for bad in ('*.azurewebsites.net', 'storage.googleapis.com', '17.0.0.1'):
                    before = {p: p.read_bytes() for folder in ('rules', 'data', 'dist')
                              for p in (root / folder).rglob('*') if p.is_file()}
                    document = copy.deepcopy(accepted)
                    document['domains']['website'].append(bad)
                    inputs[source] = json.dumps(document)
                    with self.subTest(bad=bad), self.assertRaises(Invalid): pipeline.run()
                    self.assertEqual(before, {p: p.read_bytes() for folder in ('rules', 'data', 'dist')
                                             for p in (root / folder).rglob('*') if p.is_file()})
