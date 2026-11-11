import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

import test_manager
from retro_tv import research
from retro_tv.manager import assess
from retro_tv.scheduler import extend
from test_station import ROOT, REAL


def html(rows,day='July 18, 1995'):
    return '<h1>'+day+'</h1><table><tr><th>Time</th><th>Show</th><th>Episode</th></tr>'+rows+'</table>'


class ResearchTest(unittest.TestCase):
    setUp=test_manager.ManagerTest.setUp
    tearDown=test_manager.ManagerTest.tearDown

    def batch(self,**changes):
        return research.create_batch(self.db,{'service_id':'kids','start_date':'1995-07-18','until_date':'1995-07-20',
            'timezone':'America/New_York','adapter':'mediawiki_daily','url_template':'https://nickstory.fandom.com/wiki/{wiki_date}',**changes})

    def staged(self):
        batch=self.batch()
        body=html('<tr><td>4:00pm</td><td>Synthetic Show</td><td>Episode A</td></tr><tr><td>4:30pm</td><td></td><td></td></tr><tr><td>5:00pm</td><td>Synthetic Show</td><td></td></tr><tr><td>5:30pm</td><td>End boundary</td><td></td></tr>')
        return research.fetch_page(self.db,{'page_id':batch['pages'][0]['id'],'html':body})

    def test_research_caches_source_but_claims_no_coverage_until_accepted(self):
        now=extend(self.db,real_now=REAL)
        before={t:[tuple(r) for r in self.db.execute(f'SELECT * FROM {t}')] for t in ('state','broadcast','segment')}
        batch=self.staged();page=batch['pages'][0]
        self.assertEqual(page['status'],'staged');self.assertEqual(len(page['candidates']),2)
        self.assertEqual(assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'historical'})['known_schedule_percent'],0)
        with patch.object(research,'fetch_html',side_effect=AssertionError('must use cache')):
            research.fetch_page(self.db,{'page_id':page['id']})
        result=research.accept(self.db,{'page_id':page['id'],'selections':[{'index':0}]})
        self.assertIn('Accepted 1',result['status'])
        report=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'historical'})
        self.assertAlmostEqual(report['known_schedule_percent'],2.1)
        self.assertEqual(report['exact_schedule_percent'],0)
        self.assertEqual(report['health']['research_status'],'partial')
        self.assertEqual(len(report['history']),1)
        self.assertTrue(any(r['kind']=='known_program_gap' for r in report['recommendations']))
        self.assertEqual(before,{t:[tuple(r) for r in self.db.execute(f'SELECT * FROM {t}')] for t in before})
        research.accept(self.db,{'page_id':page['id'],'selections':[{'index':0}]})
        self.assertEqual(self.db.execute('SELECT count(*) FROM historical_airing').fetchone()[0],1)
        self.assertEqual(result['batch']['pages'][0]['accepted_listings'][0]['candidate_index'],0)

    def test_html_rowspans_midnight_blanks_and_final_boundary(self):
        body=html('<tr><td>11:00pm</td><td rowspan="2">Long show</td><td rowspan="2">Part</td></tr><tr><td>11:30pm</td></tr><tr><td>12:00am</td><td></td><td></td></tr><tr><td>12:30am</td><td>Last</td><td></td></tr>')
        rows,warnings=research.parse_html(body,'1995-07-18','America/New_York','mediawiki_daily')
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['title'],'Long show');self.assertTrue(rows[0]['end'].startswith('1995-07-19T00:00'))
        self.assertNotIn('Last',[r['title'] for r in rows])

    def test_bad_clocks_do_not_bridge_or_invent_coverage(self):
        body=html('<tr><td>4:00pm</td><td>A</td><td></td></tr><tr><td>4:xxpm</td><td>Unknown boundary</td><td></td></tr><tr><td>5:00pm</td><td>B</td><td></td></tr><tr><td>5:30pm</td><td>C</td><td></td></tr>')
        rows,warnings=research.parse_html(body,'1995-07-18','America/New_York','mediawiki_daily')
        self.assertEqual([r['title'] for r in rows],['B']);self.assertTrue(any('Unparsed clock' in w for w in warnings))
        with self.assertRaises(ValueError):research.parse_html(body,'1995-07-19','America/New_York','mediawiki_daily')
        with self.assertRaises(ValueError):research.parse_html('<html>challenge page</html>','1995-07-18','America/New_York','mediawiki_daily')

    def test_post_parser_only_reads_article_and_preserves_blank_hours(self):
        body='<h2>Tuesday, July 4, 1995</h2><div class="entry-content"><p>04:00PM Salute Your Shorts: “Source annotation”<br>04:30PM<br>05:00PM Other show:<br>05:30PM End:</p></div><aside>06:00PM Wrong</aside>'
        rows,warnings=research.parse_html(body,'1995-07-04','America/New_York','kidsblock_post')
        self.assertEqual(len(rows),2);self.assertEqual(rows[0]['episode_title'],'Source annotation')
        self.assertEqual(rows[-1]['end'],'1995-07-04T17:30:00-04:00')

    def test_fetch_errors_are_persisted_and_can_be_retried(self):
        batch=self.batch();ident=batch['pages'][0]['id']
        def failed(url):raise OSError('blocked destination')
        result=research.fetch_page(self.db,{'page_id':ident},fetcher=failed)
        self.assertEqual(result['pages'][0]['status'],'failed');self.assertEqual(self.db.execute('SELECT count(*) FROM historical_airing').fetchone()[0],0)
        result=research.fetch_page(self.db,{'page_id':ident,'html':html('<tr><td>1:00pm</td><td>A</td><td></td></tr><tr><td>1:30pm</td><td>B</td><td></td></tr>')})
        self.assertEqual(result['pages'][0]['status'],'staged')

    def test_acceptance_conflict_rolls_back_whole_page_including_new_identities(self):
        batch=self.staged();page=batch['pages'][0]
        from retro_tv.manager import import_plan
        import_plan(self.db,test_manager.ManagerTest.plan(self))
        count=self.db.execute('SELECT count(*) FROM content').fetchone()[0]
        with self.assertRaises(ValueError):research.accept(self.db,{'page_id':page['id'],'selections':[{'index':1},{'index':0}]})
        self.assertEqual(self.db.execute('SELECT count(*) FROM content').fetchone()[0],count)
        self.assertEqual(self.db.execute('SELECT status FROM research_page WHERE id=?',(page['id'],)).fetchone()[0],'staged')
        self.assertEqual(self.db.execute('SELECT count(*) FROM historical_airing').fetchone()[0],1)

    def test_exact_requires_identity_and_confirmation_and_inference_is_not_researched(self):
        page=self.staged()['pages'][0]
        for selection in ({'index':0,'evidence_state':'exact'},{'index':0,'content_id':'program:episode','evidence_state':'exact','episode_confirmed':True}):
            with self.assertRaises(ValueError):research.accept(self.db,{'page_id':page['id'],'selections':[selection]})
        research.accept(self.db,{'page_id':page['id'],'selections':[{'index':0,'evidence_state':'inferred'}]})
        report=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'historical'})
        self.assertEqual(report['known_schedule_percent'],0);self.assertEqual(report['health']['research_status'],'unresearched')
        self.assertFalse(any(r['kind']=='known_program_gap' for r in report['recommendations']))

    def test_real_browsed_bundle_can_be_sideloaded_and_exported_without_media(self):
        from retro_tv.records import import_records
        import_records(self.db,json.loads((ROOT/'examples/research/nickelodeon-service.json').read_text()))
        doc=json.loads((ROOT/'examples/research/nickelodeon-1995-07-04.json').read_text());batch=research.sideload(self.db,doc)
        self.assertEqual(len(batch['pages'][0]['candidates']),44)
        self.assertEqual(self.db.execute('SELECT count(*) FROM historical_airing').fetchone()[0],0)
        research.accept(self.db,{'page_id':batch['pages'][0]['id'],'selections':[{'index':i} for i in range(44)]})
        report=assess(self.db,{'service_id':'nickelodeon','date':'1995-07-04','mode':'historical'})
        self.assertEqual(report['known_schedule_percent'],93.8);self.assertEqual(report['exact_schedule_percent'],0)
        exported=research.export_bundle(self.db,batch['id']);self.assertEqual(exported['pages'][0]['url'],doc['pages'][0]['url'])
        second=research.sideload(self.db,exported)
        research.accept(self.db,{'page_id':second['pages'][0]['id'],'selections':[{'index':i} for i in range(44)]})
        self.assertEqual(self.db.execute('SELECT count(*) FROM historical_airing').fetchone()[0],44)
        self.assertEqual(self.db.execute("SELECT count(*) FROM lineup_entry WHERE service_id='nickelodeon'").fetchone()[0],0)

    def test_period_bounds_and_unsafe_source_urls(self):
        for until in ('1995-07-18','1995-10-01'):
            with self.assertRaises(ValueError):self.batch(until_date=until)
        for url in ('file:///etc/passwd','http://example.com','https://user:secret@example.com'):
            with self.assertRaises(ValueError):research.public_url(url)
        with patch('socket.getaddrinfo',return_value=[(None,None,None,None,('127.0.0.1',443))]):
            with self.assertRaises(ValueError):research.public_url('https://example.com')
        with self.assertRaises(ValueError):research.local_stamp(__import__('datetime').date(2026,11,1),90,__import__('zoneinfo').ZoneInfo('America/New_York'))
