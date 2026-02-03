"""
NRAIZES - Unit Tests for Pricing Module
Tests for SafetyGuard, StoreMultiplier, and PricingEngine classes.
"""

import os
import sys
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from pricing import PricingRule, SafetyGuard, StoreMultiplier, PricingEngine


class TestPricingRule(unittest.TestCase):
    """Tests for PricingRule dataclass."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        rule = PricingRule()
        self.assertEqual(rule.min_margin_percent, 20.0)
        self.assertEqual(rule.max_swing_percent, 15.0)
        self.assertEqual(rule.strategy, "protect_margin")

    def test_custom_values(self):
        """Test that custom values are applied correctly."""
        rule = PricingRule(
            min_margin_percent=25.0, max_swing_percent=10.0, strategy="aggressive"
        )
        self.assertEqual(rule.min_margin_percent, 25.0)
        self.assertEqual(rule.max_swing_percent, 10.0)
        self.assertEqual(rule.strategy, "aggressive")


class TestSafetyGuard(unittest.TestCase):
    """Tests for SafetyGuard pricing validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.guard = SafetyGuard()

    def test_validate_positive_price(self):
        """Test that zero or negative prices are rejected."""
        is_valid, msg, price = self.guard.validate_price_change(100, 0, 50)
        self.assertFalse(is_valid)
        self.assertIn("positive", msg.lower())

        is_valid, msg, price = self.guard.validate_price_change(100, -10, 50)
        self.assertFalse(is_valid)

    def test_validate_max_swing_increase(self):
        """Test that price increases are limited by max swing."""
        # Current: 100, Trying to set: 130 (+30%)
        # Max swing: 15%, so should be limited to 115
        is_valid, msg, adjusted = self.guard.validate_price_change(100, 130, 50)
        self.assertFalse(is_valid)
        self.assertIn("swing", msg.lower())
        self.assertAlmostEqual(adjusted, 115.0, places=2)  # 100 * 1.15

    def test_validate_max_swing_decrease(self):
        """Test that price decreases are limited by max swing."""
        # Current: 100, Trying to set: 70 (-30%)
        # Max swing: 15%, so should be limited to 85
        is_valid, msg, adjusted = self.guard.validate_price_change(100, 70, 50)
        self.assertFalse(is_valid)
        self.assertEqual(adjusted, 85.0)  # 100 * 0.85

    def test_validate_minimum_margin(self):
        """Test that minimum margin is enforced."""
        # Cost: 100, Min margin: 20%, so min price: 120
        # Trying to set: 110 (only 10% margin)
        is_valid, msg, adjusted = self.guard.validate_price_change(115, 110, 100)
        self.assertFalse(is_valid)
        self.assertIn("margin", msg.lower())
        self.assertEqual(adjusted, 120.0)  # 100 * 1.20

    def test_validate_valid_price_change(self):
        """Test that valid price changes pass."""
        # Current: 100, New: 108 (+8%), Cost: 50 (margin > 20%)
        is_valid, msg, adjusted = self.guard.validate_price_change(100, 108, 50)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "OK")
        self.assertEqual(adjusted, 108)

    def test_validate_no_current_price(self):
        """Test handling of zero current price."""
        is_valid, msg, adjusted = self.guard.validate_price_change(0, 100, 50)
        # Should not fail on swing check since current is 0
        self.assertTrue(is_valid)

    def test_validate_no_cost(self):
        """Test handling when cost is not provided."""
        is_valid, msg, adjusted = self.guard.validate_price_change(100, 105, None)
        self.assertTrue(is_valid)

        is_valid, msg, adjusted = self.guard.validate_price_change(100, 105, 0)
        self.assertTrue(is_valid)

    def test_calculate_safe_price(self):
        """Test calculate_safe_price method."""
        # Target is too high (30% swing), should return max allowed
        safe = self.guard.calculate_safe_price(100, 130, 50)
        self.assertAlmostEqual(safe, 115.0, places=2)

        # Valid target should be returned as-is
        safe = self.guard.calculate_safe_price(100, 110, 50)
        self.assertEqual(safe, 110.0)


