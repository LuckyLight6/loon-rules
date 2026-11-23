"""ASN rules require a current registry record for the declared operator."""
import json
import unittest

from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class AsnRegistrySources(unittest.TestCase):
    def recipe(self):
        return {'format':'rdap-autnum','asn':62041,
                'registrant-ids':['ORG-TMI4-RIPE'],
                'registrant-name':'Telegram Messenger Inc'}

    def record(self):
        return {'objectClassName':'autnum','startAutnum':62041,'endAutnum':62041,
                'handle':'AS62041','name':'Telegram',
                'entities':[{'handle':'MNT-TELEGRAM','roles':['registrant'],
                             'vcardArray':['vcard',[['fn',{},'text','Maintainer']]]},
                            {'handle':'ORG-TMI4-RIPE','roles':['registrant'],
                             'vcardArray':['vcard',[['fn',{},'text','Telegram Messenger Inc']]]}]}

    def test_registered_operator_emits_one_native_rule_without_dns_resolution(self):
        try:actual=extract_rows(self.recipe(),json.dumps(self.record()))
        except Invalid as error:self.fail('Registry-backed ASN generation is missing: '+str(error))
        self.assertEqual(actual,{'IP-ASN,62041,no-resolve'})

    def test_wrong_or_broader_autnum_record_cannot_authorize_the_declared_asn(self):
        for field,value in [('startAutnum',62040),('endAutnum',62042),('objectClassName','ip network'),
                            ('startAutnum',True),('handle','AS59930')]:
            record=self.record();record[field]=value
            with self.subTest(field=field),self.assertRaisesRegex(Invalid,'ASN 记录身份'):
                extract_rows(self.recipe(),json.dumps(record))

    def test_an_asn_transferred_to_another_registrant_stops_generation(self):
        for field,value in [('handle','ORG-OTHER-RIPE'),('roles',['technical']),
                            ('roles',None),('roles','registrant'),
                            ('vcardArray',['vcard',[['fn',{},'text','Other company']]])]:
            record=self.record();record['entities'][1][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(Invalid,'ASN 注册持有人'):
                extract_rows(self.recipe(),json.dumps(record))

    def test_maintainer_and_unrelated_nested_entities_are_not_operator_proof(self):
        record=self.record();operator=record['entities'].pop()
        record['entities'][0]['entities']=[operator]
        with self.assertRaisesRegex(Invalid,'ASN 注册持有人'):
            extract_rows(self.recipe(),json.dumps(record))

    def test_invalid_asn_and_unscoped_owner_declarations_are_rejected(self):
        for changes in ({'asn':0},{'asn':True},{'asn':4294967296},
                        {'registrant-ids':[]},{'registrant-name':''}):
            with self.subTest(changes=changes),self.assertRaisesRegex(Invalid,'ASN 来源声明'):
                extract_rows({**self.recipe(),**changes},json.dumps(self.record()))
