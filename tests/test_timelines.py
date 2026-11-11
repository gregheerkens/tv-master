import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from retro_tv.catalog import connect, import_library
from retro_tv.scheduler import initialize, extend, tune, HORIZON_MS
from retro_tv.timelines import preflight, launch, context_path, normalize_request, save_recipe, options, sync_catalog
from retro_tv.manager import import_plan
from test_station import ROOT, REAL, library


class TimelineTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        self.path=self.folder/'station.sqlite';self.db=connect(self.path)
        initialize(self.db,json.loads((ROOT/'examples/station.json').read_text()),real_now=REAL)
        doc=library()
        for source in doc['sources']:(self.folder/source['path']).write_bytes(b'synthetic metadata fixture')
        import_library(self.db,doc,self.folder,verify_media=False)
        self.db.execute('UPDATE content SET tags=? WHERE id=?',('["cartoon","summer"]','program:episode'));self.db.commit()
        self.request={'mode':'representative','service_id':'kids','destination':'1995-07-18T16:47',
                      'rules':{'tags':['Cartoon']}}

    def tearDown(self):self.db.close();self.temp.cleanup()

    def station_snapshot(self):
        return {table:[tuple(r) for r in self.db.execute(f'SELECT * FROM {table}')] for table in ('state','broadcast','segment','source','asset')}

    def test_preflight_and_launch_reuse_media_without_changing_surfing_station(self):
        extend(self.db,real_now=REAL);before=self.station_snapshot()
        check=preflight(self.path,self.request,real_now=REAL)
        self.assertEqual(check['current_kind'],'program');self.assertEqual(check['current_offset_ms'],117500)
        self.assertEqual(check['rules']['tags'],['cartoon'])
        self.assertEqual(self.station_snapshot(),before)
        context=launch(self.path,self.request,real_now=REAL)
        with connect(context_path(self.path,context['context_id'])) as session:
            now=extend(session,real_now=REAL)
            playing=tune(session,'kids',now)
            self.assertEqual(playing['asset_id'],'act2');self.assertEqual(playing['offset_ms'],117500)
            self.assertEqual([r[0] for r in session.execute('SELECT path FROM source ORDER BY id')],
                             [r[0] for r in self.db.execute('SELECT path FROM source ORDER BY id')])
            with self.assertRaises(sqlite3.IntegrityError):session.execute('UPDATE state SET real_anchor_ms=0')
        self.assertEqual(self.station_snapshot(),before)
        self.assertEqual(list((self.folder/'contexts').glob('*.mp4')),[])

    def test_reentering_same_selection_resumes_instead_of_restarting(self):
        first=launch(self.path,self.request,real_now=REAL)
        second=launch(self.path,{**self.request,'rules':{'tags':['cartoon']}},real_now=REAL+60000)
        self.assertEqual(first['context_id'],second['context_id']);self.assertTrue(second['resuming'])
        resumed=preflight(self.path,self.request,real_now=REAL+60000)
        self.assertTrue(resumed['resuming']);self.assertEqual(resumed['current_offset_ms'],177500)
        self.assertEqual(self.db.execute('SELECT count(*) FROM viewing_context').fetchone()[0],1)

    def test_filtering_changes_what_but_preserves_slot_duration_and_clock(self):
        empty=preflight(self.path,{**self.request,'rules':{'tags':['horror']}},real_now=REAL)
        ready=preflight(self.path,self.request,real_now=REAL)
        self.assertEqual(empty['now_ms'],ready['now_ms']);self.assertEqual(empty['current_kind'],'slate')
        context=launch(self.path,self.request,real_now=REAL)
        with connect(context_path(self.path,context['context_id'])) as db:
            row=db.execute('SELECT start_ms,end_ms FROM broadcast WHERE service_id="kids" ORDER BY start_ms LIMIT 1').fetchone()
            self.assertEqual(row['end_ms']-row['start_ms'],1800000)

    def test_representative_templates_are_deterministic_and_explicit(self):
        value=normalize_request(self.db,{'mode':'representative','service_id':'kids',
            'template':'saturday_morning','year':1995,'month':7})
        self.assertEqual(value['destination'],'1995-07-01T08:00:00-04:00')
        weekday=normalize_request(self.db,{'mode':'representative','service_id':'kids',
            'template':'weekday_afternoon','year':1995,'month':7})
        self.assertEqual(weekday['destination'],'1995-07-04T16:30:00-04:00')

    def test_surfing_selection_uses_existing_clock_and_rejects_time_controls(self):
        value={'mode':'surfing','service_id':'kids','rules':{'tags':['cartoon']}}
        context=launch(self.path,value,real_now=REAL+120000)
        with connect(context_path(self.path,context['context_id'])) as db:
            now=extend(db,real_now=REAL+120000)
            original=self.db.execute('SELECT * FROM state').fetchone()
            self.assertEqual(now,original['historical_anchor_ms']+120000)
            self.assertEqual(db.execute('SELECT real_anchor_ms FROM state').fetchone()[0],REAL)
        for invalid in ({'destination':'1995-07-18T16:00'},{'rules':{'speed':2}},{'seed':'reroll'}):
            with self.assertRaises(ValueError):normalize_request(self.db,{**value,**invalid})

    def test_saved_selection_can_be_reused_with_different_destinations(self):
        recipe=save_recipe(self.db,{'name':'Summer cartoons','service_id':'kids','rules':{'tags':['cartoon']}})
        one=normalize_request(self.db,{'recipe_id':recipe['id'],'destination':'1995-07-18T16:47'})
        two=normalize_request(self.db,{'recipe_id':recipe['id'],'destination':'1995-07-19T16:47'})
        self.assertEqual(one['rules'],two['rules']);self.assertNotEqual(one['destination'],two['destination'])
        self.assertEqual(options(self.db)['recipes'][0]['name'],'Summer cartoons')

    def test_historical_mode_uses_evidence_while_representative_mode_does_not_claim_it(self):
        import_plan(self.db,{'version':1,'airings':[{'id':'a','service_id':'kids',
            'content_id':'program:episode','title':'Synthetic known airing','start':'1995-07-18T16:30:00-04:00',
            'end':'1995-07-18T17:00:00-04:00','evidence_state':'exact','provenance':'Synthetic fixture'}]})
        exact=preflight(self.path,{**self.request,'mode':'historical'},real_now=REAL)
        plausible=preflight(self.path,self.request,real_now=REAL)
        self.assertEqual(exact['historical_evidence'],'exact');self.assertEqual(plausible['historical_evidence'],'composed')

    def test_dst_gap_and_unknown_lineup_are_not_silently_adjusted(self):
        with self.assertRaises(ValueError):normalize_request(self.db,{**self.request,'destination':'1995-04-02T02:30'})
        with self.assertRaises(ValueError):normalize_request(self.db,{**self.request,'mode':'historical','destination':'2000-07-01T08:00'})
        period=launch(self.path,{**self.request,'destination':'2000-07-01T08:00'},real_now=REAL)
        with connect(context_path(self.path,period['context_id'])) as db:
            self.assertEqual(db.execute('SELECT name FROM provider WHERE id="context-personal"').fetchone()[0],'Personal representative lineup')

    def test_concurrent_launches_share_one_timeline_and_context_ids_are_not_paths(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:launch(self.path,self.request,real_now=REAL),range(2)))
        self.assertEqual(results[0]['context_id'],results[1]['context_id'])
        self.assertEqual(len(list((self.folder/'contexts').glob('*.sqlite'))),1)
        with self.assertRaises(ValueError):context_path(self.path,'../../station.sqlite')

    def test_new_shared_catalog_entries_do_not_reroll_a_saved_timeline(self):
        result=launch(self.path,self.request,real_now=REAL);ident=result['context_id']
        path=context_path(self.path,ident)
        with connect(path) as session:before=[tuple(r) for r in session.execute('SELECT * FROM segment ORDER BY id')]
        doc=library()
        for row in doc['sources']:row['id']='new-'+row['id']
        for row in doc['assets']:row['id']='new-'+row['id'];row['source_id']='new-'+row['source_id']
        for row in doc['programs']:row['id']='new-'+row['id'];row['parts']=['new-'+part for part in row['parts']]
        import_library(self.db,doc,self.folder,verify_media=False)
        sync_catalog(self.path,ident)
        with connect(path) as session:
            self.assertIsNotNone(session.execute('SELECT 1 FROM program WHERE id="new-episode"').fetchone())
            self.assertEqual([tuple(r) for r in session.execute('SELECT * FROM segment ORDER BY id')],before)

    def test_same_day_destinations_do_not_provide_a_hidden_shuffle(self):
        a=launch(self.path,self.request,real_now=REAL)
        b=launch(self.path,{**self.request,'destination':'1995-07-18T16:48'},real_now=REAL)
        with connect(context_path(self.path,a['context_id'])) as first, connect(context_path(self.path,b['context_id'])) as second:
            cutoff=min(first.execute('SELECT max(end_ms) FROM broadcast').fetchone()[0],second.execute('SELECT max(end_ms) FROM broadcast').fetchone()[0])
            # Both destinations use the same day/order; only their clock offsets differ.
            query='''SELECT b.service_id,s.start_ms,s.end_ms,s.asset_id FROM segment s JOIN broadcast b
                ON b.id=s.broadcast_id WHERE s.start_ms<? ORDER BY b.service_id,s.start_ms'''
            left=[tuple(r) for r in first.execute(query,(cutoff,))]
            right=[tuple(r) for r in second.execute(query,(cutoff,))]
            self.assertEqual(left,right)

    def test_unfiltered_surfing_returns_the_original_station_not_a_recomposed_copy(self):
        extend(self.db,real_now=REAL);before=self.station_snapshot()
        check=preflight(self.path,{'mode':'surfing','service_id':'kids'},real_now=REAL)
        result=launch(self.path,{'mode':'surfing','service_id':'kids'},real_now=REAL)
        self.assertTrue(check['resuming']);self.assertIsNone(result['context_id'])
        self.assertEqual(result['url'],'/?channel=kids');self.assertEqual(self.station_snapshot(),before)
        self.assertEqual(self.db.execute('SELECT count(*) FROM viewing_context').fetchone()[0],0)

    def test_representative_session_keeps_evidence_available_for_the_historical_manager_view(self):
        import_plan(self.db,{'version':1,'airings':[{'id':'a','service_id':'kids',
            'content_id':'program:episode','title':'Synthetic known airing','start':'1995-07-18T16:30:00-04:00',
            'end':'1995-07-18T17:00:00-04:00','evidence_state':'exact','provenance':'Synthetic fixture'}]})
        context=launch(self.path,self.request,real_now=REAL)
        from retro_tv.manager import assess
        with connect(context_path(self.path,context['context_id'])) as db:
            now=extend(db,real_now=REAL)
            current=db.execute('SELECT evidence FROM broadcast WHERE service_id="kids" AND start_ms<=? AND end_ms>?',(now,now)).fetchone()[0]
            self.assertEqual(current,'composed')
            analysis=assess(db,{'service_id':'kids','date':'1995-07-18','mode':'historical'})
            self.assertEqual(analysis['known_schedule_percent'],2.1)
            self.assertEqual(db.execute('SELECT mode FROM viewing_mode').fetchone()[0],'representative')
