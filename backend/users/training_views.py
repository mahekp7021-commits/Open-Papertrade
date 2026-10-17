"""Manager-only API for virtual trading classroom accounts.

All trades and balances managed by these endpoints are simulated. This module
never connects to a live broker or accepts real-money deposits.
"""
import secrets
import string
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    UserProfile, UserSettings, TrainingAccount, TrainerTradingConfig,
    TrainingNote, TrainingAuditEvent,
)
from .views import get_user


def _manager(request):
    actor = get_user(request)
    if not actor.is_admin:
        raise PermissionDenied("Manager access required.")
    return actor


def _account_payload(account):
    user = account.user
    config, _ = TrainerTradingConfig.objects.get_or_create(account=account)
    return {
        "id": str(account.id),
        "userId": str(user.id),
        "name": user.name,
        "username": user.username,
        "email": user.email,
        "role": account.role,
        "enabled": account.is_enabled,
        "demoBalance": str(user.buying_power),
        "initialBalance": str(user.initial_balance),
        "leverage": config.leverage,
        "spreadPips": str(config.spread_pips),
        "marginCallLevelPercent": str(config.margin_call_level_percent),
        "stopOutLevelPercent": str(config.stop_out_level_percent),
        "maxPositionSize": str(config.max_position_size),
        "allowedSymbols": config.allowed_symbols,
        "createdAt": account.created_at.isoformat(),
    }


