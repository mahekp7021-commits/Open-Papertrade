# Forex Demo Engine — Milestone 1

This is an educational virtual-funds engine. It does not connect to a broker, submit real orders, or fetch live quotes.

## Included
- Separate forex wallet per training account, isolated from the legacy share-based paper ledger.
- Leverage-based initial margin, standard lot size of 100,000 units, and spread-adjusted simulated entry/exit prices.
- Floating P/L, equity, used margin, free margin and margin-level snapshots.
- Margin-call warning and audited simulated stop-out when the threshold is reached and current mid-price quotes are supplied for every open position.
- Manager identity and a required reason in trade history and audit events.
- Initial scope is USD-quoted FX pairs such as EURUSD, GBPUSD, AUDUSD and NZDUSD. Non-USD quote-currency conversion is not implemented.
- Prices are supplied by the caller as demo mid-prices; they are not verified or market-fed.

## Manager API routes
Routes are under `/api/users/` and require manager/admin authentication.
- `POST training/accounts/{account_id}/forex/snapshot/`
- `GET training/accounts/{account_id}/forex/positions/`
- `POST training/accounts/{account_id}/forex/open/`
- `POST training/accounts/{account_id}/forex/positions/{position_id}/close/`

## Open example
Send JSON to `POST /api/users/training/accounts/{account_id}/forex/open/`:

    {
      "symbol": "EURUSD",
      "side": "BUY",
      "lots": "0.10",
      "midPrice": "1.08500",
      "quotes": {},
      "reason": "Practice order after reviewing the setup"
    }

If the account already has open positions, include a current demo mid-price for every existing open symbol in `quotes`. This prevents free-margin checks from silently ignoring floating P/L.

## Snapshot example
Send `POST /api/users/training/accounts/{account_id}/forex/snapshot/`:

    {
      "quotes": {
        "EURUSD": "1.08620",
        "GBPUSD": "1.27100"
      }
    }

## Close example
Send `POST /api/users/training/accounts/{account_id}/forex/positions/{position_id}/close/`:

    {
      "midPrice": "1.08620",
      "reason": "Close for lesson review"
    }

## Calculation assumptions
- Standard lot = 100,000 base units.
- Required margin = lots × 100,000 × supplied mid-price ÷ leverage.
- BUY enters at mid + half spread and exits at mid − half spread; SELL does the reverse.
- USD-quoted pair P/L = price movement × lots × 100,000, adjusted for BUY/SELL direction.
- JPY pip size is 0.01; other supported pair pip size is 0.0001.

## Status and limitations
This milestone has been committed but has not been run against a Django environment/database here. Run migrations and automated checks before deployment. It is not a broker-grade Forex terminal. Streaming quotes, non-USD quote conversion, pending orders, stop-loss/take-profit, swaps/commission, partial closes, and the user-facing WebTrader UI remain future work.