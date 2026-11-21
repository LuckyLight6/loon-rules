from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class ProductOrigins(PublicSourceExamples):
    def site(self,canonical='https://www.vendor.example',graph='https://vendor.example/pay'):
        return ('<meta property="og:title" content="Vendor: a way to pay">'
                '<link rel="canonical" href="'+canonical+'">'+
                ('<meta property="og:url" content="'+graph+'">' if graph else ''))

    def recipe(self):
        return {'format':'site-identity','source':'https://www.vendor.example/',
                'scope':'source-root','brand':'Vendor','brand-field':'og:title','brand-match':'word'}

    def test_source_canonical_and_optional_graph_agree_on_the_dedicated_product_root(self):
        self.assertEqual(extract_rows(self.recipe(),self.site()),{'DOMAIN-SUFFIX,vendor.example'})
        self.assertEqual(extract_rows(self.recipe(),self.site(graph=None)),{'DOMAIN-SUFFIX,vendor.example'})

    def test_origin_mode_rejects_other_roots_shared_hosting_and_duplicate_metadata(self):
        for recipe,body in [(self.recipe(),self.site(canonical='https://other.example')),
                            (self.recipe(),self.site(graph='https://other.example/pay')),
                            ({**self.recipe(),'source':'https://vendor.zendesk.com/'},
                             self.site(canonical='https://vendor.zendesk.com',graph=None)),
                            (self.recipe(),self.site()+self.site())]:
            with self.subTest(recipe=recipe),self.assertRaises(Invalid):extract_rows(recipe,body)

    def test_brand_tokens_do_not_match_a_substring_or_accept_conflicting_identity_fields(self):
        for body in (self.site().replace('Vendor: a way','UnrelatedVendor: a way'),
                     self.site()+'<meta property="og:title" content="Different company">'):
            with self.assertRaises(Invalid):extract_rows(self.recipe(),body)

    def test_default_identity_contract_keeps_requiring_both_url_fields_and_the_site_name(self):
        recipe={'format':'site-identity','brand':'Vendor'}
        body=('<meta property="og:site_name" content="Vendor">'
              '<link rel="canonical" href="https://vendor.example">'
              '<meta property="og:url" content="https://vendor.example">')
        self.assertEqual(extract_rows(recipe,body),{'DOMAIN-SUFFIX,vendor.example'})
        with self.assertRaises(Invalid):extract_rows(recipe,body.replace('<meta property="og:url" content="https://vendor.example">',''))

    def test_domain_blocks_are_scoped_to_each_required_section_and_never_import_addresses(self):
        recipe={'format':'section-code-domains','sections':['production','sandbox']}
        doc=('<h2 id="production">Production</h2><p>Required domains</p><pre><code>'
             'api.vendor.example\nassets.vendor.example</code></pre>'
             '<h2 id="addresses">Addresses</h2><pre><code>198.51.100.0/24</code></pre>'
             '<h2 id="sandbox">Sandbox</h2><pre><code>api.sandbox.vendor.example</code></pre>')
        self.assertEqual(extract_rows(recipe,doc),{'DOMAIN,api.vendor.example','DOMAIN,assets.vendor.example',
                                                 'DOMAIN,api.sandbox.vendor.example'})
        for bad in (doc.replace('id="sandbox"','id="elsewhere"'),doc.replace('assets.vendor.example','127.0.0.1'),
                    doc.replace('api.sandbox.vendor.example','Set api.other.example here')):
            with self.subTest(body=bad),self.assertRaises(Invalid):extract_rows(recipe,bad)
