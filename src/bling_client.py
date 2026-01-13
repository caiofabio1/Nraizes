import requests
import os
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load tokens from .credentials/bling_api_tokens.env
cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.credentials', 'bling_api_tokens.env')
load_dotenv(cred_path)

class BlingClient:
    def __init__(self):
        self.base_url = "https://www.bling.com.br/Api/v3"
        self.access_token = os.getenv("ACCESS_TOKEN")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        })

    def _request(self, method: str, url: str, **kwargs) -> Any:
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Handle Token expiration
            if response.status_code == 401:
                print("⚠️ Token expirado. Tentando renovar...")
                if self.refresh_token():
                    # Update header with new token
                    self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
                    # Retry request
                    response = self.session.request(method, url, **kwargs)
                else:
                    raise Exception("Unauthorized - Failed to refresh token")
            
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Request Failed: {e}")
            if e.response is not None:
                print(f"Response: {e.response.text}")
            raise

    def refresh_token(self):
        """Refreshes the OAuth token"""
        refresh_token = os.getenv("REFRESH_TOKEN")
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")
        
        url = "https://www.bling.com.br/Api/v3/oauth/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        try:
            response = requests.post(url, data=payload, auth=(client_id, client_secret))
            if response.status_code == 200:
                tokens = response.json()
                new_access = tokens.get('access_token')
                new_refresh = tokens.get('refresh_token')
                
                # Update env file
                with open(cred_path, 'r') as f:
                    content = f.read()
                
                # Simple string replacement might be risky if values are substrings, but standard for this env file
                # Better to regex or precise replace if possible, but keeping it simple for now as per previous script
                current_access = self.access_token
                current_refresh = refresh_token
                
                # We need to read the file again or just overwrite lines if we parse it.
                # Let's use the same logic as the test script which seemed to work for writing
                content = content.replace(f"ACCESS_TOKEN={current_access}", f"ACCESS_TOKEN={new_access}")
                content = content.replace(f"REFRESH_TOKEN={current_refresh}", f"REFRESH_TOKEN={new_refresh}")
                 
                with open(cred_path, 'w') as f:
                    f.write(content)
                
                # Update instance variables
                self.access_token = new_access
                os.environ["ACCESS_TOKEN"] = new_access
                os.environ["REFRESH_TOKEN"] = new_refresh
                return True
            else:
                print(f"Failed to refresh token: {response.text}")
                return False
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return False

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
        return self._request('GET', url, params=params)

    def get_estoques_saldos(self, **kwargs) -> Any:
        """
        Obtém o saldo em estoque de produtos, em todos os depósitos.

        idsProdutos[] (query): IDs dos produtos
        codigos[] (query): Códigos dos produtos
        filtroSaldoEstoque (query): 
        """
        url = f"{self.base_url}/estoques/saldos"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('GET', url, params=params)

    def post_estoques(self, body: Dict[str, Any], **kwargs) -> Any:
        """
        Cria um registro de estoque.

        body: Payload to send
        """
        url = f"{self.base_url}/estoques"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('POST', url, params=params, json=body)

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
        return self._request('GET', url, params=params)

    def post_produtos(self, body: Dict[str, Any], **kwargs) -> Any:
        """
        Cria um produto.

        body: Payload to send
        """
        url = f"{self.base_url}/produtos"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('POST', url, params=params, json=body)

    def delete_produtos(self, **kwargs) -> Any:
        """
        Remove múltiplos produtos pelos IDs.

        idsProdutos[] (query): IDs dos produtos
        """
        url = f"{self.base_url}/produtos"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('DELETE', url, params=params)

    def get_produtos_id_produto(self, idProduto: str, **kwargs) -> Any:
        """
        Obtém um produto pelo ID.

        idProduto: 
        """
        url = f"{self.base_url}/produtos/{idProduto}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('GET', url, params=params)

    def put_produtos_id_produto(self, idProduto: str, body: Dict[str, Any], **kwargs) -> Any:
        """
        Altera um produto pelo ID.

        idProduto: 
        body: Payload to send
        """
        url = f"{self.base_url}/produtos/{idProduto}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('PUT', url, params=params, json=body)

    def delete_produtos_id_produto(self, idProduto: str, **kwargs) -> Any:
        """
        Remove um produto pelo ID.

        idProduto: 
        """
        url = f"{self.base_url}/produtos/{idProduto}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('DELETE', url, params=params)

    def patch_produtos_id_produto(self, idProduto: str, body: Dict[str, Any], **kwargs) -> Any:
        """
        Altera parcialmente um produto pelo ID. Somente os campos informados terão o valor alterado.

        idProduto: 
        body: Payload to send
        """
        url = f"{self.base_url}/produtos/{idProduto}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('PATCH', url, params=params, json=body)

    def patch_produtos_id_produto_situacoes(self, idProduto: str, body: Dict[str, Any], **kwargs) -> Any:
        """
        Altera a situação de um produto pelo ID.

        idProduto: 
        body: Payload to send
        """
        url = f"{self.base_url}/produtos/{idProduto}/situacoes"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('PATCH', url, params=params, json=body)

    def post_produtos_situacoes(self, body: Dict[str, Any], **kwargs) -> Any:
        """
        Altera a situação de múltiplos produtos pelos IDs.

        body: Payload to send
        """
        url = f"{self.base_url}/produtos/situacoes"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('POST', url, params=params, json=body)

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
        return self._request('GET', url, params=params)

    def post_produtos_lojas(self, body: Dict[str, Any], **kwargs) -> Any:
        """
        Cria o vínculo de um produto com uma loja.

        body: Payload com dados do vínculo (idProduto, idLoja, preco, etc.)
        """
        url = f"{self.base_url}/produtos/lojas"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('POST', url, params=params, json=body)

    def get_produtos_lojas_id(self, idProdutoLoja: str, **kwargs) -> Any:
        """
        Obtém um vínculo de produto com loja pelo ID.

        idProdutoLoja: ID do vínculo produto-loja
        """
        url = f"{self.base_url}/produtos/lojas/{idProdutoLoja}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('GET', url, params=params)

    def put_produtos_lojas_id(self, idProdutoLoja: str, body: Dict[str, Any], **kwargs) -> Any:
        """
        Altera o vínculo de um produto com uma loja pelo ID.
        Use para atualizar preços específicos por loja/marketplace.

        idProdutoLoja: ID do vínculo produto-loja
        body: Payload com dados atualizados (preco, etc.)
        """
        url = f"{self.base_url}/produtos/lojas/{idProdutoLoja}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('PUT', url, params=params, json=body)

    def delete_produtos_lojas_id(self, idProdutoLoja: str, **kwargs) -> Any:
        """
        Remove o vínculo de um produto com uma loja pelo ID.

        idProdutoLoja: ID do vínculo produto-loja
        """
        url = f"{self.base_url}/produtos/lojas/{idProdutoLoja}"
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._request('DELETE', url, params=params)

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
            data = result.get('data', [])
            
            if not data:
                break
                
            all_products.extend(data)
            pagina += 1
            
            # Rate limiting protection
            time.sleep(0.5)
        
        return all_products

    def get_all_produtos_lojas(self, idProduto: int = None, idLoja: int = None, limite: int = 100) -> list:
        """
        Obtém TODOS os vínculos produto-loja com paginação automática.
        """
        all_links = []
        pagina = 1
        
        while True:
            result = self.get_produtos_lojas(
                pagina=pagina, 
                limite=limite,
                idProduto=idProduto,
                idLoja=idLoja
            )
            data = result.get('data', [])
            
            if not data:
                break
                
            all_links.extend(data)
            pagina += 1
            time.sleep(0.5)
        
        return all_links
