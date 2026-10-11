from tests.ui_helpers import workspace_app, AuthenticatedFixture
"""RPC mocks only. Real local signing is ephemeral; nothing is broadcast."""
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import rlp
from eth_account import Account
from web3 import Web3
from web3.providers.base import BaseProvider
import ledger.anchor as anchor
from dashboard.client import APIError, LiveClient, FixtureClient
from streamlit.testing.v1 import AppTest

ROOT='ab'*32

class FakeRPC(BaseProvider):
    def __init__(self,chain=11155111,fail=None,balance=10**18,price=10**9):
        super().__init__()
        self.chain,self.fail,self.balance,self.price=chain,fail,balance,price
        self.calls=[];self.raw=None
    def make_request(self,method,params):
        self.calls.append((method,params))
        if method==self.fail:
            raise TimeoutError('provider-secret-internal-detail')
        if method=='eth_sendRawTransaction':
            self.raw=params[0]
            result=Web3.to_hex(Web3.keccak(hexstr=self.raw))
        else:
            result={'eth_chainId':hex(self.chain),'eth_gasPrice':hex(self.price),
                    'eth_getTransactionCount':'0x7','eth_estimateGas':hex(22000),
                    'eth_getBalance':hex(self.balance)}[method]
        return {'jsonrpc':'2.0','id':1,'result':result}

@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    anchor._attempts.clear()
    monkeypatch.setattr(anchor,'load_dotenv',lambda:None)
    wallet=Account.create()  # transient test account; never printed/persisted
    monkeypatch.setenv('SEPOLIA_RPC','https://mock.invalid')
    monkeypatch.setenv('SEPOLIA_KEY',wallet.key.hex())
    monkeypatch.setenv('SEPOLIA_THROWAWAY','1')
    return wallet


def install_rpc(monkeypatch,**kwargs):
    rpc=FakeRPC(**kwargs)
    monkeypatch.setattr(Web3,'HTTPProvider',lambda *args,**kwargs:rpc)
    return rpc


def test_signed_zero_value_sepolia_self_transfer(monkeypatch,isolate):
    rpc=install_rpc(monkeypatch)
    tx=anchor.anchor_root(ROOT)
    assert tx==Web3.to_hex(Web3.keccak(hexstr=rpc.raw))
    assert Account.recover_transaction(rpc.raw)==isolate.address
    decoded=rlp.decode(bytes.fromhex(rpc.raw[2:]))
    assert decoded[3].hex()==isolate.address[2:].lower()
    assert decoded[4]==b''
    assert decoded[5].hex()==ROOT
    assert (int.from_bytes(decoded[6])-35)//2==11155111
    assert int.from_bytes(decoded[0])==7
    assert int.from_bytes(decoded[2])==26400
    assert any(method=='eth_getTransactionCount' and params[1]=='pending' for method,params in rpc.calls)
    assert anchor.anchor_root(ROOT)==tx
    assert sum(method=='eth_sendRawTransaction' for method,_ in rpc.calls)==1

@pytest.mark.parametrize('chain',[1,5,17000])
def test_wrong_network_never_signs_or_sends(monkeypatch,chain):
    rpc=install_rpc(monkeypatch,chain=chain)
    with pytest.raises(anchor.AnchorError,match='not Sepolia'): anchor.anchor_root(ROOT)
    assert [method for method,_ in rpc.calls]==['eth_chainId']

@pytest.mark.parametrize('root',[None,'','0x'+ROOT,'ff','g'*64])
def test_bad_root_before_rpc(root):
    with pytest.raises(anchor.AnchorError,match='64 hexadecimal'):anchor.anchor_root(root)


def test_missing_credentials(monkeypatch):
    monkeypatch.delenv('SEPOLIA_KEY')
    with pytest.raises(anchor.AnchorError,match='Configure'):anchor.anchor_root(ROOT)


def test_wrong_wallet_declaration(monkeypatch):
    monkeypatch.setenv('SEPOLIA_THROWAWAY','0')
    with pytest.raises(anchor.AnchorError,match='Configure'):anchor.anchor_root(ROOT)


@pytest.mark.parametrize('kwargs,message',[({'balance':0},'free Sepolia'),({'price':51*10**9},'50 gwei')])
def test_funding_and_fee_guard(monkeypatch,kwargs,message):
    rpc=install_rpc(monkeypatch,**kwargs)
    with pytest.raises(anchor.AnchorError,match=message):anchor.anchor_root(ROOT)
    assert not any(method=='eth_sendRawTransaction' for method,_ in rpc.calls)


