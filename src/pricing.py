"""
NRAIZES - Pricing Engine
Dynamic pricing with safety bounds and market intelligence.

This module provides a comprehensive pricing system that:
- Validates price changes against business rules
- Enforces minimum margin requirements
- Limits daily price swings
- Calculates channel-specific prices with marketplace multipliers
"""
import os
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime

from logger import get_business_logger

# Initialize logger
_logger = get_business_logger('pricing')


@dataclass
class PricingRule:
    """
    Defines a pricing rule with safety constraints.

    Attributes:
        min_margin_percent: Minimum margin percentage over cost (default: 20%)
        max_swing_percent: Maximum allowed daily price change (default: 15%)
        strategy: Pricing strategy - 'protect_margin' or 'aggressive'
    """
    min_margin_percent: float = 20.0
    max_swing_percent: float = 15.0
    strategy: str = 'protect_margin'


class SafetyGuard:
    """
    Ensures pricing changes don't violate business rules.

    This class validates price changes against configurable constraints:
    - Minimum margin over cost
    - Maximum daily price swing
    - Positive price requirement

    Example:
        >>> guard = SafetyGuard()
        >>> is_valid, msg, price = guard.validate_price_change(100, 130, 50)
        >>> print(is_valid)  # False - 30% swing exceeds 15% max
    """

    def __init__(self, rules: Optional[PricingRule] = None):
        """
        Initialize SafetyGuard with pricing rules.

        Args:
            rules: Optional PricingRule instance. Uses defaults if not provided.
        """
        self.rules = rules or PricingRule()
    
    def validate_price_change(
        self,
        current_price: float,
        new_price: float,
        cost: Optional[float] = None
    ) -> Tuple[bool, str, float]:
        """
        Validate a proposed price change against business rules.

        Checks:
        1. Price must be positive
        2. Price change must not exceed max swing percentage
        3. Price must maintain minimum margin over cost (if cost provided)

        Args:
            current_price: Current product price
            new_price: Proposed new price
            cost: Optional product cost for margin calculation

        Returns:
            Tuple of (is_valid, message, adjusted_price):
            - is_valid: True if change passes all rules
            - message: Description of validation result
            - adjusted_price: Safe price (original if valid, adjusted if not)
        """
        if new_price <= 0:
            return False, "Price must be positive", current_price
        
        # Check max swing
        if current_price > 0:
            change_percent = abs(new_price - current_price) / current_price * 100
            if change_percent > self.rules.max_swing_percent:
                # Limit the swing
                if new_price > current_price:
                    adjusted = current_price * (1 + self.rules.max_swing_percent / 100)
                else:
                    adjusted = current_price * (1 - self.rules.max_swing_percent / 100)
                return False, f"Price swing {change_percent:.1f}% exceeds max {self.rules.max_swing_percent}%", adjusted
        
        # Check minimum margin
        if cost and cost > 0:
            min_price = cost * (1 + self.rules.min_margin_percent / 100)
            if new_price < min_price:
                return False, f"Price R${new_price:.2f} below min margin. Min: R${min_price:.2f}", min_price
        
        return True, "OK", new_price
    
    def calculate_safe_price(
        self,
        current_price: float,
        target_price: float,
        cost: Optional[float] = None
    ) -> float:
        """
        Calculate the safest achievable price towards a target within constraints.

        This method attempts to move the price towards the target while
        respecting all safety rules. If the target violates rules, it
        returns the closest safe price.

        Args:
            current_price: Current product price
            target_price: Desired target price
            cost: Optional product cost for margin calculation

        Returns:
            Safe price (may be different from target if constraints apply)
        """
        is_valid, _, safe_price = self.validate_price_change(current_price, target_price, cost)
        return safe_price


