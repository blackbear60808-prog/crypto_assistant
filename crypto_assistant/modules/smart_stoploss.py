# modules/smart_stoploss.py
import pandas as pd
import numpy as np
from datetime import datetime
import logging

class SmartStopLoss:
    """智能止損系統 - 根據波動率自動調整止損"""
    
    def __init__(self, db, technical_indicators):
        self.db = db
        self.technical_indicators = technical_indicators
        self.logger = logging.getLogger('SmartStopLoss')
        
        # 止損設定
        self.settings = {
            'atr_period': 14,           # ATR計算週期
            'atr_multiplier': 2.0,      # ATR倍數
            'volatility_threshold': 0.02, # 波動率閾值
            'trailing_enabled': True,   # 啟用移動止損
            'break_even_enabled': True, # 啟用保本止損
            'max_risk_per_trade': 0.02  # 每筆交易最大風險
        }
        
        # 持倉止損資訊
        self.position_stops = {}
    
    def calculate_dynamic_stop_loss(self, symbol, position_type, entry_price, current_price):
        """計算動態止損價格"""
        try:
            # 獲取技術指標
            ohlcv_data = self.get_recent_ohlcv(symbol, 50)
            if ohlcv_data.empty:
                return self.calculate_fixed_stop_loss(entry_price, position_type)
            
            # 計算ATR
            atr = self.calculate_atr(ohlcv_data)
            if atr == 0:
                return self.calculate_fixed_stop_loss(entry_price, position_type)
            
            # 計算波動率調整因子
            volatility_factor = self.calculate_volatility_factor(ohlcv_data)
            
            # 基礎止損距離
            base_stop_distance = atr * self.settings['atr_multiplier'] * volatility_factor
            
            if position_type == 'LONG':
                stop_loss = entry_price - base_stop_distance
                # 確保止損不會太遠（最大風險控制）
                max_stop_loss = entry_price * (1 - self.settings['max_risk_per_trade'])
                stop_loss = max(stop_loss, max_stop_loss)
            else:  # SHORT
                stop_loss = entry_price + base_stop_distance
                # 確保止損不會太遠（最大風險控制）
                max_stop_loss = entry_price * (1 + self.settings['max_risk_per_trade'])
                stop_loss = min(stop_loss, max_stop_loss)
            
            self.logger.info(f"{symbol} {position_type} 智能止損計算: 進場={entry_price:.4f}, 止損={stop_loss:.4f}, ATR={atr:.4f}")
            
            return stop_loss
            
        except Exception as e:
            self.logger.error(f"計算動態止損錯誤 {symbol}: {e}")
            return self.calculate_fixed_stop_loss(entry_price, position_type)
    
    def calculate_trailing_stop_loss(self, symbol, position_type, entry_price, current_price, previous_stop=None):
        """計算移動止損"""
        try:
            if not self.settings['trailing_enabled']:
                return previous_stop
            
            # 獲取ATR用於移動止損距離
            ohlcv_data = self.get_recent_ohlcv(symbol, 20)
            if ohlcv_data.empty:
                return previous_stop
            
            atr = self.calculate_atr(ohlcv_data)
            trailing_distance = atr * self.settings['atr_multiplier'] * 0.7  # 移動止損使用較小距離
            
            if position_type == 'LONG':
                if previous_stop is None:
                    return entry_price - trailing_distance
                
                # 只在價格上漲時移動止損
                new_stop = current_price - trailing_distance
                if new_stop > previous_stop:
                    return new_stop
                else:
                    return previous_stop
                    
            else:  # SHORT
                if previous_stop is None:
                    return entry_price + trailing_distance
                
                # 只在價格下跌時移動止損
                new_stop = current_price + trailing_distance
                if new_stop < previous_stop:
                    return new_stop
                else:
                    return previous_stop
                    
        except Exception as e:
            self.logger.error(f"計算移動止損錯誤 {symbol}: {e}")
            return previous_stop
    
    def calculate_break_even_stop(self, symbol, position_type, entry_price, current_price, profit_threshold=0.01):
        """計算保本止損"""
        try:
            if not self.settings['break_even_enabled']:
                return None
            
            profit_pct = abs(current_price - entry_price) / entry_price
            
            if profit_pct >= profit_threshold:
                # 達到利潤閾值，移動到保本點
                if position_type == 'LONG':
                    return entry_price * 1.001  # 稍微高於進場價
                else:  # SHORT
                    return entry_price * 0.999  # 稍微低於進場價
            
            return None
            
        except Exception as e:
            self.logger.error(f"計算保本止損錯誤 {symbol}: {e}")
            return None
    
    def calculate_volatility_factor(self, ohlcv_data):
        """計算波動率調整因子"""
        try:
            returns = ohlcv_data['close'].pct_change().dropna()
            volatility = returns.std()
            
            # 波動率越高，止損距離越大
            if volatility < self.settings['volatility_threshold']:
                return 0.8  # 低波動環境，使用較緊止損
            elif volatility > self.settings['volatility_threshold'] * 2:
                return 1.5  # 高波動環境，使用較寬止損
            else:
                return 1.0  # 正常波動環境
            
        except Exception as e:
            self.logger.error(f"計算波動率因子錯誤: {e}")
            return 1.0
    
    def calculate_atr(self, ohlcv_data):
        """計算平均真實範圍(ATR)"""
        try:
            high = ohlcv_data['high']
            low = ohlcv_data['low']
            close = ohlcv_data['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=self.settings['atr_period']).mean().iloc[-1]
            
            return atr
            
        except Exception as e:
            self.logger.error(f"計算ATR錯誤: {e}")
            return 0
    
    def get_recent_ohlcv(self, symbol, limit=50):
        """獲取最近OHLCV數據"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT timestamp, open, high, low, close, volume 
                FROM market_data 
                WHERE symbol = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (symbol, limit))
            
            data = cursor.fetchall()
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            return df.sort_values('timestamp').reset_index(drop=True)
            
        except Exception as e:
            self.logger.error(f"獲取OHLCV數據錯誤 {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_fixed_stop_loss(self, entry_price, position_type, risk_percent=0.02):
        """計算固定百分比止損（備用方法）"""
        if position_type == 'LONG':
            return entry_price * (1 - risk_percent)
        else:  # SHORT
            return entry_price * (1 + risk_percent)
    
    def update_position_stop_loss(self, position_id, symbol, position_type, entry_price, current_price):
        """更新持倉止損價格"""
        try:
            # 計算動態止損
            dynamic_stop = self.calculate_dynamic_stop_loss(symbol, position_type, entry_price, current_price)
            
            # 計算移動止損
            previous_stop = self.position_stops.get(position_id, {}).get('current_stop')
            trailing_stop = self.calculate_trailing_stop_loss(symbol, position_type, entry_price, current_price, previous_stop)
            
            # 計算保本止損
            break_even_stop = self.calculate_break_even_stop(symbol, position_type, entry_price, current_price)
            
            # 選擇最優止損價格
            if position_type == 'LONG':
                final_stop = max([dynamic_stop, trailing_stop or dynamic_stop, break_even_stop or dynamic_stop])
            else:  # SHORT
                final_stop = min([dynamic_stop, trailing_stop or dynamic_stop, break_even_stop or dynamic_stop])
            
            # 更新止損資訊
            self.position_stops[position_id] = {
                'symbol': symbol,
                'position_type': position_type,
                'entry_price': entry_price,
                'current_stop': final_stop,
                'dynamic_stop': dynamic_stop,
                'trailing_stop': trailing_stop,
                'break_even_stop': break_even_stop,
                'last_updated': datetime.now().isoformat()
            }
            
            self.logger.info(f"位置 {position_id} 止損更新: {final_stop:.4f}")
            
            return final_stop
            
        except Exception as e:
            self.logger.error(f"更新位置止損錯誤 {position_id}: {e}")
            return self.calculate_fixed_stop_loss(entry_price, position_type)
    
    def check_stop_loss_hit(self, position_id, current_price):
        """檢查是否觸發止損"""
        try:
            if position_id not in self.position_stops:
                return False
            
            stop_info = self.position_stops[position_id]
            position_type = stop_info['position_type']
            stop_price = stop_info['current_stop']
            
            if position_type == 'LONG' and current_price <= stop_price:
                self.logger.info(f"位置 {position_id} 觸發多單止損: 價格={current_price:.4f}, 止損={stop_price:.4f}")
                return True
            elif position_type == 'SHORT' and current_price >= stop_price:
                self.logger.info(f"位置 {position_id} 觸發空單止損: 價格={current_price:.4f}, 止損={stop_price:.4f}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"檢查止損觸發錯誤 {position_id}: {e}")
            return False
    
    def get_stop_loss_info(self, position_id):
        """獲取止損資訊"""
        return self.position_stops.get(position_id)
    
    def remove_position_stop(self, position_id):
        """移除持倉止損資訊"""
        if position_id in self.position_stops:
            del self.position_stops[position_id]
    
    def update_settings(self, new_settings):
        """更新止損設定"""
        self.settings.update(new_settings)
        self.logger.info(f"止損設定已更新: {new_settings}")