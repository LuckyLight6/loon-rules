from checks.source_fixtures import prepare_workspace
import copy
import json
import plistlib
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from unittest.mock import patch

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid


class PublicClientProfiles(PublicSourceExamples):
    def spec(self):
        return {'method':'ios-client-config','source':'https://updates.vendor.example/catalog',
                'config-source':'https://config.vendor.example/defaults','max-documents':8,
                'document':{'format':'plist-service-fields',
                    'identity':[{'path':['com.vendor.GEO'],'contains-keys':['CountryProviders']}],
                    'records':{'paths':[['com.vendor.GEO'],['com.vendor.GEO','CountryProviders','*']],
                               'url-fields':['CLAppleLocationServer','GEOVoltaireResourceManifestURL'],
                               'url-patterns':['CL[A-Za-z]+TileServer'],
                               'required-fields':['CLAppleLocationServer']}}}

    def catalog(self):
        today=datetime.now(timezone.utc).date()
        def release(version,devices,expires=30):
            return {'ProductVersion':version,'SupportedDevices':devices,
                    'PostingDate':str(today-timedelta(days=2)),
                    'ExpirationDate':str(today+timedelta(days=expires))}
        return {'PublicAssetSets':{'iOS':[
            release('27.1',['iPhone19,1','iPad18,1','Watch12,1']),
            release('26.7',['iPhone14,1']),
            release('15.8',['iPhone7,1'],-1),
            release('27.1',['iPhone19,1'])]}}

    def configuration(self,host='lookup.vendor.example'):
        return {'com.vendor.GEO':{'CountryProviders':{
            'CN':{'CLAppleLocationServer':'https://'+host+'/lookup',
                  'CLWifiTileServer':'https://tiles.vendor.example/tile',
                  'CLAppleCollectionServer_Trace':'https://telemetry.vendor.example/upload'},
            'KR':{'GEOVoltaireResourceManifestURL':'https://manifest.vendor.example/config%{DEVICE_QUERY}'},
            'DE':{'FeatureEnabled':False}},'SomeOtherURL':'https://unrelated.vendor.example/'}}

    def test_downloader_requires_explicit_public_profile_mode_and_rejects_secret_queries(self):
        from loon_rules.sources import transport as maintain
        url='https://config.vendor.example/defaults?os=ios&os_version=27.1&hardware=iPhone19%2C1'
        requests=[]
        def run(command,**kwargs):requests.append(command[-1]);return SimpleNamespace(returncode=0,stdout=b'public config')
        with patch.object(maintain.subprocess,'run',side_effect=run):
            with self.assertRaises(Invalid):maintain.download(url)
            self.assertEqual(maintain.download(url,public_profile=True),'public config')
        self.assertEqual(requests,[url])
        bad=[url+'&token=private',url+'&os=ios',url.replace('27.1','credential-value'),
             url.replace('iPhone19%2C1','serial-unique-value'),url.replace('https://','http://'),
             url.replace('config.vendor','user:secret@config.vendor'),url+'#private']
        with patch.object(maintain.subprocess,'run',side_effect=AssertionError('must not request')):
            for value in bad:
                with self.subTest(value=value),self.assertRaises(Invalid):maintain.download(value,public_profile=True)

    def test_record_fields_add_new_regions_and_tile_types_without_a_hostname_list(self):
        from loon_rules.sources.inputs import extract_rows
        recipe=self.spec()['document'];body=self.configuration()
        expected={'DOMAIN,lookup.vendor.example','DOMAIN,tiles.vendor.example','DOMAIN,manifest.vendor.example'}
        self.assertEqual(extract_rows(recipe,plistlib.dumps(body).decode()),expected)
        body['com.vendor.GEO']['CountryProviders']['JP']={'CLFutureTileServer':'https://new-tile.vendor.example/x'}
        self.assertEqual(extract_rows(recipe,plistlib.dumps(body).decode()),expected|{'DOMAIN,new-tile.vendor.example'})
        for change in (lambda b:b['com.vendor.GEO']['CountryProviders'].update(CN='not an object'),
                       lambda b:b['com.vendor.GEO']['CountryProviders']['CN'].update(CLAppleLocationServer=False),
                       lambda b:b.update({'com.vendor.GEO':{'unexpected':{}}})):
            candidate=self.configuration();change(candidate)
            with self.subTest(change=change),self.assertRaises(Invalid):extract_rows(recipe,plistlib.dumps(candidate).decode())

    def test_catalog_drives_all_current_phone_tablet_profiles_and_checks_missing_documents(self):
        from loon_rules.sources import profiles as source_profiles
        spec=self.spec();catalog=self.catalog();record=source_profiles.plan(spec,json.dumps(catalog))
        self.assertEqual({(d['version'],d['device']) for d in record['documents']},
                         {('27.1','iPhone19,1'),('27.1','iPad18,1'),('26.7','iPhone14,1')})
        inputs={d['source']:plistlib.dumps(self.configuration()).decode() for d in record['documents']}
        rows,report=source_profiles.read(spec,record,inputs,())
        self.assertEqual(set(rows),{'DOMAIN,lookup.vendor.example','DOMAIN,tiles.vendor.example','DOMAIN,manifest.vendor.example'})
        source_profiles.verify(spec,report)
        selected,shared=source_profiles.read(spec,record,inputs,['tiles.vendor.example'])
        self.assertNotIn('DOMAIN,tiles.vendor.example',selected)
        self.assertTrue(all(doc['shared-rows']==['DOMAIN,tiles.vendor.example'] for doc in shared['documents']))
        missing=copy.deepcopy(report);missing['documents'].pop()
        with self.assertRaises(Invalid):source_profiles.verify(spec,missing)
        changed=copy.deepcopy(spec);changed['document']['records']['url-fields']=['DifferentServer']
        with self.assertRaises(Invalid):source_profiles.verify(changed,report)
        catalog['PublicAssetSets']['iOS'][0]['SupportedDevices'].append('iPhone99,1')
        expanded=source_profiles.plan(spec,json.dumps(catalog))
        self.assertIn(('27.1','iPhone99,1'),{(d['version'],d['device']) for d in expanded['documents']})
        with self.assertRaises(Invalid):source_profiles.plan({**spec,'max-documents':2},json.dumps(catalog))

    def test_corrupt_selected_profiles_are_rejected_instead_of_silently_disappearing(self):
        from loon_rules.sources import profiles as source_profiles
        for mutate in (lambda r:r.update(PostingDate=r['PostingDate'].replace('-','')),
                       lambda r:r.update(SupportedDevices=['iPhone19,1?token=private']),
                       lambda r:r.update(ProductVersion='27.1&token=private')):
            catalog=self.catalog();mutate(catalog['PublicAssetSets']['iOS'][0])
            with self.subTest(mutate=mutate),self.assertRaises(Invalid):
                source_profiles.plan(self.spec(),json.dumps(catalog))

    def test_record_selector_changes_do_not_reuse_another_fields_retirement_timer(self):
        from loon_rules.generation import inventories as inventory
        recipe={'format':'plist-service-fields','source':'document',
                'identity':[{'path':['kind'],'equals':'endpoints'}],
                'records':{'paths':[['hosts']],'url-fields':['Primary']}}
        entry={'mode':'compiled','inventory-refresh':True,'extract':[recipe]}
        entries={'service':entry};old='DOMAIN,old.vendor.example';new='DOMAIN,new.vendor.example'
        body={'kind':'endpoints','hosts':{'Primary':'https://old.vendor.example/','Secondary':'https://new.vendor.example/'}}
        _,first=inventory.reconcile(entries,{'service':[old]},{'service':[old]},
            {'document':plistlib.dumps(body).decode()},{},0)
        body['hosts']['Primary']='https://new.vendor.example/'
        held,second=inventory.reconcile(entries,{'service':[old]},{'service':[new]},
            {'document':plistlib.dumps(body).decode()},first,100)
        self.assertEqual(held,{'service':[old]})
        changed=copy.deepcopy(entries);changed['service']['extract'][0]['records']['url-fields']=['Secondary']
        _,third=inventory.reconcile(changed,{'service':[old,new]},{'service':[new]},
            {'document':plistlib.dumps(body).decode()},second,100+21*3600)
        self.assertEqual(third['service']['retired'],[])

    def test_expansion_hosts_are_checked_even_when_compacted_under_a_parent_rule(self):
        from loon_rules.sources import expansion as source_expansion
        config={'critical':{'legacy.vendor.example':['location']}}
        data={'location':['DOMAIN-SUFFIX,vendor.example']}
        report={'location':{'documents':[{'rows':['DOMAIN,new.vendor.example'],'shared-rows':[]}]}}
        runtime,count=source_expansion.with_cases(config,data,report)
        self.assertEqual(runtime['critical'],{'legacy.vendor.example':['location'],'new.vendor.example':['location']})
        self.assertEqual(count,1)
        self.assertEqual(config,{'critical':{'legacy.vendor.example':['location']}})
        with self.assertRaises(Invalid):source_expansion.with_cases(config,{'location':[]},report)

    def test_refresh_discovers_versions_and_hosts_and_checks_their_actual_routing(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from urllib.parse import parse_qs,urlsplit
        from loon_rules.generation import pipeline as lib
        spec=self.spec();catalog=self.catalog();body=self.configuration('dynamic.service.vendor.example')
        entry={'id':'location','priority':30,'section':'service','mode':'compiled','description':'定位',
               'boundary':'公开定位用途','sources':[spec['source'],spec['config-source']],
               'include':['DOMAIN-SUFFIX,service.vendor.example'],'expand':spec}
        view={'id':'services-all','priority':25,'section':'service','mode':'view','description':'服务合集',
              'boundary':'服务','member-selection':{'section':'service'}}
        config={'schema-version':2,'entries':[entry,view],'sections':[{'id':'service','title':'服务'}],
                'critical':{'legacy.service.vendor.example':['location']},'shared-negatives':[]}
        allowed={('27.1','iPhone19,1'),('27.1','iPad18,1'),('26.7','iPhone14,1')}
        unavailable=set()
        def read(url,**kwargs):
            if url==spec['source']:return json.dumps(catalog)
            args=parse_qs(urlsplit(url).query);profile=(args.get('os_version',[''])[0],args.get('hardware',[''])[0])
            if url.split('?')[0]!=spec['config-source'] or profile not in allowed or kwargs!={'public_profile':True}:
                raise AssertionError('unexpected public request')
            if profile in unavailable:raise Invalid('unavailable public configuration')
            return plistlib.dumps(body).decode()
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir()
            def save():
                entries=lib.validate_declarations(config)
                (root/'config/catalog.json').write_text(json.dumps(config));(root/'docs/rules.md').write_text(lib.render_index(config,entries))
                return entries
            entries=save();(root/'config/endpoint-contracts.json').write_text('[]')
            for e,rows in ((entry,entry['include']),(view,entry['include'])):
                (root/'rules'/lib.rule_filename(e)).write_text(lib.decorate(entries[e['id']],rows,None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=read):
                lib.run()
                state=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(state['expanded-domain-cases'],3)
                self.assertEqual(state['business-domain-cases'],4)
                self.assertEqual(lib.run(offline=True),0)
                catalog['PublicAssetSets']['iOS'][0]['SupportedDevices'].append('iPhone99,1')
                allowed.add(('27.1','iPhone99,1'))
                body['com.vendor.GEO']['CountryProviders']['CN']['CLAppleLocationServer']='https://next.service.vendor.example/new'
                lib.run();self.assertEqual(lib.run(offline=True),0)
                state=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(len(state['expanded-inputs']['location']['documents']),4)
                self.assertTrue(all('DOMAIN,next.service.vendor.example' in doc['rows']
                                    for doc in state['expanded-inputs']['location']['documents']))
                unavailable.add(('27.1','iPhone99,1'))
                snapshot={p:p.read_text() for p in root.rglob('*') if p.is_file()}
                with self.assertRaises(Invalid):lib.run()
                self.assertEqual(snapshot,{p:p.read_text() for p in root.rglob('*') if p.is_file()})
                unavailable.clear()
                config['entries'].append({'id':'other','priority':20,'section':'service','mode':'compiled',
                    'description':'其他产品','boundary':'其他产品的专用主机','sources':['https://other.vendor.example/network'],
                    'include':['DOMAIN,next.service.vendor.example']})
                save();snapshot={p:p.read_text() for p in root.rglob('*') if p.is_file()}
                with self.assertRaises(Invalid):lib.run()
                self.assertEqual(snapshot,{p:p.read_text() for p in root.rglob('*') if p.is_file()})
