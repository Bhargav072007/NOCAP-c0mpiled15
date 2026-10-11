"""Server-side Sepolia anchoring. Never import wallet secrets into browser code.

The caller must persist (root, tx_hash) and reconcile ambiguous submissions.
Process-local protection is not a replacement for API/database idempotency.
"""
import os
import re
import threading
from urllib.parse import urlparse
from dotenv import load_dotenv
from web3 import Web3

SEPOLIA_CHAIN_ID = 11155111
_lock = threading.Lock()
_attempts: dict[tuple[str, str], tuple[str, bool]] = {}


class AnchorError(Exception):
    """Sanitized configuration/RPC failure."""


class SubmissionUnknown(AnchorError):
    """An RPC failure after signing must be reconciled before retry."""


def anchor_root(root_hex: str) -> str:
    """Submit a 0-value self-transfer with the 32-byte root as transaction data.

    Returns a submitted transaction hash, not a confirmation. Refuses all chain
    IDs other than Sepolia. SEPOLIA_THROWAWAY=1 declares a disposable wallet.
    """
    if not isinstance(root_hex,str) or not re.fullmatch(r'[0-9a-fA-F]{64}',root_hex):
        raise AnchorError('Root must be exactly 64 hexadecimal characters without 0x.')
    root_hex=root_hex.lower()
    load_dotenv()
    rpc=os.getenv('SEPOLIA_RPC','')
    key=os.getenv('SEPOLIA_KEY','')
    if not rpc or not key or os.getenv('SEPOLIA_THROWAWAY')!='1':
        raise AnchorError('Configure SEPOLIA_RPC, SEPOLIA_KEY and SEPOLIA_THROWAWAY=1 on the API host.')
    if urlparse(rpc).scheme not in ('http','https') or not urlparse(rpc).netloc:
        raise AnchorError('SEPOLIA_RPC must be an HTTP(S) endpoint.')
    with _lock:
        try:
            w3=Web3(Web3.HTTPProvider(rpc,request_kwargs={'timeout':15},exception_retry_configuration=None))
            if w3.eth.chain_id!=SEPOLIA_CHAIN_ID:
                raise AnchorError('Refusing transaction: RPC chain is not Sepolia (11155111).')
            account=w3.eth.account.from_key(key)
            cache_key=(account.address,root_hex)
            if cache_key in _attempts:
                tx_hash,submitted=_attempts[cache_key]
                if submitted:
                    return tx_hash
                raise SubmissionUnknown(f'Prior submission outcome unknown. Reconcile {tx_hash} on Sepolia before any retry.')
            gas_price=int(w3.eth.gas_price)
            if not 0 < gas_price <= Web3.to_wei(50,'gwei'):
                raise AnchorError('RPC gas price exceeds the 50 gwei testnet guard or is invalid.')
            transaction={'from':account.address,'to':account.address,'value':0,
                         'data':'0x'+root_hex,'chainId':SEPOLIA_CHAIN_ID,
                         'nonce':w3.eth.get_transaction_count(account.address,'pending'),
                         'gasPrice':gas_price}
            estimate=int(w3.eth.estimate_gas(transaction))
            if not 21000 <= estimate <= 100000:
                raise AnchorError('Unexpected gas estimate; no transaction sent.')
            transaction['gas']=(estimate*12+9)//10
            if w3.eth.get_balance(account.address)<transaction['gas']*gas_price:
                raise AnchorError('Throwaway wallet needs free Sepolia test ETH for gas.')
            signed=account.sign_transaction(transaction)
            tx_hash=Web3.to_hex(signed.hash)
        except AnchorError:
            raise
        except Exception:
            raise AnchorError('Could not prepare Sepolia transaction. Check API-host configuration and RPC; no broadcast attempted.') from None
        _attempts[cache_key]=(tx_hash,False)
        try:
            returned=Web3.to_hex(w3.eth.send_raw_transaction(signed.raw_transaction))
            if returned.lower()!=tx_hash.lower():
                raise ValueError('RPC hash mismatch')
        except Exception:
            raise SubmissionUnknown(f'Submission outcome unknown. Reconcile {tx_hash} on Sepolia; do not automatically retry.') from None
        _attempts[cache_key]=(tx_hash,True)
        return tx_hash


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Anchor one root on Sepolia using a configured disposable wallet.')
    parser.add_argument('root_hex')
    args=parser.parse_args()
    try:
        print(anchor_root(args.root_hex))
    except AnchorError as exc:
        parser.exit(2,str(exc)+'\n')
