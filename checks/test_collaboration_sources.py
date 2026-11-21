from checks.source_fixtures import prepare_workspace
from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class CollaborationSources(PublicSourceExamples):
    def test_owned_domain_sections_keep_products_separate_and_ignore_partner_tables(self):
        recipe={'format':'purpose-domain-table','sections':['owned','government'],
                'headers':['Domain','Purpose'],'domain-scope':'domain-and-subdomains'}
        def table(rows):
            return '<table>'+''.join('<tr>'+''.join('<td>'+c+'</td>' for c in row)+'</tr>' for row in rows)+'</table>'
        doc=('<h2>Domain names</h2><h3 id="owned">Vendor domains</h3>'+table([
                recipe['headers'],['*.vendor.example','Shared services'],
                ['<p>app.other.example</p><p>www.other.example</p>','Related app'],
                ['*.repo.vendor.example','Repository service']])+ '<h3 id="government">Government</h3>'+table([
                recipe['headers'],['*.vendor-government.example','Government service']])+
             '<h3 id="partners">Partner domains</h3>'+table([
                recipe['headers'],['*.shared.example','Shared services']]))
        self.assertEqual(extract_rows(recipe,doc),{
            'DOMAIN-SUFFIX,vendor.example','DOMAIN-SUFFIX,app.other.example','DOMAIN-SUFFIX,www.other.example',
            'DOMAIN-SUFFIX,repo.vendor.example','DOMAIN-SUFFIX,vendor-government.example'})
        self.assertEqual(extract_rows({**recipe,'purpose-prefixes':['Repository']},doc),
                         {'DOMAIN-SUFFIX,repo.vendor.example'})
        doc=doc.replace('</table>','<tr><td>*.new-app.example</td><td>New vendor service</td></tr></table>',1)
        self.assertIn('DOMAIN-SUFFIX,new-app.example',extract_rows(recipe,doc))

    def test_domain_table_requires_each_owned_section_and_the_declared_columns(self):
        recipe={'format':'purpose-domain-table','sections':['owned'],'headers':['Domain','Purpose'],'domain-scope':'domain-and-subdomains'}
        for body in ('<h3 id="wrong">Domains</h3><table><tr><td>Domain</td><td>Purpose</td></tr><tr><td>*.vendor.example</td><td>App</td></tr></table>',
                     '<h3 id="owned">Domains</h3><table><tr><td>Domain</td><td>Description</td><td>Purpose</td></tr><tr><td>*.shared.example</td><td>CDN</td><td>App</td></tr></table>'):
            with self.assertRaises(Invalid):extract_rows(recipe,body)

    def test_nested_network_list_reads_only_domains_in_the_selected_instruction(self):
        recipe={'format':'nested-purpose-domains','parent-contains':'support the connection'}
        doc=('<ol><li>For login see unrelated.example<ul><li>auth.other.example</li></ul></li>'
             '<li>Please support the connection<ul><li>wss.vendor.example</li><li>*.new-socket.example</li></ul>'
             'Read ordinary-links.example for more.</li></ol><script><li>support the connection<ul><li>bad.example</li></ul></li></script>')
        self.assertEqual(extract_rows(recipe,doc),{'DOMAIN,wss.vendor.example','DOMAIN-WILDCARD,*.new-socket.example'})
        for bad in (doc.replace('support the connection','something else'),doc.replace('wss.vendor.example','127.0.0.1')):
            with self.assertRaises(Invalid):extract_rows(recipe,bad)

    def test_inline_network_fields_follow_the_instruction_without_collecting_plain_links(self):
        recipe={'format':'nested-purpose-domains','parent-contains':'support the connection'}
        doc=('<li><code>auth.other.example</code> For this client, support the connection:'
             '<br><code>wss.vendor.example</code><br><code>*.new-socket.example</code>'
             'More at ordinary-links.example</li>')
        self.assertEqual(extract_rows(recipe,doc),{'DOMAIN,wss.vendor.example','DOMAIN-WILDCARD,*.new-socket.example'})

    def test_plain_domain_fields_after_a_declared_label_cannot_silently_include_prose(self):
        recipe={'format':'nested-purpose-domains','parent-contains':'Support this connection',
                'value-after':'Required domains:'}
        doc='<li>Support this connection. Required domains: one.vendor.example *.socket.other.example</li>'
        self.assertEqual(extract_rows(recipe,doc),{'DOMAIN,one.vendor.example','DOMAIN-WILDCARD,*.socket.other.example'})
        for invalid in (doc.replace('Required domains:','Ordinary information:'),
                        doc.replace('</li>',' More at help.other.example</li>')):
            with self.assertRaises(Invalid):extract_rows(recipe,invalid)

    def test_labelled_server_pairs_preserve_api_hosts_and_expand_only_the_same_provider_root(self):
        recipe={'format':'labelled-url-pairs','source':'https://developer.vendor.example/rest',
                'purpose-prefixes':['Production server','Sandbox server'],'required-prefixes':['Production server'],
                'scope':'source-root'}
        doc=('<div><code>https://api.vendor.example</code><p>Production server</p></div>'
             '<div><code>wss://sandbox.vendor.example</code><p>Sandbox server</p></div>'
             '<div><code>https://api.external-provider.example</code><p>Production server</p></div>'
             '<div><code>https://wrong.example</code><p>Authentication provider</p></div>'
             '<script><div><code>https://bad.example</code><p>Production server</p></div></script>')
        self.assertEqual(extract_rows(recipe,doc),{'DOMAIN-SUFFIX,vendor.example','DOMAIN,api.external-provider.example'})
        self.assertEqual(extract_rows({**recipe,'scope':'exact'},doc),{
            'DOMAIN,api.vendor.example','DOMAIN,sandbox.vendor.example','DOMAIN,api.external-provider.example'})
        for bad in (doc.replace('Production server','Other use'),doc.replace('https://api.vendor.example','https://127.0.0.1')):
            with self.assertRaises(Invalid):extract_rows(recipe,bad)

    def test_server_roles_must_belong_to_the_same_parent_as_the_url(self):
        recipe={'format':'labelled-url-pairs','source':'https://developer.vendor.example/rest',
                'purpose-prefixes':['Production server'],'scope':'exact'}
        with self.assertRaises(Invalid):
            extract_rows(recipe,'<div><code>https://wrong.example</code></div><div><p>Production server</p></div>')

    def test_new_product_domains_leave_the_shared_platform_without_repeating_exclusion_lists(self):
        from contextlib import redirect_stdout
        from io import StringIO
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        source='https://support.vendor.example/domains'
        recipe={'format':'purpose-domain-table','source':source,'sections':['owned'],
                'headers':['Domain','Purpose'],'domain-scope':'domain-and-subdomains'}
        repo={'id':'repository','mode':'compiled','priority':20,'section':'development','description':'代码托管',
              'boundary':'专用服务','sources':[source],'extract':[{**recipe,'purpose-prefixes':['Repository']} ]}
        shared={'id':'shared-cloud','mode':'compiled','priority':30,'section':'development','description':'共用平台',
                'boundary':'其余自营云服务','sources':[source],'domain-remainder':True,'extract':[recipe]}
        cfg={'schema-version':2,'entries':[repo,shared],'critical':{'app.common.example':['shared-cloud']},
             'shared-negatives':[],'sections':[{'id':'development','title':'开发'}]}
        def document(extra=''):
            return ('<h3 id="owned">Vendor domains</h3><table><tr><td>Domain</td><td>Purpose</td></tr>'
                    '<tr><td>*.repo.vendor.example</td><td>Repository</td></tr>'
                    '<tr><td>*.common.example</td><td>Shared platform</td></tr>'+extra+'</table>'
                    '<h3 id="partner">Partners</h3><table><tr><td>Domain</td><td>Purpose</td></tr>'
                    '<tr><td>*.cloud.other.example</td><td>Repository</td></tr></table>')
        urls={source:document()}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(cfg)
            (root/'config/catalog.json').write_text(json.dumps(cfg));(root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,entries))
            for e,rows in [(repo,['DOMAIN-SUFFIX,repo.vendor.example']),(shared,['DOMAIN-SUFFIX,common.example'])]:
                (root/'rules'/lib.rule_filename(e)).write_text(lib.decorate(e,rows,None,'2026-11-20T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=urls.__getitem__):
                lib.run()
                urls[source]=document('<tr><td>*.unlisted-repo.example</td><td>Repository</td></tr>')
                lib.run();lib.run()
            data={e['id']:lib.rules.read_rules((root/'rules'/lib.rule_filename(e)).read_text()) for e in [repo,shared]}
            self.assertEqual(lib.ordered_route('api.unlisted-repo.example',['repository','shared-cloud'],data),'repository')
            self.assertNotIn('DOMAIN-SUFFIX,unlisted-repo.example',data['shared-cloud'])
            self.assertIsNone(lib.ordered_route('api.cloud.other.example',['repository','shared-cloud'],data))
            self.assertEqual(lib.run(offline=True),0)
