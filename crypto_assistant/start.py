# start.py - 一鍵啟動程式
import os
import sys
import subprocess

def main():
    print("🚀 啟動幣圈交易輔助系統")
    print("📍支援繁體中文")
    print("=" * 50)
    
    # 檢查必要目錄
    required_dirs = ['config', 'data', 'modules', 'logs', 'backtest', 'monitor', 'learning', 'utils']
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"✓ 創建目錄: {dir_name}")
    
    # 檢查必要文件
    required_files = [
        'main.py', 
        'modules/gui.py', 
        'modules/okx_api.py', 
        'modules/database.py', 
        'modules/trading_system.py', 
        'modules/discord_bot.py',
        'modules/copy_trading.py'  # 新增跟單系統
    ]
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ 缺少必要文件:")
        for file in missing_files:
            print(f"   - {file}")
        print("\n請確保所有文件都已下載完整。")
        input("按 Enter 鍵退出...")
        return
    
    # 檢查Python依賴
    try:
        import tkinter
        import ccxt
        import pandas
        import requests
        print("✓ 依賴庫檢查通過")
    except ImportError as e:
        print(f"❌ 缺少依賴庫: {e}")
        print("請執行: pip install ccxt pandas requests")
        input("按 Enter 鍵退出...")
        return
    
    # 啟動主程式
    try:
        print("✓ 啟動主界面...")
        from main import CryptoAssistant
        app = CryptoAssistant()
        app.run()
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        import traceback
        traceback.print_exc()
        input("按 Enter 鍵退出...")

if __name__ == "__main__":
    main()