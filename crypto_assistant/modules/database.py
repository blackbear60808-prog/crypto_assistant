# modules/database.py
import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
import shutil
from typing import Dict, List, Optional, Any

class DatabaseManager:
    def __init__(self, db_path: str = "data/"):
        self.db_path = db_path
        self.db_file = os.path.join(db_path, "crypto_assistant.db")
        self.conn = None
        self.logger = logging.getLogger('database')
        
        # 確保目錄存在
        os.makedirs(db_path, exist_ok=True)
        
        self.connect()
        self.create_tables()
    
    def connect(self):
        """連接數據庫"""
        try:
            self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.logger.info(f"數據庫連接成功: {self.db_file}")
        except Exception as e:
            self.logger.error(f"數據庫連接失敗: {str(e)}")
            raise
    
    def create_tables(self):
        """創建數據庫表格"""
        try:
            cursor = self.conn.cursor()
            
            # 交易記錄表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    side TEXT NOT NULL,
                    amount REAL NOT NULL,
                    price REAL NOT NULL,
                    total_value REAL NOT NULL,
                    fee REAL DEFAULT 0,
                    status TEXT NOT NULL,
                    order_id TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # 帳戶餘額表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_balance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_type TEXT NOT NULL,
                    total_balance REAL NOT NULL,
                    available_balance REAL NOT NULL,
                    used_balance REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # SMC 數據表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS smc_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    value TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 價格警報表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    target_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    triggered BOOLEAN DEFAULT FALSE,
                    triggered_at TEXT,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 系統設定表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT NOT NULL,
                    description TEXT,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # 學習數據表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    feature_vector TEXT NOT NULL,
                    prediction REAL NOT NULL,
                    actual_result REAL,
                    accuracy REAL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 期望值計算表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expectancy_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    total_trades INTEGER NOT NULL,
                    winning_trades INTEGER NOT NULL,
                    losing_trades INTEGER NOT NULL,
                    win_rate REAL NOT NULL,
                    avg_win REAL NOT NULL,
                    avg_loss REAL NOT NULL,
                    expectancy REAL NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 技術指標表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS technical_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    indicator_name TEXT NOT NULL,
                    indicator_value REAL NOT NULL,
                    signal TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 智能止損記錄表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS smart_stoploss_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    position_type TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    atr_value REAL NOT NULL,
                    volatility REAL NOT NULL,
                    stop_loss_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 操作審計表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    operation_details TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 鏈上數據表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS onchain_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    change_24h REAL,
                    signal TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 跟單交易記錄表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS copy_trading_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trader_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    amount REAL NOT NULL,
                    price REAL NOT NULL,
                    copied_amount REAL NOT NULL,
                    profit_loss REAL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 新增掃描結果表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS smc_scan_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    signal_strength REAL NOT NULL,
                    trade_direction TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    reward_risk_ratio REAL,
                    entry_points TEXT,
                    stop_loss_points TEXT,
                    take_profit_points TEXT,
                    scan_timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 創建索引以提高查詢性能
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_trades_symbol_timestamp 
                ON trades(symbol, timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_smc_data_symbol 
                ON smc_data(symbol, timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_price_alerts_symbol 
                ON price_alerts(symbol, triggered)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_learning_data_symbol 
                ON learning_data(symbol, timeframe)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_technical_indicators 
                ON technical_indicators(symbol, timeframe, indicator_name)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp 
                ON audit_logs(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_scan_symbol_time 
                ON smc_scan_results(symbol, scan_timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_scan_strength 
                ON smc_scan_results(signal_strength)
            ''')
            
            self.conn.commit()
            self.logger.info("數據庫表格創建完成")
            
        except Exception as e:
            self.logger.error(f"創建數據庫表格錯誤: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """執行查詢"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor
        except Exception as e:
            self.logger.error(f"執行查詢錯誤: {e}")
            raise
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """獲取單條記錄"""
        try:
            cursor = self.execute_query(query, params)
            result = cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"獲取單條記錄錯誤: {e}")
            return None
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """獲取所有記錄"""
        try:
            cursor = self.execute_query(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            self.logger.error(f"獲取所有記錄錯誤: {e}")
            return []
    
    def insert_trade(self, trade_data: Dict) -> bool:
        """插入交易記錄"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO trades 
                (symbol, order_type, side, amount, price, total_value, fee, status, order_id, timestamp, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data['symbol'],
                trade_data['order_type'],
                trade_data['side'],
                trade_data['amount'],
                trade_data['price'],
                trade_data['total_value'],
                trade_data.get('fee', 0),
                trade_data['status'],
                trade_data.get('order_id', ''),
                trade_data['timestamp'],
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"插入交易記錄錯誤: {e}")
            return False
    
    def update_account_balance(self, balance_data: Dict) -> bool:
        """更新帳戶餘額"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO account_balance 
                (account_type, total_balance, available_balance, used_balance, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                balance_data['account_type'],
                balance_data['total_balance'],
                balance_data['available_balance'],
                balance_data['used_balance'],
                balance_data['timestamp'],
                datetime.now().isoformat()
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"更新帳戶餘額錯誤: {e}")
            return False
    
    def get_recent_trades(self, symbol: str = None, limit: int = 50) -> List[Dict]:
        """獲取最近交易記錄"""
        try:
            if symbol:
                query = '''
                    SELECT * FROM trades 
                    WHERE symbol = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                '''
                return self.fetch_all(query, (symbol, limit))
            else:
                query = '''
                    SELECT * FROM trades 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                '''
                return self.fetch_all(query, (limit,))
        except Exception as e:
            self.logger.error(f"獲取最近交易記錄錯誤: {e}")
            return []
    
    def get_account_balance_history(self, account_type: str = None, hours: int = 24) -> List[Dict]:
        """獲取帳戶餘額歷史"""
        try:
            time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            if account_type:
                query = '''
                    SELECT * FROM account_balance 
                    WHERE account_type = ? AND timestamp >= ? 
                    ORDER BY timestamp DESC
                '''
                return self.fetch_all(query, (account_type, time_threshold))
            else:
                query = '''
                    SELECT * FROM account_balance 
                    WHERE timestamp >= ? 
                    ORDER BY timestamp DESC
                '''
                return self.fetch_all(query, (time_threshold,))
        except Exception as e:
            self.logger.error(f"獲取帳戶餘額歷史錯誤: {e}")
            return []
    
    def save_smc_data(self, smc_data: Dict) -> bool:
        """保存SMC數據"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO smc_data 
                (symbol, timestamp, level, value, signal, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                smc_data['symbol'],
                smc_data['timestamp'],
                'market_structure',
                json.dumps(smc_data, ensure_ascii=False),
                smc_data['bias'],
                smc_data.get('confidence', 0.8),
                datetime.now().isoformat()
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"保存SMC數據錯誤: {e}")
            return False
    
    def get_latest_smc_data(self, symbol: str) -> Optional[Dict]:
        """獲取最新SMC數據"""
        try:
            query = '''
                SELECT value FROM smc_data 
                WHERE symbol = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            '''
            result = self.fetch_one(query, (symbol,))
            if result:
                return json.loads(result['value'])
            return None
        except Exception as e:
            self.logger.error(f"獲取最新SMC數據錯誤: {e}")
            return None
    
    def save_price_alert(self, alert_data: Dict) -> bool:
        """保存價格警報"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO price_alerts 
                (symbol, alert_type, target_price, current_price, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                alert_data['symbol'],
                alert_data['alert_type'],
                alert_data['target_price'],
                alert_data['current_price'],
                datetime.now().isoformat()
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"保存價格警報錯誤: {e}")
            return False
    
    def get_active_price_alerts(self) -> List[Dict]:
        """獲取活躍的價格警報"""
        try:
            query = '''
                SELECT * FROM price_alerts 
                WHERE triggered = FALSE 
                ORDER BY created_at DESC
            '''
            return self.fetch_all(query)
        except Exception as e:
            self.logger.error(f"獲取活躍價格警報錯誤: {e}")
            return []
    
    def save_system_setting(self, key: str, value: str, description: str = None) -> bool:
        """保存系統設定"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO system_settings 
                (setting_key, setting_value, description, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (
                key,
                value,
                description,
                datetime.now().isoformat()
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"保存系統設定錯誤: {e}")
            return False
    
    def get_system_setting(self, key: str) -> Optional[str]:
        """獲取系統設定"""
        try:
            query = '''
                SELECT setting_value FROM system_settings 
                WHERE setting_key = ?
            '''
            result = self.fetch_one(query, (key,))
            return result['setting_value'] if result else None
        except Exception as e:
            self.logger.error(f"獲取系統設定錯誤: {e}")
            return None
    
    def backup_database(self, backup_path: str = None) -> bool:
        """備份數據庫"""
        try:
            if backup_path is None:
                backup_path = os.path.join(self.db_path, "backups")
            
            os.makedirs(backup_path, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_path, f"crypto_assistant_backup_{timestamp}.db")
            
            # 使用SQLite的備份API
            def progress(status, remaining, total):
                print(f'備份進度: {total-remaining}/{total} pages...')
            
            backup_conn = sqlite3.connect(backup_file)
            self.conn.backup(backup_conn, pages=1, progress=progress)
            backup_conn.close()
            
            self.logger.info(f"數據庫備份完成: {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"數據庫備份錯誤: {e}")
            return False
    
    def cleanup_old_data(self, days: int = 30) -> bool:
        """清理舊數據"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            cursor = self.conn.cursor()
            
            # 清理交易記錄
            cursor.execute('DELETE FROM trades WHERE timestamp < ?', (cutoff_date,))
            
            # 清理帳戶餘額記錄
            cursor.execute('DELETE FROM account_balance WHERE timestamp < ?', (cutoff_date,))
            
            # 清理SMC數據
            cursor.execute('DELETE FROM smc_data WHERE timestamp < ?', (cutoff_date,))
            
            # 清理技術指標數據
            cursor.execute('DELETE FROM technical_indicators WHERE timestamp < ?', (cutoff_date,))
            
            self.conn.commit()
            
            self.logger.info(f"已清理 {days} 天前的舊數據")
            return True
            
        except Exception as e:
            self.logger.error(f"清理舊數據錯誤: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """獲取數據庫統計信息"""
        try:
            stats = {}
            
            # 各表格記錄數量
            tables = ['trades', 'account_balance', 'smc_data', 'price_alerts', 
                     'learning_data', 'technical_indicators', 'audit_logs', 'smc_scan_results']
            
            for table in tables:
                result = self.fetch_one(f'SELECT COUNT(*) as count FROM {table}')
                stats[f'{table}_count'] = result['count'] if result else 0
            
            # 數據庫檔案大小
            if os.path.exists(self.db_file):
                stats['database_size_mb'] = round(os.path.getsize(self.db_file) / (1024 * 1024), 2)
            else:
                stats['database_size_mb'] = 0
            
            # 最後更新時間
            result = self.fetch_one('SELECT MAX(created_at) as last_update FROM trades')
            stats['last_update'] = result['last_update'] if result else 'N/A'
            
            return stats
            
        except Exception as e:
            self.logger.error(f"獲取數據庫統計信息錯誤: {e}")
            return {}
    
    def close(self):
        """關閉數據庫連接"""
        try:
            if self.conn:
                self.conn.close()
                self.logger.info("數據庫連接已關閉")
        except Exception as e:
            self.logger.error(f"關閉數據庫連接錯誤: {e}")