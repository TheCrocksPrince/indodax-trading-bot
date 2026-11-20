
from app.clients.binance_client import BinanceClient


def main():
    client = BinanceClient()

    print("=== BINANCE PING ===")
    print(client.ping())

    print("\n=== BTCUSDT BOOK TICKER ===")
    ticker = client.get_book_ticker("BTCUSDT")
    print(ticker)

    print("\n=== BTCUSDT ORDER BOOK ===")
    order_book = client.get_order_book("BTCUSDT", limit=5)

    print("Last Update ID:", order_book["lastUpdateId"])
    print("Bids:", order_book["bids"])
    print("Asks:", order_book["asks"])


if __name__ == "__main__":
    main()

