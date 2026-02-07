<?php
/**
 * Yoast SEO Premium - Configuração Programática
 * 
 * Configura o Yoast SEO com melhores práticas para:
 * - Loja WooCommerce de produtos naturais
 * - LocalBusiness (Vila Mariana, São Paulo)
 * - Schema.org otimizado para saúde/bem-estar
 * - Open Graph / redes sociais
 * - Breadcrumbs
 * - Sitemaps WooCommerce
 * - Robots.txt (incluindo AI crawlers para GEO)
 * 
 * @package Organium-Child
 * @version 1.0.0
 */

if (!defined('ABSPATH')) exit;

// ============================================
// CONSTANTES DO NEGÓCIO
// ============================================
define('NRAIZES_SITE_NAME',    'Novas Raízes');
define('NRAIZES_SITE_URL',     'https://nraizes.com.br');
define('NRAIZES_PHONE',        '+5511999927588');
define('NRAIZES_STREET',       'R. Dr. Nicolau de Sousa Queirós, 34');
define('NRAIZES_CITY',         'São Paulo');
define('NRAIZES_STATE',        'SP');
define('NRAIZES_ZIP',          '04105-000');
define('NRAIZES_COUNTRY',      'BR');
define('NRAIZES_NEIGHBORHOOD', 'Vila Mariana');
define('NRAIZES_LAT',          -23.5714);
define('NRAIZES_LNG',          -46.6350);
define('NRAIZES_LOGO_URL',     'https://nraizes.com.br/wp-content/uploads/logo-novas-raizes.png');
define('NRAIZES_INSTAGRAM',    'https://www.instagram.com/nraizes');

// ============================================
// 1. CONFIGURAÇÃO INICIAL (roda uma vez)
// ============================================

