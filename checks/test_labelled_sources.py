from checks.source_fixtures import prepare_workspace
from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class LabelledSources(PublicSourceExamples):
    def recipe(self):
        return {'format':'purpose-domain-lists','labels':['Product owned domains:']}

    def test_layout_wrappers_do_not_separate_a_label_from_its_domain_list(self):
        document=('<div><p><strong>Product owned domains:</strong></p></div>'
                  '<div><ul><li><div><p>api.vendor.example</p></div></li>'
                  '<li><p>*.assets.vendor.example</p></li></ul></div>')
        self.assertEqual(extract_rows(self.recipe(),document),
                         {'DOMAIN,api.vendor.example','DOMAIN-WILDCARD,*.assets.vendor.example'})
        changed=document.replace('api.vendor.example','new-api.other-provider.example')
        self.assertIn('DOMAIN,new-api.other-provider.example',extract_rows(self.recipe(),changed))

    def test_visible_intervening_content_cancels_the_pending_purpose(self):
        for content in ('<h2>Another product</h2>','<p>Other domains:</p>','Unrelated service:'):
            document='<p>Product owned domains:</p><div>'+content+'<ul><li>other.vendor.example</li></ul></div>'
            with self.subTest(content=content),self.assertRaises(Invalid):extract_rows(self.recipe(),document)

    def test_inert_lists_are_ignored_and_nested_purposes_are_rejected(self):
        real='<p>Product owned domains:</p><div><ul><li>api.vendor.example</li></ul></div>'
        hidden='<template><p>Product owned domains:</p><ul><li>hidden.other.example</li></ul></template>'
        self.assertEqual(extract_rows(self.recipe(),hidden+real),{'DOMAIN,api.vendor.example'})
        nested=real.replace('api.vendor.example','api.vendor.example<ul><li>Other product: other.vendor.example</li></ul>')
        with self.assertRaises(Invalid):extract_rows(self.recipe(),nested)

    def test_domain_fields_reject_addresses_and_do_not_claim_shared_hosting_or_request_hosts(self):
        document=('<p>Product owned domains:</p><ul><li>api.vendor.example</li>'
                  '<li>*.github.io</li><li>github.io</li><li>storage.shared.example</li></ul>')
        self.assertEqual(extract_rows(self.recipe(),document,shared_hosts={'storage.shared.example'}),
                         {'DOMAIN,api.vendor.example'})
        for value in ('127.0.0.1','api.internal'):
            with self.subTest(value=value),self.assertRaises(Invalid):
                extract_rows(self.recipe(),document.replace('api.vendor.example',value))

    def test_declared_nested_subdomains_preserve_parent_and_following_items(self):
        recipe={**self.recipe(),'nested-subdomain-labels':['These subdomains are also used:']}
        document=('<p>Product owned domains:</p><ul><li>api.vendor.example: API requests. '
                  'These subdomains are also used:<ul><li>agent.api.vendor.example</li>'
                  '<li>agent.eu.api.vendor.example</li></ul></li><li>after.other-provider.example</li></ul>')
        self.assertEqual(extract_rows(recipe,document),{'DOMAIN,api.vendor.example','DOMAIN,agent.api.vendor.example',
                         'DOMAIN,agent.eu.api.vendor.example','DOMAIN,after.other-provider.example'})
        for text in (document.replace('These subdomains are also used:','Another product:'),
                     document.replace('agent.api.vendor.example','unrelated.other-provider.example')):
            with self.subTest(text=text[:100]),self.assertRaises(Invalid):extract_rows(recipe,text)

    def test_plain_product_references_can_opt_in_to_http_without_changing_api_url_readers(self):
        recipe={'format':'product-domain-statements','paragraph-contains':['installation','Product client'],
                'reference-schemes':['https','http']}
        document='<p>Installation of the Product client (http://new-product.example) may be required.</p>'
        self.assertEqual(extract_rows(recipe,document),{'DOMAIN-SUFFIX,new-product.example'})
        default={k:v for k,v in recipe.items() if k!='reference-schemes'}
        with self.assertRaises(Invalid):extract_rows(default,document)
        with self.assertRaises(Invalid):extract_rows({**recipe,'reference-schemes':['ftp']},document)

    def test_item_purposes_select_only_the_named_role_and_fail_if_it_disappears(self):
        recipe={**self.recipe(),'item-purpose-prefixes':['Shared sign-in']}
        document=('<p>Product owned domains:</p><ul><li>api.vendor.example: API requests</li>'
                  '<li>accounts.identity-provider.example, login.identity-provider.example: Shared sign-in page</li>'
                  '<li>logs.vendor.example: Usage statistics</li></ul>')
        self.assertEqual(extract_rows(recipe,document),{'DOMAIN,accounts.identity-provider.example',
                         'DOMAIN,login.identity-provider.example'})
        with self.assertRaises(Invalid):extract_rows(recipe,document.replace('Shared sign-in page','Usage statistics'))

    def test_parenthesized_purposes_select_the_declared_namespace_without_name_filters(self):
        recipe={**self.recipe(),'item-purpose-style':'parentheses',
                'item-purpose-contains':['serves user-generated content']}
        document=('<p>Product owned domains:</p><ul>'
                  '<li>*.accounts.vendor.example (shared login)</li>'
                  '<li>*.content.other-provider.example (covers auth; serves user-generated content)</li></ul>')
        self.assertEqual(extract_rows(recipe,document),{'DOMAIN-WILDCARD,*.content.other-provider.example'})
        changed=document.replace('content.other-provider.example','files.new-provider.example')
        self.assertEqual(extract_rows(recipe,changed),{'DOMAIN-WILDCARD,*.files.new-provider.example'})
        for bad in (document.replace('serves user-generated content','Usage statistics'),
                    document.replace('content)</li>','content</li>')):
            with self.subTest(bad=bad[-100:]),self.assertRaises(Invalid):extract_rows(recipe,bad)

    def test_selector_type_errors_cannot_silently_expand_the_purpose(self):
        document=('<p>Product owned domains:</p><ul><li>api.vendor.example: API requests</li>'
                  '<li>login.identity-provider.example: Shared sign-in</li></ul>')
        for change in ({'item-purpose-prefixes':'Shared sign-in'},{'item-purpose-prefixes':[]},
                       {'nested-subdomain-labels':'Additional subdomains:'},{'allow-identical-duplicates':'true'},
                       {'item-purpose-contains':'Shared sign-in'},{'item-purpose-contains':[]},
                       {'item-purpose-style':'guess'}):
            with self.subTest(change=change),self.assertRaises(Invalid):
                extract_rows({**self.recipe(),**change},document)

    def test_discovery_explains_an_existing_specific_owner_before_a_broader_provider(self):
        import copy
        from loon_rules.generation import discovery
        source='https://support.vendor.example/network'
        entries={'shared-auth':{'section':'ai'},'models':{'section':'ai'},
                 'editor':{'section':'ai','discovery':{'inputs':[{'source':source,'family':'vendor',
                           'authority':True,'recipe':self.recipe()}]}}}
        data={'shared-auth':['DOMAIN,login.identity-provider.example'],
              'models':['DOMAIN-SUFFIX,identity-provider.example'],'editor':['DOMAIN-SUFFIX,vendor.example']}
        document='<p>Product owned domains:</p><ul><li>login.identity-provider.example</li><li>api.vendor.example</li></ul>'
        proposals,report=discovery.propose(entries,data,{source:document},active=list(entries),shared=set())
        self.assertEqual(proposals['editor'],[])
        self.assertEqual(report['editor']['reserved-owners'],{'shared-auth':1})
        self.assertEqual(report['editor']['pending'],0)
        discovery.verify_report(entries,data,report)
        for owners in ({'unknown':1},{'shared-auth':2},{'shared-auth':0}):
            bad=copy.deepcopy(report);bad['editor']['reserved-owners']=owners
            with self.subTest(owners=owners),self.assertRaises(Invalid):discovery.verify_report(entries,data,bad)

    def test_exact_source_hosts_obey_the_same_wildcards_as_request_matching(self):
        from loon_rules import domains as domain_scope
        from loon_rules.rules import match_domain
        patterns=['DOMAIN-WILDCARD,p??-api.vendor.example','DOMAIN-WILDCARD,node[0-9].vendor.example',
                  'DOMAIN-WILDCARD,*.*.vendor.example']
        hosts=['p01-api.vendor.example','p123-api.vendor.example','node4.vendor.example',
               'node44.vendor.example','one.two.vendor.example','vendor.example']
        for pattern in patterns:
            for host in hosts:
                with self.subTest(pattern=pattern,host=host):
                    self.assertEqual(domain_scope.covers(pattern,'DOMAIN,'+host),match_domain(host,pattern))

    def test_scheduled_labelled_inventory_follows_new_hosts_and_keeps_the_last_complete_outputs(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import json
        from loon_rules.generation import pipeline as lib
        url='https://support.vendor.example/network'
        recipe={**self.recipe(),'source':url,'protect-from-reject':True}
        entry={'id':'product','mode':'compiled','priority':30,'section':'service','description':'产品',
               'boundary':'官方服务主机','sources':[url],'extract':[recipe],'inventory-refresh':True,
               'include':['DOMAIN-SUFFIX,vendor.example']}
        cfg={'schema-version':2,'entries':[entry],'critical':{},'shared-negatives':['storage.shared.example'],
             'sections':[{'id':'service','title':'服务'}]}
        def document(extra=''):
            return ('<div><p>Product owned domains:</p></div><div><ul><li>api.vendor.example</li>'+extra+
                    '</ul></div><p>Other service:</p><ul><li>wrong.other.example</li></ul>')
        urls={url:document()}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(cfg)
            (root/'config/catalog.json').write_text(json.dumps(cfg));(root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,entries));output=root/'rules'/lib.rule_filename(entry)
            output.write_text(lib.decorate(entry,entry['include'],None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=urls.__getitem__):
                lib.run()
                urls[url]=document('<li>new-api.other-provider.example</li><li>storage.shared.example</li>')
                lib.run();lib.run()
                self.assertIn('DOMAIN,new-api.other-provider.example',lib.rules.read_rules(output.read_text()))
                report=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(report['inventory-domain-cases'],2)
                self.assertNotIn('storage.shared.example',report['functional-hosts'])
                self.assertEqual(lib.run(offline=True),0)
                before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
                urls[url]=urls[url].replace('Product owned domains:','Another product:')
                with self.assertRaises(Invalid):lib.run()
                self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*') if p.is_file()})
