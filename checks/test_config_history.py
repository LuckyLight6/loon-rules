from checks.source_fixtures import prepare_workspace
import copy
import json
import plistlib
from contextlib import contextmanager,redirect_stdout
from datetime import datetime,timedelta,timezone
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid


class ConfigHistory(PublicSourceExamples):
    @contextmanager
    def workspace(self,*,broad=False,external=False):
        from loon_rules.generation import pipeline as lib
        source='https://config.vendor.example/getBag?ix=3'
        other='https://api.platform.example/services.json'
        spec={'method':'public-plist-bag','source':source,'protect-from-reject':True,
              'document':{'format':'plist-service-fields','data-path':['bag'],
                  'identity':[{'path':['kind'],'equals':'identityConfiguration'}],
                  'records':{'paths':[[]],'typed-url-patterns':['id-[A-Za-z-]+'],
                             'required-fields':['id-register','id-query']}}}
        initial='old.cdn.example' if external else 'old.vendor.example'
        entry={'id':'identity','priority':30,'section':'service','mode':'compiled','description':'身份服务',
               'boundary':'按公开用途字段','sources':[source],
               'include':['DOMAIN-SUFFIX,vendor.example'] if broad else ['DOMAIN,legacy.vendor.example'],
               'expand':spec}
        secondary={'id':'other','priority':40,'section':'service','mode':'compiled','description':'其他产品',
                   'boundary':'独立服务字段','sources':[other],
                   'extract':[{'source':other,'format':'json-service-urls','paths':[['servers','*']]}]}
        view={'id':'identity-all','priority':29,'section':'service','mode':'view','description':'身份合集',
              'boundary':'身份服务','members':['identity']}
        config={'schema-version':2,'entries':[view,entry,secondary],
                'sections':[{'id':'service','title':'服务'}],
                'critical':{'legacy.vendor.example':['identity'],'api.platform.example':['other']},
                'shared-negatives':[]}
        class Workspace:
            def __init__(self,root):
                self.root=root;self.config=config;self.entry=entry;self.spec=spec
                self.query=initial;self.kind='identityConfiguration';self.servers=['https://api.platform.example/']
                self.clock=datetime(2026,11,20,0,0,tzinfo=timezone.utc)
            def save(self):
                self.entries=lib.validate_declarations(self.config)
                (self.root/'config/catalog.json').write_text(json.dumps(self.config))
                (self.root/'docs/rules.md').write_text(lib.render_index(self.config,self.entries))
            def read(self,url,**kwargs):
                if url==other and not kwargs:return json.dumps({'servers':self.servers})
                if url!=source or kwargs!={'public_bag':True}:raise AssertionError('unexpected source request')
                document={'kind':self.kind,'id-register':'https://identity.vendor.example/register',
                          'id-query':'https://'+self.query+'/query','id-query-interval':1200}
                return plistlib.dumps({'bag':plistlib.dumps(document)}).decode()
            def run(self,**kwargs):
                clock=self.clock
                class Clock(datetime):
                    @classmethod
                    def now(cls,tz=None):return clock if tz else clock.replace(tzinfo=None)
                with patch.object(lib.transport,'download',side_effect=self.read),patch.object(lib,'datetime',Clock):
                    return lib.run(**kwargs)
            def state(self):return json.loads((self.root/'data/maintenance-state.json').read_text())
            def body(self,key):return lib.rules.read_rules((self.root/'rules'/lib.rule_filename(self.entries[key])).read_text())
            def snapshot(self):return {p:p.read_text() for p in self.root.rglob('*') if p.is_file()}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            w=Workspace(prepare_workspace(tmp));(w.root/'rules').mkdir();w.save()
            (w.root/'config/endpoint-contracts.json').write_text('[]')
            for e in w.entries.values():
                rows=['DOMAIN,api.platform.example'] if e['id']=='other' else entry['include']
                (w.root/'rules'/lib.rule_filename(e)).write_text(lib.decorate(e,rows,None,'2026-01-01T00:00:00Z'))
            yield w

    def test_missing_publisher_endpoint_does_not_stop_unrelated_updates(self):
        with self.workspace() as w:
            self.assertEqual(w.run(),0)
            w.clock+=timedelta(days=1);w.query='next.vendor.example'
            w.servers.append('https://new.api.platform.example/')
            try:result=w.run()
            except Invalid as error:self.fail('不完整配置的缺项不应停止其他更新：'+str(error))
            self.assertEqual(result,0)
            self.assertIn('DOMAIN,old.vendor.example',w.body('identity'))
            self.assertIn('DOMAIN,old.vendor.example',w.body('identity-all'))
            self.assertIn('DOMAIN,new.api.platform.example',w.body('other'))
            state=w.state()
            self.assertEqual(state['config-history-domain-cases'],1)
            self.assertEqual(state['business-domain-cases'],5)
            proof=state['config-endpoint-history']['identity']['retained']['DOMAIN,old.vendor.example']
            self.assertEqual(proof['source'],w.spec['source'])
            self.assertEqual(proof['accepted-at'],'2026-11-20T00:00:00Z')
            self.assertIn('old.vendor.example',state['functional-hosts'])
            self.assertEqual(w.run(offline=True),0)

    def test_offline_validation_does_not_require_a_generated_markdown_report(self):
        with self.workspace() as w:
            w.run();(w.root/'build/verification.md').unlink();before=w.snapshot()
            try:result=w.run(offline=True)
            except OSError as error:self.fail('离线校验不应依赖构建报告：'+str(error))
            self.assertEqual(result,0)
            self.assertEqual(before,w.snapshot())

    def test_compaction_keeps_explicit_missing_host_evidence_and_cases(self):
        with self.workspace(broad=True) as w:
            self.assertEqual(w.run(),0)
            w.query='next.vendor.example';w.clock+=timedelta(days=1)
            self.assertEqual(w.run(),0)
            self.assertEqual(w.body('identity'),['DOMAIN-SUFFIX,vendor.example'])
            state=w.state()
            self.assertIn('DOMAIN,old.vendor.example',state['config-endpoint-history']['identity']['retained'])
            self.assertEqual(state['config-history-domain-cases'],1)
            self.assertIn('old.vendor.example',state['functional-hosts'])

    def test_repeated_absence_keeps_the_original_proof_and_reappearance_replaces_history(self):
        with self.workspace() as w:
            w.run();w.query='next.vendor.example';w.clock+=timedelta(days=1);w.run()
            first=w.state()['config-endpoint-history']['identity']['retained']['DOMAIN,old.vendor.example']
            w.clock+=timedelta(days=30);w.run()
            self.assertEqual(w.state()['config-endpoint-history']['identity']['retained']['DOMAIN,old.vendor.example'],first)
            w.query='old.vendor.example';w.clock+=timedelta(days=1);w.run()
            history=w.state()['config-endpoint-history']['identity']['retained']
            self.assertNotIn('DOMAIN,old.vendor.example',history)
            self.assertIn('DOMAIN,next.vendor.example',history)
            self.assertEqual(w.run(offline=True),0)

    def test_third_party_endpoints_are_not_automatically_kept(self):
        with self.workspace(external=True) as w:
            w.run();w.query='next.vendor.example';w.clock+=timedelta(days=1)
            before=w.snapshot()
            with self.assertRaises(Invalid):w.run()
            self.assertEqual(before,w.snapshot())

    def test_a_changed_purpose_cannot_inherit_old_proofs(self):
        with self.workspace() as w:
            w.run();w.query='next.vendor.example';w.clock+=timedelta(days=1);w.run()
            w.kind='anotherConfiguration'
            w.spec['document']['identity'][0]['equals']=w.kind;w.save()
            before=w.snapshot()
            with self.assertRaises(Invalid):w.run()
            self.assertEqual(before,w.snapshot())

    def test_an_explicit_scope_exclusion_removes_the_historical_entry(self):
        with self.workspace() as w:
            w.run();w.query='next.vendor.example';w.clock+=timedelta(days=1);w.run()
            w.config['scope-negatives']={'old.vendor.example':['identity']};w.save();w.run()
            self.assertNotIn('DOMAIN,old.vendor.example',w.body('identity'))
            self.assertEqual(w.state()['config-endpoint-history'],{})
            self.assertEqual(w.state()['config-history-domain-cases'],0)
            self.assertNotIn('old.vendor.example',w.state()['functional-hosts'])
            self.assertEqual(w.run(offline=True),0)

    def test_new_shared_scope_or_other_product_claim_blocks_the_update(self):
        for conflict in ('shared','product'):
            with self.subTest(conflict=conflict),self.workspace() as w:
                w.run();w.query='next.vendor.example';w.clock+=timedelta(days=1);w.run()
                if conflict=='shared':w.config['shared-negatives']=['old.vendor.example'];w.save()
                else:w.servers.append('https://old.vendor.example/')
                before=w.snapshot()
                with self.assertRaises(Invalid):w.run()
                self.assertEqual(before,w.snapshot())

    def test_offline_check_rejects_invalid_historical_proofs(self):
        from loon_rules.generation import pipeline as lib
        with self.workspace() as w:
            w.run();w.query='next.vendor.example';w.clock+=timedelta(days=1);w.run()
            state=w.state()
            mutations=[lambda p:p.update(source='https://other.vendor.example/getBag?ix=3'),
                       lambda p:p.update(source=w.spec['source']+'&token=secret'),
                       lambda p:p.update({'accepted-at':'2099-01-01T00:00:00Z'}),
                       lambda p:p.update({'unexpected':'field'})]
            for mutate in mutations:
                changed=copy.deepcopy(state)
                mutate(changed['config-endpoint-history']['identity']['retained']['DOMAIN,old.vendor.example'])
                (w.root/'data/maintenance-state.json').write_text(json.dumps(changed))
                (w.root/'build/verification.md').write_text(lib.render_review(changed,w.entries))
                with self.subTest(mutate=mutate),self.assertRaises(Invalid):w.run(offline=True)

    def test_client_profile_history_keeps_a_valid_public_model_request(self):
        from loon_rules.generation import config_history
        from loon_rules.sources import profiles
        spec={'method':'ios-client-config','source':'https://updates.vendor.example/catalog',
              'config-source':'https://config.vendor.example/defaults','max-documents':4,
              'document':{'format':'plist-service-fields','identity':[{'path':['kind'],'equals':'location'}],
                          'url-paths':[['lookupURL']]}}
        today=datetime.now(timezone.utc).date()
        catalog={'PublicAssetSets':{'iOS':[{'ProductVersion':'27.1','SupportedDevices':['iPhone19,1'],
                  'PostingDate':str(today-timedelta(days=2)),'ExpirationDate':str(today+timedelta(days=30))}]}}
        plan=profiles.plan(spec,json.dumps(catalog));url=plan['documents'][0]['source']
        def record(host):
            raw=plistlib.dumps({'kind':'location','lookupURL':'https://'+host+'/query'}).decode()
            return profiles.read(spec,plan,{url:raw},())[1]
        old=record('old.vendor.example');current=record('next.vendor.example')
        checked=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        previous={'checked-at':checked,'expanded-inputs':{'location':old}}
        spec['max-documents']=8
        entries={'location':{'expand':spec}}
        retained,history=config_history.reconcile(entries,{'location':['DOMAIN,old.vendor.example']},
            {'location':['DOMAIN,next.vendor.example']},{'location':current},previous,checked_at=checked)
        self.assertEqual(retained,{'location':['DOMAIN,old.vendor.example']})
        self.assertEqual(history['location']['retained']['DOMAIN,old.vendor.example']['source'],url)
