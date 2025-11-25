# monitor/account_monitor.py
import threading
import time
from datetime import datetime
import requests
import json

class AccountMonitor:
    def __init__(self, okx_api, db, discord_bot, monitor_config):
        self.okx_api = okx_api
        self.db = db
        self.discord_bot = discord_bot
        self.monitor_config = monitor_config
        
        self.monitoring = False
        self.thread = None
        
        # 監控設定
        self.check_interval = monitor_config.get('check_interval_seconds', 60)
        self.balance_alert_threshold = monitor_config.get('balance_alert_threshold', 0.1)
        self.price_alert_threshold = monitor_config.get('price_alert_threshold', 0.05)
        self.last_balance = None
        self.last_prices = {}
        
        # 用於線程安全的數據庫操作隊列
        self.db_operations = []
        self.db_lock = threading.Lock()
        
    def start_monitoring(self):
        """開始監控"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("✓ 帳戶監控已啟動")
        
        # 發送啟動通知
        if self.discord_bot.enabled:
            self.discord_bot.send_message("👁️ 帳戶監控系統已啟動", "info")
        
    def stop_monitoring(self):
        """停止監控"""
        self.monitoring = False
        if self.thread:
            self.thread.join(timeout=5)
        print("✓ 帳戶監控已停止")
        
    def _monitor_loop(self):
        """監控循環"""
        while self.monitoring:
            try:
                self.check_account_balance()
                self.check_market_conditions()
                
                # 處理數據庫操作
                self.process_db_operations()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"監控循環錯誤: {e}")
                time.sleep(self.check_interval)
    
    def check_account_balance(self):
        """檢查帳戶餘額"""
        try:
            balance = self.okx_api.get_account_balance()
            if balance:
                current_balance = balance['total_balance']
                
                # 檢查餘額變化
                if self.last_balance is not None:
                    change = (current_balance - self.last_balance) / self.last_balance
                    
                    if abs(change) > self.balance_alert_threshold:
                        message = f"帳戶餘額顯著變化: {change:.2%}，當前餘額: {current_balance:.2f} USDT"
                        self.send_alert("warning", message)
                
                self.last_balance = current_balance
                
                # 將數據庫操作加入隊列，在主線程處理
                self.add_db_operation('save_balance', balance)
                
        except Exception as e:
            print(f"檢查帳戶餘額錯誤: {e}")
    
    def check_market_conditions(self):
        """檢查市場條件"""
        try:
            # 檢查主要幣種的異常波動
            major_pairs = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT']
            
            for pair in major_pairs:
                ticker = self.okx_api.get_ticker(pair)
                if ticker:
                    # 修正：使用正確的字段名稱
                    current_price = float(ticker.get('last', 0))
                    open_price = float(ticker.get('open', current_price))  # 如果沒有open24h，使用當前價格
                    
                    change_24h = 0
                    if open_price > 0:
                        change_24h = (current_price - open_price) / open_price
                    
                    # 檢查價格變化
                    if pair in self.last_prices:
                        price_change = (current_price - self.last_prices[pair]) / self.last_prices[pair]
                        if abs(price_change) > self.price_alert_threshold:
                            message = f"{pair} 短期內大幅波動: {price_change:.2%}，當前價格: {current_price:.4f}"
                            self.send_alert("info", message)
                    
                    self.last_prices[pair] = current_price
                    
                    # 檢查24小時內的大幅變化
                    if abs(change_24h) > 0.1:  # 24小時內變化超過10%
                        message = f"{pair} 24小時內大幅變化: {change_24h:.2%}，當前價格: {current_price:.4f}"
                        self.send_alert("info", message)
                        
        except Exception as e:
            print(f"檢查市場條件錯誤: {e}")
    
    def add_db_operation(self, operation_type, data):
        """添加數據庫操作到隊列"""
        with self.db_lock:
            self.db_operations.append({
                'type': operation_type,
                'data': data,
                'timestamp': datetime.now().isoformat()
            })
    
    def process_db_operations(self):
        """處理數據庫操作隊列"""
        try:
            with self.db_lock:
                operations = self.db_operations.copy()
                self.db_operations.clear()
            
            for op in operations:
                if op['type'] == 'save_balance':
                    self._save_balance_record(op['data'])
                    
        except Exception as e:
            print(f"處理數據庫操作錯誤: {e}")
    
    def _save_balance_record(self, balance):
        """儲存餘額記錄（線程安全版本）"""
        try:
            # 在主線程中執行數據庫操作
            self.root.after(0, self._execute_save_balance, balance)
        except Exception as e:
            print(f"安排數據庫保存錯誤: {e}")
    
    def _execute_save_balance(self, balance):
        """在主線程中執行餘額保存"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                INSERT INTO account_data (timestamp, total_balance, available_balance, used_balance)
                VALUES (?, ?, ?, ?)
            ''', (
                balance.get('timestamp', datetime.now().isoformat()),
                balance.get('total_balance', 0),
                balance.get('available_balance', 0),
                balance.get('used_balance', 0)
            ))
            self.db.conn.commit()
        except Exception as e:
            print(f"保存餘額記錄錯誤: {e}")
    
    def send_alert(self, level, message):
        """發送警報"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            full_message = f"[{timestamp}] {message}"
            
            print(f"🔔 {full_message}")
            
        except Exception as e:
            print(f"發送警報錯誤: {e}")
    
    def get_account_history(self, hours=24):
        """獲取帳戶歷史"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT timestamp, total_balance, available_balance 
                FROM account_data 
                WHERE timestamp >= datetime('now', ?) 
                ORDER BY timestamp
            ''', (f'-{hours} hours',))
            
            return cursor.fetchall()
        except Exception as e:
            print(f"獲取帳戶歷史錯誤: {e}")
            return []