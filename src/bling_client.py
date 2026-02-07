import requests
import os
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from logger import get_api_logger

# Load tokens from .credentials/bling_api_tokens.env
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cred_path = os.path.join(PROJECT_ROOT, ".credentials", "bling_api_tokens.env")
load_dotenv(cred_path)

# Initialize logger
_api_logger = get_api_logger("bling")


class BlingClient:
    def __init__(self):
        self.base_url = "https://www.bling.com.br/Api/v3"
        self.access_token = os.getenv("ACCESS_TOKEN")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            }
        )

    def _request(self, method: str, url: str, **kwargs) -> Any:
        """Execute an HTTP request with automatic token refresh on 401."""
        start_time = time.time()
        _api_logger.log_request(method, url, kwargs.get("params"))

        try:
            response = self.session.request(method, url, **kwargs)
            response_time_ms = (time.time() - start_time) * 1000

            # Handle Token expiration
            if response.status_code == 401:
                _api_logger.logger.warning("Token expired, attempting refresh...")
                if self.refresh_token():
                    # Update header with new token
                    self.session.headers.update(
                        {"Authorization": f"Bearer {self.access_token}"}
                    )
                    # Retry request
                    response = self.session.request(method, url, **kwargs)
                    response_time_ms = (time.time() - start_time) * 1000
                else:
                    _api_logger.log_error(
                        Exception("Failed to refresh token"), "token_refresh"
                    )
                    raise requests.exceptions.HTTPError(
                        "Unauthorized - Failed to refresh token"
                    )

            _api_logger.log_response(response.status_code, url, response_time_ms)
            response.raise_for_status()

            if response.status_code == 204:
                return None
            return response.json()

        except requests.exceptions.Timeout as e:
            _api_logger.log_error(e, f"Timeout on {method} {url}")
            raise
        except requests.exceptions.ConnectionError as e:
            _api_logger.log_error(e, f"Connection error on {method} {url}")
            raise
        except requests.exceptions.HTTPError as e:
            _api_logger.log_error(e, f"HTTP error on {method} {url}")
            if e.response is not None:
                _api_logger.logger.error(f"Response body: {e.response.text[:500]}")
            raise
        except requests.exceptions.RequestException as e:
            _api_logger.log_error(e, f"Request failed: {method} {url}")
            raise

    def refresh_token(self) -> bool:
        """
        Refresh the OAuth token using the refresh token.

        Returns:
            True if refresh was successful, False otherwise.
        """
        refresh_token_value = os.getenv("REFRESH_TOKEN")
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")

        url = "https://www.bling.com.br/Api/v3/oauth/token"
        payload = {"grant_type": "refresh_token", "refresh_token": refresh_token_value}

        try:
            response = requests.post(url, data=payload, auth=(client_id, client_secret))

            if response.status_code == 200:
                tokens = response.json()
                new_access = tokens.get("access_token")
                new_refresh = tokens.get("refresh_token")

                # Update env file
                with open(cred_path, "r", encoding="utf-8") as f:
                    content = f.read()

                current_access = self.access_token
                current_refresh = refresh_token_value

                content = content.replace(
                    f"ACCESS_TOKEN={current_access}", f"ACCESS_TOKEN={new_access}"
                )
                content = content.replace(
                    f"REFRESH_TOKEN={current_refresh}", f"REFRESH_TOKEN={new_refresh}"
                )

                with open(cred_path, "w", encoding="utf-8") as f:
                    f.write(content)

                # Update instance variables
                self.access_token = new_access
                os.environ["ACCESS_TOKEN"] = new_access
                os.environ["REFRESH_TOKEN"] = new_refresh

                _api_logger.log_token_refresh(True)
                return True
            else:
                _api_logger.logger.error(
                    f"Token refresh failed: HTTP {response.status_code} - {response.text[:200]}"
                )
                _api_logger.log_token_refresh(False)
                return False

        except requests.exceptions.RequestException as e:
            _api_logger.log_error(e, "Token refresh request failed")
            _api_logger.log_token_refresh(False)
            return False
        except IOError as e:
            _api_logger.log_error(e, "Failed to update credentials file")
            _api_logger.log_token_refresh(False)
            return False

    # =========================================================================
    # LOJAS (Stores/Marketplaces)
    # =========================================================================

    def get_lojas(self, **kwargs) -> Any:
        """
        Obtém lojas virtuais configuradas.

        pagina (query): Página
        limite (query): Limite por página
        situacao (query): A=Ativa, I=Inativa
        """
        url = f"{self.base_url}/lojas"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def get_estoques_saldos_id_deposito(self, idDeposito: str, **kwargs) -> Any:
        """
        Obtém o saldo em estoque de produtos pelo ID do depósito.

        idDeposito: ID do depósito
        idsProdutos[] (query): IDs dos produtos
        codigos[] (query): Códigos dos produtos
        filtroSaldoEstoque (query):
        """
        url = f"{self.base_url}/estoques/saldos/{idDeposito}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def get_estoques_saldos(self, **kwargs) -> Any:
        """
        Obtém o saldo em estoque de produtos, em todos os depósitos.

        idsProdutos[] (query): IDs dos produtos
        codigos[] (query): Códigos dos produtos
        filtroSaldoEstoque (query):
        """
        url = f"{self.base_url}/estoques/saldos"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def post_estoques(self, body: Dict[str, Any], **kwargs) -> Any:
        """
        Cria um registro de estoque.

        body: Payload to send
        """
        url = f"{self.base_url}/estoques"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("POST", url, params=params, json=body)

    def get_produtos(self, **kwargs) -> Any:
        """
        Obtém produtos paginados.

        pagina (query):
        limite (query):
        criterio (query): Critério de listagem <br> `1` Últimos incluídos <br> `2` Ativos <br> `3` Inativos <br> `4` Excluídos <br> `5` Todos
        tipo (query): `T` Todos <br> `P` Produtos <br> `S` Serviços <br> `E` Composições <br> `PS` Produtos simples <br> `C` Com variações <br> `V` Variações
        idComponente (query): ID do componente. Utilizado quando o filtro **tipo** for `E`.
        dataInclusaoInicial (query): Data de inclusão inicial
        dataInclusaoFinal (query): Data de inclusão final
        dataAlteracaoInicial (query): Data de alteração inicial
        dataAlteracaoFinal (query): Data de alteração final
        idCategoria (query): ID da categoria do produto
        idLoja (query): ID da loja
        nome (query): Nome do produto
        idsProdutos[] (query): IDs dos produtos
        codigos[] (query): Códigos (SKU) dos produtos
        gtins[] (query): GTINs/EANs dos produtos
        filtroSaldoEstoque (query):
        filtroSaldoEstoqueDeposito (query):
        """
        url = f"{self.base_url}/produtos"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def post_produtos(self, body: Dict[str, Any], **kwargs) -> Any:
        """
        Cria um produto.

        body: Payload to send
        """
        url = f"{self.base_url}/produtos"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("POST", url, params=params, json=body)

    # =========================================================================
    # CONTATOS (Suppliers/Customers)
    # =========================================================================

    def get_contatos(self, **kwargs) -> Any:
        """
        Obtém contatos paginados.

        pagina (query)
        limite (query)
        criterio (query): 1=Ultimos, 2=Ativos, 3=Inativos, 4=Excluidos, 5=Todos
        tipoPessoa (query): F=Fisica, J=Juridica, E=Estrangeiro
        numeroDocumento (query): CPF ou CNPJ
        """
        url = f"{self.base_url}/contatos"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def post_contatos(self, body: Dict[str, Any], **kwargs) -> Any:
        """
        Cria um contato.
        """
        url = f"{self.base_url}/contatos"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("POST", url, params=params, json=body)

    def delete_produtos(self, **kwargs) -> Any:
        """
        Remove múltiplos produtos pelos IDs.

        idsProdutos[] (query): IDs dos produtos
        """
        url = f"{self.base_url}/produtos"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("DELETE", url, params=params)

    def get_produtos_id_produto(self, idProduto: str, **kwargs) -> Any:
        """
        Obtém um produto pelo ID.

        idProduto:
        """
        url = f"{self.base_url}/produtos/{idProduto}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def put_produtos_id_produto(
        self, idProduto: str, body: Dict[str, Any], **kwargs
    ) -> Any:
        """
        Altera um produto pelo ID.

        idProduto:
        body: Payload to send
        """
        url = f"{self.base_url}/produtos/{idProduto}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("PUT", url, params=params, json=body)

    def delete_produtos_id_produto(self, idProduto: str, **kwargs) -> Any:
        """
        Remove um produto pelo ID.

        idProduto:
        """
        url = f"{self.base_url}/produtos/{idProduto}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("DELETE", url, params=params)

    def patch_produtos_id_produto(
        self, idProduto: str, body: Dict[str, Any], **kwargs
    ) -> Any:
        """
        Altera parcialmente um produto pelo ID. Somente os campos informados terão o valor alterado.

        idProduto:
        body: Payload to send
        """
        url = f"{self.base_url}/produtos/{idProduto}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("PATCH", url, params=params, json=body)

    def patch_produtos_id_produto_situacoes(
        self, idProduto: str, body: Dict[str, Any], **kwargs
    ) -> Any:
        """
        Altera a situação de um produto pelo ID.

        idProduto:
        body: Payload to send
        """
        url = f"{self.base_url}/produtos/{idProduto}/situacoes"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("PATCH", url, params=params, json=body)

    def post_produtos_situacoes(self, body: Dict[str, Any], **kwargs) -> Any:
        """
        Altera a situação de múltiplos produtos pelos IDs.

        body: Payload to send
        """
        url = f"{self.base_url}/produtos/situacoes"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("POST", url, params=params, json=body)

    def get_depositos(self, **kwargs) -> Any:
        """
        Obtém depósitos paginados.

        pagina (query)
        limite (query)
        situacao (query): A=Ativo, I=Inativo
        """
        url = f"{self.base_url}/depositos"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    # =========================================================================
    # PRODUTOS - LOJAS (Multi-Store Management)
    # =========================================================================

    def get_produtos_lojas(self, **kwargs) -> Any:
        """
        Obtém vínculos de produtos com lojas paginados.

        pagina (query): Página
        limite (query): Limite por página
        idProduto (query): ID do produto
        idLoja (query): ID da loja
        idCategoriaProduto (query): ID da categoria do produto vinculada à loja
        dataAlteracaoInicial (query): Data de alteração inicial (YYYY-MM-DD HH:MM:SS)
        dataAlteracaoFinal (query): Data de alteração final (YYYY-MM-DD HH:MM:SS)
        """
        url = f"{self.base_url}/produtos/lojas"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def post_produtos_lojas(self, body: Dict[str, Any], **kwargs) -> Any:
        """
        Cria o vínculo de um produto com uma loja.

        body: Payload com dados do vínculo (idProduto, idLoja, preco, etc.)
        """
        url = f"{self.base_url}/produtos/lojas"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("POST", url, params=params, json=body)

    def get_produtos_lojas_id(self, idProdutoLoja: str, **kwargs) -> Any:
        """
        Obtém um vínculo de produto com loja pelo ID.

        idProdutoLoja: ID do vínculo produto-loja
        """
        url = f"{self.base_url}/produtos/lojas/{idProdutoLoja}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def put_produtos_lojas_id(
        self, idProdutoLoja: str, body: Dict[str, Any], **kwargs
    ) -> Any:
        """
        Altera o vínculo de um produto com uma loja pelo ID.
        Use para atualizar preços específicos por loja/marketplace.

        idProdutoLoja: ID do vínculo produto-loja
        body: Payload com dados atualizados (preco, etc.)
        """
        url = f"{self.base_url}/produtos/lojas/{idProdutoLoja}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("PUT", url, params=params, json=body)

    def delete_produtos_lojas_id(self, idProdutoLoja: str, **kwargs) -> Any:
        """
        Remove o vínculo de um produto com uma loja pelo ID.

        idProdutoLoja: ID do vínculo produto-loja
        """
        url = f"{self.base_url}/produtos/lojas/{idProdutoLoja}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("DELETE", url, params=params)

    # =========================================================================
    # CAMPOS CUSTOMIZADOS (Custom Fields - ML Ficha Tecnica)
    # =========================================================================

    def get_campos_customizados_modulos(self, **kwargs) -> Any:
        """
        Obtem modulos que possuem campos customizados.
        Necessario para descobrir o ID do modulo 'Produtos'.
        """
        url = f"{self.base_url}/campos-customizados/modulos"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def get_campos_customizados_tipos(self, **kwargs) -> Any:
        """
        Obtem tipos de campos customizados disponiveis.
        (texto, lista, inteiro, decimal, logico, data, texto longo)
        """
        url = f"{self.base_url}/campos-customizados/tipos"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def get_campos_customizados_modulo(self, idModulo: int, **kwargs) -> Any:
        """
        Obtem campos customizados de um modulo especifico.
        Use para listar todos os campos customizados do modulo Produtos.

        idModulo: ID do modulo (obtido via get_campos_customizados_modulos)
        """
        url = f"{self.base_url}/campos-customizados/modulos/{idModulo}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def get_campo_customizado(self, idCampoCustomizado: int, **kwargs) -> Any:
        """
        Obtem detalhes de um campo customizado.
        """
        url = f"{self.base_url}/campos-customizados/{idCampoCustomizado}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def post_campo_customizado(self, body: Dict[str, Any], **kwargs) -> Any:
        """
        Cria um campo customizado.

        body example:
        {
            "nome": "Marca",
            "situacao": 1,
            "obrigatorio": false,
            "modulo": {"id": 1},
            "tipoCampo": {"id": 1}
        }
        """
        url = f"{self.base_url}/campos-customizados"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("POST", url, params=params, json=body)

    def put_campo_customizado(
        self, idCampoCustomizado: int, body: Dict[str, Any], **kwargs
    ) -> Any:
        """
        Altera um campo customizado.
        """
        url = f"{self.base_url}/campos-customizados/{idCampoCustomizado}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("PUT", url, params=params, json=body)

    def delete_campo_customizado(self, idCampoCustomizado: int, **kwargs) -> Any:
        """
        Remove um campo customizado.
        """
        url = f"{self.base_url}/campos-customizados/{idCampoCustomizado}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("DELETE", url, params=params)

    # =========================================================================
    # ANUNCIOS (Marketplace Listings - ML)
    # =========================================================================

    def get_anuncios(self, **kwargs) -> Any:
        """
        Obtem anuncios paginados.

        pagina (query): Pagina
        limite (query): Limite
        situacao (query): 1=Publicado, 2=Rascunho, 3=Com problema, 4=Pausado
        idProduto (query): Filtrar por produto
        idLoja (query): Filtrar por loja (ex: 205294269 para ML)
        """
        url = f"{self.base_url}/anuncios"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def post_anuncios(self, body: Dict[str, Any], **kwargs) -> Any:
        """
        Cria um anuncio.
        """
        url = f"{self.base_url}/anuncios"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("POST", url, params=params, json=body)

    def get_anuncio(self, idAnuncio: int, **kwargs) -> Any:
        """
        Obtem detalhes de um anuncio.
        """
        url = f"{self.base_url}/anuncios/{idAnuncio}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def put_anuncio(self, idAnuncio: int, body: Dict[str, Any], **kwargs) -> Any:
        """
        Altera um anuncio (titulo, descricao, preco, etc).
        """
        url = f"{self.base_url}/anuncios/{idAnuncio}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("PUT", url, params=params, json=body)

    def delete_anuncio(self, idAnuncio: int, **kwargs) -> Any:
        """
        Remove um anuncio.
        """
        url = f"{self.base_url}/anuncios/{idAnuncio}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("DELETE", url, params=params)

    def post_anuncio_publicar(self, idAnuncio: int, **kwargs) -> Any:
        """
        Publica um anuncio (altera status para publicado).
        """
        url = f"{self.base_url}/anuncios/{idAnuncio}/publicar"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("POST", url, params=params)

    def post_anuncio_pausar(self, idAnuncio: int, **kwargs) -> Any:
        """
        Pausa um anuncio.
        """
        url = f"{self.base_url}/anuncios/{idAnuncio}/pausar"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("POST", url, params=params)

    # =========================================================================
    # CATEGORIAS - LOJAS (Category-Store Mapping for ML)
    # =========================================================================

    def get_categorias_lojas(self, **kwargs) -> Any:
        """
        Obtem vinculos de categorias com lojas.
        """
        url = f"{self.base_url}/categorias/lojas"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def post_categorias_lojas(self, body: Dict[str, Any], **kwargs) -> Any:
        """
        Cria vinculo categoria de produto <-> categoria da loja ML.

        body example:
        {
            "loja": {"id": 205294269},
            "descricao": "Suplementos Alimentares",
            "codigo": "MLB123456",
            "categoriaProduto": {"id": 88001}
        }
        """
        url = f"{self.base_url}/categorias/lojas"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("POST", url, params=params, json=body)

    def get_categoria_loja(self, idCategoriaLoja: int, **kwargs) -> Any:
        """
        Obtem um vinculo especifico de categoria-loja.
        """
        url = f"{self.base_url}/categorias/lojas/{idCategoriaLoja}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("GET", url, params=params)

    def put_categoria_loja(
        self, idCategoriaLoja: int, body: Dict[str, Any], **kwargs
    ) -> Any:
        """
        Altera um vinculo categoria-loja.
        """
        url = f"{self.base_url}/categorias/lojas/{idCategoriaLoja}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("PUT", url, params=params, json=body)

    def delete_categoria_loja(self, idCategoriaLoja: int, **kwargs) -> Any:
        """
        Remove um vinculo categoria-loja.
        """
        url = f"{self.base_url}/categorias/lojas/{idCategoriaLoja}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request("DELETE", url, params=params)

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def get_all_produtos(self, criterio: int = 2, limite: int = 100) -> list:
        """
        Obtém TODOS os produtos ativos com paginação automática.

        criterio: 1=Últimos, 2=Ativos, 3=Inativos, 4=Excluídos, 5=Todos
        limite: Itens por página (max 100)
        """
        all_products = []
        pagina = 1

        while True:
            result = self.get_produtos(pagina=pagina, limite=limite, criterio=criterio)
            data = result.get("data", [])

            if not data:
                break

            all_products.extend(data)
            pagina += 1

            # Rate limiting protection
            time.sleep(0.5)

        return all_products

    def get_all_produtos_lojas(
        self, idProduto: int = None, idLoja: int = None, limite: int = 100
    ) -> list:
        """
        Obtém TODOS os vínculos produto-loja com paginação automática.
        """
        all_links = []
        pagina = 1

        while True:
            result = self.get_produtos_lojas(
                pagina=pagina, limite=limite, idProduto=idProduto, idLoja=idLoja
            )
            data = result.get("data", [])

            if not data:
                break

            all_links.extend(data)
            pagina += 1
            time.sleep(0.5)

        return all_links
