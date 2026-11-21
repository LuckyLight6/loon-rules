import json

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class DocumentFields(PublicSourceExamples):
    def recipe(self,part='other'):
        return {'format':'json-document','body-path':['article','body'],
                'identity':[{'path':['article','id'],'equals':123}],
                'document':{'format':'product-domain-statements','paragraph-contains':['AI hosts:'],
                            'code-only':True,'value-after':'AI hosts:','annotation':'for China','part':part}}

    def document(self):
        body=('<p>A <code>*.vendor.example</code> rule misses AI hosts: '
              '<code>api.ai.vendor.example</code>, <code>api.models.other.example</code>, '
              'and <code>api.china.vendor.example</code> for China. '
              'Read <a href="https://docs.unrelated.example">docs.unrelated.example</a>.</p>')
        return json.dumps({'article':{'id':123,'body':body}})

    def test_json_fields_and_code_annotations_separate_endpoints_without_hostname_selectors(self):
        self.assertEqual(extract_rows(self.recipe(),self.document()),
                         {'DOMAIN,api.ai.vendor.example','DOMAIN,api.models.other.example'})
        self.assertEqual(extract_rows(self.recipe('annotated'),self.document()),{'DOMAIN,api.china.vendor.example'})
        changed=self.document().replace('api.models.other.example','new-api.new-provider.example')
        self.assertIn('DOMAIN,new-api.new-provider.example',extract_rows(self.recipe(),changed))

    def test_missing_identity_body_or_region_marker_cannot_silently_change_the_edition(self):
        for text in (self.document().replace('123','456'),json.dumps({'article':{'id':123,'body':None}}),
                     self.document().replace('for China','for a different edition')):
            with self.subTest(text=text[:100]),self.assertRaises(Invalid):extract_rows(self.recipe(),text)

    def test_json_html_tables_keep_role_fields_and_ignore_other_products(self):
        recipe={'format':'json-document','body-path':['content'],
                'document':{'format':'exclusive-purpose-table','headers':['Host','Used for','Needed for'],
                            'purposes':['Every app','Account licenses']}}
        table='<table><tr><th>Host</th><th>Used for</th><th>Needed for</th></tr>'
        table+='<tr><td>config.vendor.example</td><td>Configuration</td><td>Every app</td></tr>'
        table+='<tr><td>account.vendor.example</td><td>Login</td><td>Account licenses</td></tr>'
        table+='<tr><td>AI hosts</td><td>api.ai.vendor.example</td><td>AI</td></tr></table>'
        self.assertEqual(extract_rows(recipe,json.dumps({'content':table})),
                         {'DOMAIN,config.vendor.example','DOMAIN,account.vendor.example'})

    def test_inert_templates_and_scripts_cannot_supply_a_domain_code_block(self):
        recipe={'format':'section-code-domains','sections':['domains']}
        doc=('<h2 id="domains">Domains</h2><pre><code>api.vendor.example</code></pre>'
             '<template><code>hidden.other.example</code></template>'
             '<script><code>script.other.example</code></script>')
        self.assertEqual(extract_rows(recipe,doc),{'DOMAIN,api.vendor.example'})
