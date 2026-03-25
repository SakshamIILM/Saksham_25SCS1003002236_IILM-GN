import os
import requests
import logging
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# ========================
# Configuration
# ========================
CONFIG = {
    'CACHE_DIR': 'mcx_data_cache',
    'SYMBOL_MAP': {
        'gold': {
            'alpha_vantage': 'GOLD',
            'yahoo': 'GOLDM.NS',
            'investing': 'gold'
        },
        'silver': {
            'alpha_vantage': 'SILVER',
            'yahoo': 'SILVERM.NS',
            'investing': 'silver'
        },
        'crudeoil': {
            'alpha_vantage': 'CRUDEOIL',
            'yahoo': 'CRUDEOIL.NS',
            'investing': 'crude-oil'
        }
    },
    'DATA_SOURCES': ['alpha_vantage', 'yahoo', 'investing'],
    'REQUEST_HEADERS': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
}

# Create cache directory
os.makedirs(CONFIG['CACHE_DIR'], exist_ok=True)

# ========================
# Helper Functions
# ========================
def get_cache_path(symbol, source):
    return os.path.join(CONFIG['CACHE_DIR'], f"{symbol}_{source}.csv")

def is_cache_valid(file_path, max_age_hours=24):
    if not os.path.exists(file_path):
        return False
    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    return (datetime.now() - file_time) < timedelta(hours=max_age_hours)

# ========================
# Data Fetching Modules
# ========================
def fetch_alpha_vantage(symbol):
    """Fetch data from Alpha Vantage API"""
    api_key = os.getenv('ALPHA_VANTAGE_KEY')
    if not api_key:
        logging.error("Alpha Vantage API key not found")
        return None

    params = {
        'function': 'TIME_SERIES_DAILY',
        'symbol': CONFIG['SYMBOL_MAP'][symbol]['alpha_vantage'],
        'apikey': api_key
    }

    try:
        response = requests.get('https://www.alphavantage.co/query', params=params)
        data = response.json()
        
        if 'Time Series (Daily)' not in data:
            logging.error(f"Alpha Vantage error: {data.get('Error Message', 'Unknown error')}")
            return None
            
        df = pd.DataFrame.from_dict(data['Time Series (Daily)'], orient='index', dtype=float)
        df.index = pd.to_datetime(df.index)
        df = df.rename(columns={
            '1. open': 'open',
            '2. high': 'high',
            '3. low': 'low',
            '4. close': 'close',
            '5. volume': 'volume'
        })
        return df[['close']].rename(columns={'close': 'price'})
        
    except Exception as e:
        logging.error(f"Alpha Vantage failed: {str(e)}")
        return None

def fetch_yahoo_finance(symbol):
    """Fetch data from Yahoo Finance API"""
    yahoo_symbol = CONFIG['SYMBOL_MAP'][symbol]['yahoo']
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
    
    params = {
        'interval': '1d',
        'range': '5y'
    }

    try:
        response = requests.get(url, params=params, headers=CONFIG['REQUEST_HEADERS'])
        data = response.json()
        
        if 'chart' not in data or 'result' not in data['chart'] or not data['chart']['result']:
            logging.error("Yahoo Finance returned no data")
            return None
        
        timestamps = data['chart']['result'][0]['timestamp']
        prices = data['chart']['result'][0]['indicators']['quote'][0]['close']
        
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(timestamps, unit='s'),
            'price': prices
        }).set_index('timestamp')
        
        return df.dropna()
        
    except Exception as e:
        logging.error(f"Yahoo Finance failed: {str(e)}")
        return None

def fetch_investing_com(symbol):
    """Fetch data from Investing.com via web scraping"""
    investing_id = CONFIG['SYMBOL_MAP'][symbol]['investing']
    url = f"https://www.investing.com/commodities/{investing_id}-historical-data"
    
    try:
        response = requests.get(url, headers=CONFIG['REQUEST_HEADERS'])
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract data from the historical data table
        table = soup.find('table', {'id': 'curr_table'})
        if table is None:
            logging.error("Investing.com table not found")
            return None
        
        df = pd.read_html(str(table))[0]
        
        # Clean and format data
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        df['Price'] = df['Price'].str.replace(',', '').astype(float)
        
        return df[['Price']].rename(columns={'Price': 'price'})
        
    except Exception as e:
        logging.error(f"Investing.com failed: {str(e)}")
        return None

# ========================
# Unified Interface
# ========================
def fetch_mcx_data(symbol, force_refresh=False):
    """Fetch MCX data with multi-source fallback"""
    symbol = symbol.lower()
    if symbol not in CONFIG['SYMBOL_MAP']:
        raise ValueError(f"Unsupported symbol. Available: {', '.join(CONFIG['SYMBOL_MAP'].keys())}")

    combined_df = pd.DataFrame()

    for source in CONFIG['DATA_SOURCES']:
        cache_path = get_cache_path(symbol, source)
        
        # Use cached data if valid
        if not force_refresh and is_cache_valid(cache_path):
            try:
                df = pd.read_csv(cache_path, parse_dates=['timestamp'], index_col='timestamp')
                combined_df = pd.concat([combined_df, df])
                logging.info(f"Used cached data from {source}")
                continue
            except Exception as e:
                logging.error(f"Cache load failed: {str(e)}")

        # Fetch fresh data
        logging.info(f"Fetching from {source}...")
try:
    if source == 'alpha_vantage':
        df = fetch_alpha_vantage(symbol)
    elif source == 'yahoo':
        df = fetch_yahoo_finance(symbol)
    elif source == 'investing':
        df = fetch_investing_com(symbol)

    if df is not None and not df.empty:
        df.to_csv(cache_path)
        combined_df = pd.concat([combined_df, df])
        time.sleep(1)  # Rate limiting
except Exception as e:
    logging.error(f"{source} fetch error: {str(e)[:200]}")
 
