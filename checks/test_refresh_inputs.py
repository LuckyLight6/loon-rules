from checks.source_fixtures import prepare_workspace
import unittest
from loon_rules.generation import pipeline as lib
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows
from checks.source_fixtures import PublicSourceExamples

class RefreshInputs(unittest.TestCase):
    def test_compaction_removes_only_hosts_covered_by_the_same_simple_wildcard(self):
        rows=['DOMAIN-WILDCARD,*.vendor.example','DOMAIN,vendor.example',
              'DOMAIN,auth.vendor.example','DOMAIN-SUFFIX,assets.vendor.example']
        self.assertEqual(lib.compact(rows),['DOMAIN-WILDCARD,*.vendor.example','DOMAIN,vendor.example'])

    def test_active_official_endpoints_do_not_start_a_community_withdrawal_timer(self):
        entry={'id':'company','mode':'managed','sources':['feed'],'kinds':['DOMAIN-SUFFIX','DOMAIN'],
               'flags':[],'official-hosts':True,'reconcile':'confirmed-withdrawals'}
        rows=['DOMAIN,service'+str(i)+'.vendor.example' for i in range(24)]
        auth='DOMAIN,accounts.vendor.example'
        result,state=lib.refresh_reviewed_feed(entry,rows+[auth],{'feed':'\n'.join(rows)},
            official=['accounts.vendor.example'],revision='published snapshot',epoch=100)
        self.assertIn(auth,result)
        self.assertNotIn('withdrawal-observation',state)

    def test_database_is_not_seeded_from_yesterdays_subscription(self):
        entry={'id':'files','include':['DOMAIN,keep.example']}
        self.assertEqual(lib.compile_entry(entry,{}),['DOMAIN,keep.example'])

    def test_equal_counts_do_not_hide_loss_of_one_whole_scope(self):
        before=['DOMAIN-SUFFIX,files.example','DOMAIN,a.example']
        with self.assertRaisesRegex(Invalid,'files.example'):
            lib.guard_coverage('files',before,['DOMAIN,one.files.example','DOMAIN,b.example'])
        lib.guard_coverage('files',['DOMAIN,one.files.example'],before)

    def test_published_apex_and_subdomain_wildcard_together_preserve_a_suffix_scope(self):
        before=['DOMAIN-SUFFIX,meetings.vendor.example']
        published=['DOMAIN,meetings.vendor.example','DOMAIN-WILDCARD,*.meetings.vendor.example']
        self.assertEqual(lib.uncovered_count(before,published),0)
        lib.guard_coverage('meetings',before,published)
        for partial in ([published[0]],[published[1]],
                        ['DOMAIN,meetings.vendor.example','DOMAIN-WILDCARD,*.other.vendor.example']):
            with self.subTest(partial=partial),self.assertRaises(Invalid):
                lib.guard_coverage('meetings',before,partial)

    def test_new_official_exact_host_needs_both_purpose_and_product(self):
        recipe={'source':'vendor','format':'host-table','sections':['service'],
                'select':[{'role':['account authentication'],'roots':['vendor.example']}]}
        text='<h2 id="service">Service</h2><table>'+''.join(
            f'<tr><td>{host}</td><td>443</td><td>TCP</td><td>OS</td><td>{role}</td></tr>'
            for host,role in [('new.vendor.example','Account authentication'),
                              ('tenant.shared.example','Account authentication'),
                              ('cdn.vendor.example','File downloads')])+'</table>'
        self.assertEqual(lib.compile_entry({'id':'login','extract':[recipe]}, {'vendor':text}),
                         ['DOMAIN,new.vendor.example'])
    def test_mixed_dns_intent_is_authored_once(self):
        e={'id':'lan','ip-match':'per-rule','include':['DOMAIN,router.example'],
           'dns_required':['IP-CIDR,10.0.0.0/8'],'literal_ips':['IP-CIDR,169.254.0.0/16']}
        self.assertEqual(lib.compile_entry(e,{}),['DOMAIN,router.example',
            'IP-CIDR,10.0.0.0/8','IP-CIDR,169.254.0.0/16,no-resolve'])

    def test_new_official_endpoint_cannot_assign_itself_by_just_appearing_in_a_table(self):
        from loon_rules.generation.contracts import resolve_additions
        recipe={'format':'host-table','source':'doc','sections':['service'],
                'select':[{'role':['Authentication'],'roots':['vendor.example']}]}
        entry={'id':'account','extract':[recipe]}
        contract={'id':'network','format':'apple-host-table','source':'doc','sections':['service'],
                  'routes':{'account':['login.vendor.example']},'discover':{'account':'extract'}}
        def doc(new,role):
            return {'doc':'<h2 id="service"></h2><table>'+''.join(
                f'<tr><td>{h}</td><td>443</td><td>TCP</td><td>OS</td><td>{r}</td></tr>'
                for h,r in [('login.vendor.example','Authentication'),(new,role)])+'</table>'}
        expanded=resolve_additions([contract],{'account':entry},doc('new.vendor.example','Authentication'))
        self.assertIn('new.vendor.example',expanded[0]['routes']['account'])
        self.assertEqual(contract['routes']['account'],['login.vendor.example'])
        for host,role in [('files.vendor.example','Download'),('auth.cdn.example','Authentication')]:
            with self.subTest(host=host), self.assertRaisesRegex(Invalid,'待归属'):
                resolve_additions([contract],{'account':entry},doc(host,role))

    def test_push_addresses_only_come_from_both_labelled_lists(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'labelled-networks','lists':{
            'IPv4':{'family':4,'parents':['17.0.0.0/8'],'min-prefix':16},
            'IPv6':{'family':6,'parents':['2620:149::/32'],'min-prefix':48}}}
        doc='<p>The entire 17.0.0.0/8 is Apple.</p><p>IPv4</p><ul><li>17.249.0.0/16</li></ul><p>IPv6</p><ul><li>2620:149:a44::/48</li></ul>'
        self.assertEqual(extract_rows(recipe,doc),{'IP-CIDR,17.249.0.0/16,no-resolve','IP-CIDR6,2620:149:a44::/48,no-resolve'})
        for broken in (doc.split('<p>IPv6')[0],doc.replace('17.249.0.0/16','17.0.0.0/8'),doc.replace('17.249.0.0/16','1.1.1.0/24')):
            with self.assertRaises(Invalid): extract_rows(recipe,broken)

    def test_service_endpoint_table_respects_section_id_row_and_address_column(self):
        from loon_rules.sources.inputs import extract_rows
        src={'format':'endpoint-sets','sections':['mail'],'sets':[10],'roots':['mx.example']}
        doc='<h2 id="mail">Mail</h2><table>'+''.join(
            f'<tr><td>{n}</td><td>Required</td><td>Yes</td><td>{addr}</td><td>443</td></tr>'
            for n,addr in [(10,'*.mx.example, api.mx.example<br>192.0.2.0/24, shared.example'),(11,'skip.mx.example')])+'</table>'
        self.assertEqual(extract_rows(src,doc),{'DOMAIN-WILDCARD,*.mx.example','DOMAIN,api.mx.example'})
        with self.assertRaises(Invalid): extract_rows(src,doc.replace('<td>10','<td>12'))

    def test_official_wildcard_is_not_an_apex_and_is_redundant_under_a_suffix(self):
        root='DOMAIN-WILDCARD,*.mx.example'
        self.assertEqual(lib.compact([root,'DOMAIN-WILDCARD,*.tenant.mx.example','DOMAIN,mx.example']),
                         [root,'DOMAIN,mx.example'])
        self.assertEqual(lib.compact([root,'DOMAIN-SUFFIX,mx.example']),['DOMAIN-SUFFIX,mx.example'])

    def test_official_address_rotation_does_not_pin_retired_ips_or_accept_a_truncated_family(self):
        old=['DOMAIN,api.example', 'IP-CIDR,17.57.144.0/22,no-resolve','IP-CIDR,17.249.0.0/16,no-resolve',
             'IP-CIDR6,2620:149:a44::/48,no-resolve']
        new=[old[0],old[2],old[3],'IP-CIDR,17.188.128.0/22,no-resolve']
        lib.guard_coverage('push',old,new,official_networks=True)
        for broken in ([old[0],old[1],old[2]], [old[0],old[1],old[3]], new[1:]):
            with self.assertRaises(Invalid): lib.guard_coverage('push',old,broken,official_networks=True)

    def test_official_voice_json_accepts_only_public_addresses_of_the_declared_family(self):
        import json
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'ip-prefix-json','fields':{'ipv4Prefix':4,'ipv6Prefix':6}}
        def doc(rows):return json.dumps({'creationTime':'2026-11-16T00:00:00Z','prefixes':rows})
        valid=[{'ipv4Prefix':'102.37.57.54/32'},{'ipv6Prefix':'2606:4700::1/128'}]
        self.assertEqual(extract_rows(recipe,doc(valid)),{
            'IP-CIDR,102.37.57.54/32,no-resolve','IP-CIDR6,2606:4700::1/128,no-resolve'})
        for records in ([],[{'ipv4Prefix':'10.0.0.1/32'}],
                        [{'ipv4Prefix':'102.37.57.0/24'}],
                        [{'ipv4Prefix':'2606:4700::1/128'}],
                        [{'otherPrefix':'102.37.57.54/32'}]):
            with self.subTest(records=records),self.assertRaises(Invalid):
                extract_rows(recipe,doc(records))

    def test_a_new_official_address_family_can_be_added_without_losing_domain_coverage(self):
        old=['DOMAIN,api.example'];new=old+['IP-CIDR,102.37.57.54/32,no-resolve']
        lib.guard_coverage('voice',old,new,official_networks=True)
        lib.guard_coverage('voice',new,new+['IP-CIDR6,2606:4700::1/128,no-resolve'],official_networks=True)
        with self.assertRaises(Invalid):lib.guard_coverage('voice',new,old,official_networks=True)
        with self.assertRaises(Invalid):lib.guard_coverage('voice',old,new[1:],official_networks=True)

    def test_both_blocklists_protect_functional_hosts_even_when_used_alone(self):
        entry={'id':'ads','kinds':['DOMAIN','DOMAIN-SUFFIX'],'flags':[],'sources':['feed']}
        trusted={'login.vendor.example'}
        old=['DOMAIN-SUFFIX,vendor.example','DOMAIN,ads.other.example']
        for downloaded in ({}, {'feed':'DOMAIN-SUFFIX,vendor.example\nDOMAIN,ads.other.example\nDOMAIN,dubious.example'}):
            kept,_=lib.refresh_reviewed_feed(entry,old,downloaded,protected=trusted)
            self.assertEqual(kept,['DOMAIN,ads.other.example'])

