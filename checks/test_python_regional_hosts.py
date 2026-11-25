"""Read finite regional hosts and the request construction that actually uses them."""
import copy

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class PythonRegionalHosts(PublicSourceExamples):
    def recipe(self):
        return {'format': 'python-regional-hosts', 'source': 'https://source.vendor.example/client.py',
                'class': 'ProductIE', 'field': '_VALID_URL', 'origin-group': 'domain',
                'path-field': '_PATH_REGEX',
                'branch-group': 'product_region', 'function': '_real_extract',
                'pattern-groups': ['domain', 'product_region', 'other_product', 'id'],
                'other-branch-groups': ['other_product'],
                'origin-variable': 'domain', 'server-variable': 'host',
                'request-method': '_get_product_info', 'server-argument': 2,
                'non-network-fields': {'_TESTS': {'kind': 'test-cases', 'reason': '客户端测试样例'}}}

    def source(self):
        return r'''
class BaseIE:
    _PATH_REGEX = r'/(?P<id>[^/?#]+)'

class ProductIE:
    _VALID_URL = r'https?://(?P<domain>(?:www\.)?api\.(?P<product_region>us|eu)\.vendor\.example|(?P<other_product>other\.vendor\.example))/[^/]+' + BaseIE._PATH_REGEX
    _TESTS = [{'url': 'https://fixture.unrelated.example/video'}]
    def _real_extract(self, url):
        match = self._match_valid_url(url)
        display_id = match.group('id')
        domain = remove_start(match.group('domain'), 'www.')
        host = 'backend.' + domain if domain[0] == 'a' else 'shared.platform.example'
        return self._get_product_info(url, display_id, host, domain)
'''

    def test_all_selected_regions_and_optional_frontends_are_read_without_claiming_other_branches(self):
        expected = {'DOMAIN,' + prefix + region + '.vendor.example'
                    for prefix in ('api.', 'www.api.', 'backend.api.') for region in ('us', 'eu')}
        self.assertEqual(extract_rows(self.recipe(), self.source()), expected)
        changed = self.source().replace('us|eu', 'us|eu|new')
        self.assertEqual(extract_rows(self.recipe(), changed), expected | {
            'DOMAIN,api.new.vendor.example', 'DOMAIN,www.api.new.vendor.example',
            'DOMAIN,backend.api.new.vendor.example'})

    def test_unbounded_or_changed_input_scopes_cannot_be_read_as_partial_region_sets(self):
        for old, new in (('us|eu', '[a-z]+'), ('us|eu', r'\w+'),
                         ('?P<product_region>', '?P<other_region>'),
                         ('api\\.', '.*\\.'), ('https?://', '(?:https://wrong.example/|https://)'),
                         ('BaseIE._PATH_REGEX', 'BaseIE._UNKNOWN_PATH'),
                         ('BaseIE._PATH_REGEX', 'load_path()._PATH_REGEX'),
                         ("r'/(?P<id>[^/?#]+)'", "r'/(?P<id>[^/?#]+)|https://escaped.other.example/'"),
                         ('(?P<other_product>', '(?P<unreviewed_product>'),
                         ('))/[^/]+', ')|unclassified.vendor.example)/[^/]+'),
                         ('domain[0]', 'domain[-1]')):
            with self.subTest(change=(old, new)), self.assertRaises(Invalid):
                extract_rows(self.recipe(), self.source().replace(old, new))

    def test_changed_network_construction_or_unassigned_destinations_stop_the_whole_read(self):
        for old, new in (("'backend.' + domain", 'find_runtime_server()'),
                         ("'a' else", "'x' else"),
                         ('display_id =', 'self._fetch_other_service()\n        display_id ='),
                         ("host, domain)", "host, 'https://unassigned.other.example')"),
                         ('_TESTS =', '_OTHER_API = "https://unknown.other.example/"\n    _TESTS ='),
                         ('_TESTS =', '_OTHER_API = select_runtime_api()\n    _TESTS ='),
                         ('_TESTS =', '_ASNS = [399358]\n    _TESTS =')):
            with self.subTest(change=(old, new)), self.assertRaises(Invalid):
                extract_rows(self.recipe(), self.source().replace(old, new))
        with self.assertRaises(Invalid):
            extract_rows(self.recipe(), self.source(), shared_hosts=['backend.api.eu.vendor.example'])

    def test_mandatory_client_role_selectors_and_scope_are_not_guessed(self):
        for field in ('class', 'field', 'path-field', 'branch-group', 'origin-group', 'function',
                      'origin-variable', 'server-variable', 'request-method', 'server-argument',
                      'pattern-groups', 'other-branch-groups'):
            recipe = copy.deepcopy(self.recipe()); recipe.pop(field)
            with self.subTest(field=field), self.assertRaises(Invalid):
                extract_rows(recipe, self.source())

    def config(self):
        recipe = self.recipe()
        child = {'id': 'product', 'mode': 'compiled', 'priority': 20, 'section': 'products',
                 'description': '地区服务', 'boundary': '客户端产品分支的来源主机与实际 API',
                 'policy-hint': 'global', 'sources': [recipe['source']], 'extract': [recipe]}
        view = {'id': 'products-all', 'mode': 'view', 'priority': 10, 'section': 'products',
                'description': '合集', 'boundary': '替代细分', 'members': ['product']}
        return {'schema-version': 2, 'entries': [view, child], 'shared-negatives': [],
                'critical': {'api.us.vendor.example': ['product']},
                'sections': [{'id': 'products', 'title': '产品'}],
                'source-inventories': [{'id': 'complete-region-branch', 'source': recipe['source'],
                    'recipe': {k: v for k, v in recipe.items() if k != 'source'}, 'owners': ['product']}]}

    def test_regions_require_an_independent_inventory_for_the_same_client_branch_and_request_purpose(self):
        from loon_rules.generation import pipeline
        for field in ('branch-group', 'server-argument', 'path-field'):
            config = self.config(); config['source-inventories'][0]['recipe'].pop(field)
            with self.subTest(field=field), self.assertRaises(Invalid):
                pipeline.validate_declarations(config)

    def test_new_regions_reach_fine_aggregate_and_clients_and_invalid_sources_write_nothing(self):
        import json
        from contextlib import redirect_stdout
        from io import StringIO
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from checks.source_fixtures import prepare_workspace
        from loon_rules.generation import pipeline
        from loon_rules.exports import publish

        config = self.config(); recipe = self.recipe()
        inputs = {recipe['source']: self.source()}
        with TemporaryDirectory() as tmp, redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            with patch.object(pipeline, 'ROOT', root):
                (root / 'rules').mkdir()
                entries = pipeline.validate_declarations(config)
                (root / 'config/catalog.json').write_text(json.dumps(config))
                (root / 'config/endpoint-contracts.json').write_text('[]')
                (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
                for entry in entries.values():
                    (root / 'rules' / pipeline.rule_filename(entry)).write_text(pipeline.decorate(
                        entry, sorted(extract_rows(recipe, self.source())), None, '2026-11-20T00:00:00Z'))
                with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                    pipeline.run()
                    regions = []
                    for region in ('new0', 'new1'):
                        regions.append(region)
                        source = self.source().replace('us|eu', 'us|eu|' + '|'.join(regions))
                        inputs[recipe['source']] = source
                        pipeline.run(); publish(root)
                        for stem in ('020-product', '010-products-all'):
                            file = root / 'rules' / (stem + '.lsr')
                            self.assertEqual(file.read_bytes(), file.with_suffix('.list').read_bytes())
                            for host in ('api.' + region + '.vendor.example', 'backend.api.' + region + '.vendor.example'):
                                self.assertIn('DOMAIN,' + host, file.read_text())
                                for client in ('sing-box', 'v2ray', 'clash-classical'):
                                    self.assertTrue(any(host in p.read_text() for p in (root / 'dist' / client).rglob('*') if p.is_file()))
                    before = {p: p.read_bytes() for folder in ('rules', 'dist', 'data')
                              for p in (root / folder).rglob('*') if p.is_file()}
                    for changed in (source.replace('us|eu', '[a-z]+'),
                                    source.replace("'backend.' + domain", 'resolve_live_api()'),
                                    source.replace("host, domain)", "host, 'https://unassigned.other.example')")):
                        inputs[recipe['source']] = changed
                        with self.assertRaises(Invalid): pipeline.run()
                        self.assertEqual(before, {p: p.read_bytes() for folder in ('rules', 'dist', 'data')
                                                 for p in (root / folder).rglob('*') if p.is_file()})
