import unittest
import test_timelines as fixtures
from retro_tv import block_party,playlists,timelines
from retro_tv.catalog import connect
from test_station import REAL

class QualityOfLifeTest(unittest.TestCase):
    setUp=fixtures.TimelineTest.setUp
    tearDown=fixtures.TimelineTest.tearDown

    def test_matches_use_filters_duration_exclusions_files_and_leave_station_fixed(self):
        before=fixtures.TimelineTest.station_snapshot(self)
        request={**self.request,'rules':{'block_minutes':30,'tags':['cartoon']}}
        result=block_party.match_count(self.db,request)
        self.assertEqual(result['programs'],1);self.assertEqual(result['duration_ms'],1200000)
        self.assertEqual(block_party.match_count(self.db,{**request,'rules':{'block_minutes':15}})['programs'],0)
        self.assertEqual(block_party.match_count(self.db,{**request,'rules':{'block_minutes':30,'tags':['unavailable']}})['programs'],0)
        self.assertEqual(fixtures.TimelineTest.station_snapshot(self),before)
        (self.folder/'act1.mp4').unlink()
        result=block_party.match_count(self.db,request)
        self.assertEqual(result['programs'],0);self.assertEqual(result['offline_programs'],1)

    def test_pins_copies_and_delete_cascade(self):
        block=playlists.generate(self.db,{'selection':{**self.request,'rules':{'block_minutes':30}},'name':'Pinned'})
        other=playlists.generate(self.db,{'selection':{**self.request,'rules':{'block_minutes':30}},'name':'Newer'})
        playlists.pin(self.db,{'id':block['id'],'pinned':True})
        self.assertEqual(playlists.listing(self.db)['blocks'][0]['id'],block['id'])
        launched=timelines.launch(self.path,{'block_id':block['id']},real_now=REAL)
        doc={k:block[k] for k in ('version','name','duration_minutes','selection','items')};doc['name']='Edited'
        block=playlists.save(self.db,{'id':block['id'],'revision':1,'document':doc})
        listed=playlists.listing(self.db)['blocks'][0]
        self.assertEqual(listed['copies'][0]['id'],launched['context_id'])
        self.assertEqual(listed['copies'][0]['revision'],1)
        # Saving unchanged content must rejoin the existing snapshot, not reset it.
        same=timelines.launch(self.path,{'block_id':block['id']},real_now=REAL)
        block=playlists.save(self.db,{'id':block['id'],'revision':block['revision'],'document':doc})
        resumed=timelines.launch(self.path,{'block_id':block['id']},real_now=REAL+1000)
        self.assertEqual(same['context_id'],resumed['context_id'])
        playlists.delete(self.db,{'id':block['id'],'revision':block['revision']})
        self.assertEqual(self.db.execute('SELECT count(*) FROM party_pin').fetchone()[0],0)
        with connect(timelines.context_path(self.path,launched['context_id'])) as db:
            self.assertTrue(db.execute('SELECT count(*) FROM segment').fetchone()[0])
