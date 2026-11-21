from checks.source_fixtures import prepare_workspace
import copy
import json

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid


class ProductPageExpansion(PublicSourceExamples):
    def fixture(self, api='api.product.example', build='first'):
        spec={'method':'next-page','source':'https://product.example/apis/workflow','page':'/apis/workflow',
              'asset-roots':['cdn.example'],'request-labels':['接口请求：','查询结果'],'max-documents':1}
        asset='https://static.cdn.example/assets'
        source=asset+'/_next/static/chunks/pages/apis/workflow-'+build+'.js'
        initial={'page':spec['page'],'assetPrefix':asset,'buildId':build}
        html=('<script src="https://tracker.other.example/noise.js"></script><script src="'+source+'"></script>'
              '<script id="__NEXT_DATA__" type="application/json">'+json.dumps(initial)+'</script>')
        script=('debug="https://noise.other.example/api";'
                '(0,N.jsx)("h3",{children:"接口请求："}),(0,N.jsx)(Example,{value:"https://'+api+'/generate",isDark:true}),'
                '(0,N.jsx)("h3",{children:"查询结果"}),(0,N.jsx)(Example,{value:"https://'+api+'/status",isDark:true})')
        return spec,html,{source:script}

    def test_selected_page_asset_and_request_examples_are_read_without_other_scripts(self):
        from loon_rules.sources import expansion as source_expansion
        spec,html,inputs=self.fixture()
        rows,report,read=source_expansion.collect({'product':{'expand':spec}},
            {spec['source']:html},inputs.__getitem__)
        self.assertEqual(rows,{'product':['DOMAIN,api.product.example','DOMAIN,static.cdn.example']})
        self.assertEqual(read,inputs)
        self.assertEqual(report['product']['method'],'next-page')
        source_expansion.verify_report({'product':{'expand':spec}},rows,report)

    def test_hash_and_server_changes_follow_the_page_without_fixed_urls(self):
        from loon_rules.sources import expansion as source_expansion
        for build,api in [('first','api.product.example'),('unlisted','new-api.product.example')]:
            spec,html,inputs=self.fixture(api,build)
            rows,_,_=source_expansion.collect({'product':{'expand':spec}},{spec['source']:html},inputs.__getitem__)
            self.assertIn('DOMAIN,'+api,rows['product'])

    def test_internationalized_api_names_are_normalized_and_private_addresses_are_rejected(self):
        from loon_rules.sources import expansion as source_expansion
        spec,html,inputs=self.fixture(api='模型.product.example')
        rows,report,_=source_expansion.collect({'product':{'expand':spec}},{spec['source']:html},inputs.__getitem__)
        self.assertIn('DOMAIN,'+'模型'.encode('idna').decode()+'.product.example',rows['product'])
        source_expansion.verify_report({'product':{'expand':spec}},rows,report)
        spec,html,inputs=self.fixture(api='127.0.0.1')
        with self.assertRaises(Invalid):
            source_expansion.collect({'product':{'expand':spec}},{spec['source']:html},inputs.__getitem__)

    def test_missing_role_wrong_page_untrusted_assets_and_duplicate_page_data_fail(self):
        from loon_rules.sources import expansion as source_expansion
        for changed in ('role','page','asset','duplicate'):
            with self.subTest(changed=changed):
                spec,html,inputs=self.fixture()
                if changed=='role':inputs={k:v.replace('查询结果','普通链接') for k,v in inputs.items()}
                if changed=='page':html=html.replace('"/apis/workflow"','"/other"')
                if changed=='asset':html=html.replace('static.cdn.example','127.0.0.1')
                if changed=='duplicate':html+=html
                with self.assertRaises(Invalid):
                    source_expansion.collect({'product':{'expand':spec}},{spec['source']:html},inputs.__getitem__)

    def test_wrong_or_missing_api_evidence_cannot_pass_offline_verification(self):
        from loon_rules.sources import expansion as source_expansion
        spec,html,inputs=self.fixture();entries={'product':{'expand':spec}}
        rows,report,_=source_expansion.collect(entries,{spec['source']:html},inputs.__getitem__)
        for changed in ('body','role','source'):
            with self.subTest(changed=changed):
                evidence=copy.deepcopy(report);data=copy.deepcopy(rows)
                if changed=='body':data['product']=['DOMAIN,static.cdn.example']
                if changed=='role':evidence['product']['documents'][0]['roles'].pop('查询结果')
                if changed=='source':evidence['product']['documents'][0]['source']='https://tracker.other.example/a.js'
                with self.assertRaises(Invalid):source_expansion.verify_report(entries,data,evidence)

    def test_scheduled_refresh_follows_a_new_page_file_and_keeps_the_last_good_outputs_on_failure(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        spec,html,inputs=self.fixture()
        spec['protect-from-reject']=True
        entry={'id':'product','mode':'compiled','priority':20,'section':'service','description':'产品',
               'boundary':'网页资源与 API','sources':[spec['source']],'expand':spec}
        cfg={'schema-version':2,'entries':[entry],'critical':{'api.product.example':['product']},
             'shared-negatives':[],'sections':[{'id':'service','title':'产品'}]}
        urls={spec['source']:html,**inputs}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(cfg)
            (root/'config/catalog.json').write_text(json.dumps(cfg));(root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,entries))
            path=root/'rules'/lib.rule_filename(entry)
            path.write_text(lib.decorate(entry,['DOMAIN,api.product.example'],None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=urls.__getitem__):
                lib.run()
                _,new_html,new_inputs=self.fixture(build='second')
                new_inputs={k:v.replace('api.product.example/status','new-api.product.example/status') for k,v in new_inputs.items()}
                urls.update(new_inputs);urls[spec['source']]=new_html
                lib.run();lib.run()
                self.assertIn('DOMAIN,new-api.product.example',lib.rules.read_rules(path.read_text()))
                self.assertEqual(lib.run(offline=True),0)
                before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
                urls.update({k:v.replace('查询结果','ordinary link') for k,v in new_inputs.items()})
                with self.assertRaises(Invalid):lib.run()
                self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*') if p.is_file()})