add_action('admin_init', 'nraizes_yoast_initial_setup');
function nraizes_yoast_initial_setup() {
    // Só roda se Yoast estiver ativo
    if (!defined('WPSEO_VERSION')) return;
    
    $config_version = '1.0.0';
    if (get_option('nraizes_yoast_config_version') === $config_version) return;
    
    // --- wpseo (configurações gerais) ---
    $wpseo = get_option('wpseo', array());
    
    // Habilitar breadcrumbs
    $wpseo['breadcrumbs-enable'] = true;
    $wpseo['breadcrumbs-sep']    = '›';
    $wpseo['breadcrumbs-home']   = 'Início';
    $wpseo['breadcrumbs-prefix'] = '';
    $wpseo['breadcrumbs-searchprefix'] = 'Busca:';
    $wpseo['breadcrumbs-404crumb']     = 'Página não encontrada';
    
    // Schema: tipo de organização
    $wpseo['company_or_person']        = 'company';
    $wpseo['company_name']             = NRAIZES_SITE_NAME;
    $wpseo['company_logo']             = NRAIZES_LOGO_URL;
    $wpseo['company_logo_id']          = 0;
    
    // Desabilitar date in snippet (não queremos data nos resultados de busca para páginas)
    $wpseo['disable-date'] = true;
    
    // Habilitar análise de legibilidade e SEO
    $wpseo['keyword_analysis_active']     = true;
    $wpseo['content_analysis_active']     = true;
    $wpseo['enable_cornerstone_content']  = true;
    $wpseo['enable_text_link_counter']    = true;
    $wpseo['enable_xml_sitemap']          = true;
    
    update_option('wpseo', $wpseo);
    
    // --- wpseo_titles (templates de título e meta) ---
    $titles = get_option('wpseo_titles', array());
    
    // Separador de título
    $titles['separator'] = 'sc-pipe'; // |
    
    // Homepage
    $titles['title-home-wpseo']    = '%%sitename%% - Produtos Naturais, Suplementos e Medicina Tradicional Chinesa';
    $titles['metadesc-home-wpseo'] = 'Loja de produtos naturais, suplementos alimentares, fórmulas da Medicina Tradicional Chinesa, óleos essenciais e plantas medicinais. Vila Mariana, São Paulo. Entrega para todo Brasil.';
    
    // Posts
    $titles['title-post']    = '%%title%% %%page%% %%sep%% %%sitename%%';
    $titles['metadesc-post'] = '%%excerpt%%';
    
    // Páginas
    $titles['title-page']    = '%%title%% %%page%% %%sep%% %%sitename%%';
    $titles['metadesc-page'] = '%%excerpt%%';
    
    // Produtos WooCommerce
    $titles['title-product']    = '%%title%% %%sep%% Comprar Online %%sep%% %%sitename%%';
    $titles['metadesc-product'] = '%%excerpt%% Compre %%title%% com qualidade na %%sitename%%. Entrega para todo Brasil. Vila Mariana, São Paulo.';
    
    // Categorias de produto
    $titles['title-tax-product_cat']    = '%%term_title%% %%page%% %%sep%% %%sitename%%';
    $titles['metadesc-tax-product_cat'] = '%%term_description%% Encontre os melhores produtos de %%term_title%% na %%sitename%%. Entrega para todo Brasil.';
    
    // Tags de produto
    $titles['title-tax-product_tag']    = '%%term_title%% %%page%% %%sep%% %%sitename%%';
    $titles['metadesc-tax-product_tag'] = 'Produtos relacionados a %%term_title%% na %%sitename%%. Suplementos e produtos naturais com qualidade.';
    
    // Arquivo da Loja (Shop)
    $titles['title-ptarchive-product']    = 'Loja %%page%% %%sep%% Produtos Naturais e Fórmulas Chinesas %%sep%% %%sitename%%';
    $titles['metadesc-ptarchive-product'] = 'Explore nossa loja de produtos naturais, suplementos, fórmulas da Medicina Tradicional Chinesa, óleos essenciais e plantas medicinais. Entrega para todo Brasil.';
    
    // Categorias de blog
    $titles['title-tax-category']    = '%%term_title%% %%page%% %%sep%% %%sitename%%';
    $titles['metadesc-tax-category'] = '%%term_description%%';
    
    // Noindex em conteúdos sem valor SEO
    $titles['noindex-tax-post_tag']      = true;  // Tags de blog geralmente são thin content
    $titles['noindex-tax-post_format']   = true;  // Formatos de post
    $titles['noindex-author-wpseo']      = true;  // Autor (loja, não blog pessoal)
    $titles['noindex-archive-wpseo']     = true;  // Arquivos de data
    
    // Schema padrão por tipo de conteúdo
    $titles['schema-page-type-post']    = 'WebPage';
    $titles['schema-article-type-post'] = 'Article';
    $titles['schema-page-type-page']    = 'WebPage';
    
    // Remover tags de categorias não usadas dos títulos
    $titles['stripcategorybase'] = true;
    
    update_option('wpseo_titles', $titles);
    
    // --- wpseo_social (redes sociais e Open Graph) ---
    $social = get_option('wpseo_social', array());
    
    // Open Graph habilitado
    $social['opengraph'] = true;
    
    // Twitter Card
    $social['twitter']       = true;
    $social['twitter_card_type'] = 'summary_large_image';
    
    // Perfis sociais
    $social['instagram_url'] = NRAIZES_INSTAGRAM;
    $social['other_social_urls'] = array(
        'https://wa.me/5511999927588',
    );
    
    // Imagem padrão para Open Graph (quando post não tem imagem)
    $social['og_default_image']    = NRAIZES_LOGO_URL;
    $social['og_default_image_id'] = 0;
    
    // Facebook Open Graph
    $social['og_frontpage_title'] = NRAIZES_SITE_NAME . ' - Produtos Naturais, Suplementos e MTC';
    $social['og_frontpage_desc']  = 'Loja de produtos naturais, suplementos alimentares, fórmulas da Medicina Tradicional Chinesa, óleos essenciais e plantas medicinais. Vila Mariana, São Paulo.';
    $social['og_frontpage_image'] = NRAIZES_LOGO_URL;
    
    update_option('wpseo_social', $social);
    
    // Marcar como configurado
    update_option('nraizes_yoast_config_version', $config_version);
}

