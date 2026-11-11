import json
import sqlite3
import unittest
from unittest.mock import patch
import test_manager
from retro_tv import blocks
from retro_tv.scheduler import extend,tune,guide,compose
from retro_tv.timelines import normalize_request,build
from retro_tv.health import timeline_health,resolve_path
from test_station import REAL

class CompleteBlockTest(unittest.TestCase):
    setUp=test_manager.ManagerTest.setUp
    tearDown=test_manager.ManagerTest.tearDown

    def value(self,**changes):
        return {'complete_block':True,'title':'Synthetic 90-minute Fox Kids block','service_id':'kids','duration_ms':5400000,
            'source_in_ms':0,'source_out_ms':5400000,'anchor':{'title':'Power Rangers (synthetic anchor)','aired_at':'1995-07-18T09:00:00-04:00','source_offset_ms':1800000},
            'path':str(self.folder/'act1.mp4'),'seasonal':False,**changes}

    def test_known_airing_anchors_whole_local_block_and_midshow_tuning(self):
        now=extend(self.db,real_now=REAL);before=[tuple(r) for r in self.db.execute('SELECT * FROM broadcast')]
        result=blocks.register(self.db,self.value(),verify_media=False)
        self.assertEqual(result['end_ms']-result['start_ms'],5400000)
        request=normalize_request(self.db,{'mode':'historical','service_id':'kids','destination':'1995-07-18T09:10'})
        scratch,now=build(self.db,request,REAL)
        try:
            playing=tune(scratch,'kids',now);self.assertEqual(playing['kind'],'block');self.assertEqual(playing['offset_ms'],40*60000)
            published=scratch.execute("SELECT * FROM broadcast WHERE service_id='kids' AND start_ms<=? AND end_ms>?",(now,now)).fetchone()
            self.assertEqual(published['start_ms'],result['start_ms']);self.assertEqual(published['end_ms'],result['end_ms'])
            self.assertEqual(scratch.execute('SELECT count(*) FROM segment WHERE broadcast_id=?',(published['id'],)).fetchone()[0],1)
            h=timeline_health(scratch,'kids',result['start_ms'],result['end_ms'])[published['id']]
            self.assertEqual(h['status'],'ready');self.assertEqual(h['block_ms'],5400000);self.assertEqual(h['commercial_ms'],0)
        finally:scratch.close()
        self.assertEqual([tuple(r) for r in self.db.execute('SELECT * FROM broadcast')],before)
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('UPDATE complete_block SET start_ms=start_ms+1')
        self.db.rollback()

    def test_crop_anchor_arithmetic_and_conflicting_known_points(self):
        value=self.value(source_in_ms=300000)
        a,b,left,right=blocks.bracket(value)
        self.assertEqual(a,blocks.timestamp('1995-07-18T08:35:00-04:00'));self.assertEqual(b,blocks.timestamp('1995-07-18T10:00:00-04:00'))
        with self.assertRaises(ValueError):blocks.register(self.db,self.value(known_points=[{'aired_at':'1995-07-18T09:05:00-04:00','source_offset_ms':0}]),verify_media=False)
        self.assertEqual(self.db.execute('SELECT count(*) FROM complete_block').fetchone()[0],0)

    def test_remote_opt_in_and_measured_playback_health(self):
        value=self.value(url='https://archive.org/download/synthetic-test/recording.mp4',allow_remote=True)
        value.pop('path');result=blocks.register(self.db,value)
        self.assertEqual(blocks.stream(self.db,self.db.execute('SELECT sha256 FROM source WHERE id=?',(result['source_id'],)).fetchone()[0])['availability'],'unknown')
        request=normalize_request(self.db,{'mode':'historical','service_id':'kids','destination':'1995-07-18T09:10'})
        scratch,now=build(self.db,request,REAL)
        try:
            playing=tune(scratch,'kids',now);self.assertTrue(playing['remote']);self.assertEqual(playing['offset_ms'],2400000)
            h=list(timeline_health(scratch,'kids',now,now+60000).values())[0];self.assertEqual(h['status'],'unknown');self.assertEqual(h['playable_ms'],0)
            blocks.report_playback(scratch,{'segment_id':playing['id'],'status':'online'},now)
            h=list(timeline_health(scratch,'kids',now,now+60000).values())[0];self.assertEqual(h['status'],'ready');self.assertEqual(h['playable_ms'],60000)
            blocks.report_playback(scratch,{'segment_id':playing['id'],'status':'offline'},now)
            self.assertEqual(list(timeline_health(scratch,'kids',now,now+60000).values())[0]['status'],'offline')
            cached=self.folder/'cached.mp4';cached.write_bytes(b'synthetic cached stream')
            with patch('retro_tv.blocks.probe',return_value=5400000):blocks.attach_presentation(scratch,{'block_id':result['id'],'path':str(cached),'approved':True})
            self.assertFalse(tune(scratch,'kids',now)['remote'])
            self.assertEqual(list(timeline_health(scratch,'kids',now,now+60000).values())[0]['status'],'ready')
        finally:scratch.close()
        value['allow_remote']=False
        with self.assertRaises(ValueError):blocks.register(self.db,value)

    def test_optional_local_presentation_preserves_original_and_anchor(self):
        result=blocks.register(self.db,self.value(),verify_media=False)
        original=dict(self.db.execute('SELECT * FROM complete_block').fetchone());source=dict(self.db.execute('SELECT * FROM source WHERE id=?',(result['source_id'],)).fetchone())
        copy=self.folder/'restored.mp4';copy.write_bytes(b'synthetic restored copy')
        with patch('retro_tv.blocks.probe',return_value=5400000):blocks.attach_presentation(self.db,{'block_id':result['id'],'path':str(copy),'approved':True})
        self.assertEqual(resolve_path(self.db,source['path'],source['sha256']),str(copy))
        self.assertEqual(dict(self.db.execute('SELECT * FROM complete_block').fetchone()),original)
        self.assertTrue(__import__('pathlib').Path(source['path']).exists())
        with patch('retro_tv.blocks.probe',return_value=5300000):
            with self.assertRaises(ValueError):blocks.attach_presentation(self.db,{'block_id':result['id'],'path':str(copy),'approved':True})
