# modules/expectancy_calculator.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

class ExpectancyCalculator:
    def __init__(self, db):
        self.db = db
    
    def calculate_trade_expectancy(self, symbol, period_days=30):
        """計算交易期望值"""
        try:
            # 獲取交易記錄
            trades = self.get_trade_history(symbol, period_days)
            if not trades:
                return None
            
            # 計算基本統計
            winning_trades = [t for t in trades if t['profit_loss'] > 0]
            losing_trades = [t for t in trades if t['profit_loss'] <= 0]
            
            total_trades = len(trades)
            winning_trades_count = len(winning_trades)
            losing_trades_count = len(losing_trades)
            
            if total_trades == 0:
                return None
            
            win_rate = winning_trades_count / total_trades
            
            # 計算平均盈利和平均虧損
            avg_win = np.mean([t['profit_loss'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['profit_loss'] for t in losing_trades]) if losing_trades else 0
            
            # 計算期望值
            expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
            
            # 計算風險回報比
            risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            
            # 計算Kelly Criterion
            kelly_criterion = self.calculate_kelly_criterion(win_rate, avg_win, avg_loss)
            
            result = {
                'symbol': symbol,
                'period_days': period_days,
                'total_trades': total_trades,
                'winning_trades': winning_trades_count,
                'losing_trades': losing_trades_count,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'expectancy': expectancy,
                'risk_reward_ratio': risk_reward_ratio,
                'kelly_criterion': kelly_criterion,
                'total_profit': sum(t['profit_loss'] for t in trades),
                'largest_win': max(t['profit_loss'] for t in trades) if trades else 0,
                'largest_loss': min(t['profit_loss'] for t in trades) if trades else 0,
                'calculated_at': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            print(f"❌ 計算期望值錯誤: {e}")
            return None
    
    def get_trade_history(self, symbol, period_days):
        """獲取交易歷史"""
        try:
            cursor = self.db.conn.cursor()
            start_date = (datetime.now() - timedelta(days=period_days)).isoformat()
            
            cursor.execute('''
                SELECT symbol, side, price, quantity, timestamp, strategy, profit_loss
                FROM trade_records 
                WHERE symbol = ? AND timestamp >= ?
                ORDER BY timestamp
            ''', (symbol, start_date))
            
            trades = []
            for row in cursor.fetchall():
                trades.append({
                    'symbol': row[0],
                    'side': row[1],
                    'price': row[2],
                    'quantity': row[3],
                    'timestamp': row[4],
                    'strategy': row[5],
                    'profit_loss': row[6] or 0
                })
            
            return trades
            
        except Exception as e:
            print(f"❌ 獲取交易歷史錯誤: {e}")
            return []
    
    def calculate_kelly_criterion(self, win_rate, avg_win, avg_loss):
        """計算凱利公式"""
        try:
            if avg_loss == 0:
                return 0
            
            # 凱利公式: f = (bp - q) / b
            # 其中: b = 平均盈利 / 平均虧損, p = 勝率, q = 敗率
            b = abs(avg_win / avg_loss)
            p = win_rate
            q = 1 - p
            
            if b == 0:
                return 0
            
            kelly = (b * p - q) / b
            # 限制在0到1之間
            return max(0, min(kelly, 1))
            
        except Exception as e:
            print(f"❌ 計算凱利公式錯誤: {e}")
            return 0
    
    def calculate_position_size(self, account_balance, risk_per_trade, stop_loss_pct):
        """計算倉位大小"""
        try:
            risk_amount = account_balance * risk_per_trade
            position_size = risk_amount / stop_loss_pct
            return position_size
            
        except Exception as e:
            print(f"❌ 計算倉位大小錯誤: {e}")
            return 0
    
    def analyze_portfolio_expectancy(self, symbols, period_days=30):
        """分析投資組合期望值"""
        try:
            portfolio_results = {}
            total_expectancy = 0
            valid_symbols = 0
            
            for symbol in symbols:
                result = self.calculate_trade_expectancy(symbol, period_days)
                if result:
                    portfolio_results[symbol] = result
                    total_expectancy += result['expectancy']
                    valid_symbols += 1
            
            avg_expectancy = total_expectancy / valid_symbols if valid_symbols > 0 else 0
            
            return {
                'symbols_count': valid_symbols,
                'avg_expectancy': avg_expectancy,
                'total_expectancy': total_expectancy,
                'symbol_details': portfolio_results,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ 分析投資組合期望值錯誤: {e}")
            return None
    
    def generate_trading_report(self, symbol, period_days=30):
        """生成交易報告"""
        expectancy_data = self.calculate_trade_expectancy(symbol, period_days)
        if not expectancy_data:
            return None
        
        report = f"""
📊 交易期望值分析報告 - {symbol}

📈 基本統計:
• 總交易次數: {expectancy_data['total_trades']}
• 盈利交易: {expectancy_data['winning_trades']} 次
• 虧損交易: {expectancy_data['losing_trades']} 次
• 勝率: {expectancy_data['win_rate']:.2%}

💰 盈利分析:
• 平均盈利: {expectancy_data['avg_win']:.4f} USDT
• 平均虧損: {expectancy_data['avg_loss']:.4f} USDT
• 最大盈利: {expectancy_data['largest_win']:.4f} USDT
• 最大虧損: {expectancy_data['largest_loss']:.4f} USDT

🎯 期望值分析:
• 交易期望值: {expectancy_data['expectancy']:.4f} USDT/交易
• 風險回報比: {expectancy_data['risk_reward_ratio']:.2f}:1
• 凱利公式: {expectancy_data['kelly_criterion']:.2%}

💡 建議:
{self.generate_advice(expectancy_data)}

分析時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return report
    
    def generate_advice(self, expectancy_data):
        """生成交易建議"""
        advice = []
        
        if expectancy_data['expectancy'] > 0:
            advice.append("✅ 策略具有正期望值，可以繼續使用")
        else:
            advice.append("⚠️ 策略期望值為負，需要調整")
        
        if expectancy_data['win_rate'] > 0.6:
            advice.append("✅ 勝率良好，保持當前風險管理")
        elif expectancy_data['win_rate'] < 0.4:
            advice.append("⚠️ 勝率較低，考慮改進進場時機")
        
        if expectancy_data['risk_reward_ratio'] > 2:
            advice.append("✅ 風險回報比優秀")
        elif expectancy_data['risk_reward_ratio'] < 1:
            advice.append("⚠️ 風險回報比需要改善")
        
        if expectancy_data['kelly_criterion'] > 0.1:
            advice.append(f"💡 建議倉位: {expectancy_data['kelly_criterion']:.1%} 總資金")
        else:
            advice.append("💡 凱利公式建議暫停交易或極小倉位")
        
        return "\n".join(advice)