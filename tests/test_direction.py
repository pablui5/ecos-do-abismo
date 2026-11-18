import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
from direction import personality, campaign_settings, edit_personality
from app import Room, on_message, merge_runtime, WEAPONS


class Conn:
    def __init__(self, room, pid):
        self.room, self.pid, self.messages = room, pid, []
    async def send(self, message):
        self.messages.append(message)


class NarrativeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.room = Room('TEST16')
        self.room.host = 'host'
        self.hero = {'id': 'h0', 'owner': 'player', 'def': {'personality': personality({'quest': 'Encontrar a sentinela'})}, 'inv': [], 'sets': [{}, {}]}
        self.room.party = [self.hero]
        self.host, self.player, self.other = [Conn(self.room, p) for p in ('host', 'player', 'other')]
        self.room.conns = {c.pid: c for c in (self.host, self.player, self.other)}

    async def test_player_cannot_approve_or_edit_another_hero(self):
        await on_message(self.player, {'t':'questDecision','hero':'h0','status':'approved'})
        self.assertEqual(self.hero['def']['personality']['status'], 'pending')
        self.assertEqual(self.player.messages[-1]['t'], 'error')
        await on_message(self.other, {'t':'personality','hero':'h0','value':{'quest':'forjada'}})
        self.assertEqual(self.other.messages[-1]['t'], 'error')
        self.assertEqual(self.hero['def']['personality']['quest'], 'Encontrar a sentinela')

    async def test_edit_invalidates_approval_and_broadcasts(self):
        await on_message(self.host, {'t':'questDecision','hero':'h0','status':'approved'})
        self.assertEqual(self.hero['def']['personality']['status'], 'approved')
        await on_message(self.player, {'t':'personality','hero':'h0','value':{'quest':'Abrir o selo','status':'completed'}})
        self.assertEqual(self.hero['def']['personality']['status'], 'pending')
        self.assertEqual(self.host.messages[-1]['t'], 'party')
        self.assertTrue(self.room.dirty)
        await on_message(self.host, {'t':'questDecision','hero':'h0','status':'completed'})
        self.assertEqual(self.host.messages[-1]['t'], 'error')
        for status in ('approved','completed'):
            await on_message(self.host, {'t':'questDecision','hero':'h0','status':status})
        self.assertEqual(self.hero['def']['personality']['status'], 'completed')

    async def test_settings_are_host_only_and_merge_without_resetting_artifice(self):
        self.room.settings['artifice'] = False
        await on_message(self.player, {'t':'settings','tensionEnabled':True})
        self.assertFalse(self.room.settings['tensionEnabled'])
        await on_message(self.host, {'t':'settings','tensionEnabled':True,'tensionDC':99})
        self.assertTrue(self.room.settings['tensionEnabled'])
        self.assertEqual(self.room.settings['tensionDC'], 16)
        self.assertFalse(self.room.settings['artifice'])

    def test_persistence_and_runtime_do_not_overwrite_personality(self):
        state={'level':3,'turns':2,'grace':0}
        merge_runtime(self.room,[{'id':'h0','tension':state,'def':{'name':'Kael','personality':{'status':'completed'}}}])
        restored=Room('TEST16',self.room.to_data())
        self.assertEqual(restored.party[0]['tension'],state)
        self.assertEqual(restored.party[0]['def']['personality']['status'],'pending')
        self.assertEqual(len(WEAPONS),120)

    def test_legacy_settings_and_validation(self):
        self.assertFalse(Room('OLD',{'settings':{'artifice':False}}).settings['tensionEnabled'])
        self.assertFalse(campaign_settings({'tensionEnabled':'true'})['tensionEnabled'])
        self.assertEqual(personality({'origin':9})['origin'],'')
        self.assertEqual(len(personality({'quest':'a'*900})['quest']),600)
        edit_personality(self.hero,{'quest':'Encontrar a sentinela','status':'approved'})
        self.assertEqual(self.hero['def']['personality']['status'],'pending')


if __name__ == '__main__':
    unittest.main()
