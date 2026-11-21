from checks.source_fixtures import prepare_workspace
import copy
import json
import plistlib
from types import SimpleNamespace
from unittest.mock import patch

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid


class PublicServiceBags(PublicSourceExamples):
    def spec(self):
        return {'method':'public-plist-bag','source':'https://config.vendor.example/getBag?ix=3',
                'protect-from-reject':True,
                'document':{'format':'plist-service-fields','data-path':['bag'],
                    'identity':[{'path':['bag-test-key'],'equals':'normal'}],
                    'records':{'paths':[[]],'typed-url-patterns':['id-(?!validation-cert$)[A-Za-z-]+'],
                               'required-fields':['id-register','id-query']}}}

    def body(self,query='query.vendor.example'):
        data={'bag-test-key':'normal','id-register':'https://identity.vendor.example/register',
              'id-query':'https://'+query+'/query',
              'id-query-refresh-interval':1200,
              'id-validation-cert':'http://legacy.vendor.example/cert',
              'metrics-url':'https://metrics.unselected.example/events'}
        return plistlib.dumps({'bag':plistlib.dumps(data),'signature':b'public example'}).decode()

    def test_request_mode_only_allows_a_public_numeric_bag_index(self):
        from loon_rules.sources import transport as maintain
        source=self.spec()['source'];called=[]
        def run(command,**kwargs):called.append(command[-1]);return SimpleNamespace(returncode=0,stdout=b'config')
        with patch.object(maintain.subprocess,'run',side_effect=run):
            with self.assertRaises(Invalid):maintain.download(source)
            self.assertEqual(maintain.download(source,public_bag=True),'config')
        self.assertEqual(called,[source])
        for url in (source+'&token=secret',source+'&ix=4',source.replace('ix=3','ix=secret'),
                    source.replace('ix=3','serial=3'),source.replace('https://','http://'),source+'#fragment'):
            with self.subTest(url=url),patch.object(maintain.subprocess,'run',side_effect=AssertionError('no request')):
                with self.assertRaises(Invalid):maintain.download(url,public_bag=True)
        with self.assertRaises(Invalid):maintain.source_url(source,public_bag=True,public_profile=True)

    def test_only_selected_inner_fields_are_read_and_new_fields_do_not_need_hostname_declarations(self):
        from loon_rules.sources.inputs import extract_rows
        recipe=self.spec()['document'];body=self.body()
        self.assertEqual(extract_rows(recipe,body),{'DOMAIN,identity.vendor.example','DOMAIN,query.vendor.example'})
        outer=plistlib.loads(body.encode());inner=plistlib.loads(outer['bag'])
        inner['id-future-service']='https://new.other-provider.example/service'
        outer['bag']=plistlib.dumps(inner)
        self.assertIn('DOMAIN,new.other-provider.example',extract_rows(recipe,plistlib.dumps(outer).decode()))
        for value in (b'not a plist',b'[]',plistlib.dumps({'bag-test-key':'normal'}),'not bytes'):
            changed={**outer,'bag':value}
            with self.subTest(value=type(value).__name__),self.assertRaises(Invalid):
                extract_rows(recipe,plistlib.dumps(changed).decode())
        inner['id-register']='https://user:example@identity.vendor.example/'
        with self.assertRaises(Invalid):extract_rows(recipe,plistlib.dumps({**outer,'bag':plistlib.dumps(inner)}).decode())
        inner['id-register']=False
        with self.assertRaises(Invalid):extract_rows(recipe,plistlib.dumps({**outer,'bag':plistlib.dumps(inner)}).decode())

    def test_plan_report_and_shared_boundaries_are_checked(self):
        from loon_rules.sources import bags as source_bags
        spec=self.spec();record=source_bags.plan(spec)
        rows,report=source_bags.read(spec,record,{spec['source']:self.body()},())
        self.assertEqual(set(rows),{'DOMAIN,identity.vendor.example','DOMAIN,query.vendor.example'})
        source_bags.verify(spec,report)
        changed=copy.deepcopy(report);changed['documents'].append(changed['documents'][0])
        with self.assertRaises(Invalid):source_bags.verify(spec,changed)
        changed=copy.deepcopy(spec);changed['document']['records']['required-fields']=['id-different']
        with self.assertRaises(Invalid):source_bags.verify(changed,report)
        rows,report=source_bags.read(spec,record,{spec['source']:self.body()},['query.vendor.example'])
        self.assertEqual(rows,['DOMAIN,identity.vendor.example'])
        self.assertEqual(report['documents'][0]['shared-rows'],['DOMAIN,query.vendor.example'])
        with self.assertRaises(Invalid):source_bags.validate({**spec,'source':spec['source']+'&token=secret'})
        for source in ('https://127.0.0.1/bag?ix=3','https://config.vendor.example:8080/bag?ix=3'):
            with self.subTest(source=source),self.assertRaises(Invalid):source_bags.validate({**spec,'source':source})

    def test_refresh_follows_fields_into_detail_view_cases_and_preserves_all_outputs_on_failure(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from loon_rules.generation import pipeline as lib
        spec=self.spec();source=spec['source'];body=self.body();requests=[]
        entry={'id':'identity','priority':30,'section':'service','mode':'compiled','description':'身份服务',
               'boundary':'公开服务字段','sources':[source],'include':['DOMAIN-SUFFIX,vendor.example'],'expand':spec}
        view={'id':'services-all','priority':29,'section':'service','mode':'view','description':'服务合集',
              'boundary':'服务','member-selection':{'section':'service'}}
        config={'schema-version':2,'entries':[entry,view],'sections':[{'id':'service','title':'服务'}],
                'critical':{'legacy.vendor.example':['identity']},'shared-negatives':[]}
        def read(url,**kwargs):
            requests.append((url,kwargs))
            if url!=source or kwargs!={'public_bag':True}:raise AssertionError('unexpected public request')
            return body
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(config)
            (root/'config/catalog.json').write_text(json.dumps(config));(root/'docs/rules.md').write_text(lib.render_index(config,entries))
            (root/'config/endpoint-contracts.json').write_text('[]')
            for e in entries.values():
                (root/'rules'/lib.rule_filename(e)).write_text(lib.decorate(e,entry['include'],None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=read):
                lib.run();self.assertEqual(requests,[(source,{'public_bag':True})])
                state=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(state['expanded-domain-cases'],2)
                self.assertEqual(state['business-domain-cases'],3)
                self.assertEqual(lib.run(offline=True),0)
                missing=copy.deepcopy(state)
                missing.pop('expanded-domain-cases');missing.pop('business-domain-cases')
                (root/'data/maintenance-state.json').write_text(json.dumps(missing))
                (root/'build/verification.md').write_text(lib.render_review(missing,entries))
                with self.assertRaises(Invalid):lib.run(offline=True)
                (root/'data/maintenance-state.json').write_text(json.dumps(state))
                (root/'build/verification.md').write_text(lib.render_review(state,entries))
                body=self.body('new.other-provider.example')
                lib.run();self.assertEqual(lib.run(offline=True),0)
                for e in entries.values():
                    self.assertIn('DOMAIN,new.other-provider.example',(root/'rules'/lib.rule_filename(e)).read_text())
                state=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertIn('new.other-provider.example',state['functional-hosts'])
                body=plistlib.dumps({}).decode()
                before={p:p.read_text() for p in root.rglob('*') if p.is_file()}
                with self.assertRaises(Invalid):lib.run()
                self.assertEqual(before,{p:p.read_text() for p in root.rglob('*') if p.is_file()})
