"""Read exact public service addresses without importing whole vendor networks."""
import unittest

from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class ServiceAddresses(unittest.TestCase):
    def recipe(self):
        return {'format': 'service-address-table', 'section': 'standard',
                'columns': {'IPv4': 4, 'IPv6': 6}}

    def document(self, v4='1.1.1.1<br>1.0.0.1', v6='2606:4700:4700::1111<br>2606:4700:4700::1001'):
        return ('<h2 id="standard">Standard service</h2><table><tr><th>IPv4</th><th>IPv6</th></tr>'
                f'<tr><td>{v4}</td><td>{v6}</td></tr></table>'
                '<h2 id="families">Another product</h2><table><tr><td>1.1.1.2</td></tr></table>')

    def test_standard_service_uses_exact_addresses_and_never_resolves_a_domain_for_matching(self):
        self.assertEqual(extract_rows(self.recipe(), self.document()), {
            'IP-CIDR,1.1.1.1/32,no-resolve', 'IP-CIDR,1.0.0.1/32,no-resolve',
            'IP-CIDR6,2606:4700:4700::1111/128,no-resolve',
            'IP-CIDR6,2606:4700:4700::1001/128,no-resolve'})
        updated = extract_rows(self.recipe(), self.document(v4='1.1.1.1<br>1.0.0.1<br>8.8.8.8'))
        self.assertIn('IP-CIDR,8.8.8.8/32,no-resolve', updated)

    def test_missing_columns_wrong_family_private_addresses_and_cidrs_stop_the_update(self):
        documents = [self.document(v4='1.1.1.0/24'), self.document(v4='192.168.1.1'),
                     self.document(v4='2606:4700::1'), self.document(v6=''),
                     self.document().replace('<th>IPv6</th>', '<th>Other</th>')]
        for body in documents:
            with self.subTest(body=body[:100]), self.assertRaises(Invalid):
                extract_rows(self.recipe(), body)


class SectionNetworkBlocks(unittest.TestCase):
    def recipe(self):
        return {'format': 'section-network-blocks', 'section': 'inbound',
                'families': [4, 6], 'min-prefix': {'4': 16, '6': 24}}

    def document(self, additional=''):
        return (
            '<h2 id="inbound">Inbound addresses</h2>'
            '<h3>IPv4</h3><p><code>160.79.104.0/23</code></p>'
            '<h3>IPv6</h3><p><code>2607:6bc0::/48</code></p>' + additional +
            '<h2 id="outbound">Outbound addresses</h2>'
            '<p><code>160.79.104.0/21</code></p><p><code>153.61.208.0/20</code></p>'
            '<h2 id="retired">Retired addresses</h2><p><code>34.162.46.92/32</code></p>')

    def test_only_the_selected_direction_is_used_and_new_blocks_are_discovered(self):
        expected = {'IP-CIDR,160.79.104.0/23,no-resolve',
                    'IP-CIDR6,2607:6bc0::/48,no-resolve'}
        self.assertEqual(extract_rows(self.recipe(), self.document()), expected)
        updated = self.document('<p><code>153.61.224.0/22</code></p>')
        self.assertEqual(extract_rows(self.recipe(), updated),
                         expected | {'IP-CIDR,153.61.224.0/22,no-resolve'})

    def test_scripts_and_other_sections_do_not_supply_missing_addresses(self):
        body = self.document().replace('<p><code>2607:6bc0::/48</code></p>', '')
        body += '<script>"<h2 id=\"inbound\"><code>2607:6bc0::/48</code>"</script>'
        with self.assertRaises(Invalid):
            extract_rows(self.recipe(), body)

    def test_unscoped_broad_malformed_or_private_blocks_stop_generation(self):
        documents = [self.document().replace('id="inbound"', 'id="other"'),
                     self.document() + self.document(),
                     self.document('<p><code>0.0.0.0/0</code></p>'),
                     self.document('<p><code>192.168.1.0/24</code></p>'),
                     self.document('<p><code>160.79.104.1/23</code></p>'),
                     self.document('<p><code>160.79.104.1</code></p>')]
        for body in documents:
            with self.subTest(body=body), self.assertRaises(Invalid):
                extract_rows(self.recipe(), body)
