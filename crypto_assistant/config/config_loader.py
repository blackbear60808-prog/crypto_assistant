# config/config_loader.py
import json
import os
from datetime import datetime

class ConfigLoader:
    """設定檔載入器"""
    
    def __init__(self, config_path="config/config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        
    def load_config(self):
        """載入設定檔"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print("✓ 設定檔載入成功")
                return config
            else:
                return self.create_default_config()
                
        except Exception as e:
            print(f"❌ 載入設定檔錯誤: {e}")
            return self.create_default_config()
            
    def create_default_config(self):
        """創建預設設定檔"""
        default_config = {
            "project_name": "幣圈交易輔助系統",
            "version": "3.0.0",
            "author": "交易者",
            "description": "加密貨幣交易輔助系統",
            
            "okx": {
                "api_key": "",
                "secret_key": "",
                "passphrase": "",
                "test_net": True,
                "use_virtual_account": True,
                "rate_limit": 10
            },
            
            "database": {
                "path": "data/",
                "auto_backup": True,
                "backup_interval_hours": 24
            },
            
            "trading": {
                "enabled": False,
                "initial_capital": 1000,
                "risk_percent": 2.0,
                "max_positions": 5,
                "allowed_symbols": ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
            },
            
            "copy_trading": {
                "enabled": False,
                "max_copied_traders": 3,
                "auto_follow": True,
                "risk_multiplier": 1.0,
                "min_trader_rating": 4.0
            },
            
            "smc_strategy": {
                "enabled": True,
                "monitored_pairs": ["BTC-USDT", "ETH-USDT", "SOL-USDT"],
                "timeframe": "1h",
                "confidence_threshold": 0.7
            },
            
            "monitoring": {
                "enabled": True,
                "check_interval_seconds": 60,
                "balance_alert_threshold": 10,
                "price_alert_threshold": 5
            },
            
            "notifications": {
                "discord": {
                    "enabled": False,
                    "webhook_url": "",
                    "alert_levels": ["critical", "warning", "info"]
                },
                "sound_alerts": True
            },
            
            "risk_management": {
                "max_daily_loss": 5.0,
                "max_position_size": 20.0,
                "stop_loss_enabled": True,
                "take_profit_enabled": True
            },
            
            "ui_settings": {
                "theme": "light",
                "language": "zh-TW",
                "auto_refresh": True,
                "refresh_interval": 30
            },
            
            "advanced": {
                "backtest_period": 365,
                "model_retrain_days": 30,
                "data_retention_days": 90
            }
        }
        
        # 確保設定目錄存在
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # 保存預設設定
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
            
        print("✓ 已創建預設設定檔")
        return default_config
        
    def save_config(self, config=None):
        """保存設定檔"""
        if config:
            self.config = config
            
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            print("✓ 設定檔保存成功")
            return True
        except Exception as e:
            print(f"❌ 保存設定檔錯誤: {e}")
            return False
            
    def get(self, key, default=None):
        """獲取設定值"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    def set(self, key, value):
        """設置設定值"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
        self.save_config()
        
    def validate_config(self):
        """驗證設定檔完整性"""
        required_fields = [
            "okx.api_key",
            "okx.secret_key", 
            "okx.passphrase",
            "database.path"
        ]
        
        missing_fields = []
        for field in required_fields:
            if self.get(field) is None:
                missing_fields.append(field)
                
        return len(missing_fields) == 0, missing_fields