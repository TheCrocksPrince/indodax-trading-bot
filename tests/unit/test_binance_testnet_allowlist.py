from unittest.mock import Mock

import pytest

from app.clients.binance_testnet_client import (
    BinanceTestnetClient,
)


@pytest.mark.parametrize(
    "method,path",
    [
        ("PUT", "/api/v3/order"),
        ("PATCH", "/api/v3/order"),
        ("POST", "/api/v3/account"),
        ("DELETE", "/api/v3/account"),
        ("GET", "/api/v3/unknown"),
    ],
)
def test_testnet_rejects_unsupported_requests(
    method,
    path,
):
    client = BinanceTestnetClient(
        transport=Mock()
    )

    try:
        with pytest.raises(PermissionError):
            client.request(
                method,
                path,
                signed=False,
            )
    finally:
        client.close()