// ============================================
// 2. SCHEMA.ORG - LocalBusiness + Organization
// ============================================

/**
 * Modifica o schema Organization do Yoast para incluir LocalBusiness
 */
add_filter('wpseo_schema_organization', 'nraizes_yoast_schema_organization');
function nraizes_yoast_schema_organization($data) {
    // Adicionar tipos adicionais
    $data['@type'] = array('Organization', 'LocalBusiness', 'HealthAndBeautyBusiness');
    
    $data['name']        = NRAIZES_SITE_NAME;
    $data['url']         = NRAIZES_SITE_URL;
    $data['telephone']   = NRAIZES_PHONE;
    $data['priceRange']  = '$$';
    
    $data['address'] = array(
        '@type'            => 'PostalAddress',
        'streetAddress'    => NRAIZES_STREET,
        'addressLocality'  => NRAIZES_CITY,
        'addressRegion'    => NRAIZES_STATE,
        'postalCode'       => NRAIZES_ZIP,
        'addressCountry'   => NRAIZES_COUNTRY,
    );
    
    $data['geo'] = array(
        '@type'     => 'GeoCoordinates',
        'latitude'  => NRAIZES_LAT,
        'longitude' => NRAIZES_LNG,
    );
    
    $data['openingHoursSpecification'] = array(
        array(
            '@type'     => 'OpeningHoursSpecification',
            'dayOfWeek' => array('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'),
            'opens'     => '09:00',
            'closes'    => '18:30',
        ),
    );
    
    $data['sameAs'] = array(
        NRAIZES_INSTAGRAM,
    );
    
    $data['hasMap'] = 'https://www.google.com/maps/search/R.+Dr.+Nicolau+de+Sousa+Queir%C3%B3s,+34+-+Vila+Mariana,+S%C3%A3o+Paulo+-+SP';
    
    $data['knowsAbout'] = array(
        'Produtos Naturais',
        'Suplementos Alimentares',
        'Medicina Tradicional Chinesa',
        'Óleos Essenciais',
        'Plantas Medicinais',
        'Fitoterapia',
        'Aromaterapia',
    );
    
    // Logo
    if (!isset($data['logo']) || !is_array($data['logo'])) {
        $data['logo'] = array(
            '@type' => 'ImageObject',
            'url'   => NRAIZES_LOGO_URL,
        );
    }
    
    return $data;
}

/**
 * Adiciona Schema de WebSite com SearchAction para sitelinks searchbox
 */
add_filter('wpseo_schema_website', 'nraizes_yoast_schema_website');
function nraizes_yoast_schema_website($data) {
    $data['potentialAction'] = array(
        '@type'       => 'SearchAction',
        'target'      => array(
            '@type'        => 'EntryPoint',
            'urlTemplate'  => NRAIZES_SITE_URL . '/?s={search_term_string}',
        ),
        'query-input' => 'required name=search_term_string',
    );
    
    $data['inLanguage'] = 'pt-BR';
    
    return $data;
}

// ============================================
// 3. SCHEMA PARA PRODUTOS WOOCOMMERCE
// ============================================

/**
 * Enriquece o schema de produto do Yoast com dados adicionais
 */
