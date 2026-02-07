# Boas Praticas: Cadastro de Produtos no Mercado Livre via Bling

> Levantamento: Fevereiro 2026 | Baseado nas regras vigentes do ML e integracao Bling v3

---

## 1. Visao Geral do Fluxo

```
Bling (cadastro completo)
  |
  +-- Categorias vinculadas ao ML
  +-- Campos customizados mapeados
  +-- Fotos, EAN, ficha tecnica
  |
  v
Integracao Bling -> Mercado Livre
  |
  v
Anuncio publicado no ML
  |
  +-- Titulo otimizado (SEO ML)
  +-- Ficha tecnica preenchida (atributos obrigatorios)
  +-- Fotos em alta resolucao
  +-- Descricao rica e detalhada
  +-- Preco com multiplicador 1.15x
```

**Principio:** O ML usa os dados do Bling para criar o anuncio. Quanto mais
completo o cadastro no Bling, melhor o anuncio no ML.

---

## 2. Campos Obrigatorios e Seu Impacto

### 2.1 Campos que o ML EXIGE (bloqueiam publicacao se vazios)

| Campo | Onde preencher no Bling | Impacto no ML |
|-------|-------------------------|---------------|
| **Titulo** | Nome do produto | Titulo do anuncio (principal fator de busca) |
| **Preco** | Preco da vinculacao com a loja ML | Preco de venda (base x 1.15) |
| **Estoque** | Movimentacao de estoque (deposito Geral) | Quantidade disponivel |
| **Categoria** | Vinculacao de categorias multiloja | Onde o produto aparece no ML |
| **Condicao** | Campo no produto (Novo/Usado) | Filtro de busca |
| **Imagem** (min. 1) | Cadastro do produto, aba imagens | Foto principal do anuncio |

### 2.2 Campos Altamente Recomendados (impactam ranking)

| Campo | Onde preencher no Bling | Impacto no ML |
|-------|-------------------------|---------------|
| **GTIN/EAN** | Cadastro do produto, campo GTIN | Identidade do produto. Obrigatorio para catalogo. Melhora ranking |
| **Marca** | Campo customizado ou descricao | Filtro de busca, ficha tecnica |
| **Descricao complementar** | Descricao complementar do produto | Descricao longa do anuncio |
| **Peso bruto (kg)** | Cadastro do produto, aba logistica | Calculo de frete (Mercado Envios) |
| **Dimensoes (cm)** | Largura x Altura x Profundidade | Calculo de frete e custo de armazenamento |
| **NCM** | Cadastro do produto, campo NCM | Obrigatorio para Mercado Livre Full (Fulfillment) |
| **Campos customizados** | Campos customizados do Bling | Ficha tecnica do anuncio (atributos) |

### 2.3 Campos Customizados = Ficha Tecnica do ML

Os atributos da ficha tecnica do ML (marca, formato, tipo, vegano, sem gluten
etc.) sao mapeados como **campos customizados** no Bling.

**Como configurar:**

1. No Bling: **Cadastros > Categorias de produtos**
2. Clicar em **"Vincular categorias multiloja"**
3. Selecionar **Mercado Livre**
4. Vincular cada categoria Bling a categoria equivalente no ML
5. Apos vincular, voltar a categoria e clicar nela
6. Na secao **"Campos customizados Bling"**, o sistema mostra os campos
   exigidos pela categoria ML (com * = obrigatorio)
7. Criar os campos customizados conforme solicitado
8. **NAO renomear** campos criados automaticamente pelo Bling
9. Se um campo similar ja existe de outra categoria, usar "Mapear"

**Campos customizados tipicos para a NRAIZES:**

| Categoria ML | Campos obrigatorios |
|-------------|---------------------|
| Suplementos Alimentares | Marca, Formato (capsulas/po/liquido), Tipo, Sabor, Peso liquido, Vegano (S/N) |
| Cosmeticos/Skincare | Marca, Tipo de pele, Volume, Genero, Linha, Beneficio |
| Chas e Infusoes | Marca, Tipo de cha, Peso, Sabor, Forma (sache/granel/soluvel) |
| Oleos Essenciais | Marca, Volume, Tipo de oleo, Uso (aromaterapia/topico) |
| Velas e Aromaterapia | Marca, Peso, Fragancia, Material, Duracao |

