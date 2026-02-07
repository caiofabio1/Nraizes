# Guia Rapido do Vendedor -- Bling + NRAIZES

> Versao: Fevereiro 2026 | Sistema: Bling ERP v3 + Dashboard NRAIZES

---

## Visao Geral do Sistema

```
Bling ERP (fonte da verdade)
    |
    |-- WooCommerce (loja online nraizes.com.br)     Preco base (1.00x)
    |-- Google Shopping (anuncios)                    Preco base (1.00x)
    |-- Mercado Livre (marketplace)                   Preco +15% (1.15x)
    |
    +-- Dashboard NRAIZES (localhost:5000)
        |-- Propostas de preco (IA)
        |-- Descricoes de produto (IA)
        |-- EANs / codigos de barra
        |-- Sincronizacao com Bling
```

**Principio fundamental:** O Bling e o sistema central. Todo produto, preco e estoque
comeca no Bling e sincroniza para os outros canais.

---

## 1. Rotina Diaria

### 1.1 Abrir o Bling

Acesse: **https://www.bling.com.br** com as credenciais da loja.

Tela inicial -- confira:
- Pedidos novos (topo do menu lateral)
- Alertas de estoque baixo
- Notificacoes de integracao

### 1.2 Processar Pedidos

Caminho no Bling: **Vendas > Pedidos de Venda**

| Passo | Acao | Detalhe |
|-------|------|---------|
| 1 | Verificar pedidos novos | Filtro: "Em aberto" ou "Aprovado" |
| 2 | Conferir pagamento | Status do pagamento no detalhe do pedido |
| 3 | Separar produtos | Verificar disponibilidade em estoque |
| 4 | Emitir NF-e | Botao "Gerar Nota" dentro do pedido |
| 5 | Despachar | Gerar etiqueta de frete (Correios/transportadora) |
| 6 | Atualizar status | Marcar como "Enviado" com codigo de rastreio |

**Dica:** Pedidos do WooCommerce entram automaticamente no Bling. Pedidos do
Mercado Livre tambem sincronizam pela integracao. Voce NAO precisa criar
pedidos manualmente para vendas online.

### 1.3 Conferir Estoque

Caminho no Bling: **Produtos > Estoque**

- Deposito principal: **Geral** (ID 14888142994)
- Filtrar por "Saldo zerado" para ver o que precisa repor
- Toda entrada de mercadoria deve ser registrada como "Entrada" (tipo E)

---

## 2. Cadastrar um Novo Produto

Caminho no Bling: **Produtos > Novo Produto**

### 2.1 Informacoes Obrigatorias

| Campo | O que preencher | Exemplo |
|-------|-----------------|---------|
| **Nome** | Nome completo e descritivo | Omega 3 DHA Ocean Drop 60 Capsulas |
| **Codigo (SKU)** | Formato: `[MARCA]-[CAT]-[PRODUTO]` (max 15 chars) | OCE-CAP-OMEGA3DHA |
| **Tipo** | Sempre "Produto" (P) | P |
| **Formato** | "Simples" (S) para produtos sem variacao | S |
| **Situacao** | "Ativo" (A) | A |
| **Unidade** | UN (unidade) | UN |
| **Preco de venda** | Preco base da loja (sem markup de marketplace) | 179.10 |
| **Preco de custo** | Quanto pagamos ao fornecedor | 105.00 |

### 2.2 Informacoes Importantes (preencher sempre que possivel)

| Campo | O que preencher |
|-------|-----------------|
| **GTIN/EAN** | Codigo de barras do produto (13 digitos) |
| **Peso bruto (kg)** | Peso para calculo de frete |
| **Dimensoes (cm)** | Largura x Altura x Profundidade (frete) |
| **NCM** | Codigo fiscal do produto |
| **Descricao curta** | Frase de venda (max 150 caracteres) |
| **Descricao complementar** | Descricao longa com beneficios e ingredientes |
| **Imagem** | Foto do produto em alta resolucao |
| **Categoria** | Selecionar da arvore de categorias do Bling |

### 2.3 Formato do SKU

Seguimos o padrao semantico:

```
[MARCA 3 letras]-[CATEGORIA 2-3 letras]-[PRODUTO]

Exemplos:
  OCE-CAP-OMEGA3DHA    (Ocean Drop, Capsulas, Omega 3 DHA)
  CEN-CRE-COLLCRE      (Central Nutrition, Creatina, Collcreatine)
  MAH-SUP-SUPERFOOD    (Mahta, Superfoods, Superfood)
  AVA-SAB-LAVSAB400    (Avatim, Sabonete, Lavanda 400ml)
  XTR-DIV-BIOSHOT      (Xtratus, Diversos, Bio Shot)
```