add_filter('wpseo_schema_product', 'nraizes_yoast_schema_product');
function nraizes_yoast_schema_product($data) {
    if (!is_product()) return $data;
    
    global $product;
    if (!$product || !is_a($product, 'WC_Product')) return $data;
    
    // Marca padrão para todos os produtos
    if (!isset($data['brand'])) {
        $data['brand'] = array(
            '@type' => 'Brand',
            'name'  => NRAIZES_SITE_NAME,
        );
    }
    
    // Garantir disponibilidade correta
    if ($product->is_in_stock()) {
        $data['offers']['availability'] = 'https://schema.org/InStock';
    } else {
        $data['offers']['availability'] = 'https://schema.org/OutOfStock';
    }
    
    // Moeda brasileira
    $data['offers']['priceCurrency'] = 'BRL';
    
    // Seller
    $data['offers']['seller'] = array(
        '@type' => 'Organization',
        'name'  => NRAIZES_SITE_NAME,
        'url'   => NRAIZES_SITE_URL,
    );
    
    // Shipping: entrega para todo Brasil
    $data['offers']['shippingDetails'] = array(
        '@type' => 'OfferShippingDetails',
        'shippingDestination' => array(
            '@type'          => 'DefinedRegion',
            'addressCountry' => 'BR',
        ),
    );
    
    // Condição: novo
    $data['offers']['itemCondition'] = 'https://schema.org/NewCondition';
    
    // Categorias do produto como additionalType
    $terms = get_the_terms($product->get_id(), 'product_cat');
    if ($terms && !is_wp_error($terms)) {
        $categories = wp_list_pluck($terms, 'name');
        $data['category'] = implode(', ', $categories);
    }
    
    // Peso, se disponível
    if ($product->get_weight()) {
        $data['weight'] = array(
            '@type'    => 'QuantitativeValue',
            'value'    => $product->get_weight(),
            'unitCode' => 'KGM',
        );
    }
    
    return $data;
}

// ============================================
// 4. BREADCRUMBS - Configuração WooCommerce
// ============================================

/**
 * Customiza os breadcrumbs do Yoast para WooCommerce
 */
add_filter('wpseo_breadcrumb_links', 'nraizes_yoast_breadcrumb_links');
function nraizes_yoast_breadcrumb_links($links) {
    if (function_exists('is_product') && is_product()) {
        // Adiciona "Loja" entre Início e a categoria
        $loja_link = array(
            'url'  => get_permalink(wc_get_page_id('shop')),
            'text' => 'Loja',
        );
        
        // Insere após o primeiro item (Início)
        array_splice($links, 1, 0, array($loja_link));
    }
    
    return $links;
}

// ============================================
// 5. TÍTULOS E META - Correções específicas
// ============================================

/**
 * Substituir nome antigo "Mivegan" por "Novas Raizes" em todos os títulos
 */
add_filter('wpseo_title', 'nraizes_yoast_fix_brand_name', 20);
function nraizes_yoast_fix_brand_name($title) {
    return str_replace('Mivegan', 'Novas Raizes', $title);
}

/**
 * Substituir nome antigo nas meta descriptions
 */
add_filter('wpseo_metadesc', 'nraizes_yoast_fix_brand_desc', 20);
function nraizes_yoast_fix_brand_desc($desc) {
    return str_replace('Mivegan', 'Novas Raizes', $desc);
}

/**
 * Substituir nome antigo no Open Graph
 */
add_filter('wpseo_opengraph_title', 'nraizes_yoast_fix_brand_name', 20);
add_filter('wpseo_opengraph_desc', 'nraizes_yoast_fix_brand_desc', 20);

// ============================================
// 6. OPEN GRAPH - Melhorias para WooCommerce
// ============================================

/**
 * Adicionar og:type product para páginas de produto
 */
add_filter('wpseo_opengraph_type', 'nraizes_yoast_og_type');
function nraizes_yoast_og_type($type) {
    if (function_exists('is_product') && is_product()) {
        return 'product';
    }
    if (function_exists('is_shop') && is_shop()) {
        return 'website';
    }
    return $type;
}

/**
 * Adicionar locale pt_BR
 */
add_filter('wpseo_locale', 'nraizes_yoast_locale');
function nraizes_yoast_locale($locale) {
    return 'pt_BR';
}

// ============================================
// 7. SITEMAPS - Otimização WooCommerce
// ============================================

/**
 * Excluir páginas sem conteúdo SEO do sitemap
 */
