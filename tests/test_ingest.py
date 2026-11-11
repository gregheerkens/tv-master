import copy
import json
import unittest
from datetime import date

from retro_tv.ingest import validate_context, reuse_rule, reuse_allowed, holiday_date
from retro_tv.catalog import import_library
from retro_tv.companion import export_review
from retro_tv.scheduler import extend, tune
from retro_tv import records
import test_records
from test_station import library, REAL


class ContextTest(unittest.TestCase):
    def test_recording_context_is_required_and_precision_is_preserved(self):
        for context in (None,{'kind':'recorded'},
                        {'kind':'recorded','recorded_date':'1995'},
                        {'kind':'recorded','recorded_date':'1995','seasonal':True}):
            with self.assertRaises(ValueError):validate_context(context)
        value=validate_context({'kind':'recorded','recorded_date':'1996-02','seasonal':False})
        self.assertEqual((value['recorded_from'],value['recorded_until'],value['date_precision']),
                         ('1996-02-01','1996-03-01','month'))
        with self.assertRaises(ValueError):validate_context({'kind':'recorded','recorded_date':'1995-02-29','seasonal':False})

    def test_seasonal_context_requires_holiday_year_and_consistent_answer(self):
        ctx={'kind':'recorded','recorded_date':'1995-12','seasonal':True,'holiday':'christmas'}
        with self.assertRaises(ValueError):validate_context(ctx)
        self.assertEqual(validate_context({**ctx,'holiday_year':1995})['holiday_year'],1995)
        with self.assertRaises(ValueError):validate_context({**ctx,'holiday_year':1980})
        with self.assertRaises(ValueError):validate_context({**ctx,'seasonal':False,'holiday_year':1995})

    def test_plus_minus_two_years_is_estimated_not_an_episode_release_date(self):
        ctx={'kind':'recorded','recorded_date':'1995','seasonal':False}
        rule=reuse_rule(ctx,'commercial')
        self.assertEqual((rule['valid_from'],rule['valid_until'],rule['evidence_state']),
                         ('1993-01-01','1998-01-01','estimated'))
        self.assertTrue(reuse_allowed(rule,'1997-12-31'))
        self.assertFalse(reuse_allowed(rule,'1998-01-01'))
        self.assertIsNone(reuse_rule(ctx,'program'))

    def test_holidays_move_with_target_year_and_do_not_leak_into_summer(self):
        ctx={'kind':'recorded','recorded_date':'1995-11','seasonal':True,
             'holiday':'thanksgiving','holiday_year':1995}
        rule=reuse_rule(ctx,'bumper',{'days_before':0})
        self.assertEqual(holiday_date('thanksgiving',1995),date(1995,11,23))
        self.assertEqual(holiday_date('thanksgiving',1996),date(1996,11,28))
        self.assertTrue(reuse_allowed(rule,'1996-11-28'))
        self.assertFalse(reuse_allowed(rule,'1996-11-23'))
        self.assertFalse(reuse_allowed(rule,'1996-07-04'))
        self.assertEqual(holiday_date('easter',1995),date(1995,4,16))
        self.assertEqual(holiday_date('easter',1996),date(1996,4,7))
        new_year=reuse_rule({'kind':'recorded','recorded_date':'1995-12','seasonal':True,
            'holiday':'new_years_day','holiday_year':1996},'bumper')
        self.assertTrue(reuse_allowed(new_year,'1998-01-01'))
        self.assertFalse(reuse_allowed(new_year,'1993-01-01'))

    def test_year_specific_evidence_overrides_default_and_known_bounds_can_extend(self):
        ctx={'kind':'recorded','recorded_date':'1995','seasonal':False}
        with self.assertRaises(ValueError):reuse_rule(ctx,'commercial',{'year_specific':1995})
        rule=reuse_rule(ctx,'commercial',{'year_specific':1995,'evidence':'On-screen 1995 sweepstakes deadline'})
        self.assertTrue(reuse_allowed(rule,'1995-06-01'))
        self.assertFalse(reuse_allowed(rule,'1994-06-01'))
        self.assertFalse(reuse_allowed(rule,'1996-06-01'))
        long=reuse_rule(ctx,'commercial',{'valid_from':'1990-01-01','valid_until':'2000-01-01','evidence':'Reviewed campaign archive'})
        self.assertTrue(reuse_allowed(long,'1999-06-01'))
        # Evergreen ads in a seasonal capture can be explicitly identified as nonseasonal.
        seasonal={**ctx,'seasonal':True,'holiday':'christmas','holiday_year':1995}
        self.assertTrue(reuse_allowed(reuse_rule(seasonal,'commercial',{'seasonal':False}),'1995-07-01'))


class IngestCatalogTest(unittest.TestCase):
    setUp=test_records.RecordsTest.setUp
    tearDown=test_records.RecordsTest.tearDown

    def test_context_inheritance_reaches_scheduler_and_year_specific_ads_are_rejected(self):
        doc=library()
        for row in doc['sources']:row['id']='recorded-'+row['id'];row['ingest']={'kind':'recorded','recorded_date':'1994','seasonal':False}
        for row in doc['assets']:row['id']='recorded-'+row['id'];row['source_id']='recorded-'+row['source_id']
        doc['programs']=[]
        ad=next(a for a in doc['assets'] if a['kind']=='commercial')
        ad['metadata']['reuse_constraints']={'year_specific':1994,'evidence':'1994-only sweepstakes'}
        import_library(self.db,doc,self.temp.name,verify_media=False)
        policy=records.Policy(self.db)
        self.assertFalse(policy.allowed(ad['id'],'kids','1995-07-18'))
        self.assertTrue(policy.allowed(ad['id'],'kids','1994-07-18'))
        now=extend(self.db,real_now=REAL)
        self.assertEqual(self.db.execute('SELECT count(*) FROM segment WHERE asset_id=?',(ad['id'],)).fetchone()[0],0)

    def test_companion_export_supplies_estimated_defaults_without_inventing_airdate(self):
        draft={'source':{'id':'tape','path':'tape.mp4','duration_ms':30000,
            'ingest':{'kind':'recorded','recorded_date':'1995-12','seasonal':True,'holiday':'christmas','holiday_year':1995}},
            'candidates':[{'id':'ad','in_ms':0,'out_ms':30000,'title':'Toy spot','kind':'commercial',
                'summary':'Reviewed toy advertisement','review_status':'approved','identification_evidence':'User identification',
                'services':[],'original_air_date':None}]}
        result=export_review(draft)
        self.assertEqual(result['assets'][0]['valid_from'],'1993-11-25')
        self.assertIsNone(result['assets'][0]['metadata']['original_air_date'])
        self.assertTrue(result['sources'][0]['ingest']['seasonal'])
