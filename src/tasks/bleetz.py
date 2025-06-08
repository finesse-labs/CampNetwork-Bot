# src/tasks/bleetz.py
from web3 import Web3
from ..utils import logger
import time

EXPLORER_URL_CAMP_NETWORK = "https://basecamp.cloud.blockscout.com/tx/0x"
CHAIN_ID_CAMP_NETWORK = 123420001114
RPC_URL = "https://rpc.basecamp.t.raas.gelato.cloud"  # Replace with actual RPC

class Bleetz:
    def __init__(self, wallet: str, proxy: str = None):
        self.wallet = wallet
        self.proxy = proxy
        self.contract_address = "0x0b0A5B8e848b27a05D5cf45CAab72BC82dF48546"
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={'proxies': {'http': proxy, 'https': proxy}} if proxy else None))
        self.account = self.w3.eth.account.from_key(wallet.replace('0x', ''))
        self.contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(self.contract_address),
            abi=[
                {
                    "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [],
                    "name": "mintGamerID",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
        )

    def mint_nft(self) -> bool:
        """Mint BleetzGamerID NFT."""
        try:
            # Check NFT balance
            nft_balance = self.contract.functions.balanceOf(self.account.address).call()
            if nft_balance > 0:
                logger.info(f"Address {self.account.address[:8]}... already has NFT")
                return True

            logger.info(f"Minting NFT for {self.account.address[:8]}...")

            # Check ETH balance
            balance = self.w3.eth.get_balance(self.account.address)
            if balance < self.w3.to_wei(0.000001, 'ether'):
                logger.error(f"Low balance for {self.account.address[:8]}...: needs 0.000001 ETH")
                return False

            # Build transaction
            transaction = {
                'from': self.account.address,
                'to': self.w3.to_checksum_address(self.contract_address),
                'value': 0,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': CHAIN_ID_CAMP_NETWORK,
                'data': '0xae873a3f',  # Method mintGamerID()
            }

            # Estimate gas
            gas_limit = self.w3.eth.estimate_gas(transaction)
            transaction['gas'] = gas_limit

            # Get gas parameters
            gas_price = self.w3.eth.gas_price
            transaction['gasPrice'] = gas_price

            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)

            if tx_receipt.status == 1:
                logger.info(f"NFT minted for {self.account.address[:8]}...: {tx_hash.hex()[:8]}...")
                return True
            else:
                logger.error(f"Mint failed for {self.account.address[:8]}...: transaction reverted")
                return False

        except Exception as e:
            logger.error(f"Failed to mint NFT for {self.account.address[:8]}...: {e}")
            return False