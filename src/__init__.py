# Bling Optimizer Package
"""
Bling Optimizer - Sistema de otimização de produtos para e-commerce.

Módulos:
- bling_client: Cliente para API Bling v3
- database: Banco de dados SQLite local
- enrichment: Enriquecimento com IA (Gemini)
- pricing: Motor de precificação dinâmica
- optimizer: Interface de linha de comando
"""

import os as _os
import sys as _sys

# Ensure src/ is on sys.path so internal absolute imports work
# when this package is imported (e.g. `import src` or `from src import ...`).
_src_dir = _os.path.dirname(_os.path.abspath(__file__))
if _src_dir not in _sys.path:
    _sys.path.insert(0, _src_dir)

from .bling_client import BlingClient
from .database import VaultDB
from .enrichment import ProductEnricher
from .pricing import PricingEngine

__version__ = "1.0.0"
__all__ = ["BlingClient", "VaultDB", "ProductEnricher", "PricingEngine"]
