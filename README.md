# Indodax Trading Bot

**Python-Based Trading Bot | Indodax Trade API v2 & Binance Spot API Integration**

A Python-based trading bot project designed to explore, implement, and evaluate cryptocurrency trading API integrations across Indodax and Binance.

The project covers market data retrieval, trading simulation, portfolio tracking, order management, and Telegram-based interaction. It also serves as a technical foundation for comparing exchange API capabilities and supporting internal API testing.

## 1. Project Overview

This project was developed to gain practical experience integrating trading APIs, understand exchange-specific order execution workflows, and identify opportunities for improving trading API usability.

The implementation focuses on three key milestones:

| Milestone | Objective | Status |
|---|---|---|
| 1 | Indodax Trade API v2 integration and trading bot implementation | Core modules implemented |
| 2 | Binance Spot API integration and comparative analysis | Integration implemented; comparison ongoing |
| 3 | Reusable trading bot integration for internal product testing | Exploration in progress |

## 2. Key Features

### Indodax Trade API v2

- Authenticated API communication
- Account information and balance retrieval
- Market ticker and order book retrieval
- Market spread and liquidity analysis
- LIMIT order preparation and validation
- Order status and open order retrieval
- CREATE and CANCEL order integration
- Order execution safety checks

### Binance Spot API

- Public and authenticated API integration
- Market data retrieval
- Exchange-specific order filter validation
- LIMIT order preparation
- Order submission and reconciliation components
- Production and testnet client implementations

### Paper Trading Engine

A simulation environment for testing trading workflows without submitting real orders.

Capabilities include:

- Simulated BUY and SELL orders
- Virtual balance management
- Insufficient balance validation
- Liquidity checks
- Persistent trading history using SQLite
- Portfolio reconstruction from executed paper trades

### Portfolio Tracking

- Asset holdings calculation
- Weighted average cost basis
- Realized profit and loss
- Unrealized profit and loss
- Trading fee consideration
- Portfolio market value estimation

### Telegram Bot Integration

Telegram provides a command-based interface for interacting with trading bot functionality.

Implemented workflows include:

- Trading order previews
- Order confirmation
- Pre-execution validation
- Live execution staging
- Explicit execution confirmation
- Execution status tracking

Live execution is controlled through additional authorization and safety checks.

## 3. System Architecture

The application uses a modular Python architecture separating API clients, trading services, authentication, configuration, and tests.

```text
indodax-trading-bot/
│
├── app/
│   ├── auth/
│   │   └── signer.py
│   │
│   ├── clients/
│   │   ├── indodax_client.py
│   │   ├── indodax_market_data.py
│   │   ├── binance_client.py
│   │   ├── binance_testnet_client.py
│   │   ├── binance_execution_client.py
│   │   ├── binance_execution_transport.py
│   │   ├── paper_trading.py
│   │   ├── paper_trade_store.py
│   │   └── portfolio_engine.py
│   │
│   ├── config/
│   │   └── settings.py
│   │
│   ├── models/
│   │
│   └── services/
│       ├── indodax_live_validation.py
│       ├── binance_order_filters.py
│       ├── binance_order_reconciliation.py
│       ├── dual_exchange_execution.py
│       ├── live_telegram_execution.py
│       ├── atomic_execution_journal.py
│       └── order_fingerprint.py
│
├── scripts/
├── tests/
├── reports/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

The architecture is designed to keep exchange-specific API handling separate from trading logic and execution authorization.

## 4. Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python 3.9 |
| Primary exchange | Indodax |
| Secondary exchange | Binance |
| Indodax integration | Trade API v2 |
| Binance integration | Spot REST API |
| HTTP client | HTTPX |
| Data persistence | SQLite |
| Bot interface | Telegram |
| Testing framework | pytest |
| Development environment | macOS |

## 5. Installation and Setup

### Prerequisites

- Python 3.9 or compatible environment
- Git
- Indodax API credentials
- Binance API credentials for authenticated operations
- Telegram bot token for Telegram integration

### Clone the Repository

```bash
git clone https://github.com/TheCrocksPrince/indodax-trading-bot.git
cd indodax-trading-bot
```

### Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Copy the environment template:

```bash
cp .env.example .env
```

Configure the required credentials and settings using the variable names provided in `.env.example`.

**Security:** Never commit real API keys, secret keys, Telegram bot tokens, or account credentials.

Keep live trading disabled by default.

## 6. Running the Application

### Retrieve Indodax Account Information

```bash
python -m scripts.get_account
```

This operation requires valid Indodax API credentials and an authorized source IP address.

### Run the Telegram Bot

```bash
python -m scripts.telegram_bot
```

The Telegram bot provides access to the implemented trading and order management workflows.

### Run Unit Tests

```bash
python -m pytest tests/unit -q
```

## 7. Testing and Validation

The project uses automated unit tests to validate trading logic, exchange integrations, and safety-related components.

The latest recorded local test run completed with:

**258 tests passed**

Test coverage areas include:

- Market data processing
- Order book analysis
- Paper trading operations
- Portfolio calculations
- Order validation
- Exchange API client behavior
- Execution authorization components

This result reflects the recorded unit test run and does not imply that all production trading workflows have passed end-to-end testing.

## 8. Trading Execution Safety

Trading execution requires additional controls because requests may affect real exchange balances.

The implementation includes components for:

- Dry-run order preparation
- Trading pair validation
- Order quantity and price validation
- Maximum order notional restrictions
- Available balance checks
- Explicit order confirmation
- Execution journaling
- Duplicate execution protection

Additional production validation is required before enabling live order execution.

In particular, API response verification, exchange-specific trading rules, balance revalidation, and uncertain execution reconciliation must be tested thoroughly.

## 9. Indodax vs. Binance API Comparison

One objective of the project is to identify functional and technical differences between the two exchange integrations.

The comparative analysis covers:

| Area | Evaluation Focus |
|---|---|
| Authentication | API key and request signing |
| Market data | Ticker and order book endpoints |
| Trading rules | Minimum order size, precision, and increments |
| Order management | CREATE, CANCEL, and order status |
| Error handling | API response formats and failure scenarios |
| Execution safety | Validation and reconciliation |
| Developer experience | Documentation and integration complexity |

A detailed feature-gap analysis remains part of the ongoing project work.

## 10. Current Development Status

**Implemented**

- Indodax Trade API v2 client
- Binance Spot API client
- Market data and order book analysis
- Paper trading engine
- Portfolio tracking
- SQLite persistence
- Telegram bot integration
- Order preparation and validation modules
- Initial production order execution components
- Automated unit testing

**In Progress**

- End-to-end production execution validation
- Indodax API access and IP whitelist verification
- Live CREATE/CANCEL response validation
- Execution reconciliation and failure handling
- Binance and Indodax feature-gap analysis
- Reusable integration for internal product testing

## 11. References

- [Indodax Official Trade API v2 Documentation](https://github.com/btcid/indodax-official-api-docs/blob/master/INDODAX-TradeAPI-2.md)
- [Binance Spot API Documentation](https://developers.binance.com/docs/binance-spot-api-docs/rest-api)
- [Python Documentation](https://docs.python.org/3.9/)

## 12. Disclaimer

This project is intended for technical exploration, API integration, testing, and product evaluation.

Production trading carries financial risk. Live order execution must remain disabled until all required validations, authorization controls, and end-to-end tests have been completed.

---

**Project:** Indodax Trading Bot  
**Focus:** Trading API Integration, Automation, and Product Evaluation  
**Language:** Python