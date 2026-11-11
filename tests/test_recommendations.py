import json
import unittest
from datetime import datetime,timedelta
from urllib.parse import urlsplit,parse_qs

import test_manager
from retro_tv.manager import assess,dashboard,import_plan
from retro_tv.recommendations import get_standard,save_standard
from retro_tv.records import import_records
from retro_tv.scheduler import extend
from test_station import REAL


class RecommendationsTest(unittest.TestCase):
    setUp=test_manager.ManagerTest.setUp
    tearDown=test_manager.ManagerTest.tearDown

    def test_unresearched_period_cannot_generate_named_missing_episodes(self):
        report=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'historical'})
        self.assertEqual(report['health']['research_status'],'unresearched')
        self.assertEqual(report['health']['status'],'unknown')
        self.assertTrue(any(r['kind']=='research' for r in report['recommendations']))
        self.assertFalse(any(r['kind']=='known_program_gap' for r in report['recommendations']))

    def test_verified_missing_episodes_group_into_season_ranges_and_dvd_searches(self):
        contents=[{'id':'sitcom','kind':'series','title':'Synthetic Sitcom'}]
        airings=[];start=datetime.fromisoformat('1995-07-18T00:00:00-04:00')
        for n in range(2,14):
            contents.append({'id':f'episode-{n}','kind':'episode','title':'Synthetic Sitcom',
                'parent_id':'sitcom','season_number':4,'episode_number':n})
            airings.append({'id':f'airing-{n}','service_id':'kids','content_id':f'episode-{n}',
                'title':f'Synthetic Sitcom S4E{n}','start':start.isoformat(),
                'end':(start+timedelta(minutes=30)).isoformat(),'evidence_state':'exact','provenance':'Synthetic test listing'})
            start+=timedelta(minutes=30)
        import_records(self.db,{'version':1,'contents':contents});import_plan(self.db,{'version':1,'airings':airings})
        report=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'historical'})
        gaps=[r for r in report['recommendations'] if r['kind']=='known_program_gap']
        self.assertEqual(len(gaps),1);self.assertIn('Season 4, Episodes 2–13',gaps[0]['title'])
        self.assertEqual(len(gaps[0]['airing_ids']),12)
        self.assertEqual(parse_qs(urlsplit(gaps[0]['actions'][0]['url']).query)['_nkw'][0],'Synthetic Sitcom season 4 DVD')
        self.assertEqual(report['health']['research_status'],'partial')

    def test_inferred_episode_identity_is_not_a_verified_missing_episode(self):
        import_records(self.db,{'version':1,'contents':[{'id':'guessed','kind':'episode','title':'Possibly this episode','season_number':1,'episode_number':2}]})
        doc=test_manager.ManagerTest.plan(self,content='guessed');doc['airings'][0]['evidence_state']='inferred'
        import_plan(self.db,doc)
        report=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'historical'})
        self.assertFalse(any(r['kind']=='known_program_gap' for r in report['recommendations']))

    def test_capacity_recommendations_are_not_claims_of_named_missing_ads(self):
        report=assess(self.db,{'service_id':'kids','date':'1995-07-18','days':3,'mode':'theme','tags':['cartoon']})
        variety=[r for r in report['recommendations'] if r['kind']=='variety']
        self.assertEqual(len(variety),1);self.assertIn('1995',variety[0]['title'])
        self.assertEqual(variety[0]['evidence'],'library_capacity')
        self.assertTrue(any('archive.org' in a['url'] for a in variety[0]['actions']))
        self.assertTrue(any('youtube.com' in a['url'] for a in variety[0]['actions']))
        self.assertFalse(any(r['kind']=='known_program_gap' for r in report['recommendations']))

    def test_lineup_health_changes_by_mode_and_standards_do_not_change_the_schedule(self):
        now=extend(self.db,real_now=REAL)
        before=[tuple(r) for r in self.db.execute('SELECT * FROM segment ORDER BY id')]
        standard=get_standard(self.db,'theme');standard['settings'].update(min_unique_hours=0,max_inventory_passes=1000,ad_minutes_per_day=0)
        save_standard(self.db,standard)
        themed=dashboard(self.db,now,'theme');historical=dashboard(self.db,now,'historical')
        self.assertEqual(themed['lineup_health']['channel_count'],historical['lineup_health']['channel_count'])
        self.assertGreater(themed['lineup_health']['healthy_channels'],historical['lineup_health']['healthy_channels'])
        self.assertTrue(themed['lineup_health']['meets_target']);self.assertFalse(historical['lineup_health']['meets_target'])
        self.assertEqual([tuple(r) for r in self.db.execute('SELECT * FROM segment ORDER BY id')],before)

    def test_dashboard_assesses_requested_period_without_inventing_a_dated_lineup(self):
        now=extend(self.db,real_now=REAL)
        themed=dashboard(self.db,now,'theme','1980-01-01',1)
        historical=dashboard(self.db,now,'historical','1980-01-01',1)
        self.assertEqual(themed['assessment_date'],'1980-01-01')
        self.assertEqual(themed['assessment_days'],1)
        self.assertGreater(themed['lineup_health']['channel_count'],0)
        self.assertEqual(historical['lineup_health']['channel_count'],0)
        self.assertFalse(historical['lineup_health']['meets_target'])

    def test_owned_but_excluded_content_is_not_recommended_for_repurchase(self):
        import_plan(self.db,test_manager.ManagerTest.plan(self))
        from retro_tv.records import set_preference
        set_preference(self.db,'program:episode')
        report=assess(self.db,{'service_id':'kids','date':'1995-07-18','mode':'historical'})
        self.assertTrue(any(r['kind']=='selection_mismatch' for r in report['recommendations']))
        self.assertFalse(any(r['kind']=='known_program_gap' for r in report['recommendations']))
