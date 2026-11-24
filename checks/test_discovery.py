import unittest

from loon_rules.generation import pipeline as lib
from loon_rules.rules import Invalid
from checks.source_fixtures import PublicSourceExamples


class SourceAliases(unittest.TestCase):
    def setUp(self):
        self.cfg={'detailed':['download','certificate','system'],'general':[],
                  'source-alias-policies':{'vendor':{
                      'parents':{'vendor.example':['vendor.example.cdn.example','origin-vendor.example.cdn.example','g.images.example']},
                      'label-modifiers':['cdn','lb']}}}
        self.entries={k:{'mode':'compiled','priority':i,'aliases':{'policy':'vendor','sources':['feed']}}
                      for i,k in enumerate(self.cfg['detailed'],1)}

    def test_source_aliases_follow_their_canonical_business_and_discover_new_names(self):
        data={'download':['DOMAIN,packages.vendor.example'],
              'certificate':['DOMAIN,status.vendor.example'],
              'system':['DOMAIN,device.vendor.example']}
        feed='\n'.join(['DOMAIN,packages-cdn.vendor.example.cdn.example',
                        'DOMAIN-SUFFIX,status-lb.origin-vendor.example.cdn.example',
                        'DOMAIN,device.g.images.example','DOMAIN,unrelated.cdn.example',
                        'DOMAIN-SUFFIX,cdn.example'])
        report=lib.apply_source_aliases(self.cfg,self.entries,data,{'feed':feed})
        self.assertIn('DOMAIN,packages-cdn.vendor.example.cdn.example',data['download'])
        self.assertIn('DOMAIN-SUFFIX,status-lb.origin-vendor.example.cdn.example',data['certificate'])
        self.assertIn('DOMAIN,device.g.images.example',data['system'])
        self.assertEqual(sum(map(len,report.values())),3)
        self.assertFalse(any('unrelated' in r or r=='DOMAIN-SUFFIX,cdn.example' for rows in data.values() for r in rows))

    def test_shared_canonical_host_uses_the_earlier_specific_owner(self):
        data={'download':['DOMAIN,packages.vendor.example'],'certificate':['DOMAIN,status.vendor.example'],
              'system':['DOMAIN,packages.vendor.example']}
        lib.apply_source_aliases(self.cfg,self.entries,data,
            {'feed':'DOMAIN,packages.vendor.example.cdn.example'})
        self.assertNotIn('DOMAIN,packages.vendor.example.cdn.example',data['system'])

    def test_source_listed_transport_prefix_follows_service_names_without_fixed_aliases(self):
        policy=self.cfg['source-alias-policies']['vendor']
        policy['parents']={'vendor.example':['vendor.example']}
        policy['label-modifiers']=[]
        policy['label-prefixes']=['stream']
        data={'download':['DOMAIN,packages.vendor.example'],
              'certificate':['DOMAIN,status.vendor.example'],'system':['DOMAIN,device.vendor.example']}
        feed=('DOMAIN,stream-packages.vendor.example\nDOMAIN,stream-status.vendor.example\n'
              'DOMAIN,stream-unknown.vendor.example\nDOMAIN,packages-stream.vendor.example')
        lib.apply_source_aliases(self.cfg,self.entries,data,{'feed':feed})
        self.assertIn('DOMAIN,stream-packages.vendor.example',data['download'])
        self.assertIn('DOMAIN,stream-status.vendor.example',data['certificate'])
        self.assertFalse(any('unknown' in row or 'packages-stream' in row for rows in data.values() for row in rows))
        data['download']=['DOMAIN,new-service.vendor.example']
        lib.apply_source_aliases(self.cfg,self.entries,data,{'feed':'DOMAIN,stream-new-service.vendor.example'})
        self.assertIn('DOMAIN,stream-new-service.vendor.example',data['download'])

    def test_coverage_guard_only_accepts_a_proven_transfer(self):
        before=['DOMAIN,wrongly.owned.example'];candidate=['DOMAIN,keep.example']
        lib.guard_coverage('old',before,candidate,reassigned=['DOMAIN,wrongly.owned.example'])
        with self.assertRaises(Invalid):
            lib.guard_coverage('old',before,candidate,reassigned=['DOMAIN,unrelated.example'])

    def test_complete_operator_registry_can_retire_asns_without_weakening_domain_coverage(self):
        before = ['DOMAIN,api.vendor.example', 'IP-ASN,399358,no-resolve']
        candidate = ['DOMAIN,api.vendor.example', 'IP-ASN,399359,no-resolve']
        lib.guard_coverage('service', before, candidate, official_autnums=True)
        with self.assertRaises(Invalid):
            lib.guard_coverage('service', before, candidate)
        with self.assertRaises(Invalid):
            lib.guard_coverage('service', before, candidate[1:], official_autnums=True)
        with self.assertRaises(Invalid):
            lib.guard_coverage('service', before, candidate[:1], official_autnums=True)


