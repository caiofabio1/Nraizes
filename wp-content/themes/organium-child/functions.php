<?php
/**
 * Organium Child Theme Functions
 * 
 * @package Organium-Child
 * @version 1.1.0
 */

add_action( 'wp_enqueue_scripts', 'enqueue_theme_styles' );
function enqueue_theme_styles() {
    if (class_exists('WooCommerce')) {
        wp_enqueue_style( 'child-style', get_stylesheet_directory_uri() . '/style.css', array('organium-theme', 'organium-style', 'organium-woocommerce') );
    } else {
        wp_enqueue_style( 'child-style', get_stylesheet_directory_uri() . '/style.css', array('organium-theme', 'organium-style') );
    }
}

// ============================================
// Adicione suas customizações abaixo
// ============================================

/**
 * MELHORIA 1: Simplificar campos do checkout
 * Remove campos desnecessários para reduzir fricção
 */
add_filter('woocommerce_checkout_fields', 'nraizes_simplify_checkout');
function nraizes_simplify_checkout($fields) {
    // Remove campos que raramente são usados
    unset($fields['billing']['billing_company']);
    unset($fields['billing']['billing_address_2']);
    unset($fields['shipping']['shipping_company']);
    unset($fields['shipping']['shipping_address_2']);
    return $fields;
}

/**
 * MELHORIA 2: Badges de confiança no checkout
 * Aumenta a confiança do cliente antes do pagamento
 */
add_action('woocommerce_review_order_before_payment', 'nraizes_add_trust_badges');
function nraizes_add_trust_badges() {
    ?>
    <div class="nraizes-trust-badges" style="text-align:center; margin:15px 0; padding:15px; background:#f9f9f9; border-radius:8px; border:1px solid #e5e5e5;">
        <span style="margin:0 12px; display:inline-block;">🔒 Pagamento Seguro</span>
        <span style="margin:0 12px; display:inline-block;">🚚 Entrega Rastreável</span>
        <span style="margin:0 12px; display:inline-block;">✅ Satisfação Garantida</span>
    </div>
    <?php
}

/**
 * MELHORIA 3: Segurança - Desabilitar XML-RPC
 * Previne ataques de força bruta via xmlrpc.php
 */
add_filter('xmlrpc_enabled', '__return_false');

/**
 * MELHORIA 4: Barra de Progresso Frete Grátis
 * Mostra quanto falta para ganhar frete grátis (R$1.000)
 */
add_action('woocommerce_before_cart', 'nraizes_free_shipping_bar');
add_action('woocommerce_before_checkout_form', 'nraizes_free_shipping_bar');
function nraizes_free_shipping_bar() {
    $min_amount = 500; // Valor mínimo para frete grátis
    $current = WC()->cart->subtotal;
    $remaining = $min_amount - $current;
    
    if ($remaining > 0) {
        $percent = ($current / $min_amount) * 100;
        ?>
        <div class="nraizes-shipping-bar" style="background:linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding:20px; margin-bottom:25px; border-radius:12px; text-align:center; box-shadow:0 2px 8px rgba(0,0,0,0.08);">
            <p style="margin:0 0 12px; font-size:16px; color:#333;">
                🚚 Faltam <strong style="color:#e67e22;">R$ <?php echo number_format($remaining, 2, ',', '.'); ?></strong> para <strong>FRETE GRÁTIS!</strong>
            </p>
            <div style="background:#ddd; border-radius:6px; height:12px; overflow:hidden;">
                <div style="background:linear-gradient(90deg, #27ae60 0%, #2ecc71 100%); height:12px; border-radius:6px; width:<?php echo min($percent, 100); ?>%; transition:width 0.5s ease;"></div>
            </div>
        </div>
        <?php
    } else {
        ?>
        <div class="nraizes-shipping-bar" style="background:linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); padding:20px; margin-bottom:25px; border-radius:12px; text-align:center; box-shadow:0 2px 8px rgba(0,0,0,0.08);">
            <p style="margin:0; font-size:18px; color:#155724;">
                🎉 Parabéns! Você ganhou <strong>FRETE GRÁTIS!</strong>
            </p>
        </div>
        <?php
    }
}

/**
 * MELHORIA 5: Cross-sells Inteligentes baseados em Dados de Venda
 * Analisa pedidos anteriores para sugerir produtos frequentemente comprados juntos
 * Fallback: produtos da mesma categoria se não houver dados suficientes
 */
add_filter('woocommerce_cross_sells_total', function() { return 4; });
add_filter('woocommerce_cross_sells_columns', function() { return 4; });

