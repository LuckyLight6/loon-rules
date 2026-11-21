import json
import unittest
from loon_rules.generation import pipeline as lib
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows

class SubscriptionChoices(unittest.TestCase):
    def test_explained_source_exclusions_do_not_hide_a_new_unassigned_service(self):
        spec={'source':'feed','owners':['service'],
              'reviewed-outside':{'DOMAIN-SUFFIX,logs.example':'日志留给可选隐私规则'}}
        data={'service':['DOMAIN-SUFFIX,product.example']}
        src={'feed':'DOMAIN-SUFFIX,product.example\nDOMAIN-SUFFIX,logs.example'}
        state=lib.audit_inventory(spec,src,data)
        self.assertEqual(state['state'],'current')
        self.assertEqual(state['reviewed-outside'],1)
        state=lib.audit_inventory(spec,{'feed':src['feed']+'\nDOMAIN-SUFFIX,new.example'},data)
        self.assertEqual(state['state'],'review')
        self.assertEqual(state['outside-scope'],1)

    def test_only_provider_rows_of_all_selected_families_count(self):
        recipe={'format':'http-provider-lists','sections':['WEB','WEB6'],
                'providers':{'echo':{'roots':['echo.example'],'paths':['/']}}}
        body='''- `WEB` addresses
  - `echo` using [v4](https://one.echo.example)
  - `echo` using [account](https://one.echo.example/account)
  - `echo` using [lookalike](https://not-echo.example)
  - `echo` using [userinfo](https://foo@ignore.echo.example)
  - `other` using [shared](https://shared.echo.example)
- `WEB6` addresses
  - `echo` using [new](https://six.echo.example/)
- `DNS` addresses
  - `echo` using [resolver](https://dns.echo.example)
'''
        self.assertEqual(extract_rows(recipe,body),{'DOMAIN,one.echo.example','DOMAIN,six.echo.example'})
        with self.assertRaises(Invalid): extract_rows(recipe,body.replace('`WEB6`','`OTHER`'))
        with self.assertRaises(Invalid): extract_rows(recipe,body.replace('https://six.echo.example','http://six.echo.example'))

    def test_shared_hosting_is_not_new_generic_coverage(self):
        entry={'id':'wide','mode':'managed','sources':['feed'],'kinds':['DOMAIN','DOMAIN-SUFFIX'],
               'flags':[],'exclude-tenant-roots':['cloudapp.net']}
        old=['DOMAIN,keep.example']
        out,state=lib.refresh_reviewed_feed(entry,old,{'feed':'\n'.join(old+[
            'DOMAIN-SUFFIX,app.cloudapp.net','DOMAIN,next.example','DOMAIN,notcloudapp.net'])})
        self.assertEqual(out,old)
        self.assertEqual(state['new-matches'],2)
        self.assertEqual(state['outside-purpose'],1)

    def test_published_parent_and_tenant_rules_are_removed_without_losing_official_controls(self):
        entry={'id':'platform','mode':'managed','sources':['feed'],
               'kinds':['DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD'],'flags':[],
               'exclude-tenant-roots':['core.windows.net'],'official-hosts':True}
        old=['DOMAIN-SUFFIX,windows.net','DOMAIN,tenant.blob.core.windows.net',
             'DOMAIN-WILDCARD,*.images.tenant.blob.core.windows.net',
             'DOMAIN,management.core.windows.net','DOMAIN,portal.example']
        expected=['DOMAIN,management.core.windows.net','DOMAIN,portal.example']
        for downloaded in ({},{'feed':'\n'.join(old)}):
            out,state=lib.refresh_reviewed_feed(entry,old,downloaded,
                                               official=['management.core.windows.net'])
            self.assertEqual(out,expected)

    def test_azure_cloud_metadata_is_read_as_data_without_executing_python(self):
        text="""raise RuntimeError('must not run')
AZURE_PUBLIC_CLOUD = Cloud('AzureCloud',
    endpoints=CloudEndpoints(portal='https://portal.azure.com/',
                             resource_manager='https://management.azure.com/'),
    suffixes=CloudSuffixes(storage_endpoint='core.windows.net',
                           acr_login_server_endpoint='.azurecr.io'))
"""
        recipe={'format':'azure-cloud-metadata','clouds':['AZURE_PUBLIC_CLOUD'],'part':'suffixes'}
        self.assertEqual(extract_rows(recipe,text),{
            'DOMAIN-SUFFIX,core.windows.net','DOMAIN-SUFFIX,azurecr.io'})
        controls={**recipe,'part':'endpoints','fields':['portal']}
        self.assertEqual(extract_rows(controls,text),{'DOMAIN,portal.azure.com'})
        with self.assertRaises(Invalid):extract_rows(recipe,text.replace("'core.windows.net'",'untrusted_call()'))
        with self.assertRaises(Invalid):extract_rows(recipe,text.replace('AZURE_PUBLIC_CLOUD =','OTHER_CLOUD ='))

    def test_hosted_service_table_does_not_claim_login_or_unlisted_services(self):
        recipe={'format':'service-domain-table','services':['Azure App Service']}
        text='<table><tr><th>Service</th><th>Subdomain</th></tr>'+''.join(
            f'<tr><td>{name}</td><td>{domain}</td></tr>' for name,domain in [
                ('Azure App Service','*.azurewebsites.net'),('Microsoft Entra ID','*.graph.windows.net')])+'</table>'
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN-SUFFIX,azurewebsites.net'})
        with self.assertRaises(Invalid):extract_rows(recipe,text.replace('Azure App Service','Unknown Service'))

    def test_subscription_index_links_every_file_and_marks_optional_choices(self):
        cfg=json.loads((lib.ROOT/'config/catalog.json').read_text())
        es=lib.validate_declarations(cfg); index=lib.render_index(cfg,es)
        optional=set(cfg['optional']+cfg['alternatives'])
        for entry in cfg['entries']:
            key=entry['id']
            entry=es[key]
            row=next(line for line in index.splitlines()
                     if line.startswith('| '+lib.rule_filename(entry).split('-',1)[0]+' |'))
            filename=lib.rule_filename(entry)
            self.assertTrue(f'[{key}](../rules/{filename})' in row,key+' 缺少正文链接')
            self.assertTrue('[订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/'+filename+')' in row,
                            key+' 缺少订阅链接')
            if key in optional:self.assertIn('**可选。**',row)
        self.assertNotIn('上游变更待核',index)
        self.assertIn('(routing.md)',index)
        components={e['id'] for e in cfg['source-components']}
        self.assertTrue(all(key not in index for key in components))
        e=next(e for e in es.values() if e['id']=='overseas-media-extra')
        self.assertEqual(len(e['merge-domains']['include']),2)
        self.assertTrue(set(e['merge-domains']['include'])<=components)

    def test_review_report_names_only_actionable_groups_and_no_candidate_payloads(self):
        es={'routing':{'priority':200,'id':'routing','description':'国内网段'},
            'clean':{'priority':115,'id':'clean','description':'系统连通性'}}
        status={'checked-at':'2026-01-01T01:00:00Z','inputs-read':2,'inputs-requested':2,
                'reviewed-inputs':{'routing':{'state':'review','new-matches':3,'missing-rules':1,
                    'untrusted-data':'never-print.example'},'clean':{'state':'current','outside-purpose':5}},
                'source-inventories':{}}
        actual=lib.render_review(status,es)
        self.assertIn('200',actual)
        self.assertNotIn('never-print',actual)
        self.assertNotIn('115',actual.split('## 范围外')[0])
        self.assertIn('115',actual.split('## 范围外')[1])

    def test_domestic_subscription_on_its_own_cannot_claim_foreign_service(self):
        entry={'id':'domestic','sources':['feed'],'kinds':['DOMAIN','DOMAIN-SUFFIX'],'flags':[],
               'excluded-rules':['DOMAIN-SUFFIX,mixed.example']}
        old=['DOMAIN-SUFFIX,global.example','DOMAIN-SUFFIX,vendor.example','DOMAIN,ok.example',
             'DOMAIN-SUFFIX,mixed.example']
        raw='\n'.join(old+['DOMAIN,new.global.example','DOMAIN,other.example'])
        reserved=['DOMAIN-SUFFIX,global.example','DOMAIN,chat.vendor.example']
        effective,state=lib.refresh_reviewed_feed(entry,old,{'feed':raw},reserved=reserved)
        self.assertEqual(effective,['DOMAIN,ok.example'])
        self.assertEqual(state['new-matches'],1)
        self.assertEqual(state['missing-rules'],0)
        self.assertEqual(state['reserved-scopes'],2)
        self.assertEqual(lib.refresh_reviewed_feed(entry,old,{},reserved=reserved)[0],effective)

    def test_overlap_report_counts_scopes_not_names_and_uses_the_merge_boundary(self):
        es={'foreign':{'merge-domains':{'include':['feed'],'protect':['local']}}}
        rows={'feed':['DOMAIN-SUFFIX,shared.example','DOMAIN,news.example','USER-AGENT,SomeApp'],
              'local':['DOMAIN,cn.shared.example']}
        self.assertEqual(lib.merge_conflicts(es,rows),{'foreign':{'feed':1}})
        self.assertEqual(lib.merge_domain_sources(es['foreign'],rows),['DOMAIN,news.example'])

    def test_release_gate_checks_entire_service_against_each_domestic_choice(self):
        cfg=json.loads((lib.ROOT/'config/catalog.json').read_text())
        domestic={'mainland-routing-all','mainland-domains','source-xkww3n-mainland'}
        for source in ('apple-video-and-fitness','apple-news-and-sports','apple-intelligence-relays',
                       'apple-tv-video-delivery','ai-overseas-all','ai-cn-international-all'):
            self.assertTrue(domestic<=set(cfg['no-overlap'].get(source,[])),source)
        # An unseen child vs a parent suffix must fail even when the positive sample
        # would still hit the correct service first in the full routing profile.
        cfg={'detailed':['service','domestic'],'general':[], 'critical':{}, 'shared-negatives':[],
             'no-overlap':{'service':['domestic']},'views':[]}
        es={'service':{'priority':60,'section':'ai'},'domestic':{'priority':194,'section':'domestic'}}
        with self.assertRaisesRegex(Invalid,'跨业务规则重叠'):
            lib.verify_cases(cfg,es,{'service':['DOMAIN,new.service.example'],
                                     'domestic':['DOMAIN-SUFFIX,service.example']},False)