---

## 3. Titulo do Anuncio (Campo mais importante para SEO no ML)

### 3.1 Regras do ML para titulos

- **Limite:** 60 caracteres (tudo alem e cortado nos resultados de busca)
- **Estrutura PMME:** Produto + Marca + Modelo + Especificacao
- **Sem informacoes de frete/pagamento:** Nao colocar "Frete Gratis", "12x sem juros"
- **Sem condicao:** Nao colocar "Novo" (ja tem campo separado)
- **Sem variacoes:** Nao listar cores/tamanhos (usar variacoes do ML)
- **Sem caracteres especiais excessivos:** Evitar !, ?, #, @

### 3.2 Exemplos para a NRAIZES

**RUIM (como esta hoje em varios produtos):**
```
SUPERFOODS AMAZÔNICOS 840G - MAHTA
PROTEINA VEGETAL 450G - OCEAN DROP
GUARDIAN CENTRAL NUTRITION (CX. C/ 30 SACHÊS) Sabor Limao
```

**BOM (otimizado para ML):**
```
Superfoods Amazonicos Mahta 840g Acai Camu-Camu Cacau
Proteina Vegetal Ocean Drop 450g Chocolate Vegana
Guardian Aminoacidos Central Nutrition 30 Saches Limao
```

### 3.3 Regra pratica para titulos ML

```
[Produto] [Marca] [Quantidade/Peso] [Variacao principal]

Exemplos NRAIZES:
  Omega 3 DHA Ocean Drop 60 Capsulas 1000mg
  Creatina Collcreatine Central Nutrition 500g
  Serum Facial Acido Hialuronico Novas Raizes 30ml
  Cafe Funcional Coffee Mahta Cacau Selvagem 220g
  Oleo Essencial Alecrim Laszlo 10ml Puro
```

**IMPORTANTE:** O titulo no Bling vira o titulo no ML. Se o nome do produto
no Bling estiver em CAIXA ALTA ou com formatacao ruim, o anuncio vai sair
assim. Corrigir ANTES de vincular ao ML.

---

## 4. Descricao do Produto

### 4.1 O que o ML espera

- Texto fluido e informativo (nao apenas especificacoes)
- Sem HTML (o ML nao renderiza tags)
- Sem informacoes de contato, links externos ou precos
- Sem mencionar outros marketplaces
- Original (nao copiar de outros anuncios)

### 4.2 Estrutura ideal para produtos NRAIZES

```
PARAGRAFO 1 - Apresentacao (2-3 linhas)
O que e o produto, para que serve, beneficio principal.

PARAGRAFO 2 - Beneficios (3-5 itens)
- Beneficio 1 e como impacta o cliente
- Beneficio 2
- Beneficio 3

PARAGRAFO 3 - Composicao/Ingredientes
Ingredientes naturais, certificacoes (vegano, sem gluten, organico).

PARAGRAFO 4 - Modo de uso
Instrucoes claras, frequencia, dosagem.

PARAGRAFO 5 - Informacoes adicionais
Peso liquido, validade, fabricante, conservacao.
```

### 4.3 Tamanho ideal

- **Minimo:** 300 palavras (abaixo disso o ML considera "incompleto")
- **Ideal:** 400-600 palavras
- **Maximo:** Sem limite, mas evitar enrolacao

### 4.4 Palavras-chave na descricao

O algoritmo do ML indexa a descricao. Incluir termos de busca naturalmente:

```
Para suplementos:  suplemento natural, capsulas veganas, sem gluten,
                   importado, alta concentracao, biodisponivel

Para cosmeticos:   cosmetico natural, organico, vegano, cruelty-free,
                   hidratante, nutritivo, pele sensivel

Para chas:         cha natural, ervas, infusao, organico, sem agrotoxicos,
                   artesanal, granel

Para superfoods:   superfood, amazonico, proteina vegetal, antioxidante,
                   energia natural, imunidade
```

---

## 5. Imagens

### 5.1 Especificacoes tecnicas

