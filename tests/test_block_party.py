import json
import unittest
import test_timelines as fixtures
from retro_tv.catalog import connect
from retro_tv.timelines import options, normalize_request, launch, context_path, preflight, save_recipe


class BlockPartyTest(unittest.TestCase):
    setUp=fixtures.TimelineTest.setUp
    tearDown=fixtures.TimelineTest.tearDown

    def build_block(self, **rules):
        value={**self.request,'destination':'1995-07-18T00:00','rules':{'block_minutes':30,**rules}}
        return launch(self.path,value,real_now=1800000000000)

    def test_cloud_and_filters_use_real_metadata_and_inclusive_choices(self):
        self.db.execute('UPDATE content SET original_air_date=?,episode_metadata=? WHERE id=?',
                        ('1994-07-12',json.dumps({'network':'FOX'}),'program:episode'));self.db.commit()
        facets=options(self.db)['block_facets']
        self.assertIn({'value':1994,'label':'1994'},facets['years'])
        self.assertIn({'value':7,'label':'July'},facets['months'])
        self.assertIn({'value':'fox','label':'fox'},facets['networks'])
        good={**self.request,'rules':{'block_minutes':30,'tags':['nonexistent','cartoon'],'years':[1980,1994],'months':[7,12],'networks':['abc','fox']}}
        self.assertEqual(preflight(self.path,good,real_now=1800000000000)['current_kind'],'program')
        bad={**good,'rules':{**good['rules'],'months':[12]}}
        self.assertEqual(preflight(self.path,bad,real_now=1800000000000)['current_kind'],'slate')

    def test_fixed_boundaries_never_cut_programs_and_leave_real_gaps(self):
        for minutes in (15,30,60,90):
            result=self.build_block(block_minutes=minutes)
            with connect(context_path(self.path,result['context_id'])) as db:
                rows=list(db.execute('SELECT * FROM broadcast WHERE service_id="kids" ORDER BY start_ms'))
                origin=rows[0]['start_ms'];span=minutes*60000
                for row in rows:
                    self.assertLessEqual(row['end_ms'],origin+((row['start_ms']-origin)//span+1)*span)
                parts=list(db.execute('SELECT s.* FROM segment s JOIN broadcast b ON b.id=s.broadcast_id WHERE b.service_id="kids" AND s.kind="program"'))
                self.assertTrue(parts if minutes>=30 else not parts)
                self.assertTrue(all(s['end_ms']-s['start_ms']==600000 for s in parts))
                if minutes>=60:self.assertGreaterEqual(sum(r['program_id'] is not None for r in rows if r['start_ms']<origin+span),2)

    def test_continuity_toggles_affect_composed_media_and_saved_selections(self):
        for ads,bumpers in ((False,False),(True,False),(False,True),(True,True)):
            result=self.build_block(include_commercials=ads,include_bumpers=bumpers)
            with connect(context_path(self.path,result['context_id'])) as db:
                kinds={r[0] for r in db.execute('SELECT s.kind FROM segment s JOIN broadcast b ON b.id=s.broadcast_id WHERE b.service_id="kids"')}
                self.assertEqual('commercial' in kinds,ads)
                self.assertEqual('bumper' in kinds,bumpers)
        recipe=save_recipe(self.db,{'name':'Custom block','service_id':'kids','rules':{'block_minutes':90,'include_commercials':False,'years':[1995]}})
        normalized=normalize_request(self.db,{'mode':'representative','recipe_id':recipe['id'],'destination':'1995-07-18T16:47'})
        self.assertEqual(normalized['rules']['block_minutes'],90)
        self.assertFalse(normalized['rules']['include_commercials'])

    def test_invalid_builder_controls_and_non_party_modes_rejected(self):
        for rules in ({'block_minutes':45},{'block_minutes':True},{'block_minutes':30,'months':[0]}, {'block_minutes':30,'include_commercials':'false'}):
            with self.assertRaises(ValueError):normalize_request(self.db,{**self.request,'rules':rules})
        for mode in ('historical','surfing'):
            value={'mode':mode,'service_id':'kids','rules':{'block_minutes':30}}
            if mode=='historical':value['destination']='1995-07-18T16:47'
            with self.assertRaises(ValueError):normalize_request(self.db,value)


    def test_explicit_metadata_overrides_broad_availability_and_options_refresh(self):
        self.db.execute('UPDATE program SET metadata=? WHERE id=?',
                        (json.dumps({'year':1994,'month':7,'network':'FOX'}),'episode'));self.db.commit()
        first=options(self.db)['block_facets']
        self.assertEqual([r['value'] for r in first['years']],[1994])
        self.assertEqual([r['value'] for r in first['months']],[7])
        self.db.execute('UPDATE content SET tags=? WHERE id=?',('["new-theme"]','program:episode'));self.db.commit()
        self.assertEqual(options(self.db)['block_facets']['tags'],[{'value':'new-theme','label':'new-theme'}])

    def test_builder_resumes_and_never_changes_station_rows(self):
        before=fixtures.TimelineTest.station_snapshot(self)
        first=self.build_block(block_minutes=60,include_commercials=False)
        second=self.build_block(block_minutes=60,include_commercials=False)
        self.assertEqual(first['context_id'],second['context_id'])
        self.assertTrue(second['resuming'])
        self.assertEqual(fixtures.TimelineTest.station_snapshot(self),before)
