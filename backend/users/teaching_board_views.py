"""Editable manager-only teaching board cards; these never mutate wallet or trade ledger."""
from decimal import Decimal, InvalidOperation
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TrainingAccount, TeachingBoardTrade, TrainingAuditEvent
from .views import get_user


def _board_manager(request):
    actor = get_user(request)
    if not actor or not actor.is_admin:
        raise PermissionDenied("Manager access required.")
    return actor


def _serialize(card):
    return {
        "id": card.id, "accountId": card.account_id, "symbol": card.symbol,
        "side": card.side, "entryPrice": str(card.entry_price),
        "marginAmount": str(card.margin_amount), "leverage": card.leverage,
        "lots": str(card.lots), "status": card.status,
        "tradeTime": card.trade_time.isoformat(), "lessonTitle": card.lesson_title,
        "explanation": card.explanation, "createdAt": card.created_at.isoformat(),
        "updatedAt": card.updated_at.isoformat(),
    }


def _apply(card, data, creating=False):
    if creating or "symbol" in data:
        symbol = str(data.get("symbol", card.symbol if not creating else "")).strip().upper().replace("/", "").replace(" ", "")
        if not symbol.isalnum() or not 3 <= len(symbol) <= 12:
            raise ValueError("Symbol must be 3–12 letters/numbers, e.g. USDJPY, BTCUSD or USDBTC.")
        card.symbol = symbol
    if creating or "side" in data:
        side = str(data.get("side", "BUY")).upper()
        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL.")
        card.side = side
    if creating or "entryPrice" in data:
        try:
            price = Decimal(str(data.get("entryPrice", "1")))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Entry price must be numeric.")
        if not price.is_finite() or price <= 0:
            raise ValueError("Entry price must be a positive finite number.")
        card.entry_price = price
    if creating or "marginAmount" in data:
        try:
            margin = Decimal(str(data.get("marginAmount", "0")))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Margin must be numeric.")
        if not margin.is_finite() or margin < 0:
            raise ValueError("Margin must be zero or greater.")
        card.margin_amount = margin
    if creating or "leverage" in data:
        try:
            leverage = int(data.get("leverage", 100))
        except (ValueError, TypeError):
            raise ValueError("Leverage must be a positive whole number.")
        if leverage < 1 or leverage > 5000:
            raise ValueError("Leverage must be between 1 and 5000.")
        card.leverage = leverage
    if creating or "lots" in data:
        try:
            lots = Decimal(str(data.get("lots", "0.01")))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Lots must be numeric.")
        if not lots.is_finite() or lots <= 0:
            raise ValueError("Lots must be positive.")
        card.lots = lots
    if creating or "status" in data:
        state = str(data.get("status", "EXAMPLE")).upper()
        if state not in ("OPEN", "CLOSED", "EXAMPLE"):
            raise ValueError("Status must be OPEN, CLOSED or EXAMPLE.")
        card.status = state
    if creating or "tradeTime" in data:
        raw_time = data.get("tradeTime")
        parsed = parse_datetime(str(raw_time)) if raw_time else timezone.now()
        if parsed is None:
            raise ValueError("Trade date/time must be ISO format.")
        card.trade_time = timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed
    if creating or "lessonTitle" in data:
        card.lesson_title = str(data.get("lessonTitle", ""))[:160]
    if creating or "explanation" in data:
        card.explanation = str(data.get("explanation", ""))[:10000]


class TeachingBoardListCreateView(APIView):
    def get(self, request, account_id):
        _board_manager(request)
        account = get_object_or_404(TrainingAccount, pk=account_id)
        cards = TeachingBoardTrade.objects.filter(account=account)[:200]
        return Response({"cards": [_serialize(card) for card in cards]})

    def post(self, request, account_id):
        actor = _board_manager(request)
        account = get_object_or_404(TrainingAccount, pk=account_id)
        card = TeachingBoardTrade(account=account, created_by=actor)
        try:
            _apply(card, request.data, creating=True)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        card.save()
        TrainingAuditEvent.objects.create(
            actor=actor, account=account, action="TEACHING_CARD_CREATE",
            reason=card.lesson_title or "Created editable teaching-board card",
            details={"card_id": card.id, "symbol": card.symbol, "side": card.side, "teaching_only": True},
        )
        return Response(_serialize(card), status=201)


class TeachingBoardDetailView(APIView):
    def patch(self, request, account_id, card_id):
        actor = _board_manager(request)
        account = get_object_or_404(TrainingAccount, pk=account_id)
        card = get_object_or_404(TeachingBoardTrade, pk=card_id, account=account)
        before = _serialize(card)
        try:
            _apply(card, request.data)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        card.save()
        TrainingAuditEvent.objects.create(
            actor=actor, account=account, action="TEACHING_CARD_EDIT",
            reason=card.lesson_title or "Edited teaching-board card",
            details={"card_id": card.id, "before": before, "after": _serialize(card), "teaching_only": True},
        )
        return Response(_serialize(card))

    def delete(self, request, account_id, card_id):
        actor = _board_manager(request)
        account = get_object_or_404(TrainingAccount, pk=account_id)
        card = get_object_or_404(TeachingBoardTrade, pk=card_id, account=account)
        before = _serialize(card)
        card.delete()
        TrainingAuditEvent.objects.create(
            actor=actor, account=account, action="TEACHING_CARD_DELETE",
            reason="Deleted teaching-board card",
            details={"deleted_card": before, "teaching_only": True},
        )
        return Response(status=204)
