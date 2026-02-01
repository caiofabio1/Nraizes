# Boas Práticas de Analytics, SEO e Performance - Novas Raízes (2026)

Este documento detalha as recomendações técnicas e estratégicas para otimizar a presença digital da Novas Raízes, baseado na auditoria realizada em Janeiro de 2026.

---

## 1. Google Analytics 4 (GA4) & GTM

### ⚠️ Diagnóstico de Dados Crítico

O tráfego atual apresenta uma anomalia grave: **99% do tráfego é classificado como "(direct) / (none)"** com taxa de conversão quase nula.

**Recomendações:**

1.  **Revisão do GTM4WP**: Verifique se o plugin está disparando o `page_view` antes da aceitação do banner de cookies (Consent Mode). Se o Consent Mode sinalizar `denied` e o tráfego ainda for computado como direto por falta de cookies, os dados ficam "sujos".
2.  **Filtro de IPs Internos**: Configurar no GA4 o filtro para excluir o tráfego da equipe interna e desenvolvedores para não inflar as métricas.
3.  **Cross-Domain Tracking**: Garantir que o tráfego vindo de links externos (Instagram, Bio, etc) esteja corretamente tageado com parâmetros UTM.

---

## 2. SEO (Search Engine Optimization)

### Auditoria Técnica

Identificamos que o site utiliza **Yoast SEO** em conjunto com ajustes manuais no `functions.php`.

**Boas Práticas Implementadas:**

- ✅ Otimização de `robots.txt` para permitir indexação de feeds.
- ✅ Redirecionamento de feeds de comentários para evitar conteúdo duplicado.
- ✅ Uso correto de H1 (títulos de produtos e páginas).

**Oportunidades de Melhoria:**

- **Product Schema**: Garantir que as propriedades `priceValidUntil` e `availability` estejam sempre presentes no JSON-LD (o Google Search Console penaliza se faltarem).
- **Internal Linking**: Criar uma rede de links entre fórmulas chinesas (MTC) e suplementos premium (Ocean Drop/Central Nutrition) para transferir autoridade de página.

---

## 3. Performance & Web Vitals

### Otimizações Encontradas

O tema `organium-child` já possui uma camada de performance sólida em `performance.php`.

**Pontos Fortes:**

- Preconnect para Google Fonts e DNS-prefetch para Google Analytics.
- Lazy load nativo para imagens.
- Defer de scripts não críticos.

**Próximos Passos:**

- **Critical CSS**: Implementar a geração de CSS crítico para melhorar o _Largest Contentful Paint_ (LCP).
- **WPO (Web Performance Optimization)**: Monitorar o impacto do carregamento do GTM, que é pesado. Considere mover tags pesadas para o lado do servidor (Server-Side GTM) no futuro.

---

## 4. Plano de Ação (Próximos 30 dias)

1.  **Semana 1**: Corrigir atribuição de tráfego direto (GTM review).
2.  **Semana 2**: Atualizar Schema Markup de produtos com estoque e validade.
3.  **Semana 3**: Testar remoção de scripts JS órfãos no checkout.
4.  **Semana 4**: Gerar novo relatório de diagnóstico para validar a limpeza dos dados.

---

_Documento gerado pela Antigravity AI - Janeiro 2026_
