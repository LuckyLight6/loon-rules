from checks.source_fixtures import prepare_workspace
import copy
import json

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class DeveloperServiceSources(PublicSourceExamples):
    def test_domain_groups_follow_the_selected_services_and_ignore_ip_fields(self):
        recipe={'format':'service-domain-groups','path':['domains'],'groups':['website','packages']}
        doc={'domains':{'website':['*.vendor.example','*.github.io'],
                        'packages':['new-api.other.example','artifacts.github.io'],
                        'other':['wrong.example']},'packages':['192.0.2.0/24']}
        self.assertEqual(extract_rows(recipe,json.dumps(doc)),{
            'DOMAIN-WILDCARD,*.vendor.example','DOMAIN,new-api.other.example','DOMAIN,artifacts.github.io'})
        doc['domains']['packages'].append('new-region.new-provider.example')
        self.assertIn('DOMAIN,new-region.new-provider.example',extract_rows(recipe,json.dumps(doc)))

    def test_missing_or_malformed_service_groups_do_not_produce_a_partial_result(self):
        recipe={'format':'service-domain-groups','path':['domains'],'groups':['website','packages']}
        document={'domains':{'website':['*.vendor.example'],'packages':['api.vendor.example']}}
        for bad in ({},[],['192.0.2.1'],['api.internal.corp'],['vendor.example,PROXY']):
            doc=copy.deepcopy(document);doc['domains']['packages']=bad
            with self.subTest(bad=bad),self.assertRaises(Invalid):extract_rows(recipe,json.dumps(doc))
        with self.assertRaises(Invalid):extract_rows(recipe,json.dumps({'domains':{'website':['vendor.example']}}))

    def url_table(self,rows):
        return '<h2 id="connections">Connections</h2><table>'+''.join(
            '<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows)+'</table>'

    def test_purpose_urls_keep_exact_websockets_and_exclude_cross_tenant_wildcards(self):
        recipe={'format':'purpose-url-table','section':'connections','headers':['URL','Purpose','Wildcard'],
                'purpose-prefixes':['API service','Real-time connection','Report download']}
        rows=[recipe['headers'],['https://api.new-provider.example/v1/*','API service','unused'],
              ['wss://new-region.cloud.example','Real-time connection','unused'],
              ['https://*.private-api.vendor.example/*','API service','unused'],
              ['https://reports*.github.io/*','Report download','unused'],
              ['https://reports*.regional.github.io/*','Report download','unused'],
              ['https://login.vendor.example','Authentication','unused'],
              ['https://stats.vendor.example','Telemetry','unused']]
        self.assertEqual(extract_rows(recipe,self.url_table(rows)),{
            'DOMAIN,api.new-provider.example','DOMAIN,new-region.cloud.example',
            'DOMAIN-WILDCARD,*.private-api.vendor.example'})
        rows.append(['wss://unlisted-region.other.example','Real-time connection','unused'])
        self.assertIn('DOMAIN,unlisted-region.other.example',extract_rows(recipe,self.url_table(rows)))

    def test_selected_url_roles_require_a_public_secure_connection_and_the_right_columns(self):
        recipe={'format':'purpose-url-table','section':'connections','headers':['URL','Purpose'],
                'purpose-prefixes':['API service']}
        for url in ('http://api.vendor.example','https://127.0.0.1','https://user@api.vendor.example',
                    'https://api.private.corp','not a URL'):
            with self.subTest(url=url),self.assertRaises(Invalid):
                extract_rows(recipe,self.url_table([recipe['headers'],[url,'API service']]))
        with self.assertRaises(Invalid):extract_rows(recipe,self.url_table([['Other','Purpose'],['https://api.vendor.example','API service']]))

    def test_host_purpose_list_follows_product_services_without_adopting_experiments_or_other_sections(self):
        recipe={'format':'host-purpose-list','section':'services','purpose-prefixes':['Editor service'],
                'exclude-purpose-contains':['experiment'],'required-prefixes':['Editor service update']}
        doc=('<h2 id="services">Services</h2><ul><li>update.vendor.example - Editor service updates</li>'
             '<li>sync.new-provider.example - Editor service sync</li>'
             '<li>experiment.vendor.example - Editor service experiment</li>'
             '<li>raw.other.example - Shared repository access</li></ul>'
             '<script><li>bad.example - Editor service</li></script>'
             '<h2 id="elsewhere">Elsewhere</h2><li>wrong.example - Editor service</li>')
        self.assertEqual(extract_rows(recipe,doc),{'DOMAIN,update.vendor.example','DOMAIN,sync.new-provider.example'})
        for bad in (doc.replace('id="services"','id="changed"'),doc.replace('Editor service updates','Other use')):
            with self.assertRaises(Invalid):extract_rows(recipe,bad)

    def test_shared_service_completion_can_request_exact_hosts_without_widening_the_platform(self):
        recipe={'format':'host-purpose-list','section':'market','purpose-prefixes':['Shared marketplace'],
                'exact-only':True}
        doc=('<h2 id="market">Shared service</h2><ul><li>market.vendor.example - Shared marketplace</li>'
             '<li>*.cdn.vendor.example - Shared marketplace assets</li></ul>')
        self.assertEqual(extract_rows(recipe,doc),{'DOMAIN,market.vendor.example'})

    def test_scheduled_refresh_admits_unlisted_service_assets_and_protects_them_from_ads(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        src='https://api.vendor.example/meta';ads='https://filter.example/ads'
        product={'id':'developer-platform','mode':'compiled','priority':30,'section':'development',
            'description':'开发平台','boundary':'已选服务域名','sources':[src],
            'extract':[{'format':'service-domain-groups','source':src,'path':['domains'],
                        'groups':['packages'],'protect-from-reject':True}]}
        ad={'id':'ads','mode':'managed','priority':20,'section':'privacy','description':'广告','boundary':'广告',
            'sources':[ads],'kinds':['DOMAIN'],'flags':[],'license':'MIT','policy-hint':'reject'}
        cfg={'schema-version':2,'entries':[ad,product],'critical':{'api.vendor.example':['developer-platform']},
             'shared-negatives':[],'sections':[{'id':'privacy','title':'隐私'},{'id':'development','title':'开发'}]}
        document={'domains':{'packages':['api.vendor.example']}}
        urls={src:json.dumps(document),ads:'DOMAIN,new-asset.other.example\nDOMAIN,ads.unrelated.example'}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(cfg)
            (root/'config/catalog.json').write_text(json.dumps(cfg));(root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,entries))
            for e,rows in [(product,['DOMAIN,api.vendor.example']),(ad,urls[ads].splitlines())]:
                (root/'rules'/lib.rule_filename(e)).write_text(lib.decorate(e,rows,None,'2020-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=urls.__getitem__):
                lib.run()
                document['domains']['packages'].append('new-asset.other.example');urls[src]=json.dumps(document)
                lib.run();lib.run()
                self.assertIn('DOMAIN,new-asset.other.example',
                    lib.rules.read_rules((root/'rules'/lib.rule_filename(product)).read_text()))
                self.assertEqual(lib.rules.read_rules((root/'rules'/lib.rule_filename(ad)).read_text()),
                                 ['DOMAIN,ads.unrelated.example'])
                self.assertEqual(lib.run(offline=True),0)
                before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
                urls[src]='{"domains":{"other":["api.vendor.example"]}}'
                with self.assertRaises(Invalid):lib.run()
                self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*') if p.is_file()})
