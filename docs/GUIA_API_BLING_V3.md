# Guia Completo API Bling v3 — NRAIZES

> Documento de referencia tecnica | Fevereiro 2026
> Baseado na especificacao OpenAPI 3.0 oficial do Bling

---

## Visao Geral

| Item | Valor |
|------|-------|
| **Base URL** | `https://api.bling.com.br/Api/v3` |
| **Auth** | OAuth 2.0 — Bearer token no header `Authorization` |
| **Content-Type** | `application/json` |
| **Paginacao** | Query params `pagina` (default 1) e `limite` (default 100, min 1) |
| **Rate Limit** | ~3 req/s por token (nao documentado oficialmente; o `bling_client.py` usa `time.sleep(0.5)` entre paginas) |
| **Token Refresh** | POST `https://www.bling.com.br/Api/v3/oauth/token` com `grant_type=refresh_token` |
| **Ambiente teste** | `https://developer.bling.com.br/api/bling` |

### Autenticacao

O `bling_client.py` implementa refresh automatico: se uma request retorna 401, chama `refresh_token()`, atualiza o `.credentials/bling_api_tokens.env` e retenta a request.

### Padrao de Resposta

```json
{
  "data": { ... }       // objeto ou array
}
```

Erros retornam `ErrorResponse` com detalhes do problema.

---

## Status de Implementacao

| Categoria | Implementados | Total na API | Cobertura |
|-----------|:---:|:---:|:---:|
| Anuncios | 0 | 7 | 0% |
| Anuncios - Categorias | 0 | 2 | 0% |
| Borderos | 0 | 2 | 0% |
| Caixas e Bancos | 0 | 5 | 0% |
| Campos Customizados | 0 | 8 | 0% |
| Canais de Venda | 0 | 3 | 0% |
| Categorias - Lojas | 0 | 5 | 0% |
| Categorias - Produtos | 0 | 5 | 0% |
| Categorias - Receitas e Despesas | 0 | 6 | 0% |
| Contas Financeiras | 0 | 2 | 0% |
| Contas a Pagar | 0 | 6 | 0% |
| Contas a Receber | 0 | 8 | 0% |
| **Contatos** | **2** | 10 | 20% |
| Contatos - Tipos | 0 | 1 | 0% |
| Contratos | 0 | 5 | 0% |
| **Depositos** | **1** | 4 | 25% |
| Empresas | 0 | 1 | 0% |
| **Estoques** | **3** | 3 | 100% |
| Formas de Pagamentos | 0 | 7 | 0% |
| Grupos de Produtos | 0 | 6 | 0% |
| Homologacao | 0 | 5 | 0% |
| Logisticas | 0 | 5 | 0% |
| Logisticas - Etiquetas | 0 | 1 | 0% |
| Logisticas - Objetos | 0 | 4 | 0% |
| Logisticas - Remessas | 0 | 5 | 0% |
| Logisticas - Servicos | 0 | 5 | 0% |
| Naturezas de Operacoes | 0 | 2 | 0% |
| Notas Fiscais Eletronicas | 0 | 11 | 0% |
| NFC-e | 0 | 10 | 0% |
| NFS-e | 0 | 8 | 0% |
| Notificacoes | 0 | 3 | 0% |
| Ordens de Producao | 0 | 7 | 0% |
| Pedidos - Compras | 0 | 10 | 0% |
| Pedidos - Vendas | 0 | 14 | 0% |
| **Produtos** | **9** | 9 | 100% |
| Produtos - Estruturas | 0 | 6 | 0% |
| Produtos - Fornecedores | 0 | 5 | 0% |
| **Produtos - Lojas** | **5** | 5 | 100% |
| Produtos - Lotes | 0 | 8 | 0% |
| Produtos - Lotes Lancamentos | 0 | 8 | 0% |
| Produtos - Variacoes | 0 | 3 | 0% |
| Propostas Comerciais | 0 | 7 | 0% |
| Situacoes | 0 | 4 | 0% |
| Situacoes - Modulos | 0 | 4 | 0% |
| Situacoes - Transicoes | 0 | 4 | 0% |
| Usuarios | 0 | 3 | 0% |
| Vendedores | 0 | 2 | 0% |
| **Lojas** (fora do spec) | **1** | ~1 | 100% |
| **TOTAL** | **21** | **254+1** | **~8%** |

Alem dos 21 endpoints, o `bling_client.py` tem 2 helpers com paginacao automatica (`get_all_produtos`, `get_all_produtos_lojas`) e `refresh_token`.

---

## Endpoints por Categoria

### Anuncios

> **Relevancia NRAIZES:** CRITICA. Gerencia anuncios no Mercado Livre — criar, publicar, pausar, alterar precos e descricoes dos 50+ produtos selecionados para ML.

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/anuncios` | Obtem anuncios paginados. Filtros: `situacao` (1=Publicado, 2=Rascunho, 3=Com problema, 4=Pausado), `idProduto`, `tipoIntegracao`, `idLoja` | ❌ |
| POST | `/anuncios` | Cria um anuncio | ❌ |
| GET | `/anuncios/{idAnuncio}` | Obtem detalhes de um anuncio | ❌ |
| PUT | `/anuncios/{idAnuncio}` | Altera um anuncio | ❌ |
| DELETE | `/anuncios/{idAnuncio}` | Remove um anuncio | ❌ |
| POST | `/anuncios/{idAnuncio}/publicar` | Publica um anuncio (altera status para publicado) | ❌ |
| POST | `/anuncios/{idAnuncio}/pausar` | Pausa um anuncio | ❌ |

### Anuncios - Categorias

> **Relevancia NRAIZES:** ALTA. Necessario para mapear categorias do ML ao criar anuncios.

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/anuncios/categorias` | Obtem categorias de anuncios. Params: `tipoIntegracao`, `idLoja`, `idCategoria`, `tipoProduto` | ❌ |
| GET | `/anuncios/categorias/{idCategoria}` | Obtem atributos de uma categoria de anuncio | ❌ |

