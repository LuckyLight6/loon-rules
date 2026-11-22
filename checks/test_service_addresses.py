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
