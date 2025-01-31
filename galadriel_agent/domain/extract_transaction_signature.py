from dataclasses import dataclass
from typing import Optional

from solders.signature import Signature


@dataclass
class TaskAndPaymentSignature:
    task: str
    signature: str


def execute(message: str) -> Optional[TaskAndPaymentSignature]:
    """
    Given a string parses it to the task and the payment
    For example: "How long should I hold my ETH portfolio before selling?
    https://solscan.io/tx/5aqB4BGzQyFybjvKBjdcP8KAstZo81ooUZnf64vSbLLWbUqNSGgXWaGHNteiK2EJrjTmDKdLYHamJpdQBFevWuvy"

    :param message: string
    :return: TaskAndPaymentSignature if valid, none otherwise
    """
    if not message:
        return None

    if "https://solscan.io/tx/" in message:
        task, payment = message.split("https://solscan.io/tx/")
        task = task.strip()
        payment_signature = payment.replace("https://solscan.io/tx/", "").strip()
        return TaskAndPaymentSignature(
            task=task,
            signature=payment_signature,
        )

    signature = _find_signature(message)
    if signature:
        task = message.replace(signature, "").strip()
        return TaskAndPaymentSignature(task=task, signature=signature)
    return None


def _find_signature(message: str) -> Optional[str]:
    for word in message.split():
        try:
            signature = Signature.from_string(word.strip())
            return str(signature)
        except:
            pass
    return None
