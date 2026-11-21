import copy
import unittest

from loon_rules.generation import pipeline as lib
from loon_rules.rules import Invalid


class CatalogLayout(unittest.TestCase):
    def fixture(self):
        def product(key, rank, selection=None):
            entry={'id':key,'priority':rank,'section':'products','mode':'compiled',
                   'description':'产品','boundary':'专用入口','sources':['https://vendor.example/network'],
                   'include':['DOMAIN,'+key+'.example']}
            if selection:entry['selection']=selection
            return entry
        return {'schema-version':2,'entries':[product('regular',20),product('specialty',10,'detailed'),
                    product('variant-alt',40,'alternative'),product('extra',30,'optional')],
                'sections':[{'id':'products','title':'产品'}]}

    def test_product_declarations_generate_sections_and_compatible_selection_lists(self):
        cfg=self.fixture()
        lib.validate_declarations(cfg)
        self.assertEqual(cfg['general'],['regular'])
        self.assertEqual(cfg['detailed'],['specialty'])
        self.assertEqual(cfg['alternatives'],['variant-alt'])
        self.assertEqual(cfg['optional'],['extra'])
        self.assertEqual(cfg['views'],[])
        self.assertEqual(cfg['sections'][0]['numbers'],[10,20,30,40])

    def test_adding_a_product_replaces_stale_generated_lists_and_updates_bundle_members(self):
        cfg=self.fixture();lib.validate_declarations(cfg)
        cfg['entries'].append(dict(cfg['entries'][0],id='new-product',priority=25))
        cfg['entries'].append({'id':'products-all','priority':5,'section':'products','mode':'view',
                               'description':'合集','boundary':'产品合集',
                               'member-selection':{'section':'products'}})
        entries=lib.validate_declarations(cfg)
        self.assertEqual(cfg['general'],['regular','new-product'])
        self.assertEqual(cfg['views'],['products-all'])
        self.assertEqual(entries['products-all']['members'],['specialty','regular','new-product'])
        self.assertEqual(cfg['sections'][0]['numbers'],[5,10,20,25,30,40])
        before=copy.deepcopy(cfg);lib.validate_declarations(cfg)
        self.assertEqual(cfg,before)

    def test_original_schema_keeps_explicit_lists_and_section_ranges(self):
        cfg=self.fixture();cfg.pop('schema-version')
        cfg.update(general=['regular','extra'],detailed=['specialty'],alternatives=['variant-alt'],optional=[],views=[])
        cfg['sections'][0].update({'from':1,'through':99})
        before=copy.deepcopy(cfg);lib.validate_declarations(cfg)
        self.assertEqual(cfg,before)

    def test_unknown_schema_section_and_selection_are_rejected(self):
        for mutation in (lambda c:c.update({'schema-version':3}),
                         lambda c:c['entries'][0].update(selection='silently-ignore'),
                         lambda c:c['entries'][0].update(section='unknown')):
            with self.subTest(mutation=mutation):
                cfg=self.fixture();mutation(cfg)
                with self.assertRaises(Invalid):lib.validate_declarations(cfg)

    def test_offline_commands_refuse_stale_compatibility_fields(self):
        from loon_rules import catalog as catalog_schema
        cfg=self.fixture();lib.validate_declarations(cfg)
        catalog_schema.verify(cfg)
        cfg['general']=[]
        with self.assertRaisesRegex(Invalid,'render-index'):catalog_schema.verify(cfg)

    def test_priority_bands_generate_members_from_the_same_product_numbers(self):
        cfg=self.fixture();cfg['routing-bands']=[{'start':10,'title':'常规产品'},
                                                {'start':30,'title':'可选产品'}]
        lib.validate_declarations(cfg)
        self.assertEqual(cfg['routing-bands'][0]['ids'],['specialty','regular'])
        self.assertEqual(cfg['routing-bands'][1]['ids'],['extra','variant-alt'])
        cfg['entries'].append(dict(cfg['entries'][0],id='new-product',priority=25))
        lib.validate_declarations(cfg)
        self.assertEqual(cfg['routing-bands'][0]['ids'],['specialty','regular','new-product'])
        self.assertEqual(lib.subscription_order(cfg,{e['id']:e for e in cfg['entries']}),
                         ['specialty','regular','new-product','extra','variant-alt'])

    def test_generated_band_membership_is_checked_offline(self):
        from loon_rules import catalog as catalog_schema
        cfg=self.fixture();cfg['routing-bands']=[{'start':10,'title':'产品'}]
        lib.validate_declarations(cfg);catalog_schema.verify(cfg)
        cfg['routing-bands'][0]['ids'].remove('regular')
        with self.assertRaisesRegex(Invalid,'render-index'):catalog_schema.verify(cfg)

    def test_priority_bands_need_unique_increasing_starts_and_cannot_omit_a_product(self):
        for starts in ([30,10],[10,10],[11,30],[True,30],[10,None]):
            cfg=self.fixture();cfg['routing-bands']=[
                dict(title='分区'+str(i),**({'start':value} if value is not None else {}))
                for i,value in enumerate(starts)]
            with self.subTest(starts=starts),self.assertRaises(Invalid):lib.validate_declarations(cfg)

    def test_explicit_bands_without_ranges_keep_their_original_order(self):
        cfg=self.fixture();ids=['regular','specialty','extra','variant-alt']
        cfg['routing-bands']=[{'title':'既有调用','ids':ids.copy()}]
        lib.validate_declarations(cfg)
        self.assertEqual(cfg['routing-bands'][0]['ids'],ids)

    def test_four_digit_width_reaches_filenames_headers_and_subscription_links(self):
        from loon_rules.catalog import rule_filename
        cfg=self.fixture();cfg['priority-width']=4
        entries=lib.validate_declarations(cfg)
        entry=entries['regular']
        self.assertEqual(rule_filename(entry),'0020-regular.lsr')
        text=lib.decorate(entry,['DOMAIN,regular.example'],None,'2026-11-22T00:00:00Z')
        self.assertIn('# priority: 0020\n',text)
        index=lib.render_index(cfg,entries)
        self.assertIn('| 0020 | [regular]',index)
        self.assertIn('/main/rules/0020-regular.lsr',index)
        self.assertEqual(rule_filename({'priority':61,'id':'legacy'}),'061-legacy.lsr')

    def test_four_digit_bands_allow_insertions_between_initial_tens(self):
        cfg=self.fixture();cfg['priority-width']=4
        for entry in cfg['entries']:entry['priority']=2000+entry['priority']
        cfg['entries'].extend([
            dict(cfg['entries'][0],id='inserted',priority=2015),
            dict(cfg['entries'][0],id='last',priority=9999)])
        cfg['routing-bands']=[{'start':2000,'title':'产品'}, {'start':9000,'title':'末尾'}]
        try:entries=lib.validate_declarations(cfg)
        except Invalid as error:self.fail('合法四位编号被拒绝：'+str(error))
        self.assertEqual(lib.subscription_order(cfg,entries),
                         ['specialty','inserted','regular','extra','variant-alt','last'])
        self.assertEqual(cfg['routing-bands'][-1]['ids'],['last'])
        cfg['entries'][-1]['priority']=10000
        with self.assertRaises(Invalid):lib.validate_declarations(cfg)

    def test_number_width_must_be_a_supported_integer(self):
        for width in (True,2,5,'4'):
            cfg=self.fixture();cfg['priority-width']=width
            with self.subTest(width=width),self.assertRaises(Invalid):lib.validate_declarations(cfg)
