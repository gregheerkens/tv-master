"""Generate tiny synthetic source videos; no copyrighted programming is included."""
import json
import subprocess
from pathlib import Path
from .catalog import import_library
from .scheduler import initialize


def create(db, directory):
    if db.execute('SELECT 1 FROM state').fetchone():
        raise ValueError('station already initialized; demo cannot reset it')
    directory=Path(directory).resolve()
    directory.mkdir(parents=True,exist_ok=True)
    config={'historical_start':'1995-07-18T16:00:00-04:00','timezone':'America/New_York',
            'seed':'synthetic-demo','market':{'id':'demo','name':'Synthetic Rochester example'},
            'provider':{'id':'home','name':'Personal demo; not a historical lineup'},
            'lineup':{'id':'demo-1995','valid_from':'1995-01-01','valid_until':'2100-01-01'},
            'channels':[{'number':'1','service_id':'kids','name':'SUMMER CLUB'},
                        {'number':'2','service_id':'late','name':'LOCAL AFTER DARK'}]}
    sources=[];assets=[];programs=[]
    for ident,color,duration,kind in [('show-a','navy',120,'program'),('show-b','purple',150,'program'),
                                     ('ad','teal',60,'commercial'),('bumper','maroon',5,'bumper')]:
        path=directory/f'{ident}.mp4'
        if not path.exists():
            subprocess.run(['ffmpeg','-nostdin','-v','error','-n','-f','lavfi','-i',
                            f'color=c={color}:s=640x480:r=24','-f','lavfi','-i','anullsrc=r=48000:cl=stereo',
                            '-t',str(duration),'-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',
                            '-movflags','+faststart',str(path)],check=True)
        sources.append({'id':ident,'path':str(path),'provenance':{'origin':'generated FFmpeg color/silence fixture'}})
        assets.append({'id':ident,'source_id':ident,'title':f'Synthetic {ident}','kind':kind,
                       'valid_from':'1990-01-01','valid_until':'2100-01-01','services':[],
                       'metadata':{'review_status':'approved','evidence':'synthetic fixture'}})
        if kind=='program':
            programs.append({'id':ident,'title':f'Test Pattern Theater: {ident}', 'parts':[ident],
                             'services':[],'valid_from':'1990-01-01','valid_until':'2100-01-01'})
    initialize(db,config)
    document={'version':1,'sources':sources,'assets':assets,'programs':programs}
    # Short programs intentionally leave visible slates instead of thousands of tiny fake ads.
    for p in document['assets']:
        if p['kind']!='program':
            p['services']=['kids']
    import_library(db,document,directory)
    (directory/'library.json').write_text(json.dumps(document,indent=2))
