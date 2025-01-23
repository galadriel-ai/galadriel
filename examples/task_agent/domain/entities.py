from dataclasses import dataclass


@dataclass
class TwitterMessage:
    task: str
    payment_signature: str
