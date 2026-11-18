import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from retro_tv.catalog import connect
from retro_tv.rochester import import_packet,resolve

class RochesterTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'packet.json';self.db=connect(Path(self.tmp.name)/'station.sqlite')
        self.doc={'meta':{'timeline_id':'test-packet','timezone':'America/New_York','start':'1995-01-01','end':'2003-12-31'},'channels':[{'id':'NICK','label':'Nickelodeon'}],'catalog':[{'id':'show','title':'Show'}],'sources':[{'id':'S1','url':'https://example.org/research'}],'assets':[],'airings':[{'id':'D1','date':'2000-09-06','channel':'NICK','start':930,'end':960,'program':'Show','episode':'Named episode','priority':90,'source':'S1','evidence':'Dated cable listing'}],'rules':[{'id':'R1','channel':'NICK','valid_from':'1995-01-01','valid_to':'2003-12-31','days':[0,1,2,3,4],'start':900,'end':990,'program':'Show','episode':'','priority':30,'source':'S1','evidence':'Seasonal fallback'}]}
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def write(self):self.path.write_text(json.dumps(self.doc));return self.path
    def test_resolution_idempotency_estimates_and_atomic_updates(self):
        first=import_packet(self.db,self.write(),start='2000-09-06',through='2000-09-06')
        self.assertEqual(first['inserted'],3)
        rows=list(self.db.execute('SELECT * FROM historical_airing ORDER BY start_ms'))
        self.assertEqual([r['evidence_state'] for r in rows],['inferred','schedule_exact','inferred'])
        self.assertEqual(import_packet(self.db,self.path,start='2000-09-06',through='2000-09-06')['unchanged'],3)
        self.doc['airings'][0]['end']=975
        changed=import_packet(self.db,self.write(),start='2000-09-06',through='2000-09-06')
        self.assertTrue(changed['updated'] or changed['removed'])
        result=import_packet(self.db,self.path,start='2000-09-06',through='2000-09-06',include_estimates=False)
        self.assertEqual(self.db.execute('SELECT count(*) FROM historical_airing').fetchone()[0],1)
        self.assertTrue(result['unresolved_minutes'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM source').fetchone()[0],0)
        before=list(self.db.execute('SELECT * FROM historical_airing'))
        self.doc['airings'][0]['source']='changed';self.doc['airings'][0]['channel']='bad'
        with self.assertRaises(ValueError):import_packet(self.db,self.write(),start='2000-09-06',through='2000-09-06')
        self.assertEqual([tuple(r) for r in before],[tuple(r) for r in self.db.execute('SELECT * FROM historical_airing')])
    def test_zip_read_does_not_extract_or_execute_and_weekend_gaps(self):
        path=Path(self.tmp.name)/'packet.zip'
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('TV-Master-Rochester-data.json',json.dumps(self.doc));z.writestr('../do-not-extract.py','raise Exception()')
        result=import_packet(self.db,path,start='2000-09-09',through='2000-09-09')
        self.assertEqual(result['inserted'],0);self.assertEqual(result['unresolved_minutes'],240)
        self.assertFalse((Path(self.tmp.name).parent/'do-not-extract.py').exists())

    def test_published_research_update_rolls_back_entire_packet(self):
        import_packet(self.db,self.write(),start='2000-09-06',through='2000-09-06')
        row=self.db.execute('SELECT * FROM historical_airing WHERE title="Show" AND evidence_state="schedule_exact"').fetchone()
        with self.db:
            self.db.execute('INSERT INTO broadcast VALUES (?,?,?,?,?,?,?)',('published',row['service_id'],row['start_ms'],row['end_ms'],'Show',None,'composed'))
            self.db.execute('INSERT INTO broadcast_context VALUES (?,?,?,?)',('published',row['id'],'schedule_exact','{}'))
        before=[tuple(r) for r in self.db.execute('SELECT * FROM historical_airing ORDER BY id')]
        digest=self.db.execute('SELECT sha256 FROM reference_packet').fetchone()[0]
        self.doc['airings'][0]['end']=975
        with self.assertRaisesRegex(ValueError,'published airing'):
            import_packet(self.db,self.write(),start='2000-09-06',through='2000-09-06')
        self.assertEqual(before,[tuple(r) for r in self.db.execute('SELECT * FROM historical_airing ORDER BY id')])
        self.assertEqual(digest,self.db.execute('SELECT sha256 FROM reference_packet').fetchone()[0])
