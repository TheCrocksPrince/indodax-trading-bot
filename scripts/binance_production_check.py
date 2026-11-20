from app.clients.binance_client import BinanceClient


def main():
    client = BinanceClient(
        base_url="https://api.binance.com",
        api_key="",
        secret_key="",
    )

    print("=== Binance Production Public API ===")

    server_time = client.get_server_time()
    print("Server Time:", server_time["serverTime"])

    exchange_info = client.get_exchange_info("BTCUSDT")
    symbol = exchange_info["symbols"][0]

    print("Symbol:", symbol["symbol"])
    print("Status:", symbol["status"])

    ticker = client.get_book_ticker("BTCUSDT")

    print("Best Bid:", ticker["bidPrice"])
    print("Best Ask:", ticker["askPrice"])

    book = client.get_order_book("BTCUSDT", limit=5)

    print("Order Book Bids:", len(book["bids"]))
    print("Order Book Asks:", len(book["asks"]))

    print("Production Public API: PASS")


if __name__ == "__main__":
    main()