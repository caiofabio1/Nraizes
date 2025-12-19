<?php
/**
 * SEO Improvements
 * 
 * @package Organium-Child
 */

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Get product brand from various sources
 * Must be defined early as it's used by multiple functions
 */
function nraizes_get_product_brand($product) {
    if (!$product || !is_object($product)) return '';
    
    $product_id = $product->get_id();
    
    // Try taxonomy 'product_brand' (common plugin)
    $brands = get_the_terms($product_id, 'product_brand');
    if (!empty($brands) && !is_wp_error($brands)) {
        return strtolower($brands[0]->name);
    }
    
    // Try attribute 'pa_marca'
    $marca = $product->get_attribute('pa_marca');
    if (!empty($marca)) {
        return strtolower($marca);
    }
    
    // Try to detect from product name
    $name = strtolower($product->get_name());
    $known_brands = array('taimin', 'avatim', 'slim body', 'mivegan');
    foreach ($known_brands as $brand) {
        if (strpos($name, $brand) !== false) {
            return $brand;
        }
    }
    
    // Try to detect from categories
    $categories = get_the_terms($product_id, 'product_cat');
    if (!empty($categories) && !is_wp_error($categories)) {
        foreach ($categories as $cat) {
            $cat_name = strtolower($cat->name);
            if (in_array($cat_name, $known_brands)) {
                return $cat_name;
            }
            // Check for Chinese formulas category
            if (strpos($cat_name, 'fórmula') !== false || strpos($cat_name, 'formula') !== false || strpos($cat_name, 'chinesa') !== false) {
                return 'formulas_chinesas';
            }
        }
    }
    
    return '';
}

// ============================================
// H1 FIXES
// ============================================

/**
 * Single Product: Replace default title with visible H1
 */
remove_action('woocommerce_single_product_summary', 'woocommerce_template_single_title', 5);
add_action('woocommerce_single_product_summary', 'nraizes_product_h1_title', 5);
function nraizes_product_h1_title() {
    the_title('<h1 class="product_title entry-title">', '</h1>');
}

/**
 * Archive pages: Ensure page title is shown (theme may hide it)
 */
add_filter('woocommerce_show_page_title', '__return_true');

// ============================================
// OPTIMIZED TITLE TAGS
// ============================================

/**
 * Optimize document title for better CTR
 * Format: [Nome] [Marca] | [Benefício] - Novas Raízes
 */
add_filter('document_title_parts', 'nraizes_optimize_title_tags', 10, 1);
function nraizes_optimize_title_tags($title_parts) {
    
    if (is_product()) {
        global $product;
        $brand = nraizes_get_product_brand($product);
        $name = $product->get_name();
        
        // Remove brand from name if already present to avoid duplication
        $brand_upper = ucfirst($brand);
        $clean_name = trim(str_ireplace(array($brand, $brand_upper), '', $name));
        
        switch ($brand) {
            case 'taimin':
                $title_parts['title'] = "{$clean_name} Taimin | Fitoterapia Chinesa";
                break;
            case 'avatim':
                $title_parts['title'] = "{$clean_name} Avatim | Aromas Naturais";
                break;
            case 'formulas_chinesas':
                $title_parts['title'] = "{$name} | Fórmula Chinesa Tradicional";
                break;
            case 'slim body':
                $title_parts['title'] = "{$clean_name} | Emagrecimento Natural";
                break;
            default:
                $title_parts['title'] = "{$name} | Produto Natural";
        }
        $title_parts['site'] = 'Novas Raízes';
        
    } elseif (is_tax('product_brand') || (is_archive() && strpos($_SERVER['REQUEST_URI'], '/marca/') !== false)) {
        $term = get_queried_object();
        if ($term) {
            $title_parts['title'] = "Produtos {$term->name} | Loja Oficial";
            $title_parts['site'] = 'Novas Raízes';
        }
        
    } elseif (is_product_category()) {
        $term = get_queried_object();
        if ($term) {
            $count = $term->count;
            $title_parts['title'] = "{$term->name} | {$count} Produtos Selecionados";
            $title_parts['site'] = 'Novas Raízes';
        }
        
    } elseif (is_shop()) {
        $title_parts['title'] = 'Loja | Produtos Naturais e Fórmulas Chinesas';
        $title_parts['site'] = 'Novas Raízes';
    }
    
    return $title_parts;
}

// ============================================
// SCHEMA MARKUP (JSON-LD)
// ============================================

