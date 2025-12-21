<?php
/**
 * Admin Tools for Novas Raízes
 * Ferramentas de administração para gerenciar o tema
 * 
 * @package Organium-Child
 */

/**
 * Adiciona página de ferramentas no admin
 */
add_action('admin_menu', 'nraizes_admin_tools_menu');
function nraizes_admin_tools_menu() {
    add_submenu_page(
        'tools.php',
        'Novas Raízes Tools',
        'Novas Raízes',
        'manage_options',
        'nraizes-tools',
        'nraizes_admin_tools_page'
    );
}

/**
 * Página de ferramentas
 */
function nraizes_admin_tools_page() {
    // Verificar permissões
    if (!current_user_can('manage_options')) {
        wp_die('Acesso negado');
    }
    
    $message = '';
    $results = null;
    
    // Processar ações
    if (isset($_POST['action']) && wp_verify_nonce($_POST['_wpnonce'], 'nraizes_tools')) {
        switch ($_POST['action']) {
            case 'update_tags':
                define('NRAIZES_UPDATE_TAGS', true);
                require_once get_stylesheet_directory() . '/update-product-tags.php';
                exit; // O script já mostra output
                break;
                
            case 'update_categories':
                define('NRAIZES_UPDATE_CATEGORIES', true);
                require_once get_stylesheet_directory() . '/update-categories.php';
                exit;
                break;
                
            case 'preview_tags':
                $results = nraizes_preview_tag_updates();
                break;
        }
    }
    
    ?>
    <div class="wrap">
        <h1>🌿 Novas Raízes - Ferramentas</h1>
        
        <?php if ($message): ?>
            <div class="notice notice-success"><p><?php echo esc_html($message); ?></p></div>
        <?php endif; ?>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px;">
            
            <!-- Tags de Produtos -->
            <div class="card" style="padding: 20px;">
                <h2>🏷️ Tags de Produtos</h2>
                <p>Adiciona tags de benefício aos produtos baseado em:</p>
                <ul style="list-style: disc; margin-left: 20px;">
                    <li>Categoria do produto</li>
                    <li>Palavras-chave na descrição</li>
                </ul>
                <p><strong>⚠️ MTC:</strong> Produtos de fórmulas chinesas são ignorados (ANVISA)</p>
                
                <form method="post" style="margin-top: 15px;">
                    <?php wp_nonce_field('nraizes_tools'); ?>
                    <input type="hidden" name="action" value="update_tags">
                    <button type="submit" class="button button-primary">
                        ▶️ Executar Atualização de Tags
                    </button>
                </form>
            </div>
            
            <!-- Descrições de Categorias -->
            <div class="card" style="padding: 20px;">
                <h2>📂 Descrições de Categorias</h2>
                <p>Atualiza descrições SEO das categorias de produtos.</p>
                
                <form method="post" style="margin-top: 15px;">
                    <?php wp_nonce_field('nraizes_tools'); ?>
                    <input type="hidden" name="action" value="update_categories">
                    <button type="submit" class="button button-primary">
                        ▶️ Atualizar Descrições
                    </button>
                </form>
            </div>
            
            <!-- Status -->
            <div class="card" style="padding: 20px;">
                <h2>📊 Status das Otimizações</h2>
                <table class="widefat" style="margin-top: 10px;">
                    <tr>
                        <td>Cross-sells no Carrinho</td>
                        <td>✅ Ativo</td>
                    </tr>
                    <tr>
                        <td>Produtos Relacionados</td>
                        <td>✅ Ativo</td>
                    </tr>
                    <tr>
                        <td>Cache de Categorias</td>
                        <td>✅ Ativo</td>
                    </tr>
                    <tr>
                        <td>Lazy Loading</td>
                        <td>✅ Ativo</td>
                    </tr>
                    <tr>
                        <td>XML-RPC</td>
                        <td>🔒 Desabilitado</td>
                    </tr>
                </table>
            </div>
            
        </div>
        
        <?php if ($results): ?>
            <div class="card" style="padding: 20px; margin-top: 20px;">
                <h2>Prévia das Tags</h2>
                <pre style="background: #f5f5f5; padding: 15px; overflow: auto; max-height: 500px;">
                    <?php print_r($results); ?>
                </pre>
            </div>
        <?php endif; ?>
        
    </div>
    <?php
}

/**
 * Prévia das atualizações de tags (sem aplicar)
 */
function nraizes_preview_tag_updates() {
    require_once get_stylesheet_directory() . '/update-product-tags.php';
    
    $args = array(
        'post_type'      => 'product',
        'posts_per_page' => 20,
        'post_status'    => 'publish',
        'fields'         => 'ids',
    );
    
    $product_ids = get_posts($args);
    $preview = array();
    
    foreach ($product_ids as $product_id) {
        $product = wc_get_product($product_id);
        if (!$product) continue;
        
        $tags = nraizes_find_applicable_tags($product_id);
        if (!empty($tags)) {
            $preview[] = array(
                'name' => $product->get_name(),
                'tags' => $tags,
            );
        }
    }
    
    return $preview;
}
