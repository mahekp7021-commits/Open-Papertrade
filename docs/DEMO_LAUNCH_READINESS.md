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

## Hosted backend deployment starter (Render)

A starter Render Blueprint is included at the repository root in `render.yaml`. It deploys only the Django API; it does not deploy the Next.js frontend or automatically provision a database.

1. In Render, create a Blueprint from this repository and review the service settings before deploying.
2. Set `DATABASE_URL` to a persistent PostgreSQL connection string (the Django settings require it when `DEBUG=False`). Keep the database credentials private.
3. Set `CORS_ALLOWED_ORIGINS` to the exact browser origin(s) that will serve the frontend, comma-separated, with no trailing slash. For a GitHub Pages project site, verify the actual published origin first; the path is not part of the origin.
4. Confirm `ALLOWED_HOSTS` matches the actual API hostname. If Render assigns a different service hostname, update it before relying on the deployment.
5. Deploy and check `/api/` on the API hostname. Then create the manager account through a secure server-side/admin process; never commit credentials.
6. Configure the frontend's browser API base URL to the deployed API origin plus `/api`. A GitHub Pages static export cannot run the Next.js server-side rewrite in `frontend-ui/next.config.ts`; the browser must call the API directly and the API must allow the frontend origin.
7. Test login, manager-only trainee account controls, virtual balance/leverage updates, simulated open/close, P/L, correction audit history and account isolation before sharing the demo.

**Important:** this blueprint is a deployment starting point, not proof of a live service. A successful build does not mean the API/database is deployed. Use virtual funds and simulated orders only; do not add payment, bank, broker-login or real-order integrations.
