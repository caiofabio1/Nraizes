"""
Bling Optimizer - Content Sanitizer
Cleans up AI-generated content removing unwanted markup and special characters.
"""
import sqlite3
import re
import html
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'vault.db')


def clean_text(text: str, keep_html: bool = False) -> str:
    """
    Clean text by removing unwanted characters and formatting.
    
    Args:
        text: The text to clean
        keep_html: If True, preserve HTML tags (for descricao_complementar)
    """
    if not text:
        return text
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Remove markdown code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Remove markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold **text**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # Italic *text*
    text = re.sub(r'__([^_]+)__', r'\1', text)      # Bold __text__
    text = re.sub(r'_([^_]+)_', r'\1', text)        # Italic _text_
    
    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown lists markers at start of lines
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    if not keep_html:
        # Remove all HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove escaped HTML
        text = re.sub(r'&lt;[^&]*&gt;', '', text)
    else:
        # Keep only allowed HTML tags for Bling descriptions
        allowed_tags = ['p', 'br', 'strong', 'b', 'em', 'i', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4']
        
        # Remove all tags except allowed ones
        def keep_allowed(match):
            tag_content = match.group(0)
            tag_name = re.search(r'</?(\w+)', tag_content)
            if tag_name and tag_name.group(1).lower() in allowed_tags:
                return tag_content
            return ''
        
        text = re.sub(r'<[^>]+>', keep_allowed, text)
    
    # Remove escape sequences
    text = text.replace('\\n', '\n')
    text = text.replace('\\t', ' ')
    text = text.replace('\\r', '')
    text = text.replace('\\"', '"')
    text = text.replace("\\'", "'")
    
    # Remove JSON-like formatting
    text = re.sub(r'^\s*["\']|["\']$', '', text.strip())
    
    # Remove multiple consecutive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove multiple consecutive spaces
    text = re.sub(r' {2,}', ' ', text)
    
    # Trim whitespace
    text = text.strip()
    
    return text


def clean_all_proposals():
    """Clean all pending proposals in the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, tipo, conteudo_proposto FROM propostas_ia WHERE status = 'pendente'")
    proposals = cursor.fetchall()
    
    print(f"🧹 Limpando {len(proposals)} propostas...")
    
    cleaned_count = 0
    for p in proposals:
        original = p['conteudo_proposto']
        
        # Remove all HTML tags from all types for clean plain text
        keep_html = False
        cleaned = clean_text(original, keep_html=keep_html)
        
        if cleaned != original:
            cursor.execute(
                "UPDATE propostas_ia SET conteudo_proposto = ? WHERE id = ?",
                (cleaned, p['id'])
            )
            cleaned_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ Limpas {cleaned_count} propostas com caracteres especiais")
    return cleaned_count


def preview_cleaning(limit: int = 5):
    """Preview cleaning on a sample of proposals."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, tipo, conteudo_proposto 
        FROM propostas_ia 
        WHERE status = 'pendente' 
        LIMIT ?
    """, (limit,))
    
    for p in cursor.fetchall():
        original = p['conteudo_proposto']
        keep_html = p['tipo'] == 'descricao_complementar'
        cleaned = clean_text(original, keep_html=keep_html)
        
        if cleaned != original:
            print(f"\n=== ID: {p['id']} | Tipo: {p['tipo']} ===")
            print(f"ANTES:\n{original[:200]}...")
            print(f"\nDEPOIS:\n{cleaned[:200]}...")
            print("-" * 50)
    
    conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--preview':
        preview_cleaning()
    else:
        clean_all_proposals()
