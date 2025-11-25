# main.py
import sys
import os

# 添加模組路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'modules'))

import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading
import time
from datetime import datetime

# 導入所有模組
from modules.gui import MainGUI
from modules.okx_api import OKXAPI
from modules.database import DatabaseManager
from modules.smc_strategy import SMCStrategy
from modules.discord_bot import DiscordBot
from modules.trading_system import TradingSystem
from modules.smc_learning import SMCLearningSystem
from modules.expectancy_calculator import ExpectancyCalculator
from modules.technical_indicators import TechnicalIndicators
from modules.smart_stoploss import SmartStopLoss
from modules.audit_system import AuditSystem
from modules.onchain_analyzer import OnChainAnalyzer
from modules.copy_trading import CopyTradingSystem
from modules.smc_scanner import SMCScanner  # 新增導入

class CryptoAssistant:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("幣圈交易輔助系統")
        self.root.geometry("1400x900")
        
        # 設置關閉事件處理
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        
        # 載入設定
        self.config = self.load_config()
        
        # 初始化元件
        self.init_components()
        
    def load_config(self):
        """載入設定檔"""
        try:
            with open('config/config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                print("✓ 設定檔載入成功")
                return config
        except FileNotFoundError:
            # 創建預設設定
            default_config = {
                "project_name": "幣圈交易輔助系統",
                "version": "3.0.0",
                "author": "交易者",
                "description": "加密貨幣交易輔助系統",
                "region": "tw",
                "language": "zh-TW",
                
                "smc_scanner": {
                    "enabled": True,
                    "scan_interval_minutes": 30,
                    "max_concurrent_scans": 5,
                    "timeframes": ["1h", "4h", "1d"],
                    "min_confidence": 0.7,
                    "volume_threshold": 1000000,
                    "volatility_threshold": 0.02,
                    "notify_on_signals": True,
                    "auto_scan_on_startup": True,
                    "risk_levels": {
                        "high": 0.9,
                        "medium": 0.7,
                        "low": 0.5
                    }
                },
                
                "okx": {
                    "api_key": "",
                    "secret_key": "", 
                    "passphrase": "",
                    "test_net": True,
                    "use_virtual_account": True
                },
                
                "database": {
                    "path": "data/",
                    "auto_backup": True
                },
                
                "smc_strategy": {
                    "enabled_pairs": ["BTC-USDT", "ETH-USDT", "SOL-USDT"],
                    "timeframe": "1h"
                },
                
                "discord": {
                    "webhook_url": "",
                    "enabled": False
                },
                
                "monitor": {
                    "enabled": True,
                    "check_interval_seconds": 60
                },
                
                "learning": {
                    "enabled": True,
                    "model_path": "data/models/"
                },
                
                "trading": {
                    "initial_capital": 1000,
                    "risk_percent": 2.0,
                    "atr_multiplier": 2.0,
                    "max_positions": 5,
                    "enabled": False
                },
                
                "smart_stoploss": {
                    "atr_period": 14,
                    "atr_multiplier": 2.0,
                    "volatility_threshold": 0.02,
                    "trailing_enabled": True,
                    "break_even_enabled": True,
                    "max_risk_per_trade": 0.02
                },
                
                "onchain": {
                    "enabled": True,
                    "update_interval": 3600
                },
                
                "copy_trading": {
                    "enabled": False,
                    "max_copied_traders": 3,
                    "auto_follow": True,
                    "risk_multiplier": 1.0
                }
            }
            os.makedirs('config', exist_ok=True)
            with open('config/config.json', 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            print("✓ 已創建預設設定檔")
            return default_config
        except Exception as e:
            print(f"❌ 載入設定檔錯誤: {e}")
            messagebox.showerror("設定錯誤", f"無法載入設定檔: {str(e)}")
            sys.exit(1)

    def init_components(self):
        """初始化所有元件"""
        try:
            print("正在初始化系統元件...")
            
            # 顯示啟動畫面
            self.show_splash_screen()
            
            # 初始化數據庫
            self.db = DatabaseManager(self.config['database']['path'])
            print("✓ 數據庫初始化完成")
            
            # 初始化OKX API
            self.okx_api = OKXAPI(
                self.config['okx']['api_key'],
                self.config['okx']['secret_key'], 
                self.config['okx']['passphrase'],
                self.config['okx']['test_net'],
                self.config['okx']['use_virtual_account']
            )
            print("✓ OKX API 初始化完成")
            
            # 初始化Discord機器人
            self.discord_bot = DiscordBot(self.config['discord']['webhook_url'])
            if self.discord_bot.enabled:
                print("✓ Discord 機器人初始化完成")
            else:
                print("✓ Discord 機器人未啟用")
            
            # 初始化SMC策略系統
            self.smc_strategy = SMCStrategy(self.db, self.okx_api)
            print("✓ SMC策略系統初始化完成")
            
            # 初始化SMC掃描器
            self.smc_scanner = SMCScanner(
                self.okx_api, 
                self.smc_strategy, 
                self.db, 
                self.config
            )
            print("✓ SMC掃描器初始化完成")
            
            # 初始化SMC學習系統
            self.smc_learning = SMCLearningSystem(self.db)
            print("✓ SMC學習系統初始化完成")
            
            # 初始化期望值計算器
            self.expectancy_calculator = ExpectancyCalculator(self.db)
            print("✓ 期望值計算器初始化完成")
            
            # 初始化技術指標系統
            self.technical_indicators = TechnicalIndicators()
            print("✓ 技術指標系統初始化完成")
            
            # 初始化智能止損系統
            self.smart_stoploss = SmartStopLoss(self.db, self.technical_indicators)
            print("✓ 智能止損系統初始化完成")
            
            # 初始化交易系統
            self.trading_system = TradingSystem(
                self.okx_api,
                self.db,
                self.discord_bot,
                self.config
            )
            print("✓ 交易系統初始化完成")
            
            # 初始化跟單系統
            self.copy_trading = CopyTradingSystem(
                self.okx_api,
                self.db,
                self.discord_bot,
                self.config
            )
            print("✓ 跟單系統初始化完成")
            
            # 初始化操作審計系統
            self.audit_system = AuditSystem(self.db)
            print("✓ 操作審計系統初始化完成")
            
            # 初始化鏈上數據分析系統
            self.onchain_analyzer = OnChainAnalyzer(self.db)
            print("✓ 鏈上數據分析系統初始化完成")
            
            # 啟動自動掃描（如果啟用）
            if (self.config.get('smc_scanner', {}).get('enabled', False) and 
                self.config.get('smc_scanner', {}).get('auto_scan_on_startup', False)):
                self.smc_scanner.start_auto_scan()
                print("✓ 自動掃描已啟動")
            
            # 關閉啟動畫面
            self.hide_splash_screen()
            
            # 初始化GUI
            self.gui = MainGUI(
                self.root, 
                self.okx_api,
                self.db,
                self.trading_system,
                self.discord_bot,
                self.smc_strategy,
                self.smc_learning,
                self.expectancy_calculator,
                self.technical_indicators,
                self.smart_stoploss,
                self.audit_system,
                self.onchain_analyzer,
                self.copy_trading,
                self.smc_scanner  # 新增參數
            )
            print("✓ GUI 初始化完成")
            
            # 載入交易設定
            self.trading_system.load_settings()
            
            # 發送系統啟動通知
            if self.config['discord'].get('enabled', False) and self.config['discord']['webhook_url']:
                self.discord_bot.send_message("🚀 幣圈交易輔助系統已啟動", "success")
            
            # 記錄系統啟動審計
            self.audit_system.log_operation(
                "SYSTEM_STARTUP",
                "系統啟動完成",
                user_id="system",
                status="SUCCESS"
            )
            
            print("✓ 系統初始化完成")
            
        except Exception as e:
            error_msg = f"系統初始化失敗: {str(e)}"
            print(f"❌ {error_msg}")
            
            # 記錄系統啟動失敗審計
            try:
                self.audit_system.log_operation(
                    "SYSTEM_STARTUP",
                    "系統啟動失敗",
                    user_id="system",
                    status="FAILED",
                    error_message=str(e)
                )
            except:
                pass
            
            messagebox.showerror("初始化錯誤", error_msg)
            sys.exit(1)

    def show_splash_screen(self):
        """顯示啟動畫面"""
        self.splash = tk.Toplevel(self.root)
        self.splash.title("幣圈交易輔助系統")
        self.splash.geometry("400x300")
        self.splash.transient(self.root)
        self.splash.grab_set()
        
        # 居中顯示
        self.splash.update_idletasks()
        x = (self.splash.winfo_screenwidth() - 400) // 2
        y = (self.splash.winfo_screenheight() - 300) // 2
        self.splash.geometry(f"+{x}+{y}")
        
        # 內容
        ttk.Label(self.splash, text="幣圈交易輔助系統", 
                 font=('Microsoft JhengHei', 20, 'bold')).pack(pady=20)
        
        ttk.Label(self.splash, text="v3.0", 
                 font=('Microsoft JhengHei', 14)).pack(pady=10)
        
        ttk.Label(self.splash, text="正在初始化系統...", 
                 font=('Microsoft JhengHei', 10)).pack(pady=20)
        
        self.progress = ttk.Progressbar(self.splash, mode='indeterminate')
        self.progress.pack(fill='x', padx=50, pady=20)
        self.progress.start()
        
        ttk.Label(self.splash, text="請稍候...", 
                 font=('Microsoft JhengHei', 9)).pack(pady=10)
        
        self.splash.update()

    def hide_splash_screen(self):
        """隱藏啟動畫面"""
        if hasattr(self, 'splash'):
            self.splash.destroy()

    def run(self):
        """運行主程式"""
        try:
            print("🚀 啟動幣圈交易輔助系統")
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\n正在關閉系統...")
            self.shutdown()
        except Exception as e:
            error_msg = f"程式執行錯誤: {str(e)}"
            print(f"❌ {error_msg}")
            messagebox.showerror("系統錯誤", error_msg)
            self.shutdown()

    def shutdown(self):
        """關閉程式"""
        try:
            print("正在安全關閉系統...")
            
            # 停止掃描器
            if hasattr(self, 'smc_scanner'):
                self.smc_scanner.stop_auto_scan()
            
            # 記錄系統關閉審計
            try:
                self.audit_system.log_operation(
                    "SYSTEM_SHUTDOWN",
                    "系統正常關閉",
                    user_id="system",
                    status="SUCCESS"
                )
            except:
                pass
            
            # 停止交易系統
            if hasattr(self, 'trading_system'):
                self.trading_system.stop_auto_trading()
            
            # 停止跟單系統
            if hasattr(self, 'copy_trading'):
                self.copy_trading.stop_copy_trading()
            
            # 關閉數據庫
            if hasattr(self, 'db'):
                self.db.close()
            
            # 發送關閉通知
            if hasattr(self, 'discord_bot') and self.discord_bot.enabled:
                self.discord_bot.send_message("🛑 幣圈交易輔助系統已關閉", "info")
            
            # 關閉視窗
            self.root.quit()
            self.root.destroy()
            
            print("✓ 系統安全關閉")
        except Exception as e:
            print(f"關閉錯誤: {e}")

if __name__ == "__main__":
    app = CryptoAssistant()
    app.run()