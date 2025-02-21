from abc import ABC, abstractmethod


class WalletBase(ABC):
    @abstractmethod
    def get_address(self) -> str:
        pass

    # TODO: add fns sign() to allow wallets sign transactions
