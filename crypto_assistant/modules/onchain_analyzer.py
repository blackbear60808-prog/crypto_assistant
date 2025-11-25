# modules/onchain_analyzer.py
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional

class OnChainAnalyzer:
    """鏈上數據分析系統 - 整合鏈上數據指標"""
    
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger('OnChainAnalyzer')
        
        # API端點配置
        self.api_endpoints = {
            'glassnode': 'https://api.glassnode.com/v1',
            'messari': 'https://data.messari.io/api/v1',
            'coinmetrics': 'https://api.coinmetrics.io/v4',
            'blockchain_com': 'https://api.blockchain.info'
        }
        
        # API金鑰 (需要在設定中配置)
        self.api_keys = {}
        
        # 鏈上指標配置
        self.metrics_config = {
            'bitcoin': {
                'network': ['hash_rate', 'difficulty', 'transaction_count'],
                'market': ['mvrv', 'nupl', 'sopr'],
                'mining': ['miners_revenue', 'mining_difficulty'],
                'addresses': ['active_addresses', 'new_addresses']
            },
            'ethereum': {
                'network': ['gas_used', 'transaction_count', 'active_addresses'],
                'defi': ['total_value_locked', 'defi_dominance'],
                'staking': ['staking_ratio', 'validator_count']
            }
        }
        
        self.setup_onchain_tables()
    
    def setup_onchain_tables(self):
        """設置鏈上數據資料表"""
        try:
            cursor = self.db.conn.cursor()
            
            # 比特幣鏈上數據表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS btc_onchain_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    hash_rate REAL,
                    difficulty REAL,
                    transaction_count INTEGER,
                    active_addresses INTEGER,
                    mvrv_ratio REAL,
                    nupl_ratio REAL,
                    sopr_ratio REAL,
                    miners_revenue REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(timestamp)
                )
            ''')
            
            # 以太坊鏈上數據表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS eth_onchain_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    gas_used REAL,
                    transaction_count INTEGER,
                    active_addresses INTEGER,
                    total_value_locked REAL,
                    staking_ratio REAL,
                    validator_count INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(timestamp)
                )
            
            ''')
            
            # 交易所流量數據表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS exchange_flows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    flow_type TEXT NOT NULL,
                    amount REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 巨鯨錢包監控表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS whale_watches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    symbol TEXT NOT NULL,
                    wallet_address TEXT,
                    transaction_type TEXT,
                    amount REAL,
                    usd_value REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.db.conn.commit()
            self.logger.info("鏈上數據資料表創建完成")
            
        except Exception as e:
            self.logger.error(f"創建鏈上數據資料表錯誤: {e}")
    
    def fetch_btc_onchain_data(self, days: int = 30):
        """獲取比特幣鏈上數據"""
        try:
            # 這裡使用模擬數據，實際應用中應該調用API
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            
            simulated_data = []
            for date in dates:
                # 模擬鏈上數據
                data_point = {
                    'timestamp': date.isoformat(),
                    'hash_rate': np.random.normal(150, 20),  # EH/s
                    'difficulty': np.random.normal(25, 3),   # T
                    'transaction_count': int(np.random.normal(300000, 50000)),
                    'active_addresses': int(np.random.normal(900000, 100000)),
                    'mvrv_ratio': np.random.normal(1.5, 0.3),
                    'nupl_ratio': np.random.normal(0.2, 0.1),
                    'sopr_ratio': np.random.normal(1.02, 0.05),
                    'miners_revenue': np.random.normal(25, 5)  # 百萬美元
                }
                simulated_data.append(data_point)
            
            # 保存到數據庫
            self.save_btc_onchain_data(simulated_data)
            
            self.logger.info(f"比特幣鏈上數據獲取成功: {len(simulated_data)} 筆記錄")
            return simulated_data
            
        except Exception as e:
            self.logger.error(f"獲取比特幣鏈上數據錯誤: {e}")
            return []
    
    def fetch_eth_onchain_data(self, days: int = 30):
        """獲取以太坊鏈上數據"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            
            simulated_data = []
            for date in dates:
                data_point = {
                    'timestamp': date.isoformat(),
                    'gas_used': np.random.normal(60, 10),  # Gwei
                    'transaction_count': int(np.random.normal(1100000, 200000)),
                    'active_addresses': int(np.random.normal(450000, 50000)),
                    'total_value_locked': np.random.normal(25, 5),  # 十億美元
                    'staking_ratio': np.random.normal(0.22, 0.03),
                    'validator_count': int(np.random.normal(700000, 50000))
                }
                simulated_data.append(data_point)
            
            # 保存到數據庫
            self.save_eth_onchain_data(simulated_data)
            
            self.logger.info(f"以太坊鏈上數據獲取成功: {len(simulated_data)} 筆記錄")
            return simulated_data
            
        except Exception as e:
            self.logger.error(f"獲取以太坊鏈上數據錯誤: {e}")
            return []
    
    def save_btc_onchain_data(self, data):
        """保存比特幣鏈上數據"""
        try:
            cursor = self.db.conn.cursor()
            
            for record in data:
                cursor.execute('''
                    INSERT OR REPLACE INTO btc_onchain_data 
                    (timestamp, hash_rate, difficulty, transaction_count, 
                     active_addresses, mvrv_ratio, nupl_ratio, sopr_ratio, miners_revenue)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record['timestamp'],
                    record['hash_rate'],
                    record['difficulty'],
                    record['transaction_count'],
                    record['active_addresses'],
                    record['mvrv_ratio'],
                    record['nupl_ratio'],
                    record['sopr_ratio'],
                    record['miners_revenue']
                ))
            
            self.db.conn.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"保存比特幣鏈上數據錯誤: {e}")
            return False
    
    def save_eth_onchain_data(self, data):
        """保存以太坊鏈上數據"""
        try:
            cursor = self.db.conn.cursor()
            
            for record in data:
                cursor.execute('''
                    INSERT OR REPLACE INTO eth_onchain_data 
                    (timestamp, gas_used, transaction_count, active_addresses, 
                     total_value_locked, staking_ratio, validator_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record['timestamp'],
                    record['gas_used'],
                    record['transaction_count'],
                    record['active_addresses'],
                    record['total_value_locked'],
                    record['staking_ratio'],
                    record['validator_count']
                ))
            
            self.db.conn.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"保存以太坊鏈上數據錯誤: {e}")
            return False
    
    def analyze_network_health(self, symbol: str, days: int = 30):
        """分析網絡健康狀況"""
        try:
            if symbol.upper() == 'BTC':
                data = self.get_btc_onchain_data(days)
                analysis = self._analyze_btc_network_health(data)
            elif symbol.upper() == 'ETH':
                data = self.get_eth_onchain_data(days)
                analysis = self._analyze_eth_network_health(data)
            else:
                return None
            
            self.logger.info(f"網絡健康分析完成: {symbol}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"分析網絡健康錯誤: {e}")
            return None
    
    def _analyze_btc_network_health(self, data):
        """分析比特幣網絡健康"""
        if not data:
            return None
        
        df = pd.DataFrame(data)
        
        analysis = {
            'hash_rate_trend': self._calculate_trend(df['hash_rate']),
            'transaction_growth': self._calculate_growth(df['transaction_count']),
            'address_growth': self._calculate_growth(df['active_addresses']),
            'mvrv_signal': self._analyze_mvrv_signal(df['mvrv_ratio']),
            'miner_health': self._analyze_miner_health(df['miners_revenue']),
            'overall_score': 0
        }
        
        # 計算總體評分
        scores = []
        if analysis['hash_rate_trend'] == 'up': scores.append(1)
        if analysis['transaction_growth'] > 0: scores.append(1)
        if analysis['address_growth'] > 0: scores.append(1)
        if analysis['mvrv_signal'] == 'neutral': scores.append(1)
        if analysis['miner_health'] == 'healthy': scores.append(1)
        
        analysis['overall_score'] = sum(scores) / len(scores) * 100
        
        return analysis
    
    def _analyze_eth_network_health(self, data):
        """分析以太坊網絡健康"""
        if not data:
            return None
        
        df = pd.DataFrame(data)
        
        analysis = {
            'gas_efficiency': self._calculate_trend(df['gas_used'], inverse=True),
            'transaction_growth': self._calculate_growth(df['transaction_count']),
            'defi_health': self._analyze_defi_health(df['total_value_locked']),
            'staking_health': self._analyze_staking_health(df['staking_ratio']),
            'overall_score': 0
        }
        
        # 計算總體評分
        scores = []
        if analysis['gas_efficiency'] == 'up': scores.append(1)
        if analysis['transaction_growth'] > 0: scores.append(1)
        if analysis['defi_health'] == 'healthy': scores.append(1)
        if analysis['staking_health'] == 'healthy': scores.append(1)
        
        analysis['overall_score'] = sum(scores) / len(scores) * 100
        
        return analysis
    
    def analyze_market_sentiment(self, symbol: str):
        """分析市場情緒"""
        try:
            if symbol.upper() == 'BTC':
                data = self.get_btc_onchain_data(90)
                sentiment = self._analyze_btc_sentiment(data)
            elif symbol.upper() == 'ETH':
                data = self.get_eth_onchain_data(90)
                sentiment = self._analyze_eth_sentiment(data)
            else:
                return None
            
            return sentiment
            
        except Exception as e:
            self.logger.error(f"分析市場情緒錯誤: {e}")
            return None
    
    def _analyze_btc_sentiment(self, data):
        """分析比特幣市場情緒"""
        if not data:
            return None
        
        df = pd.DataFrame(data)
        
        # MVRV分析
        current_mvrv = df['mvrv_ratio'].iloc[-1]
        if current_mvrv > 3.5:
            mvrv_sentiment = '極度貪婪'
        elif current_mvrv > 2.5:
            mvrv_sentiment = '貪婪'
        elif current_mvrv > 1.5:
            mvrv_sentiment = '中性'
        elif current_mvrv > 1.0:
            mvrv_sentiment = '恐懼'
        else:
            mvrv_sentiment = '極度恐懼'
        
        # NUPL分析
        current_nupl = df['nupl_ratio'].iloc[-1]
        if current_nupl > 0.75:
            nupl_sentiment = '極度貪婪'
        elif current_nupl > 0.5:
            nupl_sentiment = '貪婪'
        elif current_nupl > 0.25:
            nupl_sentiment = '中性'
        elif current_nupl > 0:
            nupl_sentiment = '恐懼'
        else:
            nupl_sentiment = '極度恐懼'
        
        # SOPR分析
        current_sopr = df['sopr_ratio'].iloc[-1]
        sopr_sentiment = '盈利賣出' if current_sopr > 1 else '虧損賣出'
        
        sentiment = {
            'mvrv': {'value': current_mvrv, 'sentiment': mvrv_sentiment},
            'nupl': {'value': current_nupl, 'sentiment': nupl_sentiment},
            'sopr': {'value': current_sopr, 'sentiment': sopr_sentiment},
            'overall_sentiment': self._calculate_overall_sentiment([mvrv_sentiment, nupl_sentiment])
        }
        
        return sentiment
    
    def get_btc_onchain_data(self, days: int = 30):
        """從數據庫獲取比特幣鏈上數據"""
        try:
            cursor = self.db.conn.cursor()
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute('''
                SELECT timestamp, hash_rate, difficulty, transaction_count,
                       active_addresses, mvrv_ratio, nupl_ratio, sopr_ratio, miners_revenue
                FROM btc_onchain_data 
                WHERE timestamp >= ?
                ORDER BY timestamp
            ''', (start_date,))
            
            data = []
            for row in cursor.fetchall():
                data.append({
                    'timestamp': row[0],
                    'hash_rate': row[1],
                    'difficulty': row[2],
                    'transaction_count': row[3],
                    'active_addresses': row[4],
                    'mvrv_ratio': row[5],
                    'nupl_ratio': row[6],
                    'sopr_ratio': row[7],
                    'miners_revenue': row[8]
                })
            
            return data
            
        except Exception as e:
            self.logger.error(f"獲取比特幣鏈上數據錯誤: {e}")
            return []
    
    def get_eth_onchain_data(self, days: int = 30):
        """從數據庫獲取以太坊鏈上數據"""
        try:
            cursor = self.db.conn.cursor()
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute('''
                SELECT timestamp, gas_used, transaction_count, active_addresses,
                       total_value_locked, staking_ratio, validator_count
                FROM eth_onchain_data 
                WHERE timestamp >= ?
                ORDER BY timestamp
            ''', (start_date,))
            
            data = []
            for row in cursor.fetchall():
                data.append({
                    'timestamp': row[0],
                    'gas_used': row[1],
                    'transaction_count': row[2],
                    'active_addresses': row[3],
                    'total_value_locked': row[4],
                    'staking_ratio': row[5],
                    'validator_count': row[6]
                })
            
            return data
            
        except Exception as e:
            self.logger.error(f"獲取以太坊鏈上數據錯誤: {e}")
            return []
    
    # 輔助分析方法
    def _calculate_trend(self, series, window=7, inverse=False):
        """計算趨勢"""
        if len(series) < window:
            return 'unknown'
        
        recent = series.iloc[-window:].mean()
        previous = series.iloc[-window*2:-window].mean()
        
        if recent > previous:
            return 'up' if not inverse else 'down'
        else:
            return 'down' if not inverse else 'up'
    
    def _calculate_growth(self, series, window=7):
        """計算增長率"""
        if len(series) < window:
            return 0
        
        recent = series.iloc[-window:].mean()
        previous = series.iloc[-window*2:-window].mean()
        
        if previous == 0:
            return 0
        
        return (recent - previous) / previous * 100
    
    def _analyze_mvrv_signal(self, mvrv_series):
        """分析MVRV信號"""
        current = mvrv_series.iloc[-1]
        
        if current > 3.5:
            return 'overvalued'
        elif current < 1.0:
            return 'undervalued'
        else:
            return 'neutral'
    
    def _analyze_miner_health(self, revenue_series):
        """分析礦工健康狀況"""
        trend = self._calculate_trend(revenue_series)
        return 'healthy' if trend == 'up' else 'concerning'
    
    def _analyze_defi_health(self, tvl_series):
        """分析DeFi健康狀況"""
        growth = self._calculate_growth(tvl_series)
        return 'healthy' if growth > 0 else 'concerning'
    
    def _analyze_staking_health(self, staking_series):
        """分析質押健康狀況"""
        current = staking_series.iloc[-1]
        return 'healthy' if current > 0.15 else 'concerning'
    
    def _calculate_overall_sentiment(self, sentiments):
        """計算總體情緒"""
        sentiment_scores = {
            '極度貪婪': 5,
            '貪婪': 4, 
            '中性': 3,
            '恐懼': 2,
            '極度恐懼': 1
        }
        
        scores = [sentiment_scores.get(s, 3) for s in sentiments]
        avg_score = sum(scores) / len(scores)
        
        if avg_score >= 4:
            return '貪婪'
        elif avg_score >= 3:
            return '中性'
        else:
            return '恐懼'
    
    def generate_onchain_report(self, symbol: str, days: int = 30):
        """生成鏈上數據報告"""
        try:
            network_health = self.analyze_network_health(symbol, days)
            market_sentiment = self.analyze_market_sentiment(symbol)
            
            report = {
                'symbol': symbol,
                'period_days': days,
                'generated_at': datetime.now().isoformat(),
                'network_health': network_health,
                'market_sentiment': market_sentiment,
                'key_metrics': self.get_key_metrics(symbol, days)
            }
            
            self.logger.info(f"鏈上數據報告生成成功: {symbol}")
            return report
            
        except Exception as e:
            self.logger.error(f"生成鏈上數據報告錯誤: {e}")
            return None
    
    def get_key_metrics(self, symbol: str, days: int = 7):
        """獲取關鍵指標"""
        try:
            if symbol.upper() == 'BTC':
                data = self.get_btc_onchain_data(days)
                if not data:
                    return {}
                
                latest = data[-1]
                return {
                    'hash_rate': f"{latest['hash_rate']:.1f} EH/s",
                    'transaction_count': f"{latest['transaction_count']:,}",
                    'active_addresses': f"{latest['active_addresses']:,}",
                    'mvrv_ratio': f"{latest['mvrv_ratio']:.2f}",
                    'miner_revenue': f"${latest['miners_revenue']:.1f}M"
                }
                
            elif symbol.upper() == 'ETH':
                data = self.get_eth_onchain_data(days)
                if not data:
                    return {}
                
                latest = data[-1]
                return {
                    'gas_used': f"{latest['gas_used']:.1f} Gwei",
                    'transaction_count': f"{latest['transaction_count']:,}",
                    'active_addresses': f"{latest['active_addresses']:,}",
                    'total_value_locked': f"${latest['total_value_locked']:.1f}B",
                    'staking_ratio': f"{latest['staking_ratio']:.1%}"
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"獲取關鍵指標錯誤: {e}")
            return {}