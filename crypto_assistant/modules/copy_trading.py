# modules/copy_trading.py
import logging
import time
import threading
from datetime import datetime
from typing import Dict, List, Any
import json

class CopyTradingSystem:
    """跟單交易系統"""
    
    def __init__(self, okx_api, db, discord_bot, config):
        self.okx_api = okx_api
        self.db = db
        self.discord_bot = discord_bot
        self.config = config
        
        # 初始化 logger
        self.logger = logging.getLogger('CopyTradingSystem')
        
        # 跟單系統狀態
        self.is_running = False
        self.copy_thread = None
        
        # 交易者數據
        self.available_traders = {}
        self.copied_traders = {}
        
        # 跟單設定
        self.settings = {
            'max_copied_traders': 3,
            'risk_multiplier': 1.0,
            'auto_follow': True,
            'min_win_rate': 60,
            'min_total_trades': 50
        }
        
        # 載入設定
        if 'copy_trading' in config:
            self.settings.update(config['copy_trading'])
        
        # 初始化模擬交易者數據
        self.init_sample_traders()
        
        self.logger.info("跟單系統初始化完成")
    
    def init_sample_traders(self):
        """初始化模擬交易者數據"""
        self.available_traders = {
            'trader_001': {
                'name': '幣圈大神',
                'total_return': 245.6,
                'win_rate': 72.3,
                'total_trades': 156,
                'follower_count': 1245,
                'risk_level': '中等',
                'rating': 4.8,
                'specialty': ['BTC', 'ETH'],
                'max_drawdown': 15.2
            },
            'trader_002': {
                'name': '合約王者',
                'total_return': 189.3,
                'win_rate': 68.7,
                'total_trades': 203,
                'follower_count': 892,
                'risk_level': '高',
                'rating': 4.5,
                'specialty': ['SOL', 'ADA'],
                'max_drawdown': 22.1
            },
            'trader_003': {
                'name': '穩健投資人',
                'total_return': 156.8,
                'win_rate': 75.4,
                'total_trades': 98,
                'follower_count': 567,
                'risk_level': '低',
                'rating': 4.6,
                'specialty': ['BTC', 'DOT'],
                'max_drawdown': 8.7
            },
            'trader_004': {
                'name': '短線高手',
                'total_return': 312.4,
                'win_rate': 65.2,
                'total_trades': 345,
                'follower_count': 2103,
                'risk_level': '高',
                'rating': 4.7,
                'specialty': ['ETH', 'SOL'],
                'max_drawdown': 28.9
            }
        }
    
    def start_copy_trading(self):
        """啟動跟單系統"""
        if self.is_running:
            return False, "跟單系統已在運行中"
        
        try:
            self.is_running = True
            self.copy_thread = threading.Thread(target=self._copy_trading_loop, daemon=True)
            self.copy_thread.start()
            
            self.logger.info("跟單系統啟動成功")
            if self.discord_bot.enabled:
                self.discord_bot.send_message("🚀 跟單系統已啟動", "success")
            
            return True, "跟單系統啟動成功"
            
        except Exception as e:
            self.is_running = False
            error_msg = f"啟動跟單系統失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def stop_copy_trading(self):
        """停止跟單系統"""
        if not self.is_running:
            return False, "跟單系統未在運行"
        
        try:
            self.is_running = False
            if self.copy_thread and self.copy_thread.is_alive():
                self.copy_thread.join(timeout=5)
            
            self.logger.info("跟單系統已停止")
            if self.discord_bot.enabled:
                self.discord_bot.send_message("🛑 跟單系統已停止", "info")
            
            return True, "跟單系統已停止"
            
        except Exception as e:
            error_msg = f"停止跟單系統失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _copy_trading_loop(self):
        """跟單系統主循環"""
        self.logger.info("跟單系統主循環開始")
        
        while self.is_running:
            try:
                # 檢查已跟單交易者的新交易
                for trader_id in list(self.copied_traders.keys()):
                    self._check_trader_new_trades(trader_id)
                
                # 更新交易者數據
                self._update_trader_performance()
                
                # 自動跟單邏輯
                if self.settings['auto_follow']:
                    self._auto_follow_traders()
                
                # 每30秒檢查一次
                time.sleep(30)
                
            except Exception as e:
                self.logger.error(f"跟單循環錯誤: {str(e)}")
                time.sleep(60)  # 錯誤時等待更長時間
    
    def _check_trader_new_trades(self, trader_id):
        """檢查交易者的新交易"""
        try:
            # 這裡應該從API獲取交易者的最新交易
            # 目前使用模擬數據
            pass
            
        except Exception as e:
            self.logger.error(f"檢查交易者 {trader_id} 新交易錯誤: {str(e)}")
    
    def _update_trader_performance(self):
        """更新交易者績效數據"""
        try:
            # 模擬更新交易者數據
            for trader_id in self.available_traders:
                # 隨機微調數據
                trader = self.available_traders[trader_id]
                # 這裡可以添加實際的數據更新邏輯
                pass
                
        except Exception as e:
            self.logger.error(f"更新交易者績效錯誤: {str(e)}")
    
    def _auto_follow_traders(self):
        """自動跟單邏輯"""
        try:
            current_count = len(self.copied_traders)
            max_traders = self.settings['max_copied_traders']
            
            if current_count >= max_traders:
                return
            
            # 尋找符合條件的交易者
            available_slots = max_traders - current_count
            candidates = []
            
            for trader_id, trader_info in self.available_traders.items():
                if (trader_id not in self.copied_traders and
                    trader_info['win_rate'] >= self.settings['min_win_rate'] and
                    trader_info['total_trades'] >= self.settings['min_total_trades']):
                    candidates.append((trader_id, trader_info))
            
            # 按評分排序
            candidates.sort(key=lambda x: x[1]['rating'], reverse=True)
            
            # 跟隨前N個交易者
            for i in range(min(available_slots, len(candidates))):
                trader_id, trader_info = candidates[i]
                self.add_trader_to_copy(trader_id)
                
        except Exception as e:
            self.logger.error(f"自動跟單錯誤: {str(e)}")
    
    def add_trader_to_copy(self, trader_id):
        """添加交易者到跟單列表"""
        try:
            if trader_id not in self.available_traders:
                return False, "交易者不存在"
            
            if trader_id in self.copied_traders:
                return False, "已跟單此交易者"
            
            if len(self.copied_traders) >= self.settings['max_copied_traders']:
                return False, "已達到最大跟單交易者數量"
            
            trader_info = self.available_traders[trader_id]
            self.copied_traders[trader_id] = {
                'info': trader_info,
                'risk_multiplier': self.settings['risk_multiplier'],
                'started_at': datetime.now().isoformat(),
                'copied_trades': 0,
                'total_pnl': 0
            }
            
            self.logger.info(f"開始跟單交易者: {trader_info['name']}")
            if self.discord_bot.enabled:
                self.discord_bot.send_message(
                    f"👥 開始跟單: {trader_info['name']} "
                    f"(勝率: {trader_info['win_rate']}%, 收益: {trader_info['total_return']}%)",
                    "success"
                )
            
            return True, f"已開始跟單 {trader_info['name']}"
            
        except Exception as e:
            error_msg = f"添加跟單交易者失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def remove_trader_from_copy(self, trader_id):
        """從跟單列表中移除交易者"""
        try:
            if trader_id not in self.copied_traders:
                return False, "未跟單此交易者"
            
            trader_name = self.copied_traders[trader_id]['info']['name']
            del self.copied_traders[trader_id]
            
            self.logger.info(f"停止跟單交易者: {trader_name}")
            if self.discord_bot.enabled:
                self.discord_bot.send_message(f"❌ 停止跟單: {trader_name}", "info")
            
            return True, f"已停止跟單 {trader_name}"
            
        except Exception as e:
            error_msg = f"移除跟單交易者失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def get_copy_trading_status(self):
        """獲取跟單系統狀態"""
        return {
            'is_running': self.is_running,
            'copied_traders_count': len(self.copied_traders),
            'available_traders_count': len(self.available_traders),
            'pending_orders_count': 0,  # 可以根據實際情況調整
            'total_copied_trades': sum(t['copied_trades'] for t in self.copied_traders.values()),
            'total_pnl': sum(t['total_pnl'] for t in self.copied_traders.values())
        }
    
    def get_copy_trading_history(self, limit=10):
        """獲取跟單歷史"""
        # 模擬跟單歷史數據
        sample_history = [
            ('幣圈大神', 'BTC-USDT-SWAP', 'LONG', 43250.0, 0.01, '2024-01-15 10:30:00', 125.50),
            ('合約王者', 'ETH-USDT-SWAP', 'SHORT', 2450.0, 0.1, '2024-01-15 11:15:00', -45.20),
            ('穩健投資人', 'SOL-USDT-SWAP', 'LONG', 98.5, 1.0, '2024-01-15 09:45:00', 32.10),
            ('幣圈大神', 'BTC-USDT-SWAP', 'SHORT', 43800.0, 0.005, '2024-01-14 16:20:00', 89.30),
            ('短線高手', 'ETH-USDT-SWAP', 'LONG', 2430.0, 0.2, '2024-01-14 14:30:00', 156.80)
        ]
        
        return sample_history[:limit]
    
    def update_settings(self, new_settings):
        """更新跟單系統設定"""
        try:
            self.settings.update(new_settings)
            self.logger.info("跟單系統設定已更新")
            return True
        except Exception as e:
            self.logger.error(f"更新跟單設定失敗: {str(e)}")
            return False
    
    def get_trader_performance(self, trader_id):
        """獲取交易者績效詳情"""
        if trader_id not in self.available_traders:
            return None
        
        trader = self.available_traders[trader_id]
        is_copied = trader_id in self.copied_traders
        
        return {
            **trader,
            'is_copied': is_copied,
            'copied_since': self.copied_traders[trader_id]['started_at'] if is_copied else None,
            'copied_trades': self.copied_traders[trader_id]['copied_trades'] if is_copied else 0
        }
    
    def execute_copy_trade(self, trader_id, symbol, action, price, quantity):
        """執行跟單交易"""
        try:
            if trader_id not in self.copied_traders:
                return False, "未跟單此交易者"
            
            # 這裡應該執行實際的交易
            # 目前只是模擬
            
            trader_data = self.copied_traders[trader_id]
            trader_data['copied_trades'] += 1
            
            # 模擬盈虧計算
            simulated_pnl = quantity * price * 0.01  # 模擬1%收益
            trader_data['total_pnl'] += simulated_pnl
            
            self.logger.info(f"執行跟單交易: {trader_data['info']['name']} - {symbol} {action}")
            
            return True, f"跟單交易執行成功: {symbol} {action}"
            
        except Exception as e:
            error_msg = f"執行跟單交易失敗: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg