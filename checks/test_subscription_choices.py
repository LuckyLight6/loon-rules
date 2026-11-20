import json
import unittest
import library as lib
from maintain import Invalid
from rule_inputs import extract_rows

class SubscriptionChoices(unittest.TestCase):
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

    def test_subscription_index_separates_choices_from_inputs(self):
        cfg=json.loads((lib.ROOT/'catalog.json').read_text())
        es=lib.validate_declarations(cfg); index=lib.render_index(cfg,es)
        for n in (181,182,183,184,186,187,188,190,191,193,196,197,201):
            self.assertNotIn(f'](rules/{n}-',index)
        for n in (180,185,192,194,200,202,203,204):
            self.assertIn(f'](rules/{n}-',index)
        self.assertNotIn('上游变更待核',index)
        self.assertIn('COVERAGE.md#',index)
        # Loss of an alternate media source must not remove the other's unique domains.
        e=next(e for e in es.values() if e['priority']==180)
        members=[es[k]['priority'] for k in e['merge-domains']['include']]
        self.assertEqual(set(members),{181,182})

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
        cfg=json.loads((lib.ROOT/'catalog.json').read_text())
        ids={e['priority']:e['id'] for e in cfg['entries']}
        for source in (44,45,46,57,60,85):
            self.assertTrue({ids[n] for n in (190,191,192,194,196)} <=
                            set(cfg['no-overlap'].get(ids[source],[])),source)
        # An unseen child vs a parent suffix must fail even when the positive sample
        # would still hit the correct service first in the full routing profile.
        cfg={'detailed':['service','domestic'],'general':[], 'critical':{}, 'shared-negatives':[],
             'no-overlap':{'service':['domestic']},'views':[]}
        es={'service':{'priority':60,'section':'ai'},'domestic':{'priority':194,'section':'domestic'}}
        with self.assertRaisesRegex(Invalid,'跨业务规则重叠'):
            lib.verify_cases(cfg,es,{'service':['DOMAIN,new.service.example'],
                                     'domestic':['DOMAIN-SUFFIX,service.example']},False)