class OfficialRoleDiscovery(PublicSourceExamples):
    def test_projection_narrows_external_hosts_using_current_purpose_fields(self):
        entry = {'id': 'product', 'projection': [{'source': 'feed', 'roots': ['vendor.example'],
                  'exact-from-extract': True}], 'extract': [{'source': 'sdk',
                  'format': 'python-sdk-endpoints', 'module-level': True, 'fields': ['API_URL']}]}
        inputs = {'feed': 'DOMAIN-SUFFIX,vendor.example\nDOMAIN-SUFFIX,api.shared.example',
                  'sdk': 'API_URL = "https://api.shared.example/v1"'}
        selected = {}
        rows = lib.compile_entry(entry, inputs, projection_rows=selected)
        self.assertEqual(set(rows), {'DOMAIN-SUFFIX,vendor.example', 'DOMAIN,api.shared.example'})
        self.assertIn('DOMAIN,api.shared.example', selected['feed'])
        self.assertNotIn('DOMAIN-SUFFIX,api.shared.example', selected['feed'])
        inputs = {name: body.replace('api.shared.example', 'runtime.new-region.example')
                  for name, body in inputs.items()}
        selected = {}
        lib.compile_entry(entry, inputs, projection_rows=selected)
        self.assertIn('DOMAIN,runtime.new-region.example', selected['feed'])
        with self.assertRaises(Invalid):
            lib.compile_entry(entry, inputs, shared_hosts=['runtime.new-region.example'])

    def test_excluding_a_shared_wildcard_keeps_specific_rows_before_compaction(self):
        entry={'id':'system','extract':[{'format':'host-table','source':'doc',
               'sections':['device'],'select':[{'all-exact':True},
               {'roots':['vendor.example'],'wildcards':True}]}]}
        def row(host):
            return '<tr>'+''.join('<td>'+v+'</td>' for v in [host,'443','TCP','OS','Device management'])+'</tr>'
        doc='<h2 id="device"></h2><table>'+row('*.vendor.example')+row('licenses.vendor.example')+'</table>'
        result=lib.compile_entry(entry,{'doc':doc},shared_scopes=['*.vendor.example'])
        self.assertEqual(result,['DOMAIN,licenses.vendor.example'])
        doc=doc.replace('</table>',row('setup.other.example')+'</table>')
        self.assertEqual(lib.compile_entry(entry,{'doc':doc},shared_scopes=['licenses.vendor.example']),
                         ['DOMAIN,setup.other.example'])
        self.assertEqual(set(lib.compile_entry(entry,{'doc':doc},reserved_rows=['DOMAIN,licenses.vendor.example'])),
                         {'DOMAIN-SUFFIX,vendor.example','DOMAIN,setup.other.example'})

    def test_official_remainder_does_not_reclaim_a_specialty_or_make_new_assignments_ambiguous(self):
        from loon_rules.generation import contracts as ec
        source='doc'
        specific={'format':'host-table','source':source,'sections':['service'],
                  'select':[{'roots':['vendor.example'],'role':['Authentication']}]}
        broad={'format':'host-table','source':source,'sections':['service'],'select':[{'all-exact':True}]}
        entries={'account':{'extract':[specific]},'general':{'domain-remainder':True,'extract':[broad]}}
        contract={'id':'vendor','source':source,'format':'apple-host-table','sections':['service'],
                  'routes':{'account':['login.vendor.example'],'general':['device.vendor.example']},
                  'shared':{'www.shared.example':'共享门户'},'discover':{'account':'extract','general':'extract'}}
        def row(h,p):return '<tr>'+''.join('<td>'+v+'</td>' for v in [h,'443','TCP','OS',p])+'</tr>'
        text='<h2 id="service"></h2><table>'+''.join(row(h,p) for h,p in [
            ('login.vendor.example','Authentication'),('new.vendor.example','Authentication'),
            ('device.vendor.example','Device management'),('www.shared.example','Shared portal')])+'</table>'
        result=ec.resolve_additions([contract],entries,{source:text})
        self.assertIn('new.vendor.example',result[0]['routes']['account'])
        self.assertNotIn('new.vendor.example',result[0]['routes']['general'])

    def test_certificate_role_can_add_a_new_exact_vendor_without_importing_its_parent(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'host-table','sections':['certificate'],
                'select':[{'all-exact':True,'role':['Certificate validation']}]}
        def row(host,role):return '<tr>'+''.join('<td>'+v+'</td>' for v in [host,'443','TCP','OS',role])+'</tr>'
        text='<h2 id="certificate"></h2><table>'+row('status.new-vendor.example','Certificate validation')+row('*.shared.example','Certificate validation')+row('shop.new-vendor.example','Purchases')+'</table>'
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,status.new-vendor.example'})

    def test_product_statement_discovers_new_content_domains_and_ignores_unrelated_paragraphs(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'product-domain-statements','paragraph-contains':['domain for user content']}
        text='<p>Files use newcontent.example, the domain for user content, separate from product.example.</p><p>More information at unrelated.example.</p><script><p>domain for user content: wrong.example</p></script>'
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN-SUFFIX,newcontent.example','DOMAIN-SUFFIX,product.example'})
        with self.assertRaises(Invalid):extract_rows(recipe,text.replace('domain for user content','other content'))

    def test_link_role_discovers_the_product_root_from_its_target_not_a_fixed_hostname(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'product-role-links','labels':['Product Platform']}
        text='<a href="https://newproduct.example/model-api">Product Platform</a><a href="https://shared.example">Other link</a>'
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN-SUFFIX,newproduct.example'})
        with self.assertRaises(Invalid):extract_rows(recipe,text.replace('https://newproduct.example','http://newproduct.example'))

    def test_official_role_links_follow_new_hosts_without_claiming_a_shared_platform(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'product-role-links','labels':['Company Blog']}
        def document(url):
            return '<a href="'+url+'">Company Blog</a><a href="https://unrelated.example/">Other</a>'
        url='https://news.unlisted-provider.example/?utm_source=company&amp;utm_campaign=footer'
        self.assertEqual(extract_rows(recipe,document(url)),{'DOMAIN,news.unlisted-provider.example'})
        for unsafe in ('https://user:example@news.unlisted-provider.example/?utm_source=company',
                       'http://news.unlisted-provider.example/?utm_source=company'):
            with self.subTest(url=unsafe),self.assertRaises(Invalid):extract_rows(recipe,document(unsafe))
        with self.assertRaises(Invalid):
            extract_rows(recipe,document('https://shared.example/?utm_source=company'),shared_hosts=['shared.example'])

    def test_site_identity_requires_agreement_between_canonical_and_open_graph(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'site-identity','brand':'Product'}
        text='<meta property="og:site_name" content="Product"><meta property="og:url" content="https://newproduct.example/"><link rel="canonical" href="https://newproduct.example/">'
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN-SUFFIX,newproduct.example'})
        with self.assertRaises(Invalid):extract_rows(recipe,text.replace('canonical" href="https://newproduct.example','canonical" href="https://other.example'))

    def test_verified_website_alias_keeps_its_initial_root_when_the_official_site_redirects(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'site-identity','brand':'Company Platform',
                'source':'https://www.legacy-brand.example/',
                'include-source-alias':True,'canonical-parents':['company.example']}
        def document(host='www.company.example',brand='Company Platform'):
            return ('<meta property="og:site_name" content="'+brand+'">'
                    '<meta property="og:url" content="https://'+host+'/product">'
                    '<link rel="canonical" href="https://'+host+'/product">')
        self.assertEqual(extract_rows(recipe,document()),
                         {'DOMAIN,www.company.example','DOMAIN-SUFFIX,legacy-brand.example'})
        without_canonical=document().split('<link rel="canonical"')[0]
        try:result=extract_rows(recipe,without_canonical)
        except Invalid as error:self.fail('已核实别名应能读取品牌和官方页面 URL：'+str(error))
        self.assertEqual(result,{'DOMAIN,www.company.example','DOMAIN-SUFFIX,legacy-brand.example'})
        with self.assertRaises(Invalid):
            extract_rows({'format':'site-identity','brand':'Company Platform'},without_canonical)
        for unsafe in ('https://user:example@www.legacy-brand.example/',
                       'https://tenant.legacy-brand.example/',
                       'https://www.legacy-brand.example/private',
                       'https://www.legacy-brand.example/?token=value'):
            with self.subTest(source=unsafe),self.assertRaises(Invalid):
                extract_rows({**recipe,'source':unsafe},document())
        with self.assertRaises(Invalid):extract_rows(recipe,document('unrelated.example'))
        with self.assertRaises(Invalid):extract_rows(recipe,document(brand='Unrelated'))
        with self.assertRaises(Invalid):
            extract_rows(recipe,document(),shared_hosts=['legacy-brand.example'])