### Borderos

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/borderos/{idBordero}` | Obtem um bordero | ❌ |
| DELETE | `/borderos/{idBordero}` | Remove um bordero | ❌ |

### Caixas e Bancos

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/caixas` | Obtem lancamentos de caixas e bancos | ❌ |
| POST | `/caixas` | Cria lancamento de caixa e banco | ❌ |
| GET | `/caixas/{idCaixa}` | Obtem um lancamento | ❌ |
| PUT | `/caixas/{idCaixa}` | Atualiza um lancamento | ❌ |
| DELETE | `/caixas/{idCaixa}` | Remove um lancamento | ❌ |

### Campos Customizados

> **Relevancia NRAIZES:** ALTA. Campos customizados mapeiam atributos obrigatorios do ML (marca, formato, sabor, vegano, etc.) — essenciais para ficha tecnica.

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/campos-customizados/modulos` | Obtem modulos que possuem campos customizados | ❌ |
| GET | `/campos-customizados/tipos` | Obtem tipos de campos customizados | ❌ |
| GET | `/campos-customizados/modulos/{idModulo}` | Obtem campos customizados por modulo | ❌ |
| GET | `/campos-customizados/{idCampoCustomizado}` | Obtem um campo customizado | ❌ |
| PUT | `/campos-customizados/{idCampoCustomizado}` | Altera um campo customizado | ❌ |
| DELETE | `/campos-customizados/{idCampoCustomizado}` | Remove um campo customizado | ❌ |
| POST | `/campos-customizados` | Cria um campo customizado | ❌ |
| PATCH | `/campos-customizados/{idCampoCustomizado}/situacoes` | Altera situacao de um campo customizado | ❌ |

### Canais de Venda

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/canais-venda` | Obtem canais de venda | ❌ |
| GET | `/canais-venda/{idCanalVenda}` | Obtem um canal de venda | ❌ |
| GET | `/canais-venda/tipos` | Obtem tipos de canais de venda | ❌ |

### Categorias - Lojas

> **Relevancia NRAIZES:** CRITICA. Vincula categorias de produtos do Bling as categorias do Mercado Livre. Sem isso, produtos nao podem ser publicados na categoria correta do ML.

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/categorias/lojas` | Obtem categorias de lojas vinculadas a categorias de produtos | ❌ |
| POST | `/categorias/lojas` | Cria vinculo categoria loja <-> categoria produto | ❌ |
| GET | `/categorias/lojas/{idCategoriaLoja}` | Obtem um vinculo | ❌ |
| PUT | `/categorias/lojas/{idCategoriaLoja}` | Altera um vinculo | ❌ |
| DELETE | `/categorias/lojas/{idCategoriaLoja}` | Remove um vinculo | ❌ |

### Categorias - Produtos

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/categorias/produtos` | Obtem categorias de produtos | ❌ |
| POST | `/categorias/produtos` | Cria uma categoria de produto | ❌ |
| GET | `/categorias/produtos/{idCategoriaProduto}` | Obtem uma categoria | ❌ |
| PUT | `/categorias/produtos/{idCategoriaProduto}` | Altera uma categoria | ❌ |
| DELETE | `/categorias/produtos/{idCategoriaProduto}` | Remove uma categoria | ❌ |

### Categorias - Receitas e Despesas

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/categorias/receitas-despesas` | Obtem categorias | ❌ |
| POST | `/categorias/receitas-despesas` | Cria uma categoria | ❌ |
| DELETE | `/categorias/receitas-despesas` | Remove multiplas categorias | ❌ |
| GET | `/categorias/receitas-despesas/{idCategoria}` | Obtem uma categoria | ❌ |
| PUT | `/categorias/receitas-despesas/{idCategoria}` | Atualiza uma categoria | ❌ |
| DELETE | `/categorias/receitas-despesas/{idCategoria}` | Remove uma categoria | ❌ |

### Contas Financeiras

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/contas-contabeis` | Obtem contas financeiras | ❌ |
| GET | `/contas-contabeis/{idContaContabil}` | Obtem uma conta | ❌ |

### Contas a Pagar

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/contas/pagar` | Obtem contas a pagar | ❌ |
| POST | `/contas/pagar` | Cria uma conta a pagar | ❌ |
| GET | `/contas/pagar/{idContaPagar}` | Obtem uma conta | ❌ |
| PUT | `/contas/pagar/{idContaPagar}` | Atualiza uma conta | ❌ |
| DELETE | `/contas/pagar/{idContaPagar}` | Remove uma conta | ❌ |
| POST | `/contas/pagar/{idContaPagar}/baixar` | Cria recebimento de uma conta | ❌ |

### Contas a Receber

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/contas/receber` | Obtem contas a receber | ❌ |
| POST | `/contas/receber` | Cria uma conta a receber | ❌ |
| GET | `/contas/receber/{idContaReceber}` | Obtem uma conta | ❌ |
| PUT | `/contas/receber/{idContaReceber}` | Altera uma conta | ❌ |
| DELETE | `/contas/receber/{idContaReceber}` | Remove uma conta | ❌ |
| POST | `/contas/receber/{idContaReceber}/baixar` | Cria recebimento de uma conta | ❌ |
| GET | `/contas/receber/boletos` | Obtem boletos | ❌ |
| POST | `/contas/receber/boletos/cancelar` | Cancela boletos | ❌ |

### Contatos

> **Relevancia NRAIZES:** MEDIA. Contatos sao fornecedores e clientes. GET e POST ja implementados. Para ML, pode ser necessario criar contatos automaticamente a partir de pedidos.

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/contatos` | Obtem contatos paginados. Filtros: `criterio`, `tipoPessoa`, `numeroDocumento` | ✅ |
| POST | `/contatos` | Cria um contato | ✅ |
| DELETE | `/contatos` | Remove multiplos contatos | ❌ |
| GET | `/contatos/{idContato}` | Obtem um contato | ❌ |
| PUT | `/contatos/{idContato}` | Altera um contato | ❌ |
| DELETE | `/contatos/{idContato}` | Remove um contato | ❌ |
| GET | `/contatos/{idContato}/tipos` | Obtem tipos de um contato | ❌ |
| GET | `/contatos/consumidor-final` | Obtem dados do Consumidor Final | ❌ |
| PATCH | `/contatos/{idContato}/situacoes` | Altera situacao de um contato | ❌ |
| POST | `/contatos/situacoes` | Altera situacao de multiplos contatos | ❌ |

### Contatos - Tipos

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/contatos/tipos` | Obtem tipos de contato | ❌ |