| Requisito | Valor |
|-----------|-------|
| **Resolucao minima** | 1200 x 1200 px (quadrada) ou 1200 x 1540 px (vertical) |
| **Resolucao minima absoluta** | Lado menor >= 500px |
| **DPI** | 72 dpi |
| **Peso minimo** | ~600 KB |
| **Modo de cor** | RGB |
| **Formato** | JPG ou PNG |
| **Quantidade** | Minimo 1, ideal 5-10 |

### 5.2 Regras de conteudo

- **Foto 1 (principal):** Produto sozinho, fundo branco ou neutro, centralizado, ocupando ~95% da imagem
- **Fotos 2-5:** Diferentes angulos, detalhes, rotulo/ingredientes
- **Fotos 6+:** Produto em contexto de uso, embalagem, comparativo de tamanho
- **PROIBIDO:** Textos promocionais, logos, informacoes de contato, marca d'agua, precos, montagens com varios produtos

### 5.3 Situacao atual NRAIZES

4 dos 50 produtos selecionados para ML estao **sem imagem**:
- MUSHROOM LATA 220G - MUSHIN
- Superfoods Amazonicos Mahta Acai Camu-Camu 360g
- Barrinha Vanilla Grape Mushin (Cx. 12 Unid.)
- COFFEE MAHTA 220G

**Acao:** Fotografar estes 4 produtos ou obter imagens dos fornecedores
antes de vincular ao ML. Anuncio sem imagem = anuncio invisivel.

---

## 6. EAN/GTIN (Codigo de Barras)

### 6.1 Por que e importante no ML

- **Identificacao unica:** O ML usa o EAN para agrupar ofertas do mesmo produto
- **Catalogo:** Muitas categorias exigem EAN para publicacao via catalogo
- **Ranking:** Produtos com EAN tendem a ranquear melhor
- **Buy Box:** EAN e requisito para competir no "Buy Box" (anuncio principal)

### 6.2 Formato

- EAN-13: 13 digitos (padrao brasileiro)
- UPC: 12 digitos (padrao americano)
- ISBN: para livros

### 6.3 Onde encontrar

