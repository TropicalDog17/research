#!/usr/bin/env python3
"""
TAO Stats Visualizer
Fetches data from TAO Stats API and generates graphs showing staked percentage vs current supply over time.
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
import time
import os
import glob
import yfinance as yf
from config import TAO_STATS_API_KEY, API_BASE_URL, REQUEST_DELAY, MAX_RETRIES, RATE_LIMIT_BACKOFF

class TaoStatsAPI:
    def __init__(self, api_key=None):
        self.base_url = API_BASE_URL
        
        # Use provided key, environment variable, or config default
        if api_key is None:
            api_key = TAO_STATS_API_KEY
        
        if not api_key or api_key == 'your-api-key-here':
            raise ValueError("Please set TAO_STATS_API_KEY environment variable or update config.py with your API key.")
        
        self.headers = {
            'Authorization': api_key,
            'accept': 'application/json'
        }
    
    def fetch_all_data(self, frequency="by_day", limit=50):
        """Fetch all historical data from the API"""
        all_data = []
        page = 1
        max_retries = MAX_RETRIES
        
        print("Fetching data from TAO Stats API...")
        
        while True:
            print(f"Fetching page {page}...")
            
            params = {
                'frequency': frequency,
                'page': page,
                'limit': limit
            }
            
            retry_count = 0
            while retry_count < max_retries:
                try:
                    response = requests.get(self.base_url, headers=self.headers, params=params)
                    
                    if response.status_code == 429:  # Rate limited
                        wait_time = 5 + (2 ** retry_count)  # Longer exponential backoff
                        print(f"Rate limited. Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'data' not in data or not data['data']:
                        print(f"No more data found on page {page}")
                        return all_data
                    
                    all_data.extend(data['data'])
                    
                    # Print pagination info
                    pagination = data.get('pagination', {})
                    total_pages = pagination.get('total_pages', 1)
                    total_items = pagination.get('total_items', len(all_data))
                    print(f"Page {page}/{total_pages}, fetched {len(data['data'])} items, total so far: {len(all_data)}/{total_items}")
                    
                    # Check if we've reached the last page
                    if page >= total_pages:
                        print(f"Reached last page: {page}")
                        return all_data
                    
                    break  # Success, exit retry loop
                    
                except requests.exceptions.RequestException as e:
                    print(f"Error fetching data (attempt {retry_count + 1}): {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count
                        print(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(f"Failed to fetch page {page} after {max_retries} attempts")
                        return all_data
            
            page += 1
            time.sleep(3)  # Much longer delay between successful requests to avoid rate limits
        
        print(f"Fetched {len(all_data)} data points total")
        return all_data
    
    def fetch_tao_price_data(self):
        """Fetch current TAO price from Yahoo Finance via yfinance"""
        try:
            print("Fetching current TAO price from Yahoo Finance...")
            tao = yf.Ticker('TAO22974-USD')
            
            # Get the most recent price
            hist = tao.history(period='1d')
            if len(hist) > 0:
                current_price = hist['Close'].iloc[-1]
                print(f"Current TAO price: ${current_price:.2f}")
                return current_price
            else:
                print("Warning: Could not fetch TAO price from Yahoo Finance, using default $500")
                return 500.0  # Fallback price
                
        except Exception as e:
            print(f"Error fetching price data from Yahoo Finance: {e}")
            print("Using default TAO price of $500")
            return 500.0
    
    def fetch_historical_tao_prices(self, from_date=None, to_date=None):
        """Fetch historical TAO price data from Yahoo Finance via yfinance"""
        try:
            print("Fetching historical TAO price data from Yahoo Finance...")
            
            # If no dates provided, fetch from the earliest possible date
            if from_date is None:
                from_date = "2023-03-20"  # First data point in our dataset
            if to_date is None:
                to_date = datetime.now().strftime("%Y-%m-%d")
            
            print(f"Fetching historical TAO price data from {from_date} to {to_date}")
            
            # Use yfinance to get historical data
            tao = yf.Ticker('TAO22974-USD')
            
            # Convert date strings to datetime objects for yfinance
            start_date = datetime.strptime(from_date, "%Y-%m-%d")
            end_date = datetime.strptime(to_date, "%Y-%m-%d")
            
            # Fetch historical data
            hist = tao.history(start=start_date, end=end_date)
            
            daily_prices = {}
            if len(hist) > 0:
                # Convert to daily prices dictionary
                for date_idx, row in hist.iterrows():
                    date_str = date_idx.strftime("%Y-%m-%d")
                    price = row['Close']
                    daily_prices[date_str] = price
                
                print(f"Successfully fetched {len(daily_prices)} days of historical price data from Yahoo Finance")
                print(f"Date range: {min(daily_prices.keys())} to {max(daily_prices.keys())}")
                
                # Show sample prices
                if len(daily_prices) > 0:
                    sample_dates = sorted(daily_prices.keys())
                    print(f"Sample prices: {sample_dates[0]}: ${daily_prices[sample_dates[0]]:.2f}, {sample_dates[-1]}: ${daily_prices[sample_dates[-1]]:.2f}")
                
                return daily_prices
            else:
                print("Warning: No historical price data found in Yahoo Finance")
                
                # Fallback: try to get current price
                try:
                    current_price = self.fetch_tao_price_data()
                    if current_price:
                        current_date = datetime.now().strftime("%Y-%m-%d")
                        daily_prices[current_date] = current_price
                        print(f"Fallback: Using current price ${current_price:.2f} for latest date")
                        return daily_prices
                except Exception as e:
                    print(f"Fallback current price fetch failed: {e}")
                
                return {}
                
        except Exception as e:
            print(f"Error in fetch_historical_tao_prices: {e}")
            print("Attempting fallback to current price...")
            
            # Final fallback
            try:
                current_price = self.fetch_tao_price_data()
                if current_price:
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    return {current_date: current_price}
            except Exception as fallback_e:
                print(f"Fallback also failed: {fallback_e}")
            
            return {}
    
    def save_price_data(self, price_data, filename=None):
        """Save historical price data to CSV file"""
        if not price_data:
            print("No price data to save")
            return None
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tao_price_data_{timestamp}.csv"
        
        # Convert to DataFrame
        df = pd.DataFrame([
            {'date': date, 'price_usd': price} 
            for date, price in sorted(price_data.items())
        ])
        
        # Save to CSV
        df.to_csv(filename, index=False)
        print(f"Saved {len(df)} price data points to {filename}")
        return filename
    
    def load_price_data(self, filename):
        """Load historical price data from CSV file"""
        try:
            df = pd.read_csv(filename)
            price_dict = dict(zip(df['date'], df['price_usd']))
            print(f"Loaded {len(price_dict)} price data points from {filename}")
            return price_dict
        except Exception as e:
            print(f"Error loading price data: {e}")
            return {}
    
    def get_or_fetch_price_data(self, start_date=None, end_date=None):
        """Get price data from local file or fetch from API if needed"""
        # Look for existing price data files
        import glob
        price_files = glob.glob("tao_price_data_*.csv")
        
        if price_files:
            # Use the most recent price data file
            latest_file = max(price_files, key=os.path.getctime)
            print(f"Found existing price data: {latest_file}")
            
            # Check if we should update the data
            file_date = datetime.fromtimestamp(os.path.getctime(latest_file))
            if (datetime.now() - file_date).days > 1:
                print("Price data is more than 1 day old, fetching updates...")
                # Fetch new data and merge with existing
                existing_prices = self.load_price_data(latest_file)
                new_prices = self.fetch_historical_tao_prices(start_date, end_date)
                
                # Merge data (new data overwrites old for same dates)
                combined_prices = {**existing_prices, **new_prices}
                
                # Save updated data
                new_filename = self.save_price_data(combined_prices)
                return combined_prices
            else:
                # Use existing data
                return self.load_price_data(latest_file)
        else:
            # No existing data, fetch from API
            print("No existing price data found, fetching from CoinGecko...")
            price_data = self.fetch_historical_tao_prices(start_date, end_date)
            if price_data:
                self.save_price_data(price_data)
            return price_data
    
    def process_data(self, raw_data, include_usd=True, price_data=None):
        """Process raw API data into a pandas DataFrame"""
        processed_data = []
        
        # Get historical price data if USD calculations are requested
        if include_usd and price_data is None:
            price_data = self.get_or_fetch_price_data()
        elif not include_usd:
            price_data = None
        
        for entry in raw_data:
            # Convert values from strings to integers (they're in smallest units)
            issued = int(entry['issued'])  # Total supply in raw units
            staked = int(entry['staked'])  # Total staked in raw units
            
            # Calculate staked percentage
            staked_percentage = (staked / issued) * 100 if issued > 0 else 0
            
            # Convert from raw units to TAO (divide by 10^9)
            issued_tao = issued / 1e9
            staked_tao = staked / 1e9
            circulating_tao = issued_tao - staked_tao  # Unstaked/circulating supply
            
            # Base data structure
            data_point = {
                'timestamp': pd.to_datetime(entry['timestamp']),
                'block_number': int(entry['block_number']),
                'issued_tao': issued_tao,
                'staked_tao': staked_tao,
                'circulating_tao': circulating_tao,
                'staked_percentage': staked_percentage,
                'circulating_percentage': (circulating_tao / issued_tao) * 100 if issued_tao > 0 else 0,
                'accounts': int(entry['accounts']),
                'balance_holders': int(entry['balance_holders'])
            }
            
            # Add USD calculations if requested
            if include_usd and price_data is not None:
                # Get the date for price lookup
                timestamp_obj = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                date_str = timestamp_obj.strftime("%Y-%m-%d")
                
                # Find the closest price data for this date
                tao_price_usd = None
                if date_str in price_data:
                    tao_price_usd = price_data[date_str]
                else:
                    # Find the closest available date
                    available_dates = sorted(price_data.keys())
                    for i, available_date in enumerate(available_dates):
                        if available_date >= date_str:
                            tao_price_usd = price_data[available_date]
                            break
                    
                    # If no future date found, use the last available price
                    if tao_price_usd is None and available_dates:
                        tao_price_usd = price_data[available_dates[-1]]
                
                if tao_price_usd is not None:
                    data_point.update({
                        'total_market_cap_usd': issued_tao * tao_price_usd,
                        'staked_market_cap_usd': staked_tao * tao_price_usd,
                        'circulating_market_cap_usd': circulating_tao * tao_price_usd,
                        'tao_price_usd': tao_price_usd,
                    })
            
            processed_data.append(data_point)
        
        df = pd.DataFrame(processed_data)
        df = df.sort_values('timestamp')  # Sort by date
        return df

def create_visualizations(df):
    """Create comprehensive visualizations of TAO staking data"""
    
    # Set style
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    
    # Check if USD data is available
    has_usd_data = 'tao_price_usd' in df.columns
    
    # Create figure with subplots
    fig = plt.figure(figsize=(20, 16))
    
    # 1. Total Supply vs Circulating Supply
    ax1 = plt.subplot(3, 2, 1)
    ax1.plot(df['timestamp'], df['issued_tao'], color='#2E86AB', linewidth=2.5, label='Total Supply')
    ax1.plot(df['timestamp'], df['circulating_tao'], color='#00BF63', linewidth=2.5, label='Circulating Supply')
    ax1.fill_between(df['timestamp'], df['circulating_tao'], alpha=0.3, color='#00BF63', label='Circulating (Unstaked)')
    ax1.fill_between(df['timestamp'], df['circulating_tao'], df['issued_tao'], alpha=0.3, color='#FF6B35', label='Staked')
    
    ax1.set_title('TAO Supply: Total vs Circulating Over Time', fontsize=14, fontweight='bold')
    ax1.set_ylabel('TAO Supply', fontsize=12)
    ax1.set_xlabel('Date', fontsize=12)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M'))
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 2. TAO Staked Amount Over Time (or Price if USD data available)
    ax2 = plt.subplot(3, 2, 2)
    if has_usd_data:
        ax2.plot(df['timestamp'], df['tao_price_usd'], color='#F18F01', linewidth=3)
        ax2.set_title('TAO Price (USD) Over Time', fontsize=14, fontweight='bold')
        ax2.set_ylabel('TAO Price (USD)', fontsize=12)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:.0f}'))
        
        # Add current price annotation
        current_price = df.iloc[-1]['tao_price_usd']
        ax2.annotate(f'Current: ${current_price:.2f}', 
                    xy=(df.iloc[-1]['timestamp'], current_price),
                    xytext=(10, 10), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                    fontsize=10, fontweight='bold')
    else:
        ax2.plot(df['timestamp'], df['staked_tao'], color='#F18F01', linewidth=2.5)
        ax2.set_title('Total TAO Staked Over Time', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Staked TAO', fontsize=12)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M'))
        
        # Add current staked annotation
        current_staked = df.iloc[-1]['staked_tao']
        ax2.annotate(f'Current: {current_staked/1e6:.1f}M TAO', 
                    xy=(df.iloc[-1]['timestamp'], current_staked),
                    xytext=(10, 10), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='orange', alpha=0.7),
                    fontsize=10, fontweight='bold')
    
    ax2.set_xlabel('Date', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # 3. Staking Percentage with Moving Averages
    ax3 = plt.subplot(3, 2, 3)
    
    # Calculate rolling averages
    df['staked_pct_7d'] = df['staked_percentage'].rolling(window=7, center=True).mean()
    df['staked_pct_30d'] = df['staked_percentage'].rolling(window=30, center=True).mean()
    
    ax3.plot(df['timestamp'], df['staked_percentage'], color='lightgray', alpha=0.6, linewidth=1, label='Daily')
    ax3.plot(df['timestamp'], df['staked_pct_7d'], color='#FF6B35', linewidth=2, label='7-day average')
    ax3.plot(df['timestamp'], df['staked_pct_30d'], color='#004E89', linewidth=2.5, label='30-day average')
    
    # Add horizontal line for average staking percentage
    avg_staked = df['staked_percentage'].mean()
    ax3.axhline(y=avg_staked, color='red', linestyle='--', alpha=0.7, 
                label=f'Overall Avg: {avg_staked:.1f}%')
    
    ax3.set_title('Staking Percentage Trends with Moving Averages', fontsize=14, fontweight='bold')
    ax3.set_ylabel('Staked Percentage (%)', fontsize=12)
    ax3.set_xlabel('Date', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # 4. Circulating Supply or Market Cap (depending on data availability)
    ax4 = plt.subplot(3, 2, 4)
    if has_usd_data:
        ax4.plot(df['timestamp'], df['circulating_market_cap_usd'], color='#00BF63', linewidth=2.5)
        ax4.set_title('Circulating Market Cap (USD) Over Time', fontsize=14, fontweight='bold')
        ax4.set_ylabel('Circulating Market Cap (USD)', fontsize=12)
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e9:.1f}B'))
        
        # Add current market cap annotation
        current_mcap = df.iloc[-1]['circulating_market_cap_usd']
        ax4.annotate(f'Current: ${current_mcap/1e9:.2f}B', 
                    xy=(df.iloc[-1]['timestamp'], current_mcap),
                    xytext=(10, 10), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7),
                    fontsize=10, fontweight='bold')
    else:
        ax4.plot(df['timestamp'], df['circulating_tao'], color='#00BF63', linewidth=2.5)
        ax4.set_title('Circulating TAO Supply Over Time', fontsize=14, fontweight='bold')
        ax4.set_ylabel('Circulating TAO', fontsize=12)
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M'))
        
        # Add current circulating annotation
        current_circ = df.iloc[-1]['circulating_tao']
        ax4.annotate(f'Current: {current_circ/1e6:.1f}M TAO', 
                    xy=(df.iloc[-1]['timestamp'], current_circ),
                    xytext=(10, 10), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7),
                    fontsize=10, fontweight='bold')
    
    ax4.set_xlabel('Date', fontsize=12)
    ax4.grid(True, alpha=0.3)
    
    # 5. Supply Comparison (Staked vs Circulating)
    ax5 = plt.subplot(3, 2, 5)
    if has_usd_data:
        ax5.stackplot(df['timestamp'], 
                      df['circulating_market_cap_usd'], 
                      df['staked_market_cap_usd'],
                      labels=['Circulating Market Cap', 'Staked Market Cap'],
                      colors=['#00BF63', '#FF6B35'], alpha=0.7)
        ax5.set_title('Market Cap: Circulating vs Staked (USD)', fontsize=14, fontweight='bold')
        ax5.set_ylabel('Market Cap (USD)', fontsize=12)
        ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e9:.1f}B'))
    else:
        ax5.stackplot(df['timestamp'], 
                      df['circulating_tao'], 
                      df['staked_tao'],
                      labels=['Circulating TAO', 'Staked TAO'],
                      colors=['#00BF63', '#FF6B35'], alpha=0.7)
        ax5.set_title('TAO Supply: Circulating vs Staked', fontsize=14, fontweight='bold')
        ax5.set_ylabel('TAO Supply', fontsize=12)
        ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M'))
    
    ax5.set_xlabel('Date', fontsize=12)
    ax5.grid(True, alpha=0.3)
    ax5.legend(loc='upper left')
    
    # 6. Network Growth: Total Accounts
    ax6 = plt.subplot(3, 2, 6)
    ax6.plot(df['timestamp'], df['accounts'], color='#7209B7', linewidth=2.5)
    ax6.set_title('Network Growth: Total Accounts Over Time', fontsize=14, fontweight='bold')
    ax6.set_ylabel('Number of Accounts', fontsize=12)
    ax6.set_xlabel('Date', fontsize=12)
    ax6.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e3:.0f}K'))
    ax6.grid(True, alpha=0.3)
    
    # Add current accounts annotation
    current_accounts = df.iloc[-1]['accounts']
    ax6.annotate(f'Current: {current_accounts:,}', 
                xy=(df.iloc[-1]['timestamp'], current_accounts),
                xytext=(10, 10), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.7),
                fontsize=10, fontweight='bold')
    
    plt.tight_layout(pad=3.0)
    return fig

def print_summary_stats(df):
    """Print summary statistics"""
    print("\n" + "="*60)
    print("TAO STAKING ANALYSIS SUMMARY")
    print("="*60)
    
    latest = df.iloc[-1]
    earliest = df.iloc[0]
    
    print(f"Data Period: {earliest['timestamp'].strftime('%Y-%m-%d')} to {latest['timestamp'].strftime('%Y-%m-%d')}")
    print(f"Total Data Points: {len(df)}")
    print()
    
    print("CURRENT STATUS (Latest Data):")
    print(f"  Current Supply: {latest['issued_tao']:,.0f} TAO")
    print(f"  Total Staked: {latest['staked_tao']:,.0f} TAO")
    print(f"  Circulating Supply: {latest['circulating_tao']:,.0f} TAO")
    print(f"  Staking Percentage: {latest['staked_percentage']:.2f}%")
    
    # Only show USD data if available
    if 'tao_price_usd' in latest and latest['tao_price_usd'] is not None:
        print(f"  TAO Price: ${latest['tao_price_usd']:.2f}")
        print(f"  Total Market Cap: ${latest['total_market_cap_usd']:,.0f}")
        print(f"  Circulating Market Cap: ${latest['circulating_market_cap_usd']:,.0f}")
    
    print(f"  Total Accounts: {latest['accounts']:,}")
    print(f"  Balance Holders: {latest['balance_holders']:,}")
    print()
    
    print("STAKING STATISTICS:")
    print(f"  Average Staked %: {df['staked_percentage'].mean():.2f}%")
    print(f"  Minimum Staked %: {df['staked_percentage'].min():.2f}%")
    print(f"  Maximum Staked %: {df['staked_percentage'].max():.2f}%")
    print(f"  Standard Deviation: {df['staked_percentage'].std():.2f}%")
    print()
    
    print("GROWTH METRICS:")
    supply_growth = ((latest['issued_tao'] - earliest['issued_tao']) / earliest['issued_tao']) * 100
    staked_growth = ((latest['staked_tao'] - earliest['staked_tao']) / earliest['staked_tao']) * 100
    accounts_growth = ((latest['accounts'] - earliest['accounts']) / earliest['accounts']) * 100
    
    print(f"  Supply Growth: {supply_growth:.1f}%")
    print(f"  Staked TAO Growth: {staked_growth:.1f}%")
    print(f"  Accounts Growth: {accounts_growth:.1f}%")
    print()

def get_price_for_date(price_data, date_str):
    """Helper function to get price for a specific date"""
    if date_str in price_data:
        return price_data[date_str]
    
    # Find the closest available date
    available_dates = sorted(price_data.keys())
    for available_date in available_dates:
        if available_date >= date_str:
            return price_data[available_date]
    
    # If no future date found, use the last available price
    if available_dates:
        return price_data[available_dates[-1]]
    
    return None

def main():
    """Main function to run the analysis"""
    print("TAO Stats Visualizer")
    print("===================")
    
    # Check if we have recent data file
    import glob
    existing_files = glob.glob("tao_staking_data_*.csv")
    
    if existing_files:
        latest_file = max(existing_files)
        print(f"\nFound existing data file: {latest_file}")
        user_input = input("Use existing data? (y/n): ").lower().strip()
        
        if user_input == 'y':
            print("Loading existing data...")
            df = pd.read_csv(latest_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
            print(f"Loaded {len(df)} data points from {latest_file}")
            
            # Check if we need to add price data to existing data
            api = TaoStatsAPI()
            has_dynamic_prices = False
            if 'tao_price_usd' in df.columns:
                # Check if all prices are the same (indicating static pricing)
                unique_prices = df['tao_price_usd'].nunique()
                has_dynamic_prices = unique_prices > 5  # Allow for some variation
            
            if 'tao_price_usd' not in df.columns or df['tao_price_usd'].isna().all() or not has_dynamic_prices:
                print("Adding/updating historical price data to existing dataset...")
                
                # Get price data
                start_date = df['timestamp'].min().strftime('%Y-%m-%d')
                end_date = df['timestamp'].max().strftime('%Y-%m-%d')
                price_data = api.get_or_fetch_price_data(start_date, end_date)
                
                if price_data:
                    # Add price data to existing dataframe
                    df['tao_price_usd'] = df['timestamp'].apply(
                        lambda ts: get_price_for_date(price_data, ts.strftime('%Y-%m-%d'))
                    )
                    
                    # Recalculate USD columns
                    df['total_market_cap_usd'] = df['issued_tao'] * df['tao_price_usd']
                    df['staked_market_cap_usd'] = df['staked_tao'] * df['tao_price_usd']
                    df['circulating_market_cap_usd'] = df['circulating_tao'] * df['tao_price_usd']
                    
                    print(f"Updated {len(df)} data points with historical prices")
        else:
            print("Fetching fresh data...")
            # Initialize API client
            api = TaoStatsAPI()
            
            # Fetch all data
            raw_data = api.fetch_all_data()
            
            if not raw_data:
                print("No data fetched. Exiting.")
                return
            
            # Process data WITH USD using historical prices
            df = api.process_data(raw_data, include_usd=True)
    else:
        print("No existing data found. Fetching fresh data...")
        # Initialize API client
        api = TaoStatsAPI()
        
        # Fetch all data
        raw_data = api.fetch_all_data()
        
        if not raw_data:
            print("No data fetched. Exiting.")
            return
        
        # Process data WITH USD using historical prices
        df = api.process_data(raw_data, include_usd=True)
    
    # Print summary statistics
    print_summary_stats(df)
    
    # Create visualizations
    print("\nGenerating visualizations...")
    fig = create_visualizations(df)
    
    # Save the plot
    output_file = f"tao_staking_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    fig.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Saved visualization to: {output_file}")
    
    # Show the plot
    plt.show()
    
    # Save data to CSV
    csv_file = f"tao_staking_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(csv_file, index=False)
    print(f"Saved data to: {csv_file}")

if __name__ == "__main__":
    main()
