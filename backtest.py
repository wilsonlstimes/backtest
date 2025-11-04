import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import requests
from pytrends.request import TrendReq
import json

class HistoricalDataCollector:
    """
    Collect all necessary historical data for backtesting
    Uses alternative data sources if Binance is restricted
    """

    def __init__(self, use_coinbase=True):
        if use_coinbase:
            print("Using Coinbase as data source...")
            self.exchange = ccxt.coinbase({
                'enableRateLimit': True,
                'timeout': 30000
            })
            self.use_coinbase = True
        else:
            print("Using Binance as data source...")
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'},
                'timeout': 30000
            })
            self.use_coinbase = False

        self.data = {}

        # Test connection
        try:
            print("Testing connection...")
            markets = self.exchange.fetch_markets()
            print(f"✓ Connection successful! Found {len(markets)} markets")
        except Exception as e:
            print(f"✗ Connection test failed: {e}")
            raise

    def fetch_ohlcv(self, symbol='BTC/USDT', timeframe='1h',
                    start_date='2023-01-01', end_date='2024-12-31'):
        """
        Fetch OHLCV data from Binance
        """
        print(f"Fetching OHLCV data for {symbol}...")

        since = self.exchange.parse8601(start_date + 'T00:00:00Z')
        end = self.exchange.parse8601(end_date + 'T23:59:59Z')

        all_ohlcv = []

        while since < end:
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe,
                    since=since,
                    limit=1000
                )

                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + 1

                print(f"  Fetched {len(all_ohlcv)} candles so far...")
                time.sleep(self.exchange.rateLimit / 1000)

            except Exception as e:
                print(f"Error fetching OHLCV: {e}")
                time.sleep(5)
                continue

        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        print(f"  Total candles: {len(df)}")
        return df

    def fetch_funding_rates(self, symbol='BTC/USDT',
                           start_date='2023-01-01', end_date='2024-12-31'):
        """
        Fetch historical funding rates
        Note: Coinbase doesn't have perpetual futures, so we'll simulate funding
        """
        print(f"Fetching funding rate data for {symbol}...")

        if self.use_coinbase:
            print("  Note: Coinbase doesn't have funding rates (spot exchange)")
            print("  Creating synthetic funding rate based on price momentum...")

            # We'll create this after getting OHLCV data
            # Return empty for now, will be calculated in merge
            return pd.DataFrame()

        # Original Binance code
        binance_symbol = symbol.replace('/', '')
        since = self.exchange.parse8601(start_date + 'T00:00:00Z')
        end = self.exchange.parse8601(end_date + 'T23:59:59Z')

        all_funding = []

        while since < end:
            try:
                funding = self.exchange.fapiPublic_get_fundingrate({
                    'symbol': binance_symbol,
                    'startTime': since,
                    'limit': 1000
                })

                if not funding:
                    break

                all_funding.extend(funding)
                since = int(funding[-1]['fundingTime']) + 1

                print(f"  Fetched {len(all_funding)} funding rates so far...")
                time.sleep(self.exchange.rateLimit / 1000)

            except Exception as e:
                print(f"Error fetching funding rates: {e}")
                time.sleep(5)
                continue

        df = pd.DataFrame(all_funding)
        df['timestamp'] = pd.to_datetime(df['fundingTime'], unit='ms')
        df['funding_rate'] = df['fundingRate'].astype(float)
        df = df[['timestamp', 'funding_rate']]

        print(f"  Total funding rates: {len(df)}")
        return df

    def fetch_open_interest(self, symbol='BTC/USDT',
                           start_date='2023-01-01', end_date='2024-12-31'):
        """
        Fetch open interest data
        Note: Coinbase doesn't have futures, so we skip this
        """
        print(f"Fetching open interest data for {symbol}...")

        if self.use_coinbase:
            print("  Note: Coinbase is spot-only, no open interest data")
            return pd.DataFrame()

        # Original Binance code
        binance_symbol = symbol.replace('/', '')
        since = self.exchange.parse8601(start_date + 'T00:00:00Z')
        end = self.exchange.parse8601(end_date + 'T23:59:59Z')

        all_oi = []

        while since < end:
            try:
                oi = self.exchange.fapiPublic_get_openinteresthist({
                    'symbol': binance_symbol,
                    'period': '1h',
                    'startTime': since,
                    'limit': 500
                })

                if not oi:
                    break

                all_oi.extend(oi)
                since = int(oi[-1]['timestamp']) + 3600000

                print(f"  Fetched {len(all_oi)} OI data points so far...")
                time.sleep(self.exchange.rateLimit / 1000)

            except Exception as e:
                print(f"Error fetching OI: {e}")
                time.sleep(5)
                continue

        if not all_oi:
            return pd.DataFrame()

        df = pd.DataFrame(all_oi)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['open_interest'] = df['sumOpenInterest'].astype(float)
        df = df[['timestamp', 'open_interest']]

        print(f"  Total OI data points: {len(df)}")
        return df

    def fetch_google_trends(self, keyword='bitcoin',
                           start_date='2023-01-01', end_date='2024-12-31'):
        """
        Fetch Google Trends data
        """
        print(f"Fetching Google Trends for '{keyword}'...")

        try:
            pytrends = TrendReq(hl='en-US', tz=0)
            timeframe = f'{start_date} {end_date}'

            pytrends.build_payload([keyword], timeframe=timeframe)
            trends_df = pytrends.interest_over_time()

            if trends_df.empty:
                print("  No trends data available")
                return pd.DataFrame()

            trends_df = trends_df.reset_index()
            trends_df = trends_df.rename(columns={
                'date': 'timestamp',
                keyword: 'search_interest'
            })
            trends_df = trends_df[['timestamp', 'search_interest']]

            print(f"  Total trends data points: {len(trends_df)}")
            return trends_df

        except Exception as e:
            print(f"Error fetching Google Trends: {e}")
            return pd.DataFrame()

    def fetch_fear_greed_index(self, start_date='2023-01-01', end_date='2024-12-31'):
        """
        Fetch Crypto Fear & Greed Index
        """
        print("Fetching Fear & Greed Index...")

        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            days = (end - start).days

            url = f"https://api.alternative.me/fng/?limit={days}&format=json"
            response = requests.get(url)
            data = response.json()

            if 'data' not in data:
                print("  No fear & greed data available")
                return pd.DataFrame()

            df = pd.DataFrame(data['data'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df['fear_greed'] = df['value'].astype(int)
            df = df[['timestamp', 'fear_greed']]
            df = df.sort_values('timestamp').reset_index(drop=True)

            print(f"  Total fear & greed data points: {len(df)}")
            return df

        except Exception as e:
            print(f"Error fetching Fear & Greed: {e}")
            return pd.DataFrame()

    def merge_all_data(self, ohlcv_df, funding_df, oi_df, trends_df, fg_df):
        """
        Merge all data sources
        """
        print("\nMerging all data sources...")

        df = ohlcv_df.copy()

        # If using Coinbase (no funding data), create synthetic funding rate
        if funding_df.empty:
            print("  Creating synthetic funding rate from price momentum...")
            # Calculate 8-hour momentum as proxy for funding
            df['returns_8h'] = df['close'].pct_change(8)
            # Funding rate typically correlates with momentum
            # Normalize to typical funding rate range (-0.05% to +0.05%)
            df['funding_rate'] = df['returns_8h'].clip(-0.01, 0.01) * 0.1
            df['funding_rate'] = df['funding_rate'].fillna(0)
        else:
            df = pd.merge_asof(
                df.sort_values('timestamp'),
                funding_df.sort_values('timestamp'),
                on='timestamp',
                direction='backward'
            )

        # Handle OI
        if not oi_df.empty:
            df = pd.merge_asof(
                df.sort_values('timestamp'),
                oi_df.sort_values('timestamp'),
                on='timestamp',
                direction='backward'
            )
        else:
            # Use volume as proxy for OI
            print("  Using volume as proxy for open interest...")
            df['open_interest'] = df['volume'].rolling(window=24).mean()

        # Merge Google Trends
        if not trends_df.empty:
            df = pd.merge_asof(
                df.sort_values('timestamp'),
                trends_df.sort_values('timestamp'),
                on='timestamp',
                direction='backward'
            )
        else:
            df['search_interest'] = 50

        # Merge Fear & Greed
        if not fg_df.empty:
            df = pd.merge_asof(
                df.sort_values('timestamp'),
                fg_df.sort_values('timestamp'),
                on='timestamp',
                direction='backward'
            )
        else:
            df['fear_greed'] = 50

        df['volume_ma_7d'] = df['volume'].rolling(window=168).mean()

        print(f"  Final merged dataset: {len(df)} rows")
        print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

        return df

    def collect_all_data(self, symbol='BTC/USDT',
                        start_date='2023-01-01', end_date='2024-12-31'):
        """
        Collect all data needed for backtesting
        """
        print(f"\n{'='*60}")
        print(f"COLLECTING HISTORICAL DATA")
        print(f"{'='*60}\n")

        ohlcv_df = self.fetch_ohlcv(symbol, '1h', start_date, end_date)
        funding_df = self.fetch_funding_rates(symbol, start_date, end_date)
        oi_df = self.fetch_open_interest(symbol, start_date, end_date)
        trends_df = self.fetch_google_trends('bitcoin', start_date, end_date)
        fg_df = self.fetch_fear_greed_index(start_date, end_date)

        merged_df = self.merge_all_data(ohlcv_df, funding_df, oi_df, trends_df, fg_df)

        filename = f"{symbol.replace('/', '_')}_historical_data_{start_date}_to_{end_date}.csv"
        merged_df.to_csv(filename, index=False)
        print(f"\nData saved to: {filename}")

        return merged_df


class CompleteFundingRateBacktest:
    """
    Full implementation of Funding Rate backtests
    """

    def __init__(self, data_df):
        self.df = data_df.copy()
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)

        self.results = {
            'h1_short_squeeze': [],
            'h2_overleveraged': [],
            'h3_continuation': []
        }

        self.fee_rate = 0.002
        self.slippage = 0.001
        self.total_cost = self.fee_rate + self.slippage

    def calculate_percentile(self, value, historical_values):
        if len(historical_values) == 0:
            return 50
        sorted_vals = sorted(historical_values)
        position = sum(1 for v in sorted_vals if v < value)
        return (position / len(sorted_vals)) * 100

    def test_h1_short_squeeze(self, idx):
        if idx < 720:
            return None

        current_funding = self.df.loc[idx, 'funding_rate']
        lookback_hours = 168
        prev_funding = self.df.loc[idx-lookback_hours:idx-1, 'funding_rate'].values
        prev_funding_unique = prev_funding[::8]
        was_positive = np.mean(prev_funding_unique) > 0

        current_price = self.df.loc[idx, 'close']
        price_30d_ago = self.df.loc[idx-720, 'close']
        price_change_30d = (current_price / price_30d_ago - 1)

        funding_negative = current_funding < -0.01
        in_uptrend = price_change_30d > 0.05

        if funding_negative and was_positive and in_uptrend:
            result = self.simulate_trade(
                entry_idx=idx,
                direction='LONG',
                take_profit=0.05,
                stop_loss=0.02,
                max_hold_hours=48,
                strategy='H1_SHORT_SQUEEZE'
            )

            if result:
                self.results['h1_short_squeeze'].append(result)
                return result

        return None

    def test_h2_overleveraged_longs(self, idx):
        if idx < 720:
            return None

        current_funding = self.df.loc[idx, 'funding_rate']
        prev_72h_funding = self.df.loc[idx-72:idx-1, 'funding_rate'].values
        prev_funding_unique = prev_72h_funding[::8]

        funding_very_high = current_funding > 0.05
        sustained_high = np.mean(prev_funding_unique) > 0.03

        if funding_very_high and sustained_high:
            result = self.simulate_trade(
                entry_idx=idx,
                direction='SHORT',
                take_profit=0.05,
                stop_loss=0.02,
                max_hold_hours=72,
                strategy='H2_OVERLEVERAGED'
            )

            if result:
                self.results['h2_overleveraged'].append(result)
                return result

        return None

    def test_h3_healthy_continuation(self, idx):
        if idx < 720:
            return None

        current_funding = self.df.loc[idx, 'funding_rate']
        current_price = self.df.loc[idx, 'close']
        price_30d_ago = self.df.loc[idx-720, 'close']
        price_change_30d = (current_price / price_30d_ago - 1)

        prices_7d = self.df.loc[idx-168:idx, 'close'].values
        returns = np.diff(prices_7d) / prices_7d[:-1]
        volatility = np.std(returns)

        funding_moderate = 0.01 <= current_funding <= 0.02
        strong_uptrend = price_change_30d > 0.10
        low_vol = volatility < 0.03

        if funding_moderate and strong_uptrend and low_vol:
            result = self.simulate_trade(
                entry_idx=idx,
                direction='LONG',
                take_profit=0.04,
                stop_loss=0.03,
                max_hold_hours=168,
                strategy='H3_CONTINUATION'
            )

            if result:
                self.results['h3_continuation'].append(result)
                return result

        return None

    def simulate_trade(self, entry_idx, direction, take_profit,
                      stop_loss, max_hold_hours, strategy):
        entry_price = self.df.loc[entry_idx, 'close']
        entry_time = self.df.loc[entry_idx, 'timestamp']

        result = {
            'strategy': strategy,
            'entry_time': entry_time,
            'entry_price': entry_price,
            'direction': direction,
            'exit_time': None,
            'exit_price': None,
            'exit_reason': None,
            'hold_hours': 0,
            'gross_profit_pct': 0,
            'net_profit_pct': 0
        }

        for hours in range(1, min(max_hold_hours + 1, len(self.df) - entry_idx)):
            future_idx = entry_idx + hours

            if future_idx >= len(self.df):
                break

            candle = self.df.loc[future_idx]

            if direction == 'LONG':
                if candle['high'] >= entry_price * (1 + take_profit):
                    result['exit_time'] = candle['timestamp']
                    result['exit_price'] = entry_price * (1 + take_profit)
                    result['exit_reason'] = 'TAKE_PROFIT'
                    result['hold_hours'] = hours
                    result['gross_profit_pct'] = take_profit
                    break

                if candle['low'] <= entry_price * (1 - stop_loss):
                    result['exit_time'] = candle['timestamp']
                    result['exit_price'] = entry_price * (1 - stop_loss)
                    result['exit_reason'] = 'STOP_LOSS'
                    result['hold_hours'] = hours
                    result['gross_profit_pct'] = -stop_loss
                    break

            elif direction == 'SHORT':
                if candle['low'] <= entry_price * (1 - take_profit):
                    result['exit_time'] = candle['timestamp']
                    result['exit_price'] = entry_price * (1 - take_profit)
                    result['exit_reason'] = 'TAKE_PROFIT'
                    result['hold_hours'] = hours
                    result['gross_profit_pct'] = take_profit
                    break

                if candle['high'] >= entry_price * (1 + stop_loss):
                    result['exit_time'] = candle['timestamp']
                    result['exit_price'] = entry_price * (1 + stop_loss)
                    result['exit_reason'] = 'STOP_LOSS'
                    result['hold_hours'] = hours
                    result['gross_profit_pct'] = -stop_loss
                    break

        if result['exit_reason'] is None:
            timeout_idx = min(entry_idx + max_hold_hours, len(self.df) - 1)
            candle = self.df.loc[timeout_idx]

            result['exit_time'] = candle['timestamp']
            result['exit_price'] = candle['close']
            result['exit_reason'] = 'TIMEOUT'
            result['hold_hours'] = timeout_idx - entry_idx

            if direction == 'LONG':
                result['gross_profit_pct'] = (candle['close'] / entry_price - 1)
            else:
                result['gross_profit_pct'] = (entry_price / candle['close'] - 1)

        result['net_profit_pct'] = result['gross_profit_pct'] - self.total_cost

        return result

    def run_backtest(self):
        print(f"\n{'='*60}")
        print("RUNNING FUNDING RATE BACKTESTS")
        print(f"{'='*60}")

        start_idx = 720

        for idx in range(start_idx, len(self.df) - 168):
            self.test_h1_short_squeeze(idx)
            self.test_h2_overleveraged_longs(idx)
            self.test_h3_healthy_continuation(idx)

            if idx % 1000 == 0:
                progress = ((idx - start_idx) / (len(self.df) - 168 - start_idx)) * 100
                print(f"  Progress: {progress:.1f}%")

        print("\nBacktest complete.")
        self.print_results()

    def print_results(self):
        for hypothesis_name, trades in self.results.items():
            print(f"\n{'='*60}")
            print(f"HYPOTHESIS: {hypothesis_name.upper()}")
            print(f"{'='*60}")

            if not trades:
                print("NO SIGNALS GENERATED")
                continue

            total_trades = len(trades)
            winning_trades = [t for t in trades if t['net_profit_pct'] > 0]
            losing_trades = [t for t in trades if t['net_profit_pct'] <= 0]

            win_rate = len(winning_trades) / total_trades
            avg_win = np.mean([t['net_profit_pct'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['net_profit_pct'] for t in losing_trades]) if losing_trades else 0
            avg_trade = np.mean([t['net_profit_pct'] for t in trades])
            total_return = sum(t['net_profit_pct'] for t in trades)

            exit_reasons = {}
            for trade in trades:
                reason = trade['exit_reason']
                exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

            expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

            print(f"Total Signals: {total_trades}")
            print(f"Winning Trades: {len(winning_trades)} ({win_rate*100:.1f}%)")
            print(f"Losing Trades: {len(losing_trades)} ({(1-win_rate)*100:.1f}%)")
            print(f"\nAverage Win: {avg_win*100:.2f}%")
            print(f"Average Loss: {avg_loss*100:.2f}%")
            print(f"Average Trade: {avg_trade*100:.2f}%")
            print(f"Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}x" if avg_loss != 0 else "N/A")
            print(f"\nExpectancy per trade: {expectancy*100:.2f}%")
            print(f"Total Return: {total_return*100:.2f}%")

            print(f"\nExit Reasons:")
            for reason, count in exit_reasons.items():
                print(f"  {reason}: {count} ({count/total_trades*100:.1f}%)")


class CompleteRetailExhaustionBacktest:
    """
    Retail Exhaustion backtest
    """

    def __init__(self, data_df):
        self.df = data_df.copy()
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)
        self.results = []
        self.fee_rate = 0.002
        self.slippage = 0.001
        self.total_cost = self.fee_rate + self.slippage

    def calculate_percentile(self, value, historical_values):
        if len(historical_values) == 0:
            return 50
        sorted_vals = sorted(historical_values)
        position = sum(1 for v in sorted_vals if v < value)
        return (position / len(sorted_vals)) * 100

    def detect_exhaustion_signals(self, idx):
        if idx < 2160:
            return None, 0

        signals = {}

        current_funding = self.df.loc[idx, 'funding_rate']
        funding_30d = self.df.loc[idx-720:idx-1, 'funding_rate'].values
        funding_30d_unique = funding_30d[::8]
        funding_percentile = self.calculate_percentile(current_funding, funding_30d_unique)
        signals['funding_exhaustion'] = funding_percentile > 95

        current_price = self.df.loc[idx, 'close']
        price_7d_ago = self.df.loc[idx-168, 'close']
        price_change = (current_price / price_7d_ago - 1)

        current_volume = self.df.loc[idx, 'volume']
        volume_7d_ago = self.df.loc[idx-168, 'volume']
        volume_change = (current_volume / volume_7d_ago - 1)

        signals['volume_divergence'] = (price_change > 0.10 and volume_change < -0.20)

        if 'search_interest' in self.df.columns:
            current_search = self.df.loc[idx, 'search_interest']
            search_90d = self.df.loc[max(0, idx-2160):idx-1, 'search_interest'].values
            search_percentile = self.calculate_percentile(current_search, search_90d)
            signals['search_peaked'] = search_percentile > 90
        else:
            signals['search_peaked'] = False

        if 'fear_greed' in self.df.columns:
            current_sentiment = self.df.loc[idx, 'fear_greed']
            signals['sentiment_maxed'] = current_sentiment > 85
        else:
            signals['sentiment_maxed'] = False

        if 'open_interest' in self.df.columns:
            current_oi = self.df.loc[idx, 'open_interest']
            oi_7d_ago = self.df.loc[idx-168, 'open_interest']
            oi_change = (current_oi / oi_7d_ago - 1) if oi_7d_ago > 0 else 0
            signals['oi_explosion'] = (oi_change > 0.30 and funding_percentile > 90)
        else:
            signals['oi_explosion'] = False

        signal_count = sum(signals.values())
        return signals, signal_count

    def run_backtest(self):
        print(f"\n{'='*60}")
        print("RUNNING RETAIL EXHAUSTION BACKTEST")
        print(f"{'='*60}")

        start_idx = 2160

        for idx in range(start_idx, len(self.df) - 48):
            signals, signal_count = self.detect_exhaustion_signals(idx)

            if signals and signal_count >= 4:
                entry_price = self.df.loc[idx, 'close']
                entry_time = self.df.loc[idx, 'timestamp']

                result = {
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'signal_count': signal_count,
                    'signals': signals.copy(),
                    'direction': 'SHORT',
                    'net_profit_pct': 0
                }

                # Simulate trade
                for hours in range(1, 25):
                    future_idx = idx + hours
                    if future_idx >= len(self.df):
                        break

                    candle = self.df.loc[future_idx]

                    if candle['low'] <= entry_price * 0.96:  # 4% TP
                        result['net_profit_pct'] = 0.04 - self.total_cost
                        break
                    elif candle['high'] >= entry_price * 1.02:  # 2% SL
                        result['net_profit_pct'] = -0.02 - self.total_cost
                        break
                else:
                    # Timeout
                    exit_price = self.df.loc[min(idx+24, len(self.df)-1), 'close']
                    result['net_profit_pct'] = (entry_price / exit_price - 1) - self.total_cost

                self.results.append(result)

            if idx % 1000 == 0:
                progress = ((idx - start_idx) / (len(self.df) - 48 - start_idx)) * 100
                print(f"  Progress: {progress:.1f}%")

        print("\nBacktest complete.")
        self.print_results()

    def print_results(self):
        print(f"\n{'='*60}")
        print("RETAIL EXHAUSTION RESULTS")
        print(f"{'='*60}")

        if not self.results:
            print("NO EXHAUSTION SIGNALS DETECTED")
            return

        total_signals = len(self.results)
        winning_trades = [t for t in self.results if t['net_profit_pct'] > 0]
        losing_trades = [t for t in self.results if t['net_profit_pct'] <= 0]

        win_rate = len(winning_trades) / total_signals
        avg_win = np.mean([t['net_profit_pct'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['net_profit_pct'] for t in losing_trades]) if losing_trades else 0
        avg_return = np.mean([t['net_profit_pct'] for t in self.results])
        total_return = sum(t['net_profit_pct'] for t in self.results)
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        print(f"Total Signals: {total_signals}")
        print(f"Win Rate: {win_rate*100:.1f}%")
        print(f"Average Win: {avg_win*100:.2f}%")
        print(f"Average Loss: {avg_loss*100:.2f}%")
        print(f"Average Return: {avg_return*100:.2f}%")
        print(f"Total Return: {total_return*100:.2f}%")
        print(f"Expectancy: {expectancy*100:.2f}%")

        # Signal count breakdown
        by_count = {}
        for trade in self.results:
            count = trade['signal_count']
            if count not in by_count:
                by_count[count] = []
            by_count[count].append(trade)

        print(f"\nSignal Count Breakdown:")
        for count in sorted(by_count.keys()):
            trades = by_count[count]
            wins = sum(1 for t in trades if t['net_profit_pct'] > 0)
            wr = wins / len(trades)
            print(f"  {count} signals: {len(trades)} occurrences, {wr*100:.1f}% win rate")


def generate_synthetic_data(start_date='2023-01-01', end_date='2024-12-31'):
    """
    Generate synthetic BTC price data for testing when APIs are unavailable
    """
    print("Generating synthetic data for testing purposes...")

    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)

    # Generate hourly timestamps
    timestamps = pd.date_range(start=start, end=end, freq='h')
    n = len(timestamps)

    # Generate realistic BTC price movement using geometric Brownian motion
    np.random.seed(42)  # For reproducibility

    # Starting price
    price = 20000.0
    prices = [price]

    # Simulate price with trend and volatility
    for i in range(1, n):
        # Add some cyclical behavior and overall uptrend
        trend = 0.0001 + 0.00005 * np.sin(i / 720)  # 30-day cycles
        volatility = 0.02

        # Random walk with drift
        change = np.random.normal(trend, volatility)
        price = price * (1 + change)
        prices.append(price)

    # Create OHLCV data
    df = pd.DataFrame({
        'timestamp': timestamps,
        'close': prices
    })

    # Generate OHLC from close prices
    df['open'] = df['close'].shift(1).fillna(df['close'])
    df['high'] = df[['open', 'close']].max(axis=1) * (1 + np.random.uniform(0, 0.01, n))
    df['low'] = df[['open', 'close']].min(axis=1) * (1 - np.random.uniform(0, 0.01, n))

    # Generate volume (correlated with price volatility)
    df['volume'] = np.random.lognormal(10, 1, n) * 1000

    # Generate synthetic funding rate (correlated with price momentum)
    df['returns_8h'] = df['close'].pct_change(8)
    df['funding_rate'] = df['returns_8h'].clip(-0.01, 0.01) * 0.1
    df['funding_rate'] = df['funding_rate'].fillna(0)

    # Add noise to funding rate
    df['funding_rate'] += np.random.normal(0, 0.0001, n)

    # Generate open interest (proxy using volume)
    df['open_interest'] = df['volume'].rolling(window=24).mean()

    # Generate search interest (trending with price)
    df['search_interest'] = 50 + (df['close'].pct_change(168).fillna(0) * 1000).clip(-40, 40)

    # Generate fear & greed (inverse correlation with recent volatility)
    df['returns'] = df['close'].pct_change()
    df['volatility_7d'] = df['returns'].rolling(window=168).std()
    df['fear_greed'] = (50 + df['returns_8h'].fillna(0) * 500).clip(10, 90)

    # Volume MA
    df['volume_ma_7d'] = df['volume'].rolling(window=168).mean()

    # Fill NaNs
    df = df.bfill().ffill()

    # Select final columns
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume',
             'funding_rate', 'open_interest', 'search_interest', 'fear_greed', 'volume_ma_7d']]

    print(f"  Generated {len(df)} hourly candles")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

    return df


