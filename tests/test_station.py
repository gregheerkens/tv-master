import copy
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from retro_tv.catalog import connect, import_library
from retro_tv.scheduler import initialize, extend, guide, tune, daypart_matches, HORIZON_MS
from retro_tv.companion import boundaries, export_review

ROOT=Path(__file__).resolve().parents[1]
REAL=1800000000000


def library():
    sources=[];assets=[];programs=[]
    for ident,kind,duration in [('act1','program',600000),('act2','program',600000),
                                ('ad','commercial',30000),('bumper','bumper',5000)]:
        sources.append({'id':ident,'path':f'{ident}.mp4','duration_ms':duration,
                        'provenance':{'origin':'synthetic test'}})
        assets.append({'id':ident,'source_id':ident,'title':ident,'kind':kind,
                       'valid_from':'1995-01-01','valid_until':'1996-01-01',
                       'services':['kids'],'metadata':{'review_status':'approved'}})
    programs.append({'id':'episode','title':'Synthetic episode','parts':['act1','act2'],
                     'services':['kids'],'valid_from':'1995-01-01','valid_until':'1996-01-01'})
    return {'version':1,'sources':sources,'assets':assets,'programs':programs}


class StationTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'station.sqlite'
        self.db=connect(self.path)
        self.config=json.loads((ROOT/'examples/station.json').read_text())
        initialize(self.db,self.config,real_now=REAL)

    def tearDown(self):
        self.db.close();self.temp.cleanup()

    def load(self):
        import_library(self.db,library(),self.temp.name,verify_media=False)

    def snapshot(self):
        return [tuple(r) for r in self.db.execute('SELECT * FROM segment ORDER BY id')]

    def test_prepared_library_runs_without_analyzer_or_media_splitting(self):
        self.load()
        now=extend(self.db,real_now=REAL)
        rows=self.db.execute('SELECT * FROM segment WHERE broadcast_id=(SELECT id FROM broadcast WHERE service_id="kids" ORDER BY start_ms LIMIT 1) ORDER BY start_ms').fetchall()
        self.assertEqual(rows[0]['kind'],'bumper')
        kinds=[r['kind'] for r in rows]
        self.assertEqual(kinds.count('program'),2)
        first=kinds.index('program');second=kinds.index('program',first+1)
        self.assertIn('commercial',kinds[first+1:second])
        for a,b in zip(rows,rows[1:]): self.assertEqual(a['end_ms'],b['start_ms'])
        self.assertEqual(rows[-1]['end_ms']-rows[0]['start_ms'],1800000)
        self.assertEqual(list(Path(self.temp.name).glob('*.mp4')),[])
        self.assertEqual(tune(self.db,'kids',now+20000)['offset_ms'],15000)

    def test_three_day_horizon_and_append_only_extension(self):
        self.load();now=extend(self.db,real_now=REAL)
        before=self.snapshot()
        view=guide(self.db,now)
        self.assertEqual(view['until_ms']-view['now_ms'],HORIZON_MS)
        for channel in view['channels']:
            self.assertTrue(all(e['start_ms']<now+HORIZON_MS and e['end_ms']<=now+HORIZON_MS for e in channel['entries']))
        extend(self.db,real_now=REAL+1234567)
        self.assertEqual(self.snapshot()[:len(before)],before)
        self.assertGreater(len(self.snapshot()),len(before))

    def test_restart_and_clock_rollback_do_not_rewind(self):
        self.load();now=extend(self.db,real_now=REAL+60000);before=self.snapshot()
        self.db.close();self.db=connect(self.path)
        self.assertEqual(extend(self.db,real_now=REAL-60000),now)
        self.assertEqual(self.snapshot(),before)
        with self.assertRaises(sqlite3.IntegrityError): initialize(self.db,self.config,real_now=REAL)

    def test_published_rows_and_clock_are_immutable(self):
        self.load();extend(self.db,real_now=REAL)
        for query in ['UPDATE broadcast SET title="rerolled"','DELETE FROM broadcast',
                      'UPDATE segment SET source_in_ms=900','DELETE FROM segment',
                      'UPDATE state SET seed="reroll"','DELETE FROM state',
                      'UPDATE state SET high_water_ms=0']:
            with self.assertRaises(sqlite3.IntegrityError,msg=query):
                with self.db: self.db.execute(query)

    def test_invalid_span_and_pending_review_roll_back_entire_import(self):
        for change in ({'in_ms':-1},{'out_ms':600001},{'in_ms':600000},
                       {'in_ms':.5},{'metadata':{'review_status':'pending'}}):
            doc=library();doc['assets'][0].update(change)
            with self.assertRaises(ValueError): import_library(self.db,doc,self.temp.name,verify_media=False)
            self.assertEqual(self.db.execute('SELECT COUNT(*) FROM source').fetchone()[0],0)

    def test_new_library_does_not_rewrite_existing_guide(self):
        self.load();extend(self.db,real_now=REAL);before=self.snapshot()
        doc=library()
        for row in doc['sources']: row['id']='new-'+row['id']
        for row in doc['assets']: row['id']='new-'+row['id'];row['source_id']='new-'+row['source_id']
        for row in doc['programs']: row['id']='new-'+row['id'];row['parts']=['new-'+p for p in row['parts']]
        import_library(self.db,doc,self.temp.name,verify_media=False)
        extend(self.db,real_now=REAL)
        self.assertEqual(self.snapshot(),before)

    def test_wrong_era_and_network_become_explicit_gap(self):
        doc=library()
        doc['programs'][0]['valid_from']='1996-01-01';doc['programs'][0]['valid_until']='1997-01-01'
        import_library(self.db,doc,self.temp.name,verify_media=False)
        now=extend(self.db,real_now=REAL)
        self.assertEqual(tune(self.db,'kids',now)['kind'],'slate')
        self.assertEqual(tune(self.db,'late',now)['kind'],'slate')
        self.assertIsNone(self.db.execute('SELECT program_id FROM broadcast LIMIT 1').fetchone()[0])

    def test_repeatable_schedule_from_same_seed_clock_and_catalog(self):
        self.load();extend(self.db,real_now=REAL);before=self.snapshot()
        db=connect(':memory:')
        initialize(db,self.config,real_now=REAL)
        import_library(db,library(),self.temp.name,verify_media=False)
        extend(db,real_now=REAL)
        self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM segment ORDER BY id')],before)
        db.close()

    def test_program_expiring_at_midnight_is_not_scheduled_across_date_boundary(self):
        # A program's allowable rerun window must cover every act in its block.
        doc=library()
        for row in doc['assets']+doc['programs']:row['valid_until']='1995-07-19'
        import_library(self.db,doc,self.temp.name,verify_media=False)
        now=extend(self.db,real_now=REAL)
        midnight=now+8*3600000
        rows=self.db.execute('SELECT * FROM broadcast WHERE service_id="kids" AND start_ms>=?',(midnight,)).fetchall()
        self.assertTrue(rows)
        self.assertTrue(all(r['evidence']=='missing' for r in rows))

    def test_daypart_limits_and_overnight_weekday_ownership(self):
        doc=library()
        doc['programs'][0]['metadata']={'dayparts':[{'start':'16:00','end':'17:00','weekdays':[1]}]}
        import_library(self.db,doc,self.temp.name,verify_media=False)
        now=extend(self.db,real_now=REAL)
        self.assertEqual(tune(self.db,'kids',now)['kind'],'bumper')
        self.assertEqual(tune(self.db,'kids',now+3600000)['kind'],'slate')
        row={'metadata':json.dumps({'dayparts':[{'start':'22:00','end':'02:00','weekdays':[1]}]})}
        self.assertTrue(daypart_matches(row,datetime.fromisoformat('1995-07-19T01:00:00-04:00')))
        self.assertFalse(daypart_matches(row,datetime.fromisoformat('1995-07-20T01:00:00-04:00')))

    def test_concurrent_writers_publish_one_contiguous_schedule(self):
        self.load()
        def generate(_):
            db=connect(self.path)
            try:return extend(db,real_now=REAL)
            finally:db.close()
        with ThreadPoolExecutor(max_workers=3) as pool:
            times=list(pool.map(generate,range(3)))
        self.assertEqual(len(set(times)),1)
        rows=self.db.execute('SELECT start_ms,end_ms FROM broadcast WHERE service_id="kids" ORDER BY start_ms').fetchall()
        self.assertEqual(len(rows),144)
        for a,b in zip(rows,rows[1:]):self.assertEqual(a['end_ms'],b['start_ms'])

    def test_published_missing_slots_do_not_change_when_media_arrives(self):
        now=extend(self.db,real_now=REAL)
        before=self.snapshot();self.load();extend(self.db,real_now=REAL)
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(tune(self.db,'kids',now)['kind'],'slate')
        extend(self.db,real_now=REAL+1800000)
        tail=self.db.execute('SELECT program_id FROM broadcast WHERE service_id="kids" ORDER BY start_ms DESC LIMIT 1').fetchone()
        self.assertEqual(tail[0],'episode')


class CompanionTest(unittest.TestCase):
    def test_boundary_candidates_are_not_identities(self):
        cuts=boundaries('black_start:10 black_end:10.4\nsilence_end: 10.3',20000)
        self.assertEqual([p['at_ms'] for p in cuts],[0,10200,20000])
        self.assertEqual(cuts[1]['evidence'],'black + silence')

    def test_pending_analysis_cannot_enter_catalog(self):
        with self.assertRaises(ValueError):export_review({'source':{},'candidates':[]})

    def test_review_exports_same_import_contract_and_requires_provenance(self):
        draft={'source':{'id':'tape','path':'tape.mp4','duration_ms':1000},'candidates':[
            {'id':'a','in_ms':0,'out_ms':1000,'title':'Reviewed bumper','kind':'bumper',
             'summary':'Manually identified network bumper','valid_from':'1995-01-01',
             'valid_until':'1996-01-01','services':['kids'],'review_status':'approved',
             'identification_evidence':'Visible station logo; user verification'}]}
        result=export_review(draft)
        self.assertEqual(result['assets'][0]['metadata']['review_status'],'approved')
        draft['candidates'][0]['identification_evidence']=None
        with self.assertRaises(ValueError):export_review(draft)


if __name__=='__main__':unittest.main()
