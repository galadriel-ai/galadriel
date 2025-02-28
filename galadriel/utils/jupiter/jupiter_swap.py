import base64

import httpx
from httpx._config import Timeout

from typing import Optional

from solders import message
from solders.keypair import Keypair  # type: ignore
from solders.transaction import VersionedTransaction  # type: ignore

from solana.rpc.api import Client  # Add this import


class Jupiter:
    ENDPOINT_APIS_URL = {
        "QUOTE": "https://quote-api.jup.ag/v6/quote?",
        "SWAP": "https://quote-api.jup.ag/v6/swap",
        "OPEN_ORDER": "https://jup.ag/api/limit/v1/createOrder",
        "CANCEL_ORDERS": "https://jup.ag/api/limit/v1/cancelOrders",
        "QUERY_OPEN_ORDERS": "https://jup.ag/api/limit/v1/openOrders?wallet=",
        "QUERY_ORDER_HISTORY": "https://jup.ag/api/limit/v1/orderHistory",
        "QUERY_TRADE_HISTORY": "https://jup.ag/api/limit/v1/tradeHistory",
    }

    def __init__(
        self,
        client: Client,  # Client instance
        keypair: Keypair,
        quote_api_url: str = "https://quote-api.jup.ag/v6/quote?",
        swap_api_url: str = "https://quote-api.jup.ag/v6/swap",
        open_order_api_url: str = "https://jup.ag/api/limit/v1/createOrder",
        cancel_orders_api_url: str = "https://jup.ag/api/limit/v1/cancelOrders",
        query_open_orders_api_url: str = "https://jup.ag/api/limit/v1/openOrders?wallet=",
        query_order_history_api_url: str = "https://jup.ag/api/limit/v1/orderHistory",
        query_trade_history_api_url: str = "https://jup.ag/api/limit/v1/tradeHistory",
    ):
        self.rpc = client
        self.keypair = keypair

        self.ENDPOINT_APIS_URL["QUOTE"] = quote_api_url
        self.ENDPOINT_APIS_URL["SWAP"] = swap_api_url
        self.ENDPOINT_APIS_URL["OPEN_ORDER"] = open_order_api_url
        self.ENDPOINT_APIS_URL["CANCEL_ORDERS"] = cancel_orders_api_url
        self.ENDPOINT_APIS_URL["QUERY_OPEN_ORDERS"] = query_open_orders_api_url
        self.ENDPOINT_APIS_URL["QUERY_ORDER_HISTORY"] = query_order_history_api_url
        self.ENDPOINT_APIS_URL["QUERY_TRADE_HISTORY"] = query_trade_history_api_url

    def quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: Optional[int] = None,
        swap_mode: str = "ExactIn",
        only_direct_routes: bool = False,
        as_legacy_transaction: bool = False,
        exclude_dexes: Optional[list] = None,
        max_accounts: Optional[int] = None,
        platform_fee_bps: Optional[int] = None,
    ) -> dict:
        """Get the best swap route for a token trade pair sorted by largest output token amount from https://quote-api.jup.ag/v6/quote

        Args:
            Required:
                ``input_mint (str)``: Input token mint address\n
                ``output_mint (str)``: Output token mint address\n
                ``amount (int)``: The API takes in amount in integer and you have to factor in the decimals for each token by looking up the decimals for that token. For example, USDC has 6 decimals and 1 USDC is 1000000 in integer when passing it in into the API.\n
            Optionals:
                ``slippage_bps (int)``: The slippage % in BPS. If the output token amount exceeds the slippage then the swap transaction will fail.\n
                ``swap_mode (str)``: (ExactIn or ExactOut) Defaults to ExactIn. ExactOut is for supporting use cases where you need an exact token amount, like payments. In this case the slippage is on the input token.\n
                ``only_direct_routes (bool)``: Default is False. Direct Routes limits Jupiter routing to single hop routes only.\n
                ``as_legacy_transaction (bool)``: Default is False. Instead of using versioned transaction, this will use the legacy transaction.\n
                ``exclude_dexes (list)``: Default is that all DEXes are included. You can pass in the DEXes that you want to exclude in a list. For example, ['Aldrin','Saber'].\n
                ``max_accounts (int)``: Find a route given a maximum number of accounts involved, this might dangerously limit routing ending up giving a bad price. The max is an estimation and not the exact count.\n
                ``platform_fee_bps (int)``: If you want to charge the user a fee, you can specify the fee in BPS. Fee % is taken out of the output token.

        Returns:
            ``dict``: returns best swap route

        Example:
            >>> rpc_url = "https://neat-hidden-sanctuary.solana-mainnet.discover.quiknode.pro/2af5315d336f9ae920028bbb90a73b724dc1bbed/"
            >>> client = Client(rpc_url)
            >>> private_key_string = "tSg8j3pWQyx3TC2fpN9Ud1bS0NoAK0Pa3TC2fpNd1bS0NoASg83TC2fpN9Ud1bS0NoAK0P"
            >>> private_key = Keypair.from_bytes(base58.b58decode(private_key_string))
            >>> jupiter = Jupiter(client, private_key)
            >>> input_mint = "So11111111111111111111111111111111111111112"
            >>> output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            >>> amount = 5_000_000
            >>> quote = await jupiter.quote(input_mint, output_mint, amount)
            {
                'inputMint': 'So11111111111111111111111111111111111111112',
                'inAmount': '5000000',
                'outputMint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
                'outAmount': '353237',
                'otherAmountThreshold':'351471',
                'swapMode': 'ExactIn',
                'slippageBps': 50,
                'platformFee': None,
                'priceImpactPct': '0',
                'routePlan': [{'swapInfo': {'ammKey': 'Cx8eWxJAaCQAFVmv1mP7B2cVie2BnkR7opP8vUh23Wcr', 'label': 'Lifinity V2', 'inputMint': 'So11111111111111111111111111111111111111112', 'outputMint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'inAmount': '5000000', 'outAmount': '353237', 'feeAmount': '1000', 'feeMint': 'So11111111111111111111111111111111111111112'}, 'percent': 100}],
                'contextSlot': 236625263,
                'timeTaken': 0.069434356}
        """

        quote_url = (
            self.ENDPOINT_APIS_URL["QUOTE"]
            + "inputMint="
            + input_mint
            + "&outputMint="
            + output_mint
            + "&amount="
            + str(amount)
            + "&swapMode="
            + swap_mode
            + "&onlyDirectRoutes="
            + str(only_direct_routes).lower()
            + "&asLegacyTransaction="
            + str(as_legacy_transaction).lower()
        )
        if slippage_bps:
            quote_url += "&slippageBps=" + str(slippage_bps)
        if exclude_dexes:
            quote_url += "&excludeDexes=" + ",".join(exclude_dexes)
        if max_accounts:
            quote_url += "&maxAccounts=" + str(max_accounts)
        if platform_fee_bps:
            quote_url += "&plateformFeeBps=" + str(platform_fee_bps)

        quote_response = httpx.get(url=quote_url).json()
        try:
            quote_response["routePlan"]
            return quote_response
        except KeyError:
            raise Exception(quote_response["error"])

    def swap(
        self,
        input_mint: str,
        output_mint: str,
        amount: int = 0,
        quoteResponse: Optional[dict] = None,
        wrap_unwrap_sol: bool = True,
        slippage_bps: Optional[int] = None,
        swap_mode: str = "ExactIn",
        prioritization_fee_lamports: Optional[int] = None,
        only_direct_routes: bool = False,
        as_legacy_transaction: bool = False,
        exclude_dexes: Optional[list] = None,
        max_accounts: Optional[int] = None,
        platform_fee_bps: Optional[int] = None,
    ) -> str:
        """Perform a swap.

        Args:
            Required:
                ``input_mint (str)``: Input token mint str\n
                ``output_mint (str)``: Output token mint str\n
                ``amount (int)``: The API takes in amount in integer and you have to factor in the decimals for each token by looking up the decimals for that token. For example, USDC has 6 decimals and 1 USDC is 1000000 in integer when passing it in into the API.\n
            Optionals:
                ``prioritizationFeeLamports (int)``: If transactions are expiring without confirmation on-chain, this might mean that you have to pay additional fees to prioritize your transaction. To do so, you can set the prioritizationFeeLamports parameter.\n
                ``wrap_unwrap_sol (bool)``: Auto wrap and unwrap SOL. Default is True.\n
                ``slippage_bps (int)``: The slippage % in BPS. If the output token amount exceeds the slippage then the swap transaction will fail.\n
                ``swap_mode (str)``: (ExactIn or ExactOut) Defaults to ExactIn. ExactOut is for supporting use cases where you need an exact token amount, like payments. In this case the slippage is on the input token.\n
                ``only_direct_routes (bool)``: Default is False. Direct Routes limits Jupiter routing to single hop routes only.\n
                ``as_legacy_transaction (bool)``: Default is False. Instead of using versioned transaction, this will use the legacy transaction.\n
                ``exclude_dexes (list)``: Default is that all DEXes are included. You can pass in the DEXes that you want to exclude in a list. For example, ['Aldrin','Saber'].\n
                ``max_accounts (int)``: Find a route given a maximum number of accounts involved, this might dangerously limit routing ending up giving a bad price. The max is an estimation and not the exact count.\n
                ``platform_fee_bps (int)``: If you want to charge the user a fee, you can specify the fee in BPS. Fee % is taken out of the output token.

        Returns:
            ``str``: returns serialized transactions to perform the swap from https://quote-api.jup.ag/v6/swap

        Example:
            >>> rpc_url = "https://neat-hidden-sanctuary.solana-mainnet.discover.quiknode.pro/2af5315d336f9ae920028bbb90a73b724dc1bbed/"
            >>> client = Client(rpc_url)
            >>> private_key_string = "tSg8j3pWQyx3TC2fpN9Ud1bS0NoAK0Pa3TC2fpNd1bS0NoASg83TC2fpN9Ud1bS0NoAK0P"
            >>> private_key = Keypair.from_bytes(base58.b58decode(private_key_string))
            >>> jupiter = Jupiter(client, private_key)
            >>> input_mint = "So11111111111111111111111111111111111111112"
            >>> output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            >>> amount = 5_000_000
            >>> transaction_data = await jupiter.swap(user_public_key, input_mint, output_mint, amount)
            AQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAQAJDpQzg6Gwmq0Gtgp4+LWUVz0yQOAuHGNJAGTs0dcqEMVCBvqBKhFi2uRFEKYI4zPatxbdm7DylvnQUby9MexSmeAdsqhWUMQ86Ddz4+7pQFooE6wLglATS/YvzOVUNMOqnyAmC8Ioh9cSvEZniys4XY0OyEvxe39gSdHqlHWJQUPMn4prs0EwIc9JznmgzyMliG5PJTvaFYw75ssASGlB2gMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAImg/TLoYktlelMGKAi4mA0icnTD92092qSZhd3wNABMCv4fVqQvV1OYZ3a3bH43JpI5pIln+UAHnO1fyDJwCfIGm4hX/quBhPtof2NGGMA12sQ53BrrO1WYoPAAAAAAAQbd9uHXZaGT2cvhRs7reawctIXtX1s3kTqM9YV+/wCpT0tsDkEI/SpqJHjq4KzFnbIbtO31EcFiz2AtHgwJAfuMlyWPTiSJ8bs9ECkUjg2DC1oTmdr/EIQEjnvY2+n4WbQ/+if11/ZKdMCbHylYed5LCas238ndUUsyGqezjOXoxvp6877brTo9ZfNqq8l0MbG75MLS9uDkfKYCA0UvXWHmraeknnR8/memFAZWZHeDMQG7C5ZFLxolWUniPl6SYgcGAAUCwFwVAAYACQNIDQAAAAAAAAsGAAMACAUJAQEFAgADDAIAAAAgTgAAAAAAAAkBAwERBx8JCgADAQIECA0HBwwHGREBAhUOFxMWDxIQFAoYCQcHJMEgmzNB1pyBBwEAAAATZAABIE4AAAAAAACHBQAAAAAAADIAAAkDAwAAAQkB1rO1s+JVEuIRoGsE8f2MlAkFWssCkimIonlHpLV2w4gKBwKRTE0SjIeLSwIICg==
        """

        if quoteResponse is None:
            quoteResponse = self.quote(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                slippage_bps=slippage_bps,
                swap_mode=swap_mode,
                only_direct_routes=only_direct_routes,
                as_legacy_transaction=as_legacy_transaction,
                exclude_dexes=exclude_dexes,
                max_accounts=max_accounts,
                platform_fee_bps=platform_fee_bps,
            )

        transaction_parameters = {
            "quoteResponse": quoteResponse,
            "userPublicKey": self.keypair.pubkey().__str__(),
            "wrapAndUnwrapSol": wrap_unwrap_sol,
        }
        if prioritization_fee_lamports:
            transaction_parameters.update({"prioritizationFeeLamports": prioritization_fee_lamports})
        transaction_data = httpx.post(url=self.ENDPOINT_APIS_URL["SWAP"], json=transaction_parameters).json()
        return transaction_data["swapTransaction"]

    def open_order(
        self,
        input_mint: str,
        output_mint: str,
        in_amount: int = 0,
        out_amount: int = 0,
        expired_at: Optional[int] = None,
    ) -> dict:
        """Open an order.

        Args:
            Required:
                ``input_mint (str)``: Input token mint address\n
                ``output_mint (str)``: Output token mint address\n
                ``in_amount (int)``: The API takes in amount in integer and you have to factor in the decimals for each token by looking up the decimals for that token. For example, USDC has 6 decimals and 1 USDC is 1000000 in integer when passing it in into the API.\n
                ``out_amount (int)``: The API takes in amount in integer and you have to factor in the decimals for each token by looking up the decimals for that token. For example, USDC has 6 decimals and 1 USDC is 1000000 in integer when passing it in into the API.\n
            Optionals:
                ``expired_at (int)``: Deadline for when the limit order expires. It can be either None or Unix timestamp in seconds.
        Returns:
            ``dict``: transaction_data and signature2 in order to create the limit order.

        Example:
            >>> rpc_url = "https://neat-hidden-sanctuary.solana-mainnet.discover.quiknode.pro/2af5315d336f9ae920028bbb90a73b724dc1bbed/"
            >>> client = Client(rpc_url)
            >>> private_key_string = "tSg8j3pWQyx3TC2fpN9Ud1bS0NoAK0Pa3TC2fpNd1bS0NoASg83TC2fpN9Ud1bS0NoAK0P"
            >>> private_key = Keypair.from_bytes(base58.b58decode(private_key_string))
            >>> jupiter = Jupiter(client, private_key)
            >>> input_mint = "So11111111111111111111111111111111111111112"
            >>> output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            >>> in_amount = 5_000_000
            >>> out_amount = 100_000
            >>> transaction_data = await jupiter.open_order(
            ...     user_public_key, input_mint, output_mint, in_amount, out_amount
            ... )
            {
                'transaction_data': 'AgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgEGC5Qzg6Gwmq0Gtgp4+LWUVz0yQOAuHGNJAGTs0dcqEMVCBvqBKhFi2uRFEKYI4zPatxbdm7DylvnQUby9MexSmeAdsqhWUMQ86Ddz4+7pQFooE6wLglATS/YvzOVUNMOqnyAmC8Ioh9cSvEZniys4XY0OyEvxe39gSdHqlHWJQUPMn4prs0EwIc9JznmgzyMliG5PJTvaFYw75ssASGlB2gMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAImg/TLoYktlelMGKAi4mA0icnTD92092qSZhd3wNABMCv4fVqQvV1OYZ3a3bH43JpI5pIln+UAHnO1fyDJwCfIGm4hX/quBhPtof2NGGMA12sQ53BrrO1WYoPAAAAAAAQan1RcZLFxRIYzJTD1K8X9Y2u4Im6H9ROPb2YoAAAAABt324ddloZPZy+FGzut5rBy0he1fWzeROoz1hX7/AKmr+pT0gdwb1ZeE73qr11921UvCtCB3MMpBcLaiY8+u7QEHDAEABAMCCAIHBgUKCRmFbkqvcJ/1nxAnAAAAAAAAECcAAAAAAAAA',
                'signature2': Signature(
                    2Pip6gx9FLGVqmRqfAgwJ8HEuCY8ZbUbVERR18vHyxFngSi3Jxq8Vkpm74hS5zq7RAM6tqGUAkf3ufCBsxGXZrUC,)
            }
        """

        keypair = Keypair()
        transaction_parameters = {
            "owner": self.keypair.pubkey().__str__(),
            "inputMint": input_mint,
            "outputMint": output_mint,
            "outAmount": out_amount,
            "inAmount": in_amount,
            "base": keypair.pubkey().__str__(),
        }
        if expired_at:
            transaction_parameters["expiredAt"] = expired_at
        transaction_data = httpx.post(url=self.ENDPOINT_APIS_URL["OPEN_ORDER"], json=transaction_parameters).json()[
            "tx"
        ]
        raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
        signature2 = keypair.sign_message(message.to_bytes_versioned(raw_transaction.message))
        return {"transaction_data": transaction_data, "signature2": signature2}

    def cancel_orders(self, orders: list = []) -> str:
        """Cancel open orders from a list (max. 10).

        Args:
            Required:!:
                ``orders (list)``: List of orders to be cancelled.
        Returns:
            ``str``: returns serialized transactions to cancel orders from https://jup.ag/api/limit/v1/cancelOrders

        Example:
            >>> rpc_url = "https://neat-hidden-sanctuary.solana-mainnet.discover.quiknode.pro/2af5315d336f9ae920028bbb90a73b724dc1bbed/"
            >>> client = Client(rpc_url)
            >>> private_key_string = "tSg8j3pWQyx3TC2fpN9Ud1bS0NoAK0Pa3TC2fpNd1bS0NoASg83TC2fpN9Ud1bS0NoAK0P"
            >>> private_key = Keypair.from_bytes(base58.b58decode(private_key_string))
            >>> jupiter = Jupiter(client, private_key)
            >>> list_orders = [
            ...     item["publicKey"] for item in await jupiter.query_open_orders()
            ... ]  # Cancel all open orders
            >>> transaction_data = await jupiter.cancel_orders(orders=openOrders)
            AQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAQIlDODobCarQa2Cnj4tZRXPTJA4C4cY0kAZOzR1yoQxUIklPdDonxNd5JDfdYoHE56dvNBQ1SLN90fFZxvVlzZr9DPwpfbd+ANTB35SSvHYVViD27UZR578oC2faxJea7y958guyGPhmEVKNR9GmJIjjuZU0VSr2/k044JZIRklkwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAr+H1akL1dTmGd2t2x+NyaSOaSJZ/lAB5ztX8gycAnyBpuIV/6rgYT7aH9jRhjANdrEOdwa6ztVmKDwAAAAAAEG3fbh12Whk9nL4UbO63msHLSF7V9bN5E6jPWFfv8AqW9ZjNTy3JS6YYFodCWqtWH80+eLPmN4igHrkYHIsdQfAQUHAQIAAwQHBghfge3wCDHfhA==
        """

        transaction_parameters = {
            "owner": self.keypair.pubkey().__str__(),
            "feePayer": self.keypair.pubkey().__str__(),
            "orders": orders,
        }
        transaction_data = httpx.post(url=self.ENDPOINT_APIS_URL["CANCEL_ORDERS"], json=transaction_parameters).json()[
            "tx"
        ]
        return transaction_data

    @staticmethod
    async def query_open_orders(
        wallet_address: str, input_mint: Optional[str] = None, output_mint: Optional[str] = None
    ) -> list:
        """
        Query open orders from self.keypair public address.

        Args:
            Required:
                ``wallet_address (str)``: Wallet address.
            Optionals:
                ``input_mint (str)``: Input token mint address.
                ``output_mint (str)``: Output token mint address.
        Returns:
            ``list``: returns open orders list from https://jup.ag/api/limit/v1/openOrders

        Example:
            >>> list_open_orders = await Jupiter.query_open_orders("AyWu89SjZBW1MzkxiREmgtyMKxSkS1zVy8Uo23RyLphX")
            [
                {
                    'publicKey': '3ToRYxxMHN3CHkbqWHcbXBCBLNqmDeLoubGGfNKGSCDL',
                    'account': {
                        'maker': 'AyWu89SjZBW1MzkxiREmgtyMKxSkS1zVy8Uo23RyLphX',
                        'inputMint': 'So11111111111111111111111111111111111111112',
                        'outputMint': 'AGFEad2et2ZJif9jaGpdMixQqvW5i81aBdvKe7PHNfz3',
                        'oriInAmount': '10000',
                        'oriOutAmount': '10000',
                        'inAmount': '10000',
                        'outAmount': '10000',
                        'expiredAt': None,
                        'base': 'FghAhphJkhT74PXFQAz3QKqGVGA72Y2gUeVHU7QRw31c'
                    }
                }
            ]
        """

        query_openorders_url = "https://jup.ag/api/limit/v1/openOrders?wallet=" + wallet_address
        if input_mint:
            query_openorders_url += "inputMint=" + input_mint
        if output_mint:
            query_openorders_url += "outputMint" + output_mint

        list_open_orders = httpx.get(query_openorders_url, timeout=Timeout(timeout=30.0)).json()
        return list_open_orders

    @staticmethod
    async def query_orders_history(
        wallet_address: str,
        cursor: Optional[int] = None,
        skip: Optional[int] = None,
        take: Optional[int] = None,
    ) -> list:
        """
        Query orders history from self.keypair public address.

        Args:
            Required:
                ``wallet_address (str)``: Wallet address.
            Optionals:
                ``cursor (int)``: Pointer to a specific result in the data set.
                ``skip (int)``: Number of records to skip from the beginning.
                ``take (int)``: Number of records to retrieve from the current position.
        Returns:
            ``list``: returns open orders list from https://jup.ag/api/limit/v1/orderHistory

        Example:
            >>> list_orders_history = await Jupiter.query_orders_history("AyWu89SjZBW1MzkxiREmgtyMKxSkS1zVy8Uo23RyLphX")
            [
                {
                    'id': 1639144,
                    'orderKey': '3ToRYxxMHN3CHkbqWHcbXBCBLNqmDeLoubGGfNKGSCDL',
                    'maker': 'AyWu89SjZBW1MzkxiREmgtyMKxSkS1zVy8Uo23RyLphX',
                    'inputMint': 'So11111111111111111111111111111111111111112',
                    'outputMint': 'AGFEad2et2ZJif9jaGpdMixQqvW5i81aBdvKe7PHNfz3',
                    'inAmount': '10000',
                    'oriInAmount': '10000',
                    'outAmount': '10000',
                    'oriOutAmount': '10000',
                    'expiredAt': None,
                    'state': 'Cancelled',
                    'createTxid': '4CYy8wZG2aRPctL9do7UBzaK9w4EDLJxGkkU1EEAx4LYNYW7j7Kyet2vL4q6cKK7HbJNHp6QXzLQftpTiDdhtyfL',
                    'cancelTxid': '83eN6Lm41t2VWUchm1T6hWX2qK3sf39XzPGbxV9s2WjBZfdUADQdRGg2Y1xAKn4igMJU1xRPCTgUhnm6qFUPWRc',
                    'updatedAt': '2023-12-18T15:55:30.617Z',
                    'createdAt': '2023-12-18T15:29:34.000Z'
                }
            ]
        """

        query_orders_history_url = "https://jup.ag/api/limit/v1/orderHistory" + "?wallet=" + wallet_address
        if cursor:
            query_orders_history_url += "?cursor=" + str(cursor)
        if skip:
            query_orders_history_url += "?skip=" + str(skip)
        if take:
            query_orders_history_url += "?take=" + str(take)

        list_orders_history = httpx.get(query_orders_history_url, timeout=Timeout(timeout=30.0)).json()
        return list_orders_history

    @staticmethod
    async def query_trades_history(
        wallet_address: str,
        input_mint: Optional[str] = None,
        output_mint: Optional[str] = None,
        cursor: Optional[int] = None,
        skip: Optional[int] = None,
        take: Optional[int] = None,
    ) -> list:
        """
        Query trades history from a public address.

        Args:
            Required:
                ``wallet_address (str)``: Wallet address.
            Optionals:
                ``input_mint (str)``: Input token mint address.
                ``output_mint (str)``: Output token mint address.
                ``cursor (int)``: Pointer to a specific result in the data set.
                ``skip (int)``: Number of records to skip from the beginning.
                ``take (int)``: Number of records to retrieve from the current position.
        Returns:
            ``list``: returns trades history list from https://jup.ag/api/limit/v1/tradeHistory

        Example:
            >>> list_trades_history = await Jupiter.query_trades_history("AyWu89SjZBW1MzkxiREmgtyMKxSkS1zVy8Uo23RyLphX")
            [
                {
                    'id': 10665592,
                    'inAmount':
                    '10000000',
                    'outAmount': '675870652',
                    'txid': '5rmA1S5MDAVdRYWeVgUWYFp6pYuy5vwrYpRJUJdhjoWnuuheeg1YwqK6P5H6u4tv99cUwQttSBYm6kjSNHJGENgb',
                    'updatedAt': '2023-12-13T15:39:04.800Z',
                    'createdAt': '2023-12-13T15:37:08.000Z',
                    'order': {
                        'id': 1278268,
                        'orderKey': '3bGykFCMWPNQDTRVBdKBbZuVHqNB5z5XaphkRHLWYmE5',
                        'inputMint': 'So11111111111111111111111111111111111111112',
                        'outputMint': '8XSsNvaKU9FDhYWAv7Yc7qSNwuJSzVrXBNEk7AFiWF69'
                    }
                }
            ]
        """

        query_tradeHistoryUrl = "https://jup.ag/api/limit/v1/tradeHistory" + "?wallet=" + wallet_address
        if input_mint:
            query_tradeHistoryUrl += "inputMint=" + input_mint
        if output_mint:
            query_tradeHistoryUrl += "outputMint" + output_mint
        if cursor:
            query_tradeHistoryUrl += "?cursor=" + str(cursor)
        if skip:
            query_tradeHistoryUrl += "?skip=" + str(skip)
        if take:
            query_tradeHistoryUrl += "?take=" + str(take)

        tradeHistory = httpx.get(query_tradeHistoryUrl, timeout=Timeout(timeout=30.0)).json()
        return tradeHistory

    @staticmethod
    async def get_indexed_route_map() -> dict:
        """
        Retrieve an indexed route map for all the possible token pairs you can swap between.

        Returns:
            ``dict``: indexed route map for all the possible token pairs you can swap betwee from https://quote-api.jup.ag/v6/indexed-route-map

        Example:
            >>> indexed_route_map = await Jupiter.get_indexed_route_map()
        """

        indexed_route_map = httpx.get(
            "https://quote-api.jup.ag/v6/indexed-route-map", timeout=Timeout(timeout=30.0)
        ).json()
        return indexed_route_map

    @staticmethod
    async def get_tokens_list(list_type: str = "strict", banned_tokens: bool = False) -> dict:
        """
        The Jupiter Token List API is an open, collaborative, and dynamic token list to make trading on Solana more transparent and safer for users and developers.\n
        There are two types of list:\n
        ``strict``\n
            - Only tokens that are tagged "old-registry", "community", or "wormhole" verified.\n
            - No unknown and banned tokens.\n
        ``all``\n
            - Everything including unknown/untagged tokens that are picked up automatically.\n
            - It does not include banned tokens by default.\n
            - Often, projects notice that the token got banned and withdraw liquidity. As our lists are designed for trading, banned tokens that used to, but no longer meet our minimum liquidity requirements will not appear in this response.

        Args:
            Optionals:
                ``list_type (str)``: Default is "strict" (strict/all).
                ``banned_tokens (bool)``: Only if list_type is "all"
        Returns:
            ``dict``: indexed route map for all the possible token pairs you can swap betwee from https://token.jup.ag/{list_type}

        Example:
        >>> tokens_list = await Jupiter.get_tokens_list()
        """

        tokens_list_url = "https://token.jup.ag/" + list_type
        if banned_tokens is True:
            tokens_list_url += "?includeBanned=true"
        tokens_list = httpx.get(tokens_list_url, timeout=Timeout(timeout=30.0)).json()
        return tokens_list

    @staticmethod
    async def get_all_tickers() -> dict:
        """Returns all tickers (cached for every 2-5 mins) from https://stats.jup.ag/coingecko/tickers

        Returns:
            ``dict``: all tickers(cached for every 2-5 mins)

        Example:
            >>> all_tickers_list = await Jupiter.get_all_tickers()
        """
        all_tickers_list = httpx.get("https://stats.jup.ag/coingecko/tickers", timeout=Timeout(timeout=30.0)).json()
        return all_tickers_list

    @staticmethod
    async def get_all_swap_pairs() -> dict:
        """Returns all swap pairs (cached for every 2-5 mins) from https://stats.jup.ag/coingecko/pairs

        Returns:
            ``dict``: all swap pairs

        Example:
            >>> all_swap_pairs_list = await Jupiter.get_all_swap_pairs()
        """
        all_swap_pairs_list = httpx.get("https://stats.jup.ag/coingecko/pairs", timeout=Timeout(timeout=30.0)).json()
        return all_swap_pairs_list

    @staticmethod
    async def get_swap_pairs(
        input_mint: str,
        output_mint: str,
    ) -> dict:
        """Returns swap pairs for input token and output token

        Args:
            Required:
                ``input_mint (str)``: Input token mint address.\n
                ``output_mint (str)``: Output token mint address.\n

        Returns:
            ``dict``: all swap pairs for input token and output token

        Example:
            >>> swap_pairs_list = await Jupiter.get_swap_pairs(
            ...     "So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            ... )
        """
        swap_pairs_url = "https://stats.jup.ag/coingecko/tickers?ticker_id=" + input_mint + "_" + output_mint
        swap_pairs_list = httpx.get(swap_pairs_url, timeout=Timeout(timeout=30.0)).json()
        return swap_pairs_list

    @staticmethod
    async def get_token_stats_by_date(
        token: str,
        date: str,
    ) -> list:
        """Returns swap pairs for input token and output token

        Args:
            Required:
                ``token (str)``: Input token mint address.\n
                ``date (str)``: YYYY-MM-DD format date.\n

        Returns:
            ``list``: all swap pairs for input token and output token

        Example:
            >>> token_stats_by_date = await Jupiter.get_swap_pairs(
            ...     "B5mW68TkDewnKvWNc2trkmmdSRxcCjZz3Yd9BWxQTSRU", "2022-04-1"
            ... )
        """
        token_stats_by_date_url = "https://stats.jup.ag/token-ledger/" + token + "/" + date
        token_stats_by_date = httpx.get(token_stats_by_date_url, timeout=Timeout(timeout=30.0)).json()
        return token_stats_by_date

    @staticmethod
    async def get_jupiter_stats(
        unit_of_time: str,
    ) -> dict:
        """Stats for the unit of time specified.

        Args:
            Required:
                ``unit_of_time (str)``: Unit of time: day/week/month

        Returns:
            ``dict``: stats for the unit of time specified.

        Example:
            >>> jupiter_stats = await Jupiter.get_jupiter_stats("day")
        """
        jupiter_stats_url = "https://stats.jup.ag/info/" + unit_of_time
        jupiter_stats = httpx.get(jupiter_stats_url, timeout=Timeout(timeout=30.0)).json()
        return jupiter_stats

    @staticmethod
    async def get_token_price(
        input_mint: str,
        output_mint: Optional[str] = None,
    ) -> dict:
        """The Jupiter Price API aims to make getting precise and real-time pricing for all SPL tokens as powerful and simple as possible.

        Args:
            Required:
                ``input_mint (str)``: Input token mint name or address.
            Optionals:
                ``output_mint (str)``: Output token mint name or address.

        Returns:
            ``dict``: id, mintSymbol, vsToken, vsTokenSymbol, price, timeTaken

        Example:
            >>> token_price = await Jupiter.get_jupiter_stats("So11111111111111111111111111111111111111112", "USDC")
        {
            'So11111111111111111111111111111111111111112': {
                'id': 'So11111111111111111111111111111111111111112',
                'mintSymbol': 'SOL',
                'vsToken': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
                'vsTokenSymbol': 'USDC',
                'price': 71.893496709
            }
        }
        """
        token_prices_url = "https://price.jup.ag/v4/price?ids=" + input_mint
        if output_mint:
            token_prices_url += "&vsToken=" + output_mint
        token_prices = httpx.get(token_prices_url, timeout=Timeout(timeout=30.0)).json()["data"]
        return token_prices

    @staticmethod
    async def program_id_to_label() -> dict:
        """Returns a dict, which key is the program id and value is the label.\n
        This is used to help map error from transaction by identifying the fault program id.\n
        With that, we can use the exclude_dexes or dexes parameter for swap.

        Returns:
            ``dict``: program_id and label

        Example:
            >>> program_id_to_label_list = await Jupiter.program_id_to_label()
        """
        program_id_to_label_list = httpx.get(
            "https://quote-api.jup.ag/v6/program-id-to-label", timeout=Timeout(timeout=30.0)
        ).json()
        return program_id_to_label_list
