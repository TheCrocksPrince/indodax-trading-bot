import hashlib
import hmac
from urllib.parse import urlencode


class IndodaxSigner:
    """
    Creates HMAC-SHA256 signatures for Indodax TAPI v2 requests.
    """

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def sign(self, params: dict) -> str:
        query_string = urlencode(params)

        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature
    