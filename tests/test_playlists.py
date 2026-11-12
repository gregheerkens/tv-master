import unittest
import test_timelines as fixtures
from retro_tv import playlists, timelines
from retro_tv.catalog import connect
from retro_tv.scheduler import extend, tune
from test_station import REAL

class PlaylistTest(unittest.TestCase):
    setUp=fixtures.TimelineTest.setUp
    tearDown=fixtures.TimelineTest.tearDown

    def generate(self):
        return playlists.generate(self.db,{'selection':{**self.request,'rules':{'block_minutes':30}},'name':'Test block'})

    def document(self,block):
        return {k:block[k] for k in ('version','name','duration_minutes','selection','items')}

    def test_generate_edit_regenerate_delete_and_published_copy_is_immutable(self):
        before=fixtures.TimelineTest.station_snapshot(self)
        block=self.generate();self.assertTrue(block['items'])
        self.assertEqual(fixtures.TimelineTest.station_snapshot(self),before)
        session=timelines.launch(self.path,{'block_id':block['id']},real_now=REAL)
        path=timelines.context_path(self.path,session['context_id'])
        with connect(path) as db:
            published=[tuple(r) for r in db.execute('SELECT * FROM segment ORDER BY id')]
        doc=self.document(block);doc['name']='Changed';doc['items']=[{'asset_id':'act2'},{'asset_id':'act1'}]
        saved=playlists.save(self.db,{'id':block['id'],'revision':block['revision'],'document':doc})
        self.assertEqual(saved['revision'],2)
        with self.assertRaises(ValueError):playlists.save(self.db,{'id':block['id'],'revision':1,'document':doc})
        regenerated=playlists.generate(self.db,{'id':saved['id']})
        self.assertNotEqual(regenerated['id'],saved['id'])
        changed_context=timelines.launch(self.path,{'block_id':saved['id']},real_now=REAL)
        self.assertNotEqual(session['context_id'],changed_context['context_id'])
        playlists.delete(self.db,{'id':saved['id'],'revision':2})
        timelines.sync_catalog(self.path,session['context_id'])
        with connect(path) as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM segment ORDER BY id')][:len(published)],published)
        self.assertEqual(len(playlists.listing(self.db)['blocks']),1)

    def test_json_roundtrip_order_and_gap_budget(self):
        block=self.generate();doc=self.document(block)
        doc['items']=[{'asset_id':'act2'},{'asset_id':'act1'}]
        saved=playlists.save(self.db,{'document':doc})
        launched=timelines.launch(self.path,{'block_id':saved['id']},real_now=REAL)
        with connect(timelines.context_path(self.path,launched['context_id'])) as db:
            rows=list(db.execute('SELECT s.* FROM segment s JOIN broadcast b ON b.id=s.broadcast_id WHERE b.service_id="kids" ORDER BY s.start_ms LIMIT 3'))
            self.assertEqual([r['asset_id'] for r in rows],['act2','act1',None])
            self.assertEqual(rows[-1]['end_ms']-rows[0]['start_ms'],30*60000)
        doc['items']=[{'asset_id':'act1'}]*4
        with self.assertRaises(ValueError):playlists.save(self.db,{'document':doc})
        doc['items']=[{'asset_id':'unknown'}]
        with self.assertRaises(ValueError):playlists.save(self.db,{'document':doc})
        doc['items']=[{'path':'/etc/passwd'}]
        with self.assertRaises(ValueError):playlists.save(self.db,{'document':doc})
        doc['items']=[]
        empty=playlists.save(self.db,{'document':doc});self.assertEqual(empty['items'],[])