class ProductDomainScope(unittest.TestCase):
    def test_automatic_product_hosts_reject_ips_and_private_or_unregistered_names(self):
        from loon_rules.sources.inputs import product_host
        for host in ('169.254.0.1','api.internal.corp','api.vendor.local','api.vendor.invalid'):
            with self.subTest(host=host),self.assertRaises(Invalid):product_host(host)

    def test_shared_ranges_are_excluded_without_discarding_product_subdomains(self):
        from loon_rules import domains as domain_scope
        rows=['DOMAIN-SUFFIX,cdn.example','DOMAIN-WILDCARD,*.cdn.example',
              'DOMAIN,api.cdn.example','DOMAIN-SUFFIX,product.cdn.example','DOMAIN,www.portal.example']
        self.assertEqual(domain_scope.exclude_shared_scopes(rows,['*.cdn.example','www.portal.example']),
                         ['DOMAIN,api.cdn.example','DOMAIN-SUFFIX,product.cdn.example'])

    def test_wildcard_scope_never_includes_its_apex(self):
        from loon_rules import domains as domain_scope
        self.assertTrue(domain_scope.covers('DOMAIN-WILDCARD,*.vendor.example','DOMAIN-WILDCARD,*.*.vendor.example'))
        self.assertTrue(domain_scope.covers('DOMAIN-SUFFIX,vendor.example','DOMAIN-WILDCARD,p[0-9].vendor.example'))
        self.assertFalse(domain_scope.covers('DOMAIN-WILDCARD,*.vendor.example','DOMAIN-SUFFIX,vendor.example'))

    def test_product_root_uses_public_suffix_boundaries_including_private_clouds(self):
        from loon_rules.sources.inputs import product_host
        self.assertEqual(product_host('brand.co.uk'),'DOMAIN-SUFFIX,brand.co.uk')
        self.assertEqual(product_host('api.brand.co.uk'),'DOMAIN,api.brand.co.uk')
        self.assertEqual(product_host('project.github.io'),'DOMAIN-SUFFIX,project.github.io')
        self.assertEqual(product_host('github.io'),'DOMAIN,github.io')
        with self.assertRaises(Invalid):product_host('co.uk')

    def test_public_suffix_matcher_honors_wildcards_and_exceptions(self):
        from loon_rules import domains as domain_scope
        text='// ===BEGIN ICANN DOMAINS===\ncom\nuk\nco.uk\nck\n*.ck\n!www.ck\n// ===END ICANN DOMAINS===\n// ===BEGIN PRIVATE DOMAINS===\ngithub.io\n// ===END PRIVATE DOMAINS===\n'
        p=domain_scope.Suffixes(text)
        self.assertEqual(p.registrable('a.b.ck'),'a.b.ck')
        self.assertEqual(p.registrable('x.www.ck'),'www.ck')
        self.assertEqual(p.registrable('a.b.github.io'),'b.github.io')
        self.assertIsNone(p.registrable('co.uk'))


