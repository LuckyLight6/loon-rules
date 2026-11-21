import unittest
from unittest.mock import patch

from loon_rules.rules import Invalid


class PublicCnameDiscovery(unittest.TestCase):
    def test_one_unavailable_resolver_marks_the_service_observation_incomplete(self):
        from loon_rules.sources import dns as source_dns
        host='download.example.com'
        with patch.object(source_dns,'query',return_value={'aliases':[],'requests':2,'successful-resolvers':1}):
            records,stats=source_dns.collect([host])
        self.assertEqual(records,{host:[]})
        self.assertEqual(stats['incomplete-hosts'],[host])
        self.assertEqual(stats['partial-lookups'],1)
        self.assertEqual(stats['unavailable-lookups'],0)

    def test_a_failed_follow_up_is_reported_for_its_original_service(self):
        from loon_rules.sources import dns as source_dns
        host='download.example.com';alias='download.example.com.akadns.net'
        def answer(name):
            if name==host:return {'aliases':[alias],'requests':2,'successful-resolvers':2}
            raise Invalid('unavailable')
        with patch.object(source_dns,'query',side_effect=answer):
            records,stats=source_dns.collect([host],follow=lambda root,name:True)
        self.assertEqual(records,{host:[alias]})
        self.assertEqual(stats['incomplete-hosts'],[host])
        self.assertEqual(stats['unavailable-hosts'],0)

    def test_follow_up_queries_stay_inside_the_service_alias_policy(self):
        from loon_rules.sources import dns as source_dns
        answers={
            'download.example.com':{'aliases':['download.example.com.akadns.net'],'requests':2,'successful-resolvers':2},
            'download.example.com.akadns.net':{'aliases':['download.g.images.example.com','shared.edge.example.net'],'requests':2,'successful-resolvers':2},
            'download.g.images.example.com':{'aliases':[],'requests':2,'successful-resolvers':2}}
        def follow(root,name):return name.startswith('download.')
        with patch.object(source_dns,'query',side_effect=answers.__getitem__):
            records,stats=source_dns.collect(['download.example.com'],follow=follow)
        self.assertIn('download.g.images.example.com',records['download.example.com'])
        self.assertEqual(stats['http-requests'],6)

    def test_only_the_cname_chain_of_the_requested_host_is_followed(self):
        from loon_rules.sources import dns as source_dns
        doc={'Status':0,'Answer':[
            {'name':'download.example.com.','type':5,'data':'download.g.images.example.com.'},
            {'name':'download.g.images.example.com.','type':5,'data':'shared.edge.example.net.'},
            {'name':'unrelated.example.com.','type':5,'data':'wrong.example.net.'},
            {'name':'download.example.com.','type':1,'data':'17.0.0.1'}]}
        self.assertEqual(source_dns.cname_chain('download.example.com',doc),
                         ['download.g.images.example.com','shared.edge.example.net'])

    def test_the_http_adapter_rejects_private_names_ips_and_non_names_before_requesting(self):
        from loon_rules.sources import dns as source_dns
        with patch.object(source_dns.subprocess,'run',side_effect=AssertionError('must not request')):
            for host in ('service.corp','service.local','169.254.0.1','[::1]','example.com&key=secret'):
                with self.subTest(host=host),self.assertRaises(Invalid):source_dns.query(host)

    def test_records_do_not_become_service_rules_without_matching_the_vendor_alias_policy(self):
        from loon_rules.generation import pipeline as lib
        cfg={'detailed':['download'],'general':[],'source-alias-policies':{
            'vendor':{'parents':{'example.com':['g.images.example.com']},'label-modifiers':['cdn','lb']}}}
        entries={'download':{'mode':'compiled','priority':1,'aliases':{'policy':'vendor','sources':[]}}}
        data={'download':['DOMAIN,download.example.com']}
        lib.apply_source_aliases(cfg,entries,data,{},dns_records={
            'download.example.com':['download.g.images.example.com','shared.edge.example.net']})
        self.assertEqual(data['download'],['DOMAIN,download.example.com','DOMAIN,download.g.images.example.com'])

    def test_a_dedicated_cname_tenant_needs_the_service_chain_and_cannot_claim_the_shared_parent(self):
        from loon_rules.generation import pipeline as lib
        cfg={'detailed':['download'],'general':[],'source-alias-policies':{'vendor':{
            'parents':{'example.com':['example.com.delivery.example.com']},'label-modifiers':['lb'],
            'cname-tenants':{'example.com':['trafficmanager.net']}}}}
        entries={'download':{'mode':'compiled','priority':1,'aliases':{'policy':'vendor','sources':['feed']}}}
        data={'download':['DOMAIN,download.example.com']}
        tenant='rotated-service.trafficmanager.net'
        feed={'feed':'DOMAIN,unrelated.trafficmanager.net\nDOMAIN-SUFFIX,'+tenant}
        lib.apply_source_aliases(cfg,entries,data,feed,dns_records={'download.example.com':[
            tenant,'trafficmanager.net','child.other-tenant.trafficmanager.net','shared.edge.example.net']})
        self.assertEqual(data['download'],['DOMAIN,download.example.com','DOMAIN,'+tenant])
        self.assertTrue(lib.cname_tenant('download.example.com',tenant,cfg['source-alias-policies']['vendor']))
        self.assertFalse(lib.cname_tenant('other.example.net',tenant,cfg['source-alias-policies']['vendor']))
