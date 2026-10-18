# Demo Launch Readiness Checklist

This repository is an educational paper-trading platform. It must use virtual funds and simulated orders only. Do not connect a real brokerage account, accept deposits/withdrawals, or execute real orders.

## Current verification baseline

- Backend CI and GitHub Pages deployment passed for commit `b95cb6f650e0384b2a52a71594790c168a1895f4`.
- The passing checks confirm automated checks/builds, not that a hosted Django API is running or that login and trading work end-to-end in a browser.
- The frontend uses `NEXT_PUBLIC_API_URL` (default `/api`) for browser API requests. `next.config.ts` also defines a server-side rewrite to `BACKEND_URL` (default `http://localhost:8000`). These defaults are local-development defaults, not production hosting configuration.

## Required before sharing a live demo

- [ ] Deploy the Django backend to a host that runs Python/Django persistently.
- [ ] Configure a persistent production database (PostgreSQL recommended); do not rely on ephemeral SQLite for trainee accounts.
- [ ] Configure frontend API routing so browser requests reach the deployed backend; do not leave `localhost` in production.
- [ ] Configure Django allowed hosts, trusted origins, CORS/CSRF and secure cookie settings for the actual frontend/backend domains.
- [ ] Set secret keys and credentials through host environment variables; never commit secrets.
- [ ] Apply database migrations on the deployed backend.
- [ ] Create a manager account securely without committing or publicly documenting a password.
- [ ] Verify manager login, trainee account creation, profile edits, virtual balance/leverage changes, demo open/close, P&L, correction audit trail and account isolation.
- [ ] Confirm all UI labels clearly state DEMO / VIRTUAL FUNDS ONLY.
- [ ] Confirm no real-money payment, bank, broker login, or live order integration exists.
- [ ] Test desktop and mobile layouts in a real browser against the deployed backend.

## Release gate

Do not call the demo production-ready or share it as a working live WebTrader until the backend is reachable and the end-to-end checklist above passes. A successful GitHub Pages build alone is not sufficient.
