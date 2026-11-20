import hashlib
import hmac
from urllib.parse import urlencode

from app.auth.signer import IndodaxSigner


def test_sign_generates_expected_hmac_sha256_signature():
    signer = IndodaxSigner("test-secret")
    params = {
        "symbol": "BTCIDR",
        "timestamp": 123,
        "recvWindow": 5000,
    }

    signature = signer.sign(params)

    assert signature == (
        "0c5974ba1b0a57c06b7ad635d28d651e"
        "2330f7f3f4e6a31f37b2ac5c8f77d4d5"
    )


def test_sign_does_not_modify_input_params():
    signer = IndodaxSigner("test-secret")
    params = {"symbol": "BTCIDR"}
    original_params = params.copy()

    signer.sign(params)

    assert params == original_params


