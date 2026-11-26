"""A documented public canonical flag does not permit unknown or credential-bearing queries."""
from checks.source_fixtures import PublicSourceExamples
from loon_rules.sources.inputs import extract_rows
from loon_rules.rules import Invalid

class SiteIdentityQueries(PublicSourceExamples):
    def test_only_the_explicit_public_query_and_its_value_are_allowed(self):
        recipe={'format':'site-identity','source':'https://vendor.example/','scope':'source-root','brand':'Vendor',
                'allowed-canonical-query':{'has_gdpr':'true'}}
        def body(query):return '<meta property="og:site_name" content="Vendor"><link rel="canonical" href="https://vendor.example/'+query+'">'
        self.assertEqual(extract_rows(recipe,body('?has_gdpr=true')),{'DOMAIN-SUFFIX,vendor.example'})
        self.assertEqual(extract_rows(recipe,body('')),{'DOMAIN-SUFFIX,vendor.example'})
        for query in ['?has_gdpr=false','?has_gdpr=true&has_gdpr=true','?has_gdpr=true&token=private','?redirect=https://other.example/']:
            with self.subTest(query=query),self.assertRaises(Invalid):extract_rows(recipe,body(query))
        strict={key:value for key,value in recipe.items() if key!='allowed-canonical-query'}
        with self.assertRaises(Invalid):extract_rows(strict,body('?has_gdpr=true'))

    def test_unexpected_query_identifies_the_source_without_printing_unknown_values(self):
        recipe={'format':'site-identity','source':'https://vendor.example/','scope':'source-root','brand':'Vendor',
                'allowed-canonical-query':{'has_gdpr':'true'}}
        body='<meta property="og:site_name" content="Vendor"><link rel="canonical" href="https://vendor.example/?has_gdpr=false&amp;token=private-sensitive-value">'
        with self.assertRaises(Invalid) as caught:extract_rows(recipe,body)
        message=str(caught.exception)
        self.assertIn('Vendor',message)
        self.assertIn('vendor.example',message)
        self.assertIn('has_gdpr=false',message)
        self.assertNotIn('private-sensitive-value',message)

    def test_regional_query_alternatives_are_exact_and_cannot_be_combined(self):
        recipe={'format':'site-identity','source':'https://vendor.example/','scope':'source-root','brand':'Vendor',
                'allowed-canonical-query':[{'has_gdpr':'true'},{'is_us':'true'}]}
        def body(query):return '<meta property="og:site_name" content="Vendor"><link rel="canonical" href="https://vendor.example/'+query+'">'
        for query in ('?has_gdpr=true','?is_us=true',''):
            try:rows=extract_rows(recipe,body(query))
            except Invalid as error:self.fail('已确认的完整地区参数组合应被接受：'+str(error))
            self.assertEqual(rows,{'DOMAIN-SUFFIX,vendor.example'})
        for query in ('?has_gdpr=false','?is_us=false','?has_gdpr=true&is_us=true',
                      '?is_us=true&is_us=true','?is_us=true&token=private','?other=true'):
            with self.subTest(query=query),self.assertRaises(Invalid):extract_rows(recipe,body(query))
        for alternatives in ([],[{'is_us':'true'},{'is_us':'true'}],[{'is_us':True}],['is_us=true']):
            with self.subTest(alternatives=alternatives),self.assertRaises(Invalid):
                extract_rows({**recipe,'allowed-canonical-query':alternatives},body('?is_us=true'))
