import json
import unittest
import test_manager
from retro_tv import research
from retro_tv.identities import resolve,match,backfill_listed_episodes
from retro_tv.records import import_records
from retro_tv.manager import import_plan,assess

class EpisodeBoundaryTest(unittest.TestCase):
    setUp=test_manager.ManagerTest.setUp
    tearDown=test_manager.ManagerTest.tearDown

    def test_unicode_punctuation_segment_separators_and_explicit_aliases(self):
        ident=resolve(self.db,'Doug',"Doug’s Cartoon / Doug's Monster Movie")
        self.assertEqual(match(self.db,'DOUG',"Doug's Cartoon; Doug’s Monster Movie"),ident)
        import_records(self.db,{'version':1,'content_aliases':[{'content_id':ident,'title':'Nickelodeon Doug','episode_title':'Cartoon / Monster Movie'}]})
        self.assertEqual(match(self.db,'Nickelodeon Doug','Cartoon / Monster Movie'),ident)
        self.assertIsNone(match(self.db,'Doug','A different episode'))
        numeric=resolve(self.db,'Show with numbers','S01E02: An episode')
        self.assertEqual(match(self.db,'Show with numbers','1x02'),numeric)
        self.assertEqual(self.db.execute('SELECT season_number FROM content WHERE id=?',(ident,)).fetchone()[0],None)

    def test_old_annotation_imports_gain_episode_identities_and_episode_coverage(self):
        doc=test_manager.ManagerTest.plan(self);doc['airings'][0]['content_id']=None;doc['airings'][0]['title']='Synthetic show';doc['airings'][0]['evidence_state']='schedule_exact';doc['airings'][0]['provenance']={'source_episode_text':'The named episode'}
        import_plan(self.db,doc)
        with self.db:backfill_listed_episodes(self.db)
        report=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'historical'})
        self.assertEqual(report['identified_episode_percent'],2.1)
        self.assertTrue(any(r['kind']=='known_program_gap' for r in report['recommendations']))
        links=[a['url'] for r in report['recommendations'] for a in r.get('actions',[])]
        self.assertTrue(any('ebay.com' in u for u in links));self.assertTrue(any('archive.org' in u for u in links))

    def test_next_day_continuation_and_2359_fallback(self):
        tail={'title':'Late movie','episode_title':'Part 1','start':'1995-07-18T23:00:00-04:00','end':None}
        following=[{'title':'Late movie','episode_title':'Part 1','start':'1995-07-19T00:00:00-04:00','end':'1995-07-19T01:00:00-04:00'}]
        row=research.close_tail(tail,following,'1995-07-19','America/New_York');self.assertEqual(row['end'],following[0]['end'])
        following[0]['episode_title']='A different episode'
        row=research.close_tail(tail,following,'1995-07-19','America/New_York');self.assertEqual(row['end'],'1995-07-19T00:00:00-04:00');self.assertIn('23:59',row['end_basis'])
        self.assertTrue(row['boundary_inferred'])

    def test_fetch_polls_following_day_even_outside_requested_period(self):
        batch=research.create_batch(self.db,{'service_id':'kids','start_date':'1995-07-18','until_date':'1995-07-19','adapter':'mediawiki_daily','url_template':'https://example.org/{date}'})
        calls=[]
        def fetch(url):
            calls.append(url)
            if url.endswith('1995-07-18'):return '<h1>July 18, 1995</h1><table><tr><th>Time</th><th>Show</th></tr><tr><td>11:30pm</td><td>Late show</td></tr></table>'
            return '<h1>July 19, 1995</h1><table><tr><th>Time</th><th>Show</th></tr><tr><td>12:00am</td><td>Other show</td></tr><tr><td>12:30am</td><td>Boundary</td></tr></table>'
        result=research.fetch_page(self.db,{'page_id':batch['pages'][0]['id']},fetcher=fetch)
        self.assertEqual(len(calls),2);self.assertEqual(result['pages'][0]['candidates'][0]['end'],'1995-07-19T00:00:00-04:00')
        self.assertEqual(result['pages'][0]['boundary']['status'],'resolved')

    def test_failed_next_day_lookup_can_resume_from_cached_primary_html(self):
        batch=research.create_batch(self.db,{'service_id':'kids','start_date':'1995-07-18','until_date':'1995-07-19','adapter':'mediawiki_daily','url_template':'https://example.org/{date}'})
        html='<h1>July 18, 1995</h1><table><tr><th>Time</th><th>Show</th></tr><tr><td>11:00pm</td><td>A</td></tr><tr><td>11:30pm</td><td>B</td></tr></table>'
        def failed(url):raise OSError('offline')
        page=research.fetch_page(self.db,{'page_id':batch['pages'][0]['id'],'html':html},fetcher=failed)['pages'][0]
        self.assertEqual(page['boundary']['status'],'pending');self.assertEqual(len(page['candidates']),1)
        next_html='<h1>July 19, 1995</h1><table><tr><th>Time</th><th>Show</th></tr><tr><td>12:00am</td><td>C</td></tr><tr><td>12:30am</td><td>D</td></tr></table>'
        page=research.fetch_page(self.db,{'page_id':page['id'],'next_html':next_html})['pages'][0]
        self.assertEqual(len(page['candidates']),2);self.assertEqual(page['boundary']['status'],'resolved')

    def test_supplemental_premiere_lookup_enriches_unique_slots_but_not_ambiguous_repeats(self):
        doc=test_manager.ManagerTest.plan(self);doc['airings'][0].update(content_id=None,title='A show',evidence_state='schedule_exact')
        import_plan(self.db,doc)
        result=research.enrich_episodes(self.db,{'service_id':'kids','episodes':[{'date':'1995-07-18','title':'A show','episode_title':'An episode','url':'https://example.org/episode-index'}]})
        self.assertEqual(result['unresolved'],[])
        self.assertEqual(self.db.execute("SELECT episode_title FROM content c JOIN historical_airing a ON a.content_id=c.id WHERE a.id='listing'").fetchone()[0],'An episode')
        doc['airings'][0].update(id='repeat',start='1995-07-18T17:00:00-04:00',end='1995-07-18T17:30:00-04:00')
        import_plan(self.db,doc)
        result=research.enrich_episodes(self.db,{'service_id':'kids','episodes':[{'date':'1995-07-18','title':'A show','episode_title':'Another episode','url':'https://example.org/episode-index'}]})
        self.assertEqual(len(result['unresolved']),1)
        with self.assertRaises(ValueError):research.close_tail({'start':'1995-07-18T23:30:00-04:00','title':'Late'},[],'1995-07-19','America/New_York')
