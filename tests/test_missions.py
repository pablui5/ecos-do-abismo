import copy
import unittest
from test_direction import Conn
from app import Room, on_message
import missions


class MissionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.room = Room('QUEST1')
        self.room.host = 'host'
        self.room.party = [{'id': 'h0', 'owner': 'player', 'gold': 7}]
        self.host, self.player = [Conn(self.room, p) for p in ('host', 'player')]
        self.room.conns = {c.pid: c for c in (self.host, self.player)}

    async def start(self):
        await on_message(self.host, {'t': 'missionStart'})

    def position(self, q):
        self.room.snap = {'scenario': q['area'], 'mode': 'explore', 'defeated': q['kills'], 'bossDefeated': q.get('boss', False),
                          'units': [{'s': 'hero', 'hid': 'h0', 'c': q['c'], 'r': q['r'], 'al': True, 'dn': False}]}

    def progress(self, ident='main', ending=None):
        return {'t': 'missionProgress', 'hero': 'h0', 'id': ident, 'revision': self.room.campaign['revision'], 'ending': ending, 'gold': 999999}

    async def test_host_authority_and_duplicate_start(self):
        await on_message(self.player, {'t': 'missionStart'})
        self.assertFalse(self.room.campaign['active'])
        await self.start()
        snapshot = copy.deepcopy(self.room.campaign)
        await self.start()
        self.assertEqual(self.room.campaign, snapshot)
        self.position(missions.DATA['steps'][0])
        await on_message(self.player, self.progress())
        self.assertEqual(self.room.campaign['step'], 0)
        self.assertEqual(self.room.party[0]['gold'], 7)

    async def test_entire_campaign_reward_replay_and_persistence(self):
        await self.start()
        for q in missions.DATA['steps']:
            self.position(q)
            message = self.progress(ending='libertar')
            await on_message(self.host, message)
            gold = self.room.party[0]['gold']
            await on_message(self.host, message)
            self.assertEqual(self.room.party[0]['gold'], gold)
        self.assertEqual(self.room.party[0]['gold'], 97)
        self.assertTrue(self.room.campaign['completed'])
        self.assertEqual(self.room.campaign['ending'], 'libertar')
        restored = Room('QUEST1', self.room.to_data())
        self.assertEqual(restored.campaign, self.room.campaign)
        self.assertEqual(restored.party, self.room.party)
        self.assertEqual(self.player.messages[-1]['t'], 'mission')

    async def test_invalid_evidence_never_rewards(self):
        await self.start()
        q = missions.DATA['steps'][0]
        for change in ({'scenario':'castelo'}, {'mode':'combat'}, {'units':[]}, {'defeated':-1}):
            self.position(q)
            self.room.snap.update(change)
            await on_message(self.host, self.progress())
            self.assertEqual(self.room.campaign['step'],0)
            self.assertEqual(self.room.party[0]['gold'],7)
        for change in ({'c':0},{'al':False},{'dn':True},{'c':4.5}):
            self.position(q)
            self.room.snap['units'][0].update(change)
            await on_message(self.host,self.progress())
            self.assertEqual(self.room.campaign['step'],0)

    async def test_secondary_acceptance_completion_and_replay(self):
        await self.start()
        for q in missions.DATA['side']:
            await on_message(self.player, {'t':'missionAccept','id':q['id']})
            revision=self.room.campaign['revision']
            await on_message(self.player, {'t':'missionAccept','id':q['id']})
            self.assertEqual(self.room.campaign['revision'],revision)
            self.position(q)
            await on_message(self.host, self.progress(q['id']))
            gold=self.room.party[0]['gold']
            await on_message(self.host, self.progress(q['id']))
            await on_message(self.player, {'t':'missionAccept','id':q['id']})
            self.assertEqual(self.room.party[0]['gold'],gold)
            self.assertEqual(self.room.campaign['side'][q['id']], 'completed')
        self.assertEqual(self.room.campaign['step'],0)
        self.assertEqual(self.room.party[0]['gold'],52)

    async def test_boss_and_valid_ending_required(self):
        await self.start()
        self.room.campaign['step']=4
        self.position(missions.DATA['steps'][4])
        self.room.snap['bossDefeated']=False
        await on_message(self.host,self.progress(ending='selar'))
        self.assertEqual(self.room.campaign['step'],4)
        self.room.snap['bossDefeated']=True
        await on_message(self.host,self.progress(ending='unknown'))
        self.assertEqual(self.room.campaign['step'],4)
        await on_message(self.host,self.progress(ending='vigiar'))
        self.assertTrue(self.room.campaign['completed'])


if __name__ == '__main__':
    unittest.main()
