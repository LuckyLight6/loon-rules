"""Directed network tables validate every role and every region before selecting destinations."""
from copy import deepcopy
import unittest
from unittest.mock import Mock

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources import expansion
from loon_rules.sources.inputs import extract_rows


class NetworkDirectionTables(PublicSourceExamples):
    def recipe(self,markdown=False):
        recipe={'format':'network-column-tables','section':'network','headers':['Egress','Ingress'],
                'column':'Ingress','families':[4,6],'min-prefix':{'4':24,'6':48}}
        if markdown:recipe.update({'document-format':'markdown','section-heading':'Vendor IP addresses'})
        return recipe

    def html(self,extra=''):
        def table(outbound,inbound):
            return '<table><tr><th>Egress</th><th>Ingress</th></tr><tr><td>'+outbound+'</td><td>'+inbound+'</td></tr></table>'
        return ('<h2 id="network">Vendor IP addresses</h2><h3>First region</h3>'+table('8.8.8.0/24','9.9.9.0/24')
                +'<h3>Second region</h3>'+table('8.8.4.0/24','9.9.8.0/24')+extra
                +'<h2 id="private">Private networking</h2>'+table('10.0.0.0/8','10.1.0.0/16'))

    def markdown(self,extra=''):
        return ('## Vendor IP addresses\n\n### First region\n\n| Egress | Ingress |\n|---|---|\n| 8.8.8.0/24 | 9.9.9.0/24 |\n\n'
                '### Second region\n\n| Egress | Ingress |\n|---|---|\n| 8.8.4.0/24 | 9.9.8.0/24 |\n\n'+extra
                +'## Private networking\n\n| Egress | Ingress |\n|---|---|\n| 10.0.0.0/8 | 10.1.0.0/16 |\n')

    def read(self,recipe,body):
        try:return extract_rows(recipe,body)
        except Invalid as error:self.fail('完整用途和地区表应读取成功：'+str(error))

    def test_all_regions_and_both_document_forms_follow_unlisted_destination_ranges(self):
        expected={'IP-CIDR,9.9.9.0/24,no-resolve','IP-CIDR,9.9.8.0/24,no-resolve'}
        self.assertEqual(self.read(self.recipe(),self.html()),expected)
        self.assertEqual(self.read(self.recipe(True),self.markdown()),expected)
        html='<h3>New region</h3><table><tr><th>Egress</th><th>Ingress</th></tr><tr><td>2606:4700::/48</td><td>2620:fe::/48</td></tr></table>'
        md='### New region\n\n| Egress | Ingress |\n|---|---|\n| 2606:4700::/48 | 2620:fe::/48 |\n\n'
        expected.add('IP-CIDR6,2620:fe::/48,no-resolve')
        self.assertEqual(self.read(self.recipe(),self.html(html)),expected)
        self.assertEqual(self.read(self.recipe(True),self.markdown(md)),expected)
        self.assertEqual(self.read({**self.recipe(True),'section-heading':"{% data variables.product.github %}'s IP addresses"},
            self.markdown().replace('Vendor IP addresses',"{% data variables.product.github %}'s IP addresses")),
            expected-{'IP-CIDR6,2620:fe::/48,no-resolve'})

    def test_unselected_columns_and_unknown_tables_or_shapes_still_stop_the_complete_source(self):
        invalid=[self.html().replace('8.8.8.0/24','10.0.0.0/8'),
                 self.html().replace('8.8.8.0/24','8.8.8.1/24'),
                 self.html().replace('8.8.8.0/24','8.8.8.0/21'),
                 self.html().replace('<td>8.8.8.0/24</td>',''),
                 self.html().replace('<th>Egress</th>','<th>Other purpose</th>'),
                 self.html().replace('<h3>Second region</h3>','<h2 id="network">Duplicate</h2>'),
                 self.html('<table><tr><th>Egress</th><th>Ingress</th></tr></table>')]
        for body in invalid:
            with self.subTest(body=body),self.assertRaises(Invalid):extract_rows(self.recipe(),body)
        with self.assertRaises(Invalid):extract_rows(self.recipe(True),self.markdown().replace('## Private networking','## Vendor IP addresses'))

    def test_new_region_without_a_complete_table_stops_both_official_document_forms(self):
        for extra in ('<h3>New region</h3>', '<h3>New region</h3><p>Ingress 8.8.8.0/24</p>',
                      '<p>Additional ingress 8.8.8.0/24</p>', '<h4>Changed hierarchy</h4>'):
            with self.subTest(html=extra), self.assertRaises(Invalid):
                extract_rows(self.recipe(), self.html(extra))
        for extra in ('### New region\n\n', '### New region\n\nIngress 8.8.8.0/24\n\n',
                      'Additional ingress 8.8.8.0/24\n\n', '#### Changed hierarchy\n\n'):
            with self.subTest(markdown=extra), self.assertRaises(Invalid):
                extract_rows(self.recipe(True), self.markdown(extra))

        for recipe, body in ((self.recipe(), self.html().replace('First region', 'First region8.8.8.0/24')),
                             (self.recipe(True), self.markdown().replace('First region', 'First region8.8.8.0/24'))):
            with self.subTest(address_in_heading=body), self.assertRaises(Invalid):
                extract_rows(recipe, body)

    def test_markdown_extra_cells_are_rejected_before_rendering_can_drop_them(self):
        for suffix in (' | 8.8.8.0/24 |', ' | unknown-purpose |', ' | |'):
            body = self.markdown().replace('| 8.8.8.0/24 | 9.9.9.0/24 |',
                                           '| 8.8.8.0/24 | 9.9.9.0/24' + suffix)
            with self.subTest(suffix=suffix), self.assertRaises(Invalid):
                extract_rows(self.recipe(True), body)

    def test_agreement_compares_regions_even_when_all_purpose_addresses_are_the_same(self):
        sources = ['https://docs.vendor.example/network', 'https://raw.vendor.example/network.md']
        spec = {'method': 'network-source-agreement', 'source': sources[0], 'max-documents': 2,
                'inputs': [{'source': sources[0], 'recipes': [self.recipe()]},
                           {'source': sources[1], 'recipes': [self.recipe(True)]}]}
        entry = {'id': 'networks', 'mode': 'compiled', 'sources': sources, 'expand': spec}
        for body in (self.markdown().replace('### Second region', '### Unmatched region'),
                     self.markdown().replace('### First region', '### Second region', 1)):
            with self.subTest(body=body), self.assertRaises(Invalid):
                expansion.collect({'networks': entry}, dict(zip(sources, [self.html(), body])), Mock())

    def test_invalid_recipe_shapes_stop_with_a_source_validation_error(self):
        for change in ({'headers':['Egress',[]]},{'headers':['Egress','Egress']},
                       {'column':'Unknown'},{'families':[4,{}]},
                       {'min-prefix':{'4':True,'6':48}},
                       {'document-format':'markdown'},{'document-format':'unknown'}):
            with self.subTest(change=change),self.assertRaises(Invalid):
                extract_rows({**self.recipe(),**change},self.html())

    def test_agreement_compares_full_purpose_ranges_even_when_selected_destinations_match(self):
        sources=['https://docs.vendor.example/network','https://raw.vendor.example/network.md']
        spec={'method':'network-source-agreement','source':sources[0],'max-documents':2,
              'inputs':[{'source':sources[0],'recipes':[self.recipe()]},{'source':sources[1],'recipes':[self.recipe(True)]}]}
        entry={'id':'networks','mode':'compiled','sources':sources,'expand':spec}
        inputs=dict(zip(sources,[self.html(),self.markdown()]))
        try:rows,report,_=expansion.collect({'networks':entry},inputs,Mock())
        except Invalid as error:self.fail('两份完整用途表应交叉核对：'+str(error))
        expansion.verify_report({'networks':entry},rows,report)
        self.assertEqual(set(report['networks']['documents'][0]['purpose-rows']),{'Egress','Ingress'})
        self.assertTrue(all(row.endswith(',no-resolve') for row in rows['networks']))
        changed={**inputs,sources[1]:inputs[sources[1]].replace('8.8.8.0/24','8.8.4.0/24')}
        with self.assertRaises(Invalid):expansion.collect({'networks':entry},changed,Mock())
        bad=deepcopy(report);bad['networks']['documents'][0]['purpose-rows']['Egress'].pop()
        with self.assertRaises(Invalid):expansion.verify_report({'networks':entry},rows,bad)


if __name__=='__main__':unittest.main()
