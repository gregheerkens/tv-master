import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from retro_tv.catalog import connect, import_library
from retro_tv.scheduler import initialize, extend, tune
from retro_tv import records
from test_station import library, REAL, ROOT


class RecordsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=connect(Path(self.temp.name)/'station.sqlite')
        initialize(self.db,json.loads((ROOT/'examples/station.json').read_text()),real_now=REAL)
        import_library(self.db,library(),self.temp.name,verify_media=False)

    def tearDown(self):
        self.db.close();self.temp.cleanup()

    def identity(self):
        records.import_records(self.db,{'version':1,'contents':[
            {'id':'series','kind':'series','title':'Synthetic Show'},
            {'id':'episode','kind':'episode','title':'Synthetic Show','parent_id':'series',
             'episode_title':None,'tags':['cartoon']}],
             'program_links':[{'program_id':'episode','content_id':'episode'}]})

    def test_identity_survives_recording_exclusion(self):
        self.identity()
        records.quality(self.db,'act1',20,'Tracking damage')
        records.alert(self.db,'tracking',asset_id='act1',code='tracking',details='Damaged lower field')
        # A quality warning does not itself hide the episode.
        now=extend(self.db,real_now=REAL)
        self.assertEqual(tune(self.db,'kids',now)['kind'],'bumper')
        before=[tuple(r) for r in self.db.execute('SELECT * FROM segment ORDER BY id')]
        records.set_preference(self.db,'act1',recording=True,note='Avoid this particular recording')
        extend(self.db,real_now=REAL+1800000)
        self.assertEqual([tuple(r) for r in self.db.execute('SELECT * FROM segment ORDER BY id')][:len(before)],before)
        self.assertIsNone(self.db.execute('SELECT program_id FROM broadcast WHERE service_id="kids" ORDER BY start_ms DESC LIMIT 1').fetchone()[0])
        self.assertEqual(self.db.execute('SELECT count(*) FROM content WHERE id="episode"').fetchone()[0],1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM content_preference WHERE never_schedule=1').fetchone()[0],0)

    def test_series_ban_inherits_and_never_rewrites_published_slots(self):
        self.identity();extend(self.db,real_now=REAL)
        before=[tuple(r) for r in self.db.execute('SELECT * FROM broadcast ORDER BY rowid')]
        records.set_preference(self.db,'series')
        extend(self.db,real_now=REAL+1800000)
        after=[tuple(r) for r in self.db.execute('SELECT * FROM broadcast ORDER BY rowid')]
        self.assertEqual(after[:len(before)],before)
        self.assertIsNone(self.db.execute('SELECT program_id FROM broadcast WHERE service_id="kids" ORDER BY start_ms DESC LIMIT 1').fetchone()[0])
        records.set_favorite(self.db,'series')
        self.assertEqual(self.db.execute('SELECT never_schedule,favorite FROM content_preference WHERE content_id="series"').fetchone()[:],(1,1))

    def test_seasonal_windows_union_and_network_context(self):
        self.identity()
        records.import_records(self.db,{'version':1,'networks':[{'id':'fictional','name':'Fictional Network'}],
          'affiliations':[{'id':'aff','service_id':'kids','network_id':'fictional',
              'valid_from':'1995-01-01','valid_until':'1996-01-01','evidence_state':'user_defined',
              'provenance':{'note':'Synthetic test, not a Rochester history claim'}}],
          'windows':[{'id':f'window-{m}','content_id':'episode','valid_from':'1995-01-01',
              'valid_until':'1996-01-01','months':[m],'network_id':'fictional',
              'evidence_state':'estimated','provenance':{'note':'Synthetic seasonal window'}} for m in (11,12)]})
        policy=records.Policy(self.db)
        self.assertFalse(policy.allowed('episode','kids','1995-07-18',program=True))
        self.assertTrue(policy.allowed('episode','kids','1995-11-18',program=True))
        self.assertTrue(policy.allowed('episode','kids','1995-12-18',program=True))
        self.assertFalse(policy.allowed('episode','late','1995-12-18',program=True))
        now=extend(self.db,real_now=REAL)
        self.assertEqual(tune(self.db,'kids',now)['kind'],'slate')

    def test_themed_channel_filters_program_content_tags(self):
        self.identity()
        records.import_records(self.db,{'version':1,'channels':[{'service_id':'kids','mode':'themed','theme_tags':['horror']}]})
        self.assertFalse(records.Policy(self.db).allowed('episode','kids','1995-07-18',program=True))
        records.import_records(self.db,{'version':1,'channels':[{'service_id':'kids','mode':'themed','theme_tags':['cartoon']}]})
        self.assertTrue(records.Policy(self.db).allowed('episode','kids','1995-07-18',program=True))

    def test_channel_lookup_keeps_ota_cable_and_network_separate(self):
        doc={'version':1,'channels':[{'service_id':'kids','mode':'historical'}],
            'networks':[{'id':'net','name':'Synthetic Network'}],
            'station_history':[{'id':'station','service_id':'kids','market_id':'rochester',
                 'call_sign':'TEST','broadcast_channel':'31','valid_from':'1995-01-01',
                 'valid_until':'1996-01-01','evidence_state':'user_defined','provenance':'Synthetic fixture'}],
            'affiliations':[{'id':'affiliate','service_id':'kids','network_id':'net','valid_from':'1995-01-01',
                 'valid_until':'1996-01-01','evidence_state':'user_defined','provenance':'Synthetic fixture'}]}
        records.import_records(self.db,doc)
        row=records.channel_lookup(self.db,'rochester','home','1995-07-18')[0]
        self.assertEqual((row['call_sign'],row['broadcast_channel'],row['cable_channel'],row['network']),
                         ('TEST','31','1','Synthetic Network'))
        self.assertEqual(records.channel_lookup(self.db,'rochester','home','1996-01-01'),[])
        # Conflicting historical claims must fail instead of choosing one silently.
        doc['station_history'][0]['id']='conflict'
        with self.assertRaises(sqlite3.IntegrityError):records.import_records(self.db,{'version':1,'station_history':doc['station_history']})

    def test_viewing_counts_are_explicit_and_idempotent(self):
        self.identity()
        records.import_records(self.db,{'version':1,'asset_links':[
            {'asset_id':'act1','content_id':'episode'},{'asset_id':'act2','content_id':'episode'}]})
        now=extend(self.db,real_now=REAL)
        segment=self.db.execute('SELECT s.* FROM segment s JOIN broadcast b ON b.id=s.broadcast_id WHERE b.service_id="kids" AND s.kind="program" ORDER BY s.start_ms LIMIT 1').fetchone()
        viewed_at=segment['start_ms']+15000
        records.record_view(self.db,'view-1',segment['id'],'local',10000,now_ms=viewed_at)
        records.record_view(self.db,'view-1',segment['id'],'local',10000,now_ms=viewed_at)
        counts=records.content_stats(self.db,'episode',viewed_at)
        self.assertEqual(counts['scheduled_occurrences'],144)
        self.assertEqual(counts['aired_occurrences'],1)
        self.assertEqual((counts['viewing_events'],counts['watched_ms']),(1,10000))
        with self.assertRaises(ValueError):records.record_view(self.db,'future',segment['id'],'local',10000,now_ms=now)

    def test_unowned_content_and_uncertain_episode_are_valid_but_uncited_dates_are_not(self):
        self.identity()
        self.assertIsNone(self.db.execute('SELECT episode_title FROM content WHERE id="episode"').fetchone()[0])
        records.import_records(self.db,{'version':1,'contents':[{'id':'missing','kind':'episode','title':'Not owned'}]})
        with self.assertRaises(ValueError):records.import_records(self.db,{'version':1,'contents':[
            {'id':'uncited','kind':'commercial','title':'Unknown','original_air_date':'1995-01-01'}]})
        self.assertEqual(self.db.execute('SELECT count(*) FROM content WHERE id="uncited"').fetchone()[0],0)


class LegacyMigrationTest(unittest.TestCase):
    def test_existing_database_backfills_without_changing_playout(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'legacy.sqlite'
            db=sqlite3.connect(path)
            db.executescript((ROOT/'retro_tv/schema.sql').read_text())
            db.execute('INSERT INTO service VALUES (?,?)',('station','Old Station'))
            db.execute('INSERT INTO source VALUES (?,?,?,?,?)',('source','/original.mp4',10000,'hash','{}'))
            db.execute('INSERT INTO asset VALUES (?,?,?,?,?,?,?,?,?,?)',('clip','source','Old clip','commercial',0,10000,'1995-01-01','1996-01-01','[]','{}'))
            db.execute('INSERT INTO broadcast VALUES (?,?,?,?,?,?,?)',('published','station',100,200,'Frozen',None,'missing'))
            before=list(db.execute('SELECT * FROM broadcast'));db.commit();db.close()
            db=connect(path)
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
            self.assertEqual(db.execute('SELECT content_id FROM asset_content WHERE asset_id="clip"').fetchone()[0],'asset:clip')
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM broadcast')],before)
            db.close();db=connect(path)
            self.assertEqual(db.execute('SELECT count(*) FROM content').fetchone()[0],1)
            db.close()
