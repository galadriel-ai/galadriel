from typing import List
from typing import Optional
from solders.signature import Signature

from domain.entities import TwitterMessage


def execute(twitter_message: str) -> Optional[TwitterMessage]:
    """
    Given a Twitter message parses it to the task and the payment
    For example: "How long should I hold my ETH portfolio before selling?
    https://solscan.io/tx/5aqB4BGzQyFybjvKBjdcP8KAstZo81ooUZnf64vSbLLWbUqNSGgXWaGHNteiK2EJrjTmDKdLYHamJpdQBFevWuvy"

    :param twitter_message: Twitter message
    :return: TwitterMessage if valid, none otherwise
    """
    if not twitter_message:
        return None

    if "https://solscan.io/tx/" in twitter_message:
        task, payment = twitter_message.split("https://solscan.io/tx/")
        task = task.strip()
        payment_signature = payment.replace("https://solscan.io/tx/", "").strip()
        return TwitterMessage(
            task=task,
            payment_signature=payment_signature,
        )

    signature = _find_signature(twitter_message)
    if signature:
        task = twitter_message.replace(signature, "").strip()
        return TwitterMessage(task=task, payment_signature=signature)


def _find_signature(twitter_message: str) -> Optional[str]:
    for word in twitter_message.split():
        try:
            signature = Signature.from_string(word.strip())
            return str(signature)
        except:
            pass