### Contratos

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/contratos` | Obtem contratos | ❌ |
| POST | `/contratos` | Cria um contrato | ❌ |
| GET | `/contratos/{idContrato}` | Obtem um contrato | ❌ |
| PUT | `/contratos/{idContrato}` | Altera um contrato | ❌ |
| DELETE | `/contratos/{idContrato}` | Remove um contrato | ❌ |

### Depositos

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/depositos` | Obtem depositos paginados. Filtros: `situacao` (A/I) | ✅ |
| POST | `/depositos` | Cria um deposito | ❌ |
| GET | `/depositos/{idDeposito}` | Obtem um deposito | ❌ |
| PUT | `/depositos/{idDeposito}` | Altera um deposito | ❌ |

### Empresas

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/empresas/me/dados-basicos` | Obtem dados basicos da empresa | ❌ |

### Estoques

> **Relevancia NRAIZES:** CRITICA. Ja 100% implementado. Controla saldos de estoque compartilhados entre WooCommerce e ML.

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/estoques/saldos/{idDeposito}` | Obtem saldo por deposito. Filtros: `idsProdutos[]`, `codigos[]` | ✅ |
| GET | `/estoques/saldos` | Obtem saldo em todos os depositos | ✅ |
| POST | `/estoques` | Cria registro de estoque (entrada/saida) | ✅ |

### Formas de Pagamentos

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/formas-pagamentos` | Obtem formas de pagamento | ❌ |
| POST | `/formas-pagamentos` | Cria uma forma de pagamento | ❌ |
| GET | `/formas-pagamentos/{idFormaPagamento}` | Obtem uma forma | ❌ |
| PUT | `/formas-pagamentos/{idFormaPagamento}` | Altera uma forma | ❌ |
| DELETE | `/formas-pagamentos/{idFormaPagamento}` | Remove uma forma | ❌ |
| PATCH | `/formas-pagamentos/{idFormaPagamento}/padrao` | Altera o padrao | ❌ |
| PATCH | `/formas-pagamentos/{idFormaPagamento}/situacao` | Altera situacao | ❌ |

### Grupos de Produtos

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/grupos-produtos` | Obtem grupos | ❌ |
| POST | `/grupos-produtos` | Cria um grupo | ❌ |
| DELETE | `/grupos-produtos` | Remove multiplos grupos | ❌ |
| GET | `/grupos-produtos/{idGrupoProduto}` | Obtem um grupo | ❌ |
| PUT | `/grupos-produtos/{idGrupoProduto}` | Altera um grupo | ❌ |
| DELETE | `/grupos-produtos/{idGrupoProduto}` | Remove um grupo | ❌ |

### Homologacao

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/homologacao/produtos` | Obtem produto de homologacao | ❌ |
| POST | `/homologacao/produtos` | Cria produto de homologacao | ❌ |
| PUT | `/homologacao/produtos/{idProdutoHomologacao}` | Altera produto | ❌ |
| DELETE | `/homologacao/produtos/{idProdutoHomologacao}` | Remove produto | ❌ |
| PATCH | `/homologacao/produtos/{idProdutoHomologacao}/situacoes` | Altera situacao | ❌ |

### Logisticas

> **Relevancia NRAIZES:** ALTA. Gerencia transportadoras, servicos de frete, etiquetas e rastreamento — essencial para Mercado Envios.

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/logisticas` | Obtem logisticas | ❌ |
| POST | `/logisticas` | Cria logistica | ❌ |
| GET | `/logisticas/{idLogistica}` | Obtem uma logistica | ❌ |
| PUT | `/logisticas/{idLogistica}` | Altera uma logistica | ❌ |
| DELETE | `/logisticas/{idLogistica}` | Remove uma logistica | ❌ |

### Logisticas - Etiquetas

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/logisticas/etiquetas` | Obtem etiquetas das vendas | ❌ |

### Logisticas - Objetos

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/logisticas/objetos/{idObjeto}` | Obtem um objeto de logistica | ❌ |
| PUT | `/logisticas/objetos/{idObjeto}` | Altera um objeto | ❌ |
| DELETE | `/logisticas/objetos/{idObjeto}` | Remove um objeto | ❌ |
| POST | `/logisticas/objetos` | Cria um objeto de logistica | ❌ |

### Logisticas - Remessas

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/logisticas/remessas/{idRemessa}` | Obtem uma remessa | ❌ |
| PUT | `/logisticas/remessas/{idRemessa}` | Altera uma remessa | ❌ |
| DELETE | `/logisticas/remessas/{idRemessa}` | Remove uma remessa | ❌ |
| GET | `/logisticas/{idLogistica}/remessas` | Obtem remessas de uma logistica | ❌ |
| POST | `/logisticas/remessas` | Cria uma remessa de postagem | ❌ |

### Logisticas - Servicos

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/logisticas/servicos` | Obtem servicos de logistica | ❌ |
| POST | `/logisticas/servicos` | Cria um servico | ❌ |
| GET | `/logisticas/servicos/{idLogisticaServico}` | Obtem um servico | ❌ |
| PUT | `/logisticas/servicos/{idLogisticaServico}` | Altera um servico | ❌ |
| PATCH | `/logisticas/{idLogisticaServico}/situacoes` | Ativa/desativa um servico | ❌ |

