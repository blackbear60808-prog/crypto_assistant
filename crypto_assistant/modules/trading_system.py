# modules/trading_system.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass

@dataclass
class TradingPosition:
    """交易持倉資料類別"""
    position_id: str
    symbol: str
    position_type: str  # LONG, SHORT
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    status: str  # OPEN, CLOSED
    created_at: str
    pnl: float = 0.0
    leverage: int = 1
    order_id: str = ""
    exit_price: float = 0.0
    closed_at: str = ""
    close_reason: str = ""

@dataclass
class SpotHolding:
    """現貨持倉資料類別"""
    symbol: str
    quantity: float
    avg_price: float
    total_cost: float
    last_buy_price: float = 0.0
    last_buy_time: str = ""
    last_sell_price: float = 0.0
    last_sell_time: str = ""

class TradingSystem:
    def __init__(self, okx_api, db, discord_bot, config, smc_strategy=None):
        self.okx_api = okx_api
        self.db = db
        self.discord_bot = discord_bot
        self.config = config
        self.smc_strategy = smc_strategy
        
        # 初始化設定
        self._load_configurations()
        
        # 帳戶狀態
        self.balance = self.initial_capital
        self.available_balance = self.initial_capital
        self.positions: Dict[str, TradingPosition] = {}
        self.spot_holdings: Dict[str, SpotHolding] = {}
        self.daily_pnl = 0.0
        self.today_start_balance = self.initial_capital
        self.position_count = 0
        self.total_trades_today = 0
        
        # 自動交易控制
        self.auto_trading = False
        self.trading_thread = None
        self.last_trade_time = None
        
        # 初始化子系統
        self._initialize_subsystems()
        
        self.logger = logging.getLogger('TradingSystem')
        
        # 載入設定和恢復狀態
        self.load_settings()
        self._recover_positions()
        
    def _load_configurations(self):
        """載入所有交易設定"""
        # 基礎交易設定
        trading_config = self.config.get('trading', {})
        self.initial_capital = trading_config.get('initial_capital', 1000.0)
        self.risk_percent = trading_config.get('risk_percent', 2.0)
        self.atr_multiplier = trading_config.get('atr_multiplier', 2.0)
        self.max_positions = trading_config.get('max_positions', 5)
        self.enabled = trading_config.get('enabled', False)
        self.trading_mode = trading_config.get('trading_mode', 'both')
        self.cooldown_period = trading_config.get('cooldown_period', 300)  # 冷卻時間(秒)
        
        # SMC 交易設定
        smc_config = self.config.get('smc_trading', {})
        self.smc_enabled = smc_config.get('enabled', True)
        self.smc_confidence_threshold = smc_config.get('confidence_threshold', 0.7)
        self.use_smc_signals = smc_config.get('use_signals', True)
        self.smc_min_volume = smc_config.get('min_volume', 1000000)  # 最小成交量
        
        # 現貨交易設定
        spot_config = self.config.get('spot_trading', {})
        self.spot_enabled = spot_config.get('enabled', True)
        self.spot_pairs = spot_config.get('default_pairs', ['BTC-USDT', 'ETH-USDT', 'SOL-USDT'])
        self.min_spot_amount = spot_config.get('min_trade_amount', 10.0)
        self.max_spot_amount = spot_config.get('max_trade_amount', 1000.0)
        self.spot_trading_fee = spot_config.get('trading_fee', 0.001)  # 交易手續費
        
        # 合約交易設定
        futures_config = self.config.get('futures_trading', {})
        self.futures_enabled = futures_config.get('enabled', True)
        self.futures_pairs = futures_config.get('default_pairs', ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP'])
        self.default_leverage = futures_config.get('default_leverage', 10)
        self.max_leverage = futures_config.get('max_leverage', 20)
        self.futures_trading_fee = futures_config.get('trading_fee', 0.0004)  # 合約手續費
        
        # 風險管理設定
        risk_config = self.config.get('risk_management', {})
        self.max_daily_loss = risk_config.get('max_daily_loss', 0.05)
        self.max_position_size = risk_config.get('max_position_size', 0.2)
        self.stop_loss_enabled = risk_config.get('stop_loss_enabled', True)
        self.take_profit_enabled = risk_config.get('take_profit_enabled', True)
        self.max_daily_trades = risk_config.get('max_daily_trades', 20)
        self.volatility_filter = risk_config.get('volatility_filter', True)
        self.max_volatility = risk_config.get('max_volatility', 0.1)  # 最大波動率
        
    def _initialize_subsystems(self):
        """初始化子系統"""
        try:
            from modules.technical_indicators import TechnicalIndicators
            from modules.smart_stoploss import SmartStopLoss
            
            technical_indicators = TechnicalIndicators()
            self.smart_stoploss = SmartStopLoss(self.db, technical_indicators)
            
            # 更新智能止損設定
            stoploss_settings = {
                'atr_multiplier': self.atr_multiplier,
                'max_risk_per_trade': self.risk_percent / 100,
                'volatility_threshold': self.max_volatility
            }
            self.smart_stoploss.update_settings(stoploss_settings)
            
        except Exception as e:
            self.logger.error(f"初始化子系統失敗: {e}")
            # 創建空的替代物件
            self.smart_stoploss = None

    def _recover_positions(self):
        """從資料庫恢復持倉狀態"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT * FROM trade_records 
                WHERE status = 'OPEN' AND trading_type = 'FUTURES'
            ''')
            open_positions = cursor.fetchall()
            
            for position in open_positions:
                position_obj = TradingPosition(
                    position_id=position['position_id'],
                    symbol=position['symbol'],
                    position_type=position['action'].replace('FUTURES_ENTRY_', ''),
                    entry_price=position['price'],
                    quantity=position['quantity'],
                    stop_loss=0.0,  # 需要從其他表獲取
                    take_profit=0.0,
                    status='OPEN',
                    created_at=position['timestamp']
                )
                self.positions[position_obj.position_id] = position_obj
            
            self.logger.info(f"恢復 {len(open_positions)} 個持倉")
            
        except Exception as e:
            self.logger.error(f"恢復持倉失敗: {e}")

    def start_auto_trading(self):
        """啟動自動交易"""
        if self.auto_trading:
            return False, "自動交易已在運行中"
        
        if not self._check_trading_conditions():
            return False, "交易條件檢查失敗，請檢查設定"
        
        try:
            self.auto_trading = True
            self.trading_thread = threading.Thread(
                target=self._auto_trading_loop, 
                daemon=True,
                name="AutoTradingThread"
            )
            self.trading_thread.start()
            
            message = "🔰 自動交易系統已啟動"
            self.logger.info(message)
            
            if self.discord_bot.enabled:
                self.discord_bot.send_message(message, "success")
            
            return True, message
            
        except Exception as e:
            error_msg = f"❌ 啟動自動交易失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def stop_auto_trading(self):
        """停止自動交易"""
        if not self.auto_trading:
            return False, "自動交易未在運行"
        
        try:
            self.auto_trading = False
            if self.trading_thread and self.trading_thread.is_alive():
                self.trading_thread.join(timeout=10)
            
            message = "⏹️ 自動交易系統已停止"
            self.logger.info(message)
            
            if self.discord_bot.enabled:
                self.discord_bot.send_message(message, "info")
            
            return True, message
            
        except Exception as e:
            error_msg = f"❌ 停止自動交易失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def _check_trading_conditions(self):
        """檢查交易條件"""
        try:
            # 檢查 API 連線
            if not self.okx_api.test_connection():
                self.logger.error("API 連線失敗")
                return False
            
            # 檢查資金餘額
            balance_info = self.get_spot_balance()
            if not balance_info or balance_info.get('total_balance', 0) < self.min_spot_amount:
                self.logger.error("資金餘額不足")
                return False
            
            # 檢查資料庫連線
            if not self.db.test_connection():
                self.logger.error("資料庫連線失敗")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"交易條件檢查失敗: {e}")
            return False

    def _auto_trading_loop(self):
        """自動交易主循環"""
        loop_count = 0
        
        while self.auto_trading:
            try:
                loop_count += 1
                
                # 每10個循環更新一次帳戶資訊
                if loop_count % 10 == 0:
                    self._update_account_info()
                
                # 檢查風險限制
                if self._check_risk_limits():
                    self.logger.warning("達到風險限制，停止交易")
                    self.stop_auto_trading()
                    continue
                
                # 檢查持倉止損
                self._check_position_stops()
                
                # 執行交易策略
                if self._can_execute_trade():
                    self._execute_trading_strategy()
                
                # 清理過期資料
                if loop_count % 30 == 0:
                    self._cleanup_old_data()
                
                time.sleep(10)  # 每10秒檢查一次
                
            except Exception as e:
                self.logger.error(f"自動交易循環錯誤: {e}")
                time.sleep(30)  # 錯誤時等待更久

    def _can_execute_trade(self):
        """檢查是否可以執行交易"""
        try:
            # 檢查持倉數量限制
            if len(self.positions) >= self.max_positions:
                return False
            
            # 檢查每日交易次數限制
            if self.total_trades_today >= self.max_daily_trades:
                self.logger.warning("達到每日交易次數限制")
                return False
            
            # 檢查冷卻時間
            if self.last_trade_time:
                time_since_last_trade = time.time() - self.last_trade_time
                if time_since_last_trade < self.cooldown_period:
                    return False
            
            # 檢查市場波動
            if self.volatility_filter and not self._check_market_volatility():
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"檢查交易條件錯誤: {e}")
            return False

    def _check_market_volatility(self):
        """檢查市場波動率"""
        try:
            # 這裡可以實現更複雜的波動率檢查
            # 暫時返回 True
            return True
        except Exception as e:
            self.logger.error(f"檢查市場波動率錯誤: {e}")
            return False

    def _check_risk_limits(self):
        """檢查風險限制"""
        try:
            # 檢查每日虧損限制
            daily_loss_pct = abs(self.daily_pnl) / self.today_start_balance
            if daily_loss_pct >= self.max_daily_loss:
                self.logger.warning(f"達到每日虧損限制: {daily_loss_pct:.2%}")
                return True
            
            # 檢查最大持倉數量
            if len(self.positions) >= self.max_positions:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"檢查風險限制錯誤: {e}")
            return True  # 錯誤時保守起見停止交易

    def _check_position_stops(self):
        """檢查持倉止損"""
        try:
            positions_to_close = []
            
            for position_id, position in self.positions.items():
                if position.status != 'OPEN':
                    continue
                
                symbol = position.symbol
                current_price = self._get_current_price(symbol)
                
                if current_price is None:
                    continue
                
                # 計算當前盈虧
                current_pnl = self._calculate_position_pnl(position, current_price)
                position.pnl = current_pnl
                
                # 檢查止損條件
                if self._should_close_position(position, current_price):
                    positions_to_close.append(position_id)
                
                # 更新移動止損
                if self.smart_stoploss:
                    updated_stop = self.smart_stoploss.update_position_stop_loss(
                        position_id, 
                        symbol, 
                        position.position_type, 
                        position.entry_price, 
                        current_price
                    )
                    position.stop_loss = updated_stop
            
            # 關閉觸發條件的持倉
            for position_id in positions_to_close:
                self.close_position(position_id, "STOP_LOSS")
                
        except Exception as e:
            self.logger.error(f"檢查持倉止損錯誤: {e}")

    def _should_close_position(self, position: TradingPosition, current_price: float) -> bool:
        """檢查是否應該平倉"""
        try:
            # 檢查止損
            if position.stop_loss > 0:
                if (position.position_type == 'LONG' and current_price <= position.stop_loss) or \
                   (position.position_type == 'SHORT' and current_price >= position.stop_loss):
                    self.logger.info(f"{position.symbol} 觸發止損: {current_price}")
                    return True
            
            # 檢查止盈
            if position.take_profit > 0:
                if (position.position_type == 'LONG' and current_price >= position.take_profit) or \
                   (position.position_type == 'SHORT' and current_price <= position.take_profit):
                    self.logger.info(f"{position.symbol} 觸發止盈: {current_price}")
                    return True
            
            # 檢查智能止損
            if self.smart_stoploss and self.smart_stoploss.check_stop_loss_hit(position.position_id, current_price):
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"檢查平倉條件錯誤: {e}")
            return False

    def _calculate_position_pnl(self, position: TradingPosition, current_price: float) -> float:
        """計算持倉盈虧"""
        try:
            if position.position_type == 'LONG':
                pnl = (current_price - position.entry_price) * position.quantity
            else:  # SHORT
                pnl = (position.entry_price - current_price) * position.quantity
            
            # 考慮手續費
            pnl -= position.quantity * position.entry_price * self.futures_trading_fee * 2  # 開倉和平倉
            
            return pnl * position.leverage
            
        except Exception as e:
            self.logger.error(f"計算盈虧錯誤: {e}")
            return 0.0

    def _execute_trading_strategy(self):
        """執行交易策略"""
        try:
            # 根據交易模式執行策略
            if self.trading_mode in ['both', 'futures'] and self.futures_enabled:
                self._execute_futures_strategy()
            
            if self.trading_mode in ['both', 'spot'] and self.spot_enabled:
                self._execute_spot_strategy()
                    
        except Exception as e:
            self.logger.error(f"執行交易策略錯誤: {e}")

    def _execute_futures_strategy(self):
        """執行合約交易策略"""
        try:
            for symbol in self.futures_pairs[:3]:  # 只交易前3個幣種
                if not self._can_execute_trade():
                    break
                
                # 獲取交易信號
                signal, confidence = self._get_trading_signal_with_confidence(symbol)
                current_price = self._get_current_price(symbol)
                
                if signal == 'LONG' and current_price:
                    success, message = self.open_long_position(symbol, current_price)
                    if success:
                        self.last_trade_time = time.time()
                        self.total_trades_today += 1
                elif signal == 'SHORT' and current_price:
                    success, message = self.open_short_position(symbol, current_price)
                    if success:
                        self.last_trade_time = time.time()
                        self.total_trades_today += 1
                    
        except Exception as e:
            self.logger.error(f"執行合約策略錯誤: {e}")

    def _execute_spot_strategy(self):
        """執行現貨交易策略"""
        try:
            for symbol in self.spot_pairs[:3]:  # 只交易前3個幣種
                # 獲取交易信號
                signal, confidence = self._get_trading_signal_with_confidence(symbol)
                current_price = self._get_current_price(symbol)
                
                if signal == 'LONG' and current_price:
                    # 檢查是否已經持有
                    if symbol not in self.spot_holdings or self.spot_holdings[symbol].quantity == 0:
                        success, message = self.spot_buy(symbol, current_price)
                        if success:
                            self.last_trade_time = time.time()
                            self.total_trades_today += 1
                elif signal == 'SHORT' and current_price and symbol in self.spot_holdings:
                    # 現貨做空 = 賣出持倉
                    if self.spot_holdings[symbol].quantity > 0:
                        success, message = self.spot_sell(symbol, current_price, self.spot_holdings[symbol].quantity)
                        if success:
                            self.last_trade_time = time.time()
                            self.total_trades_today += 1
                    
        except Exception as e:
            self.logger.error(f"執行現貨策略錯誤: {e}")

    def _get_trading_signal_with_confidence(self, symbol: str) -> Tuple[str, float]:
        """獲取交易信號和置信度"""
        try:
            # 如果啟用 SMC 策略且可用，優先使用 SMC 信號
            if self.smc_enabled and self.smc_strategy and self.use_smc_signals:
                signal, confidence = self._get_smc_trading_signal(symbol)
                if signal != 'HOLD' and confidence >= self.smc_confidence_threshold:
                    return signal, confidence
            
            # 備用策略：技術指標信號
            return self._get_technical_signal(symbol)
            
        except Exception as e:
            self.logger.error(f"獲取交易信號錯誤 {symbol}: {e}")
            return 'HOLD', 0.0

    def _get_smc_trading_signal(self, symbol: str) -> Tuple[str, float]:
        """獲取 SMC 交易信號"""
        try:
            recommendation = self.smc_strategy.get_trading_recommendations(symbol)
            if not recommendation or 'error' in recommendation:
                return 'HOLD', 0.0
            
            action = recommendation.get('action', '持有')
            confidence = recommendation.get('confidence', 0.0)
            
            # 轉換為交易信號
            if action == '考慮買入':
                return 'LONG', confidence
            elif action == '考慮賣出':
                return 'SHORT', confidence
            else:
                return 'HOLD', confidence
                
        except Exception as e:
            self.logger.error(f"獲取 SMC 交易信號錯誤 {symbol}: {e}")
            return 'HOLD', 0.0

    def _get_technical_signal(self, symbol: str) -> Tuple[str, float]:
        """獲取技術指標信號 (備用策略)"""
        try:
            # 這裡可以實現基於技術指標的信號生成
            # 暫時返回隨機信號用於測試
            import random
            signals = ['LONG', 'SHORT', 'HOLD']
            weights = [0.4, 0.4, 0.2]  # 權重分配
            signal = random.choices(signals, weights=weights)[0]
            confidence = random.uniform(0.5, 0.9) if signal != 'HOLD' else 0.0
            
            return signal, confidence
            
        except Exception as e:
            self.logger.error(f"獲取技術指標信號錯誤 {symbol}: {e}")
            return 'HOLD', 0.0

    # ==================== 合約交易方法 ====================
    
    def open_long_position(self, symbol: str, price: float, quantity: float = None):
        """開多倉 (合約)"""
        try:
            if not quantity:
                quantity = self._calculate_position_size(price)
            
            if quantity <= 0:
                return False, "計算的倉位大小無效"
            
            # 設置槓桿
            if not self.okx_api.futures_set_leverage(symbol, self.default_leverage):
                self.logger.warning(f"設置槓桿失敗: {symbol}")
            
            # 下單
            order = self.okx_api.futures_create_order(
                symbol=symbol,
                order_type='market',
                side='buy',
                amount=quantity,
                leverage=self.default_leverage
            )
            
            if not order:
                return False, "下單失敗"
            
            # 計算智能止損和止盈
            stop_loss = self._calculate_stop_loss(symbol, 'LONG', price)
            take_profit = self._calculate_take_profit(symbol, 'LONG', price)
            
            position_id = f"LONG_{symbol}_{int(time.time())}"
            
            position = TradingPosition(
                position_id=position_id,
                symbol=symbol,
                position_type='LONG',
                entry_price=price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                status='OPEN',
                created_at=datetime.now().isoformat(),
                leverage=self.default_leverage,
                order_id=order.get('id', '')
            )
            
            self.positions[position_id] = position
            self.position_count += 1
            
            # 初始化智能止損
            if self.smart_stoploss:
                self.smart_stoploss.update_position_stop_loss(position_id, symbol, 'LONG', price, price)
            
            # 記錄交易
            self._save_trade_record(position_id, symbol, 'FUTURES_ENTRY_LONG', price, quantity)
            
            message = f"✅ 開多倉成功: {symbol} 價格={price:.4f} 數量={quantity:.4f} 槓桿={self.default_leverage}x"
            self.logger.info(message)
            
            if self.discord_bot.enabled:
                self.discord_bot.send_trading_signal(symbol, "LONG", price, 0.7, "合約策略")
            
            return True, message
            
        except Exception as e:
            error_msg = f"❌ 開多倉失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def open_short_position(self, symbol: str, price: float, quantity: float = None):
        """開空倉 (合約)"""
        try:
            if not quantity:
                quantity = self._calculate_position_size(price)
            
            if quantity <= 0:
                return False, "計算的倉位大小無效"
            
            # 設置槓桿
            if not self.okx_api.futures_set_leverage(symbol, self.default_leverage):
                self.logger.warning(f"設置槓桿失敗: {symbol}")
            
            # 下單
            order = self.okx_api.futures_create_order(
                symbol=symbol,
                order_type='market',
                side='sell',
                amount=quantity,
                leverage=self.default_leverage
            )
            
            if not order:
                return False, "下單失敗"
            
            # 計算智能止損和止盈
            stop_loss = self._calculate_stop_loss(symbol, 'SHORT', price)
            take_profit = self._calculate_take_profit(symbol, 'SHORT', price)
            
            position_id = f"SHORT_{symbol}_{int(time.time())}"
            
            position = TradingPosition(
                position_id=position_id,
                symbol=symbol,
                position_type='SHORT',
                entry_price=price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                status='OPEN',
                created_at=datetime.now().isoformat(),
                leverage=self.default_leverage,
                order_id=order.get('id', '')
            )
            
            self.positions[position_id] = position
            self.position_count += 1
            
            # 初始化智能止損
            if self.smart_stoploss:
                self.smart_stoploss.update_position_stop_loss(position_id, symbol, 'SHORT', price, price)
            
            # 記錄交易
            self._save_trade_record(position_id, symbol, 'FUTURES_ENTRY_SHORT', price, quantity)
            
            message = f"✅ 開空倉成功: {symbol} 價格={price:.4f} 數量={quantity:.4f} 槓桿={self.default_leverage}x"
            self.logger.info(message)
            
            if self.discord_bot.enabled:
                self.discord_bot.send_trading_signal(symbol, "SHORT", price, 0.7, "合約策略")
            
            return True, message
            
        except Exception as e:
            error_msg = f"❌ 開空倉失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def _calculate_stop_loss(self, symbol: str, position_type: str, entry_price: float) -> float:
        """計算止損價格"""
        try:
            if self.smart_stoploss:
                return self.smart_stoploss.calculate_dynamic_stop_loss(symbol, position_type, entry_price, entry_price)
            
            # 備用止損計算
            if position_type == 'LONG':
                return entry_price * 0.98  # 2% 止損
            else:  # SHORT
                return entry_price * 1.02  # 2% 止損
                
        except Exception as e:
            self.logger.error(f"計算止損錯誤: {e}")
            if position_type == 'LONG':
                return entry_price * 0.98
            else:
                return entry_price * 1.02

    def _calculate_take_profit(self, symbol: str, position_type: str, entry_price: float) -> float:
        """計算止盈價格"""
        try:
            # 風險回報比 1:2
            stop_loss = self._calculate_stop_loss(symbol, position_type, entry_price)
            risk = abs(entry_price - stop_loss)
            
            if position_type == 'LONG':
                return entry_price + risk * 2
            else:  # SHORT
                return entry_price - risk * 2
                
        except Exception as e:
            self.logger.error(f"計算止盈錯誤: {e}")
            if position_type == 'LONG':
                return entry_price * 1.03  # 3% 止盈
            else:
                return entry_price * 0.97  # 3% 止盈
    def close_position(self, position_id: str, reason: str = "MANUAL"):
        """平倉 (合約)"""
        try:
            if position_id not in self.positions:
                return False, "❌ 持倉不存在"
            
            position = self.positions[position_id]
            symbol = position.symbol
            
            if position.status != 'OPEN':
                return False, "❌ 持倉已關閉"
            
            # 獲取當前價格計算盈虧
            current_price = self._get_current_price(symbol)
            if current_price is None:
                return False, "❌ 無法獲取當前價格"
            
            # 平倉
            success = self.okx_api.futures_close_position(symbol, position.position_type.lower())
            
            if not success:
                return False, "❌ 平倉失敗"
            
            # 計算盈虧（考慮手續費）
            pnl = self._calculate_position_pnl(position, current_price)
            
            # 更新持倉狀態
            position.status = 'CLOSED'
            position.exit_price = current_price
            position.closed_at = datetime.now().isoformat()
            position.pnl = pnl
            position.close_reason = reason
            
            # 更新每日盈虧和餘額
            self.daily_pnl += pnl
            self.balance += pnl
            self.available_balance += pnl
            
            # 移除智能止損
            if self.smart_stoploss:
                self.smart_stoploss.remove_position_stop(position_id)
            
            # 記錄交易
            self._save_trade_record(
                position_id, symbol, 'FUTURES_EXIT', 
                current_price, position.quantity, pnl
            )
            
            # 發送通知
            pnl_display = f"盈虧={pnl:+.2f} USDT"
            message = f"✅ 平倉成功: {symbol} {pnl_display} 原因={reason}"
            self.logger.info(message)
            
            if self.discord_bot.enabled:
                pnl_type = "盈利" if pnl >= 0 else "虧損"
                self.discord_bot.send_message(
                    f"平倉通知: {symbol} {pnl_type} {abs(pnl):.2f} USDT", 
                    "success" if pnl >= 0 else "warning"
                )
            
            return True, message
            
        except Exception as e:
            error_msg = f"❌ 平倉失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def close_all_positions(self, reason: str = "MANUAL"):
        """平掉所有持倉"""
        try:
            results = []
            open_positions = self.get_open_positions()
            
            if not open_positions:
                return True, "沒有持倉需要平倉"
            
            for position in open_positions:
                success, message = self.close_position(position.position_id, reason)
                results.append((success, message))
            
            success_count = sum(1 for success, _ in results if success)
            total_count = len(results)
            
            message = f"平倉完成: {success_count}/{total_count} 個持倉"
            self.logger.info(message)
            
            return True, message
            
        except Exception as e:
            error_msg = f"平掉所有持倉失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    # ==================== 現貨交易方法 ====================
    
    def spot_buy(self, symbol: str, price: float, quantity: float = None):
        """現貨買入"""
        try:
            if not quantity:
                quantity = self._calculate_spot_position_size(price)
            
            total_cost = quantity * price
            if total_cost > self.available_balance:
                return False, f"❌ 資金不足，需要 {total_cost:.2f} USDT，可用 {self.available_balance:.2f} USDT"
            
            # 檢查最小交易金額
            if total_cost < self.min_spot_amount:
                return False, f"❌ 交易金額低於最小值 {self.min_spot_amount} USDT"
            
            # 下單
            order = self.okx_api.spot_buy(symbol, quantity, price)
            
            if not order:
                return False, "❌ 下單失敗"
            
            # 計算手續費
            fee = total_cost * self.spot_trading_fee
            
            # 更新現貨持倉
            if symbol not in self.spot_holdings:
                self.spot_holdings[symbol] = SpotHolding(
                    symbol=symbol,
                    quantity=0,
                    avg_price=0,
                    total_cost=0
                )
            
            # 計算平均成本
            current_holding = self.spot_holdings[symbol]
            total_quantity = current_holding.quantity + quantity
            total_cost_new = current_holding.total_cost + total_cost
            avg_price = total_cost_new / total_quantity if total_quantity > 0 else 0
            
            self.spot_holdings[symbol] = SpotHolding(
                symbol=symbol,
                quantity=total_quantity,
                avg_price=avg_price,
                total_cost=total_cost_new,
                last_buy_price=price,
                last_buy_time=datetime.now().isoformat()
            )
            
            # 更新可用餘額（扣除成本和手續費）
            self.available_balance -= (total_cost + fee)
            
            # 記錄交易
            trade_id = f"SPOT_BUY_{symbol}_{int(time.time())}"
            self._save_trade_record(trade_id, symbol, 'SPOT_BUY', price, quantity, -fee)
            
            message = f"✅ 現貨買入成功: {symbol} 價格={price:.4f} 數量={quantity:.4f} 手續費={fee:.4f} USDT"
            self.logger.info(message)
            
            if self.discord_bot.enabled:
                self.discord_bot.send_trading_signal(symbol, "SPOT_BUY", price, 0.7, "現貨策略")
            
            return True, message
            
        except Exception as e:
            error_msg = f"❌ 現貨買入失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def spot_sell(self, symbol: str, price: float, quantity: float = None):
        """現貨賣出"""
        try:
            if symbol not in self.spot_holdings or self.spot_holdings[symbol].quantity <= 0:
                return False, "❌ 沒有持倉"
            
            if quantity is None:
                quantity = self.spot_holdings[symbol].quantity  # 默認賣出全部
            
            if quantity > self.spot_holdings[symbol].quantity:
                return False, f"❌ 賣出數量超過持倉，持有 {self.spot_holdings[symbol].quantity:.4f}"
            
            # 下單
            order = self.okx_api.spot_sell(symbol, quantity, price)
            
            if not order:
                return False, "❌ 下單失敗"
            
            # 計算盈虧和手續費
            avg_price = self.spot_holdings[symbol].avg_price
            pnl = (price - avg_price) * quantity
            fee = (quantity * price) * self.spot_trading_fee
            net_pnl = pnl - fee
            
            # 更新現貨持倉
            remaining_quantity = self.spot_holdings[symbol].quantity - quantity
            remaining_cost = self.spot_holdings[symbol].total_cost * (remaining_quantity / self.spot_holdings[symbol].quantity)
            
            self.spot_holdings[symbol] = SpotHolding(
                symbol=symbol,
                quantity=remaining_quantity,
                avg_price=remaining_cost / remaining_quantity if remaining_quantity > 0 else 0,
                total_cost=remaining_cost,
                last_sell_price=price,
                last_sell_time=datetime.now().isoformat()
            )
            
            # 更新可用餘額（增加收入，扣除手續費）
            self.available_balance += (quantity * price - fee)
            self.balance = self.available_balance  # 簡化處理
            
            # 更新每日盈虧
            self.daily_pnl += net_pnl
            
            # 記錄交易
            trade_id = f"SPOT_SELL_{symbol}_{int(time.time())}"
            self._save_trade_record(trade_id, symbol, 'SPOT_SELL', price, quantity, net_pnl)
            
            message = f"✅ 現貨賣出成功: {symbol} 價格={price:.4f} 數量={quantity:.4f} 淨盈虧={net_pnl:+.2f} USDT"
            self.logger.info(message)
            
            if self.discord_bot.enabled:
                pnl_type = "盈利" if net_pnl >= 0 else "虧損"
                self.discord_bot.send_message(
                    f"現貨賣出: {symbol} {pnl_type} {abs(net_pnl):.2f} USDT", 
                    "success" if net_pnl >= 0 else "warning"
                )
            
            return True, message
            
        except Exception as e:
            error_msg = f"❌ 現貨賣出失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def spot_buy_market(self, symbol: str, usdt_amount: float = None):
        """現貨市價買入"""
        try:
            if usdt_amount is None:
                usdt_amount = min(self.available_balance * self.max_position_size, self.max_spot_amount)
            
            if usdt_amount > self.available_balance:
                return False, f"❌ 資金不足，需要 {usdt_amount:.2f} USDT，可用 {self.available_balance:.2f} USDT"
            
            if usdt_amount < self.min_spot_amount:
                return False, f"❌ 交易金額低於最小值 {self.min_spot_amount} USDT"
            
            # 獲取當前價格估算數量
            current_price = self._get_current_price(symbol)
            if current_price is None:
                return False, "❌ 無法獲取當前價格"
            
            estimated_quantity = usdt_amount / current_price
            
            # 市價下單
            order = self.okx_api.spot_buy_market(symbol, usdt_amount)
            
            if not order:
                return False, "❌ 下單失敗"
            
            # 實際成交價格和數量
            filled_price = order.get('average_price', current_price)
            filled_quantity = order.get('filled_quantity', estimated_quantity)
            actual_cost = filled_quantity * filled_price
            
            # 計算手續費
            fee = actual_cost * self.spot_trading_fee
            
            # 更新現貨持倉
            if symbol not in self.spot_holdings:
                self.spot_holdings[symbol] = SpotHolding(
                    symbol=symbol,
                    quantity=0,
                    avg_price=0,
                    total_cost=0
                )
            
            current_holding = self.spot_holdings[symbol]
            total_quantity = current_holding.quantity + filled_quantity
            total_cost_new = current_holding.total_cost + actual_cost
            avg_price = total_cost_new / total_quantity
            
            self.spot_holdings[symbol] = SpotHolding(
                symbol=symbol,
                quantity=total_quantity,
                avg_price=avg_price,
                total_cost=total_cost_new,
                last_buy_price=filled_price,
                last_buy_time=datetime.now().isoformat()
            )
            
            # 更新可用餘額
            self.available_balance -= (actual_cost + fee)
            
            # 記錄交易
            trade_id = f"SPOT_BUY_MKT_{symbol}_{int(time.time())}"
            self._save_trade_record(trade_id, symbol, 'SPOT_BUY_MARKET', filled_price, filled_quantity, -fee)
            
            message = f"✅ 現貨市價買入成功: {symbol} 均價={filled_price:.4f} 數量={filled_quantity:.4f} 手續費={fee:.4f} USDT"
            self.logger.info(message)
            
            return True, message
            
        except Exception as e:
            error_msg = f"❌ 現貨市價買入失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def spot_sell_market(self, symbol: str, quantity: float = None):
        """現貨市價賣出"""
        try:
            if symbol not in self.spot_holdings or self.spot_holdings[symbol].quantity <= 0:
                return False, "❌ 沒有持倉"
            
            if quantity is None:
                quantity = self.spot_holdings[symbol].quantity  # 默認賣出全部
            
            if quantity > self.spot_holdings[symbol].quantity:
                return False, f"❌ 賣出數量超過持倉，持有 {self.spot_holdings[symbol].quantity:.4f}"
            
            # 市價下單
            order = self.okx_api.spot_sell_market(symbol, quantity)
            
            if not order:
                return False, "❌ 下單失敗"
            
            # 實際成交價格
            filled_price = order.get('average_price', self._get_current_price(symbol))
            if filled_price is None:
                return False, "❌ 無法獲取成交價格"
            
            # 計算盈虧和手續費
            avg_price = self.spot_holdings[symbol].avg_price
            pnl = (filled_price - avg_price) * quantity
            fee = (quantity * filled_price) * self.spot_trading_fee
            net_pnl = pnl - fee
            
            # 更新現貨持倉
            remaining_quantity = self.spot_holdings[symbol].quantity - quantity
            remaining_cost = self.spot_holdings[symbol].total_cost * (remaining_quantity / self.spot_holdings[symbol].quantity)
            
            self.spot_holdings[symbol] = SpotHolding(
                symbol=symbol,
                quantity=remaining_quantity,
                avg_price=remaining_cost / remaining_quantity if remaining_quantity > 0 else 0,
                total_cost=remaining_cost,
                last_sell_price=filled_price,
                last_sell_time=datetime.now().isoformat()
            )
            
            # 更新可用餘額
            self.available_balance += (quantity * filled_price - fee)
            self.balance = self.available_balance
            
            # 更新每日盈虧
            self.daily_pnl += net_pnl
            
            # 記錄交易
            trade_id = f"SPOT_SELL_MKT_{symbol}_{int(time.time())}"
            self._save_trade_record(trade_id, symbol, 'SPOT_SELL_MARKET', filled_price, quantity, net_pnl)
            
            message = f"✅ 現貨市價賣出成功: {symbol} 均價={filled_price:.4f} 數量={quantity:.4f} 淨盈虧={net_pnl:+.2f} USDT"
            self.logger.info(message)
            
            if self.discord_bot.enabled:
                pnl_type = "盈利" if net_pnl >= 0 else "虧損"
                self.discord_bot.send_message(
                    f"現貨賣出: {symbol} {pnl_type} {abs(net_pnl):.2f} USDT", 
                    "success" if net_pnl >= 0 else "warning"
                )
            
            return True, message
            
        except Exception as e:
            error_msg = f"❌ 現貨市價賣出失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    # ==================== 帳戶管理方法 ====================
    
    def get_spot_balance(self):
        """獲取現貨餘額"""
        try:
            balance_info = self.okx_api.get_spot_balance()
            if balance_info:
                # 更新本地餘額
                self.balance = balance_info.get('total_balance', self.balance)
                self.available_balance = balance_info.get('available_balance', self.available_balance)
            return balance_info
        except Exception as e:
            self.logger.error(f"獲取現貨餘額錯誤: {e}")
            return {}
    
    def get_futures_balance(self):
        """獲取合約餘額"""
        try:
            balance_info = self.okx_api.get_futures_balance()
            return balance_info
        except Exception as e:
            self.logger.error(f"獲取合約餘額錯誤: {e}")
            return {}
    
    def get_total_balance(self):
        """獲取總資產餘額"""
        try:
            total_balance = self.balance
            
            # 加上現貨持倉價值
            for symbol, holding in self.spot_holdings.items():
                if holding.quantity > 0:
                    current_price = self._get_current_price(symbol)
                    if current_price:
                        total_balance += holding.quantity * current_price
            
            # 加上合約持倉盈虧
            for position in self.get_open_positions():
                total_balance += position.pnl
            
            return {
                'total_balance': total_balance,
                'spot_balance': self.balance,
                'available_balance': self.available_balance,
                'spot_holdings_value': total_balance - self.balance,
                'futures_pnl': sum(pos.pnl for pos in self.get_open_positions()),
                'daily_pnl': self.daily_pnl
            }
        except Exception as e:
            self.logger.error(f"獲取總資產餘額錯誤: {e}")
            return {}
    
    def _calculate_position_size(self, price: float) -> float:
        """計算合約倉位大小"""
        try:
            risk_amount = self.available_balance * self.risk_percent / 100
            position_size = risk_amount / price
            
            # 考慮最大倉位限制
            max_size_usdt = self.available_balance * self.max_position_size
            max_size = max_size_usdt / price
            
            # 考慮最小交易數量
            min_size = 0.001  # 假設最小交易數量
            
            final_size = min(position_size, max_size)
            final_size = max(final_size, min_size)
            
            self.logger.debug(f"計算倉位大小: 風險金額={risk_amount:.2f}, 價格={price:.2f}, 倉位={final_size:.4f}")
            
            return final_size
            
        except Exception as e:
            self.logger.error(f"計算倉位大小錯誤: {e}")
            return 0.0
    
    def _calculate_spot_position_size(self, price: float) -> float:
        """計算現貨倉位大小"""
        try:
            max_size_usdt = min(
                self.available_balance * self.max_position_size,
                self.max_spot_amount
            )
            position_size = max_size_usdt / price
            
            # 考慮最小交易金額
            min_size_usdt = self.min_spot_amount
            if position_size * price < min_size_usdt:
                position_size = min_size_usdt / price
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"計算現貨倉位大小錯誤: {e}")
            return 0.0
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """獲取當前價格"""
        try:
            # 檢查快取（減少 API 呼叫）
            cache_key = f"price_{symbol}"
            cache_time = getattr(self, '_price_cache', {}).get(f"{cache_key}_time", 0)
            current_time = time.time()
            
            if current_time - cache_time < 5:  # 5秒快取
                return getattr(self, '_price_cache', {}).get(cache_key)
            
            ticker = self.okx_api.get_ticker(symbol)
            if ticker and 'last' in ticker:
                price = float(ticker['last'])
                
                # 更新快取
                if not hasattr(self, '_price_cache'):
                    self._price_cache = {}
                self._price_cache[cache_key] = price
                self._price_cache[f"{cache_key}_time"] = current_time
                
                return price
            
            return None
        except Exception as e:
            self.logger.error(f"獲取價格錯誤 {symbol}: {e}")
            return None
    
    def _update_account_info(self):
        """更新帳戶資訊"""
        try:
            # 更新現貨餘額
            spot_balance = self.get_spot_balance()
            if spot_balance:
                self.balance = spot_balance.get('total_balance', self.balance)
                self.available_balance = spot_balance.get('available_balance', self.available_balance)
            
            # 更新合約餘額（可選）
            futures_balance = self.get_futures_balance()
            
            # 檢查是否需要重置每日盈虧（新的一天）
            self._check_daily_reset()
            
            # 更新持倉盈虧
            self._update_positions_pnl()
                
        except Exception as e:
            self.logger.error(f"更新帳戶資訊錯誤: {e}")
    
    def _check_daily_reset(self):
        """檢查是否需要重置每日統計"""
        try:
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 如果是新的一天，重置每日統計
            if not hasattr(self, '_last_reset_date') or self._last_reset_date < today_start:
                self.daily_pnl = 0
                self.today_start_balance = self.balance
                self.total_trades_today = 0
                self._last_reset_date = today_start
                self.logger.info("新的一天，重置每日統計")
                
        except Exception as e:
            self.logger.error(f"檢查每日重置錯誤: {e}")
    
    def _update_positions_pnl(self):
        """更新持倉盈虧"""
        try:
            for position_id, position in self.positions.items():
                if position.status == 'OPEN':
                    current_price = self._get_current_price(position.symbol)
                    if current_price:
                        position.pnl = self._calculate_position_pnl(position, current_price)
                        
        except Exception as e:
            self.logger.error(f"更新持倉盈虧錯誤: {e}")
    
    def _save_trade_record(self, position_id: str, symbol: str, action: str, 
                          price: float, quantity: float, pnl: float = None):
        """保存交易記錄"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                INSERT INTO trade_records 
                (position_id, symbol, action, price, quantity, timestamp, pnl, trading_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                position_id, symbol, action, price, quantity, 
                datetime.now().isoformat(), pnl,
                'SPOT' if 'SPOT' in action else 'FUTURES'
            ))
            
            self.db.conn.commit()
            
            # 記錄詳細日誌
            self.logger.debug(f"交易記錄已保存: {symbol} {action} {quantity:.4f} @ {price:.4f}")
            
        except Exception as e:
            self.logger.error(f"保存交易記錄錯誤: {e}")
    
    def _cleanup_old_data(self):
        """清理過期資料"""
        try:
            # 清理已關閉的持倉（保留最近100個）
            closed_positions = [pid for pid, pos in self.positions.items() if pos.status == 'CLOSED']
            if len(closed_positions) > 100:
                # 按關閉時間排序，移除最舊的
                closed_with_time = [(pid, self.positions[pid].closed_at) for pid in closed_positions]
                closed_with_time.sort(key=lambda x: x[1])
                
                for pid, _ in closed_with_time[:-100]:
                    del self.positions[pid]
                
                self.logger.debug(f"清理了 {len(closed_with_time) - 100} 個舊持倉記錄")
            
            # 清理價格快取
            current_time = time.time()
            if hasattr(self, '_price_cache'):
                keys_to_remove = []
                for key, cache_time in self._price_cache.items():
                    if key.endswith('_time') and current_time - cache_time > 300:  # 5分鐘
                        symbol_key = key.replace('_time', '')
                        keys_to_remove.extend([key, symbol_key])
                
                for key in set(keys_to_remove):
                    if key in self._price_cache:
                        del self._price_cache[key]
                        
        except Exception as e:
            self.logger.error(f"清理舊資料錯誤: {e}")

    # ==================== 持倉查詢方法 ====================
    
    def get_open_positions(self) -> List[TradingPosition]:
        """獲取當前持倉 (合約)"""
        return [pos for pos in self.positions.values() if pos.status == 'OPEN']
    
    def get_closed_positions(self, limit: int = 50) -> List[TradingPosition]:
        """獲取已關閉持倉"""
        closed = [pos for pos in self.positions.values() if pos.status == 'CLOSED']
        # 按關閉時間排序，最新的在前
        closed.sort(key=lambda x: x.closed_at, reverse=True)
        return closed[:limit]
    
    def get_spot_holdings(self) -> Dict[str, SpotHolding]:
        """獲取現貨持倉"""
        return {k: v for k, v in self.spot_holdings.items() if v.quantity > 0}
    
    def get_position_by_id(self, position_id: str) -> Optional[TradingPosition]:
        """根據ID獲取持倉"""
        return self.positions.get(position_id)
    
    def get_positions_by_symbol(self, symbol: str) -> List[TradingPosition]:
        """根據交易對獲取持倉"""
        return [pos for pos in self.positions.values() if pos.symbol == symbol]

    # ==================== 交易歷史查詢 ====================
    
    def get_trading_history(self, limit: int = 20, trading_type: str = None):
        """獲取交易歷史"""
        try:
            cursor = self.db.conn.cursor()
            
            query = '''
                SELECT * FROM trade_records 
                WHERE 1=1
            '''
            params = []
            
            if trading_type:
                query += ' AND trading_type = ?'
                params.append(trading_type)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return cursor.fetchall()
            
        except Exception as e:
            self.logger.error(f"獲取交易歷史錯誤: {e}")
            return []
    
    def get_today_trades(self):
        """獲取今日交易"""
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_str = today_start.isoformat()
            
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT * FROM trade_records 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            ''', (today_str,))
            
            return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"獲取今日交易錯誤: {e}")
            return []
    
    def get_profitable_trades(self, days: int = 30):
        """獲取盈利交易"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT * FROM trade_records 
                WHERE timestamp >= ? AND pnl > 0
                ORDER BY pnl DESC
            ''', (since_date,))
            
            return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"獲取盈利交易錯誤: {e}")
            return []

    # ==================== 風險管理方法 ====================
    
    def calculate_portfolio_risk(self) -> Dict:
        """計算投資組合風險"""
        try:
            total_balance = self.get_total_balance()['total_balance']
            open_positions = self.get_open_positions()
            spot_holdings = self.get_spot_holdings()
            
            # 計算總風險暴露
            futures_exposure = sum(
                pos.quantity * pos.entry_price * pos.leverage 
                for pos in open_positions
            )
            
            spot_exposure = sum(
                holding.quantity * self._get_current_price(symbol) or holding.avg_price
                for symbol, holding in spot_holdings.items()
            )
            
            total_exposure = futures_exposure + spot_exposure
            exposure_ratio = total_exposure / total_balance if total_balance > 0 else 0
            
            # 計算當前虧損
            total_unrealized_pnl = sum(pos.pnl for pos in open_positions)
            
            # 計算風險評分 (0-10, 10為最高風險)
            risk_score = 0
            if exposure_ratio > 2.0:
                risk_score += 3
            elif exposure_ratio > 1.5:
                risk_score += 2
            elif exposure_ratio > 1.0:
                risk_score += 1
                
            if total_unrealized_pnl < -total_balance * 0.05:
                risk_score += 3
            elif total_unrealized_pnl < -total_balance * 0.02:
                risk_score += 2
            elif total_unrealized_pnl < 0:
                risk_score += 1
                
            if len(open_positions) >= self.max_positions:
                risk_score += 2
                
            risk_score = min(risk_score, 10)
            
            return {
                'total_balance': total_balance,
                'total_exposure': total_exposure,
                'exposure_ratio': exposure_ratio,
                'futures_exposure': futures_exposure,
                'spot_exposure': spot_exposure,
                'unrealized_pnl': total_unrealized_pnl,
                'risk_score': risk_score,
                'risk_level': '高' if risk_score >= 7 else '中' if risk_score >= 4 else '低',
                'position_count': len(open_positions),
                'spot_holding_count': len(spot_holdings)
            }
            
        except Exception as e:
            self.logger.error(f"計算投資組合風險錯誤: {e}")
            return {}
            # ==================== 設定管理方法 ====================
    
    def load_settings(self):
        """載入交易設定"""
        try:
            # 從資料庫或設定檔載入設定
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT key, value FROM system_settings 
                WHERE category IN ('trading', 'risk_management', 'smc_trading')
            ''')
            settings_data = cursor.fetchall()
            
            # 轉換為字典
            settings_dict = {}
            for key, value in settings_data:
                settings_dict[key] = value
            
            # 更新設定
            self._update_settings_from_dict(settings_dict)
            
            # 更新智能止損設定
            if self.smart_stoploss:
                stoploss_settings = {
                    'atr_multiplier': self.atr_multiplier,
                    'max_risk_per_trade': self.risk_percent / 100,
                    'volatility_threshold': self.max_volatility
                }
                self.smart_stoploss.update_settings(stoploss_settings)
            
            # 重置每日統計
            self._reset_daily_stats()
            
            self.logger.info("交易設定載入完成")
            return True
            
        except Exception as e:
            self.logger.error(f"載入交易設定錯誤: {e}")
            # 使用預設設定
            self._load_default_settings()
            return False
    
    def _update_settings_from_dict(self, settings_dict: Dict):
        """從字典更新設定"""
        try:
            # 基礎交易設定
            self.initial_capital = float(settings_dict.get('initial_capital', self.initial_capital))
            self.risk_percent = float(settings_dict.get('risk_percent', self.risk_percent))
            self.atr_multiplier = float(settings_dict.get('atr_multiplier', self.atr_multiplier))
            self.max_positions = int(settings_dict.get('max_positions', self.max_positions))
            self.enabled = settings_dict.get('enabled', str(self.enabled)).lower() == 'true'
            self.trading_mode = settings_dict.get('trading_mode', self.trading_mode)
            self.cooldown_period = int(settings_dict.get('cooldown_period', self.cooldown_period))
            
            # SMC 交易設定
            self.smc_enabled = settings_dict.get('smc_enabled', str(self.smc_enabled)).lower() == 'true'
            self.smc_confidence_threshold = float(settings_dict.get('smc_confidence_threshold', self.smc_confidence_threshold))
            self.use_smc_signals = settings_dict.get('use_smc_signals', str(self.use_smc_signals)).lower() == 'true'
            self.smc_min_volume = float(settings_dict.get('smc_min_volume', self.smc_min_volume))
            
            # 現貨交易設定
            self.spot_enabled = settings_dict.get('spot_enabled', str(self.spot_enabled)).lower() == 'true'
            spot_pairs_str = settings_dict.get('spot_pairs', ','.join(self.spot_pairs))
            self.spot_pairs = [pair.strip() for pair in spot_pairs_str.split(',')]
            self.min_spot_amount = float(settings_dict.get('min_spot_amount', self.min_spot_amount))
            self.max_spot_amount = float(settings_dict.get('max_spot_amount', self.max_spot_amount))
            self.spot_trading_fee = float(settings_dict.get('spot_trading_fee', self.spot_trading_fee))
            
            # 合約交易設定
            self.futures_enabled = settings_dict.get('futures_enabled', str(self.futures_enabled)).lower() == 'true'
            futures_pairs_str = settings_dict.get('futures_pairs', ','.join(self.futures_pairs))
            self.futures_pairs = [pair.strip() for pair in futures_pairs_str.split(',')]
            self.default_leverage = int(settings_dict.get('default_leverage', self.default_leverage))
            self.max_leverage = int(settings_dict.get('max_leverage', self.max_leverage))
            self.futures_trading_fee = float(settings_dict.get('futures_trading_fee', self.futures_trading_fee))
            
            # 風險管理設定
            self.max_daily_loss = float(settings_dict.get('max_daily_loss', self.max_daily_loss))
            self.max_position_size = float(settings_dict.get('max_position_size', self.max_position_size))
            self.stop_loss_enabled = settings_dict.get('stop_loss_enabled', str(self.stop_loss_enabled)).lower() == 'true'
            self.take_profit_enabled = settings_dict.get('take_profit_enabled', str(self.take_profit_enabled)).lower() == 'true'
            self.max_daily_trades = int(settings_dict.get('max_daily_trades', self.max_daily_trades))
            self.volatility_filter = settings_dict.get('volatility_filter', str(self.volatility_filter)).lower() == 'true'
            self.max_volatility = float(settings_dict.get('max_volatility', self.max_volatility))
            
        except Exception as e:
            self.logger.error(f"更新設定錯誤: {e}")
    
    def _load_default_settings(self):
        """載入預設設定"""
        self.logger.info("載入預設交易設定")
        # 使用初始化時的預設值，不需要額外設定
    
    def save_settings(self):
        """保存交易設定"""
        try:
            cursor = self.db.conn.cursor()
            
            # 準備設定資料
            settings_to_save = [
                # 基礎交易設定
                ('initial_capital', str(self.initial_capital), 'trading'),
                ('risk_percent', str(self.risk_percent), 'trading'),
                ('atr_multiplier', str(self.atr_multiplier), 'trading'),
                ('max_positions', str(self.max_positions), 'trading'),
                ('enabled', str(self.enabled).lower(), 'trading'),
                ('trading_mode', self.trading_mode, 'trading'),
                ('cooldown_period', str(self.cooldown_period), 'trading'),
                
                # SMC 交易設定
                ('smc_enabled', str(self.smc_enabled).lower(), 'smc_trading'),
                ('smc_confidence_threshold', str(self.smc_confidence_threshold), 'smc_trading'),
                ('use_smc_signals', str(self.use_smc_signals).lower(), 'smc_trading'),
                ('smc_min_volume', str(self.smc_min_volume), 'smc_trading'),
                
                # 現貨交易設定
                ('spot_enabled', str(self.spot_enabled).lower(), 'trading'),
                ('spot_pairs', ','.join(self.spot_pairs), 'trading'),
                ('min_spot_amount', str(self.min_spot_amount), 'trading'),
                ('max_spot_amount', str(self.max_spot_amount), 'trading'),
                ('spot_trading_fee', str(self.spot_trading_fee), 'trading'),
                
                # 合約交易設定
                ('futures_enabled', str(self.futures_enabled).lower(), 'trading'),
                ('futures_pairs', ','.join(self.futures_pairs), 'trading'),
                ('default_leverage', str(self.default_leverage), 'trading'),
                ('max_leverage', str(self.max_leverage), 'trading'),
                ('futures_trading_fee', str(self.futures_trading_fee), 'trading'),
                
                # 風險管理設定
                ('max_daily_loss', str(self.max_daily_loss), 'risk_management'),
                ('max_position_size', str(self.max_position_size), 'risk_management'),
                ('stop_loss_enabled', str(self.stop_loss_enabled).lower(), 'risk_management'),
                ('take_profit_enabled', str(self.take_profit_enabled).lower(), 'risk_management'),
                ('max_daily_trades', str(self.max_daily_trades), 'risk_management'),
                ('volatility_filter', str(self.volatility_filter).lower(), 'risk_management'),
                ('max_volatility', str(self.max_volatility), 'risk_management'),
            ]
            
            # 保存到資料庫
            for key, value, category in settings_to_save:
                cursor.execute('''
                    INSERT OR REPLACE INTO system_settings (key, value, category)
                    VALUES (?, ?, ?)
                ''', (key, value, category))
            
            self.db.conn.commit()
            
            # 同時保存到設定檔（備份）
            self._save_settings_to_file()
            
            self.logger.info("交易設定保存成功")
            return True
            
        except Exception as e:
            self.logger.error(f"保存交易設定錯誤: {e}")
            return False
    
    def _save_settings_to_file(self):
        """保存設定到檔案（備份）"""
        try:
            settings_data = {
                'trading': {
                    'initial_capital': self.initial_capital,
                    'risk_percent': self.risk_percent,
                    'atr_multiplier': self.atr_multiplier,
                    'max_positions': self.max_positions,
                    'enabled': self.enabled,
                    'trading_mode': self.trading_mode,
                    'cooldown_period': self.cooldown_period,
                    'spot_enabled': self.spot_enabled,
                    'spot_pairs': self.spot_pairs,
                    'min_spot_amount': self.min_spot_amount,
                    'max_spot_amount': self.max_spot_amount,
                    'spot_trading_fee': self.spot_trading_fee,
                    'futures_enabled': self.futures_enabled,
                    'futures_pairs': self.futures_pairs,
                    'default_leverage': self.default_leverage,
                    'max_leverage': self.max_leverage,
                    'futures_trading_fee': self.futures_trading_fee,
                },
                'smc_trading': {
                    'enabled': self.smc_enabled,
                    'confidence_threshold': self.smc_confidence_threshold,
                    'use_signals': self.use_smc_signals,
                    'min_volume': self.smc_min_volume,
                },
                'risk_management': {
                    'max_daily_loss': self.max_daily_loss,
                    'max_position_size': self.max_position_size,
                    'stop_loss_enabled': self.stop_loss_enabled,
                    'take_profit_enabled': self.take_profit_enabled,
                    'max_daily_trades': self.max_daily_trades,
                    'volatility_filter': self.volatility_filter,
                    'max_volatility': self.max_volatility,
                }
            }
            
            import os
            os.makedirs('config', exist_ok=True)
            
            with open('config/trading_settings.json', 'w', encoding='utf-8') as f:
                import json
                json.dump(settings_data, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"保存設定到檔案錯誤: {e}")
    
    def reset_settings(self):
        """重設為預設設定"""
        try:
            # 刪除所有設定
            cursor = self.db.conn.cursor()
            cursor.execute('DELETE FROM system_settings')
            self.db.conn.commit()
            
            # 重新載入預設值
            self._load_configurations()
            
            # 保存預設設定
            self.save_settings()
            
            self.logger.info("交易設定已重設為預設值")
            return True
            
        except Exception as e:
            self.logger.error(f"重設設定錯誤: {e}")
            return False

    # ==================== 績效統計方法 ====================
    
    def get_performance_stats(self, period_days: int = 30):
        """獲取交易績效統計"""
        try:
            since_date = (datetime.now() - timedelta(days=period_days)).isoformat()
            
            cursor = self.db.conn.cursor()
            
            # 基礎統計
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    AVG(pnl) as avg_pnl,
                    SUM(pnl) as total_pnl,
                    MIN(pnl) as min_pnl,
                    MAX(pnl) as max_pnl,
                    AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                    AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss
                FROM trade_records 
                WHERE timestamp >= ? AND pnl IS NOT NULL
            ''', (since_date,))
            
            stats = cursor.fetchone()
            
            if not stats or stats['total_trades'] == 0:
                return self._get_empty_performance_stats()
            
            total_trades = stats['total_trades']
            winning_trades = stats['winning_trades']
            losing_trades = total_trades - winning_trades
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # 計算風險調整回報
            total_pnl = stats['total_pnl'] or 0
            avg_pnl = stats['avg_pnl'] or 0
            avg_win = stats['avg_win'] or 0
            avg_loss = stats['avg_loss'] or 0
            
            # 盈虧比
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
            
            # 最大連續盈利/虧損
            cursor.execute('''
                WITH pnl_series AS (
                    SELECT pnl, timestamp,
                           LAG(pnl) OVER (ORDER BY timestamp) as prev_pnl
                    FROM trade_records 
                    WHERE timestamp >= ? AND pnl IS NOT NULL
                    ORDER BY timestamp
                ),
                groups AS (
                    SELECT *,
                           SUM(CASE WHEN (pnl >= 0 AND prev_pnl < 0) OR (pnl < 0 AND prev_pnl >= 0) THEN 1 ELSE 0 END) 
                           OVER (ORDER BY timestamp) as group_id
                    FROM pnl_series
                )
                SELECT 
                    MAX(CASE WHEN pnl >= 0 THEN consecutive_count END) as max_win_streak,
                    MAX(CASE WHEN pnl < 0 THEN consecutive_count END) as max_loss_streak
                FROM (
                    SELECT group_id, pnl >= 0 as is_win, COUNT(*) as consecutive_count
                    FROM groups
                    GROUP BY group_id, is_win
                )
            ''', (since_date,))
            
            streak_stats = cursor.fetchone()
            max_win_streak = streak_stats['max_win_streak'] or 0
            max_loss_streak = streak_stats['max_loss_streak'] or 0
            
            # 夏普比率（簡化版）
            sharpe_ratio = self._calculate_sharpe_ratio(since_date)
            
            # 最大回撤
            max_drawdown = self._calculate_max_drawdown(since_date)
            
            # 每日統計
            daily_stats = self._get_daily_performance_stats(since_date)
            
            return {
                'period_days': period_days,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'avg_pnl': round(avg_pnl, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'profit_factor': round(profit_factor, 2),
                'max_win_streak': max_win_streak,
                'max_loss_streak': max_loss_streak,
                'sharpe_ratio': round(sharpe_ratio, 2),
                'max_drawdown': round(max_drawdown, 2),
                'daily_stats': daily_stats,
                'current_balance': round(self.balance, 2),
                'daily_pnl': round(self.daily_pnl, 2),
                'total_trades_today': self.total_trades_today,
                'open_positions': len(self.get_open_positions()),
                'portfolio_risk': self.calculate_portfolio_risk()
            }
            
        except Exception as e:
            self.logger.error(f"獲取績效統計錯誤: {e}")
            return self._get_empty_performance_stats()
    
    def _get_empty_performance_stats(self):
        """獲取空的績效統計"""
        return {
            'period_days': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'avg_pnl': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'max_win_streak': 0,
            'max_loss_streak': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'daily_stats': {},
            'current_balance': round(self.balance, 2),
            'daily_pnl': round(self.daily_pnl, 2),
            'total_trades_today': self.total_trades_today,
            'open_positions': len(self.get_open_positions()),
            'portfolio_risk': self.calculate_portfolio_risk()
        }
    
    def _calculate_sharpe_ratio(self, since_date: str) -> float:
        """計算夏普比率（簡化版）"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT pnl FROM trade_records 
                WHERE timestamp >= ? AND pnl IS NOT NULL
                ORDER BY timestamp
            ''', (since_date,))
            
            pnl_data = [row['pnl'] for row in cursor.fetchall()]
            
            if len(pnl_data) < 2:
                return 0.0
            
            # 計算年化夏普比率（假設每日交易）
            returns = np.array(pnl_data)
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return == 0:
                return 0.0
            
            # 年化（假設252個交易日）
            sharpe = (avg_return / std_return) * np.sqrt(252)
            return sharpe
            
        except Exception as e:
            self.logger.error(f"計算夏普比率錯誤: {e}")
            return 0.0
    
    def _calculate_max_drawdown(self, since_date: str) -> float:
        """計算最大回撤"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT timestamp, pnl FROM trade_records 
                WHERE timestamp >= ? AND pnl IS NOT NULL
                ORDER BY timestamp
            ''', (since_date,))
            
            trades = cursor.fetchall()
            if not trades:
                return 0.0
            
            # 計算累積盈虧
            cumulative_pnl = 0
            peak = 0
            max_drawdown = 0
            
            for trade in trades:
                cumulative_pnl += trade['pnl']
                if cumulative_pnl > peak:
                    peak = cumulative_pnl
                drawdown = peak - cumulative_pnl
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            return max_drawdown
            
        except Exception as e:
            self.logger.error(f"計算最大回撤錯誤: {e}")
            return 0.0
    
    def _get_daily_performance_stats(self, since_date: str) -> Dict:
        """獲取每日績效統計"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT 
                    DATE(timestamp) as trade_date,
                    COUNT(*) as trades_count,
                    SUM(pnl) as daily_pnl,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    AVG(pnl) as avg_pnl
                FROM trade_records 
                WHERE timestamp >= ? AND pnl IS NOT NULL
                GROUP BY DATE(timestamp)
                ORDER BY trade_date DESC
                LIMIT 10
            ''', (since_date,))
            
            daily_stats = {}
            for row in cursor.fetchall():
                date_str = row['trade_date']
                daily_stats[date_str] = {
                    'trades_count': row['trades_count'],
                    'daily_pnl': round(row['daily_pnl'] or 0, 2),
                    'winning_trades': row['winning_trades'],
                    'win_rate': round((row['winning_trades'] / row['trades_count']) * 100, 2),
                    'avg_pnl': round(row['avg_pnl'] or 0, 2)
                }
            
            return daily_stats
            
        except Exception as e:
            self.logger.error(f"獲取每日績效統計錯誤: {e}")
            return {}
    
    def get_symbol_performance(self, symbol: str, period_days: int = 30) -> Dict:
        """獲取特定交易對的績效"""
        try:
            since_date = (datetime.now() - timedelta(days=period_days)).isoformat()
            
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MIN(pnl) as min_pnl,
                    MAX(pnl) as max_pnl
                FROM trade_records 
                WHERE symbol = ? AND timestamp >= ? AND pnl IS NOT NULL
            ''', (symbol, since_date))
            
            stats = cursor.fetchone()
            
            if not stats or stats['total_trades'] == 0:
                return {
                    'symbol': symbol,
                    'total_trades': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                    'best_trade': 0,
                    'worst_trade': 0
                }
            
            total_trades = stats['total_trades']
            winning_trades = stats['winning_trades']
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            return {
                'symbol': symbol,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(stats['total_pnl'] or 0, 2),
                'avg_pnl': round(stats['avg_pnl'] or 0, 2),
                'best_trade': round(stats['max_pnl'] or 0, 2),
                'worst_trade': round(stats['min_pnl'] or 0, 2)
            }
            
        except Exception as e:
            self.logger.error(f"獲取交易對績效錯誤 {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def get_trading_analytics(self) -> Dict:
        """獲取交易分析數據"""
        try:
            # 最近30天交易分佈
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT 
                    strftime('%H', timestamp) as hour,
                    COUNT(*) as trades_count,
                    AVG(pnl) as avg_pnl,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades
                FROM trade_records 
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY strftime('%H', timestamp)
                ORDER BY hour
            ''')
            
            hourly_stats = {}
            for row in cursor.fetchall():
                hour = int(row['hour'])
                hourly_stats[hour] = {
                    'trades_count': row['trades_count'],
                    'avg_pnl': round(row['avg_pnl'] or 0, 2),
                    'win_rate': round((row['winning_trades'] / row['trades_count']) * 100, 2) if row['trades_count'] > 0 else 0
                }
            
            # 交易對表現排名
            cursor.execute('''
                SELECT 
                    symbol,
                    COUNT(*) as trades_count,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl
                FROM trade_records 
                WHERE timestamp >= datetime('now', '-30 days') AND pnl IS NOT NULL
                GROUP BY symbol
                ORDER BY total_pnl DESC
                LIMIT 10
            ''')
            
            symbol_ranking = []
            for row in cursor.fetchall():
                symbol_ranking.append({
                    'symbol': row['symbol'],
                    'trades_count': row['trades_count'],
                    'total_pnl': round(row['total_pnl'] or 0, 2),
                    'avg_pnl': round(row['avg_pnl'] or 0, 2)
                })
            
            # 交易類型分佈
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN action LIKE '%SPOT%' THEN '現貨'
                        WHEN action LIKE '%FUTURES%' THEN '合約'
                        ELSE '其他'
                    END as trade_type,
                    COUNT(*) as trades_count,
                    SUM(pnl) as total_pnl
                FROM trade_records 
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY trade_type
            ''')
            
            type_distribution = {}
            for row in cursor.fetchall():
                type_distribution[row['trade_type']] = {
                    'trades_count': row['trades_count'],
                    'total_pnl': round(row['total_pnl'] or 0, 2)
                }
            
            return {
                'hourly_stats': hourly_stats,
                'symbol_ranking': symbol_ranking,
                'type_distribution': type_distribution,
                'analysis_period': '最近30天'
            }
            
        except Exception as e:
            self.logger.error(f"獲取交易分析數據錯誤: {e}")
            return {}

    # ==================== 工具方法 ====================
    
    def _reset_daily_stats(self):
        """重置每日統計"""
        self.daily_pnl = 0
        self.today_start_balance = self.balance
        self.total_trades_today = 0
        self._last_reset_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    def export_trade_data(self, file_path: str = None):
        """導出交易數據"""
        try:
            if file_path is None:
                file_path = f"trade_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT * FROM trade_records 
                ORDER BY timestamp DESC
            ''')
            
            import csv
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 寫入標頭
                headers = [description[0] for description in cursor.description]
                writer.writerow(headers)
                
                # 寫入數據
                for row in cursor.fetchall():
                    writer.writerow([row[header] for header in headers])
            
            self.logger.info(f"交易數據已導出到: {file_path}")
            return True, file_path
            
        except Exception as e:
            error_msg = f"導出交易數據錯誤: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def get_system_status(self) -> Dict:
        """獲取系統狀態"""
        try:
            open_positions = self.get_open_positions()
            spot_holdings = self.get_spot_holdings()
            portfolio_risk = self.calculate_portfolio_risk()
            performance_stats = self.get_performance_stats(7)  # 最近7天
            
            status = {
                'system': {
                    'auto_trading': self.auto_trading,
                    'trading_enabled': self.enabled,
                    'trading_mode': self.trading_mode,
                    'last_update': datetime.now().isoformat(),
                    'uptime': self._get_uptime()
                },
                'account': {
                    'total_balance': round(self.balance, 2),
                    'available_balance': round(self.available_balance, 2),
                    'daily_pnl': round(self.daily_pnl, 2),
                    'today_trades': self.total_trades_today
                },
                'positions': {
                    'open_positions_count': len(open_positions),
                    'spot_holdings_count': len(spot_holdings),
                    'max_positions': self.max_positions
                },
                'risk_management': {
                    'risk_level': portfolio_risk.get('risk_level', '未知'),
                    'risk_score': portfolio_risk.get('risk_score', 0),
                    'exposure_ratio': round(portfolio_risk.get('exposure_ratio', 0), 2),
                    'daily_loss_limit': round(self.today_start_balance * self.max_daily_loss, 2)
                },
                'performance': {
                    'weekly_win_rate': performance_stats.get('win_rate', 0),
                    'weekly_pnl': performance_stats.get('total_pnl', 0),
                    'weekly_trades': performance_stats.get('total_trades', 0)
                },
                'connections': {
                    'api_connected': self.okx_api.test_connection(),
                    'database_connected': self.db.test_connection(),
                    'discord_connected': self.discord_bot.enabled if self.discord_bot else False
                }
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"獲取系統狀態錯誤: {e}")
            return {'error': str(e)}
    
    def _get_uptime(self) -> str:
        """獲取系統運行時間"""
        try:
            if not hasattr(self, '_start_time'):
                self._start_time = datetime.now()
            
            uptime = datetime.now() - self._start_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}天 {hours}時 {minutes}分"
            else:
                return f"{hours}時 {minutes}分 {seconds}秒"
                
        except Exception as e:
            self.logger.error(f"計算運行時間錯誤: {e}")
            return "未知"
    
    def validate_settings(self) -> Dict:
        """驗證交易設定"""
        issues = []
        
        # 檢查風險設定
        if self.risk_percent > 10:
            issues.append("風險百分比過高（建議不超過10%）")
        
        if self.max_position_size > 0.5:
            issues.append("單一倉位大小過高（建議不超過50%）")
        
        if self.max_daily_loss > 0.1:
            issues.append("每日虧損限制過高（建議不超過10%）")
        
        # 檢查交易對
        if not self.spot_pairs and self.spot_enabled:
            issues.append("未設定現貨交易對")
        
        if not self.futures_pairs and self.futures_enabled:
            issues.append("未設定合約交易對")
        
        # 檢查餘額
        if self.available_balance < self.min_spot_amount:
            issues.append(f"可用餘額不足最小交易金額 {self.min_spot_amount} USDT")
        
        # 檢查 API 連線
        if not self.okx_api.test_connection():
            issues.append("API 連線失敗")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'suggestions': self._get_setting_suggestions()
        }
    
    def _get_setting_suggestions(self) -> List[str]:
        """獲取設定建議"""
        suggestions = []
        
        if self.risk_percent < 1:
            suggestions.append("考慮提高風險百分比以增加收益潛力")
        
        if len(self.spot_pairs) + len(self.futures_pairs) > 10:
            suggestions.append("交易對數量較多，建議專注於少數高流動性交易對")
        
        if self.max_daily_trades > 50:
            suggestions.append("每日交易次數限制較高，可能導致過度交易")
        
        return suggestions
    
    def backup_system(self):
        """備份系統數據"""
        try:
            import shutil
            import os
            from datetime import datetime
            
            # 創建備份目錄
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"trading_system_backup_{timestamp}")
            os.makedirs(backup_path, exist_ok=True)
            
            # 備份資料庫
            if os.path.exists(self.db.db_path):
                shutil.copy2(self.db.db_path, os.path.join(backup_path, "trading.db"))
            
            # 備份設定
            self._save_settings_to_file()
            if os.path.exists('config/trading_settings.json'):
                shutil.copy2('config/trading_settings.json', backup_path)
            
            # 備份日誌（最近一個）
            log_files = [f for f in os.listdir('logs') if f.startswith('trading_system')]
            if log_files:
                latest_log = max(log_files)
                shutil.copy2(os.path.join('logs', latest_log), backup_path)
            
            # 創建備份資訊檔案
            backup_info = {
                'backup_time': datetime.now().isoformat(),
                'system_version': '1.0.0',
                'positions_count': len(self.positions),
                'spot_holdings_count': len(self.spot_holdings),
                'total_balance': self.balance,
                'performance_stats': self.get_performance_stats(7)
            }
            
            import json
            with open(os.path.join(backup_path, 'backup_info.json'), 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=4, ensure_ascii=False)
            
            self.logger.info(f"系統備份完成: {backup_path}")
            return True, backup_path
            
        except Exception as e:
            error_msg = f"系統備份失敗: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def emergency_stop(self):
        """緊急停止所有交易活動"""
        try:
            # 停止自動交易
            if self.auto_trading:
                self.stop_auto_trading()
            
            # 平掉所有持倉
            close_results = []
            open_positions = self.get_open_positions()
            
            for position in open_positions:
                success, message = self.close_position(position.position_id, "EMERGENCY_STOP")
                close_results.append({
                    'position_id': position.position_id,
                    'symbol': position.symbol,
                    'success': success,
                    'message': message
                })
            
            # 發送緊急通知
            emergency_msg = "🚨 緊急停止已執行！所有持倉已平倉，自動交易已停止。"
            self.logger.critical(emergency_msg)
            
            if self.discord_bot.enabled:
                self.discord_bot.send_message(emergency_msg, "critical")
            
            return {
                'success': True,
                'message': emergency_msg,
                'closed_positions': close_results,
                'positions_closed': len(open_positions)
            }
            
        except Exception as e:
            error_msg = f"緊急停止執行失敗: {e}"
            self.logger.critical(error_msg)
            return {
                'success': False,
                'message': error_msg,
                'closed_positions': [],
                'positions_closed': 0
            }

    def __del__(self):
        """解構函數，確保資源清理"""
        try:
            if self.auto_trading:
                self.stop_auto_trading()
                
            if hasattr(self, 'trading_thread') and self.trading_thread:
                self.trading_thread.join(timeout=5)
                
        except Exception as e:
            self.logger.error(f"資源清理錯誤: {e}")

