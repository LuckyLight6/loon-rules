"""Independent complete network inputs must agree before any new range is published."""
from copy import deepcopy
from ipaddress import ip_address,ip_network
import json
from unittest.mock import Mock
from checks.source_fixtures import PublicSourceExamples
from loon_rules.sources import expansion
from loon_rules.rules import Invalid

class NetworkSourceAgreement(PublicSourceExamples):
    def spec(self):
        return {'method':'network-source-agreement','source':'https://docs.vendor.example/network','max-documents':2,
            'inputs':[{'source':'https://docs.vendor.example/network','recipes':[{'format':'section-network-blocks','section':'ingest',
                'families':[4,6],'min-prefix':{'4':20,'6':32}}]},
                {'source':'https://assets.vendor.example/addresses.json','recipes':[{'format':'ip-network-map',
                    'fields':{'IPv4':4,'IPv6':6},'min-prefix':{'4':20,'6':32}}]}]}
    def inputs(self):
        return {'https://docs.vendor.example/network':'<h2 id="ingest">Ingest</h2><code>9.9.9.0/24</code><code>2620:fe::/48</code>',
            'https://assets.vendor.example/addresses.json':json.dumps({'IPv4':['9.9.9.0/25','9.9.9.128/25'],'IPv6':['2620:fe::/48']})}
    def test_adjacent_ranges_agree_and_a_new_unseeded_range_requires_both_inputs(self):
        spec=self.spec();entry={'id':'platform','mode':'compiled','sources':[item['source'] for item in spec['inputs']],'expand':spec}
        entries={'platform':entry};inputs=self.inputs()
        expansion.validate({},entries)
        fetch=Mock(side_effect=AssertionError('Already supplied input must not be fetched again'))
        rows,report,_=expansion.collect(entries,inputs,fetch)
        self.assertEqual(set(rows['platform']),{'IP-CIDR,9.9.9.0/24,no-resolve','IP-CIDR6,2620:fe::/48,no-resolve'})
        expansion.verify_report(entries,rows,report)
        inputs['https://docs.vendor.example/network']+='<code>9.9.8.0/24</code>'
        with self.assertRaises(Invalid):expansion.collect(entries,inputs,fetch)
        value=json.loads(inputs['https://assets.vendor.example/addresses.json']);value['IPv4'].append('9.9.8.0/24')
        inputs['https://assets.vendor.example/addresses.json']=json.dumps(value)
        rows,report,_=expansion.collect(entries,inputs,fetch)
        self.assertTrue(any(row.startswith('IP-CIDR,') and ip_address('9.9.8.17') in ip_network(row.split(',')[1]) for row in rows['platform']))
        expansion.verify_report(entries,rows,report)
        bad=deepcopy(report);bad['platform']['documents'][1]['rows'].pop()
        with self.assertRaises(Invalid):expansion.verify_report(entries,rows,bad)
        invalid=json.loads(inputs['https://assets.vendor.example/addresses.json']);invalid['IPv4'].append('10.0.0.0/8')
        with self.assertRaises(Invalid):expansion.collect(entries,{**inputs,'https://assets.vendor.example/addresses.json':json.dumps(invalid)},fetch)
        fetch.assert_not_called()

    def test_explicit_retirement_blocks_a_range_even_when_both_positive_lists_agree(self):
        spec=self.spec()
        spec['inputs'][0]['retired-recipes']=[{'format':'paragraph-network-list',
            'prefix':'Retired destination networks:','until':'As of','min-prefix':{'4':20,'6':32}}]
        entry={'id':'platform','mode':'compiled','sources':[item['source'] for item in spec['inputs']],'expand':spec}
        entries={'platform':entry};inputs=self.inputs()
        inputs['https://docs.vendor.example/network']+='<p>Retired destination networks: 8.8.4.0/24. As of 2026 these are no longer used.</p>'
        expansion.validate({},entries)
        rows,report,_=expansion.collect(entries,inputs,Mock())
        self.assertEqual(report['platform']['documents'][0]['retired-rows'],['IP-CIDR,8.8.4.0/24,no-resolve'])
        expansion.verify_report(entries,rows,report)
        inputs['https://docs.vendor.example/network']=inputs['https://docs.vendor.example/network'].replace('<code>9.9.9.0/24</code>','<code>9.9.9.0/24</code><code>8.8.4.0/24</code>')
        current=json.loads(inputs['https://assets.vendor.example/addresses.json']);current['IPv4'].append('8.8.4.0/24')
        inputs['https://assets.vendor.example/addresses.json']=json.dumps(current)
        with self.assertRaises(Invalid):expansion.collect(entries,inputs,Mock())
