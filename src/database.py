"""
NRAIZES - Database Schema
SQLite database for local caching, staging proposals, and price history.
Implements connection pooling for efficient database access.
"""

import sqlite3
import os
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any, Generator

from logger import get_logger

# Project paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "vault.db")

# Initialize logger
_logger = get_logger(__name__)


class ConnectionPool:
    """
    Simple thread-safe SQLite connection pool.
    Maintains one connection per thread for thread safety.
    """

    def __init__(self, db_path: str, max_connections: int = 5):
        """
        Initialize the connection pool.

        Args:
            db_path: Path to the SQLite database file
            max_connections: Maximum number of connections (per-thread)
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self._local = threading.local()
        self._lock = threading.Lock()

        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimized settings."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a connection for the current thread.
        Creates a new connection if one doesn't exist for this thread.

        Returns:
            SQLite connection object
        """
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = self._create_connection()
            _logger.debug(
                f"Created new database connection for thread {threading.current_thread().name}"
            )
        return self._local.connection

    def close_connection(self):
        """Close the connection for the current thread."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None
            _logger.debug(
                f"Closed database connection for thread {threading.current_thread().name}"
            )

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for database connections.
        Automatically handles commit/rollback on exceptions.

        Yields:
            SQLite connection object
        """
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            _logger.error(f"Database error, rolling back: {e}")
            raise


# Global connection pool instance
_pool: Optional[ConnectionPool] = None