class AutomaticAdmissions(PublicSourceExamples):
    def test_declared_exclusions_are_applied_before_counting_evidence(self):
        from loon_rules.generation import discovery
        spec={'inputs':[{'source':'a','family':'one'},{'source':'b','family':'two'}]}
        feeds={key:'DOMAIN-SUFFIX,excluded.example\nDOMAIN,api.excluded.example' for key in ('a','b')}
        admitted,report=discovery.domains(spec,[],feeds,excluded=['DOMAIN-SUFFIX,excluded.example'])
        self.assertEqual(admitted,[])
        self.assertEqual(report['policy-excluded'],2)
        self.assertEqual(report['pending'],0)

    def test_published_evidence_must_belong_to_declared_inputs_and_cover_real_output(self):
        from loon_rules.generation import discovery
        entry={'discovery':{'inputs':[{'source':'a','family':'one'},{'source':'b','family':'two'}]}}
        proof={'families':['one','two'],'sources':['a','b'],'authority':False}
        stats={'state':'current','proofs':{'DOMAIN,new.example':proof}}
        discovery.verify_report({'service':entry},{'service':['DOMAIN-SUFFIX,new.example']},{'service':stats})
        with self.assertRaises(Invalid):
            discovery.verify_report({'service':entry},{'service':['DOMAIN,other.example']},{'service':stats})
        proof['sources']=['a','unknown']
        with self.assertRaises(Invalid):
            discovery.verify_report({'service':entry},{'service':['DOMAIN-SUFFIX,new.example']},{'service':stats})

    def test_an_overbroad_source_scope_does_not_vote_for_a_narrow_candidate(self):
        from loon_rules.generation import discovery
        spec={'inputs':[{'source':'a','family':'a'},{'source':'b','family':'b'}]}
        accepted,_=discovery.domains(spec,[],{'a':'DOMAIN-SUFFIX,cloud.example',
                                           'b':'DOMAIN,product.cloud.example'},shared=('cloud.example',))
        self.assertEqual(accepted,[])

    def test_confirmed_rules_retain_the_evidence_that_qualified_their_scope(self):
        from loon_rules.generation import discovery
        spec={'inputs':[{'source':'a','family':'a'},{'source':'b','family':'b'}]}
        inputs={u:'DOMAIN-SUFFIX,new-product.example' for u in ('a','b')}
        accepted,stats=discovery.domains(spec,[],inputs,shared=())
        proof=stats['proofs'][accepted[0]]
        self.assertEqual(proof['families'],['a','b'])
        self.assertEqual(proof['sources'],['a','b'])
        again,stats=discovery.domains(spec,accepted,inputs,shared=())
        self.assertEqual(again,[])
        self.assertIn(accepted[0],stats['proofs'])

    def test_official_required_wildcards_keep_their_declared_scope(self):
        from loon_rules.generation import discovery
        spec={'inputs':[{'source':'vendor','family':'vendor','authority':True,'recipe':{
            'format':'purpose-domain-lists','labels':['required domains']}}]}
        doc='<p>Required domains:</p><ul><li>*.new-service.example</li><li>*.*.new-service.example</li></ul>'
        accepted,_=discovery.domains(spec,[],{'vendor':doc},shared=())
        self.assertIn('DOMAIN-WILDCARD,*.new-service.example',accepted)
        self.assertNotIn('DOMAIN-SUFFIX,new-service.example',accepted)

    def test_a_documented_shared_host_is_not_claimed_by_a_single_product(self):
        from loon_rules.generation import discovery
        recipe={'format':'python-sdk-endpoints','module-level':True,'fields':['API_ENDPOINT']}
        spec={'inputs':[{'source':'vendor','family':'vendor','authority':True,'recipe':recipe}]}
        accepted,stats=discovery.domains(spec,[],{'vendor':'API_ENDPOINT="https://www.shared.example/api"'},
                                         shared=(),shared_hosts=('www.shared.example',))
        self.assertEqual(accepted,[])
        self.assertEqual(stats['scope-conflicts'],1)

    def test_two_products_claiming_the_same_new_scope_are_held_together(self):
        from loon_rules.generation import discovery
        spec={'inputs':[{'source':'one','family':'a'},{'source':'two','family':'b'}]}
        entries={k:{'discovery':spec,'policy-hint':'proxy'} for k in ('first','second')}
        feeds={u:'DOMAIN-SUFFIX,new-product.example' for u in ('one','two')}
        admitted,report=discovery.propose(entries,{k:[] for k in entries},feeds,active=list(entries),shared=())
        self.assertEqual(admitted,{'first':[],'second':[]})
        self.assertTrue(all(v['cross-product-conflicts']==1 for v in report.values()))

    def test_new_root_is_admitted_without_a_literal_override_when_independent_product_sources_agree(self):
        from loon_rules.generation import discovery
        spec={'inputs':[{'source':'first','family':'one'},{'source':'second','family':'two'}]}
        inputs={'first':'DOMAIN-SUFFIX,new-product.example','second':'DOMAIN-SUFFIX,new-product.example'}
        accepted,report=discovery.domains(spec,[],inputs,shared=())
        self.assertEqual(accepted,['DOMAIN-SUFFIX,new-product.example'])
        self.assertEqual(report['admitted'],1)

    def test_mirrors_of_the_same_family_do_not_supply_two_votes(self):
        from loon_rules.generation import discovery
        spec={'inputs':[{'source':'first','family':'same'},{'source':'second','family':'same'}]}
        sources={u:'DOMAIN-SUFFIX,unconfirmed.example' for u in ('first','second')}
        accepted,report=discovery.domains(spec,[],sources,shared=())
        self.assertEqual(accepted,[])
        self.assertEqual(report['unconfirmed'],1)

    def test_official_exact_proof_does_not_authorize_a_community_parent_suffix(self):
        from loon_rules.generation import discovery
        spec={'inputs':[{'source':'feed','family':'community'},
                        {'source':'official','family':'vendor','authority':True,
                         'recipe':{'format':'product-role-links','labels':['Product Platform']}}]}
        sources={'feed':'DOMAIN-SUFFIX,shared.example',
                 'official':'<a href="https://product.shared.example/">Product Platform</a>'}
        accepted,report=discovery.domains(spec,[],sources,shared=('shared.example',))
        self.assertEqual(accepted,['DOMAIN,product.shared.example'])
        self.assertEqual(report['unconfirmed'],1)

    def test_evidence_arriving_on_a_later_run_promotes_the_same_candidate_automatically(self):
        from loon_rules.generation import discovery
        spec={'inputs':[{'source':'first','family':'one'},{'source':'second','family':'two'}]}
        sources={'first':'DOMAIN,new.product.example','second':'DOMAIN,old.product.example'}
        self.assertEqual(discovery.domains(spec,[],sources,shared=())[0],[])
        sources['second']+='\nDOMAIN,new.product.example'
        accepted,_=discovery.domains(spec,[],sources,shared=())
        self.assertEqual(accepted,['DOMAIN,new.product.example'])

    def test_another_product_and_a_shared_parent_are_not_silently_claimed(self):
        from loon_rules.generation import discovery
        spec={'inputs':[{'source':'a','family':'one'},{'source':'b','family':'two'}]}
        src={'a':'DOMAIN-SUFFIX,cloud.example\nDOMAIN-SUFFIX,another.example',
             'b':'DOMAIN-SUFFIX,cloud.example\nDOMAIN-SUFFIX,another.example'}
        accepted,report=discovery.domains(spec,[],src,shared=('cloud.example',),reserved=['DOMAIN-SUFFIX,another.example'])
        self.assertEqual(accepted,[])
        self.assertEqual(report['scope-conflicts'],2)