class ScheduledRefresh(PublicSourceExamples):
    def test_new_sdk_endpoint_is_protected_from_ads_without_a_fixed_allowlist(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from contextlib import redirect_stdout
        from io import StringIO
        import json
        feed='https://public.example/product';sdk='https://public.example/sdk';ad='https://public.example/ads'
        recipe={'format':'python-sdk-endpoints','classes':['Client'],'fields':['base_url']}
        product={'id':'product','mode':'managed','priority':30,'section':'service','description':'产品',
                 'boundary':'API','sources':[feed,sdk],'feed-sources':[feed],'kinds':['DOMAIN-SUFFIX'],
                 'flags':[],'license':'MIT','discovery':{'inputs':[{'source':sdk,'family':'vendor','authority':True,'recipe':recipe}]}}
        ads={'id':'ads','mode':'managed','priority':20,'section':'privacy','description':'广告','boundary':'广告',
             'sources':[ad],'kinds':['DOMAIN'],'flags':[],'license':'MIT','policy-hint':'reject'}
        cfg={'entries':[ads,product],'detailed':['product'],'general':['ads'],'alternatives':[],
             'optional':[],'views':[],'critical':{'old.vendor.example':['product']},'shared-negatives':[],
             'sections':[{'id':'privacy','title':'隐私','from':20,'through':20},{'id':'service','title':'服务','from':30,'through':30}]}
        ad_rows=['DOMAIN,new-api.vendor.example','DOMAIN,ad.other.example']
        downloads={ad:'\n'.join(ad_rows),feed:'DOMAIN-SUFFIX,old.vendor.example',
                   sdk:'class Client:\n    def __init__(self):\n        base_url = "https://new-api.vendor.example/v1"\n'}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();(root/'config/catalog.json').write_text(json.dumps(cfg))
            (root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,{e['id']:e for e in cfg['entries']}))
            for e,rows in [(product,['DOMAIN-SUFFIX,old.vendor.example']),(ads,ad_rows)]:
                (root/'rules'/lib.rule_filename(e)).write_text(lib.decorate(e,rows,None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=downloads.__getitem__):
                lib.run()
                lib.run()
            self.assertEqual(lib.rules.read_rules((root/'rules'/lib.rule_filename(ads)).read_text()),['DOMAIN,ad.other.example'])
            product_rows=lib.rules.read_rules((root/'rules'/lib.rule_filename(product)).read_text())
            self.assertIn('DOMAIN,new-api.vendor.example',product_rows)
            self.assertEqual(lib.run(offline=True),0)

    def test_new_root_from_source_evidence_reaches_subscription_without_an_include_or_fixed_case(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from contextlib import redirect_stdout
        from io import StringIO
        import json
        a='https://public.example/a';b='https://public.example/b'
        entry={'id':'product','mode':'managed','priority':30,'section':'service','description':'产品',
               'boundary':'业务入口','sources':[a,b],'feed-sources':[a],'kinds':['DOMAIN','DOMAIN-SUFFIX'],
               'flags':[],'license':'MIT','discovery':{'inputs':[{'source':a,'family':'one'},{'source':b,'family':'two'}]}}
        cfg={'entries':[entry],'detailed':['product'],'general':[],'alternatives':[],
             'optional':[],'views':[],'critical':{'old.vendor.example':['product']},'shared-negatives':[],
             'sections':[{'id':'service','title':'服务','from':30,'through':30}]}
        feed='DOMAIN,old.vendor.example\nDOMAIN-SUFFIX,new-product.example'
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();(root/'config/catalog.json').write_text(json.dumps(cfg))
            (root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,{'product':entry}))
            output=root/'rules'/lib.rule_filename(entry)
            output.write_text(lib.decorate(entry,['DOMAIN,old.vendor.example'],None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect={a:feed,b:feed}.__getitem__):lib.run()
            self.assertIn('DOMAIN-SUFFIX,new-product.example',lib.rules.read_rules(output.read_text()))
            self.assertEqual(lib.run(offline=True),0)

    def test_new_required_official_host_is_protected_before_it_becomes_a_fixed_case(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from contextlib import redirect_stdout
        from io import StringIO
        import json
        doc='https://public.example/required';feed='https://public.example/ads'
        service={'id':'service','mode':'compiled','priority':30,'section':'service','description':'产品',
                 'boundary':'必需入口','sources':[doc],'include':['DOMAIN,known.vendor.example'],
                 'extract':[{'source':doc,'format':'purpose-host-table','section':'required',
                             'headers':['Domains','Description'],'purposes':['Authentication'],
                             'roots':['vendor.example'],'protect-from-reject':True}]}
        ads={'id':'ads','mode':'managed','priority':20,'section':'privacy','description':'广告',
             'boundary':'只拦广告','sources':[feed],'kinds':['DOMAIN'],'flags':[],
             'license':'MIT','policy-hint':'reject'}
        cfg={'entries':[ads,service],'detailed':['service'],'general':['ads'],'alternatives':[],
             'optional':[],'views':[],'critical':{'known.vendor.example':['service']},'shared-negatives':[],
             'sections':[{'id':'privacy','title':'隐私','from':20,'through':20},
                         {'id':'service','title':'服务','from':30,'through':30}]}
        html='<h2 id="required"></h2><table><tr><th>Domains</th><th>Description</th></tr><tr><td>https://new-login.vendor.example</td><td>Authentication</td></tr></table>'
        downloaded={doc:html,feed:'DOMAIN,new-login.vendor.example\nDOMAIN,ads.other.example'}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();(root/'config/catalog.json').write_text(json.dumps(cfg))
            (root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,{e['id']:e for e in cfg['entries']}))
            for entry,rows in [(ads,downloaded[feed].splitlines()),(service,service['include'])]:
                (root/'rules'/lib.rule_filename(entry)).write_text(lib.decorate(entry,rows,None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=downloaded.__getitem__):self.assertEqual(lib.run(),0)
            output=lib.rules.read_rules((root/'rules'/lib.rule_filename(ads)).read_text())
            self.assertEqual(output,['DOMAIN,ads.other.example'])
            report=json.loads((root/'data/maintenance-state.json').read_text())
            self.assertIn('new-login.vendor.example',report['functional-hosts'])
            self.assertEqual(lib.run(offline=True),0)

    def test_tightened_scope_repairs_a_previous_output_before_validating_publication(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from contextlib import redirect_stdout
        from io import StringIO
        import json
        entry={'id':'platform','mode':'managed','priority':1,'section':'service',
               'description':'平台','boundary':'不接管共享托管','sources':['https://public.example/feed'],
               'kinds':['DOMAIN','DOMAIN-SUFFIX'],'flags':[],'license':'MIT'}
        cfg={'entries':[entry],'detailed':['platform'],'general':[],'alternatives':[],
             'optional':[],'views':[],'critical':{'api.example':['platform']},
             'shared-negatives':[],'sections':[{'id':'service','title':'服务','from':1,'through':1}]}
        old=['DOMAIN,api.example','DOMAIN-SUFFIX,azurewebsites.net']
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir()
            (root/'config/catalog.json').write_text(json.dumps(cfg))
            (root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,{'platform':entry}))
            path=root/'rules'/lib.rule_filename(entry)
            path.write_text(lib.decorate(entry,old,None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',return_value='\n'.join(old)):
                self.assertEqual(lib.run(),0)
            self.assertEqual(lib.rules.read_rules(path.read_text()),['DOMAIN,api.example'])
            self.assertEqual(lib.run(offline=True),0)

    def test_new_official_auth_host_is_published_once_and_unknown_third_party_cannot_replace_it(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from contextlib import redirect_stdout
        from io import StringIO
        import json
        url='https://public.example/official'
        entry={'id':'login','mode':'compiled','priority':31,'section':'service','description':'账户',
               'boundary':'登录','sources':[url],'extract':[{'source':url,'format':'host-table',
                 'sections':['account'],'select':[{'roots':['vendor.example'],'role':['Login']}]}]}
        cfg={'entries':[entry],'detailed':['login'],'general':[],'alternatives':[],'optional':[],
             'views':[],'critical':{'login.vendor.example':['login']},'shared-negatives':['shared.example'],
             'sections':[{'id':'service','title':'服务','from':30,'through':40}]}
        contract={'id':'service','source':url,'format':'apple-host-table','sections':['account'],
                  'routes':{'login':['login.vendor.example']},'discover':{'login':'extract'}}
        def doc(host):
            return '<h2 id="account"></h2><table>'+''.join(
                f'<tr><td>{h}</td><td>443</td><td>TCP</td><td>OS</td><td>Login</td></tr>'
                for h in ('login.vendor.example',host))+'</table>'
        with TemporaryDirectory() as tmp, patch.object(lib,'ROOT',prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root=prepare_workspace(tmp); (root/'rules').mkdir()
            (root/'config/catalog.json').write_text(json.dumps(cfg))
            (root/'config/endpoint-contracts.json').write_text(json.dumps([contract]))
            (root/'docs/rules.md').write_text(lib.render_index(cfg,{'login':entry}))
            path=root/'rules'/lib.rule_filename(entry)
            path.write_text(lib.decorate(entry,['DOMAIN,login.vendor.example'],None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',return_value=doc('new.vendor.example')):
                self.assertEqual(lib.run(),0)
                updated=path.read_text()
                self.assertIn('DOMAIN,new.vendor.example\n',updated)
                lib.run()
                self.assertEqual(updated,path.read_text())
            status=(root/'data/maintenance-state.json').read_text()
            with patch.object(lib.transport,'download',return_value=doc('new.shared.example')), self.assertRaises(Invalid):
                lib.run()
            self.assertEqual(updated,path.read_text())
            self.assertEqual((root/'data/maintenance-state.json').read_text(),status)

class SourceContracts(unittest.TestCase):
    def test_sdk_guide_discovers_new_api_and_console_hosts_by_purpose(self):
        recipe={'format':'sdk-client-endpoints','roots':['vendor.example'],
                'api-fields':['base_url','baseURL'],'console-labels':['API Keys']}
        text='''<pre><code>client = Client(<span>base_url</span>=<span>&quot;https://api.vendor.example/v1&quot;</span>)
new_client = Client(baseURL: "https://api-next.vendor.example/v2")
other_client = Client(base_url="https://api.other.example/v1")</code></pre>
<p>Example URL: https://unrelated.vendor.example/</p>
<a href="https://console-new.vendor.example/account/keys"><b>API</b> Keys</a>
<a href="https://billing.vendor.example">Pricing</a>
<a href="https://console.other.example">API Keys</a>'''
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,api.vendor.example',
            'DOMAIN,api-next.vendor.example','DOMAIN,console-new.vendor.example'})

    def test_sdk_guide_requires_both_documented_api_and_console_roles(self):
        recipe={'format':'sdk-client-endpoints','roots':['vendor.example'],
                'api-fields':['base_url'],'console-labels':['API Keys']}
        code='<pre>client = Client(base_url="https://api.vendor.example/v1")</pre>'
        link='<a href="https://console.vendor.example/account/keys">API Keys</a>'
        self.assertEqual(len(extract_rows(recipe,code+link)),2)
        for bad in (code,link,code.replace('https://api.','https://api.vendor.example@')+link,
                    code+link.replace('API Keys','Unrelated'),
                    '<script>'+code+'</script>'+link):
            with self.subTest(text=bad),self.assertRaises(Invalid):extract_rows(recipe,bad)

    def test_official_product_entry_list_can_discover_a_new_root_without_copying_other_links(self):
        recipe={'format':'product-entrypoints','item-prefix':'The Product app we offer at',
                'brand-label':'product','owned-parents':['vendor.example']}
        doc='''<ul><li>The Product app we offer at product.vendor.example, product.com, and product.ai</li>
<li>Other services: billing.vendor.example</li></ul>
<script><li>The Product app we offer at product.invalid</li></script>'''
        self.assertEqual(extract_rows(recipe,doc),{'DOMAIN,product.vendor.example',
            'DOMAIN,product.com','DOMAIN,product.ai'})
        for bad in (doc.replace('app we offer at','other apps'),
                    doc.replace('product.ai','tenant.shared.example'),
                    doc.replace('product.ai','product.evil.example')):
            with self.subTest(text=bad),self.assertRaises(Invalid):extract_rows(recipe,bad)

    def test_authentication_table_only_imports_named_product_hosts(self):
        recipe={'format':'purpose-host-table','section':'required','headers':['Domains','Description'],
                'purposes':['Authentication','Docker Pull/Push'],'roots':['docker.com','docker.io']}
        def row(host,role):return f'<tr><td>{host}</td><td>{role}</td></tr>'
        text='<h2 id="required"></h2><table><tr><th>Domains</th><th>Description</th></tr>'+''.join([
            row('https://login.docker.com','Authentication'),row('https://new-auth.docker.com','Authentication'),
            row('https://cdn.auth0.com','Authentication'),row('https://production.cloudfront.docker.com','Docker Pull/Push'),
            row('https://metrics.docker.com','Error reports')])+'</table>'
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,login.docker.com',
            'DOMAIN,new-auth.docker.com','DOMAIN,production.cloudfront.docker.com'})
        with self.assertRaises(Invalid):extract_rows(recipe,text.replace('Docker Pull/Push','Other'))

    def test_brand_domain_list_can_add_a_new_official_root_without_reading_other_lists(self):
        import json
        recipe={'format':'article-domain-list','body-path':['article','body'],
                'label-contains':'Signal utilizes other domains','brand-label':'signal'}
        body='<p>Signal utilizes other domains for sharing:</p><ul><li>signal.art</li><li>signal.tube</li></ul><p>Other links</p><ul><li>not-signal.example</li></ul>'
        doc=json.dumps({'article':{'body':body}})
        self.assertEqual(extract_rows(recipe,doc),{'DOMAIN-SUFFIX,signal.art','DOMAIN-SUFFIX,signal.tube'})
        with self.assertRaises(Invalid):extract_rows(recipe,json.dumps({'article':{'body':body.replace('signal.tube','shared.example')}}))

    def test_meeting_network_section_keeps_both_families_and_exact_sni(self):
        recipe={'format':'section-media-networks','section':'media','sni-roots':['turns.goog'],
                'min-prefix':{'4':16,'6':32}}
        text='<h4 id="other">Other</h4><li>IPv4: 8.0.0.0/8</li><h4 id="media">Media</h4><ul><li>IPv4: 74.125.250.0/24</li><li>IPv6: 2001:4860:4864:5::/64</li><li>SNI: workspace.turns.goog</li></ul><h4 id="next">Next</h4><li>IPv4: 1.1.1.0/24</li>'
        self.assertEqual(extract_rows(recipe,text),{'IP-CIDR,74.125.250.0/24,no-resolve',
            'IP-CIDR6,2001:4860:4864:5::/64,no-resolve','DOMAIN,workspace.turns.goog'})
        for broken in (text.replace('IPv6:','Version 6:'),text.replace('74.125.250.0/24','0.0.0.0/0')):
            with self.assertRaises(Invalid):extract_rows(recipe,broken)

    def test_communications_ip_table_reads_only_the_required_media_row(self):
        recipe={'format':'endpoint-network-sets','sections':['teams'],'sets':[11],
                'category':'Optimize Required','udp-port':3478,'min-prefix':{'4':14,'6':32}}
        def row(n,category,addresses,ports):return '<tr>'+''.join(f'<td>{v}</td>' for v in [n,category,'Yes',addresses,ports])+'</tr>'
        text='<h2 id="teams"></h2><table>'+row(11,'Optimize Required','52.112.0.0/14, 2603:1063::/38','UDP: 3478, 3479')+row(12,'Allow Required','40.0.0.0/8','TCP: 443')+'</table>'
        self.assertEqual(extract_rows(recipe,text),{'IP-CIDR,52.112.0.0/14,no-resolve','IP-CIDR6,2603:1063::/38,no-resolve'})
        with self.assertRaises(Invalid):extract_rows(recipe,text.replace('UDP: 3478','TCP: 3478'))

    def test_service_definition_only_reads_default_host_from_the_named_service(self):
        from loon_rules.sources.inputs import extract_rows
        spec={'format':'service-default-host','service':'Models','roots':['vendor.example']}
        text=('service Other {\n  option (google.api.default_host) = "other.vendor.example";\n}\n'
              'service Models {\n  // option (google.api.default_host) = "wrong.vendor.example";\n'
              '  option (google.api.default_host) = "api.vendor.example";\n}\n')
        self.assertEqual(extract_rows(spec,text),{'DOMAIN,api.vendor.example'})
        with self.assertRaises(Invalid): extract_rows(spec,text.replace('api.vendor.example','tenant.shared.example'))

    def test_description_or_sources_can_be_regenerated_without_changing_body_date(self):
        e={'id':'store','description':'购买','boundary':'不含下载','sources':['https://old.example']}
        rows=['DOMAIN,buy.example']; before='2020-01-01T00:00:00Z'
        old=lib.decorate(e,rows,None,before)
        revised=dict(e,sources=['https://new.example'])
        with self.assertRaises(Invalid): lib.verify_file(revised,rows,old)
        lib.verify_file(revised,rows,old,refresh=True)
        self.assertIn('# updated-at: '+before,lib.decorate(revised,rows,old,'2026-01-01T00:00:00Z'))

    def test_normal_ad_withdrawal_is_accepted_without_publishing_unreviewed_additions(self):
        e={'id':'ads','policy-hint':'reject','reconcile':'ad-withdrawals','sources':['feed'],'kinds':['DOMAIN','DOMAIN-SUFFIX'],'flags':[]}
        old=[f'DOMAIN,ad{i}.example' for i in range(20)]
        fresh=old[:-1]+['DOMAIN,unconfirmed.example']
        kept,state=lib.refresh_reviewed_feed(e,old,{'feed':'\n'.join(fresh)})
        self.assertEqual(kept,old[:-1])
        self.assertEqual(state['new-matches'],1)
        self.assertEqual(lib.refresh_reviewed_feed(e,old,{'feed':old[0]})[0],old)
        # A narrowed upstream scope only keeps the surviving child, not the obsolete parent.
        previous=old+['DOMAIN-SUFFIX,campaign.example']
        self.assertEqual(lib.refresh_reviewed_feed(e,previous,{'feed':'\n'.join(old+['DOMAIN,a.campaign.example'])})[0],old+['DOMAIN,a.campaign.example'])

    def test_independent_source_inventory_finds_unclassified_suffix_not_just_its_apex(self):
        entry={'id':'vendor','source':'feed','owners':['core']}
        published={'core':['DOMAIN,service.example','DOMAIN-SUFFIX,known.example']}
        result=lib.audit_inventory(entry,{'feed':'DOMAIN-SUFFIX,service.example\nDOMAIN,new.known.example\nUSER-AGENT,Demo'},published)
        self.assertEqual(result,{'state':'review','domain-scopes':2,'outside-scope':1,'other-rules':1})
        self.assertNotIn('service.example',str(result))

    def test_reviewed_exact_exclusion_cannot_authorize_removing_a_whole_suffix(self):
        banned={'mixed.vendor.example'}
        lib.guard_coverage('download',['DOMAIN,mixed.vendor.example'],['DOMAIN,file.vendor.example'],excluded_hosts=banned)
        with self.assertRaises(Invalid):
            lib.guard_coverage('download',['DOMAIN-SUFFIX,mixed.vendor.example'],['DOMAIN,file.vendor.example'],excluded_hosts=banned)

    def test_only_a_new_declared_buildable_subscription_can_be_bootstrapped(self):
        from pathlib import Path
        paths={'present':Path('present.lsr'),'new':Path('new.lsr')}
        entries={'present':{'mode':'managed'},'new':{'mode':'compiled'}}
        self.assertEqual(lib.new_outputs(paths,entries,{paths['present']},{'present'},refresh=True),{'new'})
        for known,refresh in [({'present','new'},True),({'present'},False)]:
            with self.assertRaises(Invalid): lib.new_outputs(paths,entries,{paths['present']},known,refresh=refresh)

    def test_shared_guards_apply_to_wildcard_and_supernet_not_only_identical_text(self):
        for rule in ('DOMAIN-WILDCARD,*.googleapis.com','DOMAIN-WILDCARD,*.com',
                     'IP-CIDR,17.1.1.1/8,no-resolve','IP-CIDR,16.0.0.0/7,no-resolve'):
            with self.subTest(rule=rule),self.assertRaises(Invalid):
                lib.lint_content('specialty',[rule])
        lib.lint_content('specific',['DOMAIN,api.vendor.example','IP-CIDR,17.249.0.0/16,no-resolve'])

    def test_existing_official_host_changing_role_is_not_an_unchanged_inventory(self):
        from loon_rules.generation.contracts import resolve_additions
        def entry(role):
            return {'extract':[{'source':'doc','format':'host-table','sections':['service'],
                                'select':[{'role':[role],'roots':['vendor.example']}]}]}
        spec={'id':'product','source':'doc','format':'apple-host-table','sections':['service'],
              'routes':{'auth':['old.vendor.example'],'download':['files.vendor.example']},
              'discover':{'auth':'extract','download':'extract'}}
        body='<h2 id="service"></h2><table>'+''.join(
            f'<tr><td>{host}</td><td>443</td><td>TCP</td><td>OS</td><td>Download</td></tr>'
            for host in ['old.vendor.example','files.vendor.example'])+'</table>'
        with self.assertRaisesRegex(Invalid,'用途变化'):
            resolve_additions([spec],{'auth':entry('Login'),'download':entry('Download')},{'doc':body})

    def test_a_region_exception_cannot_be_satisfied_by_the_domestic_bucket(self):
        spec={'id':'regional','source':'feed','owners':['home'],
              'other-owners':{'DOMAIN-SUFFIX,global.vendor.example':'international'}}
        feed={'feed':'DOMAIN-SUFFIX,global.vendor.example'}
        pools={'international':[],'home':['DOMAIN-SUFFIX,vendor.example']}
        self.assertEqual(lib.audit_inventory(spec,feed,pools)['outside-scope'],1)