**Caracteres proibidos no nome:** O Bling rejeita `?`, `:`, `(`, `)` em nomes
de produto. Usar apenas letras, numeros, virgula, ponto e hifen.

### 2.4 Regra de Preco Minimo

Nunca cadastrar um produto com margem abaixo de 20% sobre o custo.

```
Formula:   Preco minimo = Preco de custo / 0.80

Exemplo:   Custo R$100.00 -> Preco minimo R$125.00
           Custo R$50.00  -> Preco minimo R$62.50
```

---

## 3. Vincular Produto a uma Loja

Depois de cadastrar o produto no Bling, ele precisa ser **vinculado** a cada
canal de venda para aparecer naquela loja.

Caminho no Bling: **Produtos > [selecionar produto] > aba "Lojas Virtuais"**

### 3.1 Lojas Configuradas

| Loja | ID Bling | Preco | Quando vincular |
|------|----------|-------|-----------------|
| **WooCommerce** | 205326820 | Mesmo preco base | Todo produto novo |
| **Google Shopping** | 205282664 | Mesmo preco base | Produtos com imagem e EAN |
| **Mercado Livre** | 205294269 | Preco base + 15% | Produtos selecionados (margem >= 25% apos taxas) |

### 3.2 Como Vincular Manualmente (pela interface do Bling)

1. Abra o produto no Bling
2. Va na aba **"Lojas Virtuais"** (ou "Multilojas")
3. Clique em **"Vincular loja"**
4. Selecione a loja (WooCommerce, Google Shopping ou Mercado Livre)
5. Preencha o **codigo** (mesmo SKU do produto)
6. Preencha o **preco da loja**:
   - WooCommerce: mesmo preco base
   - Google Shopping: mesmo preco base
   - Mercado Livre: preco base x 1.15 (arredondar para cima)
7. Salvar

### 3.3 Calculo de Preco para Mercado Livre

```
Preco ML = Preco base x 1.15

Exemplos:
  Base R$100.00 -> ML R$115.00
  Base R$229.00 -> ML R$263.35
  Base R$98.10  -> ML R$112.82
```

O multiplicador de 15% cobre as taxas do Mercado Livre. Nunca vincular ao ML
sem esse ajuste -- voce perderia margem.

### 3.4 Vincular em Lote (via script)

Para vincular muitos produtos de uma vez, use os scripts no terminal:

```bash
# Vincular ao WooCommerce (primeiro confira em dry-run)
python src/vincular_woocommerce.py           # Dry-run (simulacao)
python src/vincular_woocommerce.py --executar # Executa de verdade

# Vincular ao Google Shopping
python src/vincular_woocommerce.py --loja 205282664 --executar

# Vincular top 50 ao Mercado Livre
python tools/vincular_produtos_ml.py           # Dry-run
python tools/vincular_produtos_ml.py --executar # Executa

# Ver diagnostico sem alterar nada
python src/vincular_woocommerce.py --status
python tools/vincular_produtos_ml.py --status
```

---

## 4. Alterar Precos

### 4.1 Alterar Preco de Um Produto (manual)

No Bling: **Produtos > [selecionar produto] > Editar**

1. Altere o campo **"Preco"** (preco base)
2. Se o produto estiver vinculado a lojas, va na aba **"Lojas Virtuais"**
3. Atualize o preco em cada loja vinculada:
   - WooCommerce: mesmo preco novo
   - Google Shopping: mesmo preco novo
   - Mercado Livre: preco novo x 1.15
4. Salvar

**ATENCAO:** Se voce alterar so o preco base e nao atualizar os precos das
lojas, o WooCommerce pode ficar com preco diferente do Bling.

### 4.2 Alterar Precos com Inteligencia (via Dashboard)

O dashboard da NRAIZES usa IA para sugerir ajustes de preco baseados em:
- Dados de vendas dos ultimos 30 dias
- Precos de concorrentes no Mercado Livre
- Margem atual vs. margem alvo
- Demanda e trafego (Google Analytics)

**Como usar:**

```bash
# 1. Abrir o dashboard
python src/web_dashboard.py
# Acesse: http://localhost:5000
```

2. Na aba **"Smart Pricing"** voce vera as propostas de preco
3. Cada proposta mostra:
   - Preco atual vs. preco sugerido
   - Margem atual vs. nova margem
   - Motivo da sugestao
   - Nivel de confianca (0 a 100%)
4. **Aprovar** as propostas que fazem sentido
5. **Rejeitar** as que nao fazem
6. Clicar em **"Aplicar Aprovados"** para sincronizar com Bling + WooCommerce

### 4.3 Regras de Seguranca de Preco (automaticas)

O sistema impede alteracoes perigosas automaticamente:

