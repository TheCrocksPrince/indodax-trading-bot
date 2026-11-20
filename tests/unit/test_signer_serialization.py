import hashlib
import hmac
import json

import httpx

from app.auth.signer import IndodaxSigner


def assert_signature_matches_body(params):
    secret = "unit-test-secret"
    signature = IndodaxSigner(secret).sign(params)

    request = httpx.Request(
        "POST",
        "https://api.indodax.com/test",
        data=params,
    )

    expected = hmac.new(
        secret.encode("utf-8"),
        request.content,
        hashlib.sha256,
    ).hexdigest()

    assert signature == expected


def test_crypto_withdrawal_signing():
    assert_signature_matches_body({
        "coin": "BTC",
        "network": "BTC",
        "address": "test-address",
        "amount": "0.001",
        "withdrawOrderId": "test001",
        "timestamp": 1234567890000,
        "recvWindow": 5000,
    })


def test_idr_withdrawal_signing():
    assert_signature_matches_body({
        "apiPaymentMethod": "bank_transfer",
        "currency": "IDR",
        "amount": 200000,
        "accountInfo": json.dumps(
            {
                "accountNumber": "0012345678",
                "bankCodeForPix": "014",
            },
            separators=(",", ":"),
        ),
        "clientRequestId": "testidr001",
        "timestamp": 1234567890000,
        "recvWindow": 5000,
    })