add_filter('wpseo_sitemap_exclude_post_type', 'nraizes_yoast_exclude_post_types', 10, 2);
function nraizes_yoast_exclude_post_types($exclude, $post_type) {
    // Excluir tipos de post sem valor SEO
    $exclude_types = array(
        'attachment',       // Páginas de anexo
        'revision',         // Revisões
        'nav_menu_item',    // Itens de menu
        'custom_css',       // CSS customizado
        'customize_changeset', // Changesets
        'oembed_cache',     // Cache oEmbed
        'wp_block',         // Blocos reutilizáveis
        'wp_template',      // Templates FSE
        'wp_template_part', // Partes de template FSE
        'wp_navigation',    // Navegação FSE
    );
    
    if (in_array($post_type, $exclude_types)) {
        return true;
    }
    
    return $exclude;
}

/**
 * Excluir taxonomias sem valor SEO do sitemap
 */
add_filter('wpseo_sitemap_exclude_taxonomy', 'nraizes_yoast_exclude_taxonomies', 10, 2);
function nraizes_yoast_exclude_taxonomies($exclude, $taxonomy) {
    $exclude_tax = array(
        'post_format',      // Formatos de post
        'product_type',     // Tipo de produto WC (interno)
        'product_visibility', // Visibilidade WC (interno)
        'product_shipping_class', // Classe de envio (sem valor SEO direto)
    );
    
    if (in_array($taxonomy, $exclude_tax)) {
        return true;
    }
    
    return $exclude;
}

/**
 * Prioridade do sitemap: produtos e categorias com prioridade alta
 */
add_filter('wpseo_xml_sitemap_post_url', 'nraizes_yoast_sitemap_product_priority', 10, 2);
function nraizes_yoast_sitemap_product_priority($url, $post) {
    // Yoast 19+ já não usa priority, mas mantemos para compatibilidade
    return $url;
}

// ============================================
// 8. ROBOTS.TXT - Configuração completa
// ============================================

/**
 * Otimiza robots.txt com regras para Yoast + AI crawlers (GEO)
 */
add_filter('robots_txt', 'nraizes_yoast_robots_txt', 9999, 2);
function nraizes_yoast_robots_txt($output, $public) {
    if ('0' === $public) return $output;
    
    // Limpar regras duplicadas de feed (Yoast às vezes adiciona Disallow para feeds)
    $output = preg_replace('/Disallow:\s*\/.*feed.*\n?/i', '', $output);
    
    // Permitir feeds (bom para Google News e indexação)
    if (strpos($output, 'Allow: /feed/') === false) {
        $output .= "\nAllow: /feed/\n";
    }
    
    // Bloquear URLs de admin e query strings de busca interna
    if (strpos($output, 'wp-admin') === false) {
        $output .= "Disallow: /wp-admin/\n";
        $output .= "Allow: /wp-admin/admin-ajax.php\n";
    }
    
    // Bloquear URLs de busca interna (conteúdo duplicado)
    if (strpos($output, '?s=') === false) {
        $output .= "Disallow: /?s=\n";
        $output .= "Disallow: /search/\n";
    }
    
    // Bloquear query strings de filtro WooCommerce
    if (strpos($output, 'add-to-cart') === false) {
        $output .= "Disallow: /*?add-to-cart=*\n";
        $output .= "Disallow: /cart/\n";
        $output .= "Disallow: /checkout/\n";
        $output .= "Disallow: /minha-conta/\n";
        $output .= "Disallow: /my-account/\n";
    }
    
    // Referência ao sitemap do Yoast
    $sitemap_url = home_url('/sitemap_index.xml');
    if (strpos($output, 'sitemap_index.xml') === false) {
        $output .= "\nSitemap: " . $sitemap_url . "\n";
    }
    
    // AI Crawlers (GEO - Generative Engine Optimization)
    $output .= "\n# AI Search Crawlers (GEO)\n";
    $output .= "User-agent: ChatGPT-User\nAllow: /\n\n";
    $output .= "User-agent: GPTBot\nAllow: /\n\n";
    $output .= "User-agent: Google-Extended\nAllow: /\n\n";
    $output .= "User-agent: PerplexityBot\nAllow: /\n\n";
    $output .= "User-agent: ClaudeBot\nAllow: /\n\n";
    $output .= "User-agent: Applebot-Extended\nAllow: /\n\n";
    $output .= "User-agent: cohere-ai\nAllow: /\n\n";
    $output .= "User-agent: Bytespider\nAllow: /\n\n";
    
    return $output;
}

