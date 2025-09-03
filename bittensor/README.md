# TAO Stats Visualizer

This project fetches historical data from the TAO Stats API and generates comprehensive visualizations showing the relationship between TAO staked percentage and current supply over time.

## Features

- Fetches historical TAO staking data from the TAO Stats API
- Generates multiple visualizations including:
  - TAO staked percentage vs current supply over time
  - Total TAO staked over time
  - Staking percentage trends with moving averages
  - Supply growth analysis
  - Network growth metrics (accounts and balance holders)
- Provides detailed summary statistics
- Exports data to CSV format

## Generated Analysis Summary

Based on the latest run (data from 2024-12-27 to 2025-09-02):

- **Current Supply**: 9,789,555 TAO
- **Total Staked**: 7,158,628 TAO (73.13%)
- **Average Staking Rate**: 72.58%
- **Staking Range**: 70.06% - 74.52%
- **Total Accounts**: 378,205
- **Supply Growth**: 21.4% over the period
- **Accounts Growth**: 81.4% over the period

## Usage

1. Set up virtual environment:

```bash
python3 -m venv tao_env
source tao_env/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure API key:

```bash
# Copy the example environment file
cp .env.example .env
# Edit .env and add your TAO Stats API key
```

4. Run the visualizer:

```bash
python tao_stats_visualizer.py
```

## Configuration

### API Key Setup

The script uses environment variables for security. You have three options:

1. **Create a .env file** (recommended):

   ```bash
   TAO_STATS_API_KEY=your-api-key-here
   ```

2. **Set environment variable**:

   ```bash
   export TAO_STATS_API_KEY=your-api-key-here
   ```

3. **Modify config.py** (not recommended for production)

## Output Files

- `tao_staking_analysis_[timestamp].png` - Comprehensive visualization with 6 subplots
- `tao_staking_data_[timestamp].csv` - Raw data in CSV format

## API Information

Uses the TAO Stats API: https://api.taostats.io/

- Endpoint: `/api/stats/history/v1`
- Frequency: Daily data
- Authentication: API key included in the script

## Visualizations Generated

1. **Main Chart**: Staked % vs Current Supply over time (dual y-axis)
2. **Total TAO Staked**: Historical staking volume
3. **Staking Percentage Trend**: With average line
4. **Supply Growth**: Total supply evolution
5. **Network Growth**: Accounts and balance holders
6. **Moving Averages**: 7-day and 30-day staking percentage averages
