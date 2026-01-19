"""
NRAIZES - Product Migration Module
Migrates product data from Gestao Click to Bling format.
"""
import pandas as pd
import os
import sys
import requests
import json
import time
import unicodedata
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from logger import get_business_logger

# Initialize logger
_logger = get_business_logger('migration')

# Project root (portable paths)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load Environment Mechanism
cred_path = os.path.join(PROJECT_ROOT, '.credentials', 'bling_api_tokens.env')
load_dotenv(cred_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Paths (relative to project root)
MIGRATION_DIR = os.path.join(PROJECT_ROOT, 'MIGRAÇÃO')
SOURCE_FILE = os.path.join(MIGRATION_DIR, 'gestão click.xlsx')
TARGET_TEMPLATE_XLS = os.path.join(MIGRATION_DIR, 'produtos.xls')
TARGET_TEMPLATE_XLSX = os.path.join(MIGRATION_DIR, 'produtos.xlsx')
OUTPUT_FILE = os.path.join(MIGRATION_DIR, 'produtos_importacao_bling.xlsx')

MODELS = ["gemini-3.0-flash-preview", "gemini-2.0-flash-exp", "gemini-1.5-flash"]

def normalize_str(s):
    if pd.isna(s): return ""
    return unicodedata.normalize('NFKD', str(s)).encode('ASCII', 'ignore').decode('ASCII').lower().strip()

def get_gemini_response(prompt, model_index=0):
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY not found. Skipping AI matching.")
        return None

    model = MODELS[model_index]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        if resp.status_code != 200:
            if model_index + 1 < len(MODELS):
                return get_gemini_response(prompt, model_index + 1)
            else:
                _logger.logger.warning(f"All Gemini models failed. Last status: {resp.status_code}")
                return None
        return resp.json()['candidates'][0]['content']['parts'][0]['text']
    except requests.exceptions.Timeout as e:
        _logger.logger.warning(f"Gemini API timeout: {e}")
        return None
    except requests.exceptions.RequestException as e:
        _logger.logger.error(f"Gemini API request error: {e}")
        return None
    except (KeyError, IndexError) as e:
        _logger.logger.error(f"Invalid Gemini API response structure: {e}")
        return None

def clean_price(val) -> Optional[float]:
    """
    Clean and convert a price value to float.

    Args:
        val: Price value (can be string, int, float, or pandas Series)

    Returns:
        Cleaned float value or None if invalid
    """
    try:
        if isinstance(val, (pd.Series, pd.DataFrame, list)):
            _logger.logger.debug(f"clean_price received non-scalar: {type(val)}")
            if hasattr(val, 'iloc') and len(val) == 1:
                val = val.iloc[0]
            else:
                return None

        if pd.isna(val) or val == '':
            return None
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).replace('R$', '').replace('.', '').replace(',', '.').strip()
        if not s:
            return None
        return float(s)
    except (ValueError, TypeError) as e:
        _logger.logger.debug(f"Error cleaning price value '{val}': {e}")
        return None

def read_file(path: str, is_source: bool = False) -> Optional[pd.DataFrame]:
    """
    Read an Excel file with automatic format detection.

    Args:
        path: Path to the Excel file
        is_source: If True, attempts header row detection

    Returns:
        DataFrame or None if file cannot be read
    """
    if not os.path.exists(path):
        _logger.logger.warning(f"File not found: {path}")
        return None

    _logger.logger.info(f"Loading: {path}")

    try:
        if path.endswith('.xls'):
            try:
                return pd.read_excel(path, engine='xlrd')
            except ImportError:
                _logger.logger.debug("xlrd not available, trying default engine")
                return pd.read_excel(path)

        if is_source:
            _logger.logger.info("Searching for header row...")
            df_raw = pd.read_excel(path, header=None, nrows=15)
            found_idx = None

            for i, row in df_raw.iterrows():
                vals = [str(x).strip() for x in row.values]
                vals_norm = [normalize_str(x) for x in vals]
                has_code = any('codigo' in v for v in vals_norm)
                has_desc = any('descricao' in v for v in vals_norm)
                if has_code and has_desc:
                    found_idx = i
                    break

            if found_idx is not None:
                _logger.logger.info(f"Detected header at row {found_idx}")
                return pd.read_excel(path, header=found_idx)

            _logger.logger.warning("Header detection failed. Trying positional fallback.")
            try:
                df_pos = pd.read_excel(path, header=None, skiprows=2)
                df_pos.rename(columns={0: 'Código', 1: 'Descrição', 7: 'Preço de custo', 8: 'Preço'}, inplace=True)
                _logger.logger.info("Applied positional mapping.")
                return df_pos
            except Exception as e:
                _logger.logger.error(f"Positional fallback failed: {e}")

        return pd.read_excel(path)

    except FileNotFoundError as e:
        _logger.log_failure(f"File not found: {path}", e)
        return None
    except pd.errors.EmptyDataError as e:
        _logger.log_failure(f"Empty file: {path}", e)
        return None
    except Exception as e:
        _logger.log_failure(f"Failed to read {path}", e)
        return None

