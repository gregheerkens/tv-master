"""Optional worker: detect candidate boundaries, review metadata, export library JSON.

No imports from the player or scheduler. No title/date recognition is claimed by
the baseline detector. An identification adapter can enrich the review document.
"""
import argparse
import hashlib
import json
import re
import subprocess
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .ingest import validate_context, reuse_rule, add_recording_arguments, arguments_context


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                             '-of', 'json', str(path)], check=True, capture_output=True, text=True)
    return round(float(json.loads(result.stdout)['format']['duration'])*1000)


def boundaries(log, duration_ms):
    black = [(float(a),float(b)) for a,b in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', log)]
    silence = [float(t) for t in re.findall(r'silence_end: ([\d.]+)', log)]
    values = [{'at_ms':0, 'evidence':'source start', 'confidence':1.0}]
    for a,b in black:
        ms = round((a+b)*500)
        if 0 < ms < duration_ms and ms-values[-1]['at_ms'] >= 500:
            paired = any(a-.5 <= t <= b+.5 for t in silence)
            values.append({'at_ms':ms, 'evidence':'black + silence' if paired else 'black transition',
                           'confidence':.7 if paired else .4})
    values.append({'at_ms':duration_ms, 'evidence':'source end', 'confidence':1.0})
    return values


def analyze(path,context=None):
    context=validate_context(context)
    if context['kind']!='recorded':raise ValueError('recording analysis requires recorded-media context')
    path = Path(path).resolve(strict=True)
    duration = probe(path)
    result = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-i', str(path),
                             '-vf', 'blackdetect=d=0.15:pix_th=0.10',
                             '-af', 'silencedetect=n=-35dB:d=0.15', '-f', 'null', '-'],
                            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    cuts = boundaries(result.stderr, duration)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'version':1, 'source':{'id':digest[:24], 'path':str(path),
            'duration_ms':duration, 'sha256':digest, 'ingest':context,
            'provenance':{'origin':'user-supplied recording','analyzer':'ffmpeg black/silence baseline'}},
            'candidates':[{'id':f'{digest[:12]}-{i:04d}', 'in_ms':a['at_ms'], 'out_ms':b['at_ms'],
                           'boundary_evidence':a['evidence'], 'boundary_confidence':a['confidence'],
                           'title':None,'kind':None,'summary':None,'original_air_date':None,
                           'valid_from':None,'valid_until':None,'services':[],
                           'network_or_station':None,'identification_evidence':None,
                           'review_status':'pending'}
                          for i,(a,b) in enumerate(zip(cuts,cuts[1:]))]}


def export_review(document):
    source = document['source']
    assets = []
    previous = 0
    for candidate in document['candidates']:
        a,b = candidate['in_ms'],candidate['out_ms']
        if type(a) is not int or type(b) is not int or not 0<=a<b<=source['duration_ms'] or a<previous:
            raise ValueError('reviewed spans must be ordered, nonoverlapping, and within the source')
        previous=b
        if candidate['review_status'] != 'approved':
            continue
        context=validate_context(source.get('ingest'))
        candidate=dict(candidate)
        rule=reuse_rule(context,candidate.get('kind'),candidate.get('reuse_constraints'))
        if rule:
            candidate['valid_from']=candidate.get('valid_from') or rule['valid_from']
            candidate['valid_until']=candidate.get('valid_until') or rule['valid_until']
        if any(not candidate.get(k) for k in ('title','kind','summary','valid_from','valid_until','identification_evidence')):
            raise ValueError('approved candidates require title, kind, summary, dates and identification evidence')
        assets.append({'id':candidate['id'], 'source_id':source['id'],
                       **{k:candidate[k] for k in ('title','kind','in_ms','out_ms','valid_from','valid_until','services')},
                       'metadata':{k:v for k,v in candidate.items() if k not in
                                   ('id','title','kind','in_ms','out_ms','valid_from','valid_until','services')}})
    if not assets:
        raise ValueError('no approved candidates; pending analysis never enters the broadcast catalog')
    return {'version':1, 'sources':[source], 'assets':assets, 'programs':document.get('programs',[])}