# 交易系統 GUI 控制類別
class TradingSystemGUI:
    """交易系統圖形界面控制類別"""
    
    def __init__(self, trading_system: TradingSystem, parent_frame: tk.Frame):
        self.trading_system = trading_system
        self.parent_frame = parent_frame
        self.setup_gui()
    
    def setup_gui(self):
        """設置圖形界面"""
        # 創建主框架
        main_frame = ttk.LabelFrame(self.parent_frame, text="交易系統控制", padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 狀態顯示
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="系統狀態: 停止", foreground="red")
        self.status_label.pack(side=tk.LEFT)
        
        self.balance_label = ttk.Label(status_frame, text="餘額: 0 USDT")
        self.balance_label.pack(side=tk.RIGHT)
        
        # 控制按鈕
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.start_button = ttk.Button(button_frame, text="啟動自動交易", command=self.start_auto_trading)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="停止自動交易", command=self.stop_auto_trading, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.emergency_button = ttk.Button(button_frame, text="緊急停止", command=self.emergency_stop, style="Emergency.TButton")
        self.emergency_button.pack(side=tk.LEFT, padx=5)
        
        # 設定樣式
        style = ttk.Style()
        style.configure("Emergency.TButton", foreground="white", background="red")
        
        # 持倉顯示
        positions_frame = ttk.LabelFrame(main_frame, text="當前持倉", padding="5")
        positions_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 創建樹狀視圖顯示持倉
        columns = ("符號", "類型", "入場價", "數量", "當前盈虧", "狀態")
        self.positions_tree = ttk.Treeview(positions_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=80)
        
        self.positions_tree.pack(fill=tk.BOTH, expand=True)
        
        # 績效顯示
        stats_frame = ttk.LabelFrame(main_frame, text="績效統計", padding="5")
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.stats_text = tk.Text(stats_frame, height=6, width=80)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # 開始更新循環
        self.update_ui()
    
    def start_auto_trading(self):
        """啟動自動交易"""
        success, message = self.trading_system.start_auto_trading()
        if success:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            messagebox.showinfo("成功", message)
        else:
            messagebox.showerror("錯誤", message)
    
    def stop_auto_trading(self):
        """停止自動交易"""
        success, message = self.trading_system.stop_auto_trading()
        if success:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            messagebox.showinfo("成功", message)
        else:
            messagebox.showerror("錯誤", message)
    
    def emergency_stop(self):
        """緊急停止"""
        result = messagebox.askyesno("確認", "確定要執行緊急停止嗎？這將平掉所有持倉並停止自動交易。")
        if result:
            stop_result = self.trading_system.emergency_stop()
            if stop_result['success']:
                messagebox.showinfo("成功", stop_result['message'])
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
            else:
                messagebox.showerror("錯誤", stop_result['message'])
    
    def update_ui(self):
        """更新界面"""
        try:
            # 更新狀態
            status = "運行中" if self.trading_system.auto_trading else "停止"
            color = "green" if self.trading_system.auto_trading else "red"
            self.status_label.config(text=f"系統狀態: {status}", foreground=color)
            
            # 更新餘額
            total_balance = self.trading_system.get_total_balance()
            self.balance_label.config(text=f"總資產: {total_balance.get('total_balance', 0):.2f} USDT")
            
            # 更新持倉列表
            self.positions_tree.delete(*self.positions_tree.get_children())
            open_positions = self.trading_system.get_open_positions()
            
            for position in open_positions:
                self.positions_tree.insert("", "end", values=(
                    position.symbol,
                    position.position_type,
                    f"{position.entry_price:.4f}",
                    f"{position.quantity:.4f}",
                    f"{position.pnl:+.2f}",
                    position.status
                ))
            
            # 更新績效統計
            stats = self.trading_system.get_performance_stats(7)
            stats_text = f"最近7天績效:\n"
            stats_text += f"交易次數: {stats['total_trades']} | 勝率: {stats['win_rate']}%\n"
            stats_text += f"總盈虧: {stats['total_pnl']:+.2f} USDT | 平均盈虧: {stats['avg_pnl']:+.2f} USDT\n"
            stats_text += f"今日盈虧: {stats['daily_pnl']:+.2f} USDT | 今日交易: {stats['total_trades_today']}次\n"
            stats_text += f"夏普比率: {stats['sharpe_ratio']:.2f} | 最大回撤: {stats['max_drawdown']:.2f} USDT"
            
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, stats_text)
            
        except Exception as e:
            self.trading_system.logger.error(f"更新界面錯誤: {e}")
        
        # 每秒更新一次
        self.parent_frame.after(1000, self.update_ui)