# main.py
import signal
import rich
import sys
import time
import random
import os
from concurrent.futures import ThreadPoolExecutor

from src.interface import display_start, clear_screen
from src.account_parser import parse_accounts, load_proxies, load_wallets, load_quests
from src.worker import process_account
from src.utils import logger

from config import SHUFFLE_ACCOUNTS, SHUFFLE_QUESTS, ACCOUNT_LAUNCH_DELAY, CAPTCHA_API_KEY

def signal_handler(sig, frame):
    """Handle program shutdown."""
    rich.print("\n[bold green]✅ Quick software shutdown[/bold green]")
    time.sleep(0.2)
    os._exit(1)

signal.signal(signal.SIGINT, signal_handler)

def handle_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions."""
    if not issubclass(exc_type, KeyboardInterrupt):
        rich.print(f"\n[bold red]⛔ Software stopped due to an error: {str(exc_value)}[/bold red]")
    os._exit(1)

sys.excepthook = handle_exception

def main():
    logger.info("Bot started")
    # Load data
    accounts = parse_accounts("config", shuffle=False)
    proxies = load_proxies("config")
    wallets = load_wallets("config")
    quests = load_quests("data", shuffle=SHUFFLE_QUESTS)

    if not accounts or not wallets or not quests:
        logger.error("Failed to load accounts, wallets, or quests")
        sys.exit(1)

    # Check counts
    if len(accounts) != len(wallets):
        logger.error(f"Number of accounts ({len(accounts)}) must match number of wallets ({len(wallets)})")
        sys.exit(1)
    
    if proxies and len(proxies) != len(accounts):
        logger.error(f"Number of proxies ({len(proxies)}) must match number of accounts ({len(accounts)})")
        sys.exit(1)
    
    # Fill proxies with None if empty
    proxies = proxies or [None] * len(accounts)

    # Create pairs (account, wallet, proxy)
    paired_data = list(zip(accounts, wallets, proxies))
    
    # Shuffle if needed
    if SHUFFLE_ACCOUNTS:
        random.shuffle(paired_data)

    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = []
        for account, wallet, proxy in paired_data:
            future = executor.submit(process_account, account, wallet, quests, proxy, CAPTCHA_API_KEY)
            
            delay = random.uniform(ACCOUNT_LAUNCH_DELAY[0] * 60, ACCOUNT_LAUNCH_DELAY[1] * 60)
            logger.info(f"Waiting {delay:.2f} seconds before processing account with wallet {wallet[:10]}...")
            time.sleep(delay)
            futures.append(future)
        
        # Wait for all tasks to complete
        for future in futures:
            future.result()

if __name__ == "__main__":
    clear_screen()
    display_start()
    main()