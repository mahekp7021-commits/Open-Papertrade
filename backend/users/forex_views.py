"""Forex classroom engine: simulated USD-quoted FX pairs, no broker connection."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    TrainingAccount, TrainerTradingConfig, TrainingAuditEvent,
    ForexDemoWallet, ForexPosition, ForexTrade,
)
from .views import get_user

CENT = Decimal("0.01")
STANDARD_LOT_UNITS = Decimal("100000")


def _manager(request):
    actor = get_user(request)
    if not actor or not actor.is_admin:
        raise PermissionDenied("Manager access required.")
    return actor


def _decimal(value, label):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{label} must be a valid number.")
    if not result.is_finite():
        raise ValueError(f"{label} must be a finite number.")
    return result


def _wallet(account):
    wallet, _ = ForexDemoWallet.objects.get_or_create(
        account=account,
        defaults={"balance": account.user.initial_balance},
    )
    return wallet


def _pip_size(symbol):
    return Decimal("0.01") if symbol.endswith("JPY") else Decimal("0.0001")


def _pnl(position, mid_price, spread_pips):
    half_spread = (_pip_size(position.symbol) * spread_pips) / Decimal("2")
    exit_price = mid_price - half_spread if position.side == "BUY" else mid_price + half_spread
    direction = Decimal("1") if position.side == "BUY" else Decimal("-1")
    value = (exit_price - position.entry_price) * position.lots * STANDARD_LOT_UNITS * direction
    return value.quantize(CENT, rounding=ROUND_HALF_UP), exit_price


def _snapshot(account, quotes):
    """Quotes are explicitly supplied demo mid-prices, not a live market feed."""
    wallet = _wallet(account)
    config, _ = TrainerTradingConfig.objects.get_or_create(account=account)
    positions = list(ForexPosition.objects.filter(account=account, status="OPEN"))
    rows = []
    unrealized = Decimal("0.00")
    used_margin = sum((p.margin_used for p in positions), Decimal("0.00"))
    for position in positions:
        raw = quotes.get(position.symbol)
        if raw is None:
            pnl = None
            exit_price = None
        else:
            mid = _decimal(raw, f"Quote for {position.symbol}")
            if mid <= 0:
                raise ValueError(f"Quote for {position.symbol} must be positive.")
            pnl, exit_price = _pnl(position, mid, position.spread_pips_at_open)
            unrealized += pnl
        rows.append({
            "id": position.id, "symbol": position.symbol, "side": position.side,
            "lots": str(position.lots), "entryPrice": str(position.entry_price),
            "midPrice": str(raw) if raw is not None else None,
            "estimatedExitPrice": str(exit_price) if exit_price is not None else None,
            "unrealizedPnl": str(pnl) if pnl is not None else None,
            "marginUsed": str(position.margin_used), "leverageAtOpen": position.leverage_at_open,
            "openedAt": position.opened_at.isoformat(),
        })
    equity = (wallet.balance + unrealized).quantize(CENT, rounding=ROUND_HALF_UP)
    free_margin = (equity - used_margin).quantize(CENT, rounding=ROUND_HALF_UP)
    margin_level = (equity / used_margin * Decimal("100")) if used_margin > 0 else None
    return {
        "accountId": account.id, "currency": "USD",
        "balance": str(wallet.balance), "unrealizedPnl": str(unrealized),
        "equity": str(equity), "usedMargin": str(used_margin),
        "freeMargin": str(free_margin),
        "marginLevelPercent": str(margin_level.quantize(Decimal("0.01"))) if margin_level is not None else None,
        "marginCallLevelPercent": str(config.margin_call_level_percent),
        "stopOutLevelPercent": str(config.stop_out_level_percent),
        "positions": rows,
    }


class ForexAccountSnapshotView(APIView):
    """Manager snapshot endpoint; quote values are caller-supplied demo mid-prices."""

    def post(self, request, account_id):
        _manager(request)
        account = get_object_or_404(TrainingAccount.objects.select_related("user"), pk=account_id)
        quotes = request.data.get("quotes", {})
        if not isinstance(quotes, dict):
            return Response({"error": "quotes must be an object of symbol to mid-price."}, status=400)
        try:
            snapshot = _snapshot(account, quotes)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        level = Decimal(snapshot["marginLevelPercent"]) if snapshot["marginLevelPercent"] is not None else None
        config, _ = TrainerTradingConfig.objects.get_or_create(account=account)
        warning = "NORMAL"
        if level is not None and level <= config.stop_out_level_percent:
            warning = "STOP_OUT_THRESHOLD_REACHED"
            open_positions = list(ForexPosition.objects.filter(account=account, status="OPEN"))
            # Liquidate only when a quote is supplied for every open position.
            if open_positions and all(p.symbol in quotes for p in open_positions):
                actor = _manager(request)
                wallet = _wallet(account)
                for position in open_positions:
                    mid = _decimal(quotes[position.symbol], f"Quote for {position.symbol}")
                    pnl, exit_price = _pnl(position, mid, position.spread_pips_at_open)
                    wallet.balance = (wallet.balance + pnl).quantize(CENT, rounding=ROUND_HALF_UP)
                    position.status = "CLOSED"
                    position.close_price = exit_price
                    position.realized_pnl = pnl
                    position.closed_by = actor
                    position.close_reason = "Automatic simulated stop-out: configured threshold reached."
                    position.closed_at = timezone.now()
                    position.save(update_fields=["status", "close_price", "realized_pnl", "closed_by", "close_reason", "closed_at"])
                    ForexTrade.objects.create(account=account, position=position, actor=actor, event_type="STOP_OUT", symbol=position.symbol, side=position.side, lots=position.lots, price=exit_price, pnl=pnl, margin_used=position.margin_used, reason=position.close_reason, details={"midPrice": str(mid), "marginLevelPercent": str(level)})
                    TrainingAuditEvent.objects.create(actor=actor, account=account, action="FOREX_DEMO_STOP_OUT", reason=position.close_reason, details={"position_id": position.id, "symbol": position.symbol, "realized_pnl": str(pnl), "no_live_order": True})
                wallet.save(update_fields=["balance", "updated_at"])
                snapshot = _snapshot(account, quotes)
        elif level is not None and level <= config.margin_call_level_percent:
            warning = "MARGIN_CALL"
        snapshot["riskStatus"] = warning
        snapshot["quoteDisclaimer"] = "Supplied demo mid-prices only; this endpoint does not fetch live quotes."
        return Response(snapshot)


class ForexOpenPositionView(APIView):
    """Open a leveraged demo FX position using a supplied mid-price."""

    @transaction.atomic
    def post(self, request, account_id):
        actor = _manager(request)
        account = get_object_or_404(TrainingAccount.objects.select_related("user"), pk=account_id)
        if not account.is_enabled:
            return Response({"error": "This training account is disabled."}, status=400)
        data = request.data
        symbol = str(data.get("symbol", "")).strip().upper()
        side = str(data.get("side", "")).strip().upper()
        reason = str(data.get("reason", "")).strip()
        try:
            lots = _decimal(data.get("lots", "0"), "lots")
            mid = _decimal(data.get("midPrice", "0"), "midPrice")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        # Keep the first engine's accounting exact: quote currency must be USD.
        if len(symbol) != 6 or not symbol.isalpha() or not symbol.endswith("USD"):
            return Response({"error": "Initial engine supports USD-quoted FX pairs only, e.g. EURUSD, GBPUSD, AUDUSD, NZDUSD."}, status=400)
        if side not in ("BUY", "SELL") or lots <= 0 or mid <= 0:
            return Response({"error": "Provide BUY/SELL, positive lots and positive midPrice."}, status=400)
        if not reason:
            return Response({"error": "A reason is required for audit."}, status=400)
        config, _ = TrainerTradingConfig.objects.get_or_create(account=account)
        if config.allowed_symbols and symbol not in config.allowed_symbols:
            return Response({"error": "This symbol is not allowed for this account."}, status=400)
        if lots > config.max_position_size:
            return Response({"error": f"Lots exceed account maximum ({config.max_position_size})."}, status=400)

        wallet = _wallet(account)
        quotes = data.get("quotes", {})
        if not isinstance(quotes, dict):
            return Response({"error": "quotes must be an object of symbol to mid-price."}, status=400)
        existing_symbols = set(ForexPosition.objects.filter(account=account, status="OPEN").values_list("symbol", flat=True))
        missing_quotes = sorted(existing_symbols.difference(quotes.keys()))
        if missing_quotes:
            return Response({"error": "Supply current demo mid-price quotes for all existing open positions.", "missingQuotes": missing_quotes}, status=400)
        try:
            current = _snapshot(account, quotes)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        equity = Decimal(current["equity"])
        used_margin = Decimal(current["usedMargin"])
        entry = mid + (_pip_size(symbol) * config.spread_pips / 2 if side == "BUY" else -_pip_size(symbol) * config.spread_pips / 2)
        notional = lots * STANDARD_LOT_UNITS * mid
        margin = (notional / Decimal(config.leverage)).quantize(CENT, rounding=ROUND_HALF_UP)
        free_margin = equity - used_margin
        if margin > free_margin:
            return Response({"error": "Insufficient free margin for this demo position.", "requiredMargin": str(margin), "freeMargin": str(free_margin)}, status=400)

        position = ForexPosition.objects.create(
            account=account, symbol=symbol, side=side, lots=lots,
            entry_price=entry, entry_mid_price=mid, margin_used=margin,
            leverage_at_open=config.leverage, spread_pips_at_open=config.spread_pips,
            opened_by=actor, open_reason=reason,
        )
        ForexTrade.objects.create(
            account=account, position=position, actor=actor, event_type="OPEN",
            symbol=symbol, side=side, lots=lots, price=entry, margin_used=margin,
            reason=reason, details={"midPrice": str(mid), "spreadPips": str(position.spread_pips_at_open), "leverage": config.leverage, "contractUnits": str(STANDARD_LOT_UNITS)},
        )
        TrainingAuditEvent.objects.create(
            actor=actor, account=account, action="FOREX_DEMO_OPEN", reason=reason,
            details={"position_id": position.id, "symbol": symbol, "side": side, "lots": str(lots), "entry_price": str(entry), "margin": str(margin), "leverage": config.leverage, "no_live_order": True},
        )
        return Response({"message": "Forex demo position opened.", "positionId": position.id, "symbol": symbol, "side": side, "lots": str(lots), "entryPrice": str(entry), "midPrice": str(mid), "marginUsed": str(margin), "leverage": config.leverage, "walletBalance": str(wallet.balance), "simulatedOnly": True}, status=status.HTTP_201_CREATED)


class ForexClosePositionView(APIView):
    """Close an open demo position at a supplied mid-price and realize P/L."""

    @transaction.atomic
    def post(self, request, account_id, position_id):
        actor = _manager(request)
        account = get_object_or_404(TrainingAccount.objects.select_related("user"), pk=account_id)
        position = get_object_or_404(ForexPosition, pk=position_id, account=account, status="OPEN")
        if not account.is_enabled:
            return Response({"error": "This training account is disabled."}, status=400)
        reason = str(request.data.get("reason", "")).strip()
        try:
            mid = _decimal(request.data.get("midPrice", "0"), "midPrice")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        if mid <= 0 or not reason:
            return Response({"error": "Positive midPrice and a close reason are required."}, status=400)
        config, _ = TrainerTradingConfig.objects.get_or_create(account=account)
        pnl, exit_price = _pnl(position, mid, config.spread_pips)
        wallet = _wallet(account)
        wallet.balance = (wallet.balance + pnl).quantize(CENT, rounding=ROUND_HALF_UP)
        wallet.save(update_fields=["balance", "updated_at"])
        position.status = "CLOSED"
        position.close_price = exit_price
        position.realized_pnl = pnl
        position.closed_by = actor
        position.close_reason = reason
        position.closed_at = timezone.now()
        position.save(update_fields=["status", "close_price", "realized_pnl", "closed_by", "close_reason", "closed_at"])
        ForexTrade.objects.create(
            account=account, position=position, actor=actor, event_type="CLOSE",
            symbol=position.symbol, side=position.side, lots=position.lots,
            price=exit_price, pnl=pnl, margin_used=position.margin_used,
            reason=reason, details={"midPrice": str(mid), "spreadPips": str(config.spread_pips)},
        )
        TrainingAuditEvent.objects.create(
            actor=actor, account=account, action="FOREX_DEMO_CLOSE", reason=reason,
            details={"position_id": position.id, "symbol": position.symbol, "exit_price": str(exit_price), "realized_pnl": str(pnl), "no_live_order": True},
        )
        return Response({"message": "Forex demo position closed.", "positionId": position.id, "exitPrice": str(exit_price), "realizedPnl": str(pnl), "walletBalance": str(wallet.balance), "simulatedOnly": True})


class ForexPositionListView(APIView):
    """Read the open positions and event history for one classroom account."""

    def get(self, request, account_id):
        _manager(request)
        account = get_object_or_404(TrainingAccount.objects.select_related("user"), pk=account_id)
        wallet = _wallet(account)
        positions = ForexPosition.objects.filter(account=account).order_by("-opened_at")[:200]
        events = ForexTrade.objects.filter(account=account).select_related("actor").order_by("-created_at")[:200]
        return Response({
            "walletBalance": str(wallet.balance),
            "positions": [{
                "id": p.id, "symbol": p.symbol, "side": p.side, "lots": str(p.lots),
                "entryPrice": str(p.entry_price), "marginUsed": str(p.margin_used),
                "leverage": p.leverage_at_open, "status": p.status,
                "realizedPnl": str(p.realized_pnl), "openReason": p.open_reason,
                "closeReason": p.close_reason, "openedAt": p.opened_at.isoformat(),
                "closedAt": p.closed_at.isoformat() if p.closed_at else None,
            } for p in positions],
            "events": [{
                "id": e.id, "eventType": e.event_type, "symbol": e.symbol, "side": e.side,
                "lots": str(e.lots), "price": str(e.price), "pnl": str(e.pnl),
                "marginUsed": str(e.margin_used), "reason": e.reason,
                "actor": e.actor.username if e.actor else None, "createdAt": e.created_at.isoformat(),
            } for e in events],
        })