def apply_update(df_target, idx, row, match_row, mapping):
    modified = False
    for src_col, tgt_cols_list in mapping.items():
         if src_col not in match_row:
             continue
        
         for tgt_col in tgt_cols_list:
             if tgt_col not in df_target.columns:
                 continue
             
             current_val = row.get(tgt_col)
             new_val = match_row.get(src_col)

             if 'Preço' in tgt_col or 'Peso' in tgt_col:
                 new_val_clean = clean_price(new_val)
                 current_val_clean = clean_price(current_val)
                 val_to_assign = new_val_clean
             else:
                 current_val_clean = current_val
                 val_to_assign = new_val

             # LOGIC: Fill if empty (0.0 cost is empty)
             is_empty = pd.isna(current_val) or str(current_val).strip() == ''
             if 'Preço' in tgt_col:
                 if current_val_clean == 0.0 or pd.isna(current_val_clean):
                     is_empty = True
            
             # Check explicitly for None or NaN
             if is_empty and val_to_assign is not None and not pd.isna(val_to_assign):
                 df_target.at[idx, tgt_col] = val_to_assign
                 modified = True
    return modified

def migrate():
    df_target = read_file(TARGET_TEMPLATE_XLSX)
    if df_target is None:
        df_target = read_file(TARGET_TEMPLATE_XLS)

    df_source = read_file(SOURCE_FILE, is_source=True)

    if df_target is None or not isinstance(df_target, pd.DataFrame):
         print("❌ Failed to read TARGET file.")
         return
    if df_source is None or not isinstance(df_source, pd.DataFrame):
         print("❌ Failed to read SOURCE file.")
         return

    # Normalize Columns
    # Normalize Columns and Deduplicate
    source_cols = [str(c).strip() for c in df_source.columns]
    # Handle duplicates by appending counter
    seen = {}
    new_source_cols = []
    for c in source_cols:
        if c in seen:
            seen[c] += 1
            new_source_cols.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            new_source_cols.append(c)
    df_source.columns = new_source_cols

    original_target_columns = list(df_target.columns)
    target_cols = [str(c).strip() for c in df_target.columns]
    seen = {}
    new_target_cols = []
    for c in target_cols:
        if c in seen:
            seen[c] += 1
            new_target_cols.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            new_target_cols.append(c)
    df_target.columns = new_target_cols
    
    print(f"Source: {df_source.shape}, Target: {df_target.shape}")
    
    # Prepare keys
    df_source['Código_Str'] = df_source['Código'].astype(str).str.strip()
    
    # Deduplicate
    dupes = df_source[df_source.duplicated('Código_Str', keep=False)]
    if not dupes.empty:
        print(f"⚠️ Deduping {len(dupes)} source records.")
        df_source.drop_duplicates(subset=['Código_Str'], keep='first', inplace=True)
    
    if 'Código' not in df_target.columns:
         print("❌ Target missing 'Código' column.")
         return

    df_target['Código_Str'] = df_target['Código'].astype(str).str.strip().replace('nan', '')
    
    source_map = df_source.set_index('Código_Str').to_dict('index')

    mapping = {
        'Preço de custo': ['Preço de custo', 'Preço de compra'],
        'Preço': ['Preço'],
        'Unidade': ['Unidade'],
        'Peso líquido (Kg)': ['Peso líq.'],
        'Peso bruto (Kg)': ['Peso bruto'],
        'GTIN/EAN': ['GTIN/EAN'],
    }

    updates_count = 0
    ai_matches = 0
    
    # Normalized name lookup
    df_source['Name_Norm'] = df_source['Descrição'].astype(str).apply(normalize_str)
    source_name_map = {row['Name_Norm']: row for i, row in df_source.iterrows()}
    
    # Context for AI
    source_list_text = []
    for i, row in df_source.iterrows():
        c = row['Código_Str']
        n = row['Descrição']
        if pd.notna(n):
             source_list_text.append(f"ID: {c} | {n}")
    full_source_context = "\n".join(source_list_text)

    # 1. Exact Matching loop
    targets_to_match = []
    
    for idx, row in df_target.iterrows():
        try:
            code = row.get('Código_Str')
            name = str(row.get('Descrição'))
            name_norm = normalize_str(name)
            
            match_row = None
            if code in source_map:
                match_row = source_map[code]
            elif name_norm in source_name_map:
                match_row = source_name_map[name_norm]
                
            if match_row:
                 if apply_update(df_target, idx, row, match_row, mapping):
                     updates_count += 1
            else:
                 if len(name) > 3 and name != 'nan':
                     # Add to AI queue
                     targets_to_match.append((idx, row, name))
        except ValueError as e:
            print(f"CRITICAL ERROR at Row {idx}: {e}")
            print(f"Row data types: {row.apply(type)}")
            # Skip this row but continue
            continue
        except Exception as e:
            print(f"Unexpected error at Row {idx}: {e}")
            continue

    print(f"\nExact Matches Complete. Total Updated: {updates_count}")
    print(f"Starting AI Batch Matching for {len(targets_to_match)} products...")

    # 2. Batch AI Matching
    BATCH_SIZE = 25
    for i in range(0, len(targets_to_match), BATCH_SIZE):
        batch = targets_to_match[i:i+BATCH_SIZE]
        print(f"  AI Batch {i//BATCH_SIZE + 1} ({len(batch)} items)...")
        
        target_list_str = "\n".join([f"Target_ID_{j}: {item[2]}" for j, item in enumerate(batch)])
        
        prompt = f"""
        You are a product matching expert. 
        Match each Target product to the BEST corresponding product in the Source List.
        The names might vary slightly (e.g. "Product X - 100ml" vs "Product X 100 ml").
        
        Task: Return JSON mapping 'Target_ID_X' to 'Source_ID'.
        If absolutely NO match exists, map to null.
        
        Source List:
        {full_source_context}
        
        Target Products:
        {target_list_str}
        
        Output Format (JSON):
        {{ "Target_ID_0": "Source_ID" }}
        """
        
        try:
            resp_text = get_gemini_response(prompt)
            if resp_text:
                cleaned_json = resp_text.strip()
                if cleaned_json.startswith('```json'): cleaned_json = cleaned_json[7:]
                if cleaned_json.endswith('```'): cleaned_json = cleaned_json[:-3]
                
                mapping_result = json.loads(cleaned_json)
                
                for j, item in enumerate(batch):
                    idx = item[0]
                    row = item[1]
                    key = f"Target_ID_{j}"
                    
                    if key in mapping_result and mapping_result[key]:
                        source_id = str(mapping_result[key]).strip()
                        if source_id in source_map:
                            match_row = source_map[source_id]
                            if apply_update(df_target, idx, row, match_row, mapping):
                                updates_count += 1
                                ai_matches += 1
        except Exception as e:
            print(f"   Batch Error: {e}")
            time.sleep(1)

    print(f"\nStats:")
    print(f"- Total Products Updated: {updates_count}")
    print(f"- Matches found via AI: {ai_matches}")
    
    final_df = df_target[original_target_columns]
    print(f"Saving to {OUTPUT_FILE}...")
    final_df.to_excel(OUTPUT_FILE, index=False)
    print("✅ Migration Completed.")

if __name__ == "__main__":
    migrate()
