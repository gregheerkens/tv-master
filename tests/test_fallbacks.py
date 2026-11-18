import unittest
import test_timelines as fixtures
from test_station import library,REAL
from retro_tv.catalog import import_library,connect
from retro_tv.records import import_records
from retro_tv.manager import import_plan
from retro_tv.timelines import launch,context_path

class FallbackTest(unittest.TestCase):
    setUp=fixtures.TimelineTest.setUp
    tearDown=fixtures.TimelineTest.tearDown
    def prepare(self,same_content=False):
        doc=library()
        for s in doc['sources']:
            s['id']='alt-'+s['id'];s['path']='alt-'+s['path'];(self.folder/s['path']).write_bytes(b'synthetic alternate copy')
        for a in doc['assets']:a['id']='alt-'+a['id'];a['source_id']='alt-'+a['source_id']
        for p in doc['programs']:p['id']='alternate';p['title']='Alternate program';p['parts']=['alt-'+i for i in p['parts']]
        import_library(self.db,doc,self.folder,verify_media=False)
        if same_content:import_records(self.db,{'version':1,'program_links':[{'program_id':'alternate','content_id':'program:episode'}]})
        else:import_records(self.db,{'version':1,'fallbacks':[{'content_id':'program:episode','fallback_id':'program:alternate','note':'Approved related replacement','priority':1}]})
        import_plan(self.db,{'version':1,'airings':[{'id':'original-airing','service_id':'kids','content_id':'program:episode','title':'Original','start':'1995-07-18T16:30:00-04:00','end':'1995-07-18T17:00:00-04:00','evidence_state':'exact','provenance':'Synthetic test'}]})
        (self.folder/'act1.mp4').unlink()
    def test_related_backup_uses_fixed_slot_and_marks_substitution(self):
        self.prepare()
        result=launch(self.path,{**self.request,'mode':'historical','rules':{}},real_now=REAL)
        with connect(context_path(self.path,result['context_id'])) as db:
            row=db.execute('SELECT * FROM broadcast WHERE service_id="kids" AND program_id IS NOT NULL').fetchone()
            self.assertEqual(row['program_id'],'alternate');self.assertEqual(row['evidence'],'substituted');self.assertEqual(row['end_ms']-row['start_ms'],1800000)
    def test_alternate_copy_keeps_same_identity_exact(self):
        self.prepare(True)
        result=launch(self.path,{**self.request,'mode':'historical','rules':{}},real_now=REAL)
        with connect(context_path(self.path,result['context_id'])) as db:
            row=db.execute('SELECT * FROM broadcast WHERE program_id IS NOT NULL').fetchone()
            self.assertEqual(row['program_id'],'alternate');self.assertEqual(row['evidence'],'exact')
