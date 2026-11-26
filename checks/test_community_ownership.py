"""Whole-scope reports distinguish partial priority conflicts, bundles and dependencies."""
import unittest
from loon_rules.community_review import compare
from loon_rules.matching import RuleIndex

class CommunityOwnership(unittest.TestCase):
    def fixture(self, ads):
        entries={'ads':{'policy-hint':'reject'},'product':{},'provider':{},
                 'bundle':{'mode':'view','members':['product'],
                           '_dependency-scopes':['DOMAIN,login.shared.example'],
                           '_dependency-owners':{'DOMAIN,login.shared.example':'provider'}}}
        data={'ads':ads,'product':['DOMAIN-SUFFIX,vendor.example','IP-CIDR,198.51.100.0/24'],
              'provider':['DOMAIN-SUFFIX,shared.example']}
        return entries,data,RuleIndex(data)

    def test_earlier_partial_domain_rejection_prevents_whole_scope_ownership(self):
        entries,data,index=self.fixture(['DOMAIN,api.vendor.example'])
        result=compare(['DOMAIN-SUFFIX,vendor.example'],['product'],entries,data,index)
        self.assertEqual(result['outcomes'].get('candidate-product-owner',0),0)
        self.assertEqual(result['findings'][0]['earlier-intersections'],['ads'])

    def test_earlier_partial_ip_rejection_prevents_whole_scope_ownership(self):
        entries,data,index=self.fixture(['IP-CIDR,198.51.100.128/25,no-resolve'])
        result=compare(['IP-CIDR,198.51.100.0/24'],['product'],entries,data,index)
        self.assertEqual(result['outcomes'].get('candidate-product-owner',0),0)
        self.assertEqual(result['findings'][0]['earlier-intersections'],['ads'])

    def test_bundle_accepts_its_product_members_and_labels_shared_dependencies_separately(self):
        entries,data,index=self.fixture([])
        result=compare(['DOMAIN,api.vendor.example','DOMAIN,login.shared.example'],['bundle'],entries,data,index)
        self.assertEqual(result['outcomes'].get('candidate-product-owner'),1)
        self.assertEqual(result['outcomes'].get('documented-shared-dependency-owner'),1)
        self.assertEqual(result['outcomes'].get('other-product-or-shared-owner',0),0)