class VendorSDKDiscovery(PublicSourceExamples):
    def test_declared_server_maps_import_all_literal_regions_without_evaluating_keys(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'python-sdk-endpoints','module-level':True,'fields':['SERVERS'],'dictionary-values':True}
        text='SERVERS = {GLOBAL: "https://api.vendor.example", EUROPE: "https://api.eu.vendor.example"}\n'
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,api.vendor.example','DOMAIN,api.eu.vendor.example'})
        with self.assertRaises(Invalid):extract_rows(recipe,text.replace('"https://api.eu.vendor.example"','untrusted()'))

    def test_vim_client_defaults_are_selected_by_api_setting_not_other_links(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'vim-config-defaults','fields':['api_url']}
        text='''" example: get(config, 'api_url', 'https://wrong.example')
let args = ['--api_server_url', get(config, 'api_url', 'https://api-new.vendor.example'),
  '--portal_url', get(config, 'portal_url', 'https://unrelated.example')]
'''
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,api-new.vendor.example'})

    def test_module_constants_and_named_function_defaults_are_scoped_as_data(self):
        from loon_rules.sources.inputs import extract_rows
        text='''API_ENDPOINT = "https://api.vendor.example"
UNRELATED = "https://unrelated.example"
def connect(*, base_url="https://rpc.vendor.example"):
    raise RuntimeError("never run")
'''
        recipe={'format':'python-sdk-endpoints','module-level':True,'fields':['API_ENDPOINT']}
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,api.vendor.example'})
        recipe={'format':'python-sdk-endpoints','functions':['connect'],'fields':['base_url']}
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,rpc.vendor.example'})

    def test_client_defaults_are_parsed_without_executing_source_or_reading_example_strings(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'python-sdk-endpoints','classes':['Client'],'fields':['base_url']}
        text='''raise RuntimeError("never execute")
class Other:
    base_url = "https://wrong.other.example"
class Client:
    def __init__(self):
        base_url = f"https://new.api.example"
        documentation = "https://unrelated.example"
'''
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,new.api.example'})
        with self.assertRaises(Invalid):extract_rows(recipe,text.replace('f"https://new.api.example"','f"https://{untrusted()}.example"'))

    def test_environment_and_rpc_defaults_keep_hosts_exact(self):
        from loon_rules.sources.inputs import extract_rows
        text='''class Environment:
    PRODUCTION = "https://api.example.com"
    PRODUCTION_EU = "https://api.eu.example.com"
class Client:
    def __init__(self, *, api_host="rpc.example.com"):
        pass
'''
        recipe={'format':'python-sdk-endpoints','classes':['Environment'],'field-prefixes':['PRODUCTION']}
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,api.example.com','DOMAIN,api.eu.example.com'})
        recipe={'format':'python-sdk-endpoints','classes':['Client'],'fields':['api_host'],'bare-hosts':True}
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,rpc.example.com'})