// Cross-sells baseados em histórico de compras
add_filter('woocommerce_product_crosssell_ids', 'nraizes_smart_crosssells', 10, 2);
function nraizes_smart_crosssells($crosssell_ids, $product) {
    // Se já tem cross-sells configurados manualmente, usa eles
    if (!empty($crosssell_ids)) {
        return $crosssell_ids;
    }
    
    $product_id = $product->get_id();
    
    // Tenta buscar produtos frequentemente comprados juntos
    $frequently_bought = nraizes_get_frequently_bought_together($product_id);
    
    if (!empty($frequently_bought)) {
        return array_slice($frequently_bought, 0, 8);
    }
    
    // Fallback: produtos da mesma categoria
    return nraizes_get_same_category_products($product_id);
}

/**
 * Busca produtos frequentemente comprados juntos baseado no histórico de pedidos
 */
function nraizes_get_frequently_bought_together($product_id) {
    global $wpdb;
    
    // Cache por 24 horas para performance
    $cache_key = 'nraizes_fbt_' . $product_id;
    $cached = get_transient($cache_key);
    if ($cached !== false) {
        return $cached;
    }
    
    // Busca pedidos que contêm este produto
    $order_ids = $wpdb->get_col($wpdb->prepare("
        SELECT DISTINCT order_id 
        FROM {$wpdb->prefix}woocommerce_order_items oi
        INNER JOIN {$wpdb->prefix}woocommerce_order_itemmeta oim 
            ON oi.order_item_id = oim.order_item_id
        WHERE oim.meta_key = '_product_id' 
        AND oim.meta_value = %d
        LIMIT 100
    ", $product_id));
    
    if (empty($order_ids)) {
        set_transient($cache_key, array(), DAY_IN_SECONDS);
        return array();
    }
    
    // Busca outros produtos nesses pedidos
    $placeholders = implode(',', array_fill(0, count($order_ids), '%d'));
    $query = $wpdb->prepare("
        SELECT oim.meta_value as product_id, COUNT(*) as frequency
        FROM {$wpdb->prefix}woocommerce_order_items oi
        INNER JOIN {$wpdb->prefix}woocommerce_order_itemmeta oim 
            ON oi.order_item_id = oim.order_item_id
        WHERE oi.order_id IN ($placeholders)
        AND oim.meta_key = '_product_id'
        AND oim.meta_value != %d
        GROUP BY oim.meta_value
        ORDER BY frequency DESC
        LIMIT 8
    ", array_merge($order_ids, array($product_id)));
    
    $results = $wpdb->get_results($query);
    
    $product_ids = array();
    foreach ($results as $row) {
        // Verifica se o produto ainda existe e está publicado
        if (get_post_status($row->product_id) === 'publish') {
            $product_ids[] = (int)$row->product_id;
        }
    }
    
    set_transient($cache_key, $product_ids, DAY_IN_SECONDS);
    return $product_ids;
}

/**
 * Fallback: busca produtos da mesma categoria
 */
function nraizes_get_same_category_products($product_id) {
    $terms = get_the_terms($product_id, 'product_cat');
    
    if (empty($terms) || is_wp_error($terms)) {
        return array();
    }
    
    $category_ids = wp_list_pluck($terms, 'term_id');
    
    $args = array(
        'post_type'      => 'product',
        'posts_per_page' => 8,
        'post_status'    => 'publish',
        'post__not_in'   => array($product_id),
        'orderby'        => 'rand',
        'tax_query'      => array(
            array(
                'taxonomy' => 'product_cat',
                'field'    => 'term_id',
                'terms'    => $category_ids,
            ),
        ),
    );
    
    $products = get_posts($args);
    return !empty($products) ? wp_list_pluck($products, 'ID') : array();
}

/**
 * MELHORIA 6: Estilos customizados para mobile
 * Adiciona CSS para botão fixo no mobile
 */
add_action('wp_head', 'nraizes_custom_mobile_styles');
function nraizes_custom_mobile_styles() {
    ?>
    <style>
    /* Botão fixo "Adicionar ao Carrinho" no mobile */
    @media (max-width: 768px) {
        .single-product .single_add_to_cart_button {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            right: 0 !important;
            z-index: 9999 !important;
            margin: 0 !important;
            border-radius: 0 !important;
            padding: 18px !important;
            font-size: 16px !important;
            font-weight: bold !important;
            box-shadow: 0 -4px 12px rgba(0,0,0,0.15) !important;
        }
        .single-product .product,
        .single-product .site-content {
            padding-bottom: 80px !important;
        }
    }
    </style>
    <?php
}

// ============================================
// SEO IMPROVEMENTS
// ============================================

/**
 * MELHORIA 7: Corrigir H1 em páginas de produto
 * Muda o título do produto de H2 para H1
 */
add_filter('woocommerce_product_loop_title_classes', function() { return 'woocommerce-loop-product__title'; });

// Força H1 no título do produto individual
add_action('woocommerce_single_product_summary', 'nraizes_product_h1_title', 4);
function nraizes_product_h1_title() {
    if (!is_product()) return;
    global $product;
    ?>
    <h1 class="product_title entry-title" style="display:none;"><?php echo esc_html($product->get_name()); ?></h1>
    <?php
}

/**
 * MELHORIA 8: Schema JSON-LD para Produtos
 * Habilita Rich Snippets (preço, disponibilidade) no Google
 */
add_action('wp_head', 'nraizes_product_schema');
function nraizes_product_schema() {
    if (!is_product()) return;
    
    global $product;
    
    // Pega a imagem do produto
    $image = wp_get_attachment_url($product->get_image_id());
    if (!$image) {
        $image = wc_placeholder_img_src();
    }
    
    // Disponibilidade
    $availability = $product->is_in_stock() 
        ? 'https://schema.org/InStock' 
        : 'https://schema.org/OutOfStock';
    
    // Monta o schema
    $schema = array(
        '@context' => 'https://schema.org',
        '@type' => 'Product',
        'name' => $product->get_name(),
        'description' => wp_strip_all_tags($product->get_short_description() ?: $product->get_description()),
        'image' => $image,
        'sku' => $product->get_sku() ?: $product->get_id(),
        'brand' => array(
            '@type' => 'Brand',
            'name' => 'Novas Raízes'
        ),
        'offers' => array(
            '@type' => 'Offer',
            'url' => get_permalink($product->get_id()),
            'priceCurrency' => 'BRL',
            'price' => $product->get_price(),
            'availability' => $availability,
            'seller' => array(
                '@type' => 'Organization',
                'name' => 'Novas Raízes'
            )
        )
    );
    
    // Adiciona rating se existir
    $rating_count = $product->get_rating_count();
    if ($rating_count > 0) {
        $schema['aggregateRating'] = array(
            '@type' => 'AggregateRating',
            'ratingValue' => $product->get_average_rating(),
            'reviewCount' => $rating_count
        );
    }
    
    echo '<script type="application/ld+json">' . wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . '</script>' . "\n";
}

/**
 * MELHORIA 9: Breadcrumbs com Schema
 * Adiciona navegação estruturada com JSON-LD
 */
add_action('woocommerce_before_single_product', 'nraizes_breadcrumbs_schema', 5);
function nraizes_breadcrumbs_schema() {
    if (!is_product()) return;
    
    global $product;
    
    // Pega as categorias do produto
    $terms = get_the_terms($product->get_id(), 'product_cat');
    $category = !empty($terms) ? $terms[0] : null;
    
    $breadcrumbs = array(
        array(
            '@type' => 'ListItem',
            'position' => 1,
            'name' => 'Início',
            'item' => home_url()
        ),
        array(
            '@type' => 'ListItem',
            'position' => 2,
            'name' => 'Loja',
            'item' => wc_get_page_permalink('shop')
        )
    );
    
    $position = 3;
    
    if ($category) {
        $breadcrumbs[] = array(
            '@type' => 'ListItem',
            'position' => $position,
            'name' => $category->name,
            'item' => get_term_link($category)
        );
        $position++;
    }
    
    $breadcrumbs[] = array(
        '@type' => 'ListItem',
        'position' => $position,
        'name' => $product->get_name()
    );
    
    $schema = array(
        '@context' => 'https://schema.org',
        '@type' => 'BreadcrumbList',
        'itemListElement' => $breadcrumbs
    );
    
    echo '<script type="application/ld+json">' . wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . '</script>' . "\n";
    
    // Exibe breadcrumbs visualmente
    ?>
    <nav class="nraizes-breadcrumb" style="font-size:14px; margin-bottom:20px; color:#666;">
        <a href="<?php echo home_url(); ?>" style="color:#888; text-decoration:none;">Início</a>
        <span style="margin:0 8px;">›</span>
        <a href="<?php echo wc_get_page_permalink('shop'); ?>" style="color:#888; text-decoration:none;">Loja</a>
        <?php if ($category): ?>
        <span style="margin:0 8px;">›</span>
        <a href="<?php echo get_term_link($category); ?>" style="color:#888; text-decoration:none;"><?php echo esc_html($category->name); ?></a>
        <?php endif; ?>
        <span style="margin:0 8px;">›</span>
        <span style="color:#333;"><?php echo esc_html($product->get_name()); ?></span>
    </nav>
    <?php
}

/**
 * MELHORIA 10: H1 para páginas de arquivo/loja
 * Adiciona H1 nas páginas de categoria e loja
 */
add_action('woocommerce_before_shop_loop', 'nraizes_archive_h1', 5);
function nraizes_archive_h1() {
    if (is_shop()) {
        echo '<h1 class="page-title" style="display:none;">Loja - Produtos Naturais e Fórmulas Chinesas</h1>';
    } elseif (is_product_category()) {
        $term = get_queried_object();
        if ($term) {
            echo '<h1 class="page-title" style="display:none;">' . esc_html($term->name) . ' - Novas Raízes</h1>';
        }
    }
}
