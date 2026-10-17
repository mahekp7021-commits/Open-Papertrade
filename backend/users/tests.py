from decimal import Decimal

from django.test import SimpleTestCase

from .forex_views import _decimal, _pnl


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
            "symbol": "EURUSD",
            "side": "BUY",
            "entry_price": Decimal("1.10005"),
            "lots": Decimal("1.0000"),
        })()
        pnl, exit_price = _pnl(position, Decimal("1.10100"), Decimal("1.000"))

        self.assertEqual(exit_price, Decimal("1.10095"))
        self.assertEqual(pnl, Decimal("90.00"))

    def test_sell_profit_accounts_for_half_spread(self):
        position = type("Position", (), {
            "symbol": "EURUSD",
            "side": "SELL",
            "entry_price": Decimal("1.09995"),
            "lots": Decimal("1.0000"),
        })()
        pnl, exit_price = _pnl(position, Decimal("1.09900"), Decimal("1.000"))

        self.assertEqual(exit_price, Decimal("1.09905"))
        self.assertEqual(pnl, Decimal("90.00"))

    def test_jpy_pair_uses_jpy_pip_size(self):
        position = type("Position", (), {
            "symbol": "USDJPY",
            "side": "BUY",
            "entry_price": Decimal("150.005"),
            "lots": Decimal("1.0000"),
        })()
        pnl, exit_price = _pnl(position, Decimal("150.100"), Decimal("1.000"))

        self.assertEqual(exit_price, Decimal("150.095"))
        self.assertEqual(pnl, Decimal("9000.00"))
