from checks.source_fixtures import prepare_workspace
import copy
import json

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid


class InventoryLifecycle(PublicSourceExamples):
    def test_official_inventory_can_update_inside_a_managed_company_group(self):
        from loon_rules.generation import inventories as inventory
        source='https://auth.vendor.example/config'
        recipe={'source':source,'format':'json-service-urls','paths':[['servers','*']]}
        entry={'mode':'managed','official-hosts':True,'inventory-refresh':True,'official-inputs':[recipe]}
        entries={'company':entry};old='DOMAIN,old.accounts.vendor.example';new='DOMAIN,new.accounts.vendor.example'
        root='DOMAIN-SUFFIX,product.vendor.example'
        def data(host):return {source:json.dumps({'servers':['https://'+host+'/']})}
        _,first=inventory.reconcile(entries,{'company':[root,old]},{'company':[root,old]},
            data('old.accounts.vendor.example'),{},0)
        held,second=inventory.reconcile(entries,{'company':[root,old]},{'company':[root,new]},
            data('new.accounts.vendor.example'),first,100)
        self.assertEqual(held['company'],[old])
        held,last=inventory.reconcile(entries,{'company':[root,old,new]},{'company':[root,new]},
            data('new.accounts.vendor.example'),second,100+21*3600)
        self.assertEqual(held['company'],[])
        self.assertEqual(last['company']['retired'],[old])
        inventory.verify_report(entries,{'company':[root,new]},last)

    def fixture(self):
        recipe={'source':'https://api.vendor.example/meta','format':'service-domain-groups',
                'path':['domains'],'groups':['assets'],'protect-from-reject':True}
        entry={'mode':'compiled','inventory-refresh':True,'extract':[recipe]}
        rows=['DOMAIN,asset'+str(i)+'.vendor.example' for i in range(24)]
        def inputs(selected):return {recipe['source']:json.dumps({'domains':{'assets':[r.split(',')[1] for r in selected]}})}
        return {'product':entry},rows,inputs

    def test_retirement_needs_two_separated_observations_and_survives_unrelated_additions(self):
        from loon_rules.generation import inventories as inv
        entries,old,inputs=self.fixture()
        _,initial=inv.reconcile(entries,{'product':old},{'product':old},inputs(old),{},0)
        candidate=old[1:]
        kept,first=inv.reconcile(entries,{'product':old},{'product':candidate},inputs(candidate),initial,3600)
        self.assertEqual(kept['product'],old[:1]);self.assertEqual(first['product']['retired'],[])
        candidate+=['DOMAIN,new-asset.other.example']
        _,second=inv.reconcile(entries,{'product':old},{'product':candidate},inputs(candidate),first,7200)
        kept,last=inv.reconcile(entries,{'product':old},{'product':candidate},inputs(candidate),second,22*3600)
        self.assertEqual(kept['product'],[]);self.assertEqual(last['product']['retired'],old[:1])
        inv.verify_report(entries,{'product':candidate},last)
        too_early=copy.deepcopy(last);too_early['product']['last-read']=7200
        with self.assertRaises(Invalid):inv.verify_report(entries,{'product':candidate},too_early)

    def test_complete_service_inventories_require_withdrawal_from_every_declared_source(self):
        from loon_rules.generation import inventories as inv
        recipes=[{'source':'https://support.vendor.example/'+part,'format':'purpose-domain-lists',
                  'labels':['Required hosts:']} for part in ['application','account']]
        entries={'product':{'mode':'compiled','inventory-refresh':True,'extract':recipes}}
        account='DOMAIN,accounts.identity-provider.example';app='DOMAIN,app.vendor.example';other='DOMAIN,other.vendor.example'
        def document(rows):return '<p>Required hosts:</p><ul>'+''.join('<li>'+r.split(',')[1]+'</li>' for r in rows)+'</ul>'
        inputs={recipes[0]['source']:document([app,account]),recipes[1]['source']:document([other,account])}
        before=[app,account,other];data={'product':before}
        _,report=inv.reconcile(entries,data,data,inputs,{},0)
        inputs[recipes[0]['source']]=document([app])
        kept,state=inv.reconcile(entries,data,data,inputs,report,3600)
        self.assertEqual(kept['product'],[])
        self.assertIn(account,state['product']['observed'])
        inputs[recipes[1]['source']]=document([other]);candidate={'product':[app,other]}
        kept,state=inv.reconcile(entries,data,candidate,inputs,state,7200)
        self.assertEqual(kept['product'],[account])
        kept,state=inv.reconcile(entries,data,candidate,inputs,state,23*3600)
        self.assertEqual(kept['product'],[])
        self.assertEqual(state['product']['retired'],[account])
        inv.verify_report(entries,candidate,state)

    def test_a_gap_in_observation_restarts_the_timer_and_reappearing_hosts_cancel_it(self):
        from loon_rules.generation import inventories as inv
        entries,old,inputs=self.fixture()
        _,initial=inv.reconcile(entries,{'product':old},{'product':old},inputs(old),{},0)
        _,first=inv.reconcile(entries,{'product':old},{'product':old[1:]},inputs(old[1:]),initial,3600)
        kept,late=inv.reconcile(entries,{'product':old},{'product':old[1:]},inputs(old[1:]),first,5*86400)
        self.assertEqual(kept['product'],old[:1]);self.assertEqual(late['product']['retired'],[])
        _,back=inv.reconcile(entries,{'product':old},{'product':old},inputs(old),late,5*86400+3600)
        self.assertEqual(back['product']['first-absent'],{})

    def test_only_previous_official_exact_rows_are_eligible_not_supplements_or_wildcards(self):
        from loon_rules.generation import inventories as inv
        from loon_rules.generation import pipeline as lib
        entries,old,inputs=self.fixture();supplement='DOMAIN,supplement.other.example'
        _,initial=inv.reconcile(entries,{'product':old+[supplement]},{'product':old+[supplement]},inputs(old),{},0)
        candidate=old[1:]
        kept,first=inv.reconcile(entries,{'product':old+[supplement]},{'product':candidate},inputs(candidate),initial,3600)
        self.assertNotIn(supplement,first['product']['retired'])
        with self.assertRaises(Invalid):lib.guard_coverage('product',old+[supplement],candidate+kept['product'])

    def test_current_exact_assets_supply_routing_cases_that_disappear_with_a_confirmed_retirement(self):
        from loon_rules.generation import inventories as inv
        entries,old,inputs=self.fixture()
        _,report=inv.reconcile(entries,{'product':old},{'product':old},inputs(old),{},0)
        self.assertEqual(inv.routing_cases({'product':old},report),{r.split(',')[1]:['product'] for r in old})
        fixed={'critical':{'manual.other.example':['manual']}}
        combined,count=inv.with_cases(fixed,{'product':old},report)
        self.assertEqual(count,len(old));self.assertEqual(fixed,{'critical':{'manual.other.example':['manual']}})
        self.assertEqual(combined['critical']['manual.other.example'],['manual'])
        with self.assertRaises(Invalid):
            inv.with_cases({'critical':{old[0].split(',')[1]:['different-product']}},{'product':old},report)
        _,first=inv.reconcile(entries,{'product':old},{'product':old[1:]},inputs(old[1:]),report,3600)
        self.assertIn(old[0].split(',')[1],inv.routing_cases({'product':old},first))
        _,retired=inv.reconcile(entries,{'product':old},{'product':old[1:]},inputs(old[1:]),first,22*3600)
        self.assertNotIn(old[0].split(',')[1],inv.routing_cases({'product':old[1:]},retired))

    def test_suffix_compaction_does_not_hide_explicit_source_hosts_from_routing_checks(self):
        from loon_rules.generation import inventories as inv
        entries,old,inputs=self.fixture();data={'product':['DOMAIN-SUFFIX,vendor.example']}
        _,report=inv.reconcile(entries,data,data,inputs(old),{},0)
        inv.verify_report(entries,data,report)
        cases=inv.routing_cases(data,report)
        self.assertEqual(cases,{r.split(',')[1]:['product'] for r in old})
        host=old[0].split(',')[1];cfg={'critical':{host:['product'],'manual.other.example':['manual']}}
        combined,count=inv.with_cases(cfg,data,report)
        self.assertEqual(count,24)
        self.assertEqual(len(combined['critical']),25)

    def test_json_document_tracks_only_the_selected_product_and_region_fields(self):
        from loon_rules.generation import inventories as inv
        from loon_rules.sources.inputs import extract_rows
        recipe={'source':'https://support.vendor.example/api/articles/123.json',
                'format':'json-document','body-path':['article','body'],
                'identity':[{'path':['article','id'],'equals':123}],
                'document':{'format':'product-domain-statements','paragraph-contains':['AI hosts:'],
                            'code-only':True,'value-after':'AI hosts:','annotation':'for China','part':'other'}}
        entry={'mode':'compiled','inventory-refresh':True,'extract':[recipe]}
        entries={'product':entry}
        def body(host):
            return json.dumps({'article':{'id':123,'body':
                '<p>AI hosts: <code>'+host+'</code> and <code>api.china.vendor.example</code> for China.</p>'}})
        first=body('api.global.vendor.example');second=body('api.new-provider.example')
        initial=sorted(extract_rows(recipe,first));candidate=sorted(extract_rows(recipe,second))
        _,report=inv.reconcile(entries,{'product':initial},{'product':initial},{recipe['source']:first},{},0)
        self.assertEqual(report['product']['observed'],initial)
        held,updated=inv.reconcile(entries,{'product':initial},{'product':candidate},
                                   {recipe['source']:second},report,3600)
        self.assertEqual(held['product'],initial)
        self.assertEqual(updated['product']['observed'],candidate)
        self.assertEqual(inv.inputs(entry)[0]['document'],recipe['document'])
        inv.verify_report(entries,{'product':candidate+held['product']},updated)
        cases=inv.routing_cases({'product':candidate+held['product']},updated)
        self.assertEqual(set(cases),{'api.global.vendor.example','api.new-provider.example'})
        self.assertNotIn('api.china.vendor.example',cases)

    def test_inventory_policy_and_offline_evidence_cannot_reclassify_unconfirmed_rows_as_retired(self):
        from loon_rules.generation import inventories as inv
        entries,old,inputs=self.fixture()
        _,report=inv.reconcile(entries,{'product':old},{'product':old},inputs(old),{},0)
        inv.verify_report(entries,{'product':old},report)
        fake=copy.deepcopy(report);fake['product']['retired']=old[:1]
        with self.assertRaises(Invalid):inv.verify_report(entries,{'product':old},fake)
        for change in ({'mode':'managed'},{'inventory-refresh':'yes'},
                       {'extract':[{'source':'x','format':'rules','exact':['api.vendor.example']}]}):
            invalid=copy.deepcopy(entries);invalid['product'].update(change)
            with self.subTest(change=change),self.assertRaises(Invalid):inv.validate(invalid)

    def test_scheduled_generation_retains_then_retires_a_confirmed_inventory_withdrawal(self):
        from contextlib import redirect_stdout
        from datetime import datetime,timezone
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        entries,old,inputs=self.fixture();entry=entries['product']
        entry.update(id='product',priority=30,section='development',description='开发平台',boundary='完整服务清单',
                     sources=[entry['extract'][0]['source']])
        supplement='DOMAIN,supplement.other.example';entry['include']=[supplement]
        cfg={'schema-version':2,'entries':[entry],'critical':{'supplement.other.example':['product']},
             'shared-negatives':[],'sections':[{'id':'development','title':'开发'}]}
        urls=inputs(old);now=datetime(2026,11,21,tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()),patch.object(lib,'datetime',wraps=datetime) as clock:
            clock.now.return_value=now
            root=prepare_workspace(tmp);(root/'rules').mkdir();declared=lib.validate_declarations(cfg)
            (root/'config/catalog.json').write_text(json.dumps(cfg));(root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,declared))
            output=root/'rules'/lib.rule_filename(entry)
            output.write_text(lib.decorate(entry,old+[supplement],None,'2026-11-20T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=urls.__getitem__):
                lib.run()
                urls.update(inputs(old[1:]));clock.now.return_value=now.replace(hour=1)
                lib.run();self.assertIn(old[0],lib.rules.read_rules(output.read_text()))
                clock.now.return_value=now.replace(hour=2);urls.update(inputs(old[1:]+['DOMAIN,new.other.example']))
                lib.run()
                clock.now.return_value=now.replace(hour=22);lib.run()
            self.assertNotIn(old[0],lib.rules.read_rules(output.read_text()))
            self.assertIn(supplement,lib.rules.read_rules(output.read_text()))
            self.assertIn('DOMAIN,new.other.example',lib.rules.read_rules(output.read_text()))
            self.assertEqual(lib.run(offline=True),0)