### Naturezas de Operacoes

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/naturezas-operacoes` | Obtem naturezas de operacoes | ❌ |
| POST | `/naturezas-operacoes/{idNaturezaOperacao}/obter-tributacao` | Obtem regras de tributacao | ❌ |

### Notas Fiscais Eletronicas (NF-e)

> **Relevancia NRAIZES:** CRITICA. Emissao automatica de NF-e a partir de pedidos ML. Obrigatorio para toda venda no Mercado Livre.

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/nfe` | Obtem notas fiscais | ❌ |
| POST | `/nfe` | Cria uma nota fiscal | ❌ |
| DELETE | `/nfe` | Remove multiplas NF-e | ❌ |
| GET | `/nfe/{idNotaFiscal}` | Obtem uma NF-e | ❌ |
| PUT | `/nfe/{idNotaFiscal}` | Altera uma NF-e | ❌ |
| POST | `/nfe/{idNotaFiscal}/enviar` | Envia NF-e para SEFAZ | ❌ |
| POST | `/nfe/{idNotaFiscal}/lancar-contas` | Lanca contas da NF-e | ❌ |
| POST | `/nfe/{idNotaFiscal}/estornar-contas` | Estorna contas da NF-e | ❌ |
| POST | `/nfe/{idNotaFiscal}/lancar-estoque` | Lanca estoque (deposito padrao) | ❌ |
| POST | `/nfe/{idNotaFiscal}/lancar-estoque/{idDeposito}` | Lanca estoque (deposito especifico) | ❌ |
| POST | `/nfe/{idNotaFiscal}/estornar-estoque` | Estorna estoque da NF-e | ❌ |

### Notas Fiscais de Consumidor (NFC-e)

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/nfce` | Obtem NFC-e | ❌ |
| POST | `/nfce` | Cria uma NFC-e | ❌ |
| GET | `/nfce/{idNotaFiscalConsumidor}` | Obtem uma NFC-e | ❌ |
| PUT | `/nfce/{idNotaFiscalConsumidor}` | Altera uma NFC-e | ❌ |
| POST | `/nfce/{idNotaFiscalConsumidor}/enviar` | Envia NFC-e | ❌ |
| POST | `/nfce/{idNotaFiscalConsumidor}/lancar-contas` | Lanca contas | ❌ |
| POST | `/nfce/{idNotaFiscalConsumidor}/estornar-contas` | Estorna contas | ❌ |
| POST | `/nfce/{idNotaFiscalConsumidor}/lancar-estoque` | Lanca estoque (padrao) | ❌ |
| POST | `/nfce/{idNotaFiscalConsumidor}/lancar-estoque/{idDeposito}` | Lanca estoque (especifico) | ❌ |
| POST | `/nfce/{idNotaFiscalConsumidor}/estornar-estoque` | Estorna estoque | ❌ |

### Notas Fiscais de Servico (NFS-e)

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/nfse` | Obtem notas de servico | ❌ |
| POST | `/nfse` | Cria nota de servico | ❌ |
| GET | `/nfse/{idNotaServico}` | Obtem uma NFS-e | ❌ |
| DELETE | `/nfse/{idNotaServico}` | Exclui uma NFS-e | ❌ |
| POST | `/nfse/{idNotaServico}/enviar` | Envia NFS-e | ❌ |
| POST | `/nfse/{idNotaServico}/cancelar` | Cancela NFS-e | ❌ |
| GET | `/nfse/configuracoes` | Obtem configuracoes NFS-e | ❌ |
| PUT | `/nfse/configuracoes` | Altera configuracoes NFS-e | ❌ |

### Notificacoes

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/notificacoes` | Obtem notificacoes de um periodo | ❌ |
| POST | `/notificacoes/{idNotificacao}/confirmar-leitura` | Marca como lida | ❌ |
| GET | `/notificacoes/quantidade` | Obtem quantidade de notificacoes | ❌ |

### Ordens de Producao

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/ordens-producao` | Obtem ordens de producao | ❌ |
| POST | `/ordens-producao` | Cria uma ordem | ❌ |
| GET | `/ordens-producao/{idOrdemProducao}` | Obtem uma ordem | ❌ |
| PUT | `/ordens-producao/{idOrdemProducao}` | Altera uma ordem | ❌ |
| DELETE | `/ordens-producao/{idOrdemProducao}` | Remove uma ordem | ❌ |
| PUT | `/ordens-producao/{idOrdemProducao}/situacoes` | Altera situacao | ❌ |
| POST | `/ordens-producao/gerar-sob-demanda` | Gera ordens sob demanda | ❌ |

### Pedidos - Compras

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/pedidos/compras` | Obtem pedidos de compra | ❌ |
| POST | `/pedidos/compras` | Cria pedido de compra | ❌ |
| GET | `/pedidos/compras/{idPedidoCompra}` | Obtem um pedido | ❌ |
| PUT | `/pedidos/compras/{idPedidoCompra}` | Altera um pedido | ❌ |
| DELETE | `/pedidos/compras/{idPedidoCompra}` | Remove um pedido | ❌ |
| PATCH | `/pedidos/compras/{idPedidoCompra}/situacoes` | Altera situacao | ❌ |
| POST | `/pedidos/compras/{idPedidoCompra}/lancar-contas` | Lanca contas | ❌ |
| POST | `/pedidos/compras/{idPedidoCompra}/estornar-contas` | Estorna contas | ❌ |
| POST | `/pedidos/compras/{idPedidoCompra}/lancar-estoque` | Lanca estoque | ❌ |
| POST | `/pedidos/compras/{idPedidoCompra}/estornar-estoque` | Estorna estoque | ❌ |

### Pedidos - Vendas

> **Relevancia NRAIZES:** CRITICA. Recebe pedidos do ML, gerencia situacoes, gera NF-e automaticamente, controla estoque e financeiro.

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/pedidos/vendas` | Obtem pedidos de venda paginados | ❌ |
| POST | `/pedidos/vendas` | Cria um pedido de venda | ❌ |
| DELETE | `/pedidos/vendas` | Remove multiplos pedidos | ❌ |
| GET | `/pedidos/vendas/{idPedidoVenda}` | Obtem um pedido | ❌ |
| PUT | `/pedidos/vendas/{idPedidoVenda}` | Altera um pedido | ❌ |
| DELETE | `/pedidos/vendas/{idPedidoVenda}` | Remove um pedido | ❌ |
| PATCH | `/pedidos/vendas/{idPedidoVenda}/situacoes/{idSituacao}` | Altera situacao de um pedido | ❌ |
| POST | `/pedidos/vendas/{idPedidoVenda}/lancar-estoque/{idDeposito}` | Lanca estoque (deposito especifico) | ❌ |
| POST | `/pedidos/vendas/{idPedidoVenda}/lancar-estoque` | Lanca estoque (deposito padrao) | ❌ |
| POST | `/pedidos/vendas/{idPedidoVenda}/estornar-estoque` | Estorna estoque | ❌ |
| POST | `/pedidos/vendas/{idPedidoVenda}/lancar-contas` | Lanca contas | ❌ |
| POST | `/pedidos/vendas/{idPedidoVenda}/estornar-contas` | Estorna contas | ❌ |
| POST | `/pedidos/vendas/{idPedidoVenda}/gerar-nfe` | Gera NF-e a partir do pedido | ❌ |
| POST | `/pedidos/vendas/{idPedidoVenda}/gerar-nfce` | Gera NFC-e a partir do pedido | ❌ |

