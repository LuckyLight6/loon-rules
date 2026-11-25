from checks.source_fixtures import prepare_workspace
import json

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class RegistrySources(PublicSourceExamples):
    def recipe(self):
        return {'format':'json-service-urls','source':'https://registry.example/config.json',
                'paths':[['urls','*','url']],
                'identity':[{'path':['info','name'],'equals':'tool'}]}

    def document(self,host='files.vendor.example'):
        return {'info':{'name':'tool','version':'1.0','project_url':'https://project.other.example'},
                'urls':[{'url':'https://'+host+'/tool.whl'}],
                'releases':{'old':[{'url':'https://historical.other.example/old.whl'}]}}

    def test_download_fields_do_not_collect_project_links_or_historical_releases(self):
        recipe=self.recipe();doc=self.document()
        self.assertEqual(extract_rows(recipe,json.dumps(doc)),{'DOMAIN,files.vendor.example'})
        doc['urls'].append({'url':'https://new-cdn.other.example/tool.tar.gz'})
        self.assertEqual(extract_rows(recipe,json.dumps(doc)),
                         {'DOMAIN,files.vendor.example','DOMAIN,new-cdn.other.example'})

    def test_static_server_fields_can_contain_download_templates_only_in_the_path(self):
        recipe={**self.recipe(),'paths':[['dl'],['api']],'identity':[]}
        doc={'dl':'https://download.vendor.example/crates/{crate}/{version}/download',
             'api':'https://api.vendor.example','other':'https://unselected.other.example'}
        self.assertEqual(extract_rows(recipe,json.dumps(doc)),
                         {'DOMAIN,download.vendor.example','DOMAIN,api.vendor.example'})

    def test_identity_empty_arrays_and_missing_members_reject_partial_metadata(self):
        for doc in ({**self.document(),'info':{'name':'wrong'}},{**self.document(),'urls':[]},
                    {**self.document(),'urls':[{'url':'https://files.vendor.example/a'},{}]},
                    {**self.document(),'urls':{'url':'https://files.vendor.example/a'}}):
            with self.subTest(doc=doc),self.assertRaises(Invalid):extract_rows(self.recipe(),json.dumps(doc))

    def test_server_fields_reject_non_urls_private_hosts_and_parameters(self):
        for value in ('https://127.0.0.1/file','https://files.internal/file',
                      'https://reader@files.vendor.example/file','http://files.vendor.example/file',
                      'https://files.vendor.example:not-a-port/file','https://files.vendor.example:70000/file',
                      'https://files.vendor.example/file?credential=value','https://{tenant}.shared.example/file',3):
            doc=self.document();doc['urls'][0]['url']=value
            with self.subTest(value=value),self.assertRaises(Invalid):extract_rows(self.recipe(),json.dumps(doc))

    def test_a_valid_alternate_service_port_does_not_change_the_domain_rule(self):
        document = self.document()
        document['urls'][0]['url'] = 'https://files.vendor.example:8443/file.whl'
        self.assertEqual(extract_rows(self.recipe(), json.dumps(document)), {'DOMAIN,files.vendor.example'})

    def test_shared_storage_request_hosts_cannot_become_package_rules_from_a_file_path(self):
        doc=self.document();doc['urls'].append({'url':'https://storage.googleapis.com/vendor/file.whl'})
        with self.assertRaises(Invalid):
            extract_rows(self.recipe(),json.dumps(doc),shared_hosts=['storage.googleapis.com'])

    def test_url_inventory_rotations_keep_the_same_observation_and_dynamic_case_contract(self):
        from loon_rules.generation import inventories as inv
        entry={'mode':'compiled','inventory-refresh':True,'extract':[self.recipe()]}
        old=['DOMAIN,files.vendor.example'];new=['DOMAIN,new-cdn.other.example']
        source=self.recipe()['source']
        _,initial=inv.reconcile({'product':entry},{'product':old},{'product':old},
            {source:json.dumps(self.document())},{},0)
        held,first=inv.reconcile({'product':entry},{'product':old},{'product':new},
            {source:json.dumps(self.document('new-cdn.other.example'))},initial,3600)
        self.assertEqual(held['product'],old)
        held,last=inv.reconcile({'product':entry},{'product':old+new},{'product':new},
            {source:json.dumps(self.document('new-cdn.other.example'))},first,22*3600)
        self.assertEqual(held['product'],[]);self.assertEqual(last['product']['retired'],old)
        inv.verify_report({'product':entry},{'product':new},last)
        self.assertEqual(inv.routing_cases({'product':new},last),{'new-cdn.other.example':['product']})

    def test_published_artifact_hosts_are_kept_with_version_evidence_after_a_new_release(self):
        from loon_rules.generation import inventories as inv
        recipe={**self.recipe(),'revision-path':['info','version']}
        entry={'mode':'compiled','inventory-refresh':True,'inventory-retention':'published-artifacts','extract':[recipe]}
        source=recipe['source'];old=['DOMAIN,files.vendor.example'];new=['DOMAIN,new-cdn.other.example']
        _,initial=inv.reconcile({'product':entry},{'product':old},{'product':old},
            {source:json.dumps(self.document())},{},0)
        document=self.document('new-cdn.other.example');document['info']['version']='2.0'
        _,first=inv.reconcile({'product':entry},{'product':old},{'product':new},
            {source:json.dumps(document)},initial,3600)
        held,last=inv.reconcile({'product':entry},{'product':old+new},{'product':new},
            {source:json.dumps(document)},first,22*3600)
        self.assertEqual(held['product'],old);self.assertEqual(last['product']['retired'],[])
        proof=last['product']['artifact-hosts'][old[0]]
        self.assertEqual(proof,{'source':source,'revision':'1.0','first-seen':0})
        inv.verify_report({'product':entry},{'product':old+new},last)
        self.assertEqual(len(inv.routing_cases({'product':old+new},last)),2)

    def test_artifact_retention_needs_version_fields_and_cannot_forge_a_source_or_a_host(self):
        import copy
        from loon_rules.generation import inventories as inv
        recipe={**self.recipe(),'revision-path':['info','version']}
        entry={'mode':'compiled','inventory-refresh':True,'inventory-retention':'published-artifacts','extract':[recipe]}
        rows=['DOMAIN,files.vendor.example']
        _,report=inv.reconcile({'product':entry},{'product':rows},{'product':rows},
            {recipe['source']:json.dumps(self.document())},{},0)
        wrong=copy.deepcopy(report);wrong['product']['artifact-hosts'][rows[0]]['source']='https://wrong.example/'
        with self.assertRaises(Invalid):inv.verify_report({'product':entry},{'product':rows},wrong)
        with self.assertRaises(Invalid):inv.verify_report({'product':entry},{'product':[]},report)
        multiple=copy.deepcopy(entry)
        multiple['extract'].append({**recipe,'source':'https://another-registry.example/package.json'})
        with self.assertRaises(Invalid):inv.validate({'product':multiple})
        entry['extract']=[self.recipe()]
        with self.assertRaises(Invalid):inv.validate({'product':entry})

    def test_new_file_hosts_are_generated_and_tested_without_fixed_host_samples(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        entry={'id':'product','mode':'compiled','priority':30,'section':'service',
               'description':'包注册表','boundary':'注册表和文件','sources':[self.recipe()['source']],
               'include':['DOMAIN-SUFFIX,registry.example'],
               'extract':[{**self.recipe(),'revision-path':['info','version'],'protect-from-reject':True}],
               'inventory-refresh':True,'inventory-retention':'published-artifacts'}
        cfg={'schema-version':2,'entries':[entry],'critical':{'registry.example':['product']},
             'shared-negatives':['storage.shared.example'],'sections':[{'id':'service','title':'服务'}],
             'routing-bands':[{'start':30,'title':'服务'}]}
        documents={self.recipe()['source']:json.dumps(self.document())}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(cfg)
            (root/'config/catalog.json').write_text(json.dumps(cfg));(root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,entries))
            output=root/'rules'/lib.rule_filename(entry)
            output.write_text(lib.decorate(entry,['DOMAIN-SUFFIX,registry.example','DOMAIN,files.vendor.example'],None,'2026-11-20T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=documents.__getitem__):
                lib.run()
                doc=self.document();doc['urls'].append({'url':'https://new-cdn.other.example/tool.zip'})
                documents[self.recipe()['source']]=json.dumps(doc)
                lib.run();lib.run()
                before={p:p.read_bytes() for folder in ('rules','data')
                        for p in (root/folder).rglob('*') if p.is_file()}
                doc['urls'].append({'url':'https://storage.shared.example/vendor/tool.zip'})
                documents[self.recipe()['source']]=json.dumps(doc)
                with self.assertRaises(Invalid):lib.run()
                self.assertEqual(before,{p:p.read_bytes() for folder in ('rules','data')
                                         for p in (root/folder).rglob('*') if p.is_file()})
            self.assertIn('DOMAIN,new-cdn.other.example',lib.rules.read_rules(output.read_text()))
            self.assertNotIn('DOMAIN,storage.shared.example',lib.rules.read_rules(output.read_text()))
            report=json.loads((root/'data/maintenance-state.json').read_text())
            self.assertNotIn('storage.shared.example',report['functional-hosts'])
            self.assertNotIn('DOMAIN,storage.shared.example',report['service-inventories']['product']['observed'])
            self.assertNotIn('DOMAIN,storage.shared.example',report['service-inventories']['product']['artifact-hosts'])
            self.assertEqual(report['inventory-domain-cases'],2)
            self.assertEqual(lib.run(offline=True),0)