class TrainingAccountsView(APIView):
    """List classroom accounts or create a trainer/trainee login."""

    def get(self, request):
        _manager(request)
        accounts = TrainingAccount.objects.select_related("user", "created_by").order_by("user__name")
        return Response({"accounts": [_account_payload(a) for a in accounts]})

    @transaction.atomic
    def post(self, request):
        actor = _manager(request)
        data = request.data
        name = str(data.get("name", "")).strip()
        username = str(data.get("username", "")).strip().lower()
        email = str(data.get("email", "")).strip().lower()
        role = str(data.get("role", "TRAINEE")).upper()
        password = str(data.get("password", ""))

        if not name or not username or not email:
            return Response({"error": "Name, username and email are required."}, status=status.HTTP_400_BAD_REQUEST)
        if role not in ("TRAINER", "TRAINEE"):
            return Response({"error": "Role must be TRAINER or TRAINEE."}, status=status.HTTP_400_BAD_REQUEST)
        if len(username) < 3 or len(username) > 30 or not all(c.islower() or c.isdigit() or c == "-" for c in username) or username.startswith("-") or username.endswith("-"):
            return Response({"error": "Username must be 3-30 lowercase letters, numbers or hyphens, and cannot start/end with a hyphen."}, status=status.HTTP_400_BAD_REQUEST)
        if UserProfile.objects.filter(username=username).exists():
            return Response({"error": "Username is already taken."}, status=status.HTTP_400_BAD_REQUEST)
        if UserProfile.objects.filter(email=email).exists():
            return Response({"error": "Email is already registered."}, status=status.HTTP_400_BAD_REQUEST)

        if not password:
            alphabet = string.ascii_letters + string.digits + "!@#$%*-_"
            password = "".join(secrets.choice(alphabet) for _ in range(16))
        if len(password) < 12:
            return Response({"error": "Use a password of at least 12 characters, or leave it blank to generate one."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            balance = Decimal(str(data.get("demoBalance", "100000")))
            leverage = int(data.get("leverage", 100))
            spread = Decimal(str(data.get("spreadPips", "1.000")))
            max_size = Decimal(str(data.get("maxPositionSize", "10")))
            margin_call = Decimal(str(data.get("marginCallLevelPercent", "100")))
            stop_out = Decimal(str(data.get("stopOutLevelPercent", "50")))
        except (InvalidOperation, ValueError, TypeError):
            return Response({"error": "Invalid number in account settings."}, status=status.HTTP_400_BAD_REQUEST)

        if balance < 0 or not 1 <= leverage <= 2000 or spread < 0 or max_size <= 0 or margin_call <= 0 or stop_out < 0 or stop_out > margin_call:
            return Response({"error": "Settings out of range. Balance/spread cannot be negative, leverage must be 1-2000, size positive, and stop-out cannot exceed margin-call."}, status=status.HTTP_400_BAD_REQUEST)

        user = UserProfile(
            name=name, username=username, email=email,
            buying_power=balance, initial_balance=balance,
            is_email_verified=True, is_admin=False,
        )
        user.set_password(password)
        user.save()
        UserSettings.objects.get_or_create(user=user)
        account = TrainingAccount.objects.create(
            user=user, created_by=actor, role=role,
            is_enabled=bool(data.get("enabled", True)),
            notes=str(data.get("notes", ""))[:5000],
        )
        TrainerTradingConfig.objects.create(
            account=account, leverage=leverage, spread_pips=spread,
            margin_call_level_percent=margin_call,
            stop_out_level_percent=stop_out,
            max_position_size=max_size,
            allowed_symbols=data.get("allowedSymbols", []),
        )
        TrainingAuditEvent.objects.create(
            actor=actor, account=account, action="ACCOUNT_CREATED",
            reason="Manager created a virtual training account.",
            details={"role": role, "username": username, "initial_demo_balance": str(balance)},
        )
        return Response({
            "account": _account_payload(account),
            "temporaryPassword": password,
            "message": "Account created. Share the password securely and ask the user to change it after first login.",
        }, status=status.HTTP_201_CREATED)


class TrainingAccountDetailView(APIView):
    """Enable/disable a training account and update its demo configuration."""

    @transaction.atomic
    def patch(self, request, account_id):
        actor = _manager(request)
        account = get_object_or_404(TrainingAccount.objects.select_related("user"), pk=account_id)
        data = request.data
        if "enabled" in data:
            account.is_enabled = bool(data["enabled"])
            account.save(update_fields=["is_enabled", "updated_at"])
            TrainingAuditEvent.objects.create(
                actor=actor, account=account,
                action="ACCOUNT_ENABLED" if account.is_enabled else "ACCOUNT_DISABLED",
                reason=str(data.get("reason", "Manager changed account access."))[:5000],
                details={"enabled": account.is_enabled},
            )
        config, _ = TrainerTradingConfig.objects.get_or_create(account=account)
        fields = {
            "leverage": ("leverage", int, 1, 2000),
            "spreadPips": ("spread_pips", Decimal, 0, None),
            "marginCallLevelPercent": ("margin_call_level_percent", Decimal, 0.01, None),
            "stopOutLevelPercent": ("stop_out_level_percent", Decimal, 0, None),
            "maxPositionSize": ("max_position_size", Decimal, 0.0001, None),
        }
        changed = {}
        for incoming, (field, converter, minimum, maximum) in fields.items():
            if incoming not in data:
                continue
            try:
                value = converter(data[incoming])
            except (InvalidOperation, ValueError, TypeError):
                return Response({"error": f"Invalid value for {incoming}."}, status=status.HTTP_400_BAD_REQUEST)
            if value < minimum or (maximum is not None and value > maximum):
                return Response({"error": f"Value out of range for {incoming}."}, status=status.HTTP_400_BAD_REQUEST)
            setattr(config, field, value)
            changed[field] = str(value)
        if "allowedSymbols" in data:
            symbols = data["allowedSymbols"]
            if not isinstance(symbols, list) or any(not isinstance(s, str) or len(s) > 32 for s in symbols):
                return Response({"error": "allowedSymbols must be a list of short strings."}, status=status.HTTP_400_BAD_REQUEST)
            config.allowed_symbols = [s.strip().upper() for s in symbols if s.strip()]
            changed["allowed_symbols"] = config.allowed_symbols
        if config.stop_out_level_percent > config.margin_call_level_percent:
            return Response({"error": "Stop-out level cannot exceed margin-call level."}, status=status.HTTP_400_BAD_REQUEST)
        if changed:
            config.save()
            TrainingAuditEvent.objects.create(
                actor=actor, account=account, action="TRADING_CONFIG_UPDATED",
                reason=str(data.get("reason", "Manager updated simulated trading settings."))[:5000],
                details=changed,
            )
        return Response({"account": _account_payload(account)})


class TrainingNotesView(APIView):
    """Create/list coaching notes; notes never rewrite historical trades."""

    def get(self, request, account_id):
        _manager(request)
        account = get_object_or_404(TrainingAccount, pk=account_id)
        notes = account.coaching_notes.select_related("author", "trade")
        return Response({"notes": [{
            "id": note.id, "title": note.title, "body": note.body,
            "category": note.category, "author": note.author.name if note.author else None,
            "tradeId": str(note.trade_id) if note.trade_id else None,
            "createdAt": note.created_at.isoformat(),
        } for note in notes]})

    def post(self, request, account_id):
        actor = _manager(request)
        account = get_object_or_404(TrainingAccount, pk=account_id)
        data = request.data
        title = str(data.get("title", "")).strip()
        body = str(data.get("body", "")).strip()
        category = str(data.get("category", "REVIEW")).upper()
        if not title or not body:
            return Response({"error": "Title and coaching note are required."}, status=status.HTTP_400_BAD_REQUEST)
        if category not in ("REVIEW", "RISK", "TIMING", "GENERAL"):
            return Response({"error": "Invalid coaching category."}, status=status.HTTP_400_BAD_REQUEST)
        trade = None
        trade_id = data.get("tradeId")
        if trade_id:
            from .models import Trade
            trade = get_object_or_404(Trade, pk=trade_id, user=account.user)
        note = TrainingNote.objects.create(account=account, author=actor, trade=trade, title=title[:160], body=body, category=category)
        TrainingAuditEvent.objects.create(
            actor=actor, account=account, action="COACHING_NOTE_ADDED",
            reason="Manager added a coaching/review note.",
            details={"note_id": note.id, "trade_id": str(trade.id) if trade else None, "category": category},
        )
        return Response({"id": note.id, "title": note.title, "category": note.category}, status=status.HTTP_201_CREATED)
