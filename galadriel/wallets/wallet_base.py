from abc import ABC, abstractmethod


class WalletBase(ABC):
    @abstractmethod
    def get_address(self) -> str:
        pass

    # @abstractmethod
    # def sign_message(self, message: str) -> str:
    #    pass

    # @abstractmethod
    # def balance_of(self, address: str) -> float:
    #    pass