| Regra | Limite | O que acontece |
|-------|--------|----------------|
| Margem minima | 20% | Preco nunca fica abaixo de custo + 20% |
| Variacao maxima | 15% por ajuste | Preco nao muda mais de 15% de uma vez |
| Cooldown | 3 dias | Mesmo produto nao tem preco ajustado 2x em 3 dias |

---

## 5. Gerenciar Estoque

### 5.1 Dar Entrada de Estoque (recebimento de mercadoria)

Caminho no Bling: **Estoque > Lancar movimentacao**

| Campo | Valor |
|-------|-------|
| Tipo | **Entrada** (E) |
| Deposito | **Geral** |
| Produto | Buscar pelo nome ou SKU |
| Quantidade | Quantidade recebida |
| Observacao | Nota fiscal do fornecedor / data recebimento |

### 5.2 Baixa de Estoque

A baixa de estoque e **automatica** quando:
- Um pedido e faturado (NF-e emitida) no Bling
- Uma venda e confirmada no WooCommerce/ML e sincroniza com o Bling

**Nao faca baixa manual** de estoque para vendas online -- isso causaria
estoque negativo porque a integracao ja faz a baixa.

### 5.3 Ajuste de Inventario (contagem fisica)

Se a contagem fisica diferir do sistema:

1. Caminho: **Estoque > Balanco** (ou Ajuste de Estoque)
2. Busque o produto
3. Informe a quantidade real contada
4. O Bling calcula a diferenca e gera a movimentacao de ajuste
5. Adicionar observacao explicando o motivo do ajuste

---

## 6. Emitir Nota Fiscal (NF-e)

### 6.1 A partir de um Pedido

1. Abra o pedido em **Vendas > Pedidos de Venda**
2. Clique em **"Gerar Nota Fiscal"**
3. Confira:
   - Dados do cliente (CPF/CNPJ, endereco)
   - Produtos e quantidades
   - NCM de cada produto
   - CFOP (normalmente 5102 para venda dentro do estado, 6102 para fora)
4. Clique em **"Emitir"**
5. Aguarde a autorizacao da SEFAZ
6. Feito -- o XML e o DANFE ficam salvos no Bling

### 6.2 Campos Fiscais Importantes

| Campo | O que e | Onde encontrar |
|-------|---------|----------------|
| **NCM** | Classificacao fiscal do produto | Cadastro do produto no Bling |
| **CFOP** | Codigo da operacao fiscal | 5102 (dentro SP), 6102 (fora SP) |
| **CSOSN** | Codigo da situacao tributaria (Simples Nacional) | Configuracao fiscal do Bling |
| **Origem** | Origem da mercadoria | 0 = Nacional, 1 = Importado |

---

## 7. Dashboard NRAIZES (Painel de Controle)

### 7.1 Como Acessar

```bash
# No terminal, na pasta do projeto
python src/web_dashboard.py

# Abra no navegador:
http://localhost:5000
```

### 7.2 Abas do Dashboard

| Aba | Para que serve | Frequencia de uso |
|-----|----------------|-------------------|
| **Smart Pricing** | Ver e aprovar sugestoes de preco da IA | Diario |
| **Enrichment** | Ver e aprovar descricoes geradas pela IA | Semanal |
| **Precos** | Ver ajustes de preco baseados em regras | Semanal |
| **EANs** | Sincronizar codigos de barra com o Bling | Quando necessario |
| **Sync** | Log de todas as sincronizacoes feitas | Para conferencia |

### 7.3 Indicadores no Topo (KPIs)

| Indicador | O que significa | Acao se estiver ruim |
|-----------|-----------------|----------------------|
| Produtos ativos | Total de produtos ativos no catalogo | -- |
| Sem EAN | Produtos sem codigo de barras | Buscar EAN na aba EANs |
| Propostas IA | Descricoes pendentes de revisao | Revisar na aba Enrichment |
| Precos mercado | Produtos com dados de concorrentes | -- |
| Propostas preco | Sugestoes de preco para revisar | Revisar na aba Smart Pricing |
| Aprovados | Precos aprovados esperando aplicacao | Clicar "Aplicar Aprovados" |

---

## 8. Comandos Uteis no Terminal

Para vendedores que tem acesso ao terminal (computador da loja):

### Consultas rapidas

```bash
# Ver lojas configuradas no Bling
python tools/list_bling_lojas.py

# Ver status de vinculacao WooCommerce
python src/vincular_woocommerce.py --status

# Ver selecao de produtos do Mercado Livre
python tools/vincular_produtos_ml.py --status
```

### Operacoes de preco

```bash
# Abrir dashboard de precos
python src/web_dashboard.py

# Gerar novas sugestoes de preco (IA analisa vendas + concorrencia)
# (depois aprovar no dashboard)
python src/smart_pricing.py analyze
```

### Operacoes de produto