def get_pool() -> ConnectionPool:
    """Get the global connection pool, creating it if necessary."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(DB_PATH)
    return _pool


def get_connection() -> sqlite3.Connection:
    """
    Get database connection from the pool.
    This is the primary way to get database connections.

    Returns:
        SQLite connection object
    """
    return get_pool().get_connection()


def init_database():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    # Produtos table - cached product data from Bling
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY,
            id_bling INTEGER UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            codigo TEXT,
            preco REAL,
            preco_custo REAL,
            descricao_curta TEXT,
            descricao_complementar TEXT,
            situacao TEXT DEFAULT 'A',
            tipo TEXT DEFAULT 'P',
            imagem_url TEXT,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Lojas table - stores/marketplaces linked to Bling
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lojas (
            id INTEGER PRIMARY KEY,
            id_bling INTEGER UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            tipo_integracao TEXT,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Produtos_Lojas table - product-store links with specific pricing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos_lojas (
            id INTEGER PRIMARY KEY,
            id_bling INTEGER UNIQUE NOT NULL,
            id_produto INTEGER NOT NULL,
            id_loja INTEGER NOT NULL,
            preco_loja REAL,
            multiplicador REAL DEFAULT 1.0,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_produto) REFERENCES produtos(id_bling),
            FOREIGN KEY (id_loja) REFERENCES lojas(id_bling)
        )
    """)

    # Propostas_IA table - AI-generated content proposals for review
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS propostas_ia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_produto INTEGER NOT NULL,
            tipo TEXT NOT NULL,  -- 'descricao_curta', 'descricao_complementar', 'seo', 'titulo_ml', 'descricao_curta_ml', 'descricao_ml', 'ficha_tecnica_ml'
            conteudo_original TEXT,
            conteudo_proposto TEXT NOT NULL,
            status TEXT DEFAULT 'pendente',  -- 'pendente', 'aprovado', 'rejeitado', 'aplicado'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            FOREIGN KEY (id_produto) REFERENCES produtos(id_bling)
        )
    """)

    # Historico_Precos table - price change history for auditing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_precos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_produto INTEGER NOT NULL,
            id_loja INTEGER,  -- NULL means base price
            preco_anterior REAL,
            preco_novo REAL NOT NULL,
            motivo TEXT,  -- 'ai_suggestion', 'market_adjustment', 'manual'
            alterado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aplicado INTEGER DEFAULT 0,  -- 0=pending, 1=applied to Bling
            FOREIGN KEY (id_produto) REFERENCES produtos(id_bling),
            FOREIGN KEY (id_loja) REFERENCES lojas(id_bling)
        )
    """)

    # Config table - application settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =========================================================================
    # PRICE MONITORING TABLES
    # =========================================================================

    # Regras de precificação por categoria/marca
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regras_preco (
            id INTEGER PRIMARY KEY,
            tipo TEXT NOT NULL,  -- 'categoria', 'marca', 'produto'
            referencia TEXT NOT NULL,  -- nome categoria/marca ou id_produto
            margem_minima REAL DEFAULT 20,
            margem_alvo REAL DEFAULT 35,
            permite_auto_ajuste INTEGER DEFAULT 1,
            premium_permitido REAL DEFAULT 15,  -- % acima mercado permitido
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Preços de concorrentes coletados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS precos_concorrentes (
            id INTEGER PRIMARY KEY,
            id_produto INTEGER NOT NULL,
            fonte TEXT NOT NULL,  -- 'mercado_livre', 'google', 'kaizen', etc
            preco REAL NOT NULL,
            url TEXT,
            vendedor TEXT,
            disponivel INTEGER DEFAULT 1,
            coletado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_produto) REFERENCES produtos(id_bling)
        )
    """)

    # Alertas de preço gerados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alertas_preco (
            id INTEGER PRIMARY KEY,
            id_produto INTEGER NOT NULL,
            tipo TEXT NOT NULL,  -- 'acima_mercado', 'abaixo_mercado', 'margem_baixa', 'oportunidade'
            mensagem TEXT,
            preco_atual REAL,
            preco_mercado REAL,
            diferenca_percent REAL,
            acao_sugerida TEXT,
            status TEXT DEFAULT 'pendente',  -- 'pendente', 'aplicado', 'ignorado'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolvido_em TIMESTAMP,
            FOREIGN KEY (id_produto) REFERENCES produtos(id_bling)
        )
    """)

    # Histórico de ajustes aplicados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_ajustes (
            id INTEGER PRIMARY KEY,
            id_produto INTEGER NOT NULL,
            preco_anterior REAL,
            preco_novo REAL,
            motivo TEXT,
            fonte_referencia TEXT,  -- 'mercado_livre', 'google', 'manual'
            aplicado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aplicado_por TEXT DEFAULT 'sistema',
            FOREIGN KEY (id_produto) REFERENCES produtos(id_bling)
        )
    """)

    # =========================================================================
    # STRATEGIC DASHBOARD TABLES
    # =========================================================================

    # Snapshots diários de métricas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metricas_snapshot (
            id INTEGER PRIMARY KEY,
            data DATE NOT NULL UNIQUE,
            
            -- Financeiras
            faturamento_dia REAL,
            ticket_medio REAL,
            num_pedidos INTEGER,
            margem_media REAL,
            
            -- Estoque
            produtos_ativos INTEGER,
            produtos_sem_estoque INTEGER,
            cobertura_estoque_dias REAL,
            
            -- Precificação
            produtos_acima_mercado INTEGER,
            produtos_abaixo_mercado INTEGER,
            alertas_margem INTEGER,
            
            -- IA
            propostas_pendentes INTEGER,
            produtos_sem_ean INTEGER,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Relatórios estratégicos gerados pela IA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relatorios_estrategicos (
            id INTEGER PRIMARY KEY,
            data DATE NOT NULL,
            tipo TEXT NOT NULL,  -- 'diario', 'semanal', 'mensal'
            titulo TEXT,
            conteudo TEXT,  -- Markdown do relatório
            insights_json TEXT,  -- JSON com insights estruturados
            acoes_recomendadas TEXT,  -- JSON com ações
            prioridade INTEGER DEFAULT 3,  -- 1-5
            status TEXT DEFAULT 'pendente',  -- 'pendente', 'lido', 'aplicado'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ações estratégicas sugeridas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS acoes_estrategicas (
            id INTEGER PRIMARY KEY,
            id_relatorio INTEGER,
            tipo TEXT,  -- 'preco', 'estoque', 'marketing', 'produto'
            descricao TEXT,
            impacto_estimado TEXT,
            urgencia TEXT DEFAULT 'media',  -- 'baixa', 'media', 'alta', 'critica'
            status TEXT DEFAULT 'sugerida',
            aplicada_em TIMESTAMP,
            resultado TEXT,
            FOREIGN KEY (id_relatorio) REFERENCES relatorios_estrategicos(id)
        )
    """)

    # =========================================================================
    # SMART PRICING - Price Proposals (approval workflow)
    # =========================================================================

    # Propostas de preço para aprovação
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS propostas_preco (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_produto INTEGER NOT NULL,
            id_loja INTEGER,  -- NULL = preço base, ou ID da loja específica
            preco_atual REAL NOT NULL,
            preco_sugerido REAL NOT NULL,
            preco_custo REAL,
            margem_atual REAL,  -- % margem atual
            margem_nova REAL,   -- % margem com novo preço
            acao TEXT NOT NULL,  -- 'increase', 'decrease'
            motivo TEXT,  -- Explicação legível
            fonte_dados TEXT,  -- 'concorrentes', 'vendas', 'gemini', 'regra'
            dados_analise TEXT,  -- JSON com dados que embasaram a decisão
            confianca REAL DEFAULT 0.5,  -- 0-1
            status TEXT DEFAULT 'pendente',  -- 'pendente', 'aprovado', 'rejeitado', 'aplicado'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            applied_at TIMESTAMP,
            aplicado_lojas TEXT,  -- JSON com lojas onde foi aplicado
            FOREIGN KEY (id_produto) REFERENCES produtos(id_bling)
        )
    """)

    # Default config values
    defaults = [
        ("MIN_MARGIN_PERCENT", "20"),
        ("MAX_PRICE_SWING_PERCENT", "15"),
        ("PRICING_STRATEGY", "protect_margin"),  # 'protect_margin' or 'aggressive'
        ("SEO_TITLE_MAX_LENGTH", "60"),
        ("SEO_META_MAX_LENGTH", "160"),
    ]

    for key, value in defaults:
        cursor.execute(
            """
            INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)
        """,
            (key, value),
        )

    conn.commit()
    _logger.info(f"Database initialized at: {DB_PATH}")


class VaultDB:
    """High-level interface for the Bling Optimizer database."""

    def __init__(self):
        init_database()

    def _get_conn(self):
        return get_connection()

    # =========================================================================
    # PRODUTOS
    # =========================================================================

    def upsert_produto(self, produto: Dict[str, Any]) -> int:
        """Insert or update a product from Bling API response."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO produtos (id_bling, nome, codigo, preco, preco_custo, 
                                  descricao_curta, situacao, tipo, imagem_url, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id_bling) DO UPDATE SET
                nome = excluded.nome,
                codigo = excluded.codigo,
                preco = excluded.preco,
                preco_custo = excluded.preco_custo,
                descricao_curta = excluded.descricao_curta,
                situacao = excluded.situacao,
                tipo = excluded.tipo,
                imagem_url = excluded.imagem_url,
                synced_at = CURRENT_TIMESTAMP
        """,
            (
                produto.get("id"),
                produto.get("nome"),
                produto.get("codigo"),
                produto.get("preco"),
                produto.get("precoCusto"),
                produto.get("descricaoCurta", ""),
                produto.get("situacao", "A"),
                produto.get("tipo", "P"),
                produto.get("imagemURL", ""),
            ),
        )

        conn.commit()
        row_id = cursor.lastrowid
        return row_id

    def get_produtos_sem_descricao(self) -> List[Dict]:
        """Get products missing short description (candidates for AI enrichment)."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM produtos 
            WHERE (descricao_curta IS NULL OR descricao_curta = '')
            AND situacao = 'A'
            ORDER BY synced_at DESC
        """)

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_produto_by_bling_id(self, id_bling: int) -> Optional[Dict]:
        """Get a single product by Bling ID."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM produtos WHERE id_bling = ?", (id_bling,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # =========================================================================
    # PROPOSTAS IA
    # =========================================================================

    def create_proposta(
        self, id_produto: int, tipo: str, conteudo_original: str, conteudo_proposto: str
    ) -> int:
        """Create a new AI proposal for review."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO propostas_ia (id_produto, tipo, conteudo_original, conteudo_proposto)
            VALUES (?, ?, ?, ?)
        """,
            (id_produto, tipo, conteudo_original, conteudo_proposto),
        )

        conn.commit()
        proposal_id = cursor.lastrowid
        return proposal_id

    def get_propostas_pendentes(self) -> List[Dict]:
        """Get all pending AI proposals."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.*, pr.nome as produto_nome, pr.codigo as produto_codigo
            FROM propostas_ia p
            JOIN produtos pr ON p.id_produto = pr.id_bling
            WHERE p.status = 'pendente'
            ORDER BY p.created_at DESC
        """)

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def aprovar_proposta(self, proposta_id: int):
        """Mark a proposal as approved."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE propostas_ia 
            SET status = 'aprovado', reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (proposta_id,),
        )
        conn.commit()

    def rejeitar_proposta(self, proposta_id: int):
        """Mark a proposal as rejected."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE propostas_ia 
            SET status = 'rejeitado', reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (proposta_id,),
        )
        conn.commit()

    # =========================================================================
    # HISTÓRICO DE PREÇOS
    # =========================================================================

    def registrar_alteracao_preco(
        self,
        id_produto: int,
        preco_anterior: float,
        preco_novo: float,
        motivo: str,
        id_loja: int = None,
    ) -> int:
        """Record a price change in history."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO historico_precos (id_produto, id_loja, preco_anterior, preco_novo, motivo)
            VALUES (?, ?, ?, ?, ?)
        """,
            (id_produto, id_loja, preco_anterior, preco_novo, motivo),
        )

        conn.commit()
        history_id = cursor.lastrowid
        return history_id

    # =========================================================================
    # CONFIG
    # =========================================================================

    def get_config(self, key: str) -> Optional[str]:
        """Get a configuration value."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None

    def set_config(self, key: str, value: str):
        """Set a configuration value."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """,
            (key, value),
        )
        conn.commit()

    # =========================================================================
    # SYNC
    # =========================================================================

    # =========================================================================
    # VÍNCULOS PRODUTO-LOJA
    # =========================================================================

    def upsert_vinculo(self, vinculo: Dict[str, Any]) -> int:
        """Insert or update a product-store link from Bling API response."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO produtos_lojas (id_bling, id_produto, id_loja, preco_loja, synced_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id_bling) DO UPDATE SET
                id_produto = excluded.id_produto,
                id_loja = excluded.id_loja,
                preco_loja = excluded.preco_loja,
                synced_at = CURRENT_TIMESTAMP
        """,
            (
                vinculo.get("id"),
                vinculo.get("produto", {}).get("id"),
                vinculo.get("loja", {}).get("id"),
                vinculo.get("preco"),
            ),
        )

        conn.commit()
        return cursor.lastrowid

    def get_produtos_vinculados(self, id_loja: int) -> List[int]:
        """Get list of Bling product IDs linked to a specific store."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_produto FROM produtos_lojas WHERE id_loja = ?", (id_loja,)
        )
        return [row["id_produto"] for row in cursor.fetchall()]

    def get_produtos_nao_vinculados(self, id_loja: int) -> List[Dict]:
        """Get active products NOT linked to a specific store."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.* FROM produtos p
            WHERE p.situacao = 'A'
              AND p.tipo = 'P'
              AND p.id_bling NOT IN (
                  SELECT pl.id_produto FROM produtos_lojas pl WHERE pl.id_loja = ?
              )
            ORDER BY p.nome
        """,
            (id_loja,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def sync_vinculos_from_bling(self, bling_client, id_loja: int = None) -> int:
        """
        Sync product-store links from Bling to local database.

        Args:
            bling_client: Instance of BlingClient
            id_loja: Optional store ID to filter by

        Returns:
            Number of links synced
        """
        _logger.info(f"Syncing product-store links from Bling (loja={id_loja})...")
        links = bling_client.get_all_produtos_lojas(idLoja=id_loja)

        count = 0
        for link in links:
            self.upsert_vinculo(link)
            count += 1

        _logger.info(f"Synced {count} product-store links to local database")
        return count

    # =========================================================================
    # PROPOSTAS DE PREÇO (Smart Pricing approval workflow)
    # =========================================================================

    def criar_proposta_preco(self, proposta: Dict[str, Any]) -> int:
        """Create a price change proposal for review."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO propostas_preco 
            (id_produto, id_loja, preco_atual, preco_sugerido, preco_custo,
             margem_atual, margem_nova, acao, motivo, fonte_dados, dados_analise, confianca)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                proposta["id_produto"],
                proposta.get("id_loja"),
                proposta["preco_atual"],
                proposta["preco_sugerido"],
                proposta.get("preco_custo"),
                proposta.get("margem_atual"),
                proposta.get("margem_nova"),
                proposta["acao"],
                proposta.get("motivo", ""),
                proposta.get("fonte_dados", ""),
                proposta.get("dados_analise", "{}"),
                proposta.get("confianca", 0.5),
            ),
        )

        conn.commit()
        return cursor.lastrowid

    def listar_propostas_preco(
        self, status: str = "pendente", limit: int = 200
    ) -> List[Dict]:
        """List price proposals with product info."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT pp.*, p.nome as produto_nome, p.codigo as produto_codigo, p.imagem_url
            FROM propostas_preco pp
            JOIN produtos p ON pp.id_produto = p.id_bling
            WHERE pp.status = ?
            ORDER BY pp.confianca DESC, ABS(pp.preco_sugerido - pp.preco_atual) DESC
            LIMIT ?
        """,
            (status, limit),
        )

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def aprovar_proposta_preco(self, proposta_id: int):
        """Mark a price proposal as approved."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE propostas_preco 
            SET status = 'aprovado', reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (proposta_id,),
        )
        conn.commit()

    def rejeitar_proposta_preco(self, proposta_id: int):
        """Mark a price proposal as rejected."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE propostas_preco 
            SET status = 'rejeitado', reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (proposta_id,),
        )
        conn.commit()

    def aprovar_todas_propostas_preco(self) -> int:
        """Approve all pending price proposals. Returns count."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE propostas_preco 
            SET status = 'aprovado', reviewed_at = CURRENT_TIMESTAMP
            WHERE status = 'pendente'
        """
        )
        count = cursor.rowcount
        conn.commit()
        return count

    def marcar_proposta_aplicada(self, proposta_id: int, lojas_aplicadas: str = "{}"):
        """Mark a price proposal as applied (synced to Bling/WooCommerce)."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE propostas_preco 
            SET status = 'aplicado', applied_at = CURRENT_TIMESTAMP, aplicado_lojas = ?
            WHERE id = ?
        """,
            (lojas_aplicadas, proposta_id),
        )
        conn.commit()

    def get_proposta_preco(self, proposta_id: int) -> Optional[Dict]:
        """Get a single price proposal by ID."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT pp.*, p.nome as produto_nome, p.codigo as produto_codigo
            FROM propostas_preco pp
            JOIN produtos p ON pp.id_produto = p.id_bling
            WHERE pp.id = ?
        """,
            (proposta_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def limpar_propostas_pendentes(self) -> int:
        """Delete all pending proposals (before regenerating). Returns count deleted."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM propostas_preco WHERE status = 'pendente'")
        count = cursor.rowcount
        conn.commit()
        return count

    def get_all_produtos_ativos(self) -> List[Dict]:
        """Get all active products."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM produtos WHERE situacao = 'A' ORDER BY nome")
        return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # SYNC
    # =========================================================================

    def sync_produtos_from_bling(self, bling_client) -> int:
        """
        Sync all products from Bling to local database.

        Args:
            bling_client: Instance of BlingClient

        Returns:
            Number of products synced
        """
        _logger.info("Syncing products from Bling...")
        products = bling_client.get_all_produtos(criterio=2)  # Active only

        count = 0
        for product in products:
            self.upsert_produto(product)
            count += 1

        _logger.info(f"Synced {count} products to local database")
        return count


if __name__ == "__main__":
    # Initialize database when run directly
    db = VaultDB()
    _logger.info("Database ready!")
    print("Database ready!")
