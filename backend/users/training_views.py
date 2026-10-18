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
    TrainingNote, TrainingAuditEvent, Trade, Holding,
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
        user = account.user
        profile_before = {"name": user.name, "username": user.username, "email": user.email}
        profile_changes = {}
        for incoming, field in (("name", "name"), ("username", "username"), ("email", "email")):
            if incoming not in data:
                continue
            value = str(data[incoming]).strip().lower() if incoming in ("username", "email") else str(data[incoming]).strip()
            if not value:
                return Response({"error": f"{incoming} cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
            if field == "username" and (len(value) < 3 or len(value) > 30 or not all(c.islower() or c.isdigit() or c == "-" for c in value) or value.startswith("-") or value.endswith("-")):
                return Response({"error": "Username must be 3-30 lowercase letters, numbers or hyphens, and cannot start/end with a hyphen."}, status=status.HTTP_400_BAD_REQUEST)
            if UserProfile.objects.filter(**{field: value}).exclude(pk=user.pk).exists():
                return Response({"error": f"{incoming.capitalize()} is already in use."}, status=status.HTTP_400_BAD_REQUEST)
            if getattr(user, field) != value:
                setattr(user, field, value)
                profile_changes[field] = value
        if "password" in data and str(data.get("password", "")):
            new_password = str(data["password"])
            if len(new_password) < 12:
                return Response({"error": "Password must be at least 12 characters."}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(new_password)
            profile_changes["password"] = "reset"
        if profile_changes:
            user.save()
            TrainingAuditEvent.objects.create(actor=actor, account=account, action="TRAINEE_PROFILE_UPDATED",
                reason=str(data.get("reason", "Manager corrected trainee registration details."))[:5000],
                details={"before": profile_before, "changed": profile_changes})
        if "demoBalance" in data:
            try:
                new_balance = Decimal(str(data["demoBalance"]))
            except (InvalidOperation, ValueError, TypeError):
                return Response({"error": "demoBalance must be a valid number."}, status=status.HTTP_400_BAD_REQUEST)
            if not new_balance.is_finite() or new_balance < 0:
                return Response({"error": "demoBalance must be a finite non-negative number."}, status=status.HTTP_400_BAD_REQUEST)
            new_balance = new_balance.quantize(Decimal("0.01"))
            old_balance = user.buying_power
            user.buying_power = new_balance
            user.save(update_fields=["buying_power", "updated_at"])
            from .models import ForexDemoWallet
            wallet, _ = ForexDemoWallet.objects.get_or_create(account=account, defaults={"balance": user.initial_balance})
            old_forex_balance = wallet.balance
            wallet.balance = new_balance
            wallet.save(update_fields=["balance", "updated_at"])
            TrainingAuditEvent.objects.create(actor=actor, account=account, action="VIRTUAL_BALANCE_ADJUSTED",
                reason=str(data.get("reason", "Trainer adjusted virtual demo balance."))[:5000],
                details={"paper_balance_before": str(old_balance), "paper_balance_after": str(new_balance),
                         "forex_wallet_before": str(old_forex_balance), "forex_wallet_after": str(new_balance),
                         "virtual_only": True})
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



class TrainingAccountTradesView(APIView):
    """Manager view of one training account's current positions and trade history."""

    def get(self, request, account_id):
        _manager(request)
        account = get_object_or_404(TrainingAccount.objects.select_related("user"), pk=account_id)
        holdings = Holding.objects.filter(user=account.user).order_by("symbol")
        trades = Trade.objects.filter(user=account.user).order_by("-executed_at")[:200]
        return Response({
            "account": _account_payload(account),
            "positions": [holding.to_dict() for holding in holdings],
            "trades": [trade.to_dict() for trade in trades],
        })


class ManagerDemoTradeView(APIView):
    """Place an explicitly manager-attributed BUY/SELL in the virtual paper ledger."""

    @transaction.atomic
    def post(self, request, account_id):
        actor = _manager(request)
        account = get_object_or_404(TrainingAccount.objects.select_related("user"), pk=account_id)
        if not account.is_enabled:
            return Response({"error": "This training account is disabled."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        symbol = str(data.get("symbol", "")).strip().upper()
        name = str(data.get("name", symbol)).strip()[:200]
        side = str(data.get("side", "")).strip().upper()
        reason = str(data.get("reason", "")).strip()
        try:
            quantity = Decimal(str(data.get("quantity", "0")))
            price = Decimal(str(data.get("price", "0")))
        except (InvalidOperation, ValueError, TypeError):
            return Response({"error": "Quantity and price must be valid numbers."}, status=status.HTTP_400_BAD_REQUEST)

        if not symbol or side not in ("BUY", "SELL") or quantity <= 0 or price <= 0:
            return Response({"error": "Provide symbol, BUY/SELL side, positive quantity and positive demo price."}, status=status.HTTP_400_BAD_REQUEST)
        if not reason:
            return Response({"error": "A reason is required for every manager-assisted trade."}, status=status.HTTP_400_BAD_REQUEST)
        if len(symbol) > 20:
            return Response({"error": "Symbol is too long."}, status=status.HTTP_400_BAD_REQUEST)

        config, _ = TrainerTradingConfig.objects.get_or_create(account=account)
        if config.allowed_symbols and symbol not in config.allowed_symbols:
            return Response({"error": "This symbol is not allowed for this training account."}, status=status.HTTP_400_BAD_REQUEST)
        if quantity > config.max_position_size:
            return Response({"error": f"Quantity exceeds this account's maximum position size ({config.max_position_size})."}, status=status.HTTP_400_BAD_REQUEST)

        user = account.user
        total = quantity * price
        if side == "BUY":
            if total > user.buying_power:
                return Response({"error": "Insufficient demo balance."}, status=status.HTTP_400_BAD_REQUEST)
            user.buying_power -= total
            user.save(update_fields=["buying_power", "updated_at"])
            holding, created = Holding.objects.get_or_create(
                user=user, symbol=symbol,
                defaults={"name": name, "shares": Decimal("0"), "avg_cost": Decimal("0"), "currency": "USD"},
            )
            previous_quantity = holding.shares
            new_quantity = previous_quantity + quantity
            holding.avg_cost = ((previous_quantity * holding.avg_cost) + total) / new_quantity
            holding.shares = new_quantity
            holding.name = name
            holding.save()
        else:
            try:
                holding = Holding.objects.get(user=user, symbol=symbol)
            except Holding.DoesNotExist:
                return Response({"error": f"No demo position exists for {symbol}."}, status=status.HTTP_400_BAD_REQUEST)
            if quantity > holding.shares:
                return Response({"error": "SELL quantity exceeds the available demo position."}, status=status.HTTP_400_BAD_REQUEST)
            user.buying_power += total
            user.save(update_fields=["buying_power", "updated_at"])
            holding.shares -= quantity
            if holding.shares == 0:
                holding.delete()
            else:
                holding.save()

        trade = Trade.objects.create(
            user=user, symbol=symbol, name=name, trade_type=side,
            shares=quantity, price=price, total=total, currency="USD",
        )
        TrainingAuditEvent.objects.create(
            actor=actor, account=account, action="MANAGER_DEMO_TRADE",
            reason=reason[:5000],
            details={
                "trade_id": str(trade.id), "symbol": symbol, "side": side,
                "quantity": str(quantity), "price": str(price), "total": str(total),
                "leverage_setting": config.leverage,
                "note": "Manager-assisted simulated paper trade; no live broker order was sent.",
            },
        )
        return Response({
            "message": "Manager-assisted demo trade recorded.",
            "trade": trade.to_dict(),
            "demoBalance": str(user.buying_power),
            "actor": actor.username,
            "auditLogged": True,
        }, status=status.HTTP_201_CREATED)
