import json
import unittest
import test_manager
from retro_tv import broadcasts
from retro_tv.scheduler import extend,guide
from retro_tv.timelines import normalize_request,build,options
from retro_tv.records import Policy
from test_station import REAL

class BroadcastsTest(unittest.TestCase):
    setUp=test_manager.ManagerTest.setUp
    tearDown=test_manager.ManagerTest.tearDown

    def layout(self,**changes):
        provider=self.db.execute('SELECT id FROM provider LIMIT 1').fetchone()[0]
        return {'name':'Basic cable','region':'Rochester, NY','timezone':'America/New_York','provider_id':provider,'reception':'cable','tier':'Basic',
            'channels':[{'service_id':'kids','channel':'7','valid_from':'1990-01-01','valid_until':'2100-01-01'}],**changes}

    def test_active_setup_scopes_guide_and_choices_without_changing_published_rows(self):
        now=extend(self.db,real_now=REAL);before=[tuple(r) for r in self.db.execute('SELECT * FROM broadcast')]
        first=broadcasts.save(self.db,self.layout());self.assertEqual([c['channel'] for c in guide(self.db,now)['channels']],['7'])
        self.assertEqual([c['id'] for c in options(self.db)['channels']],['kids'])
        r=normalize_request(self.db,{'mode':'historical','service_id':'kids','destination':'1995-07-18T16:00'})
        self.assertEqual(r['layout_id'],first['id'])
        other=broadcasts.save(self.db,self.layout(name='Antenna',reception='antenna',tier='',channels=[{'service_id':'late','channel':'31','valid_from':'1990-01-01','valid_until':'2100-01-01'}]))
        self.assertEqual([c['channel'] for c in guide(self.db,now)['channels']],['31'])
        with self.assertRaises(ValueError):normalize_request(self.db,{'mode':'surfing','service_id':'kids'})
        broadcasts.activate(self.db,{'id':first['id']})
        self.assertEqual([tuple(r) for r in self.db.execute('SELECT * FROM broadcast')],before)
        self.assertEqual(broadcasts.home(self.db,now)['channels'][0]['channel'],'7')

    def test_new_region_changes_market_eligibility_and_local_timezone(self):
        broadcasts.save(self.db,self.layout(region='Chicago, IL',timezone='America/Chicago'))
        self.assertEqual(broadcasts.timezone(self.db),'America/Chicago')
        policy=Policy(self.db)
        self.assertIsNotNone(policy.active_market)
        self.assertEqual(self.db.execute('SELECT name FROM market WHERE id=?',(policy.active_market,)).fetchone()[0],'Chicago, IL')
        with self.assertRaises(ValueError):broadcasts.save(self.db,self.layout(channels=self.layout()['channels']*2))

    def test_representative_context_supports_channels_defined_only_in_personal_layout(self):
        self.db.execute("INSERT INTO service VALUES ('new','New theme')");self.db.commit()
        broadcasts.save(self.db,self.layout(channels=[{'service_id':'new','channel':'99','valid_from':'1990-01-01','valid_until':'2100-01-01'}]))
        request=normalize_request(self.db,{'mode':'representative','service_id':'new','destination':'1995-07-18T16:00'})
        scratch,now=build(self.db,request,REAL)
        try:self.assertEqual(guide(scratch,now)['channels'][0]['id'],'new')
        finally:scratch.close()