1. Embalagem fisica do produto (codigo de barras)
2. Nota fiscal do fornecedor (campo GTIN)
3. Site do fabricante
4. Open Food Facts (https://world.openfoodfacts.org/)
5. Script do projeto: `python src/ean_finder.py`

### 6.4 Como cadastrar no Bling

Cadastro do produto > campo **"GTIN/EAN"** > inserir os 13 digitos

---

## 7. Categorias: Mapeamento Bling -> ML

### 7.1 Categorias principais da NRAIZES no ML

| Produtos NRAIZES | Categoria ML sugerida |
|------------------|----------------------|
| Suplementos (Ocean Drop, Central Nutrition) | Saude > Suplementos Alimentares > Vitaminas e Suplementos |
| Proteinas vegetais | Saude > Suplementos Alimentares > Proteinas |
| Creatina | Esportes e Fitness > Suplementos > Creatinas |
| Pre-treinos (Xtratus) | Esportes e Fitness > Suplementos > Pre-Treinos |
| Superfoods (Mahta) | Alimentos e Bebidas > Alimentos Saudaveis > Superfoods |
| Cafes funcionais | Alimentos e Bebidas > Cafe, Cha e Infusoes |
| Cosmeticos (Solo Fertil) | Beleza e Cuidado Pessoal > Cuidado da Pele |
| Oleos vegetais/essenciais | Beleza e Cuidado Pessoal > Aromaterapia |
| Colageno (Miya) | Saude > Suplementos Alimentares > Colageno |
| Propolis | Saude > Suplementos Alimentares > Propolis |
| Avatim (aromaterapia) | Casa, Moveis e Decoracao > Aromaterapia |
| Mushin (cogumelos) | Alimentos e Bebidas > Alimentos Saudaveis |

### 7.2 Como vincular no Bling

1. **Cadastros > Categorias de produtos > Vincular categorias multiloja**
2. Selecionar **Mercado Livre** como loja
3. Para cada categoria NRAIZES, navegar na arvore do ML e selecionar
4. Salvar
5. Voltar na categoria e preencher os campos customizados obrigatorios (*)

**ATENCAO:** O `category_map.json` do projeto ja tem 88 categorias mapeadas
com IDs do Bling. Verificar se as categorias ML estao vinculadas no Bling.

---

## 8. Precificacao para o ML

### 8.1 Custos do Mercado Livre

| Item | Valor tipico |
|------|-------------|
| Taxa de venda (comissao) | 11% a 16% (varia por categoria e reputacao) |
| Frete (Mercado Envios) | Custo variavel. Vendedor paga se oferecer frete gratis |
| Anuncio Premium (exposicao maxima) | Taxa mais alta (~16%) |
| Anuncio Classico (exposicao normal) | Taxa mais baixa (~11%) |

### 8.2 Multiplicador NRAIZES

O sistema usa **1.15x** (15%) sobre o preco base para cobrir taxas do ML.

```
Preco ML = Preco base Bling x 1.15

Exemplo: Base R$100.00 -> ML R$115.00
```

### 8.3 Validacao de margem

Antes de vincular, o sistema valida:
- **Margem ML minima:** 25% apos aplicar o multiplicador
- **Formula:** (Preco_ML - Custo) / Preco_ML >= 25%

Produtos com margem abaixo de 25% apos taxas ML nao sao elegiveis.

### 8.4 Regras de preco do ML

- Nao e permitido preco diferente entre variacoes do mesmo anuncio (salvo via UP/Family ID)
- Preco promocional: usar campo "Preco promocional" no Bling, nao alterar o preco base
- Parcelamento: configurado nas opcoes de pagamento do vendedor ML, nao no anuncio

---

## 9. Configuracao da Integracao Bling -> ML

### 9.1 Regras de exportacao recomendadas

No Bling: **Preferencias > Integracoes > Mercado Livre > Regras de operacao**

| Regra | Configuracao recomendada |
|-------|--------------------------|
| Exportar produtos | Somente vinculados (nao exportar tudo automaticamente) |
| Atualizar preco | Automatico (quando alterado no Bling) |
| Atualizar estoque | Automatico (quando movimentado no Bling) |
| Atualizar dimensoes | Ativado (usar dimensoes do produto Bling) |
| Produtos sem estoque | Pausar anuncio no ML |
| Tipo de anuncio | Premium (maior exposicao, taxa ~16%) para produtos premium. Classico para margem apertada |
| Frete gratis | Configurar conforme estrategia (pode ser por produto ou por valor minimo) |

### 9.2 Sincronizacao de estoque

- O Bling sincroniza estoque automaticamente para o ML
- Toda venda no ML gera pedido no Bling e da baixa no estoque
- Toda venda no WooCommerce tambem da baixa, refletindo no ML
- **CUIDADO:** Estoque e compartilhado entre canais. Se tem 5 unidades,
  5 ficam disponiveis no WooCommerce E 5 no ML simultaneamente.
  Uma venda em um canal reduz para ambos.

---

## 10. Checklist Pre-Publicacao ML

Antes de vincular cada produto ao Mercado Livre, verificar:

```
DADOS BASICOS
[ ] Nome/titulo otimizado (formato PMME, max 60 chars, sem CAIXA ALTA)
[ ] SKU preenchido
[ ] Preco base correto (preco ML sera base x 1.15)
[ ] Preco de custo preenchido (para controle de margem)
[ ] Margem apos taxas ML >= 25%

IDENTIFICACAO
[ ] EAN/GTIN preenchido (13 digitos)
[ ] Marca preenchida
[ ] NCM preenchido (obrigatorio para Full)

LOGISTICA
[ ] Peso bruto (kg) preenchido
[ ] Dimensoes (cm) preenchidas (LxAxP)
[ ] Estoque > 0

CONTEUDO
[ ] Foto principal: min 1200x1200px, fundo branco/neutro
[ ] Fotos adicionais: 3-5 fotos de angulos diferentes
[ ] Descricao complementar: min 300 palavras, sem HTML
[ ] Descricao curta preenchida

INTEGRACAO
[ ] Categoria Bling vinculada a categoria ML
[ ] Campos customizados obrigatorios (*) preenchidos
[ ] Produto vinculado a loja ML (ID 205294269) no Bling
```

---

## 11. Erros Comuns e Como Evitar

| Erro | Causa | Solucao |
|------|-------|---------|
| "Categoria invalida" | Categoria Bling nao vinculada ao ML | Vincular em Cadastros > Categorias > Multiloja |
| "Atributo obrigatorio" | Campo customizado vazio | Preencher campos com * na categoria |
| "GTIN invalido" | EAN com digito errado ou formato incorreto | Verificar checksum. Usar EAN-13 (13 digitos) |
| "Titulo muito longo" | Nome do produto > 60 chars | Reduzir titulo mantendo palavras-chave |
| "Imagem invalida" | Resolucao baixa ou formato errado | Usar JPG/PNG min 1200x1200px |
| Anuncio pausado | Estoque zerado no Bling | Dar entrada de estoque |
| Preco desatualizado | Alterou preco base mas nao da loja ML | Atualizar preco na vinculacao da loja |
| Produto nao exporta | Nao vinculado a loja ML no Bling | Criar vinculo: Produto > Lojas Virtuais > ML |

---

## 12. Impacto no Enrichment da IA (Ajustes Necessarios)

O script de enrichment (`src/enrichment.py`) precisa ser ajustado para gerar
conteudo compativel com as regras do ML:

### Titulo (seo_title -> titulo ML)
- ATUAL: Otimizado para Google (Yoast SEO, max 60 chars)
- AJUSTE ML: Usar formato PMME (Produto + Marca + Modelo + Especificacao)
- Remover caracteres especiais (?, :, parenteses)
- Nao incluir "Compre", "Melhor preco" ou CTAs no titulo

### Descricao complementar
- ATUAL: Gera descricao com foco em storytelling e CTA para WooCommerce
- AJUSTE ML: Sem HTML, sem links, sem mencao a "nraizes.com.br"
- Incluir: ingredientes, modo de uso, peso liquido, validade
- Incluir palavras-chave de busca ML naturalmente no texto
- Min 300 palavras (400-600 ideal)

### Descricao curta
- ATUAL: Frase de impacto (max 150 chars)
- ML: A descricao curta do Bling NAO e usada no ML diretamente.
  O ML usa o titulo + descricao complementar.
  Mas e util para o campo "Subtitulo" se disponivel.

### Campos customizados (NOVO - nao existe hoje)
- Gerar valores para: Marca, Formato, Tipo, Sabor, Vegano (S/N),
  Livre de Gluten (S/N) a partir dos dados do produto
- Preencher via Bling API ou manualmente

---

## 13. Plano de Acao para os 50 Produtos NRAIZES

### Fase 1: Preparacao (antes de vincular)

| # | Acao | Responsavel | Ferramentas |
|---|------|-------------|-------------|
| 1 | Vincular categorias Bling -> ML | Operacional | Bling > Categorias > Multiloja |
| 2 | Criar campos customizados obrigatorios | Operacional | Bling > Configuracoes > Campos customizados |
| 3 | Corrigir titulos (PMME, sem CAIXA ALTA) | IA + Revisao | Script de enrichment ajustado |
| 4 | Gerar descricoes para 21 produtos sem descricao | IA | `python tools/enrich_ml_products.py` |
| 5 | Fotografar 4 produtos sem imagem | Manual | Foto com fundo branco 1200x1200 |
| 6 | Preencher EANs faltantes | Script + Manual | `python src/ean_finder.py` + embalagens |
| 7 | Preencher peso e dimensoes dos 50 produtos | Manual | Balanca + fita metrica |
| 8 | Preencher campos customizados (marca, formato, etc.) | IA + Manual | Bling cadastro produto |

### Fase 2: Vinculacao e publicacao

| # | Acao | Ferramentas |
|---|------|-------------|
| 9 | Configurar regras de exportacao ML no Bling | Bling > Integracoes > ML |
| 10 | Executar vinculacao dos 50 produtos | `python tools/vincular_produtos_ml.py --executar` |
| 11 | Verificar anuncios publicados no ML | Painel do vendedor ML |
| 12 | Ajustar ficha tecnica de cada anuncio no ML (se necessario) | Painel do vendedor ML |

### Fase 3: Otimizacao pos-publicacao

| # | Acao |
|---|------|
| 13 | Ativar Mercado Ads para os 10 produtos com maior margem |
| 14 | Monitorar perguntas e responder em ate 1 hora |
| 15 | Acompanhar metricas: impressoes, cliques, conversao |
| 16 | Ajustar titulos e precos dos produtos com baixo desempenho |
| 17 | Avaliar inclusao de mais produtos apos 30 dias |
