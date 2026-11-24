"""Messaging rules follow official scope changes without importing other clients."""
import json
from pathlib import Path

from checks.source_fixtures import PublicSourceExamples
from loon_rules.generation.compilation import compile_entry
from loon_rules.generation.membership import merge_view


class MessagingSources(PublicSourceExamples):
    def telegram(self):
        config = json.loads(Path('config/catalog.json').read_text())
        return next(entry for entry in config['entries'] if entry['id'] == 'telegram-messaging')

    def inputs(self, entry):
        inputs = {
            entry['projection'][0]['source']: 'DOMAIN-SUFFIX,telegram.org',
            entry['cidr-source']: '91.108.4.0/22\n',
            'https://core.telegram.org/bug-bounty': (
                '<p>Below is a list of Telegram domains which can be considered in scope.</p>'
                '<ul><li>new-resource.example, *.new-resource.example</li></ul>'
                '<p>Third-party applications are excluded.</p>'
                '<ul><li>unrelated-client.example</li></ul>'),
        }
        for recipe in entry.get('extract', []):
            if recipe['format'] == 'product-role-links':
                inputs[recipe['source']] = ('<a href="https://comments-tool.example/">Comments.App</a>'
                                            '<a href="https://other-product.example/">Other product</a>')
            if recipe['format'] == 'qt-host-predicate':
                inputs[recipe['source']] = (
                    'QStringList Links() { return {u"fragment.com"_q}; }\n'
                    'bool ' + recipe['function'] + '(const QUrl &url) {\n'
                    'const auto host = url.host().toLower();\n'
                    'return (host == u"article.example"_q) || (host == u"new-mirror.example"_q);\n}')
            if recipe['format'] != 'rdap-entity-autnums':
                continue
            identity=recipe['registrant-id']
            numbers={'ORG-TMI4-RIPE':[44907,59930,62014,62041], 'ORG-TMI5-RIPE':[211157]}[identity]
            inputs[recipe['source']] = json.dumps({
                'objectClassName':'entity','handle':identity,
                'vcardArray':['vcard',[['fn',{},'text',recipe['registrant-name']]]],
                'autnums':[{'objectClassName':'autnum','handle':'AS'+str(asn),
                            'startAutnum':asn,'endAutnum':asn,'status':['active']} for asn in numbers],
            })
        return inputs

    def test_new_official_domains_enter_the_product_and_social_bundle(self):
        entry = self.telegram()
        rows = compile_entry(entry, self.inputs(entry))
        self.assertIn('DOMAIN,new-resource.example', rows)
        self.assertIn('DOMAIN-WILDCARD,*.new-resource.example', rows)
        self.assertFalse(any('unrelated-client' in row for row in rows))
        bundle = merge_view({'members': [entry['id']]}, {entry['id']: rows})
        self.assertEqual(set(bundle), set(rows))

    def test_content_predicate_and_comments_do_not_import_an_unrelated_link_allowlist(self):
        entry = self.telegram()
        rows = compile_entry(entry, self.inputs(entry))
        self.assertIn('DOMAIN,new-mirror.example', rows)
        self.assertIn('DOMAIN-SUFFIX,comments-tool.example', rows)
        self.assertFalse(any('fragment.com' in row or 'other-product.example' in row for row in rows))

    def test_native_addresses_keep_no_resolve_and_registry_backed_asns(self):
        entry = self.telegram()
        rows = compile_entry(entry, self.inputs(entry))
        self.assertIn('IP-CIDR,91.108.4.0/22,no-resolve', rows)
        asns = {row for row in rows if row.startswith('IP-ASN,')}
        self.assertEqual(asns, {
            'IP-ASN,211157,no-resolve', 'IP-ASN,44907,no-resolve',
            'IP-ASN,59930,no-resolve', 'IP-ASN,62014,no-resolve',
            'IP-ASN,62041,no-resolve',
        })