class StoreMultiplier:
    """
    Manages price multipliers for different sales channels.

    Each marketplace has different fee structures, so prices need to be
    adjusted to maintain margins. This class handles channel-specific
    pricing with configurable multipliers.

    Default multipliers:
    - WooCommerce: 1.00 (base price)
    - Mercado Livre: 1.15 (+15% for ML fees)
    - Shopee: 1.12 (+12% for Shopee fees)
    - Amazon: 1.18 (+18% for Amazon fees)

    Example:
        >>> multiplier = StoreMultiplier()
        >>> price = multiplier.calculate_store_price(100.0, 'mercadolivre')
        >>> print(price)  # 115.0
    """

    DEFAULT_MULTIPLIERS = {
        'woocommerce': 1.00,
        'mercadolivre': 1.15,
        'shopee': 1.12,
        'amazon': 1.18,
        'instagram': 1.05,
        'whatsapp': 1.00,
    }

    def __init__(self, custom_multipliers: Optional[Dict[str, float]] = None):
        """
        Initialize StoreMultiplier with optional custom multipliers.

        Args:
            custom_multipliers: Optional dict of store_name -> multiplier.
                               Merges with and overrides defaults.
        """
        self.multipliers = {**self.DEFAULT_MULTIPLIERS}
        if custom_multipliers:
            self.multipliers.update(custom_multipliers)

    def get_multiplier(self, store_name: str) -> float:
        """
        Get the price multiplier for a store (case-insensitive).

        Args:
            store_name: Store/channel name (e.g., 'mercadolivre', 'ML')

        Returns:
            Multiplier value (1.0 if store not found)
        """
        store_lower = store_name.lower()

        for key, mult in self.multipliers.items():
            if key in store_lower or store_lower in key:
                return mult

        return 1.0

    def calculate_store_price(self, base_price: float, store_name: str) -> float:
        """
        Calculate the final price for a specific store/channel.

        Args:
            base_price: Base product price
            store_name: Store/channel name

        Returns:
            Adjusted price for the store (rounded to 2 decimal places)
        """
        multiplier = self.get_multiplier(store_name)
        return round(base_price * multiplier, 2)

    def calculate_all_prices(self, base_price: float) -> Dict[str, float]:
        """
        Calculate prices for all configured stores/channels.

        Args:
            base_price: Base product price

        Returns:
            Dict mapping store names to calculated prices
        """
        return {
            store: round(base_price * mult, 2)
            for store, mult in self.multipliers.items()
        }


