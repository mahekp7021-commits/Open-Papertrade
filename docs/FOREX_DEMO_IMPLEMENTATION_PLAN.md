# Forex Demo Training Platform — Implementation Plan

## Project goal

Extend this fork of Open Papertrade into a transparent, multi-user Forex demo-training platform for trainers and trainees. All balances and orders are simulated; the platform must not accept real-money deposits/withdrawals or place real broker trades.

## Current baseline

- Backend: Django + Django REST Framework.
- Frontend: Next.js App Router + TypeScript.
- Database: SQLite for development; PostgreSQL intended for production.
- Existing paper-trading functionality covers virtual portfolios, market/limit orders, holdings, transactions, and price alerts.
- The existing repository is primarily general paper trading. Forex-specific instruments, lot sizing, leverage, margin, and a complete Forex execution/accounting engine must not be assumed to exist until audited and implemented.

## Roles

- **Platform Manager/Admin:** manages trainers/trainees, account permissions, demo settings, and audit records.
- **Trainer/Trainee account:** logs into its own WebTrader and practices with virtual funds.
- Role and account ownership checks must be enforced on the backend, not just hidden in the UI.

## Planned features

### 1. Trainer account creation and access
- Manager creates a separate login username and temporary password for each trainer/trainee account.
- Require password change on first login; never display or store plaintext passwords.
- Manager can reset access, enable/disable an account, and view account status.
- Each account has its own isolated virtual balance, positions, orders, and history.

### 2. Trainer account support and teaching
- Manager can open a trainee's account view in a clearly marked supervised/support mode.
- Show account balance, equity, open positions, margin, orders, and history to authorized staff.
- Add a lesson/notes area to explain trading concepts, mistakes, risk, and suggested next steps.
- Record who added each note and when; the trainee can see the coaching notes.
- Provide educational explanations for position sizing, spread, leverage, margin, entry/exit timing, and risk management.

### 3. Supervised trading on behalf of a trainee
- Authorized Manager/Trainer can place a simulated BUY/SELL order for a selected trainee account.
- Before submission, show the selected account, instrument, side, size, estimated spread/margin, and reason.
- Clearly label it as a staff-assisted demo order.
- Record actor, account owner, order details, timestamp, and reason in an immutable audit log.
- Never submit real-money trades. Do not allow staff to impersonate a trainee without an audit trail.

### 4. Per-account trading configuration
- Set each account's virtual starting balance.
- Configure leverage, margin requirements, spread, allowed instruments, maximum position size, maximum open positions, and risk limits per account.
- Validate every setting and every order server-side.
- Explain the active account rules to the trainee in the WebTrader.
- Spread and price rules must be disclosed as demo configuration; do not secretly alter prices to force an outcome.

### 5. Trade review, correction, and coaching
- Manager can flag a trade as a learning example and attach an explanation: entry timing, exit timing, position size, spread cost, leverage, margin, Stop Loss/Take Profit, and risk/reward.
- Show trade timeline and the market data available at the time, when that data exists.
- Manager can suggest a correction or a hypothetical alternative trade for learning.
- If a demo position needs an administrative close or account correction, require a reason and create an audit event.
- Never silently rewrite past trades, fabricate a market price, or change historical P&L to mislead the trainee. Keep original events and record any adjustment separately.
- Add a review status such as Needs Review / Discussed / Learning Completed.

### 6. Demo account and audit management
- Manager-only account creation and account status controls.
- Configurable starting virtual balance and manager adjustments.
- Append-only audit records for balance adjustments, order actions, account changes, and administrative position closure, including actor, amount/details, reason, and timestamp.
- Reset flow must clearly state what will be reset and require confirmation; preserve an audit record.

### 7. Forex instruments and simulated execution
- Start with configurable demo instruments such as EURUSD, GBPUSD, USDJPY, XAUUSD, and BTCUSD, subject to a suitable data provider.
- Model position size/lot units, quote precision, bid/ask, spread, leverage, margin, equity, free margin, and unrealized/realized P&L explicitly.
- Support market orders first, then pending orders, Stop Loss, and Take Profit.
- Validate orders and update balances/positions atomically on the server.
- Display a clear DEMO / VIRTUAL FUNDS ONLY notice and show stale/unavailable market data honestly.

### 8. WebTrader
- Responsive desktop and mobile browser UI.
- Market Watch, chart area, order ticket, open positions, history, and account metrics.
- Mobile-friendly touch controls; desktop layout optimized for wider screens.
- Clearly show the current account's assigned leverage, margin rules, spread configuration, permissions, and any trading restrictions.
- Clearly distinguish provider quotes from simulated execution prices.

### 9. Verification and deployment readiness
- Add tests for authorization, account isolation, password handling, manager-assisted orders, audit logs, balance adjustments, order validation, margin calculations, and P&L.
- Review secrets, CORS, CSRF/authentication, rate limits, and production settings.
- Document deployment environment variables and database persistence requirements.

## Non-goals

- No real-money deposits or withdrawals.
- No live broker execution.
- No misleading representation that demo trades are real trades.
- No silent or deceptive alteration of trainee trades, historical prices, or results.
- No hardcoded fake live prices presented as real market data.

## Hosting note

A GitHub fork is source code, not hosting. A public deployment needs a frontend host, a backend host capable of running Django, and a persistent database. Free tiers can have sleeping services, quotas, or expiring databases; verify current terms before relying on them for user accounts.

## License

This fork is based on an AGPL-3.0 project. Review and comply with the applicable license requirements when modifying, hosting, or distributing the service.
