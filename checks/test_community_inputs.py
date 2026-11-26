"""Regression cases for cross-client comparisons that must not change rule semantics."""
import json
import unittest
from loon_rules.community import normalize, contributions
from loon_rules.rules import Invalid

class CommunityInputSemantics(unittest.TestCase):
    def test_leading_dot_keeps_each_clients_boundary(self):
        surge=normalize('domain-set','.vendor.example\nexact.vendor.example\n')
        self.assertCountEqual(surge['rules'],['DOMAIN-SUFFIX,vendor.example','DOMAIN,exact.vendor.example'])
        sing=normalize('sing-box',json.dumps({'version':3,'rules':[{'domain_suffix':['.vendor.example','other.example']}]}))
        self.assertEqual(sing['rules'],['DOMAIN-SUFFIX,other.example','DOMAIN-WILDCARD,*.vendor.example'])
        clash=normalize('clash-domain','payload:\n  - +.vendor.example\n  - .only-subdomains.example\n')
        self.assertEqual(clash['rules'],['DOMAIN-SUFFIX,vendor.example','DOMAIN-WILDCARD,*.only-subdomains.example'])
    def test_logical_and_inverted_rows_are_not_flattened_into_unconditional_domains(self):
        body={'version':3,'rules':[{'type':'logical','mode':'and','rules':[{'domain':['api.vendor.example']},{'port':[443]}]}, {'domain':['not-public.example'],'invert':True},{'domain':['plain.example']}]}
        data=normalize('sing-box',json.dumps(body))
        self.assertEqual(data['rules'],['DOMAIN,plain.example'])
        self.assertEqual(data['conditions'],body['rules'][:2])
        text='AND,((DOMAIN,api.vendor.example),(DEST-PORT,443))\nDOMAIN,plain.example\n'
        value=normalize('classical',text)
        self.assertEqual(value['rules'],['DOMAIN,plain.example'])
        self.assertEqual(len(value['conditions']),1)
    def test_unknown_fields_and_policies_hold_the_complete_input(self):
        for body in [{'rules':[{'domain':['x.example']}]},{'version':3,'rules':[{'domain':['x.example'],'unrecognized':True}]}]:
            with self.assertRaises(Invalid):normalize('sing-box',json.dumps(body))
        for body in ['DOMAIN,x.example\nUNKNOWN,y.example','DOMAIN,x.example,unexpected-policy','DOMAIN,x.example\n']:
            if 'UNKNOWN' in body or 'policy' in body:
                with self.assertRaises(Invalid):normalize('classical',body)
    def test_quantumult_policy_is_kept_as_context(self):
        value=normalize('quantumult-x','host-suffix,vendor.example,proxy\nip6-cidr,2001:db8::/32,direct,no-resolve\n')
        self.assertEqual(value['rules'],['DOMAIN-SUFFIX,vendor.example','IP-CIDR6,2001:db8::/32,no-resolve'])
        self.assertEqual(value['policies'],{'DOMAIN-SUFFIX,vendor.example':'proxy','IP-CIDR6,2001:db8::/32,no-resolve':'direct'})
    def test_inherited_rows_and_each_downstream_change_keep_their_author(self):
        upstream={'upstream-a':{'rules':['DOMAIN-SUFFIX,shared.example','DOMAIN,removed.example','DOMAIN,same.example'],'products':['service-a']}}
        child={'rules':['DOMAIN,api.shared.example','DOMAIN,new.example','DOMAIN,same.example'],'products':['service-b']}
        value=contributions('downstream',child,upstream)
        rows={item['rule']:item for item in value['entries']}
        self.assertEqual(rows['DOMAIN,api.shared.example']['change'],'narrowed')
        self.assertEqual(rows['DOMAIN,api.shared.example']['contributors'],['downstream'])
        self.assertEqual(rows['DOMAIN,new.example']['change'],'added')
        self.assertEqual(rows['DOMAIN,same.example']['inherited-from'],['upstream-a'])
        self.assertEqual(rows['DOMAIN,same.example']['classification-contributors'],['downstream'])
        self.assertIn('DOMAIN,removed.example',value['removed'])
        self.assertEqual(value['removed-contributors'],['downstream'])
    def test_similar_files_are_not_automatically_independent_votes(self):
        value=contributions('unverified',{'rules':['DOMAIN,a.example'],'products':['a']},None)
        self.assertEqual(value['independence'],'unverified')
        self.assertEqual(value['entries'][0]['contributors'],[])

    def test_downstream_policy_change_keeps_its_own_contribution(self):
        parent=normalize('quantumult-x','host,api.vendor.example,direct\n')
        child=normalize('quantumult-x','host,api.vendor.example,proxy\n')
        value=contributions('child',child,{'parent':parent})
        row=value['entries'][0]
        self.assertEqual(row['policy-contributors'],['child'])
        self.assertIn('child',row['contributors'])
        self.assertEqual(row['policy-change'],{'from':{'parent':'direct'},'to':'proxy'})
        same=contributions('child',child,{'parent':child})['entries'][0]
        self.assertEqual(same['policy-contributors'],[])
