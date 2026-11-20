
import re
from typing import Any, Dict, List

import httpx


class IndodaxMarketDataClient:
    """Client untuk membaca data pasar publik Indodax."""

    BASE_URL = "https://indodax.com"
    TIMEOUT = 10.0

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str) -> Any:
        """Mengirim GET request dan memeriksa respons HTTP."""
        response = httpx.get(
            "{}{}".format(self.base_url, path),
            timeout=self.TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _validate_pair_id(pair_id: str) -> str:
        """Validasi format pair ID, misalnya btcidr."""
        normalized = pair_id.strip().lower()

        if not re.fullmatch(r"[a-z0-9]+", normalized):
            raise ValueError(
                "Invalid pair_id format. Example: btcidr"
            )

        return normalized

    def get_pairs(self) -> List[Dict[str, Any]]:
        """Mengambil daftar pasangan trading yang tersedia."""
        data = self._get("/api/pairs")

        if not isinstance(data, list):
            raise ValueError("Unexpected response format from /api/pairs")

        return data

    def get_ticker(self, pair_id: str = "btcidr") -> Dict[str, Any]:
        """
        Mengambil ticker satu pasangan trading.

        Endpoint: GET /api/ticker/{pair_id}
        """
        pair_id = self._validate_pair_id(pair_id)
        data = self._get("/api/ticker/{}".format(pair_id))

        if not isinstance(data, dict) or "ticker" not in data:
            raise ValueError("Unexpected ticker response format")

        return data["ticker"]

    def get_order_book(self, pair_id: str = "btcidr") -> Dict[str, Any]:
        """
        Mengambil order book sisi buy dan sell.

        Endpoint: GET /api/depth/{pair_id}
        """
        pair_id = self._validate_pair_id(pair_id)
        data = self._get("/api/depth/{}".format(pair_id))

        if not isinstance(data, dict):
            raise ValueError("Unexpected order book response format")

        if "buy" not in data or "sell" not in data:
            raise ValueError("Order book response is missing buy/sell")

        return data