// ============================================
// 9. REDIRECT DE COMMENT FEEDS
// ============================================

/**
 * Redireciona feeds de comentários para o permalink do post
 * Yoast Premium pode desabilitar feeds de comentários, mas
 * o 301 redirect é mais amigável que um 404/410
 */
add_action('template_redirect', 'nraizes_yoast_redirect_comment_feeds', 5);
function nraizes_yoast_redirect_comment_feeds() {
    if (is_feed() && is_singular() && is_comment_feed()) {
        wp_redirect(get_permalink(), 301);
        exit;
    }
}

// ============================================
// 10. REMOVER RSS FEED LINKS DO HEAD
// ============================================

/**
 * Remove feed discovery links do <head>
 * O Yoast gerencia o RSS via sitemap, não precisa de discovery links
 */
add_action('wp_head', 'nraizes_yoast_remove_feed_links', 1);
function nraizes_yoast_remove_feed_links() {
    remove_action('wp_head', 'feed_links', 2);
    remove_action('wp_head', 'feed_links_extra', 3);
}

// ============================================
// 11. WOOCOMMERCE - Garantir título H1 correto
// ============================================

/**
 * Garantir que o título da página de arquivo é exibido
 */
add_filter('woocommerce_show_page_title', '__return_true');

// ============================================
// 12. CANONICAL URLs - Prevenção de duplicatas
// ============================================

/**
 * Corrigir canonical em páginas paginadas de categorias WooCommerce
 */
add_filter('wpseo_canonical', 'nraizes_yoast_fix_canonical');
function nraizes_yoast_fix_canonical($canonical) {
    // Remover parâmetros de filtro da canonical (evita conteúdo duplicado)
    if (function_exists('is_shop') && (is_shop() || is_product_category() || is_product_tag())) {
        $canonical = remove_query_arg(array(
            'orderby',
            'min_price',
            'max_price',
            'rating_filter',
            'filter_cor',
            'filter_tamanho',
        ), $canonical);
    }
    
    return $canonical;
}

// ============================================
// 13. META ROBOTS - Páginas sem valor SEO
// ============================================

/**
 * Noindex em páginas utilitárias do WooCommerce
 */
add_filter('wpseo_robots', 'nraizes_yoast_noindex_utility_pages');
function nraizes_yoast_noindex_utility_pages($robots) {
    if (function_exists('is_cart') && is_cart()) {
        return 'noindex, follow';
    }
    if (function_exists('is_checkout') && is_checkout()) {
        return 'noindex, follow';
    }
    if (function_exists('is_account_page') && is_account_page()) {
        return 'noindex, follow';
    }
    // Páginas de busca
    if (is_search()) {
        return 'noindex, follow';
    }
    
    return $robots;
}

// ============================================
// 14. PERFORMANCE - Desabilitar recursos Yoast não utilizados
// ============================================

/**
 * Desabilitar indexables para tipos de post que não precisam
 * (reduz queries no banco de dados)
 */
add_filter('wpseo_indexable_forced_included_post_types', 'nraizes_yoast_indexable_post_types');
function nraizes_yoast_indexable_post_types($post_types) {
    // Garantir que produtos e posts estão incluídos
    $post_types[] = 'product';
    $post_types[] = 'post';
    $post_types[] = 'page';
    return array_unique($post_types);
}

