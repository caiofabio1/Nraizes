"""
NRAIZES - Financial Analysis Module
Analyzes sales data to calculate margins and projected revenue.
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from gestao_client import GestaoClient
from logger import get_business_logger

# Initialize logger
_logger = get_business_logger('financial')

def analyze_financials():
    """
    Perform financial analysis including margin calculation and revenue projection.
    Fetches sales data from Gestao Click API and calculates:
    - Overall average margin
    - Monthly revenue (actual and projected)
    """
    _logger.log_start("Financial analysis")

    gc = GestaoClient()
    
    print("📥 Fetching Sales Data (Fetching latest 500 records to determine period)...")
    
    sales_data = []
    page = 1
    MAX_PAGES = 50 # 500 records max
    
    found_valid_dates = 0
    
    while page <= MAX_PAGES:
        print(f"   Page {page}...", end='\r')
        resp = gc.get_vendas(limit=10, page=page)
        
        if not resp or 'data' not in resp or not resp['data']:
            # If 200 OK but empty data, stop.
            break
            
        dataset = resp['data']
        sales_data.extend(dataset)
        
        # Check current batch for valid dates (debug)
        valid_in_batch = 0
        for s in dataset:
            if s.get('data_emissao'): valid_in_batch += 1
            
        # print(f"   Page {page}: {len(dataset)} items (Valid Dates: {valid_in_batch})")
        
        found_valid_dates += valid_in_batch
        
        # If we have enough valid data, we can stop early? 
        # No, we need historical context (3 months).
        # But if total records are small (like 2), we stop naturally.
        
        page += 1
        
    print(f"\n   Fetched {len(sales_data)} records. Found {found_valid_dates} with valid dates.")
    
    if not sales_data:
        print("❌ No sales found.")
        return

    # Determine Date Range from Data
    dates = []
    valid_sales = []
    
    for i, s in enumerate(sales_data):
        dstr = s.get('data_emissao')
        if dstr:
            try:
                dt = datetime.strptime(dstr, "%Y-%m-%d")
                dates.append(dt)
                s['_u_date'] = dt
                valid_sales.append(s)
            except ValueError as e:
                _logger.logger.debug(f"Invalid date format in sale {i}: {dstr} - {e}")
                continue
    
    if not dates:
        print("❌ No valid dates found in sales.")
        # Fallback: Check if we can deduce date from other fields? 
        # Or just report failure.
        return
        
    dates.sort()
    min_date = dates[0]
    max_date = dates[-1]
    
    print(f"   Data Range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
    
    # Logic: If max_date is far from Now (e.g. > 30 days), warn user but use Max Date Month as "Current".
    # User asked for "Faturamento presumido desse mês".
    # matches system time?
    now = datetime.now()
    
    # Check if we have data for "System Current Month"
    curr_month_start = datetime(now.year, now.month, 1)
    
    target_month_sales = [s for s in valid_sales if s['_u_date'] >= curr_month_start]
    
    reference_month_start = curr_month_start
    is_historical_ref = False
    
    if not target_month_sales and (now - max_date).days > 30:
        # Fallback to last available month
        reference_month_start = datetime(max_date.year, max_date.month, 1)
        is_historical_ref = True
        print(f"⚠️ No sales found for current system month ({now.strftime('%B %Y')}).")
        print(f"⚠️ Using latest available data: {max_date.strftime('%B %Y')}")
    
    # Calculate Metrics
    total_revenue_period = 0.0
    total_cost_period = 0.0
    
    # Financials for Reference Month
    month_revenue = 0.0
    month_cost = 0.0
    
    # For Margin, utilize ALL fetched data (better average)
    for s in valid_sales:
        # Revenue
        try:
            rev = float(s.get('valor_total', 0) or 0)
        except (ValueError, TypeError) as e:
            _logger.logger.debug(f"Invalid revenue value: {s.get('valor_total')} - {e}")
            rev = 0.0

        # Cost - Look into 'produtos'
        cost = 0.0
        products = s.get('produtos', [])
        if isinstance(products, list):
            for p_wrap in products:
                # Structure: {'produto': {...}} or just {...}?
                p = p_wrap.get('produto', {})
                try:
                    p_qty = float(p.get('quantidade', 0))
                    p_cost_unit = float(p.get('valor_custo', 0) or 0)
                    cost += (p_cost_unit * p_qty)
                except (ValueError, TypeError) as e:
                    _logger.logger.debug(f"Invalid product cost data: {e}")
                    continue
        
        total_revenue_period += rev
        total_cost_period += cost
        
        # Month specific
        s_date = s['_u_date']
        # Check if sale is in the Reference Month
        # (Compare Year and Month)
        if s_date.year == reference_month_start.year and s_date.month == reference_month_start.month:
            month_revenue += rev
            month_cost += cost

    # Margin (Overall)
    avg_margin = 0
    gross_profit = total_revenue_period - total_cost_period
    if total_revenue_period > 0:
        avg_margin = (gross_profit / total_revenue_period) * 100
        
    # Presumed Revenue
    # If historical, presumes full month (actual).
    # If current, presumes projection.
    
    ref_month_name = reference_month_start.strftime('%B %Y')
    
    if is_historical_ref:
        presumed_rev = month_revenue # Month is done
        days_passed_label = "Complete Month"
    else:
        # Projection
        days_in_month_passed = (now - reference_month_start).days + 1
        # Total days in month
        next_m = reference_month_start.replace(day=28) + timedelta(days=4)
        last_day = next_m - timedelta(days=next_m.day)
        total_days = last_day.day
        
        if days_in_month_passed > 0:
            daily_avg = month_revenue / days_in_month_passed
            presumed_rev = daily_avg * total_days
        else:
            presumed_rev = 0
            
        days_passed_label = f"{days_in_month_passed}/{total_days} days"

    print("\n" + "="*40)
    print("📊 FINANCIAL REPORT")
    print("="*40)
    print(f"Data Used: {len(valid_sales)} sales ({min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')})")
    print("-" * 40)
    print(f"Global Average Margin: {avg_margin:.2f}%")
    print(f"(Based on Revenue R$ {total_revenue_period:,.2f} vs Cost R$ {total_cost_period:,.2f})")
    print("-" * 40)
    print(f"📅 REF MONTH: {ref_month_name} {'(Historical Only)' if is_historical_ref else '(Active)'}")
    print(f"Current Revenue: R$ {month_revenue:,.2f}")
    print(f"Time Elapsed: {days_passed_label}")
    print(f"🔮 ESTIMATED REVENUE: R$ {presumed_rev:,.2f}")
    if is_historical_ref:
         print("(Note: Using last active month as reference since current month has no data)")
    print("="*40)

if __name__ == "__main__":
    analyze_financials()
