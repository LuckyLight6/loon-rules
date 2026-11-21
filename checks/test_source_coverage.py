from checks.source_fixtures import prepare_workspace
import copy
import json

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid


class ProjectionCoverage(PublicSourceExamples):
    def fixture(self):
        source='https://rules.public.example/product.list'
        entries={'product':{'mode':'compiled','priority':30,'projection':[
                     {'source':source,'roots':['product.example'],'exact':['known.shared.example']}]},
                 'other':{'mode':'compiled','priority':40},
                 'privacy':{'mode':'managed','priority':20,'policy-hint':'reject'},
                 'fallback':{'mode':'compiled','priority':90,'fallback':True}}
        text='\ufeff# Published product rules\n'+'\n'.join(['DOMAIN-SUFFIX,product.example','DOMAIN-SUFFIX,known.shared.example',
                        'DOMAIN-SUFFIX,friend.example','DOMAIN-SUFFIX,unassigned.example',
                        'DOMAIN,cloud.example','DOMAIN,unknown.unmatched.example',
                        'DOMAIN,unrelated.employer.example','DOMAIN,ads.example',
                        'PROCESS-NAME,not-a-domain-program','DOMAIN-WILDCARD,*.github.io'])
        data={'product':['DOMAIN-SUFFIX,product.example','DOMAIN,known.shared.example'],
              'other':['DOMAIN-SUFFIX,friend.example'],'privacy':['DOMAIN,ads.example'],
              'fallback':['DOMAIN-SUFFIX,unassigned.example']}
        selected={'product':{source:{'DOMAIN-SUFFIX,product.example','DOMAIN,known.shared.example'}}}
        return source,entries,text,data,selected

    def audit(self,entries,text,data,selected,**kwargs):
        from loon_rules.sources import coverage as source_coverage
        source=next(iter(selected['product']))
        return source_coverage.audit(entries,data,{source:text},order=['privacy','product','other','fallback'],
            selected=selected,shared_suffixes={'cloud.example'},
            exemptions={source:{'DOMAIN,unrelated.employer.example'}},**kwargs)

    def test_each_publisher_scope_has_one_explanation_without_exporting_unknown_candidates(self):
        from loon_rules.sources import coverage as source_coverage
        source,entries,text,data,selected=self.fixture()
        report=self.audit(entries,text,data,selected);state=report[source]
        self.assertEqual(state['domain-scopes'],9)
        self.assertEqual(state['selected-scopes'],2)
        self.assertEqual(state['narrowed-scopes'],1)
        self.assertEqual(state['product-scopes'],2)
        self.assertEqual(state['other-products'],{'other':1})
        self.assertEqual(state['fallback-scopes'],1)
        self.assertEqual(state['privacy-scopes'],1)
        self.assertEqual(state['shared-scopes'],2)
        self.assertEqual(state['declared-exclusions'],1)
        self.assertEqual(state['outside-selection'],1)
        self.assertEqual(state['other-lines'],1)
        self.assertNotIn('unknown.unmatched.example',json.dumps(report))
        self.assertNotIn('unrelated.employer.example',json.dumps(report))
        source_coverage.verify_report(entries,report)
        forged=copy.deepcopy(report);forged[source]['outside-selection']+=1
        with self.assertRaises(Invalid):source_coverage.verify_report(entries,forged)
        forged=copy.deepcopy(report);forged[source]['candidates']=['private.company.example']
        with self.assertRaises(Invalid):source_coverage.verify_report(entries,forged)
        changed=copy.deepcopy(entries);changed['product']['projection'][0]['roots']=['different.example']
        with self.assertRaises(Invalid):source_coverage.verify_report(changed,report)
        forged=copy.deepcopy(report);forged[source].update(state='invalid',**{'other-products':{}})
        for field in source_coverage.COUNTS:forged[source][field]=0
        with self.assertRaises(Invalid):source_coverage.verify_report(entries,forged)

    def test_selected_product_scopes_cannot_silently_disappear_into_a_fallback(self):
        _,entries,text,data,selected=self.fixture();data['product']=[]
        data['fallback'].append('DOMAIN-SUFFIX,example')
        with self.assertRaises(Invalid):self.audit(entries,text,data,selected)
        _,entries,text,data,selected=self.fixture()
        entries['privacy']['fallback']=True
        data['privacy'].append('DOMAIN-SUFFIX,example')
        # A privacy decision is still visible, and required endpoint protection is checked separately.
        state=self.audit(entries,text,data,selected)
        self.assertTrue(state)

    def test_publisher_subdomains_require_whole_scope_coverage_not_an_apex_probe(self):
        _,entries,text,data,selected=self.fixture()
        data['other']=['DOMAIN,friend.example']
        report=self.audit(entries,text,data,selected)
        self.assertEqual(next(iter(report.values()))['outside-selection'],2)
        data['other'].append('DOMAIN-WILDCARD,*.friend.example')
        report=self.audit(entries,text,data,selected)
        self.assertEqual(next(iter(report.values()))['other-products'],{'other':1})

    def test_missing_or_malformed_domain_source_cannot_appear_to_pass_coverage(self):
        from loon_rules.sources import coverage as source_coverage
        source,entries,text,data,selected=self.fixture()
        with self.assertRaises(Invalid):
            self.audit(entries,text+'\nDOMAIN-WILDCARD,',data,selected)
        with self.assertRaises(Invalid):
            source_coverage.audit(entries,data,{},order=list(entries),selected=selected)

    def test_compilation_records_the_effective_projection_including_regional_namespaces(self):
        from loon_rules.generation import pipeline as lib
        entry={'id':'regional','projection':[{'source':'feed','roots':['scholar.brand.com'],
                'parent-domains-source':'domains','brand-label':'brand','prefix-label':'scholar'}]}
        inputs={'feed':'DOMAIN,scholar.brand.com\nDOMAIN,scholar.brand.net\nDOMAIN,accounts.brand.net',
                'domains':'.brand.com\n.brand.net\n'}
        evidence={}
        actual=lib.compile_entry(entry,inputs,projection_rows=evidence)
        self.assertEqual(set(actual),{'DOMAIN,scholar.brand.com','DOMAIN,scholar.brand.net'})
        self.assertEqual(evidence,{'feed':set(actual)})

    def test_refresh_updates_all_source_counts_and_offline_checks_notice_changed_filters(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        source='https://rules.public.example/product.list'
        entry={'id':'product','mode':'compiled','priority':30,'section':'service','description':'产品',
               'boundary':'产品范围','sources':[source],
               'projection':[{'source':source,'roots':['vendor.example'],'domain-lines-only':True}]}
        config={'schema-version':2,'entries':[entry],'critical':{'api.vendor.example':['product']},
                'shared-negatives':[],'sections':[{'id':'service','title':'服务'}]}
        inputs={source:'DOMAIN,api.vendor.example\nDOMAIN,unknown.outside.example\nUNSUPPORTED,not-a-domain'}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(config)
            path=root/'rules'/lib.rule_filename(entry)
            path.write_text(lib.decorate(entry,['DOMAIN,api.vendor.example'],None,'2020-01-01T00:00:00Z'))
            (root/'config/catalog.json').write_text(json.dumps(config));(root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(config,entries))
            with patch.object(lib.transport,'download',side_effect=inputs.__getitem__):
                lib.run()
                report=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(report['projection-coverage'][source]['outside-selection'],1)
                self.assertEqual(report['projection-coverage'][source]['other-lines'],1)
                self.assertNotIn('unknown.outside.example',json.dumps(report))
                self.assertIn('产品来源有没有漏查',(root/'build/verification.md').read_text())
                self.assertNotIn('unknown.outside.example',(root/'build/verification.md').read_text())
                inputs[source]+='\n \t DOMAIN,new-api.vendor.example\n \ufeff \tDOMAIN,new-bom.vendor.example\n DOMAIN  , spaced.vendor.example'
                lib.run();lib.run()
                report=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(report['projection-coverage'][source]['selected-scopes'],4)
                self.assertIn('DOMAIN,new-api.vendor.example',lib.rules.read_rules(path.read_text()))
                self.assertIn('DOMAIN,new-bom.vendor.example',lib.rules.read_rules(path.read_text()))
                self.assertIn('DOMAIN,spaced.vendor.example',lib.rules.read_rules(path.read_text()))
                self.assertEqual(lib.run(offline=True),0)
                snapshot={p:p.read_text() for p in root.rglob('*') if p.is_file()}
                inputs[source]+='\nDOMAIN-WILDCARD,'
                with self.assertRaises(Invalid):lib.run()
                self.assertEqual(snapshot,{p:p.read_text() for p in root.rglob('*') if p.is_file()})
                changed=json.loads((root/'config/catalog.json').read_text())
                changed['entries'][0]['projection'][0]['roots']=['different.example']
                (root/'config/catalog.json').write_text(json.dumps(changed))
                with self.assertRaises(Invalid):lib.run(offline=True)

    def test_reclassification_requires_a_unique_product_with_the_same_source_and_whole_scope(self):
        from loon_rules.sources import coverage as source_coverage
        source='https://rules.public.example/publisher.list'
        entries={key:{'priority':n,'mode':'compiled','projection':[{'source':source}]}
                 for n,key in enumerate(('social','shared','other'),10)}
        previous={'social':['DOMAIN-SUFFIX,images.example']}
        data={'social':[], 'shared':['DOMAIN-SUFFIX,images.example'],'other':[]}
        selected={'shared':{source:set(data['shared'])}}
        result=source_coverage.reassignments(entries,previous,data,selected=selected,order=list(entries))
        self.assertEqual(result,{'social':{'DOMAIN-SUFFIX,images.example':{'owner':'shared','sources':[source]}}})
        source_coverage.verify_reassignments(entries,data,result,order=list(entries))
        data['shared']=['DOMAIN,images.example']
        self.assertEqual(source_coverage.reassignments(entries,previous,data,selected=selected,order=list(entries)),{})
        with self.assertRaises(Invalid):source_coverage.verify_reassignments(entries,data,result,order=list(entries))
        data['shared']=['DOMAIN-SUFFIX,images.example']
        selected['other']={source:set(data['shared'])};data['other']=data['shared'].copy()
        with self.assertRaisesRegex(Invalid,'多个'):
            source_coverage.reassignments(entries,previous,data,selected=selected,order=list(entries))
        data['other']=[];selected.pop('other')
        for flag,value in (('fallback',True),('policy-hint','reject')):
            changed=copy.deepcopy(entries);changed['shared'][flag]=value
            self.assertEqual(source_coverage.reassignments(changed,previous,data,selected=selected,order=list(entries)),{})
        changed=copy.deepcopy(entries);changed['shared']['projection'][0]['source']='https://different.example/list'
        with self.assertRaises(Invalid):source_coverage.verify_reassignments(changed,data,result,order=list(entries))

    def test_refresh_moves_a_source_scope_without_pinning_a_migration_domain_in_code(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        source='https://rules.public.example/publisher.list'
        social={'id':'social','mode':'compiled','priority':30,'section':'service','description':'社交',
                'boundary':'社交产品','sources':[source],
                'projection':[{'source':source,'roots':['social.example','images.example']}]}
        config={'schema-version':2,'entries':[social],'critical':{},'shared-negatives':[],
                'sections':[{'id':'service','title':'服务'}]}
        inputs={source:'DOMAIN-SUFFIX,social.example\nDOMAIN-SUFFIX,images.example'}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(config)
            path=root/'rules'/lib.rule_filename(social)
            path.write_text(lib.decorate(social,['DOMAIN-SUFFIX,social.example','DOMAIN-SUFFIX,images.example'],None,'2020-01-01T00:00:00Z'))
            (root/'config/endpoint-contracts.json').write_text('[]')
            def save():
                entries=lib.validate_declarations(config)
                (root/'config/catalog.json').write_text(json.dumps(config))
                (root/'docs/rules.md').write_text(lib.render_index(config,entries))
            save()
            with patch.object(lib.transport,'download',side_effect=inputs.__getitem__):
                lib.run()
                social['projection'][0]['roots'].remove('images.example')
                shared={**social,'id':'shared','priority':40,'description':'共用图片',
                        'projection':[{'source':source,'roots':['images.example']}]}
                config['entries'].append(shared);save();lib.run()
                report=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(report['projection-reassignments']['social']['DOMAIN-SUFFIX,images.example']['owner'],'shared')
                self.assertIn('哪些来源范围改了归属',(root/'build/verification.md').read_text())
                self.assertNotIn('images.example',path.read_text())
                self.assertEqual(lib.run(offline=True),0)
                lib.run();self.assertEqual(lib.run(offline=True),0)
                self.assertEqual(json.loads((root/'data/maintenance-state.json').read_text())['projection-reassignments'],{})
