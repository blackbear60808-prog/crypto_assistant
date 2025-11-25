# backtest/backtest_engine.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

class BacktestEngine:
    def __init__(self, db, smc_strategy):
        self.db = db
        self.smc_strategy = smc_strategy
        self.results = {}
        
    def run_backtest(self, symbol, start_date, end_date, initial_balance=1000, commission=0.001):
        """運行回測"""
        try:
            # 獲取歷史數據
            historical_data = self.get_historical_data(symbol, start_date, end_date)
            if not historical_data:
                return None
            
            df = pd.DataFrame(historical_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 初始化回測變量
            balance = initial_balance
            position = 0
            trades = []
            equity_curve = []
            
            # 運行策略
            for i in range(1, len(df)):
                current_data = df.iloc[:i]
                current_price = df['close'].iloc[i]
                
                # 獲取SMC信號 (簡化版本)
                signal = self.get_trading_signal(current_data)
                
                # 執行交易邏輯
                if signal == 'buy' and position == 0:
                    # 開多倉
                    position_size = balance * 0.1  # 10%倉位
                    units = position_size / current_price
                    position = units
                    balance -= position_size
                    
                    trades.append({
                        'timestamp': df['timestamp'].iloc[i],
                        'action': 'BUY',
                        'price': current_price,
                        'units': units,
                        'balance': balance
                    })
                    
                elif signal == 'sell' and position > 0:
                    # 平多倉
                    position_value = position * current_price * (1 - commission)
                    balance += position_value
                    
                    trades.append({
                        'timestamp': df['timestamp'].iloc[i],
                        'action': 'SELL',
                        'price': current_price,
                        'units': position,
                        'balance': balance
                    })
                    
                    position = 0
                
                # 記錄權益曲線
                current_equity = balance + (position * current_price if position > 0 else 0)
                equity_curve.append({
                    'timestamp': df['timestamp'].iloc[i],
                    'equity': current_equity,
                    'price': current_price
                })
            
            # 計算績效指標
            performance = self.calculate_performance(equity_curve, trades, initial_balance)
            
            # 儲存回測結果
            result_id = self.save_backtest_result(symbol, start_date, end_date, initial_balance, performance)
            
            return {
                'result_id': result_id,
                'performance': performance,
                'trades': trades,
                'equity_curve': equity_curve
            }
            
        except Exception as e:
            print(f"回測運行錯誤 {symbol}: {e}")
            return None
    
    def get_historical_data(self, symbol, start_date, end_date):
        """獲取歷史數據"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT timestamp, open, high, low, close, volume 
                FROM market_data 
                WHERE symbol = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            ''', (symbol, start_date, end_date))
            
            return cursor.fetchall()
        except Exception as e:
            print(f"獲取歷史數據錯誤: {e}")
            return None
    
    def get_trading_signal(self, data):
        """獲取交易信號 (簡化版本)"""
        try:
            # 簡單的基於移動平均線的信號
            if len(data) < 30:
                return 'hold'
            
            short_ma = data['close'].rolling(10).mean().iloc[-1]
            long_ma = data['close'].rolling(30).mean().iloc[-1]
            
            if short_ma > long_ma:
                return 'buy'
            elif short_ma < long_ma:
                return 'sell'
            else:
                return 'hold'
                
        except Exception as e:
            print(f"獲取交易信號錯誤: {e}")
            return 'hold'
    
    def calculate_performance(self, equity_curve, trades, initial_balance):
        """計算績效指標"""
        try:
            if not equity_curve:
                return {}
            
            final_equity = equity_curve[-1]['equity']
            total_return = (final_equity - initial_balance) / initial_balance
            
            # 計算最大回撤
            equity_values = [point['equity'] for point in equity_curve]
            peak = equity_values[0]
            max_drawdown = 0
            
            for value in equity_values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            # 計算夏普比率 (簡化)
            returns = []
            for i in range(1, len(equity_curve)):
                ret = (equity_curve[i]['equity'] - equity_curve[i-1]['equity']) / equity_curve[i-1]['equity']
                returns.append(ret)
            
            if returns:
                sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(365) if np.std(returns) > 0 else 0
            else:
                sharpe_ratio = 0
            
            win_trades = len([t for t in trades if t['action'] == 'SELL' and 
                             t['price'] > trades[trades.index(t)-1]['price']]) if len(trades) > 1 else 0
            total_trade_trades = len(trades) // 2  # 買賣成對
            
            win_rate = win_trades / total_trade_trades if total_trade_trades > 0 else 0
            
            return {
                'initial_balance': initial_balance,
                'final_balance': final_equity,
                'total_return': total_return,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'win_rate': win_rate,
                'total_trades': total_trade_trades,
                'win_trades': win_trades
            }
            
        except Exception as e:
            print(f"計算績效錯誤: {e}")
            return {}
    
    def save_backtest_result(self, symbol, start_date, end_date, initial_balance, performance):
        """儲存回測結果"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                INSERT INTO backtest_results 
                (strategy_name, symbol, period_start, period_end, initial_balance, 
                 final_balance, total_return, sharpe_ratio, max_drawdown, parameters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                'SMC_Strategy',
                symbol,
                start_date,
                end_date,
                initial_balance,
                performance.get('final_balance', initial_balance),
                performance.get('total_return', 0),
                performance.get('sharpe_ratio', 0),
                performance.get('max_drawdown', 0),
                json.dumps({'commission': 0.001})
            ))
            
            self.db.conn.commit()
            return cursor.lastrowid
            
        except Exception as e:
            print(f"儲存回測結果錯誤: {e}")
            return None
    
    def get_backtest_history(self, limit=10):
        """獲取回測歷史"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT * FROM backtest_results 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            return cursor.fetchall()
        except Exception as e:
            print(f"獲取回測歷史錯誤: {e}")
            return []