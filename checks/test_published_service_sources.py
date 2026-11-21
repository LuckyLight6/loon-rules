import json
from unittest.mock import patch

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class PublishedServiceSources(PublicSourceExamples):
    def test_endpoint_rows_can_follow_the_published_product_without_hostname_selectors(self):
        recipe={'format':'endpoint-sets','sections':['mail'],'sets':[1,2],'all-hosts':True}
        def row(*cells):return '<tr>'+''.join('<td>'+cell+'</td>' for cell in cells)+'</tr>'
        document='<h2 id="mail">Mail</h2><table>'+row('ID','Category','ER','Addresses','Ports')
        document+=row('1','Required','Yes','api.new-provider.example, 192.0.2.3, 2001:db8::/32','TCP: 443')
        document+=row('2','Optional','No','*.mail.vendor.example, autodiscover.&lt;tenant&gt;.hosted.example, '
                      '*.github.io, storage.shared.example','TCP: 443')
        document+=row('3','Other product','No','unrelated.other.example','TCP: 443')+'</table>'
        fake='<template><h2 id="mail">Hidden</h2><table>'+row('1','Required','No','hidden.other.example','TCP: 443')+'</table></template>'
        document=fake+document
        self.assertEqual(extract_rows(recipe,document,shared_hosts=['storage.shared.example']),
                         {'DOMAIN,api.new-provider.example','DOMAIN-WILDCARD,*.mail.vendor.example'})
        changed=document.replace('api.new-provider.example','moved.different-provider.example')
        self.assertIn('DOMAIN,moved.different-provider.example',extract_rows(recipe,changed))
        with self.assertRaises(Invalid):extract_rows(recipe,document.replace('<td>2</td>','<td>9</td>'))

    def test_all_host_rows_require_an_explicit_boolean_and_cannot_mix_name_filters(self):
        recipe={'format':'endpoint-sets','sections':['mail'],'sets':[1],'all-hosts':True}
        document='<h2 id="mail">Mail</h2><table><tr><td>1</td><td>Required</td><td>No</td>'
        document+='<td>api.vendor.example</td><td>TCP: 443</td></tr></table>'
        for changes in ({'all-hosts':'true'},{'all-hosts':1},{'roots':['vendor.example']},
                        {'exact':['api.vendor.example']}):
            with self.subTest(changes=changes),self.assertRaises(Invalid):extract_rows({**recipe,**changes},document)

    def test_country_registries_without_an_apex_psl_entry_are_public_domains(self):
        from loon_rules import domains as domain_scope
        from loon_rules.sources import dns as source_dns
        psl=domain_scope.Suffixes('com\n*.ck\n!www.ck\nco.za\n')
        with patch.object(domain_scope,'_current',psl):
            for host in ('api.brand.co.ck','api.brand.co.za','www.ck'):
                self.assertEqual(domain_scope.public_host(host),host)
                self.assertEqual(source_dns.public_name(host),host)
            for host in ('api.brand.private','co.za','random.ck'):
                with self.subTest(host=host),self.assertRaises(Invalid):domain_scope.public_host(host)

    def test_brand_list_can_add_new_registered_domains_without_a_manual_country_list(self):
        recipe={'format':'brand-domain-list','brand-label':'brand'}
        self.assertEqual(extract_rows(recipe,'.brand.com\n.brand.co.uk\n.brand.example\n'),
                         {'DOMAIN-SUFFIX,brand.com','DOMAIN-SUFFIX,brand.co.uk','DOMAIN-SUFFIX,brand.example'})
        for bad in ('.brand.com.evil.example','.other.example','.brand.internal','.com'):
            with self.subTest(bad=bad),self.assertRaises(Invalid):extract_rows(recipe,bad)

    def test_derp_map_reads_published_node_names_without_claiming_ips_or_private_names(self):
        recipe={'format':'derp-map'}
        document={'Regions':{'7':{'RegionID':7,'RegionCode':'new','RegionName':'New region',
                    'Nodes':[{'Name':'7a','RegionID':7,'HostName':'relay.new-provider.example',
                              'IPv4':'192.0.2.1','IPv6':'2001:db8::1'}]}}}
        self.assertEqual(extract_rows(recipe,json.dumps(document)),{'DOMAIN,relay.new-provider.example'})
        node=document['Regions']['7']['Nodes'][0]
        for field,value in [('RegionID',8),('HostName','relay.internal')]:
            original=node[field];node[field]=value
            with self.subTest(field=field),self.assertRaises(Invalid):extract_rows(recipe,json.dumps(document))
            node[field]=original

    def test_api_discovery_reads_service_urls_and_ignores_documentation_and_auth_links(self):
        recipe={'format':'api-discovery','name':'market','version':'v1'}
        document={'kind':'discovery#restDescription','discoveryVersion':'v1','name':'market','version':'v1',
                  'rootUrl':'https://api.new-provider.example/','baseUrl':'https://api.new-provider.example/v1/',
                  'mtlsRootUrl':'https://mtls.new-provider.example/','documentationLink':'https://unrelated.example/',
                  'auth':{'oauth2':{'scopes':{'https://shared-auth.example/scope':{}}}}}
        self.assertEqual(extract_rows(recipe,json.dumps(document)),
                         {'DOMAIN,api.new-provider.example','DOMAIN,mtls.new-provider.example'})
        document['name']='different-product'
        with self.assertRaises(Invalid):extract_rows(recipe,json.dumps(document))

    def test_exclusive_purpose_table_retains_related_uses_and_excludes_other_products(self):
        recipe={'format':'exclusive-purpose-table','headers':['Destination Host','Ports','Purpose'],
                'purposes':['Product store'],'related-purposes':['Store updates']}
        rows=[['Destination Host','Ports','Purpose'],
              ['shop.vendor.example shared.vendor.example','443','Product store'],
              ['shop.vendor.example','443','Store updates'],
              ['shared.vendor.example','443','Connectivity checks'],
              ['api.new-provider.example','443','Product store']]
        doc='<table>'+''.join('<tr>'+''.join('<td>'+cell+'</td>' for cell in row)+'</tr>' for row in rows)+'</table>'
        self.assertEqual(extract_rows(recipe,doc),{'DOMAIN,shop.vendor.example','DOMAIN,api.new-provider.example'})
        with self.assertRaises(Invalid):extract_rows(recipe,doc.replace('Destination Host','Some other column'))

    def test_shared_uses_include_related_api_hosts_without_claiming_the_whole_provider(self):
        recipe={'format':'exclusive-purpose-table','headers':['Destination Host','Ports','Purpose'],
                'purposes':['Product store'],'related-purposes':['Store updates'],'part':'shared'}
        rows=[['Destination Host','Ports','Purpose'],
              ['shop.vendor.example','443','Product store'],
              ['common-api.vendor.example','443','Store updates'],
              ['common-api.vendor.example','443','Device registration']]
        doc='<table>'+''.join('<tr>'+''.join('<td>'+cell+'</td>' for cell in row)+'</tr>' for row in rows)+'</table>'
        self.assertEqual(extract_rows(recipe,doc),{'DOMAIN,common-api.vendor.example'})

    def test_shared_transfer_needs_source_evidence_and_an_existing_destination(self):
        from loon_rules.generation import pipeline as lib
        recipe={'format':'exclusive-purpose-table','source':'official','headers':['Destination Host','Ports','Purpose'],
                'purposes':['Product store'],'related-purposes':['Store updates'],'check-sharing':True}
        entries={'store':{'extract':[recipe]},'platform':{'fallback':True}}
        previous={'store':['DOMAIN,common-api.vendor.example','DOMAIN,vanished.vendor.example']}
        data={'store':['DOMAIN,shop.vendor.example'],'platform':['DOMAIN-SUFFIX,vendor.example']}
        rows=[['Destination Host','Ports','Purpose'],['shop.vendor.example','443','Product store'],
              ['common-api.vendor.example','443','Store updates'],['common-api.vendor.example','443','Device registration']]
        doc='<table>'+''.join('<tr>'+''.join('<td>'+cell+'</td>' for cell in row)+'</tr>' for row in rows)+'</table>'
        result=lib.shared_service_transfers(entries,previous,data,{'official':doc},['store','platform'])
        self.assertEqual(result,{'store':{'DOMAIN,common-api.vendor.example':'platform'}})
        with self.assertRaises(Invalid):
            lib.guard_coverage('store',previous['store'],data['store'],reassigned=result['store'])
        with self.assertRaises(Invalid):
            lib.shared_service_transfers(entries,previous,{**data,'platform':[]},{'official':doc},['store','platform'])

    def test_shared_ownership_report_must_match_the_generated_tables(self):
        from loon_rules.generation import pipeline as lib
        entries={'store':{'extract':[{'check-sharing':True}]},'platform':{}}
        data={'store':['DOMAIN,shop.vendor.example'],'platform':['DOMAIN-SUFFIX,vendor.example']}
        report={'store':{'DOMAIN,common-api.vendor.example':'platform'}}
        lib.verify_shared_service_transfers(entries,data,report)
        with self.assertRaises(Invalid):
            lib.verify_shared_service_transfers(entries,{**data,'platform':[]},report)
        with self.assertRaises(Invalid):
            lib.verify_shared_service_transfers(entries,{**data,'store':['DOMAIN,common-api.vendor.example']},report)