def test_preparation_failure_is_sanitized(monkeypatch):
    install_rpc(monkeypatch,fail='eth_estimateGas')
    with pytest.raises(anchor.AnchorError,match='no broadcast attempted') as caught:anchor.anchor_root(ROOT)
    assert 'secret' not in str(caught.value)


def test_ambiguous_broadcast_blocks_retry(monkeypatch):
    rpc=install_rpc(monkeypatch,fail='eth_sendRawTransaction')
    with pytest.raises(anchor.SubmissionUnknown,match='do not automatically retry'):anchor.anchor_root(ROOT)
    with pytest.raises(anchor.SubmissionUnknown,match='Prior submission'):anchor.anchor_root(ROOT)
    assert sum(method=='eth_sendRawTransaction' for method,_ in rpc.calls)==1


def test_api_anchor_contract_no_request_body():
    session=Mock();session.request.return_value.status_code=200
    tx='0x'+'a'*64
    session.request.return_value.json.return_value={'tx_hash':tx,'explorer_url':'https://sepolia.etherscan.io/tx/'+tx}
    result=LiveClient('http://localhost:8000',session).anchor()
    assert result['tx_hash']==tx
    session.request.assert_called_once_with('POST','http://localhost:8000/ledger/anchor',timeout=(3.05,20),allow_redirects=False)
    session.request.return_value.json.return_value['explorer_url']='https://etherscan.io/tx/'+tx
    with pytest.raises(APIError,match='Sepolia'):LiveClient('http://localhost:8000',session).anchor()


def test_fixture_anchor_disabled(monkeypatch):
    monkeypatch.setenv('NOCAP_MODE','fixture')
    monkeypatch.setenv('NOCAP_ENABLE_ANCHOR','1')
    app=workspace_app()
    app.button(key='nav_Evidence studio').click().run()
    assert not app.exception
    assert app.button(key='anchor_submit').disabled


def test_anchor_ui_submission_no_duplicate(monkeypatch):
    # UI uses a live-shaped fake adapter; no actual HTTP or RPC here.
    monkeypatch.setenv('NOCAP_ENABLE_ANCHOR','1')
    class FakeLive(AuthenticatedFixture):
        mode='live'
        calls=0
        def ledger(self):
            return dict(super().ledger(),fixture=False)
        def anchor(self):
            self.calls+=1
            tx='0x'+'b'*64
            return {'tx_hash':tx,'explorer_url':'https://sepolia.etherscan.io/tx/'+tx}
    fake=FakeLive()
    with patch('dashboard.client.make_client',return_value=fake):
        app=workspace_app()
        app.button(key='nav_Evidence studio').click().run()
        app.button(key='anchor_submit').click().run()
        assert not app.exception
        assert fake.calls==1
        assert app.button(key='anchor_submit').disabled
        app.run()
        assert fake.calls==1
        assert any('association is unverified' in w.value for w in app.warning)


def test_anchor_ui_failure_disables_retry(monkeypatch):
    monkeypatch.setenv('NOCAP_ENABLE_ANCHOR','1')
    class FailingLive(AuthenticatedFixture):
        mode='live'
        calls=0
        def ledger(self):
            return dict(super().ledger(),fixture=False)
        def anchor(self):
            self.calls+=1
            raise APIError('API disconnected or timed out.')
    fake=FailingLive()
    with patch('dashboard.client.make_client',return_value=fake):
        app=workspace_app()
        app.button(key='nav_Evidence studio').click().run()
        app.button(key='anchor_submit').click().run()
        assert not app.exception
        assert fake.calls==1
        assert app.button(key='anchor_submit').disabled
        assert app.session_state.anchor_attempt['state']=='outcome unknown'
        app.run()
        assert fake.calls==1


def test_live_scenario_control_disabled(monkeypatch):
    monkeypatch.setenv('NOCAP_MODE','live')
    monkeypatch.setenv('NOCAP_SERVICE_DEMO','1')
    class FakeLive(AuthenticatedFixture):mode='live'
    with patch('dashboard.client.make_client',return_value=FakeLive()):
        app=workspace_app()
        app.button(key='nav_Evidence studio').click().run()
        app.button(key='nav_Settings').click().run()
        assert app.selectbox(key='fixture_scenario').disabled
