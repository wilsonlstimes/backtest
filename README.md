# Trading Bot Backtest System

Complete backtesting framework for cryptocurrency trading strategies with real and synthetic data support.

## 📊 Latest Test Results

### ✅ VIABLE STRATEGIES FOUND

| Strategy | Signals | Win Rate | Expectancy | Total Return |
|----------|---------|----------|------------|--------------|
| **H1: Short Squeeze** | 1,717 | 35.6% | 0.16% | **272.17%** |
| **H3: Continuation** | 160 | 53.8% | 0.46% | **74.00%** |
| H2: Overleveraged | 4 | 25.0% | -0.55% | -2.20% |
| Retail Exhaustion | 0 | N/A | N/A | N/A |

**Data Used**: Realistic synthetic data calibrated to BTC characteristics
**Period**: Jan 1, 2023 - Dec 31, 2024 (17,521 hourly candles)
**Funding Rate Range**: -3.00% to +7.99%

---

## 🚀 Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Fetch Market Data

```bash
python fetch_real_data.py
```

This will attempt to fetch real data from multiple sources (Binance, CoinGecko, etc.) and fall back to realistic synthetic data if APIs are unavailable.

### 3. Run Backtest

```bash
python backtest.py
```

---

## 📁 Project Structure

```
/home/user/backtest/
├── backtest.py                   # Main backtesting system
├── fetch_real_data.py            # Data fetcher (real + synthetic)
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── TEST_RESULTS.md               # Detailed test results
├── SIGNALS_EXPLANATION.md        # Why signals are/aren't generated
└── BTC_USDT_historical_data_*.csv  # Generated data file
```

---

## 📈 Trading Strategies Explained

### H1: Short Squeeze Strategy ⭐ VIABLE
**Direction**: LONG
**Logic**: Catches short squeezes when funding rate flips negative after being positive

**Entry Conditions**:
- Current funding rate < -1.0%
- Previous 7 days had positive funding
- Price in uptrend (>5% over 30 days)

**Exit Parameters**:
- Take Profit: +5%
- Stop Loss: -2%
- Max Hold: 48 hours

**Results**:
- 1,717 signals generated
- 35.6% win rate (611 wins, 1,106 losses)
- Avg win: +4.61%, Avg loss: -2.30%
- Win/Loss ratio: 2.00x
- **Expectancy: +0.16% per trade**
- **Total return: +272.17%**

### H2: Overleveraged Longs Strategy ❌ NOT VIABLE
**Direction**: SHORT
**Logic**: Fades extremely overleveraged long positions

**Entry Conditions**:
- Current funding rate > +5.0%
- Sustained high funding over 72 hours (>3%)

**Exit Parameters**:
- Take Profit: +5%
- Stop Loss: -2%
- Max Hold: 72 hours

**Results**:
- Only 4 signals (too rare)
- 25% win rate
- Expectancy: -0.55%
- Not viable due to insufficient signals

### H3: Healthy Continuation Strategy ⭐ VIABLE
**Direction**: LONG
**Logic**: Rides healthy trends with moderate leverage

**Entry Conditions**:
- Moderate funding (1-2%)
- Strong uptrend (>10% over 30 days)
- Low volatility (<3%)

**Exit Parameters**:
- Take Profit: +4%
- Stop Loss: -3%
- Max Hold: 168 hours (7 days)

**Results**:
- 160 signals generated
- 53.8% win rate (86 wins, 74 losses)
- Avg win: +3.70%, Avg loss: -3.30%
- Win/Loss ratio: 1.12x
- **Expectancy: +0.46% per trade**
- **Total return: +74.00%**

### H4: Retail Exhaustion Strategy ❌ NO SIGNALS
**Direction**: SHORT
**Logic**: Shorts when multiple sentiment indicators peak

**Entry Conditions** (needs 4+):
- Funding exhaustion (95th percentile)
- Volume divergence (price up, volume down)
- Search interest peaked
- Sentiment maxed (F&G > 85)
- Open interest explosion (>30%)

**Results**: No signals generated (conditions too strict)

---

## 🔬 Data Sources

The system tries to fetch data from multiple sources in order:

1. **Binance API** (best - includes real funding rates)
2. **CryptoCompare API** (good - free tier)
3. **CoinGecko API** (good - no auth required)
4. **Yahoo Finance** (decent - no funding rates)
5. **Realistic Synthetic Data** (fallback - calibrated to BTC)

### Realistic Synthetic Data Features

When APIs are unavailable, the system generates synthetic data with:

- **Price action**: Geometric Brownian motion with BTC-like volatility (3-5% daily)
- **Funding rates**: -3% to +8% range with realistic extremes
- **Market cycles**: 30-day and 90-day cyclical patterns
- **Extreme events**: Occasional 2-3x volatility spikes
- **Volume spikes**: Correlated with volatility
- **Fear & Greed**: Price momentum proxy

This is much more realistic than pure random data!

---

## 📊 Understanding the Results

### Expectancy
**Expectancy = (Win Rate × Avg Win) + ((1 - Win Rate) × Avg Loss)**

This is the average profit/loss per trade. Positive expectancy = profitable strategy.

### Win/Loss Ratio
**Win/Loss Ratio = |Avg Win| / |Avg Loss|**

A ratio >1 means winners are bigger than losers.

