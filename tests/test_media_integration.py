"""Optional real FFmpeg integration, using only locally generated colors/silence."""
import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from retro_tv.catalog import connect, import_library, probe
from retro_tv.companion import analyze, export_review, extract
from retro_tv.scheduler import initialize
from retro_tv.ingest import ingest_path
from retro_tv.manager import attach_media


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg not installed')
class MediaIntegration(unittest.TestCase):
    def test_detect_review_export_import_extract_preserves_original(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);source=directory/'tape.mp4'
            subprocess.run(['ffmpeg','-nostdin','-v','error','-n',
                '-f','lavfi','-i','color=c=blue:s=320x240:r=24:d=2',
                '-f','lavfi','-i','color=c=black:s=320x240:r=24:d=0.5',
                '-f','lavfi','-i','color=c=red:s=320x240:r=24:d=2',
                '-f','lavfi','-i','anullsrc=r=48000:cl=stereo',
                '-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]',
                '-map','[v]','-map','3:a','-t','4.5','-c:v','libx264','-c:a','aac',
                '-pix_fmt','yuv420p',str(source)],check=True,capture_output=True)
            original=source.read_bytes()
            document=analyze(source,{'kind':'recorded','recorded_date':'1995','seasonal':False})
            self.assertEqual(len(document['candidates']),2)
            self.assertAlmostEqual(document['candidates'][0]['out_ms'],2250,delta=50)
            with self.assertRaises(ValueError):export_review(document)
            for index,candidate in enumerate(document['candidates']):
                candidate.update(title=f'Synthetic spot {index}',kind='commercial',
                    summary='Generated color and silence; not a historical ad',
                    valid_from='1995-01-01',valid_until='1996-01-01',services=['kids'],
                    identification_evidence='Synthetic integration fixture',review_status='approved')
            manifest=export_review(document)
            db=connect(directory/'catalog.sqlite')
            config=json.loads((Path(__file__).resolve().parents[1]/'examples/station.json').read_text())
            initialize(db,config)
            context={'kind':'recorded','recorded_date':'1995','seasonal':False}
            with self.assertRaises(ValueError):ingest_path(db,source,{'kind':'ripped'})
            with self.assertRaises(ValueError):ingest_path(db,directory,context)
            ingest_path(db,source,context)
            import_library(db,manifest,directory)
            self.assertEqual(db.execute('SELECT count(*) FROM source').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM asset').fetchone()[0],2)
            self.assertEqual(extract(document,directory/'cuts'),2)
            for path in (directory/'cuts').glob('*.mp4'):
                self.assertAlmostEqual(probe(path),2250,delta=100)
            self.assertEqual(source.read_bytes(),original)
            self.assertEqual(len(list(directory.glob('*.mp4'))),1)
            content_id=db.execute('SELECT content_id FROM asset_content ORDER BY asset_id LIMIT 1').fetchone()[0]
            linked=attach_media(db,{'content_id':content_id,'folder':str(directory),'file':'tape.mp4',
                'valid_from':'1995-01-01','valid_until':'1996-01-01'})
            self.assertEqual(db.execute('SELECT content_id FROM asset_content WHERE asset_id=?',(linked['asset_id'],)).fetchone()[0],content_id)
            with self.assertRaises(ValueError):attach_media(db,{'content_id':content_id,'folder':str(directory/'cuts'),'file':'../tape.mp4'})
            db.close()


if __name__=='__main__':unittest.main()
