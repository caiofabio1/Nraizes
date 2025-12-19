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