### Produtos

> **Relevancia NRAIZES:** CRITICA. Ja 100% implementado. CRUD completo de produtos, alteracao em lote de situacoes.

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/produtos` | Obtem produtos paginados. Filtros: `criterio`, `tipo`, `idCategoria`, `idLoja`, `nome`, `idsProdutos[]`, `codigos[]`, `gtins[]` | ✅ |
| POST | `/produtos` | Cria um produto | ✅ |
| DELETE | `/produtos` | Remove multiplos produtos por IDs | ✅ |
| GET | `/produtos/{idProduto}` | Obtem um produto | ✅ |
| PUT | `/produtos/{idProduto}` | Altera um produto | ✅ |
| DELETE | `/produtos/{idProduto}` | Remove um produto | ✅ |
| PATCH | `/produtos/{idProduto}` | Altera parcialmente um produto | ✅ |
| PATCH | `/produtos/{idProduto}/situacoes` | Altera situacao de um produto | ✅ |
| POST | `/produtos/situacoes` | Altera situacao de multiplos produtos | ✅ |

### Produtos - Estruturas

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/produtos/estruturas/{idProdutoEstrutura}` | Obtem estrutura de composicao | ❌ |
| PUT | `/produtos/estruturas/{idProdutoEstrutura}` | Altera estrutura | ❌ |
| POST | `/produtos/estruturas/{idProdutoEstrutura}/componentes` | Adiciona componentes | ❌ |
| DELETE | `/produtos/estruturas/{idProdutoEstrutura}/componentes` | Remove componentes | ❌ |
| PATCH | `/produtos/estruturas/{idProdutoEstrutura}/componentes/{idComponente}` | Altera um componente | ❌ |
| DELETE | `/produtos/estruturas` | Remove estrutura de multiplos produtos | ❌ |

### Produtos - Fornecedores

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/produtos/fornecedores` | Obtem produtos fornecedores | ❌ |
| POST | `/produtos/fornecedores` | Cria produto fornecedor | ❌ |
| GET | `/produtos/fornecedores/{idProdutoFornecedor}` | Obtem um produto fornecedor | ❌ |
| PUT | `/produtos/fornecedores/{idProdutoFornecedor}` | Altera um produto fornecedor | ❌ |
| DELETE | `/produtos/fornecedores/{idProdutoFornecedor}` | Remove um produto fornecedor | ❌ |

### Produtos - Lojas

> **Relevancia NRAIZES:** CRITICA. Ja 100% implementado. Gerencia vinculos produto-loja (precos por canal, como ML com multiplicador 1.15x).

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/produtos/lojas` | Obtem vinculos produto-loja. Filtros: `idProduto`, `idLoja`, `idCategoriaProduto`, `dataAlteracaoInicial/Final` | ✅ |
| POST | `/produtos/lojas` | Cria vinculo produto-loja | ✅ |
| GET | `/produtos/lojas/{idProdutoLoja}` | Obtem um vinculo | ✅ |
| PUT | `/produtos/lojas/{idProdutoLoja}` | Altera um vinculo | ✅ |
| DELETE | `/produtos/lojas/{idProdutoLoja}` | Remove um vinculo | ✅ |

### Produtos - Lotes

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/produtos/lotes` | Obtem lotes de produtos | ❌ |
| PUT | `/produtos/lotes` | Salva lotes | ❌ |
| DELETE | `/produtos/lotes` | Remove lotes | ❌ |
| GET | `/produtos/lotes/{idLote}` | Obtem um lote | ❌ |
| PUT | `/produtos/lotes/{idLote}` | Altera um lote | ❌ |
| GET | `/produtos/lotes/controla-lote` | Verifica controle de lote | ❌ |
| POST | `/produtos/{idProduto}/lotes/controla-lote/desativar` | Desativa controle de lote | ❌ |
| PATCH | `/produtos/lotes/{idLote}/status` | Altera status de um lote | ❌ |

### Produtos - Lotes Lancamentos

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/produtos/lotes/{idLote}/lancamentos` | Obtem lancamentos de um lote | ❌ |
| POST | `/produtos/lotes/{idLote}/lancamentos` | Cria lancamento de lote | ❌ |
| GET | `/produtos/lotes/lancamentos/{idLancamento}` | Obtem um lancamento | ❌ |
| PATCH | `/produtos/lotes/lancamentos/{idLancamento}` | Altera observacao do lancamento | ❌ |
| GET | `/produtos/{idProduto}/lotes/{idLote}/depositos/{idDeposito}/saldo` | Saldo de um lote | ❌ |
| GET | `/produtos/{idProduto}/lotes/depositos/{idDeposito}/saldo` | Saldos dos lotes por deposito | ❌ |
| GET | `/produtos/{idProduto}/lotes/depositos/{idDeposito}/saldo/soma` | Soma de saldos no deposito | ❌ |
| GET | `/produtos/{idProduto}/lotes/saldo/soma` | Saldo total dos lotes | ❌ |

### Produtos - Variacoes

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/produtos/variacoes/{idProdutoPai}` | Obtem produto e variacoes | ❌ |
| POST | `/produtos/variacoes/atributos/gerar-combinacoes` | Gera combinacoes de variacoes | ❌ |
| PATCH | `/produtos/variacoes/{idProdutoPai}/atributos` | Altera nome do atributo | ❌ |

### Propostas Comerciais

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/propostas-comerciais` | Obtem propostas | ❌ |
| POST | `/propostas-comerciais` | Cria uma proposta | ❌ |
| DELETE | `/propostas-comerciais` | Remove multiplas | ❌ |
| GET | `/propostas-comerciais/{idPropostaComercial}` | Obtem uma proposta | ❌ |
| PUT | `/propostas-comerciais/{idPropostaComercial}` | Altera uma proposta | ❌ |
| DELETE | `/propostas-comerciais/{idPropostaComercial}` | Remove uma proposta | ❌ |
| PATCH | `/propostas-comerciais/{idPropostaComercial}/situacoes` | Altera situacao | ❌ |

