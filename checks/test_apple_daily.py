"""Exercise split Apple routing and mutually exclusive subscription bundles."""
import json
import unittest

from loon_rules import rules
from loon_rules.generation import ordering, pipeline
from loon_rules.generation.membership import merge_view
from loon_rules.plugins import scoped_dns


class BundleChoices(unittest.TestCase):
    def fixture(self):
        config = {'detailed': ['account', 'video'], 'general': ['general'],
                  'views': ['whole-all', 'overseas-all', 'direct-all'], 'optional': [],
                  'critical': {'login.vendor.example': ['account'],
                               'video.vendor.example': ['video'],
                               'other.vendor.example': ['general']}}
        entries = {
            'whole-all': {'priority': 2000, 'members': ['account', 'video']},
            'overseas-all': {'priority': 2005, 'members': ['video']},
            'account': {'priority': 2010},
            'video': {'priority': 2190},
            'general': {'priority': 2340, 'fallback': True},
            'direct-all': {'priority': 2350, 'members': ['account', 'general'], 'fallback': True},
        }
        data = {'account': ['DOMAIN,login.vendor.example'],
                'video': ['DOMAIN,video.vendor.example'],
                'general': ['DOMAIN-SUFFIX,vendor.example']}
        for key in config['views']:
            data[key] = merge_view(entries[key], data)
        return config, entries, data

    def test_selecting_overlapping_bundles_reports_the_conflicting_member(self):
        config, entries, data = self.fixture()
        with self.assertRaisesRegex(rules.Invalid, 'account'):
            ordering.route_order(config, entries, ['whole-all', 'direct-all'])

    def test_combination_check_covers_five_valid_choices_instead_of_stacking_alternatives(self):
        config, entries, data = self.fixture()
        try:
            count = pipeline.verify_combinations(config, entries, data)
        except rules.Invalid as error:
            self.fail('互斥合集应分别校验，不能当作同时订阅：' + str(error))
        self.assertEqual(count, 5)

    def test_disjoint_bundles_preserve_specific_routes_before_a_parent_fallback(self):
        config, entries, data = self.fixture()
        order = ordering.route_order(config, entries, ['overseas-all', 'direct-all'])
        self.assertEqual(ordering.ordered_route('video.vendor.example', order, data), 'overseas-all')
        self.assertEqual(ordering.ordered_route('login.vendor.example', order, data), 'direct-all')
        self.assertEqual(ordering.ordered_route('other.vendor.example', order, data), 'direct-all')


class AppleDailyRouting(unittest.TestCase):
    def test_daily_apple_bundles_keep_cloud_account_and_system_direct_and_overseas_features_separate(self):
        config = json.loads((pipeline.ROOT / 'config/catalog.json').read_text())
        entries = pipeline.validate_declarations(config)
        chosen = ['apple-overseas-all', 'apple-direct-all']
        self.assertTrue(set(chosen) <= set(entries), '缺少日常 Apple 直连与海外功能合集')
        data = {}
        for entry in config['entries']:
            path = pipeline.ROOT / 'rules' / pipeline.rule_filename(entry)
            if path.is_file():
                data[entry['id']] = rules.read_rules(path.read_text())
        for key in chosen:
            data[key] = merge_view(entries[key], data)
        expected = {
            'account.apple.com': 'apple-direct-all',
            'gsa.apple.com': 'apple-direct-all',
            'appleid.cdn-apple.com': 'apple-direct-all',
            'gateway.icloud.com': 'apple-direct-all',
            'data.icloud-content.com': 'apple-direct-all',
            'guzzoni.apple.com': 'apple-direct-all',
            'ocsp2.apple.com': 'apple-direct-all',
            'www.apple.com': 'apple-direct-all',
            'news.apple.com': 'apple-overseas-all',
            'tv.apple.com': 'apple-overseas-all',
            'mask-api.icloud.com': 'apple-overseas-all',
            'cp4.cloudflare.com': 'apple-overseas-all',
        }
        order = ordering.route_order(config, entries, chosen)
        for host, owner in expected.items():
            with self.subTest(host=host):
                self.assertEqual(ordering.ordered_route(host, order, data), owner)
        self.assertNotIn('apple-push-connection', entries['apple-direct-all']['members'])
        self.assertNotIn('apple-push-connection', entries['apple-overseas-all']['members'])
        self.assertIn('apple-push-connection', order)

    def test_direct_apple_dns_follows_local_encrypted_resolution_while_pcc_keeps_its_resolver(self):
        config = json.loads((pipeline.ROOT / 'config/catalog.json').read_text())
        content = scoped_dns.build(config)
        mappings = dict(line.split(' = server:', 1) for line in content.splitlines()
                        if ' = server:' in line)
        self.assertEqual(mappings.get('account.apple.com'), 'https://223.5.5.5/dns-query')
        self.assertEqual(mappings.get('gsa.apple.com'), 'https://223.5.5.5/dns-query')
        self.assertEqual(mappings.get('*.icloud-content.com'), 'https://223.5.5.5/dns-query')
        self.assertEqual(mappings.get('cp4.cloudflare.com'), 'https://1.1.1.1/dns-query')
