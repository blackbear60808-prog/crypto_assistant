# modules/smc_scanner.py
import pandas as pd
import numpy as np
import logging
import time
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

class SMCScanner:
    def __init__(self, okx_api, smc_strategy, db, config):
        self.okx_api = okx_api
        self.smc_strategy = smc_strategy
        self.db = db
        self.config = config.get('smc_scanner', {})
        self.logger = logging.getLogger('smc_scanner')
        
        # 掃描狀態
        self.is_scanning = False
        self.last_scan_time = None
        self.scan_results = {}
        self.high_confidence_signals = []
        
        # 執行緒池
        self.executor = None
        
        self.logger.info("SMC掃描器初始化完成")
    
    def get_all_perpetual_pairs(self) -> List[str]:
        """獲取所有永續合約交易對"""
        try:
            # 主要永續合約交易對 (USDT保證金)
            perpetual_pairs = [
                # 主要幣種
                "BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", 
                "ADA-USDT-SWAP", "DOT-USDT-SWAP", "XRP-USDT-SWAP",
                "LTC-USDT-SWAP", "BNB-USDT-SWAP", "AVAX-USDT-SWAP",
                "MATIC-USDT-SWAP", "LINK-USDT-SWAP", "UNI-USDT-SWAP",
                "DOGE-USDT-SWAP", "ATOM-USDT-SWAP", "NEAR-USDT-SWAP",
                
                # 中市值幣種
                "ALGO-USDT-SWAP", "FIL-USDT-SWAP", "ETC-USDT-SWAP",
                "XLM-USDT-SWAP", "EOS-USDT-SWAP", "XTZ-USDT-SWAP",
                "AAVE-USDT-SWAP", "SUSHI-USDT-SWAP", "MKR-USDT-SWAP",
                "COMP-USDT-SWAP", "YFI-USDT-SWAP", "SNX-USDT-SWAP",
                
                # 新興幣種
                "SAND-USDT-SWAP", "MANA-USDT-SWAP", "ENJ-USDT-SWAP",
                "GALA-USDT-SWAP", "APE-USDT-SWAP", "GMT-USDT-SWAP",
                "IMX-USDT-SWAP", "RNDR-USDT-SWAP", "OP-USDT-SWAP",
                "ARB-USDT-SWAP", "APT-USDT-SWAP", "SUI-USDT-SWAP"
            ]
            
            self.logger.info(f"獲取到 {len(perpetual_pairs)} 個永續合約交易對")
            return perpetual_pairs
            
        except Exception as e:
            self.logger.error(f"獲取永續合約交易對錯誤: {str(e)}")
            return []
    
    def scan_single_pair(self, pair: str, timeframe: str = '4H') -> Optional[Dict]:
        """掃描單一交易對的SMC架構"""
        try:
            self.logger.debug(f"開始掃描 {pair} ({timeframe})")
            
            # 獲取K線數據
            ohlcv_data = self.okx_api.get_ohlcv(pair, timeframe, 200)
            if not ohlcv_data or len(ohlcv_data) < 100:
                self.logger.warning(f"{pair} 數據不足，跳過掃描")
                return None
            
            # 計算SMC等級
            smc_data = self.smc_strategy.calculate_smc_levels(pair, ohlcv_data)
            if not smc_data:
                return None
            
            # 分析交易機會
            opportunity = self.analyze_trading_opportunity(pair, smc_data, timeframe)
            
            self.logger.debug(f"完成掃描 {pair}: {opportunity.get('signal_strength', 0)}")
            return opportunity
            
        except Exception as e:
            self.logger.error(f"掃描 {pair} 錯誤: {str(e)}")
            return None
    
    def analyze_trading_opportunity(self, pair: str, smc_data: Dict, timeframe: str) -> Dict:
        """分析交易機會"""
        try:
            current_price = smc_data['current_price']
            market_structure = smc_data['market_structure']
            trading_signals = smc_data['trading_signals']
            bias = smc_data['bias']
            confidence = smc_data.get('confidence', 0.5)
            
            # 計算信號強度
            signal_strength = self.calculate_signal_strength(smc_data)
            
            # 確定交易方向
            trade_direction = self.determine_trade_direction(bias, trading_signals)
            
            # 計算風險等級
            risk_level = self.calculate_risk_level(smc_data)
            
            # 尋找進出場點位
            entry_points = self.find_entry_points(current_price, smc_data, trade_direction)
            stop_loss_points = self.find_stop_loss_points(current_price, smc_data, trade_direction)
            take_profit_points = self.find_take_profit_points(current_price, smc_data, trade_direction)
            
            opportunity = {
                'symbol': pair,
                'timeframe': timeframe,
                'timestamp': datetime.now().isoformat(),
                'current_price': current_price,
                'trade_direction': trade_direction,
                'signal_strength': signal_strength,
                'risk_level': risk_level,
                'confidence': confidence,
                'bias': bias,
                'market_structure': market_structure,
                'entry_points': entry_points,
                'stop_loss_points': stop_loss_points,
                'take_profit_points': take_profit_points,
                'reward_risk_ratio': self.calculate_reward_risk_ratio(entry_points, stop_loss_points, take_profit_points),
                'volume_status': market_structure.get('volume_profile', {}).get('status', '正常'),
                'volatility': market_structure.get('volatility', 0),
                'key_levels': {
                    'support': smc_data.get('support_levels', [])[:3],
                    'resistance': smc_data.get('resistance_levels', [])[:3]
                }
            }
            
            return opportunity
            
        except Exception as e:
            self.logger.error(f"分析交易機會錯誤 {pair}: {str(e)}")
            return {}
    
    def calculate_signal_strength(self, smc_data: Dict) -> float:
        """計算信號強度"""
        try:
            factors = []
            
            # 置信度因子
            confidence = smc_data.get('confidence', 0.5)
            factors.append(confidence)
            
            # 趨勢強度因子
            trend_score = abs(smc_data['market_structure']['trend']['score']) / 3.0
            factors.append(trend_score)
            
            # 等級清晰度因子
            support_levels = len(smc_data.get('support_levels', []))
            resistance_levels = len(smc_data.get('resistance_levels', []))
            level_clarity = min((support_levels + resistance_levels) / 6.0, 1.0)
            factors.append(level_clarity)
            
            # 成交量因子
            volume_status = smc_data['market_structure']['volume_profile']['status']
            volume_factor = 1.0 if volume_status in ['異常大量', '放量'] else 0.5
            factors.append(volume_factor)
            
            # 信號數量因子
            buy_signals = len(smc_data['trading_signals'].get('buy_signals', []))
            sell_signals = len(smc_data['trading_signals'].get('sell_signals', []))
            signal_count = buy_signals + sell_signals
            signal_factor = min(signal_count / 4.0, 1.0)
            factors.append(signal_factor)
            
            # 計算加權平均
            weights = [0.3, 0.25, 0.2, 0.15, 0.1]  # 置信度權重最高
            weighted_strength = sum(f * w for f, w in zip(factors, weights))
            
            return min(weighted_strength, 1.0)
            
        except Exception as e:
            self.logger.error(f"計算信號強度錯誤: {str(e)}")
            return 0.5
    
    def determine_trade_direction(self, bias: str, trading_signals: Dict) -> str:
        """確定交易方向"""
        try:
            buy_signals = trading_signals.get('buy_signals', [])
            sell_signals = trading_signals.get('sell_signals', [])
            
            if bias == "偏多" and len(buy_signals) > len(sell_signals):
                return "做多"
            elif bias == "偏空" and len(sell_signals) > len(buy_signals):
                return "做空"
            else:
                return "觀望"
                
        except Exception as e:
            self.logger.error(f"確定交易方向錯誤: {str(e)}")
            return "觀望"
    
    def calculate_risk_level(self, smc_data: Dict) -> str:
        """計算風險等級"""
        try:
            signal_strength = self.calculate_signal_strength(smc_data)
            volatility = smc_data['market_structure'].get('volatility', 0)
            
            if signal_strength >= self.config.get('risk_levels', {}).get('high', 0.9):
                return "低風險"
            elif signal_strength >= self.config.get('risk_levels', {}).get('medium', 0.7):
                return "中風險"
            else:
                return "高風險"
                
        except Exception as e:
            self.logger.error(f"計算風險等級錯誤: {str(e)}")
            return "高風險"
    
    def find_entry_points(self, current_price: float, smc_data: Dict, direction: str) -> List[Dict]:
        """尋找進場點位"""
        try:
            entry_points = []
            support_levels = smc_data.get('support_levels', [])
            resistance_levels = smc_data.get('resistance_levels', [])
            
            if direction == "做多":
                # 在支撐位附近尋找買入機會
                for level in support_levels[:3]:  # 前3個最強支撐
                    if current_price <= level['price'] * 1.02:  # 當前價格在支撐位上方2%以內
                        entry_points.append({
                            'price': level['price'],
                            'strength': level.get('strength', 0.5),
                            'type': '支撐位買入',
                            'distance_pct': abs(current_price - level['price']) / current_price
                        })
            
            elif direction == "做空":
                # 在阻力位附近尋找賣出機會
                for level in resistance_levels[:3]:  # 前3個最強阻力
                    if current_price >= level['price'] * 0.98:  # 當前價格在阻力位下方2%以內
                        entry_points.append({
                            'price': level['price'],
                            'strength': level.get('strength', 0.5),
                            'type': '阻力位賣出',
                            'distance_pct': abs(current_price - level['price']) / current_price
                        })
            
            # 按強度排序
            entry_points.sort(key=lambda x: x['strength'], reverse=True)
            return entry_points[:2]  # 返回前2個最佳進場點
            
        except Exception as e:
            self.logger.error(f"尋找進場點位錯誤: {str(e)}")
            return []
    
    def find_stop_loss_points(self, current_price: float, smc_data: Dict, direction: str) -> List[Dict]:
        """尋找止損點位"""
        try:
            stop_loss_points = []
            support_levels = smc_data.get('support_levels', [])
            resistance_levels = smc_data.get('resistance_levels', [])
            
            if direction == "做多":
                # 做多止損放在下方支撐位
                for level in support_levels:
                    if level['price'] < current_price:
                        stop_loss_points.append({
                            'price': level['price'] * 0.99,  # 在支撐位下方1%
                            'strength': level.get('strength', 0.5),
                            'type': '支撐止損',
                            'risk_pct': (current_price - level['price'] * 0.99) / current_price
                        })
            
            elif direction == "做空":
                # 做空止損放在上方阻力位
                for level in resistance_levels:
                    if level['price'] > current_price:
                        stop_loss_points.append({
                            'price': level['price'] * 1.01,  # 在阻力位上方1%
                            'strength': level.get('strength', 0.5),
                            'type': '阻力止損',
                            'risk_pct': (level['price'] * 1.01 - current_price) / current_price
                        })
            
            # 按風險百分比排序 (選擇風險較小的)
            stop_loss_points.sort(key=lambda x: x['risk_pct'])
            return stop_loss_points[:2]  # 返回前2個最佳止損點
            
        except Exception as e:
            self.logger.error(f"尋找止損點位錯誤: {str(e)}")
            return []
    
    def find_take_profit_points(self, current_price: float, smc_data: Dict, direction: str) -> List[Dict]:
        """尋找止盈點位"""
        try:
            take_profit_points = []
            support_levels = smc_data.get('support_levels', [])
            resistance_levels = smc_data.get('resistance_levels', [])
            
            if direction == "做多":
                # 做多止盈放在上方阻力位
                for level in resistance_levels:
                    if level['price'] > current_price:
                        take_profit_points.append({
                            'price': level['price'],
                            'strength': level.get('strength', 0.5),
                            'type': '阻力止盈',
                            'reward_pct': (level['price'] - current_price) / current_price
                        })
            
            elif direction == "做空":
                # 做空止盈放在下方支撐位
                for level in support_levels:
                    if level['price'] < current_price:
                        take_profit_points.append({
                            'price': level['price'],
                            'strength': level.get('strength', 0.5),
                            'type': '支撐止盈',
                            'reward_pct': (current_price - level['price']) / current_price
                        })
            
            # 按回報百分比排序
            take_profit_points.sort(key=lambda x: x['reward_pct'], reverse=True)
            return take_profit_points[:3]  # 返回前3個最佳止盈點
            
        except Exception as e:
            self.logger.error(f"尋找止盈點位錯誤: {str(e)}")
            return []
    
    def calculate_reward_risk_ratio(self, entry_points: List, stop_loss_points: List, take_profit_points: List) -> float:
        """計算報酬風險比"""
        try:
            if not entry_points or not stop_loss_points or not take_profit_points:
                return 0.0
            
            best_entry = entry_points[0]
            best_stop_loss = stop_loss_points[0]
            best_take_profit = take_profit_points[0]
            
            entry_price = best_entry['price']
            stop_loss_price = best_stop_loss['price']
            take_profit_price = best_take_profit['price']
            
            if entry_price > stop_loss_price:  # 做多
                risk = entry_price - stop_loss_price
                reward = take_profit_price - entry_price
            else:  # 做空
                risk = stop_loss_price - entry_price
                reward = entry_price - take_profit_price
            
            if risk == 0:
                return 0.0
            
            ratio = reward / risk
            return round(ratio, 2)
            
        except Exception as e:
            self.logger.error(f"計算報酬風險比錯誤: {str(e)}")
            return 0.0
    
    def scan_all_pairs(self, pairs: List[str] = None) -> Dict:
        """掃描所有交易對"""
        try:
            if not pairs:
                pairs = self.get_all_perpetual_pairs()
            
            self.is_scanning = True
            self.last_scan_time = datetime.now()
            
            self.logger.info(f"開始掃描 {len(pairs)} 個交易對")
            
            results = {}
            high_confidence_signals = []
            
            # 使用執行緒池並行掃描
            max_workers = self.config.get('max_concurrent_scans', 5)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任務
                future_to_pair = {
                    executor.submit(self.scan_single_pair, pair, '4H'): pair 
                    for pair in pairs
                }
                
                # 收集結果
                for future in as_completed(future_to_pair):
                    pair = future_to_pair[future]
                    try:
                        result = future.result(timeout=60)  # 60秒超時
                        if result:
                            results[pair] = result
                            
                            # 檢查是否為高置信度信號
                            if (result.get('signal_strength', 0) >= 
                                self.config.get('min_confidence', 0.7)):
                                high_confidence_signals.append(result)
                                
                    except Exception as e:
                        self.logger.error(f"掃描 {pair} 時發生錯誤: {str(e)}")
                        continue
            
            # 更新狀態
            self.scan_results = results
            self.high_confidence_signals = sorted(
                high_confidence_signals, 
                key=lambda x: x['signal_strength'], 
                reverse=True
            )
            
            self.is_scanning = False
            
            # 記錄掃描結果
            self.log_scan_results(results, high_confidence_signals)
            
            self.logger.info(f"掃描完成: 找到 {len(high_confidence_signals)} 個高置信度信號")
            return {
                'total_scanned': len(pairs),
                'successful_scans': len(results),
                'high_confidence_signals': high_confidence_signals,
                'scan_time': self.last_scan_time.isoformat(),
                'results': results
            }
            
        except Exception as e:
            self.logger.error(f"掃描所有交易對錯誤: {str(e)}")
            self.is_scanning = False
            return {}
    
    def log_scan_results(self, results: Dict, high_confidence_signals: List):
        """記錄掃描結果到資料庫"""
        try:
            cursor = self.db.conn.cursor()
            
            for signal in high_confidence_signals:
                cursor.execute('''
                    INSERT INTO smc_scan_results 
                    (symbol, timeframe, signal_strength, trade_direction, risk_level, 
                     confidence, reward_risk_ratio, entry_points, stop_loss_points, 
                     take_profit_points, scan_timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal['symbol'],
                    signal['timeframe'],
                    signal['signal_strength'],
                    signal['trade_direction'],
                    signal['risk_level'],
                    signal['confidence'],
                    signal['reward_risk_ratio'],
                    json.dumps(signal['entry_points'], ensure_ascii=False),
                    json.dumps(signal['stop_loss_points'], ensure_ascii=False),
                    json.dumps(signal['take_profit_points'], ensure_ascii=False),
                    signal['timestamp'],
                    datetime.now().isoformat()
                ))
            
            self.db.conn.commit()
            self.logger.info(f"已記錄 {len(high_confidence_signals)} 個掃描結果到資料庫")
            
        except Exception as e:
            self.logger.error(f"記錄掃描結果錯誤: {str(e)}")
    
    def get_high_confidence_signals(self, min_confidence: float = None) -> List[Dict]:
        """獲取高置信度信號"""
        if min_confidence is None:
            min_confidence = self.config.get('min_confidence', 0.7)
        
        return [
            signal for signal in self.high_confidence_signals 
            if signal.get('signal_strength', 0) >= min_confidence
        ]
    
    def start_auto_scan(self):
        """啟動自動掃描"""
        if self.is_scanning:
            self.logger.warning("掃描器正在運行中")
            return
        
        def auto_scan_worker():
            while self.is_scanning:
                try:
                    self.scan_all_pairs()
                    
                    # 等待下一次掃描
                    interval = self.config.get('scan_interval_minutes', 30)
                    time.sleep(interval * 60)
                    
                except Exception as e:
                    self.logger.error(f"自動掃描錯誤: {str(e)}")
                    time.sleep(60)  # 錯誤時等待1分鐘
        
        self.is_scanning = True
        thread = threading.Thread(target=auto_scan_worker, daemon=True)
        thread.start()
        self.logger.info("自動掃描已啟動")
    
    def stop_auto_scan(self):
        """停止自動掃描"""
        self.is_scanning = False
        self.logger.info("自動掃描已停止")
    
    def get_scan_status(self) -> Dict:
        """獲取掃描狀態"""
        return {
            'is_scanning': self.is_scanning,
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'total_signals': len(self.high_confidence_signals),
            'high_confidence_count': len(self.get_high_confidence_signals())
        }