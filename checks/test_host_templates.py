from checks.source_fixtures import prepare_workspace
import copy
import json

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid


class PublishedHostTemplates(PublicSourceExamples):
    def spec(self):
        return {'method':'host-templates','source':'https://support.brand.example/network',
                'registry-source':'https://www.brand.example/domains','brand-label':'brand',
                'placeholder':'[country]','purposes':['Authentication'],'ports':'TCP/443',
                'max-documents':1,'protect-from-reject':True}

    def document(self):
        return ('<table><tr><th>Destination Host</th><th>Ports</th><th>Purpose</th></tr>'
                '<tr><td>accounts.brand.com<br>accounts.brand.[country]</td><td>TCP/443</td>'
                '<td>Authentication<br>Use a published country domain</td></tr>'
                '<tr><td>unrelated.other.example</td><td>TCP/443</td><td>Downloads</td></tr></table>')

    def inputs(self):
        spec=self.spec()
        return {spec['source']:self.document(),spec['registry-source']:'.brand.com\n.brand.co.uk\n'}

    def collect(self,inputs=None,spec=None):
        from loon_rules.sources import expansion as source_expansion
        spec=spec or self.spec();entry={'expand':spec}
        return source_expansion.collect({'account':entry},inputs or self.inputs(),
                                        lambda url:self.fail('both public inputs were already read'))

    def test_published_template_and_registry_generate_new_regions_without_domain_declarations(self):
        from loon_rules.sources import expansion as source_expansion
        rows,report,downloaded=self.collect()
        self.assertEqual(rows['account'],['DOMAIN,accounts.brand.co.uk','DOMAIN,accounts.brand.com'])
        self.assertEqual(downloaded,{})
        inputs=self.inputs();inputs[self.spec()['registry-source']]+='.brand.net\n'
        rows,report,_=self.collect(inputs)
        self.assertIn('DOMAIN,accounts.brand.net',rows['account'])
        source_expansion.verify_report({'account':{'expand':self.spec()}},rows,report)
        forged=copy.deepcopy(report);forged['account']['templates']=['other.brand.[country]']
        with self.assertRaises(Invalid):
            source_expansion.verify_report({'account':{'expand':self.spec()}},rows,forged)

    def test_missing_purposes_unknown_placeholders_and_unrelated_registries_stop_the_update(self):
        spec=self.spec()
        for document in (self.document().replace('Authentication','Advertising'),
                         self.document().replace('[country]','[region]'),
                         self.document().replace('accounts.brand.[country]','*.brand.com'),
                         self.document().replace('accounts.brand.com<br>','other.brand.com<br>')):
            inputs=self.inputs();inputs[spec['source']]=document
            with self.subTest(document=document[-100:]),self.assertRaises(Invalid):self.collect(inputs)
        for registry in ('.brand.com.evil.example\n','.other.com\n','.brand.github.io\n',
                         '.brand.com\n.brand.github.io\n',''):
            inputs=self.inputs();inputs[spec['registry-source']]=registry
            with self.subTest(registry=registry),self.assertRaises(Invalid):self.collect(inputs)

    def test_hidden_tables_cannot_supply_templates_and_shared_exact_hosts_stay_separate(self):
        from loon_rules.sources import expansion as source_expansion
        spec=self.spec();inputs=self.inputs()
        fake='<template>'+self.document().replace('accounts.brand.','hidden.brand.')+'</template>'
        inputs[spec['source']]=fake+inputs[spec['source']]
        rows,report,_=source_expansion.collect({'account':{'expand':spec}},inputs,lambda url:self.fail(url),
                                             shared_hosts=['accounts.brand.com'])
        self.assertEqual(rows['account'],['DOMAIN,accounts.brand.co.uk'])
        self.assertEqual(report['account']['documents'][0]['shared-rows'],['DOMAIN,accounts.brand.com'])
        source_expansion.verify_report({'account':{'expand':spec}},rows,report,shared_hosts=['accounts.brand.com'])
        with self.assertRaises(Invalid):source_expansion.verify_report({'account':{'expand':spec}},rows,report)

    def test_template_schema_rejects_empty_or_wrongly_typed_scope_conditions(self):
        from loon_rules.sources import templates as source_templates
        for changes in ({'brand-label':3},{'placeholder':False},{'source':None},{'registry-source':'http://brand.example/domains'},
                        {'purposes':'Authentication'},{'purposes':[]},{'purposes':['']},{'ports':''},
                        {'max-documents':True}):
            with self.subTest(changes=changes),self.assertRaises(Invalid):source_templates.validate({**self.spec(),**changes})

    def test_two_products_share_one_registry_read_without_sharing_their_host_namespace(self):
        from loon_rules.sources import expansion as source_expansion
        first=self.spec();second={**first,'source':'https://support.brand.example/downloads',
                                  'purposes':['File downloads']}
        first_document=self.document();second_document=first_document.replace('accounts.brand.','files.brand.')
        second_document=second_document.replace('Authentication','File downloads')
        entries={'account':{'expand':first},'downloads':{'expand':second}}
        calls=[]
        def read(url):
            calls.append(url)
            self.assertEqual(url,first['registry-source'])
            return '.brand.com\n.brand.co.uk\n'
        rows,report,_=source_expansion.collect(entries,
            {first['source']:first_document,second['source']:second_document},read)
        self.assertEqual(calls,[first['registry-source']])
        self.assertEqual(rows['downloads'],['DOMAIN,files.brand.co.uk','DOMAIN,files.brand.com'])
        self.assertEqual(rows['account'],['DOMAIN,accounts.brand.co.uk','DOMAIN,accounts.brand.com'])
        source_expansion.verify_report(entries,rows,report)

    def test_complete_refresh_updates_views_cases_and_observes_a_removed_region(self):
        from contextlib import redirect_stdout
        from datetime import datetime,timedelta,timezone
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        spec=self.spec()
        issuer='https://accounts.brand.com/.well-known/openid-configuration'
        entry={'id':'account','mode':'compiled','priority':30,'section':'service','description':'地区登录',
               'boundary':'官方模板与官方地区注册域','sources':[spec['source'],spec['registry-source'],issuer],
               'extract':[{'source':issuer,'format':'openid-discovery','issuer':'https://accounts.brand.com',
                           'fields':['token_endpoint'],'roots':['brand.com'],'exclude':[],'protect-from-reject':True}],
               'expand':spec,'inventory-refresh':True,'selection':'detailed'}
        view={'id':'service-all','mode':'view','priority':29,'section':'service',
              'description':'合集','boundary':'登录','members':['account'],'fallback':True}
        config={'schema-version':2,'entries':[view,entry],'critical':{'accounts.brand.com':['account']},
                'shared-negatives':['accounts.brand.com'],
                'sections':[{'id':'service','title':'服务'}]}
        inputs=self.inputs()
        inputs[issuer]=json.dumps({'issuer':'https://accounts.brand.com','token_endpoint':'https://accounts.brand.com/token'})
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()),\
                patch.object(lib,'datetime',wraps=datetime) as clock:
            start=datetime(2026,11,21,tzinfo=timezone.utc);clock.now.return_value=start
            root=prepare_workspace(tmp);(root/'rules' / 'loon').mkdir(parents=True, exist_ok=True);entries=lib.validate_declarations(config)
            (root/'config/catalog.json').write_text(json.dumps(config));(root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(config,entries))
            for item in (entry,view):
                (root/'rules' / 'loon'/lib.rule_filename(item)).write_text(lib.decorate(entries[item['id']],
                    ['DOMAIN,accounts.brand.com','DOMAIN,accounts.brand.co.uk'],None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=inputs.__getitem__):
                lib.run()
                review=(root/'build/verification.md').read_text()
                self.assertIn('## 地区主机怎样随来源更新？',review)
                self.assertIn('accounts.brand.[country]',review)
                inputs[spec['registry-source']]+='.brand.net\n';lib.run();lib.run()
                for item in (entry,view):
                    self.assertIn('DOMAIN,accounts.brand.net',lib.rules.read_rules(
                        (root/'rules' / 'loon'/lib.rule_filename(item)).read_text()))
                report=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(report['inventory-domain-cases'],2)
                self.assertEqual(report['business-domain-cases'],3)
                self.assertIn('accounts.brand.net',report['functional-hosts'])
                inputs[spec['registry-source']]='.brand.com\n.brand.net\n'
                clock.now.return_value=start+timedelta(hours=1);lib.run()
                report=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(report['service-inventories']['account']['retained'],['DOMAIN,accounts.brand.co.uk'])
                before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
                inputs[spec['source']]=self.document().replace('Authentication','Different purpose')
                with self.assertRaises(Invalid):lib.run()
                self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*') if p.is_file()})
                inputs[spec['source']]=self.document()
                clock.now.return_value=start+timedelta(hours=22);lib.run()
                self.assertEqual(lib.run(offline=True),0)
                report=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(report['service-inventories']['account']['retired'],['DOMAIN,accounts.brand.co.uk'])