class NetworkDocumentDiscovery(PublicSourceExamples):
    def test_a_curl_config_download_url_is_not_mistaken_for_the_api_target(self):
        from loon_rules.sources.inputs import extract_rows
        with self.assertRaises(Invalid):
            extract_rows({'format':'curl-api-endpoints'},'<pre>curl --config https://settings.example/config</pre>')

    def test_granular_required_hosts_are_protected_without_disabling_brand_wide_ad_filters(self):
        recipe={'format':'purpose-domain-lists','labels':['required domains']}
        entry={'discovery':{'inputs':[{'source':'vendor','family':'vendor','authority':True,'recipe':recipe}]}}
        document='<p>Required domains:</p><ul><li>*.product.example</li><li>*.*.product.example</li><li>api.product.example</li></ul>'
        self.assertEqual(lib.functional_hostnames({'product':entry},{'vendor':document}),{'api.product.example'})

    def test_help_center_identity_discovers_brand_roots_without_claiming_the_hosting_provider(self):
        from loon_rules.sources.inputs import extract_rows
        import json
        recipe={'format':'help-center-domains','root-brand':'product'}
        document={'articles':[{'html_url':'https://docs.product.example/article/1'},
                              {'html_url':'https://support.product.co.uk/article/2'},
                              {'html_url':'https://other.zendesk.com/article/3'}]}
        self.assertEqual(extract_rows(recipe,json.dumps(document)),
                         {'DOMAIN-SUFFIX,product.example','DOMAIN-SUFFIX,product.co.uk'})
        with self.assertRaises(Invalid):extract_rows(recipe,'{"articles":[]}')

    def test_official_network_lists_read_only_named_roles_and_the_host_field(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'purpose-domain-lists','labels':['allow these domains','additional hosts'],
                'allow-identical-duplicates':True}
        part='<p>Allow these domains:</p><ul><li>*.new-product.example</li><li>*.*.new-product.example</li></ul><p>Additional hosts:</p><ul><li>bucket.shared.example, next.shared.example: Required downloads. See unrelated.example for notes.</li></ul>'
        self.assertEqual(extract_rows(recipe,part+part),{'DOMAIN-WILDCARD,*.new-product.example',
            'DOMAIN-WILDCARD,*.*.new-product.example','DOMAIN,bucket.shared.example','DOMAIN,next.shared.example'})
        with self.assertRaises(Invalid):extract_rows(recipe,part+part.replace('next.shared.example','changed.shared.example'))

    def test_sdk_code_uses_only_base_url_fields(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'code-api-endpoints','api-fields':['base_url','baseURL']}
        text='<pre>Client(base_url="https://api-new.vendor.example/v1", docs="https://unrelated.example")</pre>'
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,api-new.vendor.example'})

    def test_curl_command_does_not_treat_headers_or_payload_urls_as_server_hosts(self):
        from loon_rules.sources.inputs import extract_rows
        recipe={'format':'curl-api-endpoints'}
        text='''<pre>curl -X POST "https://api-new.vendor.example/v3/sessions/$ID" \\
 -H "Authorization: Bearer EXAMPLE" \\
 --header "Referer: https://unrelated.example" \\
 --data "https://payload.example"</pre>'''
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,api-new.vendor.example'})
