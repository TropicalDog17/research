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
    
    def process_data(self, raw_data):
        """Process raw API data into a pandas DataFrame"""
        processed_data = []
        
        for entry in raw_data:
            # Convert values from strings to integers (they're in smallest units)
            issued = int(entry['issued'])  # Total supply in raw units
            staked = int(entry['staked'])  # Total staked in raw units
            
            # Calculate staked percentage
            staked_percentage = (staked / issued) * 100 if issued > 0 else 0
            
            # Convert from raw units to TAO (divide by 10^9)
            issued_tao = issued / 1e9
            staked_tao = staked / 1e9
            
            processed_data.append({
                'timestamp': pd.to_datetime(entry['timestamp']),
                'block_number': int(entry['block_number']),
                'issued_tao': issued_tao,
                'staked_tao': staked_tao,
                'staked_percentage': staked_percentage,
                'accounts': int(entry['accounts']),
                'balance_holders': int(entry['balance_holders'])
            })
        
        df = pd.DataFrame(processed_data)
        df = df.sort_values('timestamp')  # Sort by date
        return df

def create_visualizations(df):
    """Create comprehensive visualizations of TAO staking data"""
    
    # Set style
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    
    # Create figure with subplots
    fig = plt.figure(figsize=(20, 16))
    
    # 1. Main chart: Staked % vs Current Supply over time
    ax1 = plt.subplot(3, 2, 1)
    ax1_twin = ax1.twinx()
    
    # Plot staked percentage
    line1 = ax1.plot(df['timestamp'], df['staked_percentage'], 
                     color='#2E86AB', linewidth=2.5, label='Staked %')
    ax1.set_ylabel('Staked Percentage (%)', color='#2E86AB', fontsize=12, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor='#2E86AB')
    ax1.grid(True, alpha=0.3)
    
    # Plot current supply
    line2 = ax1_twin.plot(df['timestamp'], df['issued_tao'], 
                         color='#A23B72', linewidth=2.5, label='Current Supply (TAO)')
    ax1_twin.set_ylabel('Current Supply (TAO)', color='#A23B72', fontsize=12, fontweight='bold')
    ax1_twin.tick_params(axis='y', labelcolor='#A23B72')
    
    # Format y-axis for supply
    ax1_twin.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M'))
    
    ax1.set_title('TAO Staked Percentage vs Current Supply Over Time', 
                  fontsize=16, fontweight='bold', pad=20)
    ax1.set_xlabel('Date', fontsize=12)
    
    # Add legend
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left')
    
    # 2. Staked TAO over time
    ax2 = plt.subplot(3, 2, 2)
    ax2.plot(df['timestamp'], df['staked_tao'], color='#F18F01', linewidth=2.5)
    ax2.set_title('Total TAO Staked Over Time', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Staked TAO', fontsize=12)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M'))
    ax2.grid(True, alpha=0.3)
    
    # 3. Staked percentage trend
    ax3 = plt.subplot(3, 2, 3)
    ax3.plot(df['timestamp'], df['staked_percentage'], color='#C73E1D', linewidth=2.5)
    ax3.set_title('Staking Percentage Trend', fontsize=14, fontweight='bold')
    ax3.set_ylabel('Staked Percentage (%)', fontsize=12)
    ax3.set_xlabel('Date', fontsize=12)
    ax3.grid(True, alpha=0.3)
    
    # Add horizontal line for average staking percentage
    avg_staked = df['staked_percentage'].mean()
    ax3.axhline(y=avg_staked, color='red', linestyle='--', alpha=0.7, 
                label=f'Average: {avg_staked:.1f}%')
    ax3.legend()
    
    # 4. Supply growth
    ax4 = plt.subplot(3, 2, 4)
    ax4.plot(df['timestamp'], df['issued_tao'], color='#3E92CC', linewidth=2.5)
    ax4.set_title('Total Supply Growth', fontsize=14, fontweight='bold')
    ax4.set_ylabel('Total Supply (TAO)', fontsize=12)
    ax4.set_xlabel('Date', fontsize=12)
    ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M'))
    ax4.grid(True, alpha=0.3)
    
    # 5. Accounts growth
    ax5 = plt.subplot(3, 2, 5)
    ax5.plot(df['timestamp'], df['accounts'], color='#7209B7', linewidth=2.5, label='Total Accounts')
    ax5.plot(df['timestamp'], df['balance_holders'], color='#560BAD', linewidth=2.5, label='Balance Holders')
    ax5.set_title('Network Growth: Accounts & Balance Holders', fontsize=14, fontweight='bold')
    ax5.set_ylabel('Number of Accounts', fontsize=12)
    ax5.set_xlabel('Date', fontsize=12)
    ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e3:.0f}K'))
    ax5.grid(True, alpha=0.3)
    ax5.legend()
    
    # 6. Staking ratio analysis
    ax6 = plt.subplot(3, 2, 6)
    
    # Calculate rolling averages
    df['staked_pct_7d'] = df['staked_percentage'].rolling(window=7, center=True).mean()
    df['staked_pct_30d'] = df['staked_percentage'].rolling(window=30, center=True).mean()
    
    ax6.plot(df['timestamp'], df['staked_percentage'], color='lightgray', alpha=0.5, linewidth=1, label='Daily')
    ax6.plot(df['timestamp'], df['staked_pct_7d'], color='#FF6B35', linewidth=2, label='7-day average')
    ax6.plot(df['timestamp'], df['staked_pct_30d'], color='#004E89', linewidth=2.5, label='30-day average')
    
    ax6.set_title('Staking Percentage with Moving Averages', fontsize=14, fontweight='bold')
    ax6.set_ylabel('Staked Percentage (%)', fontsize=12)
    ax6.set_xlabel('Date', fontsize=12)
    ax6.grid(True, alpha=0.3)
    ax6.legend()
    
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
    print(f"  Staking Percentage: {latest['staked_percentage']:.2f}%")
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

def main():
    """Main function to run the analysis"""
    print("TAO Stats Visualizer")
    print("===================")
    
    # Initialize API client
    api = TaoStatsAPI()
    
    # Fetch all data
    raw_data = api.fetch_all_data()
    
    if not raw_data:
        print("No data fetched. Exiting.")
        return
    
    # Process data
    df = api.process_data(raw_data)
    
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
