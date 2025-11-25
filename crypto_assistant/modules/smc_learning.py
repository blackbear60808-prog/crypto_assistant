# modules/smc_learning.py
import sqlite3
import json
import requests
from datetime import datetime
from urllib.parse import urlparse
import re

class SMCLearningSystem:
    def __init__(self, db):
        self.db = db
        self.setup_smc_tables()
    
    def setup_smc_tables(self):
        """設置SMC學習資料表"""
        try:
            cursor = self.db.conn.cursor()
            
            # SMC知識庫表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS smc_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_type TEXT,  -- website, manual, strategy
                    source_url TEXT,
                    category TEXT,     -- basic, advanced, strategy, example
                    confidence_score REAL DEFAULT 0.5,
                    tags TEXT,         -- JSON array of tags
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # SMC策略規則表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS smc_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT NOT NULL,
                    condition TEXT NOT NULL,  -- JSON condition
                    action TEXT NOT NULL,     -- JSON action
                    description TEXT,
                    success_rate REAL,
                    usage_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # SMC學習記錄表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS smc_learning_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    timestamp DATETIME,
                    market_condition TEXT,
                    decision TEXT,
                    outcome TEXT,
                    learning_notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.db.conn.commit()
            print("✓ SMC學習資料表創建完成")
            
        except Exception as e:
            print(f"❌ 創建SMC學習資料表錯誤: {e}")
    
    def add_knowledge(self, title, content, source_type="manual", source_url="", category="basic", tags=None):
        """添加SMC知識"""
        try:
            cursor = self.db.conn.cursor()
            tags_json = json.dumps(tags or [])
            
            cursor.execute('''
                INSERT INTO smc_knowledge 
                (title, content, source_type, source_url, category, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, content, source_type, source_url, category, tags_json))
            
            self.db.conn.commit()
            print(f"✓ 已添加SMC知識: {title}")
            return True
            
        except Exception as e:
            print(f"❌ 添加SMC知識錯誤: {e}")
            return False
    
    def import_from_website(self, url, title=None):
        """從網站導入SMC資料"""
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # 簡單的內容提取（實際應用中可能需要更複雜的解析）
                content = self.extract_content(response.text)
                
                if not title:
                    title = self.extract_title(response.text) or f"SMC資料從 {url}"
                
                return self.add_knowledge(
                    title=title,
                    content=content,
                    source_type="website",
                    source_url=url,
                    category="learning",
                    tags=["web_import", "smc"]
                )
            else:
                print(f"❌ 無法訪問網站: {url}")
                return False
                
        except Exception as e:
            print(f"❌ 從網站導入SMC資料錯誤: {e}")
            return False
    
    def extract_content(self, html_content):
        """從HTML提取主要內容"""
        # 簡單的內容提取邏輯
        # 移除HTML標籤
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', html_content)
        
        # 移除多餘空白
        text = ' '.join(text.split())
        
        # 取前1000個字符
        return text[:1000] + "..." if len(text) > 1000 else text
    
    def extract_title(self, html_content):
        """從HTML提取標題"""
        title_match = re.search('<title>(.*?)</title>', html_content, re.IGNORECASE)
        if title_match:
            return title_match.group(1)
        return None
    
    def search_knowledge(self, query, category=None, limit=10):
        """搜索SMC知識"""
        try:
            cursor = self.db.conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT * FROM smc_knowledge 
                    WHERE (title LIKE ? OR content LIKE ? OR tags LIKE ?) 
                    AND category = ?
                    ORDER BY updated_at DESC 
                    LIMIT ?
                ''', (f'%{query}%', f'%{query}%', f'%{query}%', category, limit))
            else:
                cursor.execute('''
                    SELECT * FROM smc_knowledge 
                    WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?
                    ORDER BY updated_at DESC 
                    LIMIT ?
                ''', (f'%{query}%', f'%{query}%', f'%{query}%', limit))
            
            return cursor.fetchall()
            
        except Exception as e:
            print(f"❌ 搜索SMC知識錯誤: {e}")
            return []
    
    def add_trading_rule(self, rule_name, condition, action, description="", success_rate=0.5):
        """添加交易規則"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                INSERT INTO smc_rules 
                (rule_name, condition, action, description, success_rate)
                VALUES (?, ?, ?, ?, ?)
            ''', (rule_name, json.dumps(condition), json.dumps(action), description, success_rate))
            
            self.db.conn.commit()
            print(f"✓ 已添加交易規則: {rule_name}")
            return True
            
        except Exception as e:
            print(f"❌ 添加交易規則錯誤: {e}")
            return False
    
    def log_learning_experience(self, symbol, market_condition, decision, outcome, notes=""):
        """記錄學習經驗"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                INSERT INTO smc_learning_logs 
                (symbol, timestamp, market_condition, decision, outcome, learning_notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol, datetime.now().isoformat(), market_condition, decision, outcome, notes))
            
            self.db.conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ 記錄學習經驗錯誤: {e}")
            return False
    
    def get_recommended_rules(self, market_condition, symbol=None, limit=5):
        """根據市場條件獲取推薦規則"""
        try:
            cursor = self.db.conn.cursor()
            
            # 簡單的推薦邏輯 - 根據歷史成功率
            if symbol:
                cursor.execute('''
                    SELECT r.* 
                    FROM smc_rules r
                    LEFT JOIN smc_learning_logs l ON r.rule_name = l.decision
                    WHERE l.symbol = ? OR l.symbol IS NULL
                    AND r.is_active = TRUE
                    GROUP BY r.id
                    ORDER BY r.success_rate DESC, r.usage_count DESC
                    LIMIT ?
                ''', (symbol, limit))
            else:
                cursor.execute('''
                    SELECT * FROM smc_rules 
                    WHERE is_active = TRUE
                    ORDER BY success_rate DESC, usage_count DESC
                    LIMIT ?
                ''', (limit,))
            
            return cursor.fetchall()
            
        except Exception as e:
            print(f"❌ 獲取推薦規則錯誤: {e}")
            return []