### Situacoes

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/situacoes/{idSituacao}` | Obtem uma situacao | ❌ |
| PUT | `/situacoes/{idSituacao}` | Altera uma situacao | ❌ |
| DELETE | `/situacoes/{idSituacao}` | Remove uma situacao | ❌ |
| POST | `/situacoes` | Cria uma situacao | ❌ |

### Situacoes - Modulos

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/situacoes/modulos` | Obtem modulos | ❌ |
| GET | `/situacoes/modulos/{idModuloSistema}` | Obtem situacoes de um modulo | ❌ |
| GET | `/situacoes/modulos/{idModuloSistema}/acoes` | Obtem acoes de um modulo | ❌ |
| GET | `/situacoes/modulos/{idModuloSistema}/transicoes` | Obtem transicoes | ❌ |

### Situacoes - Transicoes

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/situacoes/transicoes/{idTransicao}` | Obtem uma transicao | ❌ |
| PUT | `/situacoes/transicoes/{idTransicao}` | Altera uma transicao | ❌ |
| DELETE | `/situacoes/transicoes/{idTransicao}` | Remove uma transicao | ❌ |
| POST | `/situacoes/transicoes` | Cria uma transicao | ❌ |

### Usuarios

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| POST | `/usuarios/recuperar-senha` | Solicita recuperacao de senha | ❌ |
| PATCH | `/usuarios/redefinir-senha` | Redefine senha | ❌ |
| GET | `/usuarios/verificar-hash` | Valida hash recebido | ❌ |

### Vendedores

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/vendedores` | Obtem vendedores | ❌ |
| GET | `/vendedores/{idVendedor}` | Obtem um vendedor | ❌ |

### Lojas (endpoint fora da spec OpenAPI)

> Endpoint usado pelo `bling_client.py` mas ausente na spec OpenAPI publica.

| Metodo | Endpoint | Descricao | Impl? |
|--------|----------|-----------|:-----:|
| GET | `/lojas` | Obtem lojas virtuais configuradas. Filtros: `pagina`, `limite`, `situacao` (A/I) | ✅ |

---

## Endpoints Prioritarios para Integracao Mercado Livre

Baseado no fluxo descrito em `BOAS_PRATICAS_ML_BLING.md`, estes sao os endpoints que devem ser implementados no `bling_client.py` para viabilizar a operacao ML:

### 1. Anuncios (PRIORIDADE MAXIMA)

**Por que:** Criar, publicar, pausar e alterar anuncios no ML diretamente via API, sem depender da interface do Bling.

Endpoints necessarios:
- `GET /anuncios` — listar anuncios existentes, filtrar por situacao
- `POST /anuncios` — criar novos anuncios
- `GET /anuncios/{id}` — obter detalhes (verificar status de publicacao)
- `PUT /anuncios/{id}` — alterar titulo, descricao, preco
- `POST /anuncios/{id}/publicar` — ativar anuncio
- `POST /anuncios/{id}/pausar` — pausar quando estoque zera

### 2. Categorias - Lojas (PRIORIDADE MAXIMA)

**Por que:** Vincular categorias Bling as categorias do ML. O `category_map.json` ja tem 88 categorias mapeadas; esse endpoint automatiza a vinculacao.

Endpoints necessarios:
- `GET /categorias/lojas` — listar vinculos existentes
- `POST /categorias/lojas` — criar vinculos novos
- `PUT /categorias/lojas/{id}` — atualizar vinculos

### 3. Campos Customizados (PRIORIDADE ALTA)

**Por que:** Atributos da ficha tecnica do ML (marca, formato, sabor, vegano, etc.) sao campos customizados no Bling. Sem eles, o anuncio nao e publicado em muitas categorias.

Endpoints necessarios:
- `GET /campos-customizados/modulos` — descobrir modulo de Produtos
- `GET /campos-customizados/modulos/{idModulo}` — listar campos do modulo
- `POST /campos-customizados` — criar campos faltantes
- `PUT /campos-customizados/{id}` — atualizar valores

### 4. Pedidos de Venda (PRIORIDADE ALTA)

**Por que:** Receber pedidos do ML, gerenciar status, dar baixa em estoque e gerar NF-e automaticamente.

Endpoints necessarios:
- `GET /pedidos/vendas` — listar pedidos (filtrar por loja ML)
- `GET /pedidos/vendas/{id}` — detalhes do pedido
- `PATCH /pedidos/vendas/{id}/situacoes/{idSituacao}` — atualizar status
- `POST /pedidos/vendas/{id}/lancar-estoque` — dar baixa no estoque
- `POST /pedidos/vendas/{id}/gerar-nfe` — gerar NF-e automaticamente

### 5. NF-e (PRIORIDADE ALTA)

**Por que:** Emissao obrigatoria para toda venda no ML. O fluxo ideal: pedido chega -> gera NF-e -> envia para SEFAZ -> disponibiliza DANFE.

Endpoints necessarios:
- `POST /nfe` — criar NF-e
- `POST /nfe/{id}/enviar` — enviar para SEFAZ
- `GET /nfe/{id}` — obter XML/DANFE (link no response)
- `POST /nfe/{id}/lancar-estoque` — baixa automatica

### 6. Logisticas (PRIORIDADE MEDIA)

**Por que:** Gerenciar etiquetas de envio e rastreamento para Mercado Envios.

Endpoints necessarios:
- `GET /logisticas` — listar logisticas configuradas
- `GET /logisticas/etiquetas` — obter etiquetas para impressao
- `POST /logisticas/objetos` — criar objeto de envio
- `GET /logisticas/objetos/{id}` — consultar rastreamento

---

## Schemas de Request Body (Endpoints Prioritarios)

### POST /anuncios — Criar Anuncio

