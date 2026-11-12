import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from retro_tv.timelines import destination, normalize_request, key_for, preflight, launch
import test_timelines as fixtures

class DestinationTest(unittest.TestCase):
    setUp=fixtures.TimelineTest.setUp
    tearDown=fixtures.TimelineTest.tearDown

    def test_date_only_starts_at_local_midnight(self):
        result=normalize_request(self.db,{**self.request,'destination_type':'date','destination':'1995-07-18'})
        self.assertEqual(result['destination'],'1995-07-18T00:00:00-04:00')

    def test_today_uses_broadcast_zone_calendar_and_local_clock(self):
        real=int(datetime.fromisoformat('2026-11-13T02:17:45+00:00').timestamp()*1000)
        value={**self.request,'destination_type':'today','year':1996};value.pop('destination')
        result=normalize_request(self.db,value,real_now=real)
        self.assertEqual(result['destination'],'1996-11-12T21:17:45-05:00')
        later=normalize_request(self.db,value,real_now=real+60000)
        self.assertEqual(key_for(result),key_for(later))
        self.assertNotEqual(key_for(result),key_for(normalize_request(self.db,value,real_now=real+86400000)))

    def test_today_preflight_is_pinned_and_launch_reuses_daily_context(self):
        real=int(datetime.fromisoformat('2026-07-18T20:00:00+00:00').timestamp()*1000)
        value={**self.request,'destination_type':'today','year':1995};value.pop('destination')
        checked=preflight(self.path,value,real_now=real)
        first=launch(self.path,checked['resolved_selection'],real_now=real+30000)
        again=launch(self.path,value,real_now=real+60000)
        self.assertEqual(first['context_id'],again['context_id'])
        self.assertTrue(again['resuming'])

    def test_leap_day_and_missing_local_time_are_explicit(self):
        zone=ZoneInfo('America/New_York')
        real=int(datetime.fromisoformat('2024-02-29T12:00:00-05:00').timestamp()*1000)
        with self.assertRaisesRegex(ValueError,'February 29'):destination({'destination_type':'today','year':1995},zone,real)
        self.assertEqual(destination({'destination_type':'today','year':1996},zone,real).date().isoformat(),'1996-02-29')
        gap=int(datetime.fromisoformat('2026-04-02T02:30:00-04:00').timestamp()*1000)
        with self.assertRaisesRegex(ValueError,'does not exist'):destination({'destination_type':'today','year':1995},zone,gap)
