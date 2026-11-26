import json
import plistlib

from checks.source_fixtures import PublicSourceExamples, prepare_workspace
from loon_rules.project import ROOT
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class PlistSources(PublicSourceExamples):
    def store_search_recipe(self):
        entries = json.loads((ROOT / 'config/catalog.json').read_text())['entries']
        store = next(entry for entry in entries if entry['id'] == 'apple-store-transactions')
        return next(recipe for recipe in store['extract'] if recipe['format'] == 'plist-service-fields')

    def store_search_document(self):
        return {
            'jingleDocType': 'initiateSessionSuccess',
            'jingleAction': 'mzInitiateSession',
            'apps-media-api-host': 'apps.vendor.example',
            'search': 'https://search.vendor.example/search',
            'searchHints': 'https://hints.vendor.example/hints',
            'p3-games-search': 'https://new-search.other-provider.example/search?media=software',
            'ampMusicAPIDomains': {'search': 'https://music.vendor.example/search'},
            'research': 'https://unrelated.vendor.example/',
            'searchAnalytics': 'https://stats.vendor.example/',
        }

    def test_store_search_fields_follow_new_endpoints_without_taking_music_or_metrics(self):
        actual = extract_rows(self.store_search_recipe(), self.encode(self.store_search_document()))
        self.assertEqual(actual, {
            'DOMAIN,apps.vendor.example', 'DOMAIN,search.vendor.example',
            'DOMAIN,hints.vendor.example', 'DOMAIN,new-search.other-provider.example',
        })

    def test_store_search_missing_required_fields_cannot_publish_only_the_media_api(self):
        document = self.store_search_document()
        document.pop('searchHints')
        with self.assertRaises(Invalid):
            extract_rows(self.store_search_recipe(), self.encode(document))

    def test_store_search_still_rejects_url_credentials(self):
        document = self.store_search_document()
        document['searchHints'] = 'https://user@hints.vendor.example/hints?media=software'
        with self.assertRaises(Invalid):
            extract_rows(self.store_search_recipe(), self.encode(document))

    def recipe(self):
        return {'format':'plist-service-fields',
                'source':'https://config.vendor.example/services.plist',
                'identity':[{'path':['documentType'],'equals':'serviceConfiguration'}],
                'host-paths':[['services','*']],
                'url-paths':[['accountURL']]}

    def document(self):
        return {'documentType':'serviceConfiguration',
                'services':{'default':'api.vendor.example','search':'search.other-provider.example'},
                'accountURL':'https://account.vendor.example/session',
                'metricsURL':'https://logs.unselected.example/events'}

    def encode(self,document):
        return plistlib.dumps(document).decode()

    def test_selected_server_fields_follow_new_hosts_and_mapping_members_without_name_filters(self):
        document=self.document()
        expected={'DOMAIN,api.vendor.example','DOMAIN,search.other-provider.example','DOMAIN,account.vendor.example'}
        self.assertEqual(extract_rows(self.recipe(),self.encode(document)),expected)
        document['services']['new-purpose']='new.api-provider.example'
        document['services']['default']='moved.other-provider.example'
        expected.remove('DOMAIN,api.vendor.example')
        expected.update({'DOMAIN,new.api-provider.example','DOMAIN,moved.other-provider.example'})
        self.assertEqual(extract_rows(self.recipe(),self.encode(document)),expected)

    def test_missing_identity_fields_and_empty_mappings_refuse_partial_configuration(self):
        for document in ({**self.document(),'documentType':'otherConfiguration'},
                         {**self.document(),'services':{}},
                         {k:v for k,v in self.document().items() if k!='accountURL'}):
            with self.subTest(document=document),self.assertRaises(Invalid):
                extract_rows(self.recipe(),self.encode(document))
        for identity in ([],None,'serviceConfiguration'):
            with self.subTest(identity=identity),self.assertRaises(Invalid):
                extract_rows({**self.recipe(),'identity':identity},self.encode(self.document()))

    def test_untrusted_host_fields_and_url_parameters_do_not_widen_service_scope(self):
        for host in ('127.0.0.1','files.internal','*.vendor.example','https://api.vendor.example',
                     ' api.vendor.example',3,False,[],{}):
            document=self.document();document['services']['default']=host
            with self.subTest(host=host),self.assertRaises(Invalid):extract_rows(self.recipe(),self.encode(document))
        for url in ('http://account.vendor.example','https://reader@account.vendor.example/',
                    'https://account.vendor.example/?token=value','https://account.vendor.example/#section'):
            document=self.document();document['accountURL']=url
            with self.subTest(url=url),self.assertRaises(Invalid):extract_rows(self.recipe(),self.encode(document))
        document=self.document();document['services']['shared']='storage.shared.example'
        with self.assertRaises(Invalid):
            extract_rows(self.recipe(),self.encode(document),shared_hosts=['storage.shared.example'])

    def test_duplicate_keys_invalid_paths_and_external_entities_fail_before_adoption(self):
        document=self.encode(self.document())
        duplicate=document.replace('<key>accountURL</key>',
                    '<key>documentType</key><string>serviceConfiguration</string><key>accountURL</key>')
        external=('<?xml version="1.0"?><!DOCTYPE plist [<!ENTITY external SYSTEM "file:///not-read">]>'
                  '<plist version="1.0"><dict><key>documentType</key><string>&external;</string></dict></plist>')
        for text in (duplicate,external,'<plist><dict>','[]'):
            with self.subTest(text=text[:80]),self.assertRaises(Invalid):extract_rows(self.recipe(),text)
        for paths in ([],['services'],[[]],[['services',1]],'services'):
            recipe={**self.recipe(),'host-paths':paths,'url-paths':[]}
            with self.subTest(paths=paths),self.assertRaises(Invalid):extract_rows(recipe,document)

    def test_new_fields_use_the_existing_service_withdrawal_and_dynamic_case_lifecycle(self):
        from loon_rules.generation import inventories as inventory
        recipe=self.recipe();entry={'mode':'compiled','inventory-refresh':True,'extract':[recipe]}
        source=recipe['source'];old_document=self.document()
        old=sorted(extract_rows(recipe,self.encode(old_document)))
        _,initial=inventory.reconcile({'product':entry},{'product':old},{'product':old},
                  {source:self.encode(old_document)},{},0)
        new_document=self.document();new_document['services']['default']='new.other-provider.example'
        new=sorted(extract_rows(recipe,self.encode(new_document)))
        held,first=inventory.reconcile({'product':entry},{'product':old},{'product':new},
                    {source:self.encode(new_document)},initial,3600)
        self.assertEqual(held['product'],['DOMAIN,api.vendor.example'])
        held,last=inventory.reconcile({'product':entry},{'product':old+new},{'product':new},
                    {source:self.encode(new_document)},first,22*3600)
        self.assertEqual(held['product'],[])
        self.assertEqual(last['product']['retired'],['DOMAIN,api.vendor.example'])
        inventory.verify_report({'product':entry},{'product':new},last)
        self.assertEqual(inventory.routing_cases({'product':new},last)['new.other-provider.example'],['product'])

    def test_refresh_updates_detail_view_and_cases_and_preserves_outputs_if_the_field_breaks(self):
        from contextlib import redirect_stdout
        from io import StringIO
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        source=self.recipe()['source']
        entry={'id':'product','mode':'compiled','priority':30,'section':'service',
               'description':'产品接口','boundary':'用途字段','sources':[source],
               'include':['DOMAIN-SUFFIX,vendor.example'],
               'extract':[{**self.recipe(),'protect-from-reject':True}],'inventory-refresh':True,'selection':'detailed'}
        view={'id':'service-all','mode':'view','priority':29,'section':'service','description':'合集',
              'boundary':'产品接口','members':['product']}
        cfg={'schema-version':2,'entries':[view,entry],'critical':{},
             'shared-negatives':['storage.shared.example'],'sections':[{'id':'service','title':'服务'}]}
        inputs={source:self.encode(self.document())}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules' / 'loon').mkdir(parents=True, exist_ok=True);entries=lib.validate_declarations(cfg)
            (root/'config/catalog.json').write_text(json.dumps(cfg));(root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,entries))
            for item in (entry,view):
                (root/'rules' / 'loon'/lib.rule_filename(item)).write_text(
                    lib.decorate(entries[item['id']],entry['include'],None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=inputs.__getitem__):
                lib.run()
                doc=self.document();doc['services']['new-function']='new.api-provider.example'
                inputs[source]=self.encode(doc)
                lib.run();lib.run()
                for item in (entry,view):
                    self.assertIn('DOMAIN,new.api-provider.example',
                        lib.rules.read_rules((root/'rules' / 'loon'/lib.rule_filename(item)).read_text()))
                report=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertIn('new.api-provider.example',report['functional-hosts'])
                self.assertNotIn('logs.unselected.example',report['functional-hosts'])
                self.assertEqual(report['inventory-domain-cases'],4)
                self.assertEqual(lib.run(offline=True),0)
                before={path:path.read_bytes() for path in root.rglob('*') if path.is_file()}
                doc.pop('accountURL');inputs[source]=self.encode(doc)
                with self.assertRaises(Invalid):lib.run()
                self.assertEqual(before,{path:path.read_bytes() for path in root.rglob('*') if path.is_file()})