class PricingEngine:
    """
    Main pricing engine combining all components.

    This is the primary interface for pricing operations. It combines:
    - SafetyGuard for validation
    - StoreMultiplier for channel-specific pricing
    - Database integration for configuration

    Example:
        >>> engine = PricingEngine(db=vault_db)
        >>> suggestion = engine.suggest_price(product)
        >>> print(f"Suggested: R${suggestion['suggested_price']}")
    """

    def __init__(self, db=None):
        """
        Initialize PricingEngine with optional database connection.

        Args:
            db: Optional VaultDB instance for configuration and history.
                If not provided, uses default pricing rules.
        """
        self.db = db
        self.guard = SafetyGuard()
        self.store_multiplier = StoreMultiplier()

        if db:
            self._load_config_from_db()

    def _load_config_from_db(self):
        """Load pricing configuration from database."""
        min_margin = self.db.get_config('MIN_MARGIN_PERCENT')
        max_swing = self.db.get_config('MAX_PRICE_SWING_PERCENT')
        strategy = self.db.get_config('PRICING_STRATEGY')

        self.guard.rules = PricingRule(
            min_margin_percent=float(min_margin) if min_margin else 20.0,
            max_swing_percent=float(max_swing) if max_swing else 15.0,
            strategy=strategy or 'protect_margin'
        )
    
    def suggest_price(self, 
                      product: Dict[str, Any],
                      competitor_price: float = None,
                      target_margin: float = None) -> Dict[str, Any]:
        """
        Suggest a new price for a product.
        
        Returns dict with:
        - suggested_price: The recommended price
        - reason: Why this price was chosen
        - is_safe: Whether it passes all safety checks
        - store_prices: Prices for each channel
        """
        current_price = product.get('preco', 0) or 0
        cost = product.get('preco_custo') or product.get('precoCusto', 0) or 0
        
        suggested_price = current_price
        reason = "No change needed"
        
        # Strategy: Aggressive - beat competitor
        if competitor_price and self.guard.rules.strategy == 'aggressive':
            suggested_price = competitor_price - 0.01  # Beat by 1 cent
            reason = f"Beat competitor price R${competitor_price:.2f}"
        
        # Strategy: Protect Margin - ensure minimum margin
        elif cost > 0:
            min_price = cost * (1 + self.guard.rules.min_margin_percent / 100)
            if current_price < min_price:
                suggested_price = min_price
                reason = f"Raised to meet {self.guard.rules.min_margin_percent}% margin"
            elif target_margin:
                suggested_price = cost * (1 + target_margin / 100)
                reason = f"Adjusted to {target_margin}% margin"
        
        # Apply safety validation
        is_safe, msg, safe_price = self.guard.validate_price_change(
            current_price, suggested_price, cost
        )
        
        if not is_safe:
            suggested_price = safe_price
            reason = f"Safety adjusted: {msg}"
        
        # Calculate store-specific prices
        store_prices = self.store_multiplier.calculate_all_prices(suggested_price)
        
        return {
            'current_price': current_price,
            'suggested_price': round(suggested_price, 2),
            'cost': cost,
            'margin_percent': round((suggested_price - cost) / cost * 100, 1) if cost > 0 else None,
            'reason': reason,
            'is_safe': is_safe,
            'store_prices': store_prices
        }
    
    def generate_repricing_report(self, products: List[Dict], 
                                   competitor_prices: Dict[int, float] = None) -> List[Dict]:
        """
        Generate a repricing report for multiple products.
        
        Args:
            products: List of product dicts
            competitor_prices: Optional dict mapping product_id to competitor price
        """
        competitor_prices = competitor_prices or {}
        report = []
        
        for product in products:
            product_id = product.get('id_bling') or product.get('id')
            competitor_price = competitor_prices.get(product_id)
            
            suggestion = self.suggest_price(product, competitor_price)
            
            report.append({
                'id': product_id,
                'nome': product.get('nome', ''),
                'codigo': product.get('codigo', ''),
                **suggestion
            })
        
        return report
    
    def apply_price_change(self, bling_client, product_id: int, 
                           new_price: float, reason: str = 'manual') -> bool:
        """
        Apply a price change to Bling and record in history.
        
        Returns True if successful.
        """
        # Get current product
        product = bling_client.get_produtos_id_produto(product_id)
        current_price = product.get('data', {}).get('preco', 0)
        cost = product.get('data', {}).get('precoCusto', 0)
        
        # Safety check
        is_safe, msg, safe_price = self.guard.validate_price_change(
            current_price, new_price, cost
        )
        
        if not is_safe:
            print(f"⚠️ Safety adjustment: {msg}")
            new_price = safe_price
        
        # Record in history
        if self.db:
            self.db.registrar_alteracao_preco(
                id_produto=product_id,
                preco_anterior=current_price,
                preco_novo=new_price,
                motivo=reason
            )
        
        # Apply to Bling
        try:
            bling_client.patch_produtos_id_produto(product_id, {'preco': new_price})
            print(f"✅ Price updated: R${current_price:.2f} → R${new_price:.2f}")
            return True
        except Exception as e:
            print(f"❌ Failed to update price: {e}")
            return False


if __name__ == "__main__":
    # Quick test
    engine = PricingEngine()
    
    test_product = {
        'id': 123,
        'nome': 'Mel Orgânico 500g',
        'preco': 45.90,
        'precoCusto': 25.00
    }
    
    suggestion = engine.suggest_price(test_product)
    
    print("Pricing Suggestion:")
    print(f"  Current: R${suggestion['current_price']:.2f}")
    print(f"  Suggested: R${suggestion['suggested_price']:.2f}")
    print(f"  Margin: {suggestion['margin_percent']}%")
    print(f"  Reason: {suggestion['reason']}")
    print(f"\nStore Prices:")
    for store, price in suggestion['store_prices'].items():
        print(f"  {store}: R${price:.2f}")
