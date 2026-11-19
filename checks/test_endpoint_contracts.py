import unittest

from maintain import Invalid
import endpoint_contracts as gate


class PublicEndpointChecks(unittest.TestCase):
    def setUp(self):
        self.contract={
            'id':'vendor', 'source':'https://docs.example.test/endpoints',
            'format':'apple-host-table', 'sections':['service'],
            'routes':{'account':['login.vendor.example'], 'files':['*.files.vendor.example']},
            'shared':{'*.cdn.example':'Shared provider, not a vendor product.'},
            'guard-sections':['product'],
        }
        self.entries={
            'account':{'section':'product'}, 'files':{'section':'product'},
            'common':{'section':'common'}, 'all':{'section':'product'},
        }
        self.data={
            'account':['DOMAIN,login.vendor.example'],
            'files':['DOMAIN-SUFFIX,files.vendor.example'],
            'common':['DOMAIN-SUFFIX,cdn.example'],
        }

    def _doc(self,*hosts):
        body=''.join(f'<tr><td>{h}</td><td>443</td><td>TCP</td><td>App</td><td>Service</td></tr>' for h in hosts)
        return {self.contract['source']:'<h2 id="service">Service</h2><table>'+body+'</table>'}

    def test_new_or_removed_official_endpoint_stops_release(self):
        hosts=['login.vendor.example','*.files.vendor.example','*.cdn.example']
        expected={'mode':'table','assigned':2,'shared':1}
        self.assertEqual(gate.verify_sources([self.contract],self._doc(*hosts)),{'vendor':expected})
        with self.assertRaisesRegex(Invalid,'待归属.*login2.vendor.example'):
            gate.verify_sources([self.contract],self._doc(*hosts,'login2.vendor.example'))
        with self.assertRaisesRegex(Invalid,'已不列出.*login.vendor.example'):
            gate.verify_sources([self.contract],self._doc(*hosts[1:]))

    def test_claude_code_table_keeps_first_data_row(self):
        text=('## Network access requirements\n\n'
              '| URL | Required for |\n| - | - |\n'
              '| `api.anthropic.com` | API |\n| `claude.ai` | Sign-in |\n\n'
              '## Other details\n')
        self.assertEqual(gate.claude_table_hosts(text),{'api.anthropic.com','claude.ai'})

    def test_expected_owner_and_whole_wildcard_must_match(self):
        contracts=[self.contract]
        gate.verify_routes(contracts,self.entries,['common','account','files'],self.data)
        self.data['common'].append('DOMAIN-SUFFIX,vendor.example')
        with self.assertRaisesRegex(Invalid,'处理，实际：common'):
            gate.verify_routes(contracts,self.entries,['common','account','files'],self.data)
        self.data['common'].pop()
        self.data['files']=['DOMAIN,one.files.vendor.example']
        with self.assertRaisesRegex(Invalid,'实际：未匹配'):
            gate.verify_routes(contracts,self.entries,['common','account','files'],self.data)

    def test_aggregate_also_cannot_claim_shared_cdn(self):
        self.data['all']=self.data['account']+self.data['files']
        replace={'account':'all','files':'all'}
        gate.verify_routes([self.contract],self.entries,['all','common'],self.data,replace)
        self.data['all'].append('DOMAIN-SUFFIX,cdn.example')
        with self.assertRaisesRegex(Invalid,'共享端点.*被专项 all'):
            gate.verify_routes([self.contract],self.entries,['all','common'],self.data,replace)

    def test_named_host_must_be_named_not_part_of_another_host(self):
        self.contract.update(format='named-endpoints',routes={'account':['login.vendor.example']},shared={})
        source=self.contract['source']
        gate.verify_sources([self.contract],{source:'<p>Use login.vendor.example.</p>'})
        for impostor in ('bad-login.vendor.example','login.vendor.example.bad.test'):
            with self.assertRaisesRegex(Invalid,'已不列出'):
                gate.verify_sources([self.contract],{source:impostor})