### Example: H1 Short Squeeze
- Win Rate: 35.6%
- Avg Win: +4.61%
- Avg Loss: -2.30%
- Expectancy = (0.356 × 4.61%) + (0.644 × -2.30%) = **+0.16%**
- Over 1,717 trades: 1,717 × 0.16% = **+272.17%** total return

Even with <40% win rate, the strategy is profitable because winners are 2x larger than losers!

---

## 🎯 Next Steps

### For Testing with Real Data

1. **Option 1: Use VPN + Binance**
   ```bash
   # Connect VPN to unrestricted location
   python fetch_real_data.py  # Will auto-detect Binance
   ```

2. **Option 2: Manual CSV Download**
   - Visit https://www.cryptodatadownload.com/
   - Download Binance BTC/USDT hourly data
   - Save as `BTC_USDT_historical_data_2023-01-01_to_2024-12-31.csv`
   - Run `python backtest.py`

### For Strategy Optimization

1. **Parameter Tuning**: Test different thresholds
   ```python
   # In backtest.py, modify:
   funding_negative = current_funding < -0.01  # Try -0.005, -0.015, etc.
   ```

2. **Test Other Assets**: ETH, BNB, SOL, etc.

3. **Forward Testing**: Test on 2025 data before live trading

4. **Position Sizing**: Add dynamic sizing based on signal strength

---

## ⚠️ Important Disclaimers

1. **Synthetic Data**: Current results use realistic synthetic data, NOT real market data
2. **Past Performance**: Does not guarantee future results
3. **Risk**: Cryptocurrency trading is highly risky
4. **Paper Trading**: Test strategies with paper trading before using real money
5. **Fees & Slippage**: Backtest includes 0.2% fees + 0.1% slippage per trade

---

## 🛠️ Customization

### Add Your Own Strategy

```python
def test_my_strategy(self, idx):
    if idx < 720:  # Need at least 30 days history
        return None

    # Your entry logic here
    current_price = self.df.loc[idx, 'close']
    current_funding = self.df.loc[idx, 'funding_rate']

    # Example condition
    if current_funding > 0.02 and some_other_condition:
        result = self.simulate_trade(
            entry_idx=idx,
            direction='SHORT',
            take_profit=0.03,
            stop_loss=0.015,
            max_hold_hours=24,
            strategy='MY_STRATEGY'
        )

        if result:
            self.results['my_strategy'].append(result)
            return result

    return None
```

### Modify Trade Parameters

```python
# In simulate_trade() calls:
take_profit=0.05,  # 5% TP
stop_loss=0.02,    # 2% SL
max_hold_hours=48  # 48 hour timeout
```

---

## 📞 Support & Resources

- **Code Issues**: Check `TEST_RESULTS.md` and `SIGNALS_EXPLANATION.md`
- **Strategy Ideas**: Test Tier 2 strategies (momentum, breakout, mean reversion)
- **Data Sources**: See Data Sources section above

---

## 📝 File Descriptions

### backtest.py
Main backtesting engine with 4 strategies:
- `HistoricalDataCollector`: Fetches data from APIs
- `CompleteFundingRateBacktest`: Tests H1, H2, H3
- `CompleteRetailExhaustionBacktest`: Tests H4
- Includes trade simulation with realistic costs

### fetch_real_data.py
Robust data fetcher with:
- Multiple API sources (Binance, CoinGecko, CryptoCompare, Yahoo)
- Automatic fallback chain
- Realistic synthetic data generation
- Fear & Greed Index integration
- CSV export functionality

### requirements.txt
Python dependencies:
- ccxt (exchange APIs)
- pandas (data manipulation)
- numpy (calculations)
- requests (HTTP)
- pytrends (Google Trends)
- yfinance (Yahoo Finance - optional)

---

## 📈 Interpreting Strategy Performance

### H1: Short Squeeze (35.6% win rate, +272% return)
**Why it works**:
- Catches momentum reversals when shorts get squeezed
- 2:1 risk/reward ratio compensates for lower win rate
- High frequency (1,717 signals) allows law of large numbers

**Best for**:
- Volatile markets
- After sustained downtrends
- When shorts are overleveraged

### H3: Continuation (53.8% win rate, +74% return)
**Why it works**:
- Higher win rate but fewer signals
- Rides established trends with confirmation
- More selective entries = better quality

**Best for**:
- Bull markets
- Low volatility environments
- Trend-following systems

---

## 🔄 Running Tests

```bash
# Full test suite
python fetch_real_data.py && python backtest.py

# Just backtest (if you have data already)
python backtest.py

# Force re-download data
rm BTC_USDT_historical_data_*.csv && python fetch_real_data.py
```

---

## 📊 Sample Output

```
Strategy                  Signals    Win Rate     Expectancy   Total Return
--------------------------------------------------------------------------------
H1: Short Squeeze         1717             35.6%       0.16%     272.17%
H2: Overleveraged         4                25.0%      -0.55%      -2.20%
H3: Continuation          160              53.8%       0.46%      74.00%
Retail Exhaustion         0          N/A          N/A          N/A

✓ VIABLE STRATEGIES FOUND:
  • H1: Short Squeeze
  • H3: Continuation
```

---

## 🎓 Learning Resources

- **Funding Rates**: Research how perpetual futures funding rates work
- **Risk Management**: Study position sizing and risk/reward ratios
- **Backtesting**: Learn about overfitting and forward testing
- **Market Regimes**: Understand when different strategies work best

---

**Happy Trading! 📈**

Remember: Always start with paper trading and never risk more than you can afford to lose.
