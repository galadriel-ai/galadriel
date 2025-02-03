import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv
from solders.keypair import Keypair

from examples.trading.repositories.solana_repository import SolanaRepository

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)


async def main():
    pub_key = "3pAxo3Ae1Uo6kmY3qmQvkJ41hJacxFhEQVLwRiQFbw5j"
    pub_key2 = "EPQbJZLiUwdoK7yVdBP3QcfEF6nruWswJb3FGcKxaDDu"
    repo = SolanaRepository("/Users/kristjanpeterson/.config/solana/devnet.json")

    # await transfer(pub_key, pub_key2, repo)

    # response = await repo.fetch_account_data(
    #     "HCkvLKhWQ8TTRdoSry29epRZnAoEDhP9CjmDS8jLtY9"
    # )
    # print(response)



async def transfer(pub_key, pub_key2, repo):
    balance = await repo.get_user_token_balance(pub_key)
    print(f"Origin balance before: {balance}")
    balance = await repo.get_user_token_balance(pub_key2)
    print(f"Destination balance before: {balance}")
    transfer_result = await repo.transfer_sol(pub_key2, 0.01)
    balance = await repo.get_user_token_balance(pub_key)
    print(f"Origin balance after: {balance}")
    balance = await repo.get_user_token_balance(pub_key2)
    print(f"Destination balance after: {balance}")


if __name__ == '__main__':
    asyncio.run(main())