```json
{
  "produto": {
    "id": 123                          // ID do produto no Bling (obrigatorio)
  },
  "integracao": {
    "tipo": "MercadoLivre"             // Tipo de integracao (obrigatorio)
  },
  "loja": {
    "id": 205294269                    // ID da loja ML no Bling (obrigatorio)
  },
  "nome": "Omega 3 DHA Ocean Drop 60 Capsulas 1000mg",
  "descricao": "Descricao do anuncio com min 300 palavras...",
  "preco": {
    "valor": 115.00,                   // Preco de venda (base x 1.15)
    "promocional": 99.90               // Preco promocional (opcional)
  },
  "estoques": {
    "gerencia": true,                  // Gerenciar estoque automaticamente
    "itens": [1234567]                 // IDs dos depositos
  },
  "categoria": {
    "id": "MLB12345"                   // ID da categoria no ML
  },
  "variacoes": [                       // Opcional: variacoes do anuncio
    {
      "produto": { "id": 456 },
      "integracao": { "tipo": "MercadoLivre" },
      "loja": { "id": 205294269 },
      "nome": "Variacao Sabor Chocolate",
      "preco": { "valor": 115.00 }
    }
  ]
}
```

### POST /categorias/lojas — Vincular Categoria

```json
{
  "loja": {
    "id": 205294269                    // ID da loja ML no Bling (obrigatorio)
  },
  "descricao": "Suplementos Alimentares",  // Nome descritivo (obrigatorio)
  "codigo": "MLB123456",              // Codigo da categoria na loja (obrigatorio)
  "categoriaProduto": {
    "id": 88001                        // ID da categoria de produto no Bling (obrigatorio)
  }
}
```

### POST /campos-customizados — Criar Campo

```json
{
  "nome": "Marca",                     // Nome do campo (obrigatorio)
  "situacao": 1,                       // 0=Inativo, 1=Ativo
  "placeholder": "Informe a marca do produto",
  "obrigatorio": false,
  "modulo": {
    "id": 1                            // ID do modulo (ex: Produtos) (obrigatorio)
  },
  "tipoCampo": {
    "id": 1                            // ID do tipo (texto, lista, etc.) (obrigatorio)
  },
  "opcoes": [                          // Para campos do tipo lista
    { "nome": "Ocean Drop" },
    { "nome": "Central Nutrition" },
    { "nome": "Mahta" }
  ],
  "tamanho": {
    "minimo": 1,
    "maximo": 100
  }
}
```

### POST /pedidos/vendas — Criar Pedido de Venda

```json
{
  "contato": {
    "id": 12345                        // ID do contato/cliente (obrigatorio)
  },
  "data": "2026-02-03",               // Data do pedido (obrigatorio)
  "dataSaida": "2026-02-04",          // Data de saida (obrigatorio)
  "dataPrevista": "2026-02-10",       // Data prevista de entrega (obrigatorio)
  "numero": 1001,
  "numeroLoja": "ML-5001234567",      // Numero do pedido no ML
  "situacao": {
    "id": 9                            // ID da situacao (ex: Em andamento)
  },
  "loja": {
    "id": 205294269                    // ID da loja ML
  },
  "itens": [                           // Itens do pedido (obrigatorio)
    {
      "produto": { "id": 123 },
      "quantidade": 2,
      "valor": 115.00,
      "desconto": 0
    }
  ],
  "parcelas": [                        // Parcelas de pagamento (obrigatorio)
    {
      "data": "2026-02-03",
      "valor": 230.00,
      "formaPagamento": { "id": 1 }
    }
  ],
  "transporte": {
    "frete": 0,
    "transportador": "Mercado Envios"
  },
  "observacoes": "Pedido Mercado Livre #5001234567",
  "desconto": {
    "valor": 0,
    "unidade": "REAL"
  }
}
```

### POST /nfe — Criar Nota Fiscal

```json
{
  "tipo": 1,                           // 0=Entrada, 1=Saida (obrigatorio)
  "contato": {
    "id": 12345                        // ID do contato (obrigatorio)
  },
  "numero": "6542",                    // Numero da NF-e (obrigatorio)
  "dataOperacao": "2026-02-03 10:00:00",  // Data de saida (obrigatorio)
  "naturezaOperacao": {
    "id": 1                            // ID da natureza de operacao (obrigatorio)
  },
  "finalidade": 1,                     // 1=Normal, 2=Complementar, 3=Ajuste, 4=Devolucao
  "loja": {
    "id": 205294269
  },
  "itens": [                           // Minimo 1 item
    {
      "produto": { "id": 123 },
      "quantidade": 2,
      "valor": 115.00
    }
  ],
  "parcelas": [
    {
      "data": "2026-02-03",
      "valor": 230.00,
      "formaPagamento": { "id": 1 }
    }
  ],
  "transporte": {
    "frete": 0
  },
  "observacoes": "NF-e ref. pedido ML #5001234567"
}
```

### POST /logisticas/objetos — Criar Objeto de Logistica

```json
{
  "pedidoVenda": {
    "id": 12345                        // ID do pedido de venda (obrigatorio)
  },
  "notaFiscal": {
    "id": 67890                        // ID da NF-e (obrigatorio)
  },
  "servico": {
    "id": 111                          // ID do servico de logistica (obrigatorio)
  },
  "rastreamento": {
    "codigo": "BR123456789BR"
  },
  "dimensoes": {
    "peso": 0.5,
    "altura": 10,
    "largura": 15,
    "comprimento": 20
  },
  "embalagem": {
    "id": 1
  },
  "dataSaida": "2026-02-04",
  "prazoEntregaPrevisto": 7,
  "fretePrevisto": 25.90,
  "valorDeclarado": 230.00,
  "avisoRecebimento": false,
  "maoPropria": false
}
```

---

## Plano de Expansao do bling_client.py

### Fase 1: Lancamento ML (Anuncios + Categorias)

**Objetivo:** Publicar os 50 produtos selecionados no Mercado Livre via API.

**Endpoints a implementar:**