def main():
    """
    Main execution
    """

    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     TIER 1 STRATEGY BACKTESTING SYSTEM                    ║
    ║     Testing Period: 2023-01-01 to 2024-12-31              ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    print("\nSTEP 1: DATA COLLECTION")
    print("-" * 60)

    df = None

    # Try Binance first (most reliable)
    print("\n[Attempt 1/4] Trying Binance...")
    try:
        collector = HistoricalDataCollector(use_coinbase=False)
        df = collector.collect_all_data(
            symbol='BTC/USDT',
            start_date='2023-01-01',
            end_date='2024-12-31'
        )
        print("\n✓ Data collection complete with Binance!")
    except Exception as e:
        print(f"✗ Binance failed: {str(e)[:100]}")

    # Try Coinbase if Binance failed
    if df is None:
        print("\n[Attempt 2/4] Trying Coinbase...")
        try:
            collector = HistoricalDataCollector(use_coinbase=True)
            df = collector.collect_all_data(
                symbol='BTC/USD',
                start_date='2023-01-01',
                end_date='2024-12-31'
            )
            print("\n✓ Data collection complete with Coinbase!")
        except Exception as e:
            print(f"✗ Coinbase failed: {str(e)[:100]}")

    # Try loading from CSV
    if df is None:
        print("\n[Attempt 3/4] Trying to load from existing CSV...")
        try:
            # Try various possible filenames
            for filename in ['BTC_USDT_historical_data_2023-01-01_to_2024-12-31.csv',
                           'BTC_USD_historical_data_2023-01-01_to_2024-12-31.csv',
                           'btc_data.csv']:
                try:
                    df = pd.read_csv(filename)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    print(f"✓ Loaded data from {filename}")
                    break
                except FileNotFoundError:
                    continue
        except Exception as e:
            print(f"✗ CSV loading failed: {e}")

    # Generate synthetic data as last resort
    if df is None:
        print("\n[Attempt 4/4] All data sources failed. Generating synthetic data for testing...")
        print("⚠️  WARNING: Using synthetic data - results are for testing purposes only!")
        df = generate_synthetic_data('2023-01-01', '2024-12-31')
        print("✓ Synthetic data generated successfully!")

    print("\n" + "="*60)
    print("STEP 2: FUNDING RATE BACKTESTS")
    print("="*60)

    funding_backtest = CompleteFundingRateBacktest(df)
    funding_backtest.run_backtest()

    print("\n" + "="*60)
    print("STEP 3: RETAIL EXHAUSTION BACKTEST")
    print("="*60)

    exhaustion_backtest = CompleteRetailExhaustionBacktest(df)
    exhaustion_backtest.run_backtest()

    print("\n" + "="*60)
    print("STEP 4: STRATEGY COMPARISON")
    print("="*60)

    strategies = [
        ('H1: Short Squeeze', funding_backtest.results['h1_short_squeeze']),
        ('H2: Overleveraged', funding_backtest.results['h2_overleveraged']),
        ('H3: Continuation', funding_backtest.results['h3_continuation']),
        ('Retail Exhaustion', exhaustion_backtest.results)
    ]

    print(f"\n{'Strategy':<25} {'Signals':<10} {'Win Rate':<12} {'Expectancy':<12} {'Total Return':<12}")
    print("-" * 80)

    viable_strategies = []

    for name, trades in strategies:
        if not trades:
            print(f"{name:<25} {0:<10} {'N/A':<12} {'N/A':<12} {'N/A':<12}")
            continue

        wins = sum(1 for t in trades if t['net_profit_pct'] > 0)
        win_rate = wins / len(trades)

        winning = [t for t in trades if t['net_profit_pct'] > 0]
        losing = [t for t in trades if t['net_profit_pct'] <= 0]
        avg_win = np.mean([t['net_profit_pct'] for t in winning]) if winning else 0
        avg_loss = np.mean([t['net_profit_pct'] for t in losing]) if losing else 0
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        total_return = sum(t['net_profit_pct'] for t in trades)

        print(f"{name:<25} {len(trades):<10} {win_rate*100:>10.1f}% {expectancy*100:>10.2f}% {total_return*100:>10.2f}%")

        if expectancy > 0 and len(trades) > 10:
            viable_strategies.append(name)

    print("\n" + "="*60)
    print("FINAL ASSESSMENT")
    print("="*60)

    if viable_strategies:
        print("\n✓ VIABLE STRATEGIES FOUND:")
        for s in viable_strategies:
            print(f"  • {s}")
        print("\nNEXT STEPS:")
        print("1. Analyze why these strategies worked")
        print("2. Refine parameters for optimization")
        print("3. Test on ETH/USDT for validation")
        print("4. Move to paper trading")
    else:
        print("\n✗ NO VIABLE STRATEGIES")
        print("  No strategies showed positive expectancy with sufficient signals.")
        print("\nNEXT STEPS:")
        print("1. Analyze why strategies failed")
        print("2. Adjust parameters and thresholds")
        print("3. Test Tier 2 strategies")
        print("4. Develop new hypotheses")

    print("\n" + "="*60)
    print("BACKTEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
