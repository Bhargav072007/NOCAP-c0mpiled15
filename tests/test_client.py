import json
import unittest
from unittest.mock import Mock
import requests
from dashboard.client import APIError, FixtureClient, LiveClient, export_ledger, validate_ledger, explorer_url

class LedgerClientTests(unittest.TestCase):
    def test_populated_export_exact(self):
        ledger = FixtureClient().ledger()
        self.assertEqual(len(ledger['records']), 3)
        self.assertEqual(json.loads(export_ledger(ledger)), ledger)
        self.assertIsNone(ledger['chain_ok'])
        self.assertTrue(ledger['fixture'])
    def test_empty(self):
        ledger = FixtureClient('Empty').ledger()
        self.assertEqual(ledger['records'], [])
        self.assertIsNone(ledger['merkle_root'])
    def test_failure_and_recovery(self):
        client = FixtureClient('Disconnected')
        with self.assertRaises(APIError): client.ledger()
        client.scenario = 'Populated'
        self.assertEqual(len(client.ledger()['records']), 3)
    def test_missing_chain_is_not_success(self):
        data = {'records': [], 'merkle_root': None, 'anchor_tx': None}
        self.assertNotIn('chain_ok', validate_ledger(data))
    def test_malformed(self):
        for data in [None, {}, {'records': 'bad'}, {'records': [], 'merkle_root': 'bad', 'anchor_tx': None}]:
            with self.subTest(data=data), self.assertRaises(APIError): validate_ledger(data)
    def test_live_transport_and_timeout(self):
        session = Mock()
        session.request.return_value.status_code = 200
        session.request.return_value.json.return_value = FixtureClient().ledger()
        self.assertEqual(len(LiveClient('http://localhost:8000', session).ledger()['records']), 3)
        session.request.assert_called_once_with('GET', 'http://localhost:8000/ledger', timeout=(3.05,20), allow_redirects=False)
        session.request.side_effect = requests.ConnectionError('secret internal detail')
        with self.assertRaisesRegex(APIError, 'disconnected'): LiveClient('http://localhost:8000', session).ledger()
    def test_http_and_invalid_json(self):
        session=Mock()
        session.request.return_value.status_code=503
        with self.assertRaisesRegex(APIError, '503'): LiveClient('http://localhost',session).ledger()
        session.request.return_value.status_code=200
        session.request.return_value.json.side_effect=ValueError()
        with self.assertRaisesRegex(APIError, 'valid JSON'): LiveClient('http://localhost',session).ledger()
    def test_explorer_validation(self):
        self.assertIsNone(explorer_url('javascript:bad'))
        self.assertEqual(explorer_url('0x'+'a'*64), 'https://sepolia.etherscan.io/tx/0x'+'a'*64)
