# learning/learning_system.py
import pandas as pd
import numpy as np
from datetime import datetime
import json
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import os

class LearningSystem:
    def __init__(self, db):
        self.db = db
        self.models = {}
        self.model_path = "data/models/"
        os.makedirs(self.model_path, exist_ok=True)
        
    def train_price_prediction_model(self, symbol, features, target, model_name="price_predictor"):
        """訓練價格預測模型"""
        try:
            # 獲取訓練數據
            training_data = self.get_training_data(symbol, features, target)
            if training_data.empty:
                return None
            
            # 準備特徵和標籤
            X = training_data[features]
            y = training_data[target]
            
            # 分割數據集
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # 訓練模型
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            
            # 評估模型
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            # 儲存模型
            model_filename = f"{self.model_path}{symbol}_{model_name}.pkl"
            joblib.dump(model, model_filename)
            
            # 儲存模型資訊
            model_info = {
                'symbol': symbol,
                'model_name': model_name,
                'features': features,
                'accuracy': accuracy,
                'training_date': datetime.now().isoformat(),
                'model_path': model_filename
            }
            
            self.save_model_info(model_info)
            
            print(f"✓ 模型訓練完成 - 準確率: {accuracy:.4f}")
            return model_info
            
        except Exception as e:
            print(f"訓練模型錯誤 {symbol}: {e}")
            return None
    
    def get_training_data(self, symbol, features, target, lookback=100):
        """獲取訓練數據"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT timestamp, open, high, low, close, volume 
                FROM market_data 
                WHERE symbol = ? 
                ORDER BY timestamp 
                LIMIT ?
            ''', (symbol, lookback))
            
            data = cursor.fetchall()
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 計算技術指標作為特徵
            feature_df = self.calculate_technical_indicators(df)
            
            # 計算目標變量 (價格方向)
            feature_df['price_tomorrow'] = df['close'].shift(-1)
            feature_df['target'] = (feature_df['price_tomorrow'] > df['close']).astype(int)
            
            # 移除NaN值
            feature_df = feature_df.dropna()
            
            return feature_df
            
        except Exception as e:
            print(f"獲取訓練數據錯誤: {e}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, df):
        """計算技術指標"""
        try:
            # 價格特徵
            df['returns'] = df['close'].pct_change()
            df['volatility'] = df['returns'].rolling(10).std()
            
            # 移動平均線
            df['ma_5'] = df['close'].rolling(5).mean()
            df['ma_10'] = df['close'].rolling(10).mean()
            df['ma_20'] = df['close'].rolling(20).mean()
            
            # RSI
            df['rsi'] = self.calculate_rsi(df['close'])
            
            # MACD
            macd, signal = self.calculate_macd(df['close'])
            df['macd'] = macd
            df['macd_signal'] = signal
            
            # 布林帶
            bb_upper, bb_lower = self.calculate_bollinger_bands(df['close'])
            df['bb_upper'] = bb_upper
            df['bb_lower'] = bb_lower
            df['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
            
            # 成交量特徵
            df['volume_ma'] = df['volume'].rolling(10).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            return df
            
        except Exception as e:
            print(f"計算技術指標錯誤: {e}")
            return df
    
    def calculate_rsi(self, prices, period=14):
        """計算RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """計算MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        return macd, macd_signal
    
    def calculate_bollinger_bands(self, prices, period=20, std=2):
        """計算布林帶"""
        sma = prices.rolling(period).mean()
        rolling_std = prices.rolling(period).std()
        upper_band = sma + (rolling_std * std)
        lower_band = sma - (rolling_std * std)
        return upper_band, lower_band
    
    def save_model_info(self, model_info):
        """儲存模型資訊"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                INSERT INTO learning_data (model_name, symbol, features, accuracy, parameters)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                model_info['model_name'],
                model_info['symbol'],
                json.dumps(model_info['features']),
                model_info['accuracy'],
                json.dumps({
                    'training_date': model_info['training_date'],
                    'model_path': model_info['model_path']
                })
            ))
            self.db.conn.commit()
        except Exception as e:
            print(f"儲存模型資訊錯誤: {e}")
    
    def predict_price_direction(self, symbol, model_name="price_predictor"):
        """預測價格方向"""
        try:
            # 載入模型
            model_filename = f"{self.model_path}{symbol}_{model_name}.pkl"
            if not os.path.exists(model_filename):
                return None
            
            model = joblib.load(model_filename)
            
            # 獲取最新數據
            latest_data = self.get_latest_features(symbol)
            if latest_data.empty:
                return None
            
            # 進行預測
            prediction = model.predict(latest_data)
            probability = model.predict_proba(latest_data)
            
            return {
                'prediction': 'up' if prediction[0] == 1 else 'down',
                'confidence': max(probability[0]),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"預測價格方向錯誤: {e}")
            return None
    
    def get_latest_features(self, symbol):
        """獲取最新特徵數據"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT timestamp, open, high, low, close, volume 
                FROM market_data 
                WHERE symbol = ? 
                ORDER BY timestamp DESC 
                LIMIT 30
            ''', (symbol,))
            
            data = cursor.fetchall()
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 計算特徵
            feature_df = self.calculate_technical_indicators(df)
            
            # 返回最新的一筆
            return feature_df.iloc[[-1]].drop(['timestamp', 'target'], axis=1, errors='ignore')
            
        except Exception as e:
            print(f"獲取最新特徵錯誤: {e}")
            return pd.DataFrame()
    
    def get_model_performance(self, symbol=None):
        """獲取模型性能"""
        try:
            cursor = self.db.conn.cursor()
            
            if symbol:
                cursor.execute('''
                    SELECT * FROM learning_data 
                    WHERE symbol = ? 
                    ORDER BY created_at DESC
                ''', (symbol,))
            else:
                cursor.execute('''
                    SELECT * FROM learning_data 
                    ORDER BY created_at DESC
                ''')
            
            results = cursor.fetchall()
            return results
            
        except Exception as e:
            print(f"獲取模型性能錯誤: {e}")
            return []