def extract(document, directory):
    """Optional exact-boundary H.264/AAC derivatives. Archival source stays untouched."""
    manifest = export_review(document)
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    for index, asset in enumerate(manifest['assets']):
        target = directory/f'segment-{index:04d}.mp4'
        subprocess.run(['ffmpeg','-nostdin','-n','-ss',str(asset['in_ms']/1000),'-i',
                        document['source']['path'],'-t',str((asset['out_ms']-asset['in_ms'])/1000),
                        '-map','0:v:0','-map','0:a?','-c:v','libx264','-crf','18','-c:a','aac',
                        '-movflags','+faststart',str(target)],check=True,capture_output=True)
    return len(manifest['assets'])


def serve(root, jobs, host, port):
    root=Path(root).resolve(strict=True)
    jobs=Path(jobs).resolve()
    jobs.mkdir(parents=True,exist_ok=True)
    pool=ThreadPoolExecutor(max_workers=1)
    lock=threading.Lock()

    def write_job(ident, value):
        with lock:
            temporary=jobs/f'{ident}.tmp'
            temporary.write_text(json.dumps(value,indent=2))
            temporary.replace(jobs/f'{ident}.json')

    def run(ident,path,context):
        write_job(ident,{'status':'running'})
        try:
            result=analyze(path,context)
            write_job(ident,{'status':'awaiting_review','review':result})
        except Exception as error:
            write_job(ident,{'status':'failed','error':str(error)})

    class Handler(BaseHTTPRequestHandler):
        def reply(self,value,status=200):
            body=json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path!='/jobs':
                return self.reply({'error':'not found'},404)
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=8192:
                    raise ValueError('expected a small JSON job request')
                value=json.loads(self.rfile.read(length))
                context=validate_context(value.get('ingest'))
                if context['kind']!='recorded':raise ValueError('analysis jobs require recorded-media context')
                path=(root/value['path']).resolve(strict=True)
                if not path.is_relative_to(root) or not path.is_file():
                    raise ValueError('source must be a file under media-root')
                ident=uuid.uuid4().hex
                write_job(ident,{'status':'queued'})
                pool.submit(run,ident,path,context)
                self.reply({'id':ident,'status':'queued'},202)
            except (ValueError,OSError,KeyError) as error:
                self.reply({'error':str(error)},400)

        def do_GET(self):
            match=re.fullmatch(r'/jobs/([a-f0-9]{32})',self.path)
            if not match or not (jobs/f'{match[1]}.json').exists():
                return self.reply({'error':'not found'},404)
            with lock:
                value=json.loads((jobs/f'{match[1]}.json').read_text())
            self.reply(value)

    # A killed worker never silently marks an incomplete job as finished.
    for path in jobs.glob('*.json'):
        value=json.loads(path.read_text())
        if value.get('status') in ('queued','running'):
            write_job(path.stem,{'status':'interrupted','error':'Resubmit source after restart'})
    print(f'Optional analyzer: http://{host}:{port}',flush=True)
    try:
        ThreadingHTTPServer((host,port),Handler).serve_forever()
    finally:
        pool.shutdown(wait=False,cancel_futures=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    scan=sub.add_parser('analyze');scan.add_argument('source',type=Path);scan.add_argument('output',type=Path)
    add_recording_arguments(scan)
    export=sub.add_parser('export');export.add_argument('review',type=Path);export.add_argument('output',type=Path)
    cut=sub.add_parser('extract');cut.add_argument('review',type=Path);cut.add_argument('directory',type=Path)
    service=sub.add_parser('serve');service.add_argument('--media-root',required=True,type=Path)
    service.add_argument('--jobs',default='data/analysis-jobs',type=Path)
    service.add_argument('--host',default='127.0.0.1');service.add_argument('--port',default=8790,type=int)
    args=parser.parse_args()
    try:
        if args.command=='analyze':
            args.output.write_text(json.dumps(analyze(args.source,arguments_context(args)),indent=2))
        elif args.command=='export':
            review=json.loads(args.review.read_text())
            # Service GET responses wrap the same independent review document.
            args.output.write_text(json.dumps(export_review(review.get('review',review)),indent=2))
        elif args.command=='extract':
            document=json.loads(args.review.read_text())
            print(extract(document.get('review',document),args.directory))
        else:
            serve(args.media_root,args.jobs,args.host,args.port)
    except (ValueError,OSError,KeyError,subprocess.CalledProcessError) as error:
        parser.exit(1,f'Error: {error}\n')


if __name__=='__main__':
    main()
