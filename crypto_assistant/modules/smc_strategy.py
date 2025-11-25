# modules/smc_strategy.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional, Tuple
import talib

class SMCStrategy:
    def __init__(self, db, okx_api):
        self.db = db
        self.okx_api = okx_api
        self.smc_levels = {}
        self.signals = {}
        self.logger = logging.getLogger('smc_strategy')
        
        # SMC 參數設定
        self.config = {
            'support_resistance_window': 20,
            'level_merge_threshold': 0.02,  # 2% 以內的等級合併
            'min_touches_for_strength': 3,
            'volume_weight': 0.3,
            'time_weight': 0.2,
            'price_weight': 0.5
        }
    
    def calculate_smc_levels(self, symbol: str, ohlcv_data: List) -> Optional[Dict]:
        """計算 SMC 等級 - 主要入口函數"""
        try:
            if not ohlcv_data or len(ohlcv_data) < 100:
                self.logger.warning(f"數據不足，無法計算 {symbol} 的 SMC 等級")
                return None
            
            # 轉換為 DataFrame
            df = self._create_dataframe(ohlcv_data)
            
            # 計算技術指標
            df = self._calculate_technical_indicators(df)
            
            # 計算支撐阻力位
            resistance_levels = self.calculate_resistance_levels(df)
            support_levels = self.calculate_support_levels(df)
            
            # 計算市場結構
            market_structure = self.analyze_market_structure(df)
            
            # 計算交易信號
            trading_signals = self.generate_trading_signals(df, support_levels, resistance_levels)
            
            smc_data = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'current_price': df['close'].iloc[-1],
                'resistance_levels': resistance_levels,
                'support_levels': support_levels,
                'market_structure': market_structure,
                'trading_signals': trading_signals,
                'bias': self.calculate_bias(df),
                'confidence': self.calculate_confidence(df, support_levels, resistance_levels)
            }
            
            # 儲存到資料庫
            self.save_smc_data(symbol, smc_data)
            
            self.logger.info(f"成功計算 {symbol} 的 SMC 等級")
            return smc_data
            
        except Exception as e:
            self.logger.error(f"計算 SMC 等級錯誤 {symbol}: {str(e)}", exc_info=True)
            return None
    
    def _create_dataframe(self, ohlcv_data: List) -> pd.DataFrame:
        """創建 DataFrame 並處理數據"""
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算技術指標"""
        try:
            # RSI
            df['rsi'] = talib.RSI(df['close'], timeperiod=14)
            
            # 移動平均線
            df['ma_20'] = talib.SMA(df['close'], timeperiod=20)
            df['ma_50'] = talib.SMA(df['close'], timeperiod=50)
            df['ma_200'] = talib.SMA(df['close'], timeperiod=200)
            
            # 布林帶
            df['bb_upper'], df['bb_middle'], df['bb_lower'] = talib.BBANDS(
                df['close'], timeperiod=20, nbdevup=2, nbdevdn=2
            )
            
            # MACD
            df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(df['close'])
            
            # ATR (平均真實範圍)
            df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
            
            # 成交量加權平均價
            df['vwap'] = self._calculate_vwap(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算技術指標錯誤: {str(e)}")
            return df
    
    def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """計算 VWAP"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return vwap
    
    def calculate_resistance_levels(self, df: pd.DataFrame, window: int = 20) -> List[Dict]:
        """計算阻力位 - 改進版本"""
        try:
            resistance_levels = []
            
            # 方法1: 局部高點
            df['high_rollmax'] = df['high'].rolling(window=window).max()
            local_highs = []
            
            for i in range(window, len(df)-window):
                if df['high'].iloc[i] == df['high_rollmax'].iloc[i]:
                    local_highs.append({
                        'price': df['high'].iloc[i],
                        'index': i,
                        'volume': df['volume'].iloc[i]
                    })
            
            # 方法2: 前高點突破失敗
            failed_breakouts = self._find_failed_breakouts(df, 'high')
            
            # 合併所有候選點位
            all_candidates = local_highs + failed_breakouts
            
            # 合併相近的等級
            resistance_levels = self._merge_similar_levels(
                all_candidates, 'resistance', df
            )
            
            # 計算強度並排序
            for level in resistance_levels:
                level['strength'] = self.calculate_level_strength(df, level, 'resistance')
            
            return sorted(resistance_levels, key=lambda x: x['strength'], reverse=True)[:5]
            
        except Exception as e:
            self.logger.error(f"計算阻力位錯誤: {str(e)}")
            return []
    
    def calculate_support_levels(self, df: pd.DataFrame, window: int = 20) -> List[Dict]:
        """計算支撐位 - 改進版本"""
        try:
            support_levels = []
            
            # 方法1: 局部低點
            df['low_rollmin'] = df['low'].rolling(window=window).min()
            local_lows = []
            
            for i in range(window, len(df)-window):
                if df['low'].iloc[i] == df['low_rollmin'].iloc[i]:
                    local_lows.append({
                        'price': df['low'].iloc[i],
                        'index': i,
                        'volume': df['volume'].iloc[i]
                    })
            
            # 方法2: 前低點跌破失敗
            failed_breakdowns = self._find_failed_breakouts(df, 'low')
            
            # 合併所有候選點位
            all_candidates = local_lows + failed_breakdowns
            
            # 合併相近的等級
            support_levels = self._merge_similar_levels(
                all_candidates, 'support', df
            )
            
            # 計算強度並排序
            for level in support_levels:
                level['strength'] = self.calculate_level_strength(df, level, 'support')
            
            return sorted(support_levels, key=lambda x: x['strength'], reverse=True)[:5]
            
        except Exception as e:
            self.logger.error(f"計算支撐位錯誤: {str(e)}")
            return []
    
    def _find_failed_breakouts(self, df: pd.DataFrame, level_type: str) -> List[Dict]:
        """尋找突破失敗的點位"""
        failed_points = []
        window = 10
        
        for i in range(window, len(df)-window):
            if level_type == 'high':
                # 檢查是否嘗試突破但失敗
                if (df['high'].iloc[i] > df['high'].iloc[i-window:i].max() and
                    df['close'].iloc[i] < df['high'].iloc[i] * 0.99):  # 收盤價低於高點
                    failed_points.append({
                        'price': df['high'].iloc[i],
                        'index': i,
                        'volume': df['volume'].iloc[i],
                        'type': 'failed_breakout'
                    })
            else:  # low
                # 檢查是否嘗試跌破但失敗
                if (df['low'].iloc[i] < df['low'].iloc[i-window:i].min() and
                    df['close'].iloc[i] > df['low'].iloc[i] * 1.01):  # 收盤價高於低點
                    failed_points.append({
                        'price': df['low'].iloc[i],
                        'index': i,
                        'volume': df['volume'].iloc[i],
                        'type': 'failed_breakdown'
                    })
        
        return failed_points
    
    def _merge_similar_levels(self, candidates: List[Dict], level_type: str, df: pd.DataFrame) -> List[Dict]:
        """合併相近的等級"""
        if not candidates:
            return []
        
        # 按價格排序
        candidates.sort(key=lambda x: x['price'])
        merged_levels = []
        
        current_group = [candidates[0]]
        
        for i in range(1, len(candidates)):
            current_price = candidates[i]['price']
            group_avg_price = np.mean([c['price'] for c in current_group])
            
            # 檢查是否在同一組合併範圍內
            price_diff_pct = abs(current_price - group_avg_price) / group_avg_price
            
            if price_diff_pct <= self.config['level_merge_threshold']:
                current_group.append(candidates[i])
            else:
                # 合併當前組並創建新組
                merged_level = self._create_merged_level(current_group, level_type, df)
                merged_levels.append(merged_level)
                current_group = [candidates[i]]
        
        # 處理最後一組
        if current_group:
            merged_level = self._create_merged_level(current_group, level_type, df)
            merged_levels.append(merged_level)
        
        return merged_levels
    
    def _create_merged_level(self, group: List[Dict], level_type: str, df: pd.DataFrame) -> Dict:
        """創建合併後的等級"""
        avg_price = np.mean([c['price'] for c in group])
        total_volume = sum([c['volume'] for c in group])
        latest_timestamp = df.index[max([c['index'] for c in group])]
        
        return {
            'price': avg_price,
            'touches': len(group),
            'total_volume': total_volume,
            'latest_touch': latest_timestamp,
            'type': level_type
        }
    
    def analyze_market_structure(self, df: pd.DataFrame) -> Dict:
        """分析市場結構 - 改進版本"""
        try:
            current_price = df['close'].iloc[-1]
            
            # 多時間框架分析
            structure = {
                'current_price': current_price,
                'trend': self.determine_trend(df),
                'momentum': self.analyze_momentum(df),
                'volatility': self.calculate_volatility(df),
                'volume_profile': self.analyze_volume_profile(df),
                'key_levels': self.identify_key_levels(df),
                'market_regime': self.determine_market_regime(df)
            }
            
            return structure
            
        except Exception as e:
            self.logger.error(f"分析市場結構錯誤: {str(e)}")
            return {}
    
    def determine_trend(self, df: pd.DataFrame) -> Dict:
        """判斷趨勢方向 - 多時間框架"""
        try:
            # 短期趨勢 (20期)
            ma_20 = df['close'].rolling(20).mean()
            ma_20_trend = "上漲" if df['close'].iloc[-1] > ma_20.iloc[-1] else "下跌"
            
            # 中期趨勢 (50期)
            ma_50 = df['close'].rolling(50).mean()
            ma_50_trend = "上漲" if df['close'].iloc[-1] > ma_50.iloc[-1] else "下跌"
            
            # 長期趨勢 (200期)
            ma_200 = df['close'].rolling(200).mean()
            ma_200_trend = "上漲" if df['close'].iloc[-1] > ma_200.iloc[-1] else "下跌"
            
            # 綜合判斷
            trend_score = sum([
                1 if ma_20_trend == "上漲" else -1,
                1 if ma_50_trend == "上漲" else -1,
                1 if ma_200_trend == "上漲" else -1
            ])
            
            if trend_score >= 2:
                overall_trend = "強勢上漲"
            elif trend_score >= 0:
                overall_trend = "溫和上漲"
            elif trend_score >= -1:
                overall_trend = "溫和下跌"
            else:
                overall_trend = "強勢下跌"
            
            return {
                'short_term': ma_20_trend,
                'medium_term': ma_50_trend,
                'long_term': ma_200_trend,
                'overall': overall_trend,
                'score': trend_score
            }
            
        except Exception as e:
            self.logger.error(f"判斷趨勢錯誤: {str(e)}")
            return {'overall': '未知', 'score': 0}
    
    def analyze_momentum(self, df: pd.DataFrame) -> Dict:
        """分析動能指標"""
        try:
            rsi = df['rsi'].iloc[-1]
            macd_hist = df['macd_hist'].iloc[-1]
            
            # RSI 動能
            if rsi > 70:
                rsi_momentum = "超買"
            elif rsi > 55:
                rsi_momentum = "強勢"
            elif rsi > 45:
                rsi_momentum = "中性"
            elif rsi > 30:
                rsi_momentum = "弱勢"
            else:
                rsi_momentum = "超賣"
            
            # MACD 動能
            if macd_hist > 0:
                macd_momentum = "看漲" if macd_hist > df['macd_hist'].iloc[-2] else "看漲減弱"
            else:
                macd_momentum = "看跌" if macd_hist < df['macd_hist'].iloc[-2] else "看跌減弱"
            
            return {
                'rsi': rsi,
                'rsi_momentum': rsi_momentum,
                'macd_histogram': macd_hist,
                'macd_momentum': macd_momentum
            }
            
        except Exception as e:
            self.logger.error(f"分析動能錯誤: {str(e)}")
            return {}
    
    def analyze_volume_profile(self, df: pd.DataFrame) -> Dict:
        """分析成交量分佈"""
        try:
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_ratio = current_volume / avg_volume
            
            if volume_ratio > 2.0:
                volume_status = "異常大量"
            elif volume_ratio > 1.5:
                volume_status = "放量"
            elif volume_ratio > 0.8:
                volume_status = "正常"
            else:
                volume_status = "縮量"
            
            return {
                'current_volume': current_volume,
                'volume_ratio': volume_ratio,
                'status': volume_status
            }
            
        except Exception as e:
            self.logger.error(f"分析成交量分佈錯誤: {str(e)}")
            return {}
    
    def identify_key_levels(self, df: pd.DataFrame) -> Dict:
        """識別關鍵價位"""
        try:
            pivot = (df['high'].iloc[-1] + df['low'].iloc[-1] + df['close'].iloc[-1]) / 3
            r1 = 2 * pivot - df['low'].iloc[-1]
            s1 = 2 * pivot - df['high'].iloc[-1]
            
            return {
                'pivot_point': pivot,
                'resistance_1': r1,
                'support_1': s1,
                'weekly_high': df['high'].rolling(7).max().iloc[-1],
                'weekly_low': df['low'].rolling(7).min().iloc[-1]
            }
            
        except Exception as e:
            self.logger.error(f"識別關鍵價位錯誤: {str(e)}")
            return {}
    
    def determine_market_regime(self, df: pd.DataFrame) -> str:
        """判斷市場狀態"""
        try:
            volatility = self.calculate_volatility(df)
            atr_percentage = df['atr'].iloc[-1] / df['close'].iloc[-1]
            
            if atr_percentage > 0.05:  # 5% ATR
                return "高波動"
            elif atr_percentage > 0.02:
                return "正常波動"
            else:
                return "低波動"
                
        except Exception as e:
            self.logger.error(f"判斷市場狀態錯誤: {str(e)}")
            return "未知"
    
    def calculate_volatility(self, df: pd.DataFrame) -> float:
        """計算波動率 - 改進版本"""
        try:
            # 使用多種方法計算波動率
            returns = df['close'].pct_change().dropna()
            historical_vol = returns.std() * np.sqrt(365)
            
            # ATR 基礎的波動率
            atr_vol = df['atr'].iloc[-1] / df['close'].iloc[-1] * np.sqrt(365)
            
            # 綜合波動率
            combined_vol = (historical_vol + atr_vol) / 2
            
            return combined_vol
            
        except Exception as e:
            self.logger.error(f"計算波動率錯誤: {str(e)}")
            return 0.0
    
    def calculate_bias(self, df: pd.DataFrame) -> str:
        """計算市場偏見 - 改進版本"""
        try:
            signals = []
            
            # RSI 信號
            rsi = df['rsi'].iloc[-1]
            if rsi > 70:
                signals.append("bearish")
            elif rsi < 30:
                signals.append("bullish")
            else:
                signals.append("neutral")
            
            # 移動平均線信號
            if df['ma_20'].iloc[-1] > df['ma_50'].iloc[-1] > df['ma_200'].iloc[-1]:
                signals.append("bullish")
            elif df['ma_20'].iloc[-1] < df['ma_50'].iloc[-1] < df['ma_200'].iloc[-1]:
                signals.append("bearish")
            else:
                signals.append("neutral")
            
            # MACD 信號
            if df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]:
                signals.append("bullish")
            else:
                signals.append("bearish")
            
            # 計算綜合偏見
            bull_count = signals.count("bullish")
            bear_count = signals.count("bearish")
            
            if bull_count >= 2:
                return "偏多"
            elif bear_count >= 2:
                return "偏空"
            else:
                return "中性"
                
        except Exception as e:
            self.logger.error(f"計算偏見錯誤: {str(e)}")
            return "中性"
    
    def calculate_level_strength(self, df: pd.DataFrame, level: Dict, level_type: str) -> float:
        """計算等級強度 - 改進版本"""
        try:
            price = level['price']
            touches = level.get('touches', 1)
            total_volume = level.get('total_volume', 0)
            
            # 價格觸碰強度
            price_strength = min(touches / 10.0, 1.0)  # 最多10次觸碰
            
            # 成交量強度
            avg_volume = df['volume'].mean()
            volume_strength = min(np.log(total_volume / avg_volume + 1) * 0.5, 1.0)
            
            # 時間強度 (最近觸碰的權重更高)
            latest_index = level.get('latest_index', len(df)-1)
            recency = 1.0 - (len(df) - 1 - latest_index) / len(df)
            time_strength = max(recency, 0.1)
            
            # 綜合強度
            strength = (
                price_strength * self.config['price_weight'] +
                volume_strength * self.config['volume_weight'] +
                time_strength * self.config['time_weight']
            )
            
            return min(strength, 1.0)
            
        except Exception as e:
            self.logger.error(f"計算等級強度錯誤: {str(e)}")
            return 0.5
    
    def generate_trading_signals(self, df: pd.DataFrame, support_levels: List, resistance_levels: List) -> Dict:
        """生成交易信號"""
        try:
            current_price = df['close'].iloc[-1]
            signals = {}
            
            # 支撐阻力信號
            nearest_support = self._find_nearest_level(current_price, support_levels)
            nearest_resistance = self._find_nearest_level(current_price, resistance_levels)
            
            # 買入信號條件
            buy_signals = []
            if nearest_support and (current_price - nearest_support['price']) / current_price < 0.02:
                buy_signals.append("接近強力支撐")
            if df['rsi'].iloc[-1] < 35:
                buy_signals.append("RSI超賣")
            if df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]:
                buy_signals.append("MACD金叉")
            
            # 賣出信號條件
            sell_signals = []
            if nearest_resistance and (nearest_resistance['price'] - current_price) / current_price < 0.02:
                sell_signals.append("接近強力阻力")
            if df['rsi'].iloc[-1] > 65:
                sell_signals.append("RSI超買")
            if df['macd'].iloc[-1] < df['macd_signal'].iloc[-1]:
                sell_signals.append("MACD死叉")
            
            signals = {
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'action': '持有' if not buy_signals and not sell_signals else 
                         '考慮買入' if len(buy_signals) > len(sell_signals) else
                         '考慮賣出' if len(sell_signals) > len(buy_signals) else '持有',
                'confidence': len(buy_signals + sell_signals) / 6.0  # 信號強度
            }
            
            return signals
            
        except Exception as e:
            self.logger.error(f"生成交易信號錯誤: {str(e)}")
            return {'buy_signals': [], 'sell_signals': [], 'action': '持有', 'confidence': 0}
    
    def _find_nearest_level(self, current_price: float, levels: List[Dict]) -> Optional[Dict]:
        """尋找最近的等級"""
        if not levels:
            return None
        
        nearest = min(levels, key=lambda x: abs(x['price'] - current_price))
        return nearest if abs(nearest['price'] - current_price) / current_price < 0.05 else None
    
    def calculate_confidence(self, df: pd.DataFrame, support_levels: List, resistance_levels: List) -> float:
        """計算信號置信度"""
        try:
            factors = []
            
            # 數據質量
            data_quality = min(len(df) / 200.0, 1.0)
            factors.append(data_quality)
            
            # 等級清晰度
            level_clarity = min((len(support_levels) + len(resistance_levels)) / 8.0, 1.0)
            factors.append(level_clarity)
            
            # 趨勢一致性
            trend = self.determine_trend(df)
            trend_consistency = abs(trend['score']) / 3.0
            factors.append(trend_consistency)
            
            # 平均置信度
            confidence = np.mean(factors)
            return min(confidence, 1.0)
            
        except Exception as e:
            self.logger.error(f"計算置信度錯誤: {str(e)}")
            return 0.5
    
    def save_smc_data(self, symbol: str, smc_data: Dict):
        """儲存 SMC 數據到資料庫"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO smc_data 
                (symbol, timestamp, level, value, signal, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                smc_data['timestamp'],
                'market_structure',
                json.dumps(smc_data, ensure_ascii=False),
                smc_data['bias'],
                smc_data.get('confidence', 0.8),
                datetime.now().isoformat()
            ))
            self.db.conn.commit()
            
        except Exception as e:
            self.logger.error(f"儲存 SMC 數據錯誤: {str(e)}")
    
    def get_smc_signals(self, symbol: str) -> Optional[Dict]:
        """獲取 SMC 信號"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT value FROM smc_data 
                WHERE symbol = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (symbol,))
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None
            
        except Exception as e:
            self.logger.error(f"獲取 SMC 信號錯誤: {str(e)}")
            return None
    
    def analyze_all_pairs(self, pairs: List[str]) -> Dict:
        """分析所有幣種"""
        results = {}
        total_pairs = len(pairs)
        
        self.logger.info(f"開始分析 {total_pairs} 個交易對")
        
        for i, pair in enumerate(pairs, 1):
            try:
                self.logger.info(f"分析進度: {i}/{total_pairs} - {pair}")
                
                # 獲取 K 線數據 (4小時線，更多數據點)
                ohlcv = self.okx_api.get_ohlcv(pair, '4H', 200)
                if ohlcv and len(ohlcv) >= 100:
                    smc_data = self.calculate_smc_levels(pair, ohlcv)
                    if smc_data:
                        results[pair] = smc_data
                        self.logger.info(f"✓ 成功分析 {pair}")
                    else:
                        self.logger.warning(f"✗ 分析 {pair} 失敗")
                else:
                    self.logger.warning(f"✗ {pair} 數據不足")
                    
            except Exception as e:
                self.logger.error(f"分析 {pair} 錯誤: {str(e)}")
                continue
        
        self.logger.info(f"分析完成: 成功 {len(results)}/{total_pairs} 個交易對")
        return results
    
    def get_trading_recommendations(self, symbol: str) -> Dict:
        """獲取交易建議"""
        smc_data = self.get_smc_signals(symbol)
        if not smc_data:
            return {'error': '沒有可用的 SMC 數據'}
        
        signals = smc_data.get('trading_signals', {})
        structure = smc_data.get('market_structure', {})
        
        recommendation = {
            'symbol': symbol,
            'timestamp': smc_data['timestamp'],
            'current_price': smc_data['current_price'],
            'bias': smc_data['bias'],
            'action': signals.get('action', '持有'),
            'confidence': signals.get('confidence', 0),
            'reasoning': signals.get('buy_signals', []) + signals.get('sell_signals', []),
            'key_levels': {
                'nearest_support': None,
                'nearest_resistance': None
            },
            'risk_level': self._calculate_risk_level(structure)
        }
        
        # 尋找關鍵價位
        current_price = smc_data['current_price']
        support_levels = smc_data.get('support_levels', [])
        resistance_levels = smc_data.get('resistance_levels', [])
        
        if support_levels:
            recommendation['key_levels']['nearest_support'] = self._find_nearest_level(current_price, support_levels)
        if resistance_levels:
            recommendation['key_levels']['nearest_resistance'] = self._find_nearest_level(current_price, resistance_levels)
        
        return recommendation
    
    def _calculate_risk_level(self, market_structure: Dict) -> str:
        """計算風險等級"""
        volatility = market_structure.get('volatility', 0)
        trend = market_structure.get('trend', {}).get('overall', '中性')
        
        if volatility > 0.5 or trend == "強勢下跌":
            return "高風險"
        elif volatility > 0.3:
            return "中風險"
        else:
            return "低風險"