```bash
# Gerar descricoes com IA para produtos sem descricao
python src/enrichment.py

# Buscar EANs para produtos sem codigo de barras
python src/ean_finder.py
```

### Em caso de erro de autenticacao

```bash
# Renovar token do Bling (se der erro 401)
python scripts/refresh_tokens.py

# Se o refresh token tambem expirou (raro):
python tools/bling_oauth_helper.py
# Abre navegador -> autorizar -> copiar codigo -> colar no terminal
```

---

## 9. Tabela de Multiplicadores por Canal

Quando for definir preco em qualquer canal, use esta referencia:

| Canal | Multiplicador | Exemplo (base R$100) | Motivo |
|-------|---------------|----------------------|--------|
| WooCommerce | 1.00x | R$100.00 | Preco base (venda direta) |
| Google Shopping | 1.00x | R$100.00 | Preco base (trafego pago) |
| Mercado Livre | 1.15x | R$115.00 | Taxas ML (~11-16%) |
| Shopee | 1.12x | R$112.00 | Taxas Shopee (~12%) |
| Amazon | 1.18x | R$118.00 | Taxas Amazon (~15-20%) |
| Instagram | 1.05x | R$105.00 | Custo de atendimento manual |
| WhatsApp | 1.00x | R$100.00 | Venda direta sem taxa |

---

## 10. Checklist Diario do Vendedor

```
MANHA (abertura)
[ ] Acessar Bling -> verificar pedidos novos
[ ] Conferir pagamentos aprovados
[ ] Separar e embalar pedidos para despacho
[ ] Emitir NF-e dos pedidos aprovados
[ ] Gerar etiquetas de frete
[ ] Despachar com transportadora/Correios

TARDE
[ ] Verificar mensagens de clientes (ML, WhatsApp, WooCommerce)
[ ] Conferir estoque fisico dos produtos mais vendidos
[ ] Dar entrada de mercadoria recebida (se houver)
[ ] Abrir dashboard (localhost:5000) -> revisar propostas de preco
[ ] Aprovar/rejeitar sugestoes e clicar "Aplicar Aprovados"

SEMANAL
[ ] Revisar descricoes de produto geradas pela IA (aba Enrichment)
[ ] Verificar produtos sem imagem ou sem EAN
[ ] Conferir balanco de estoque vs. sistema
[ ] Verificar se ha novos produtos para vincular nas lojas
```

---

## 11. Problemas Comuns e Solucoes

| Problema | Causa provavel | Solucao |
|----------|----------------|---------|
| Produto nao aparece no WooCommerce | Nao esta vinculado a loja | Vincular na aba "Lojas Virtuais" do produto no Bling |
| Preco diferente entre Bling e loja | Preco da loja nao foi atualizado | Editar o preco na vinculacao da loja (nao so o preco base) |
| Erro 401 no terminal | Token do Bling expirou | Rodar `python scripts/refresh_tokens.py` |
| Pedido nao aparece no Bling | Integracao pode estar pausada | Verificar em Bling > Preferencias > Integracoes |
| Estoque negativo | Baixa manual + baixa automatica | Fazer ajuste de inventario no Bling |
| Dashboard nao abre | Servidor nao esta rodando | Rodar `python src/web_dashboard.py` no terminal |
| "Produto ja vinculado" ao vincular | Vinculo ja existe | Normal -- nenhuma acao necessaria |
| NF-e rejeitada | Dados fiscais incompletos | Verificar NCM, CFOP e dados do cliente |

---

## 12. Contatos e Suporte

| Assunto | Onde resolver |
|---------|---------------|
| Duvidas sobre Bling | Central de Ajuda Bling: https://ajuda.bling.com.br |
| Problemas com WooCommerce | Verificar em Bling > Integracoes > WooCommerce |
| Problemas com Mercado Livre | Verificar em Bling > Integracoes > Mercado Livre |
| Problemas com scripts/dashboard | Contatar o responsavel tecnico |
| Problemas com NF-e / SEFAZ | Verificar certificado digital e dados fiscais |

---

## Resumo Visual do Fluxo

```
FORNECEDOR                         CLIENTE
    |                                  ^
    v                                  |
[Receber mercadoria]          [Pedido entra no Bling]
    |                                  |
    v                                  v
[Entrada de estoque       [Conferir pagamento]
 no Bling (tipo E)]               |
    |                              v
    v                     [Separar produtos]
[Cadastrar produto novo          |
 (se for novo)]                  v
    |                     [Emitir NF-e]
    v                            |
[Vincular as lojas]              v
    |                     [Gerar etiqueta frete]
    v                            |
[Produto aparece                 v
 no site/ML/Google]       [Despachar]
                                 |
                                 v
                          [Atualizar status
                           + codigo rastreio]
```