/**
 * Product Schema
 */
add_action('wp_head', 'nraizes_product_schema');
function nraizes_product_schema() {
    if (!is_product()) return;
    
    global $product;
    
    $image = wp_get_attachment_url($product->get_image_id());
    if (!$image) {
        $image = wc_placeholder_img_src();
    }
    
    $availability = $product->is_in_stock() 
        ? 'https://schema.org/InStock' 
        : 'https://schema.org/OutOfStock';
    
    $schema = array(
        '@context' => 'https://schema.org',
        '@type' => 'Product',
        'name' => $product->get_name(),
        'description' => preg_replace('/\s+/', ' ', trim(wp_strip_all_tags($product->get_short_description() ?: $product->get_description()))),
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
 * Breadcrumbs with Schema
 */
add_action('woocommerce_before_single_product', 'nraizes_breadcrumbs_schema', 5);
function nraizes_breadcrumbs_schema() {
    if (!is_product()) return;
    
    global $product;
    
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
        'name' => $product->get_name(),
        'item' => get_permalink($product->get_id())
    );
    
    $schema = array(
        '@context' => 'https://schema.org',
        '@type' => 'BreadcrumbList',
        'itemListElement' => $breadcrumbs
    );
    
    echo '<script type="application/ld+json">' . wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . '</script>' . "\n";
    
    // Visual breadcrumbs
    ?>
    <nav class="nraizes-breadcrumb" aria-label="Breadcrumb">
        <a href="<?php echo home_url(); ?>">Início</a>
        <span aria-hidden="true">›</span>
        <a href="<?php echo wc_get_page_permalink('shop'); ?>">Loja</a>
        <?php if ($category): ?>
        <span aria-hidden="true">›</span>
        <a href="<?php echo get_term_link($category); ?>"><?php echo esc_html($category->name); ?></a>
        <?php endif; ?>
        <span aria-hidden="true">›</span>
        <span aria-current="page"><?php echo esc_html($product->get_name()); ?></span>
    </nav>
    <?php
}

/**
 * Homepage Schema (Organization + WebSite)
 */
add_action('wp_head', 'nraizes_homepage_schema', 1);
function nraizes_homepage_schema() {
    if (!is_front_page() && !is_home()) return;
    
    $organization = array(
        '@context' => 'https://schema.org',
        '@type' => 'Organization',
        'name' => 'Novas Raízes',
        'alternateName' => 'Mivegan',
        'url' => home_url(),
        'logo' => get_site_icon_url() ?: home_url('/wp-content/uploads/logo.png'),
        'description' => 'Loja de Produtos Naturais, Fórmulas Chinesas e Suplementos de alta qualidade.',
        'contactPoint' => array(
            '@type' => 'ContactPoint',
            'contactType' => 'customer service',
            'availableLanguage' => 'Portuguese'
        ),
        'sameAs' => array(
            'https://www.instagram.com/mivegan.br/'
        )
    );
    
    echo '<script type="application/ld+json">' . wp_json_encode($organization, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . '</script>' . "\n";
    
    $website = array(
        '@context' => 'https://schema.org',
        '@type' => 'WebSite',
        'name' => 'Novas Raízes',
        'url' => home_url(),
        'potentialAction' => array(
            '@type' => 'SearchAction',
            'target' => array(
                '@type' => 'EntryPoint',
                'urlTemplate' => home_url('/?s={search_term_string}')
            ),
            'query-input' => 'required name=search_term_string'
        )
    );
    
    echo '<script type="application/ld+json">' . wp_json_encode($website, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . '</script>' . "\n";
}

// ============================================
// DYNAMIC META DESCRIPTIONS (Enhanced)
// ============================================

/**
 * Generate meta description based on brand/category
 */
add_action('wp_head', 'nraizes_meta_descriptions', 1);
function nraizes_meta_descriptions() {
    if (defined('WPSEO_VERSION') || defined('RANK_MATH_VERSION')) return;
    
    $description = '';
    
    if (is_product()) {
        global $product;
        $brand = nraizes_get_product_brand($product);
        $name = $product->get_name();
        $short_desc = wp_strip_all_tags($product->get_short_description());
        
        switch ($brand) {
            case 'taimin':
                $description = "{$name} Taimin | Fitoterapia Chinesa Original. Entrega rápida para todo Brasil. ✓ Loja especializada ✓ Frete grátis +R$500";
                break;
                
            case 'avatim':
                $description = "{$name} Avatim | Ingredientes naturais brasileiros. Aromas exclusivos. Compre na Novas Raízes com entrega garantida.";
                break;
                
            case 'formulas_chinesas':
                // Extract indication from short description if available
                $indication = !empty($short_desc) ? mb_substr($short_desc, 0, 50) : 'saúde e bem-estar';
                $description = "{$name} - Fórmula tradicional chinesa para {$indication}. ✓ Autêntico ✓ Certificado ✓ Frete Grátis +R$500";
                break;
                
            case 'slim body':
                $description = "{$name} Slim Body | Emagrecimento natural e saudável. Resultados comprovados. Compre online na Novas Raízes.";
                break;
                
            default:
                // Generic with short description
                if (!empty($short_desc)) {
                    $description = "{$name} - " . mb_substr($short_desc, 0, 100) . ". Compre na Novas Raízes.";
                } else {
                    $description = "{$name} | Produto natural de alta qualidade. Frete grátis acima de R$500. Entrega para todo Brasil.";
                }
        }
        
    } elseif (is_tax('product_brand') || (is_archive() && strpos($_SERVER['REQUEST_URI'], '/marca/') !== false)) {
        // Brand archive pages (e.g., /marca/taimin/, /marca/avatim/)
        $term = get_queried_object();
        $brand_name = $term ? $term->name : '';
        $brand_slug = $term ? strtolower($term->slug) : '';
        
        switch ($brand_slug) {
            case 'taimin':
                $description = "Produtos Taimin | Fitoterapia Chinesa Original na Novas Raízes. Fórmulas tradicionais com qualidade certificada. Frete grátis +R$500.";
                break;
            case 'avatim':
                $description = "Produtos Avatim | Cosméticos e aromas com ingredientes naturais brasileiros. Loja oficial Novas Raízes. Entrega rápida.";
                break;
            default:
                $description = "Produtos {$brand_name} | Loja oficial na Novas Raízes. Qualidade garantida e entrega para todo Brasil. Frete grátis +R$500.";
        }
        
    } elseif (is_product_category()) {
        $term = get_queried_object();
        $cat_name = $term ? $term->name : '';
        
        if (!empty($term->description)) {
            $description = wp_strip_all_tags($term->description);
        } else {
            $description = "{$cat_name} | Produtos selecionados na Novas Raízes. Qualidade garantida, entrega rápida e frete grátis acima de R$500.";
        }
        
    } elseif (is_shop()) {
        $description = 'Loja de Produtos Naturais, Fórmulas Chinesas e Suplementos. Marcas: Taimin, Avatim e mais. Frete grátis +R$500. Entrega todo Brasil.';
        
    } elseif (is_front_page()) {
        $description = 'Novas Raízes - Sua loja de produtos naturais, fórmulas chinesas (Taimin) e cosméticos (Avatim). Qualidade garantida e frete grátis.';
    }
    
    if (!empty($description)) {
        // Trim to 160 characters
        $description = preg_replace('/\s+/', ' ', trim($description));
        if (mb_strlen($description) > 160) {
            $description = mb_substr($description, 0, 157) . '...';
        }
        echo '<meta name="description" content="' . esc_attr($description) . '">' . "\n";
    }
}

// ============================================
// ROBOTS.TXT OPTIMIZATION
// ============================================

add_filter('robots_txt', 'nraizes_optimize_robots_txt', 9999, 2);
function nraizes_optimize_robots_txt($output, $public) {
    $output = preg_replace('/Disallow:.*\/feed\/(\r?\n)?/i', '', $output);
    $output .= "\nAllow: /feed/\n";
    $output .= "Allow: /*/feed/\n";
    return $output;
}

// Remove feed links from header
add_action('wp_head', 'nraizes_remove_feed_links', 1);
function nraizes_remove_feed_links() {
    remove_action('wp_head', 'feed_links', 2);
    remove_action('wp_head', 'feed_links_extra', 3);
}

// Redirect comment feeds to content
add_action('template_redirect', 'nraizes_redirect_comment_feeds', 5);
function nraizes_redirect_comment_feeds() {
    if (is_feed()) {
        if (is_singular()) {
            wp_redirect(get_permalink(), 301);
            exit;
        } elseif (is_tax() || is_category() || is_tag()) {
            wp_redirect(get_term_link(get_queried_object()), 301);
            exit;
        } else {
            wp_redirect(home_url(), 301);
            exit;
        }
    }
}