class TestSafetyGuardCustomRules(unittest.TestCase):
    """Tests for SafetyGuard with custom rules."""

    def test_custom_min_margin(self):
        """Test with custom minimum margin."""
        rules = PricingRule(min_margin_percent=30.0)
        guard = SafetyGuard(rules)

        # Cost: 100, Min margin: 30%, so min price: 130
        is_valid, msg, adjusted = guard.validate_price_change(140, 120, 100)
        self.assertFalse(is_valid)
        self.assertEqual(adjusted, 130.0)

    def test_custom_max_swing(self):
        """Test with custom max swing."""
        rules = PricingRule(max_swing_percent=5.0)
        guard = SafetyGuard(rules)

        # Max swing: 5%, current: 100, trying: 110 (+10%)
        is_valid, msg, adjusted = guard.validate_price_change(100, 110, 50)
        self.assertFalse(is_valid)
        self.assertEqual(adjusted, 105.0)  # 100 * 1.05


class TestStoreMultiplier(unittest.TestCase):
    """Tests for StoreMultiplier channel pricing."""

    def setUp(self):
        """Set up test fixtures."""
        self.multiplier = StoreMultiplier()

    def test_default_multipliers(self):
        """Test default store multipliers."""
        self.assertEqual(self.multiplier.get_multiplier("woocommerce"), 1.00)
        self.assertEqual(self.multiplier.get_multiplier("mercadolivre"), 1.15)
        self.assertEqual(self.multiplier.get_multiplier("shopee"), 1.12)
        self.assertEqual(self.multiplier.get_multiplier("amazon"), 1.18)

    def test_case_insensitive_matching(self):
        """Test that store names are matched case-insensitively."""
        self.assertEqual(self.multiplier.get_multiplier("WooCommerce"), 1.00)
        self.assertEqual(self.multiplier.get_multiplier("MERCADOLIVRE"), 1.15)
        self.assertEqual(self.multiplier.get_multiplier("MercadoLivre"), 1.15)

    def test_partial_matching(self):
        """Test that partial store names work."""
        # 'mercado' should match 'mercadolivre'
        self.assertEqual(self.multiplier.get_multiplier("mercado"), 1.15)

    def test_unknown_store(self):
        """Test that unknown stores return 1.0 (no markup)."""
        self.assertEqual(self.multiplier.get_multiplier("unknownstore"), 1.0)
        self.assertEqual(self.multiplier.get_multiplier(""), 1.0)

    def test_calculate_store_price(self):
        """Test store price calculation."""
        base_price = 100.0
        self.assertEqual(
            self.multiplier.calculate_store_price(base_price, "woocommerce"), 100.0
        )
        self.assertEqual(
            self.multiplier.calculate_store_price(base_price, "mercadolivre"), 115.0
        )
        self.assertEqual(
            self.multiplier.calculate_store_price(base_price, "amazon"), 118.0
        )

    def test_calculate_all_prices(self):
        """Test calculation of all store prices."""
        base_price = 100.0
        all_prices = self.multiplier.calculate_all_prices(base_price)

        self.assertIn("woocommerce", all_prices)
        self.assertIn("mercadolivre", all_prices)
        self.assertEqual(all_prices["woocommerce"], 100.0)
        self.assertEqual(all_prices["mercadolivre"], 115.0)

    def test_custom_multipliers(self):
        """Test with custom multipliers."""
        custom = {"magazine_luiza": 1.20, "carrefour": 1.10}
        multiplier = StoreMultiplier(custom_multipliers=custom)

        self.assertEqual(multiplier.get_multiplier("magazine_luiza"), 1.20)
        self.assertEqual(multiplier.get_multiplier("carrefour"), 1.10)
        # Default should still work
        self.assertEqual(multiplier.get_multiplier("mercadolivre"), 1.15)


