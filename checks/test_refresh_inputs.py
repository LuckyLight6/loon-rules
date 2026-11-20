import unittest
import library as lib
from maintain import Invalid

class RefreshInputs(unittest.TestCase):
    def test_database_is_not_seeded_from_yesterdays_subscription(self):
        entry={'id':'files','include':['DOMAIN,keep.example']}
        self.assertEqual(lib.compile_entry(entry,{}),['DOMAIN,keep.example'])

    def test_equal_counts_do_not_hide_loss_of_one_whole_scope(self):
        before=['DOMAIN-SUFFIX,files.example','DOMAIN,a.example']
        with self.assertRaisesRegex(Invalid,'files.example'):
            lib.guard_coverage('files',before,['DOMAIN,one.files.example','DOMAIN,b.example'])
        lib.guard_coverage('files',['DOMAIN,one.files.example'],before)

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
        from endpoint_contracts import resolve_additions
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
        from rule_inputs import extract_rows
        recipe={'format':'labelled-networks','lists':{
            'IPv4':{'family':4,'parents':['17.0.0.0/8'],'min-prefix':16},
            'IPv6':{'family':6,'parents':['2620:149::/32'],'min-prefix':48}}}
        doc='<p>The entire 17.0.0.0/8 is Apple.</p><p>IPv4</p><ul><li>17.249.0.0/16</li></ul><p>IPv6</p><ul><li>2620:149:a44::/48</li></ul>'
        self.assertEqual(extract_rows(recipe,doc),{'IP-CIDR,17.249.0.0/16,no-resolve','IP-CIDR6,2620:149:a44::/48,no-resolve'})
        for broken in (doc.split('<p>IPv6')[0],doc.replace('17.249.0.0/16','17.0.0.0/8'),doc.replace('17.249.0.0/16','1.1.1.0/24')):
            with self.assertRaises(Invalid): extract_rows(recipe,broken)

    def test_service_endpoint_table_respects_section_id_row_and_address_column(self):
        from rule_inputs import extract_rows
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

    def test_both_blocklists_protect_functional_hosts_even_when_used_alone(self):
        entry={'id':'ads','kinds':['DOMAIN','DOMAIN-SUFFIX'],'flags':[],'sources':['feed']}
        trusted={'login.vendor.example'}
        old=['DOMAIN-SUFFIX,vendor.example','DOMAIN,ads.other.example']
        for downloaded in ({}, {'feed':'DOMAIN-SUFFIX,vendor.example\nDOMAIN,ads.other.example\nDOMAIN,dubious.example'}):
            kept,_=lib.refresh_reviewed_feed(entry,old,downloaded,protected=trusted)
            self.assertEqual(kept,['DOMAIN,ads.other.example'])

class ScheduledRefresh(unittest.TestCase):
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
        with TemporaryDirectory() as tmp, patch.object(lib,'ROOT',Path(tmp)), redirect_stdout(StringIO()):
            root=Path(tmp); (root/'rules').mkdir()
            (root/'catalog.json').write_text(json.dumps(cfg))
            (root/'endpoint-contracts.json').write_text(json.dumps([contract]))
            (root/'INDEX.md').write_text(lib.render_index(cfg,{'login':entry}))
            path=root/'rules'/lib.rule_filename(entry)
            path.write_text(lib.decorate(entry,['DOMAIN,login.vendor.example'],None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.rules,'download',return_value=doc('new.vendor.example')):
                self.assertEqual(lib.run(),0)
                updated=path.read_text()
                self.assertIn('DOMAIN,new.vendor.example\n',updated)
                lib.run()
                self.assertEqual(updated,path.read_text())
            status=(root/'status.json').read_text()
            with patch.object(lib.rules,'download',return_value=doc('new.shared.example')), self.assertRaises(Invalid):
                lib.run()
            self.assertEqual(updated,path.read_text())
            self.assertEqual((root/'status.json').read_text(),status)

class SourceContracts(unittest.TestCase):
    def test_service_definition_only_reads_default_host_from_the_named_service(self):
        from rule_inputs import extract_rows
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
        from endpoint_contracts import resolve_additions
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
