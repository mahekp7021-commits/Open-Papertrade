# Forex Demo Training Platform — Implementation Plan

## Project goal

Extend this fork of Open Papertrade into a transparent, multi-user Forex demo-training platform. All orders and account funds are simulated; this project must not accept deposits, withdrawals, or place real trades.

## Current baseline

- Backend: Django + Django REST Framework.
- Frontend: Next.js App Router + TypeScript.
- Database: SQLite for development; PostgreSQL intended for production.
- Existing paper-trading functionality covers virtual portfolios, market/limit orders, holdings, transactions, and price alerts.
- The existing repository is primarily general paper trading. Forex-specific instruments, lot sizing, leverage, margin, and a complete Forex execution/accounting engine must not be assumed to exist until audited and implemented.

## Planned milestones

### 1. Audit and safe foundation
- Map the current account, trade, holding, settings, and admin models.
- Confirm existing authentication, permissions, and API behaviour.
- Preserve upstream functionality where practical.
- Keep all custom work in this fork and document each change.

### 2. Demo account management
- Manager-only demo-account creation and account status controls.
- Configurable starting virtual balance and manager adjustments.
- Append-only audit records for balance adjustments, including actor, amount, reason, and timestamp.
- Enforce permissions server-side; never trust frontend role checks alone.

### 3. Forex instruments and simulated execution
- Start with configurable demo instruments such as EURUSD, GBPUSD, USDJPY, XAUUSD, and BTCUSD, subject to a suitable data provider.
- Model position size/lot units, quote precision, spread, leverage, margin, equity, free margin, and unrealized/realized P&L explicitly.
- Support market orders first, then pending orders, stop loss, and take profit.
- Validate orders and update balances/positions atomically on the server.
- Display a clear DEMO / VIRTUAL FUNDS ONLY notice.

### 4. WebTrader
- Market Watch, chart area, order ticket, open positions, history, and account metrics.
- Show market-data freshness and errors honestly.
- Clearly distinguish provider quotes from simulated execution prices.

### 5. Verification and deployment readiness
- Add tests for authorization, balance adjustments, order validation, margin calculations, and P&L.
- Review secrets, CORS, CSRF/authentication, rate limits, and production settings.
- Document deployment environment variables and database persistence requirements.

## Non-goals

- No real-money deposits or withdrawals.
- No live broker execution.
- No misleading representation that demo trades are real trades.
- No hardcoded fake live prices presented as real market data.

## Hosting note

A GitHub fork is source code, not hosting. A public deployment needs a frontend host, a backend host capable of running Django, and a persistent database. Free tiers can have sleeping services, quotas, or expiring databases; verify current terms before relying on them for user accounts.

## License

This fork is based on an AGPL-3.0 project. Review and comply with the applicable license requirements when modifying, hosting, or distributing the service.
