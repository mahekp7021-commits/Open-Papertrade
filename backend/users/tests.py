from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from .forex_views import _decimal, _pnl
from .models import (
    ForexDemoWallet, ForexPosition, ForexTrade, TrainingAccount,
    TrainingAuditEvent, TrainerTradingConfig, TeachingBoardTrade, UserProfile,
)


class ForexDecimalHelperTests(SimpleTestCase):
    def test_decimal_accepts_valid_numeric_strings(self):
        self.assertEqual(_decimal("1.2345", "price"), Decimal("1.2345"))

    def test_decimal_rejects_invalid_and_non_finite_values(self):
        for value in ("not-a-number", "NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    _decimal(value, "price")


class ForexPnlHelperTests(SimpleTestCase):
    def test_buy_profit_accounts_for_half_spread(self):
        position = type("Position", (), {
            "symbol": "EURUSD", "side": "BUY",
            "entry_price": Decimal("1.10005"), "lots": Decimal("1.0000"),
        })()
        pnl, exit_price = _pnl(position, Decimal("1.10100"), Decimal("1.000"))
        self.assertEqual(exit_price, Decimal("1.10095"))
        self.assertEqual(pnl, Decimal("90.00"))

    def test_sell_profit_accounts_for_half_spread(self):
        position = type("Position", (), {
            "symbol": "EURUSD", "side": "SELL",
            "entry_price": Decimal("1.09995"), "lots": Decimal("1.0000"),
        })()
        pnl, exit_price = _pnl(position, Decimal("1.09900"), Decimal("1.000"))
        self.assertEqual(exit_price, Decimal("1.09905"))
        self.assertEqual(pnl, Decimal("90.00"))

    def test_jpy_pair_uses_jpy_pip_size(self):
        position = type("Position", (), {
            "symbol": "USDJPY", "side": "BUY",
            "entry_price": Decimal("150.005"), "lots": Decimal("1.0000"),
        })()
        pnl, exit_price = _pnl(position, Decimal("150.100"), Decimal("1.000"))
        self.assertEqual(exit_price, Decimal("150.095"))
        self.assertEqual(pnl, Decimal("9000.00"))


class ForexApiIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = UserProfile.objects.create(
            name="Demo Manager", username="demo-manager", email="manager@example.test",
            is_admin=True, initial_balance=Decimal("100000.00"),
            buying_power=Decimal("100000.00"),
        )
        self.trainee_user = UserProfile.objects.create(
            name="Demo Trainee", username="demo-trainee", email="trainee@example.test",
            is_admin=False, initial_balance=Decimal("100000.00"),
            buying_power=Decimal("100000.00"),
        )
        self.account = TrainingAccount.objects.create(
            user=self.trainee_user, created_by=self.manager, role="TRAINEE",
        )
        TrainerTradingConfig.objects.create(account=self.account, leverage=100, spread_pips=Decimal("1.000"))
        self.open_url = f"/api/users/training/accounts/{self.account.id}/forex/open/"
        self.positions_url = f"/api/users/training/accounts/{self.account.id}/forex/positions/"
        self.snapshot_url = f"/api/users/training/accounts/{self.account.id}/forex/snapshot/"

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_non_manager_cannot_open_demo_position(self):
        self.authenticate(self.trainee_user)
        response = self.client.post(self.open_url, {
            "symbol": "EURUSD", "side": "BUY", "lots": "0.01",
            "midPrice": "1.08500", "reason": "Integration test",
        }, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ForexPosition.objects.count(), 0)

    def test_open_close_updates_wallet_and_audit_history(self):
        self.authenticate(self.manager)
        opened = self.client.post(self.open_url, {
            "symbol": "EURUSD", "side": "BUY", "lots": "0.10",
            "midPrice": "1.08500", "reason": "Test opening a virtual position",
        }, format="json")
        self.assertEqual(opened.status_code, 201, opened.data)
        position_id = opened.data["positionId"]
        self.assertTrue(opened.data["simulatedOnly"])
        self.assertEqual(ForexTrade.objects.filter(event_type="OPEN").count(), 1)
        self.assertTrue(TrainingAuditEvent.objects.filter(action="FOREX_DEMO_OPEN").exists())

        close_url = f"/api/users/training/accounts/{self.account.id}/forex/positions/{position_id}/close/"
        closed = self.client.post(close_url, {
            "midPrice": "1.08600", "reason": "Test closing a virtual position",
        }, format="json")
        self.assertEqual(closed.status_code, 200, closed.data)
        position = ForexPosition.objects.get(pk=position_id)
        self.assertEqual(position.status, "CLOSED")
        self.assertEqual(ForexTrade.objects.filter(event_type="CLOSE").count(), 1)
        self.assertTrue(TrainingAuditEvent.objects.filter(action="FOREX_DEMO_CLOSE").exists())
        wallet = ForexDemoWallet.objects.get(account=self.account)
        self.assertEqual(wallet.balance, Decimal("100009.00"))

    def test_open_position_keeps_original_spread_after_account_config_changes(self):
        self.authenticate(self.manager)
        opened = self.client.post(self.open_url, {
            "symbol": "EURUSD", "side": "BUY", "lots": "0.10",
            "midPrice": "1.08500", "reason": "Spread-at-open consistency test",
        }, format="json")
        self.assertEqual(opened.status_code, 201, opened.data)

        config = TrainerTradingConfig.objects.get(account=self.account)
        config.spread_pips = Decimal("10.000")
        config.save(update_fields=["spread_pips", "updated_at"])

        close_url = f"/api/users/training/accounts/{self.account.id}/forex/positions/{opened.data['positionId']}/close/"
        closed = self.client.post(close_url, {
            "midPrice": "1.08500", "reason": "Close using original spread",
        }, format="json")
        self.assertEqual(closed.status_code, 200, closed.data)
        self.assertEqual(closed.data["realizedPnl"], "-1.00")
        trade = ForexTrade.objects.get(event_type="CLOSE")
        self.assertEqual(trade.details["spreadPips"], "1.000")

    def test_disabled_account_cannot_open_position(self):
        self.account.is_enabled = False
        self.account.save(update_fields=["is_enabled"])
        self.authenticate(self.manager)
        response = self.client.post(self.open_url, {
            "symbol": "EURUSD", "side": "BUY", "lots": "0.01",
            "midPrice": "1.08500", "reason": "Disabled account test",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("disabled", response.data["error"].lower())
        self.assertEqual(ForexPosition.objects.count(), 0)

    def test_rejects_unsupported_quote_currency_pair(self):
        self.authenticate(self.manager)
        response = self.client.post(self.open_url, {
            "symbol": "EURGBP", "side": "BUY", "lots": "0.01",
            "midPrice": "0.85000", "reason": "Unsupported pair test",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("USD-quoted", response.data["error"])
        self.assertEqual(ForexPosition.objects.count(), 0)

    def test_snapshot_triggers_simulated_stop_out_and_audit_event(self):
        self.authenticate(self.manager)
        opened = self.client.post(self.open_url, {
            "symbol": "EURUSD", "side": "BUY", "lots": "0.10",
            "midPrice": "1.08500", "reason": "Prepare stop-out test",
        }, format="json")
        self.assertEqual(opened.status_code, 201, opened.data)

        wallet = ForexDemoWallet.objects.get(account=self.account)
        wallet.balance = Decimal("40.00")
        wallet.save(update_fields=["balance", "updated_at"])
        response = self.client.post(self.snapshot_url, {
            "quotes": {"EURUSD": "1.08500"},
        }, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["riskStatus"], "STOP_OUT_THRESHOLD_REACHED")
        position = ForexPosition.objects.get(pk=opened.data["positionId"])
        self.assertEqual(position.status, "CLOSED")
        self.assertTrue(ForexTrade.objects.filter(
            position=position, event_type="STOP_OUT",
        ).exists())
        self.assertTrue(TrainingAuditEvent.objects.filter(
            account=self.account, action="FOREX_DEMO_STOP_OUT",
        ).exists())

    def test_snapshot_reports_margin_call_without_liquidating(self):
        self.authenticate(self.manager)
        opened = self.client.post(self.open_url, {
            "symbol": "EURUSD", "side": "BUY", "lots": "0.10",
            "midPrice": "1.08500", "reason": "Prepare margin-call test",
        }, format="json")
        self.assertEqual(opened.status_code, 201, opened.data)

        wallet = ForexDemoWallet.objects.get(account=self.account)
        wallet.balance = Decimal("150.00")
        wallet.save(update_fields=["balance", "updated_at"])
        config = TrainerTradingConfig.objects.get(account=self.account)
        config.margin_call_level_percent = Decimal("200.00")
        config.stop_out_level_percent = Decimal("50.00")
        config.save(update_fields=["margin_call_level_percent", "stop_out_level_percent", "updated_at"])

        response = self.client.post(self.snapshot_url, {
            "quotes": {"EURUSD": "1.08500"},
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["riskStatus"], "MARGIN_CALL")
        self.assertEqual(
            ForexPosition.objects.get(pk=opened.data["positionId"]).status, "OPEN",
        )

    def test_account_symbol_allowlist_is_enforced(self):
        config = TrainerTradingConfig.objects.get(account=self.account)
        config.allowed_symbols = ["GBPUSD"]
        config.save(update_fields=["allowed_symbols", "updated_at"])
        self.authenticate(self.manager)
        response = self.client.post(self.open_url, {
            "symbol": "EURUSD", "side": "BUY", "lots": "0.01",
            "midPrice": "1.08500", "reason": "Symbol allowlist test",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("not allowed", response.data["error"])
        self.assertEqual(ForexPosition.objects.count(), 0)

    def test_account_leverage_controls_required_margin(self):
        config = TrainerTradingConfig.objects.get(account=self.account)
        config.leverage = 50
        config.save(update_fields=["leverage", "updated_at"])
        self.authenticate(self.manager)
        response = self.client.post(self.open_url, {
            "symbol": "EURUSD", "side": "BUY", "lots": "0.10",
            "midPrice": "1.08500", "reason": "Leverage margin test",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["leverage"], 50)
        self.assertEqual(response.data["marginUsed"], "217.00")

    def test_snapshot_aggregates_margin_for_multiple_open_positions(self):
        self.authenticate(self.manager)
        first = self.client.post(self.open_url, {
            "symbol": "EURUSD", "side": "BUY", "lots": "0.10",
            "midPrice": "1.08500", "reason": "First aggregate margin position",
        }, format="json")
        self.assertEqual(first.status_code, 201, first.data)

        second = self.client.post(self.open_url, {
            "symbol": "GBPUSD", "side": "SELL", "lots": "0.10",
            "midPrice": "1.27000",
            "quotes": {"EURUSD": "1.08500"},
            "reason": "Second aggregate margin position",
        }, format="json")
        self.assertEqual(second.status_code, 201, second.data)

        response = self.client.post(self.snapshot_url, {
            "quotes": {"EURUSD": "1.08500", "GBPUSD": "1.27000"},
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["usedMargin"], "235.50")
        self.assertEqual(len(response.data["positions"]), 2)
        self.assertEqual(response.data["freeMargin"], "99762.50")

    def test_open_position_requires_quotes_for_existing_positions(self):
        self.authenticate(self.manager)
        first = self.client.post(self.open_url, {
            "symbol": "EURUSD", "side": "BUY", "lots": "0.10",
            "midPrice": "1.08500", "reason": "Create existing position",
        }, format="json")
        self.assertEqual(first.status_code, 201, first.data)

        second = self.client.post(self.open_url, {
            "symbol": "GBPUSD", "side": "SELL", "lots": "0.10",
            "midPrice": "1.27000", "reason": "Missing quote must reject",
        }, format="json")
        self.assertEqual(second.status_code, 400)
        self.assertIn("quotes for all existing", second.data["error"])
        self.assertEqual(ForexPosition.objects.filter(status="OPEN").count(), 1)

    def test_insufficient_margin_rejects_position(self):
        self.trainee_user.initial_balance = Decimal("1.00")
        self.trainee_user.buying_power = Decimal("1.00")
        self.trainee_user.save(update_fields=["initial_balance", "buying_power"])
        self.authenticate(self.manager)
        response = self.client.post(self.open_url, {
            "symbol": "EURUSD", "side": "BUY", "lots": "1.00",
            "midPrice": "1.08500", "reason": "Must fail due to margin",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Insufficient free margin", response.data["error"])
        self.assertEqual(ForexPosition.objects.count(), 0)



class TeachingBoardApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = UserProfile.objects.create(
            name="Board Manager", username="board-manager", email="board-manager@example.test",
            is_admin=True, initial_balance=Decimal("100000.00"), buying_power=Decimal("100000.00"),
        )
        self.trainee = UserProfile.objects.create(
            name="Board Trainee", username="board-trainee", email="board-trainee@example.test",
            is_admin=False, initial_balance=Decimal("100000.00"), buying_power=Decimal("100000.00"),
        )
        self.account = TrainingAccount.objects.create(user=self.trainee, created_by=self.manager, role="TRAINEE")
        self.list_url = f"/api/users/training/accounts/{self.account.id}/teaching-board/"

    def test_manager_can_create_and_edit_classroom_example_without_touching_wallet(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(self.list_url, {
            "symbol": "USD/JPY", "side": "BUY", "entryPrice": "150.25000",
            "marginAmount": "500", "leverage": 100, "lots": "0.10",
            "status": "EXAMPLE", "tradeTime": "2026-10-18T09:30:00Z",
            "lessonTitle": "JPY entry lesson", "explanation": "Demonstrate entry timing.",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        card_id = response.data["id"]
        card = TeachingBoardTrade.objects.get(pk=card_id)
        self.assertEqual(card.symbol, "USDJPY")
        self.assertFalse(ForexDemoWallet.objects.filter(account=self.account).exists())

        response = self.client.patch(f"{self.list_url}{card_id}/", {
            "symbol": "BTCUSD", "side": "SELL", "marginAmount": "750",
            "tradeTime": "2026-10-17T14:15:00Z",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        card.refresh_from_db()
        self.assertEqual(card.symbol, "BTCUSD")
        self.assertEqual(card.side, "SELL")
        self.assertEqual(card.margin_amount, Decimal("750"))
        self.assertEqual(card.trade_time.isoformat(), "2026-10-17T14:15:00+00:00")
        self.assertEqual(TrainingAuditEvent.objects.filter(account=self.account, action="TEACHING_CARD_CREATE").count(), 1)
        self.assertEqual(TrainingAuditEvent.objects.filter(account=self.account, action="TEACHING_CARD_EDIT").count(), 1)
        self.assertFalse(ForexDemoWallet.objects.filter(account=self.account).exists())

    def test_non_manager_cannot_access_teaching_board(self):
        self.client.force_authenticate(user=self.trainee)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 403)

    def test_teaching_board_rejects_invalid_side_and_negative_margin(self):
        self.client.force_authenticate(user=self.manager)
        for payload in (
            {"symbol": "USDJPY", "side": "HOLD", "entryPrice": "150", "marginAmount": "50", "leverage": 100, "lots": "0.1"},
            {"symbol": "USDJPY", "side": "BUY", "entryPrice": "150", "marginAmount": "-50", "leverage": 100, "lots": "0.1"},
        ):
            response = self.client.post(self.list_url, payload, format="json")
            self.assertEqual(response.status_code, 400)
        self.assertEqual(TeachingBoardTrade.objects.count(), 0)


class TrainerCorrectionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = UserProfile.objects.create(
            name="Correction Manager", username="correction-manager", email="correction-manager@example.test",
            is_admin=True, initial_balance=Decimal("100000.00"), buying_power=Decimal("100000.00"),
        )
        self.trainee = UserProfile.objects.create(
            name="Correction Trainee", username="correction-trainee", email="correction-trainee@example.test",
            is_admin=False, initial_balance=Decimal("100000.00"), buying_power=Decimal("100000.00"),
        )
        self.account = TrainingAccount.objects.create(user=self.trainee, created_by=self.manager, role="TRAINEE")
        TrainerTradingConfig.objects.create(account=self.account, leverage=100, spread_pips=Decimal("1.000"))
        self.client.force_authenticate(user=self.manager)
        self.account_url = f"/api/users/training/accounts/{self.account.id}/"
        self.open_url = f"/api/users/training/accounts/{self.account.id}/forex/open/"

    def test_manager_can_edit_profile_balance_and_leverage(self):
        response = self.client.patch(self.account_url, {
            "name": "Corrected Trainee", "username": "corrected-trainee",
            "email": "corrected-trainee@example.test", "demoBalance": "25000.50",
            "leverage": 200, "enabled": True, "reason": "Correct test profile",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.trainee.refresh_from_db()
        self.assertEqual(self.trainee.name, "Corrected Trainee")
        self.assertEqual(self.trainee.buying_power, Decimal("25000.50"))
        self.assertEqual(TrainerTradingConfig.objects.get(account=self.account).leverage, 200)
        self.assertEqual(ForexDemoWallet.objects.get(account=self.account).balance, Decimal("25000.50"))
        self.assertTrue(TrainingAuditEvent.objects.filter(account=self.account, action="VIRTUAL_BALANCE_ADJUSTED").exists())

    def test_invalid_account_patch_rolls_back_profile_change(self):
        response = self.client.patch(self.account_url, {
            "name": "Must Roll Back", "demoBalance": "not-a-balance",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.trainee.refresh_from_db()
        self.assertEqual(self.trainee.name, "Correction Trainee")

    def test_closed_trade_correction_reconciles_wallet_and_preserves_original_events(self):
        opened = self.client.post(self.open_url, {
            "symbol": "EURUSD", "side": "BUY", "lots": "0.10",
            "midPrice": "1.08500", "reason": "Open before correction",
        }, format="json")
        self.assertEqual(opened.status_code, 201, opened.data)
        position_id = opened.data["positionId"]
        close_url = f"/api/users/training/accounts/{self.account.id}/forex/positions/{position_id}/close/"
        closed = self.client.post(close_url, {
            "midPrice": "1.08600", "reason": "Close before correction",
        }, format="json")
        self.assertEqual(closed.status_code, 200, closed.data)
        original_wallet = ForexDemoWallet.objects.get(account=self.account).balance
        original_event_count = ForexTrade.objects.filter(position_id=position_id).count()
        edit_url = f"/api/users/training/accounts/{self.account.id}/forex/positions/{position_id}/edit/"
        corrected = self.client.patch(edit_url, {
            "entryMidPrice": "1.08400", "closeMidPrice": "1.08600",
            "reason": "Correct entry for training example",
        }, format="json")
        self.assertEqual(corrected.status_code, 200, corrected.data)
        position = ForexPosition.objects.get(pk=position_id)
        wallet = ForexDemoWallet.objects.get(account=self.account)
        self.assertEqual(position.realized_pnl, Decimal("19.00"))
        self.assertEqual(wallet.balance, original_wallet + Decimal("10.00"))
        from .training_views import _account_payload
        self.assertEqual(_account_payload(self.account)["demoBalance"], str(wallet.balance))
        self.assertEqual(ForexTrade.objects.filter(position_id=position_id).count(), original_event_count + 1)
        self.assertTrue(ForexTrade.objects.filter(position_id=position_id, event_type="CORRECTION").exists())
        self.assertTrue(TrainingAuditEvent.objects.filter(account=self.account, action="FOREX_DEMO_POSITION_CORRECTED").exists())


    def test_invalid_trading_config_rolls_back_profile_and_balance_changes(self):
        response = self.client.patch(self.account_url, {
            "name": "Must Not Persist", "demoBalance": "5000.00",
            "leverage": 200, "stopOutLevelPercent": 90, "marginCallLevelPercent": 50,
            "reason": "Deliberately invalid combined patch",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.trainee.refresh_from_db()
        self.assertEqual(self.trainee.name, "Correction Trainee")
        self.assertEqual(self.trainee.buying_power, Decimal("100000.00"))
        config = TrainerTradingConfig.objects.get(account=self.account)
        self.assertEqual(config.leverage, 100)
        self.assertFalse(ForexDemoWallet.objects.filter(account=self.account).exists())

    def test_non_manager_cannot_correct_a_trade(self):
        self.client.force_authenticate(user=self.trainee)
        response = self.client.patch(
            f"/api/users/training/accounts/{self.account.id}/forex/positions/999/edit/",
            {"reason": "Should be blocked"}, format="json",
        )
        self.assertEqual(response.status_code, 403)
