import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from retro_tv.catalog import connect, import_library, fingerprint
from retro_tv.scheduler import initialize, extend, compose, guide
from retro_tv.manager import import_plan, assess, set_override, repair_source, attach_media
from retro_tv.health import timeline_health, resolve_path
from retro_tv.records import import_records
from test_station import ROOT, REAL, library


class ManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        self.db=connect(self.folder/'station.sqlite')
        initialize(self.db,json.loads((ROOT/'examples/station.json').read_text()),real_now=REAL)
        document=library()
        for source in document['sources']:
            path=self.folder/source['path'];path.write_bytes(('synthetic '+source['id']).encode())
            source['sha256']=fingerprint(path)
        import_library(self.db,document,self.folder,verify_media=False)

    def tearDown(self):self.db.close();self.temp.cleanup()

    def plan(self,content='program:episode',requirements=None):
        return {'version':1,'airings':[{'id':'listing','service_id':'kids','content_id':content,
            'title':'Synthetic scheduled episode','start':'1995-07-18T16:00:00-04:00',
            'end':'1995-07-18T16:30:00-04:00','evidence_state':'exact',
            'provenance':{'origin':'Synthetic test, not a historical assertion'},
            'requirements':requirements or []}]}

    def snapshot(self):
        return {t:[tuple(r) for r in self.db.execute(f'SELECT * FROM {t}')] for t in ('state','broadcast','segment','broadcast_context')}

    def test_three_day_assessment_cannot_change_station_or_published_guide(self):
        extend(self.db,real_now=REAL);before=self.snapshot()
        result=assess(self.db,{'service_id':'kids','date':'1995-07-18','days':3,'mode':'channel'})
        self.assertTrue(result['simulation_only']);self.assertEqual(len(result['daily']),3)
        self.assertGreater(result['program_ms'],0);self.assertGreater(result['repeat_passes_needed'],1)
        self.assertEqual(result['known_schedule_percent'],0)
        self.assertFalse(result['historically_complete']);self.assertEqual(self.snapshot(),before)

    def test_theme_forecast_respects_tags_and_reports_unique_inventory(self):
        self.db.execute('UPDATE content SET tags=? WHERE id=?',('["cartoon"]','program:episode'));self.db.commit()
        hit=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'theme','tags':['cartoon']})
        miss=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'theme','tags':['horror']})
        self.assertEqual(hit['unique_programs'],1);self.assertGreater(hit['program_ms'],0)
        self.assertEqual(miss['unique_programs'],0);self.assertEqual(miss['playable_percent'],0)
        self.assertIsNone(hit['known_schedule_percent'])
        self.assertEqual(self.db.execute('SELECT mode FROM channel_profile WHERE service_id="kids"').fetchone()[0],'custom')
        import_plan(self.db,self.plan())
        theme=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'theme','tags':['cartoon']})
        self.assertEqual(theme['history'],[]);self.assertEqual(theme['requirements'],[])

    def test_known_missing_episode_stays_in_historical_evidence(self):
        import_records(self.db,{'version':1,'contents':[{'id':'missing','kind':'episode','title':'Unowned episode'}]})
        import_plan(self.db,self.plan('missing'))
        result=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'historical'})
        self.assertEqual(result['known_schedule_percent'],2.1)
        self.assertTrue(any(g['airing_id']=='listing' and 'Synthetic scheduled' in g['title'] for g in result['gaps']))
        self.assertFalse(result['historically_complete'])
        self.assertEqual(self.db.execute('SELECT content_id FROM historical_airing').fetchone()[0],'missing')

    def test_imported_listing_controls_composition_and_known_ad_gap_is_visible(self):
        import_records(self.db,{'version':1,'contents':[{'id':'missing-ad','kind':'commercial','title':'Known missing spot'}]})
        import_plan(self.db,self.plan(requirements=[{'id':'spot','kind':'commercial','content_id':'missing-ad',
            'duration_ms':30000,'note':'Known missing toy commercial','provenance':'Synthetic fixture'}]))
        now=extend(self.db,real_now=REAL)
        row=self.db.execute('SELECT * FROM broadcast WHERE service_id="kids" ORDER BY start_ms LIMIT 1').fetchone()
        self.assertEqual(row['program_id'],'episode');self.assertEqual(row['evidence'],'exact')
        health=timeline_health(self.db,'kids',now,now+1800000)[row['id']]
        self.assertEqual(health['status'],'partial')
        self.assertTrue(any('Known missing toy' in reason for reason in health['reasons']))
        result=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'historical'})
        self.assertEqual(result['requirements'][0]['status'],'missing')

    def test_explicit_substitution_is_labeled_and_does_not_rewrite_published_gap(self):
        import_records(self.db,{'version':1,'contents':[{'id':'missing','kind':'episode','title':'Missing'}]})
        import_plan(self.db,self.plan('missing'));extend(self.db,real_now=REAL);before=self.snapshot()
        set_override(self.db,{'airing_id':'listing','program_id':'episode','note':'Use another reviewed episode'})
        result=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'historical'})
        self.assertEqual(result['substituted_blocks'],1);self.assertFalse(result['historically_complete'])
        self.assertEqual(self.snapshot(),before)

    def test_matching_source_repair_restores_existing_segments_without_rewriting_them(self):
        now=extend(self.db,real_now=REAL);before=self.snapshot()
        old=self.folder/'act1.mp4';replacement=self.folder/'relocated.mp4';old.rename(replacement)
        initial=timeline_health(self.db,'kids',now,now+1800000)
        self.assertTrue(any(h['status']=='offline' for h in initial.values()))
        repair_source(self.db,{'source_id':'act1','path':str(replacement)})
        repaired=timeline_health(self.db,'kids',now,now+1800000)
        self.assertFalse(any(h['status']=='offline' for h in repaired.values()))
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(resolve_path(self.db,str(old),fingerprint(replacement)),str(replacement))
        with self.assertRaises(ValueError):repair_source(self.db,{'source_id':'act1','path':str(self.folder/'ad.mp4')})

    def test_source_absence_is_not_counted_as_playable(self):
        extend(self.db,real_now=REAL)
        (self.folder/'act1.mp4').unlink();(self.folder/'act2.mp4').unlink()
        result=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'channel'})
        self.assertEqual(result['program_ms'],0);self.assertGreater(result['missing_file_ms'],0)
        self.assertEqual(result['unique_programs'],0)

    def test_invalid_listing_import_rolls_back(self):
        doc=self.plan();doc['airings'].append({**doc['airings'][0],'id':'overlap'})
        with self.assertRaises(sqlite3.IntegrityError):import_plan(self.db,doc)
        self.assertEqual(self.db.execute('SELECT count(*) FROM historical_airing').fetchone()[0],0)
        with self.assertRaises(ValueError):assess(self.db,{'service_id':'kids','date':'1995-07-18','days':4})
