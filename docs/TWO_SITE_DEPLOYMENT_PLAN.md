# Two-Site Deployment Plan — Open Papertrade

## Goal
Publish two separate public frontends while keeping one authoritative Django API and one PostgreSQL database:

- Admin Panel: manager-only account and training controls.
- WebTrader: trainee login and virtual trading.
- Shared API/database: accounts, virtual balances, positions, orders, P/L, and audit events.

All trading is simulated and uses virtual funds only. No deposits, withdrawals, broker accounts, or live orders.

## Important architecture rule
The two websites must not maintain separate copies of trainee balances. Both must call the same Django API, and the API/database must be the source of truth. A trainee's public Demo Account ID is an identifier, not a password; require authenticated login and enforce role/account ownership server-side.

## Repository baseline
- Django + Django REST Framework backend: `backend/`
- Next.js frontend: `frontend-ui/`
- Existing Render starter: `render.yaml` (two services, but needs a PostgreSQL URL and actual hostnames)

## Deployment approach
1. Deploy the Django API and connect it to persistent PostgreSQL.
2. Deploy the frontend twice from `frontend-ui/`, with different site-mode environment variables or route entry points: admin-only for the manager and WebTrader for trainees. Both builds must use the same API URL.
3. Configure Django `ALLOWED_HOSTS`, CORS and CSRF trusted origins for the exact API and both frontend URLs. Configure secure authentication cookies or a reviewed token flow across the chosen domains.
4. Set secrets only in the hosting provider's environment-variable settings; never commit secrets or admin passwords.
5. Verify manager-only access, account creation, trainee login, per-account isolation, balance changes, demo trade open/close, P/L and audit history from separate browsers/devices.

## Free-hosting constraints
GitHub stores the source and can host static frontends with GitHub Pages, but it does not run Django or provide a shared production database. Static Next.js export is only suitable if the frontend does not require Next.js server features; review `next.config.ts` and routes before enabling export. A separate online API and persistent database are still required.

Provider free tiers can sleep, pause, expire, or have monthly runtime limits. Do not promise 24/7 uptime or permanent data retention until current provider terms and the deployed system have been verified. Never enable paid plans or enter payment details without the owner's explicit decision.

## Status
This file documents the intended deployment architecture only. It does not mean the two sites or backend have been deployed. Deployment remains blocked until a no-card hosting option is confirmed and the required provider-side setup is completed.
