"""A complete service bundle includes official shared dependencies with explicit route semantics."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from checks.source_fixtures import PublicSourceExamples,prepare_workspace
from loon_rules.generation import pipeline
from loon_rules.rules import Invalid,read_rules

class ServiceDependencies(PublicSourceExamples):
    def config(self):
        source='https://vendor.example/network'
        return {'schema-version':2,'sections':[{'id':'privacy','title':'隐私'},{'id':'ai','title':'AI'},{'id':'providers','title':'供应商'}],
            'entries':[
                {'id':'ads','mode':'managed','priority':10,'section':'privacy','selection':'detailed','policy-hint':'reject','description':'广告','boundary':'保护必需接口','sources':['https://lists.example/ads'],'kinds':['DOMAIN','DOMAIN-SUFFIX'],'flags':[],'license':'MIT'},
                {'id':'product-service-all','mode':'view','priority':15,'section':'ai','description':'服务与依赖合集','boundary':'与产品细分二选一，包含官方共享主机','members':['product'],
                 'dependency-inputs':[{'source':source,'format':'purpose-domain-lists','labels':['Required hosts'],'protect-from-reject':True}]},
                {'id':'product','mode':'compiled','priority':20,'section':'ai','selection':'detailed','policy-hint':'global','description':'产品','boundary':'自有服务','sources':[source],'include':['DOMAIN-SUFFIX,product.example']},
                {'id':'provider-service-all','mode':'view','priority':29,'section':'providers','description':'供应商合集','boundary':'替代供应商细分','members':['provider']},
                {'id':'provider','mode':'compiled','priority':30,'section':'providers','selection':'detailed','policy-hint':'global','description':'共用组件供应商','boundary':'多个产品共用','sources':[source],'include':['DOMAIN-SUFFIX,shared.example','DOMAIN,assets.sharedcdn.example']}],
            'critical':{'api.product.example':['product'],'login.shared.example':['provider']},
            'shared-negatives':['login.shared.example','storage.googleapis.com'],
            'view-cases':{'login.shared.example':['product-service-all','provider-service-all'],'api.product.example':['product-service-all']}}
    def page(self,extra=''):
        return '<p>Required hosts</p><ul><li>api.product.example</li><li>login.shared.example</li><li>assets.sharedcdn.example</li>'+extra+'</ul>'
    def test_full_pipeline_follows_new_dependencies_and_preserves_provider_ownership(self):
        cfg=self.config();inputs={'https://vendor.example/network':self.page(),'https://lists.example/ads':'DOMAIN,login.shared.example\nDOMAIN,ads.other.example\n'}
        with TemporaryDirectory() as temporary,patch.object(pipeline,'ROOT',prepare_workspace(temporary)),redirect_stdout(StringIO()):
            root=Path(temporary);(root/'rules/loon').mkdir(parents=True)
            entries=pipeline.validate_declarations(cfg)
            (root/'config/catalog.json').write_text(json.dumps(cfg));(root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(pipeline.render_index(cfg,entries))
            for key,entry in entries.items():
                rows={'ads':['DOMAIN,login.shared.example','DOMAIN,ads.other.example'],'product':['DOMAIN-SUFFIX,product.example'],
                      'provider':['DOMAIN-SUFFIX,shared.example','DOMAIN,assets.sharedcdn.example'],
                      'provider-service-all':['DOMAIN-SUFFIX,shared.example','DOMAIN,assets.sharedcdn.example'],'product-service-all':['DOMAIN-SUFFIX,product.example']}[key]
                (root/'rules/loon'/pipeline.rule_filename(entry)).write_text(pipeline.decorate(entry,rows,None,'2026-11-25T00:00:00Z'))
            with patch.object(pipeline.transport,'download',side_effect=inputs.__getitem__):
                pipeline.run()
                bundle=root/'rules/loon/015-product-service-all.lsr'
                self.assertIn('DOMAIN,login.shared.example',read_rules(bundle.read_text()))
                self.assertEqual(read_rules((root/'rules/loon/030-provider.lsr').read_text()),['DOMAIN-SUFFIX,shared.example','DOMAIN,assets.sharedcdn.example'])
                self.assertNotIn('login.shared.example',(root/'rules/loon/010-ads.lsr').read_text())
                inputs['https://vendor.example/network']=self.page('<li>unlisted.shared.example</li>')
                pipeline.run()
                self.assertIn('DOMAIN,unlisted.shared.example',read_rules(bundle.read_text()))
                pipeline.run(offline=True)
                good=bundle.read_bytes()
                inputs['https://vendor.example/network']=self.page('<li>storage.googleapis.com</li>')
                with self.assertRaises(Invalid):pipeline.run()
                self.assertEqual(bundle.read_bytes(),good)

    def test_complete_dependency_table_reads_new_purposes_and_rejects_partial_rows(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'purpose-url-table','section':'network','headers':['URL','Purpose'],'all-purposes':True}
        text='<h2 id="network">Network</h2><table><tr><th>URL</th><th>Purpose</th></tr><tr><td>https://first.shared.example/</td><td>Authentication</td></tr><tr><td>https://new.shared.example/</td><td>A future capability</td></tr></table>'
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,first.shared.example','DOMAIN,new.shared.example'})
        with self.assertRaises(Invalid):extract_rows(recipe,text.replace('<td>A future capability</td>',''))

    def test_documented_tenant_prefix_can_be_read_without_accepting_the_entire_cloud(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'purpose-url-table','section':'network','headers':['URL','Purpose'],
                'all-purposes':True,'allow-tenant-prefixes':True}
        text='<h2 id="network">Network</h2><table><tr><th>URL</th><th>Purpose</th></tr><tr><td>https://product-files-*.github.io/</td><td>Required downloads</td></tr></table>'
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN-WILDCARD,product-files-*.github.io'})
        with self.assertRaises(Invalid):extract_rows(recipe,text.replace('product-files-*','*'))
