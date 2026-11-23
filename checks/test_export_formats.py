"""Check portable outputs at the matching and publication boundaries."""
from fnmatch import fnmatchcase
from itertools import product
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from loon_rules.rules import Invalid


class ExportFormats(unittest.TestCase):
    def exports(self):
        try:
            from loon_rules import exports
        except ImportError:
            self.fail('缺少从同一份规则生成客户端格式的入口')
        return exports

    def test_classical_conversion_preserves_glob_ranges_and_ip_options(self):
        formats = self.exports()
        result = formats.convert('clash-classical', [
            'DOMAIN-SUFFIX,product.example',
            'DOMAIN-WILDCARD,p[0-9][0-9]-quota.product.example',
            'IP-CIDR,169.254.0.0/16,no-resolve',
            'IP-CIDR6,fc00::/7',
            'IP-ASN,399358,no-resolve',
        ])
        self.assertEqual(result['payload'][0], 'DOMAIN-SUFFIX,product.example')
        self.assertEqual(result['payload'][2:], [
            'IP-CIDR,169.254.0.0/16,no-resolve',
            'IP-CIDR6,fc00::/7', 'IP-ASN,399358,no-resolve',
        ])
        expression = result['payload'][1].removeprefix('DOMAIN-REGEX,')
        for host, expected in [('p00-quota.product.example', True),
                               ('p99-quota.product.example', True),
                               ('p001-quota.product.example', False),
                               ('px1-quota.product.example', False),
                               ('p12-quota.product.example.evil', False)]:
            self.assertEqual(bool(re.search(expression, host)), expected, host)

    def test_portable_regex_matches_canonical_globs_without_re2_unsupported_operators(self):
        formats = self.exports()
        patterns = ['*.example', 'p[0-2]?*.example', '*a*b?.example',
                    '[ab-]x.example', 'api*.prod-?.example', '[.example']
        hosts = ['.'.join([''.join(chars), 'example'])
                 for size in range(5) for chars in product('ab01.-x', repeat=size)]
        hosts += ['api-a.prod-1.example', 'p2x.a.example', '[.example']
        for pattern in patterns:
            expression = formats.glob_regex(pattern)
            self.assertNotIn('(?>', expression)
            self.assertNotIn('(?=', expression)
            self.assertNotIn('\\Z', expression)
            for host in hosts:
                self.assertEqual(bool(re.search(expression, host)), fnmatchcase(host, pattern),
                                 (pattern, host))

    def test_literal_glob_metacharacters_do_not_broaden_star_question_only_outputs(self):
        formats = self.exports()
        expression = formats.glob_regex('[]a].example')
        self.assertTrue(re.search(expression, 'a.example'))
        self.assertTrue(re.search(expression, '].example'))
        self.assertFalse(re.search(expression, 'b.example'))
        self.assertEqual(formats.glob_regex('[]'), '(?i)^\\[\\]$')
        with self.assertRaises(formats.Unsupported):
            formats.convert('surfboard', ['DOMAIN-WILDCARD,[*a].example'])

    def test_egern_keeps_no_resolve_on_its_own_or_branch(self):
        formats = self.exports()
        result = formats.convert('egern', [
            'DOMAIN,router.example', 'IP-CIDR,192.168.0.0/16',
            'IP-CIDR,169.254.0.0/16,no-resolve',
            'IP-CIDR6,fe80::/10,no-resolve', 'IP-ASN,399358,no-resolve',
        ])
        self.assertEqual(result, {
            'domain_set': ['router.example'],
            'ip_cidr_set': ['192.168.0.0/16'],
            'or_set': [{'no_resolve': True, 'ip_cidr_set': ['169.254.0.0/16'],
                        'ip_cidr6_set': ['fe80::/10'], 'asn_set': ['AS399358']}],
        })

    def test_glob_classes_expand_exactly_for_star_question_only_clients(self):
        formats = self.exports()
        result = formats.convert('surfboard', [
            'DOMAIN-WILDCARD,p[0-2][0-1]-quota.example',
            'DOMAIN-WILDCARD,*.unchanged.example',
            'IP-CIDR,169.254.0.0/16,no-resolve',
        ])
        self.assertEqual(result, [
            'DOMAIN-WILDCARD,p00-quota.example', 'DOMAIN-WILDCARD,p01-quota.example',
            'DOMAIN-WILDCARD,p10-quota.example', 'DOMAIN-WILDCARD,p11-quota.example',
            'DOMAIN-WILDCARD,p20-quota.example', 'DOMAIN-WILDCARD,p21-quota.example',
            'DOMAIN-WILDCARD,*.unchanged.example',
            'IP-CIDR,169.254.0.0/16,no-resolve',
        ])

    def test_unsupported_semantics_block_the_entire_group_instead_of_dropping_rows(self):
        formats = self.exports()
        cases = [('sing-box', 'IP-ASN,399358,no-resolve'),
                 ('v2ray', 'IP-ASN,399358,no-resolve'),
                 ('surfboard', 'IP-ASN,399358,no-resolve'),
                 ('quantumult-x', 'IP-CIDR,169.254.0.0/16,no-resolve'),
                 ('sing-box', 'GEOIP,CN'),
                 ('sing-box', 'IP-CIDR,169.254.0.0/16,no-resolve'),
                 ('v2ray', 'IP-CIDR,169.254.0.0/16,no-resolve')]
        for target, row in cases:
            with self.subTest(target=target, row=row), self.assertRaises(formats.Unsupported):
                formats.convert(target, ['DOMAIN,product.example', row])
        with self.assertRaises(formats.Unsupported):
            formats.convert('clash-classical', ['DOMAIN,product.example,extended-matching'])
        with self.assertRaises(Invalid):
            formats.convert('clash-classical', ['DOMAIN,product.example,PRIVATE-POLICY'])

    def test_native_json_outputs_keep_domain_and_ip_alternatives_separate(self):
        formats = self.exports()
        rows = ['DOMAIN,api.product.example', 'DOMAIN-SUFFIX,product.example',
                'DOMAIN-WILDCARD,p[0-1]?.example']
        singbox = formats.convert('sing-box', rows)
        self.assertEqual(singbox['version'], 1)
        self.assertEqual(singbox['rules'][0]['domain'], ['api.product.example'])
        self.assertEqual(singbox['rules'][0]['domain_suffix'], ['product.example'])
        v2ray = formats.convert('v2ray', rows)
        self.assertEqual(v2ray['routing']['rules'][0]['domains'][:2],
                         ['full:api.product.example', 'domain:product.example'])
        self.assertEqual(v2ray['routing']['rules'][0]['outboundTag'], 'PROXY')
        self.assertNotIn('domainStrategy', v2ray['routing'])
        self.assertNotIn('ip', v2ray['routing']['rules'][0])

    def test_quantumult_filters_bind_policy_explicitly_without_adding_final(self):
        formats = self.exports()
        self.assertEqual(formats.convert('quantumult-x', [
            'DOMAIN,api.example', 'DOMAIN-SUFFIX,product.example',
            'DOMAIN-WILDCARD,p[0-1]?.example',
        ]), ['host,api.example,proxy', 'host-suffix,product.example,proxy',
             'host-wildcard,p0?.example,proxy', 'host-wildcard,p1?.example,proxy'])

    def test_new_source_rule_flows_to_all_formats_and_a_stale_copy_fails_check(self):
        formats = self.exports()
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'rules').mkdir()
            canonical = root / 'rules/1010-product.lsr'
            canonical.write_text('# name: product\n# updated-at: 2026-11-24T00:00:00Z\n'
                                 'DOMAIN,api.product.example\n')
            formats.publish(root)
            self.assertEqual(formats.publish(root, check=True), 0)
            canonical.write_text(canonical.read_text() + 'DOMAIN,new.product.example\n')
            with self.assertRaisesRegex(Invalid, '客户端'):
                formats.publish(root, check=True)
            formats.publish(root)
            self.assertEqual(json.loads((root / 'dist/sing-box/1010-product.json').read_text())
                             ['rules'][0]['domain'], ['api.product.example', 'new.product.example'])
            manifest = json.loads((root / 'dist/manifest.json').read_text())
            self.assertEqual(manifest['clients']['stash']['format'], 'clash-classical')
            self.assertEqual(manifest['clients']['mihomo']['format'], 'clash-classical')
            self.assertEqual(manifest['formats']['surge']['rules']['1010-product']['path'],
                             'rules/1010-product.lsr')

    def test_becoming_incompatible_stops_publication_and_keeps_the_working_subscription(self):
        formats = self.exports()
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'rules').mkdir()
            source = root / 'rules/1010-product.lsr'
            source.write_text('DOMAIN,api.product.example\n')
            formats.publish(root)
            before = {p: p.read_bytes() for p in (root / 'dist').rglob('*') if p.is_file()}
            source.write_text(source.read_text() + 'IP-ASN,399358,no-resolve\n')
            with self.assertRaisesRegex(Invalid, '已发布客户端订阅'):
                formats.publish(root)
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_expanded_native_metadata_reports_the_emitted_count_and_original_timestamps(self):
        formats = self.exports()
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'rules').mkdir()
            (root / 'rules/2090-product.lsr').write_text(
                '# description: 登录\n# created-at: 2020-01-01T00:00:00Z\n'
                '# updated-at: 2026-11-24T00:00:00Z\n# rule-count: 2\n'
                'DOMAIN-WILDCARD,p[0-1][0-1].example\nDOMAIN,api.example\n')
            formats.publish(root)
            output = (root / 'dist/surge-compatible/2090-product.list').read_text()
            self.assertIn('# rule-count: 5\n', output)
            self.assertIn('# canonical-rule-count: 2\n', output)
            manifest = json.loads((root / 'dist/manifest.json').read_text())
            item = manifest['formats']['sing-box']['rules']['2090-product']
            self.assertEqual(item['updated-at'], '2026-11-24T00:00:00Z')
            self.assertEqual(item['description'], '登录')

    def test_bad_canonical_input_preserves_every_published_file(self):
        formats = self.exports()
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'rules').mkdir()
            source = root / 'rules/1010-product.lsr'
            source.write_text('DOMAIN,api.product.example\n')
            formats.publish(root)
            before = {p.relative_to(root): p.read_bytes() for p in (root / 'dist').rglob('*') if p.is_file()}
            source.write_text(source.read_text() + 'NOT-A-RULE,private.example\n')
            with self.assertRaises(Invalid):
                formats.publish(root)
            self.assertEqual(before, {p.relative_to(root): p.read_bytes()
                                     for p in (root / 'dist').rglob('*') if p.is_file()})