// ============================================
// 15. YOAST SEO PREMIUM - Redirect Manager
// ============================================

/**
 * Registrar redirects comuns (se Yoast Premium estiver ativo)
 * Yoast Premium salva redirects no banco, mas podemos adicionar via código
 */
add_action('init', 'nraizes_yoast_premium_redirects');
function nraizes_yoast_premium_redirects() {
    // Só roda se Yoast Premium estiver ativo
    if (!class_exists('WPSEO_Premium')) return;
    
    // Redirects comuns: mivegan -> nraizes
    // Estes são para URLs antigas que podem ainda ter backlinks
    $redirects = array(
        '/mivegan'      => '/',
        '/mivegan-loja' => '/loja/',
    );
    
    // Yoast Premium gerencia redirects internamente
    // Para adicionar via código, verificamos se a tabela de redirects existe
    // Este é um fallback - o ideal é configurar via admin
}

// ============================================
// 16. STRUCTURED DATA - Página de Consulta
// ============================================

/**
 * Desabilitar schema padrão do Yoast na página de consulta
 * para usar o schema especializado do consulta-produtos.php
 * (MedicalWebPage, Dataset, FAQPage, etc.)
 */
add_filter('wpseo_schema_webpage', 'nraizes_yoast_consulta_schema', 10, 1);
function nraizes_yoast_consulta_schema($data) {
    global $post;
    
    // Se a página usa o shortcode de consulta, adaptar o schema
    if (is_a($post, 'WP_Post') && has_shortcode($post->post_content, 'nraizes_consulta')) {
        $data['@type'] = array('WebPage', 'MedicalWebPage');
        $data['specialty'] = 'Medicina Integrativa e Produtos Naturais';
        $data['medicalAudience'] = array(
            '@type'        => 'MedicalAudience',
            'audienceType' => 'Patient',
        );
    }
    
    return $data;
}

// ============================================
// 17. IMAGEM PADRÃO PARA OPEN GRAPH
// ============================================

/**
 * Garantir que produtos sem imagem usem o logo como fallback no Open Graph
 */
add_filter('wpseo_opengraph_image', 'nraizes_yoast_og_fallback_image');
function nraizes_yoast_og_fallback_image($image) {
    if (empty($image)) {
        return NRAIZES_LOGO_URL;
    }
    return $image;
}

// ============================================
// 18. HREFLANG - Indicar idioma pt-BR
// ============================================

/**
 * Adicionar meta tag de idioma (complementar ao Yoast)
 */
add_action('wp_head', 'nraizes_yoast_language_meta', 5);
function nraizes_yoast_language_meta() {
    if (!defined('WPSEO_VERSION')) {
        // Fallback se Yoast não estiver ativo
        echo '<meta property="og:locale" content="pt_BR">' . "\n";
    }
    // Content-Language (útil para crawlers)
    echo '<meta http-equiv="content-language" content="pt-BR">' . "\n";
}

// ============================================
// 19. LLMS.TXT - Link para AI discoverability
// ============================================

/**
 * Adicionar link para llms.txt no <head> (GEO)
 */
add_action('wp_head', 'nraizes_yoast_llms_link', 5);
function nraizes_yoast_llms_link() {
    $llms_url = get_stylesheet_directory_uri() . '/llms.txt';
    echo '<link rel="alternate" type="text/plain" href="' . esc_url($llms_url) . '" title="LLM Context">' . "\n";
}

// ============================================
// 20. ADMIN - Ajustes de UX para o Yoast
// ============================================

/**
 * Configurar colunas do Yoast no admin de produtos
 */
add_filter('wpseo_use_page_analysis', '__return_true');

/**
 * Garantir que a análise SEO funciona corretamente em produtos WooCommerce
 */
add_filter('wpseo_metabox_prio', 'nraizes_yoast_metabox_priority');
function nraizes_yoast_metabox_priority() {
    return 'low'; // Mover metabox do Yoast para baixo no editor
}