```python
# Anuncios (7 metodos)
get_anuncios(**kwargs)
post_anuncios(body)
get_anuncio(idAnuncio)
put_anuncio(idAnuncio, body)
delete_anuncio(idAnuncio)
post_anuncio_publicar(idAnuncio)
post_anuncio_pausar(idAnuncio)

# Anuncios - Categorias (2 metodos)
get_anuncios_categorias(**kwargs)
get_anuncio_categoria(idCategoria)

# Categorias - Lojas (5 metodos)
get_categorias_lojas(**kwargs)
post_categorias_lojas(body)
get_categoria_loja(idCategoriaLoja)
put_categoria_loja(idCategoriaLoja, body)
delete_categoria_loja(idCategoriaLoja)

# Helpers
get_all_anuncios(idLoja, situacao=None)   # paginacao automatica
```

**Total: 14 metodos + 1 helper**

**Dependencias:** Nenhuma alem do que ja existe.

### Fase 2: Processamento de Pedidos (Vendas + NF-e)

**Objetivo:** Receber pedidos ML, gerar NF-e automaticamente, dar baixa em estoque/financeiro.

**Endpoints a implementar:**

```python
# Pedidos de Venda (14 metodos)
get_pedidos_vendas(**kwargs)
post_pedido_venda(body)
get_pedido_venda(idPedidoVenda)
put_pedido_venda(idPedidoVenda, body)
delete_pedido_venda(idPedidoVenda)
delete_pedidos_vendas(**kwargs)
patch_pedido_venda_situacao(idPedidoVenda, idSituacao)
post_pedido_venda_lancar_estoque(idPedidoVenda, idDeposito=None)
post_pedido_venda_estornar_estoque(idPedidoVenda)
post_pedido_venda_lancar_contas(idPedidoVenda)
post_pedido_venda_estornar_contas(idPedidoVenda)
post_pedido_venda_gerar_nfe(idPedidoVenda)
post_pedido_venda_gerar_nfce(idPedidoVenda)

# NF-e (11 metodos)
get_nfe(**kwargs)
post_nfe(body)
get_nfe_id(idNotaFiscal)
put_nfe(idNotaFiscal, body)
delete_nfe(**kwargs)
post_nfe_enviar(idNotaFiscal)
post_nfe_lancar_contas(idNotaFiscal)
post_nfe_estornar_contas(idNotaFiscal)
post_nfe_lancar_estoque(idNotaFiscal, idDeposito=None)
post_nfe_estornar_estoque(idNotaFiscal)

# Contatos - completar CRUD (8 metodos faltantes)
get_contato(idContato)
put_contato(idContato, body)
delete_contato(idContato)
delete_contatos(**kwargs)
get_contato_tipos(idContato)
get_contatos_consumidor_final()
patch_contato_situacao(idContato, body)
post_contatos_situacoes(body)

# Situacoes de Pedido (para gerenciar workflow)
get_situacoes_modulos()
get_situacoes_modulo(idModuloSistema)

# Helpers
get_all_pedidos_vendas(idLoja=None, situacao=None)   # paginacao automatica
```

**Total: 35 metodos + 1 helper**

**Dependencias:** Fase 1 concluida (anuncios publicados gerando pedidos).

### Fase 3: Otimizacao (Logisticas + Campos Customizados)

**Objetivo:** Automatizar etiquetas, rastreamento e enriquecimento de ficha tecnica.

**Endpoints a implementar:**

```python
# Campos Customizados (8 metodos)
get_campos_customizados_modulos()
get_campos_customizados_tipos()
get_campos_customizados_modulo(idModulo)
get_campo_customizado(idCampoCustomizado)
put_campo_customizado(idCampoCustomizado, body)
delete_campo_customizado(idCampoCustomizado)
post_campo_customizado(body)
patch_campo_customizado_situacao(idCampoCustomizado, body)

# Logisticas (5 metodos)
get_logisticas(**kwargs)
post_logistica(body)
get_logistica(idLogistica)
put_logistica(idLogistica, body)
delete_logistica(idLogistica)

# Logisticas - Etiquetas (1 metodo)
get_logisticas_etiquetas(**kwargs)

# Logisticas - Objetos (4 metodos)
get_logistica_objeto(idObjeto)
put_logistica_objeto(idObjeto, body)
delete_logistica_objeto(idObjeto)
post_logistica_objeto(body)

# Logisticas - Servicos (5 metodos)
get_logisticas_servicos(**kwargs)
post_logistica_servico(body)
get_logistica_servico(idLogisticaServico)
put_logistica_servico(idLogisticaServico, body)
patch_logistica_servico_situacao(idLogisticaServico, body)

# Categorias - Produtos (5 metodos, util para automacao)
get_categorias_produtos(**kwargs)
post_categoria_produto(body)
get_categoria_produto(idCategoriaProduto)
put_categoria_produto(idCategoriaProduto, body)
delete_categoria_produto(idCategoriaProduto)

# Produtos - Variacoes (3 metodos, para anuncios com variacao)
get_produto_variacoes(idProdutoPai)
post_produtos_variacoes_gerar_combinacoes(body)
patch_produto_variacoes_atributos(idProdutoPai, body)
```

**Total: 31 metodos**

**Dependencias:** Fase 2 concluida (pedidos sendo processados).

---

### Resumo do Plano

| Fase | Foco | Metodos | Acumulado | Cobertura Estimada |
|------|------|:-------:|:---------:|:------------------:|
| Atual | Produtos, Estoques, Lojas | 21+2 helpers | 23 | ~8% |
| Fase 1 | Anuncios + Categorias-Lojas | 14+1 helper | 38 | ~15% |
| Fase 2 | Pedidos + NF-e + Contatos | 35+1 helper | 74 | ~29% |
| Fase 3 | Logisticas + Campos Custom. | 31 | 105 | ~41% |

> **Nota:** Os ~59% restantes cobrem modulos financeiros (Caixas, Contas a Pagar/Receber, Borderos), NFC-e, NFS-e, Contratos, Ordens de Producao, Propostas Comerciais e outros que nao sao necessarios para a operacao ML da NRAIZES no curto prazo.

---

## Referencias

- **OpenAPI Spec:** Bling API v3.0 (documento fonte deste guia)
- **Implementacao atual:** `src/bling_client.py` (21 endpoints + 2 helpers + auth)
- **Boas praticas ML:** `docs/BOAS_PRATICAS_ML_BLING.md`
- **Documentacao oficial:** https://developer.bling.com.br/
- **Base URL producao:** https://api.bling.com.br/Api/v3
