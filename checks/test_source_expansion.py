from checks.source_fixtures import prepare_workspace
import copy
import json

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid


class ApiDirectoryExpansion(PublicSourceExamples):
    def fixture(self):
        spec={'method':'api-directory','source':'directory','title-prefixes':['Vendor Store '],
              'documents-base':'https://sources.vendor.example/apis/','max-documents':10}
        entries={'store':{'expand':spec}}
        def item(name,title,version='v1',preferred=True):
            return {'kind':'discovery#directoryItem','id':name+':'+version,'name':name,'version':version,
                    'title':title,'preferred':preferred}
        directory={'kind':'discovery#directoryList','discoveryVersion':'v1',
                   'items':[item('market','Vendor Store API'),item('market','Vendor Store API','v0',False),
                            item('unrelated','Another Product API')]}
        def api(name,host,version='v1'):
            return json.dumps({'kind':'discovery#restDescription','discoveryVersion':'v1','name':name,
                               'version':version,'rootUrl':'https://'+host+'/'})
        return entries,directory,api

    def test_new_product_and_preferred_version_are_discovered_without_declaring_api_ids(self):
        from loon_rules.sources import expansion as source_expansion
        entries,directory,api=self.fixture()
        urls={'https://sources.vendor.example/apis/market.v1.json':api('market','api.vendor.example')}
        rows,report,downloaded=source_expansion.collect(entries,{'directory':json.dumps(directory)},urls.__getitem__)
        self.assertEqual(rows,{'store':['DOMAIN,api.vendor.example']})
        self.assertEqual(len(downloaded),1)
        directory['items'].append({'kind':'discovery#directoryItem','id':'newapi:v1','name':'newapi',
                                   'version':'v1','title':'Vendor Store New Service API','preferred':True})
        urls['https://sources.vendor.example/apis/newapi.v1.json']=api('newapi','new.product.example')
        rows,report,downloaded=source_expansion.collect(entries,{'directory':json.dumps(directory)},urls.__getitem__)
        self.assertEqual(set(rows['store']),{'DOMAIN,api.vendor.example','DOMAIN,new.product.example'})
        self.assertEqual({d['name'] for d in report['store']['documents']},{'market','newapi'})

    def test_cross_product_claims_are_rejected_before_child_downloads(self):
        from loon_rules.sources import expansion as source_expansion
        entries,directory,_=self.fixture();entries['other']=copy.deepcopy(entries['store'])
        with self.assertRaises(Invalid):
            source_expansion.collect(entries,{'directory':json.dumps(directory)},
                                     lambda url:self.fail('must not fetch an ambiguous product'))

    def test_a_report_cannot_hide_an_endpoint_by_calling_it_shared_without_policy_evidence(self):
        from loon_rules.sources import expansion as source_expansion
        entries,directory,api=self.fixture()
        rows,report,_=source_expansion.collect(entries,{'directory':json.dumps(directory)},lambda u:api('market','api.vendor.example'))
        doc=report['store']['documents'][0];doc['shared-rows']=doc['rows'];doc['rows']=[]
        source_expansion.verify_report(entries,{'store':[]},report,shared_hosts={'api.vendor.example'})
        with self.assertRaises(Invalid):source_expansion.verify_report(entries,{'store':[]},report)

    def test_one_invalid_document_prevents_a_partial_product_result(self):
        from loon_rules.sources import expansion as source_expansion
        entries,directory,api=self.fixture()
        with self.assertRaises(Invalid):
            source_expansion.collect(entries,{'directory':json.dumps(directory)},lambda url:api('different','other.example'))

    def test_directory_report_must_match_product_identity_and_real_output(self):
        from loon_rules.sources import expansion as source_expansion
        entries,directory,api=self.fixture()
        rows,report,_=source_expansion.collect(entries,{'directory':json.dumps(directory)},
                                               lambda url:api('market','api.vendor.example'))
        source_expansion.verify_report(entries,rows,report)
        invalid=copy.deepcopy(report);invalid['store']['documents'][0]['source']='https://unexpected.example/api'
        with self.assertRaises(Invalid):source_expansion.verify_report(entries,rows,invalid)
        with self.assertRaises(Invalid):source_expansion.verify_report(entries,{'store':['DOMAIN,other.example']},report)

    def test_directory_identifiers_cannot_escape_the_declared_source_path(self):
        from loon_rules.sources import expansion as source_expansion
        entries,directory,_=self.fixture();directory['items'][0]['name']='../unexpected'
        with self.assertRaises(Invalid):
            source_expansion.collect(entries,{'directory':json.dumps(directory)},
                                     lambda url:self.fail('must not fetch an invalid path'))

    def test_subproducts_can_be_split_without_fetching_the_same_document_twice(self):
        from loon_rules.sources import expansion as source_expansion
        entries,directory,api=self.fixture()
        entries['store']['expand']['exclude-title-prefixes']=['Vendor Store Games ']
        entries['games']={'expand':{**entries['store']['expand'],'title-prefixes':['Vendor Store Games '],
                                   'exclude-title-prefixes':[]}}
        directory['items'].append({'kind':'discovery#directoryItem','id':'games:v1','name':'games',
                                   'version':'v1','title':'Vendor Store Games API','preferred':True})
        urls={'https://sources.vendor.example/apis/market.v1.json':api('market','shop.vendor.example'),
              'https://sources.vendor.example/apis/games.v1.json':api('games','games.vendor.example')}
        rows,report,downloaded=source_expansion.collect(entries,{'directory':json.dumps(directory)},urls.__getitem__)
        self.assertEqual(rows,{'store':['DOMAIN,shop.vendor.example'],'games':['DOMAIN,games.vendor.example']})
        self.assertEqual(len(downloaded),2)

    def test_scheduled_generation_admits_a_new_directory_api_and_preserves_it_on_the_next_run(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        entries,directory,api=self.fixture()
        entry={'id':'store','mode':'compiled','priority':30,'section':'service','description':'产品',
               'boundary':'专用 API','sources':['directory'],'expand':entries['store']['expand']}
        entry['expand']['protect-from-reject']=True
        ads={'id':'ads','mode':'managed','priority':20,'section':'privacy','description':'广告','boundary':'广告',
             'sources':['ads'],'kinds':['DOMAIN'],'flags':[],'license':'MIT','policy-hint':'reject'}
        cfg={'entries':[ads,entry],'detailed':['store'],'general':['ads'],'alternatives':[],
             'optional':[],'views':[],'critical':{'api.vendor.example':['store']},'shared-negatives':[],
             'sections':[{'id':'privacy','title':'隐私','from':20,'through':20},
                         {'id':'service','title':'服务','from':30,'through':30}]}
        urls={'directory':json.dumps(directory),
              'ads':'DOMAIN,new.product.example\nDOMAIN,ad.other.example',
              'https://sources.vendor.example/apis/market.v1.json':api('market','api.vendor.example')}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();(root/'config/catalog.json').write_text(json.dumps(cfg))
            (root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,{'store':entry,'ads':ads}))
            output=root/'rules'/lib.rule_filename(entry)
            output.write_text(lib.decorate(entry,['DOMAIN,api.vendor.example'],None,'2020-01-01T00:00:00Z'))
            adpath=root/'rules'/lib.rule_filename(ads)
            adpath.write_text(lib.decorate(ads,urls['ads'].splitlines(),None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=urls.__getitem__):
                lib.run()
                directory['items'].append({'kind':'discovery#directoryItem','id':'newapi:v1','name':'newapi',
                                           'version':'v1','title':'Vendor Store New API','preferred':True})
                urls['directory']=json.dumps(directory)
                urls['https://sources.vendor.example/apis/newapi.v1.json']=api('newapi','new.product.example')
                lib.run()
                lib.run()
            self.assertEqual(set(lib.rules.read_rules(output.read_text())),
                             {'DOMAIN,api.vendor.example','DOMAIN,new.product.example'})
            self.assertEqual(lib.rules.read_rules(adpath.read_text()),['DOMAIN,ad.other.example'])
            self.assertEqual(lib.run(offline=True),0)

    def test_complete_api_directories_rotate_hosts_and_keep_required_protection_during_observation(self):
        from contextlib import redirect_stdout
        from datetime import datetime,timedelta,timezone
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        entries,directory,api=self.fixture()
        spec={**entries['store']['expand'],'protect-from-reject':True,'versions':'published'}
        entry={'id':'store','mode':'compiled','priority':30,'section':'service','description':'产品',
               'boundary':'完整 API 端点','sources':['directory'],'expand':spec,'inventory-refresh':True}
        ads={'id':'ads','mode':'managed','priority':20,'section':'privacy','description':'广告','boundary':'广告',
             'sources':['ads'],'kinds':['DOMAIN'],'flags':[],'license':'MIT','policy-hint':'reject'}
        cfg={'schema-version':2,'entries':[ads,entry],'critical':{},'shared-negatives':[],
             'sections':[{'id':'privacy','title':'隐私'},{'id':'service','title':'服务'}]}
        source='https://sources.vendor.example/apis/market.v1.json'
        legacy='https://sources.vendor.example/apis/market.v0.json'
        urls={'directory':json.dumps(directory),source:api('market','old.provider.example'),
              legacy:api('market','legacy.provider.example','v0'),
              'ads':'DOMAIN,old.provider.example\nDOMAIN,new.provider.example\nDOMAIN,legacy.provider.example\nDOMAIN,ad.other.example'}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()),\
                patch.object(lib,'datetime',wraps=datetime) as clock:
            start=datetime(2026,11,21,tzinfo=timezone.utc);clock.now.return_value=start
            root=prepare_workspace(tmp);(root/'rules').mkdir();declared=lib.validate_declarations(cfg)
            (root/'config/catalog.json').write_text(json.dumps(cfg));(root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,declared))
            path=root/'rules'/lib.rule_filename(entry);adpath=root/'rules'/lib.rule_filename(ads)
            path.write_text(lib.decorate(entry,['DOMAIN,old.provider.example'],None,'2020-01-01T00:00:00Z'))
            adpath.write_text(lib.decorate(ads,urls['ads'].splitlines(),None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=urls.__getitem__):
                lib.run()
                urls[source]=api('market','new.provider.example')
                clock.now.return_value=start+timedelta(hours=1);lib.run()
                self.assertEqual(set(lib.rules.read_rules(path.read_text())),
                                 {'DOMAIN,old.provider.example','DOMAIN,new.provider.example','DOMAIN,legacy.provider.example'})
                report=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(report['inventory-domain-cases'],3)
                self.assertTrue({'old.provider.example','new.provider.example'}<=set(report['functional-hosts']))
                self.assertEqual(lib.rules.read_rules(adpath.read_text()),['DOMAIN,ad.other.example'])
                self.assertEqual(lib.run(offline=True),0)
                before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
                urls[source]=api('wrong-product','wrong.other.example')
                with self.assertRaises(Invalid):lib.run()
                self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*') if p.is_file()})
                urls[source]=api('market','new.provider.example')
                clock.now.return_value=start+timedelta(hours=22);lib.run()
                self.assertEqual(set(lib.rules.read_rules(path.read_text())),
                                 {'DOMAIN,new.provider.example','DOMAIN,legacy.provider.example'})
                report=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(report['service-inventories']['store']['retired'],['DOMAIN,old.provider.example'])
                self.assertEqual(report['inventory-domain-cases'],2)
                self.assertNotIn('old.provider.example',report['functional-hosts'])
                self.assertEqual(lib.run(offline=True),0)
                directory['items']=[item for item in directory['items'] if item['version']!='v0']
                urls['directory']=json.dumps(directory)
                clock.now.return_value=start+timedelta(hours=44);lib.run()
                self.assertIn('DOMAIN,legacy.provider.example',lib.rules.read_rules(path.read_text()))
                clock.now.return_value=start+timedelta(hours=65);lib.run()
                self.assertEqual(lib.rules.read_rules(path.read_text()),['DOMAIN,new.provider.example'])
                self.assertEqual(lib.run(offline=True),0)

    def test_directory_inventory_needs_observed_api_hosts_and_cannot_be_artifact_retention(self):
        from loon_rules.generation import inventories as inventory
        from loon_rules.sources import expansion as source_expansion
        entries,_,_=self.fixture()
        entry={'mode':'compiled','expand':{**entries['store']['expand'],'versions':'published'},'inventory-refresh':True}
        inventory.validate({'store':entry})
        with self.assertRaises(Invalid):inventory.validate({'store':{**entry,'expand':entries['store']['expand']}})
        with self.assertRaises(Invalid):inventory.validate({'store':{**entry,'inventory-retention':'published-artifacts'}})
        with self.assertRaises(Invalid):inventory.validate({'store':{**entry,'expand':{'method':'next-page'}}})
        with self.assertRaises(Invalid):inventory.reconcile({'store':entry},{'store':[]},{'store':[]},{},{},0)
        old=['DOMAIN,api.vendor.example'];new=['DOMAIN,moved.provider.example']
        _,report=inventory.reconcile({'store':entry},{'store':old},{'store':old},{},{},0,expanded_rows={'store':old})
        inventory.verify_report({'store':entry},{'store':old+new},report,expanded_rows={'store':old})
        with self.assertRaises(Invalid):
            inventory.verify_report({'store':entry},{'store':old+new},report,expanded_rows={'store':new})
        for bad in (['DOMAIN-SUFFIX,vendor.example'],['DOMAIN,*.vendor.example'],['DOMAIN,api.internal']):
            with self.subTest(bad=bad),self.assertRaises(Invalid):
                inventory.reconcile({'store':entry},{'store':old},{'store':old},{},{},0,expanded_rows={'store':bad})
        with self.assertRaises(Invalid):
            inventory.reconcile({'store':entry},{'store':old},{'store':old},{},{},0,
                                expanded_rows={'store':old},shared_hosts=['api.vendor.example'])
        self.assertEqual(source_expansion.inventory_rows({'example-page':{'method':'next-page',
                         'documents':[{'rows':old}]}}),{})

    def test_published_versions_include_nonpreferred_servers_without_changing_existing_callers(self):
        from loon_rules.sources import expansion as source_expansion
        entries,directory,api=self.fixture();spec=entries['store']['expand']
        self.assertEqual([r['version'] for r in source_expansion.plan(spec,json.dumps(directory))],['v1'])
        spec['versions']='published'
        self.assertEqual({r['version'] for r in source_expansion.plan(spec,json.dumps(directory))},{'v0','v1'})
        urls={'https://sources.vendor.example/apis/market.'+version+'.json':api('market',version+'.provider.example',version)
              for version in ('v0','v1')}
        rows,report,_=source_expansion.collect(entries,{'directory':json.dumps(directory)},urls.__getitem__)
        self.assertEqual(set(rows['store']),{'DOMAIN,v0.provider.example','DOMAIN,v1.provider.example'})
        source_expansion.verify_report(entries,rows,report)
        directory['items'].append(directory['items'][0])
        with self.assertRaises(Invalid):source_expansion.plan(spec,json.dumps(directory))
        with self.assertRaises(Invalid):source_expansion.plan({**spec,'versions':'unknown'},json.dumps(directory))
