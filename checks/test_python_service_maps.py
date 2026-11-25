"""Follow a client family and its typed endpoint maps without executing the module."""
import json
import copy

from checks.source_fixtures import PublicSourceExamples, prepare_workspace
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class PythonServiceMaps(PublicSourceExamples):
    def recipe(self):
        return {'format': 'python-sdk-endpoints', 'source': 'https://source.vendor.example/client.py',
                'class-prefixes': ['Product'], 'fields': ['_SERVERS'], 'bare-hosts': True,
                'dictionary-host-fields': ['host', 'domain'], 'dictionary-required-fields': ['host'],
                'dictionary-metadata-fields': ['realm', 'country'], 'nullable-class-defaults': True}

    def source(self):
        return '''
class ProductBase:
    pass

class ProductGlobal(ProductBase):
    _SERVERS = None
    def select(self, country):
        if country == 'us':
            self._SERVERS = {'host': 'us.api.vendor.example', 'realm': 'product', 'country': country}
        else:
            self._SERVERS = {'host': 'eu.api.vendor.example', 'realm': 'product', 'country': country}

class ProductRegional(ProductBase):
    _SERVERS = {'host': 'region.api.vendor.example', 'domain': 'https://product.vendor.example/',
                'realm': 'product', 'country': 'RG'}

class Unrelated:
    _SERVERS = {'host': 'wrong.other.example', 'realm': 'other', 'country': 'OT'}
'''

    def test_all_family_branches_and_host_fields_are_read_without_adopting_unrelated_products(self):
        expected = {'DOMAIN,us.api.vendor.example', 'DOMAIN,eu.api.vendor.example',
                    'DOMAIN,region.api.vendor.example', 'DOMAIN,product.vendor.example'}
        self.assertEqual(extract_rows(self.recipe(), self.source()), expected)
        source = self.source() + '\nclass ProductNewRegion(ProductBase):\n    _SERVERS = {"host":"unprefilled.other-provider.example","realm":"product","country":"NR"}\n'
        self.assertEqual(extract_rows(self.recipe(), source), expected | {'DOMAIN,unprefilled.other-provider.example'})

    def test_dictionary_shape_dynamic_hosts_and_unresolved_class_defaults_stop_the_whole_read(self):
        for bad in (
            self.source().replace("'host': 'region.api.vendor.example'", "'host': choose_runtime_host()"),
            self.source().replace("'host': 'region.api.vendor.example'", "'host': None"),
            self.source().replace("'host': 'region.api.vendor.example'", "'host': '2001:db8::1'"),
            self.source().replace("'host': 'region.api.vendor.example'", "'host': '\\nhttps://region.api.vendor.example'"),
            self.source().replace("'realm': 'product', 'country': 'RG'", "'realm': 'product', 'country': 'RG', 'backupHost': 'unknown.other.example'"),
            self.source().replace("'host': 'region.api.vendor.example'", "'host': 'wrong.other.example', 'host': 'region.api.vendor.example'"),
            self.source().replace("'host': 'region.api.vendor.example', ", ''),
            self.source() + '\nclass ProductNoDefaults(ProductBase):\n    _SERVERS = None\n',
            self.source() + '\ndef factory():\n    class ProductNested:\n        _SERVERS = {"host":"nested.other.example"}\n',
            self.source() + '\nclass ProductRegional(ProductBase):\n    pass\n',
        ):
            with self.subTest(source=bad[-120:]), self.assertRaises(Invalid): extract_rows(self.recipe(), bad)

    def test_class_selectors_and_field_purposes_are_explicit(self):
        for changed in ({'class-prefixes': ['Missing']}, {'dictionary-host-fields': []},
                        {'dictionary-required-fields': ['unknown']}, {'dictionary-values': True},
                        {'nullable-class-defaults': 'true'}):
            with self.subTest(changed=changed), self.assertRaises(Invalid):
                extract_rows({**self.recipe(), **changed}, self.source())

    def test_nested_other_classes_and_local_names_do_not_become_the_product_configuration(self):
        source = self.source() + '''
class ProductFactory(ProductBase):
    def build(self):
        class UnrelatedNested:
            _SERVERS = {'host': 'nested.other.example', 'realm': 'other', 'country': 'OT'}
        return UnrelatedNested
'''
        self.assertEqual(extract_rows(self.recipe(), source), extract_rows(self.recipe(), self.source()))
        local = self.source() + '''
class ProductLocal(ProductBase):
    def configure(self):
        _SERVERS = {'host': 'unclassified-local.other.example', 'realm': 'other', 'country': 'OT'}
'''
        with self.assertRaises(Invalid): extract_rows(self.recipe(), local)
        ambiguous = self.source() + '''
class ProductClosure(ProductBase):
    def build(self):
        def configure(self):
            self._SERVERS = {'host': 'unknown-object.other.example', 'realm': 'other', 'country': 'OT'}
'''
        with self.assertRaises(Invalid): extract_rows(self.recipe(), ambiguous)

    def test_declared_metadata_cannot_hide_host_ip_or_asn_literals(self):
        for value in ('hidden.other.example', '192.0.2.1', '2001:db8::1',
                      '192.0.2.0/24', '2001:db8::/32', 'AS399358'):
            source = self.source().replace("'country': 'RG'", "'country': " + repr(value))
            with self.subTest(value=value), self.assertRaises(Invalid): extract_rows(self.recipe(), source)

    def test_unassigned_network_fields_cannot_hide_behind_an_existing_client_or_scope(self):
        for assignment in ('_OTHER_API = "https://us.api.vendor.example/another"',
                           '_OTHER_API = choose_runtime_server()',
                           '_OTHER_API: str',
                           '_RANGES = ["192.0.2.0/24", "2001:db8::/32"]',
                           '_ASNS = [399358]',
                           '_BACKUP = {"server": "new.other-provider.example"}'):
            source = self.source() + '\nclass ProductExtra(ProductBase):\n    ' + assignment + '\n'
            with self.subTest(assignment=assignment), self.assertRaises(Invalid):
                extract_rows(self.recipe(), source)

    def test_scalar_hosts_and_non_network_framework_fields_have_explicit_purposes(self):
        recipe = {**self.recipe(), 'scalar-host-fields': ['_BASE_API', '_DOMAIN'],
                  'non-network-fields': {
                      '_VALID_URL': {'kind': 'input-url-pattern', 'reason': '识别用户输入的链接'},
                      '_TESTS': {'kind': 'test-cases', 'reason': '提取器的用例数据'},
                  }}
        source = self.source() + '''
class ProductOtherRegion(ProductBase):
    _BASE_API = 'https://unprefilled.api.other.example/'
    _DOMAIN = 'https://unprefilled.site.other.example/'
    _VALID_URL = r'https?://(?:www\\.)?product\\.example/(.+)'
    _TESTS = [{'url': 'https://example-fixture.other.example/video'}]
    def fetch(self):
        return self.download(f'{self._BASE_API}/items')
'''
        expected = extract_rows(self.recipe(), self.source()) | {
            'DOMAIN,unprefilled.api.other.example', 'DOMAIN,unprefilled.site.other.example'}
        self.assertEqual(extract_rows(recipe, source), expected)
        with self.assertRaises(Invalid): extract_rows(self.recipe(), source)
        bad = copy.deepcopy(recipe)
        bad['non-network-fields']['_TESTS']['kind'] = 'unclassified'
        with self.assertRaises(Invalid): extract_rows(bad, source)
        with self.assertRaises(Invalid):
            extract_rows(recipe, source.replace("'https://unprefilled.api.other.example/'", 'find_runtime_server()'))

    def test_url_patterns_can_use_inherited_regex_but_templates_cannot_hide_a_new_authority(self):
        recipe = {**self.recipe(), 'scalar-host-fields': ['_BASE_API', '_DOMAIN'],
                  'non-network-fields': {
                      '_VALID_URL': {'kind': 'input-url-pattern', 'reason': '输入链接模式'},
                  }}
        source = self.source() + '''
class ProductRegion(ProductBase):
    _BASE_API = 'https://region.api.other.example'
    _DOMAIN = 'https://region.site.other.example/'
    _VALID_URL = r'https?://product\\.example/' + ProductBase._PATH_REGEX
    def fetch(self):
        return self.download(f'{self._BASE_API}/items')
'''
        expected = extract_rows(self.recipe(), self.source()) | {
            'DOMAIN,region.api.other.example', 'DOMAIN,region.site.other.example'}
        self.assertEqual(extract_rows(recipe, source), expected)
        for template in ("f'{self._BASE_API}.unclassified.example/items'",
                         "f'https://{self._DOMAIN}@unclassified.example/items'"):
            with self.subTest(template=template), self.assertRaises(Invalid):
                extract_rows(recipe, source.replace("f'{self._BASE_API}/items'", template))

    def config(self):
        recipe = self.recipe()
        child = {'id': 'product', 'mode': 'compiled', 'priority': 20, 'section': 'products',
                 'description': '产品', 'boundary': '客户端的产品家族与默认服务字段',
                 'policy-hint': 'global', 'sources': [recipe['source']], 'extract': [recipe]}
        combined = {'id': 'products-all', 'mode': 'view', 'priority': 10, 'section': 'products',
                    'description': '合集', 'boundary': '替代细分', 'members': ['product']}
        return {'schema-version': 2, 'entries': [combined, child], 'shared-negatives': [],
                'critical': {'us.api.vendor.example': ['product']},
                'sections': [{'id': 'products', 'title': '产品'}],
                'source-inventories': [{'id': 'complete-client-family', 'source': recipe['source'],
                    'recipe': {key: value for key, value in recipe.items() if key != 'source'}, 'owners': ['product']}]}

    def test_client_family_and_dictionary_fields_require_the_same_complete_inventory(self):
        from loon_rules.generation import pipeline
        for field in ('class-prefixes', 'dictionary-host-fields'):
            config = self.config()
            config['source-inventories'][0]['recipe'].pop(field)
            with self.subTest(field=field), self.assertRaises(Invalid): pipeline.validate_declarations(config)

    def test_new_family_members_reach_products_aggregates_and_exports_and_bad_maps_write_nothing(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline
        from loon_rules.exports import publish

        config = self.config()
        source_url = self.recipe()['source']
        document = self.source()
        inputs = {source_url: document}
        with TemporaryDirectory() as tmp, patch.object(pipeline, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            (root / 'rules').mkdir()
            entries = pipeline.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'config/endpoint-contracts.json').write_text('[]')
            (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
            for entry in entries.values():
                (root / 'rules' / pipeline.rule_filename(entry)).write_text(pipeline.decorate(
                    entry, ['DOMAIN,us.api.vendor.example', 'DOMAIN,eu.api.vendor.example',
                            'DOMAIN,region.api.vendor.example', 'DOMAIN,product.vendor.example'], None, '2026-11-20T00:00:00Z'))
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                for number, host in enumerate(('first-unprefilled.other.example', 'second-unprefilled.other.example')):
                    document += '\nclass ProductNew' + str(number) + '(ProductBase):\n    _SERVERS = {"host": "' + host + '", "realm": "product", "country": "NEW"}\n'
                    inputs[source_url] = document
                    pipeline.run()
                    publish(root)
                    for stem in ('020-product', '010-products-all'):
                        file = root / 'rules' / (stem + '.lsr')
                        self.assertIn('DOMAIN,' + host, file.read_text())
                        self.assertEqual(file.read_bytes(), file.with_suffix('.list').read_bytes())
                        for client in ('sing-box', 'v2ray', 'clash-classical'):
                            self.assertTrue(any(host in p.read_text() for p in (root / 'dist' / client).rglob('*') if p.is_file()))
                    self.assertEqual(pipeline.run(offline=True), 0)
                before = {p: p.read_bytes() for folder in ('rules', 'data', 'dist')
                          for p in (root / folder).rglob('*') if p.is_file()}
                for changed in (document.replace('"country": "NEW"', '"unknownHost": "unreviewed.other.example"'),
                                document + '\nclass ProductUnexpected(ProductBase):\n    _OTHER_API = "https://us.api.vendor.example/another"\n'):
                    inputs[source_url] = changed
                    with self.assertRaises(Invalid): pipeline.run()
                    self.assertEqual(before, {p: p.read_bytes() for folder in ('rules', 'data', 'dist')
                                             for p in (root / folder).rglob('*') if p.is_file()})