class TestPricingEngine(unittest.TestCase):
    """Tests for PricingEngine."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = PricingEngine(db=None)

    def test_suggest_price_no_change_needed(self):
        """Test suggestion when no change is needed."""
        product = {"nome": "Test Product", "preco": 100.0, "precoCusto": 50.0}
        result = self.engine.suggest_price(product)

        self.assertEqual(result["current_price"], 100.0)
        self.assertEqual(result["suggested_price"], 100.0)
        self.assertIn("reason", result)

    def test_suggest_price_below_margin(self):
        """Test suggestion when price is below minimum margin."""
        product = {
            "nome": "Test Product",
            "preco": 110.0,  # Only 10% margin
            "precoCusto": 100.0,
        }
        result = self.engine.suggest_price(product)

        # Should suggest raising to meet 20% margin = 120
        # But limited by max swing (15%), so max: 110 * 1.15 = 126.5
        self.assertEqual(result["suggested_price"], 120.0)
        self.assertIn("margin", result["reason"].lower())

    def test_suggest_price_with_competitor(self):
        """Test aggressive strategy with competitor price."""
        # Change strategy to aggressive
        self.engine.guard.rules.strategy = "aggressive"

        product = {"nome": "Test Product", "preco": 100.0, "precoCusto": 50.0}
        competitor_price = 95.0
        result = self.engine.suggest_price(product, competitor_price)

        # Aggressive: should try to beat competitor by 1 cent
        # But constrained by max swing (15%)
        self.assertLessEqual(result["suggested_price"], 100.0)

    def test_suggest_price_store_prices(self):
        """Test that store prices are calculated."""
        product = {"nome": "Test Product", "preco": 100.0, "precoCusto": 50.0}
        result = self.engine.suggest_price(product)

        self.assertIn("store_prices", result)
        self.assertIn("mercadolivre", result["store_prices"])
        self.assertEqual(result["store_prices"]["mercadolivre"], 115.0)

    def test_suggest_price_calculates_margin(self):
        """Test that margin percentage is calculated."""
        product = {"nome": "Test Product", "preco": 150.0, "precoCusto": 100.0}
        result = self.engine.suggest_price(product)

        # Margin: (150 - 100) / 100 = 50%
        self.assertEqual(result["margin_percent"], 50.0)

    def test_suggest_price_handles_missing_cost(self):
        """Test handling of missing cost data."""
        product = {
            "nome": "Test Product",
            "preco": 100.0,
            # No cost
        }
        result = self.engine.suggest_price(product)

        self.assertIsNone(result["margin_percent"])
        self.assertEqual(result["cost"], 0)

    def test_generate_repricing_report(self):
        """Test repricing report generation."""
        products = [
            {"id": 1, "nome": "Product 1", "preco": 100.0, "precoCusto": 50.0},
            {"id": 2, "nome": "Product 2", "preco": 200.0, "precoCusto": 100.0},
        ]
        report = self.engine.generate_repricing_report(products)

        self.assertEqual(len(report), 2)
        self.assertEqual(report[0]["id"], 1)
        self.assertEqual(report[1]["id"], 2)


class TestPricingIntegration(unittest.TestCase):
    """Integration tests for pricing workflow."""

    def test_full_pricing_workflow(self):
        """Test complete pricing workflow."""
        engine = PricingEngine(db=None)

        # Product with price below margin
        product = {
            "id": 123,
            "nome": "Mel Orgânico 500g",
            "preco": 55.0,  # 10% margin
            "precoCusto": 50.0,
        }

        # Get suggestion
        suggestion = engine.suggest_price(product)

        # Should suggest increasing price
        self.assertGreater(suggestion["suggested_price"], 55.0)
        self.assertLessEqual(
            suggestion["suggested_price"], 63.25
        )  # Max swing: 55 * 1.15

        # Verify margin would be at least 20% at suggested price
        new_margin = (suggestion["suggested_price"] - 50) / 50 * 100
        self.assertGreaterEqual(new_margin, 20.0)

    def test_pricing_respects_all_constraints(self):
        """Test that all pricing constraints are respected together."""
        engine = PricingEngine(db=None)

        # Product that needs both swing and margin constraints
        product = {
            "id": 456,
            "nome": "Test Product",
            "preco": 101.0,  # 1% margin
            "precoCusto": 100.0,
        }

        suggestion = engine.suggest_price(product)

        # Min margin would require: 120.0
        # Max swing allows: 101 * 1.15 = 116.15
        # Should be limited to 116.15
        self.assertEqual(suggestion["suggested_price"], 116.15)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_zero_price(self):
        """Test handling of zero price."""
        guard = SafetyGuard()
        is_valid, msg, adjusted = guard.validate_price_change(0, 100, 50)
        self.assertTrue(is_valid)

    def test_very_small_price(self):
        """Test handling of very small prices."""
        guard = SafetyGuard()
        is_valid, msg, adjusted = guard.validate_price_change(0.01, 0.02, 0.005)
        # Should work mathematically
        self.assertIsInstance(adjusted, float)

    def test_very_large_price(self):
        """Test handling of very large prices."""
        guard = SafetyGuard()
        is_valid, msg, adjusted = guard.validate_price_change(1000000, 1100000, 500000)
        self.assertIsInstance(adjusted, (int, float))

    def test_float_precision(self):
        """Test that float precision is handled correctly."""
        multiplier = StoreMultiplier()
        # Check rounding
        price = multiplier.calculate_store_price(99.99, "mercadolivre")
        self.assertEqual(price, 114.99)  # 99.99 * 1.15 = 114.9885 -> 114.99


if __name__ == "__main__":
    unittest.main(verbosity=2)
