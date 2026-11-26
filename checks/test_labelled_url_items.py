"""Read the single endpoint URL in each item of an explicitly labelled regional list."""
from checks.source_fixtures import PublicSourceExamples
from loon_rules.sources.inputs import extract_rows
from loon_rules.rules import Invalid

class LabelledUrlItems(PublicSourceExamples):
    def test_new_regional_url_is_read_and_multiple_or_credential_urls_stop_the_list(self):
        recipe={'format':'purpose-domain-lists','labels':['Choose the endpoint for your region:'],
                'item-address':'single-url','require-complete':True}
        page='<p>Choose the endpoint for your region:</p><ul><li>For US, https://api.vendor.example/v1</li><li>For a new region, https://next.unlisted.example/v1</li></ul>'
        self.assertEqual(extract_rows(recipe,page),{'DOMAIN,api.vendor.example','DOMAIN,next.unlisted.example'})
        for value in ['https://one.example/ https://two.example/','https://user@api.vendor.example/',
                      'https://api.vendor.example/?token=private','http://api.vendor.example/','not-an-endpoint']:
            with self.subTest(value=value),self.assertRaises(Invalid):
                extract_rows(recipe,page.replace('https://next.unlisted.example/v1',value))

    def test_mixed_schemes_and_invalid_ports_cannot_hide_a_second_or_bad_endpoint(self):
        recipe={'format':'purpose-domain-lists','labels':['Choose the endpoint for your region:'],
                'item-address':'single-url','require-complete':True}
        def page(value):return '<p>Choose the endpoint for your region:</p><ul><li>For a region, '+value+'</li></ul>'
        for value in ['https://api.vendor.example/ WSS://new.unlisted.example/v1',
                      'https://api.vendor.example/ ftp://new.unlisted.example/v1',
                      'https://api.vendor.example/ mailto:next@vendor.example',
                      'https://api.vendor.example:abc/v1','https://api.vendor.example:999999/v1',
                      'https://api.vendor.example:0/v1']:
            with self.subTest(value=value),self.assertRaises(Invalid):extract_rows(recipe,page(value))
        for value in ['WSS://NEW.UNLISTED.EXAMPLE/v1','HTTPS://NEW.UNLISTED.EXAMPLE:443/v1']:
            self.assertEqual(extract_rows(recipe,page(value)),{'DOMAIN,new.unlisted.example'})
