@echo off
chcp 65001
echo ========================================
echo   幣圈交易輔助系統
echo ========================================
echo.

echo 檢查 Python 環境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python，請先安裝 Python 3.8+
    echo 下載連結: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✓ Python 環境正常
echo.

echo 安裝核心依賴庫...
echo.

echo 1. 安裝基礎套件...
pip install requests==2.31.0
pip install python-dateutil==2.8.2
pip install joblib==1.3.2

echo.
echo 2. 安裝數據分析套件...
pip install numpy==1.24.3
if %errorlevel% neq 0 (
    echo ⚠️ NumPy 安裝遇到問題，嘗試替代方案...
    pip install numpy --prefer-binary
)

pip install pandas==2.0.3
pip install matplotlib==3.7.2
pip install scikit-learn==1.3.0

echo.
echo 3. 安裝交易相關套件...
pip install ccxt==4.1.76

echo.
echo 4. 安裝可選套件...
pip install plotly==5.15.0
pip install seaborn==0.12.2

echo.
echo 創建必要目錄...
if not exist config mkdir config
if not exist data mkdir data
if not exist logs mkdir logs
if not exist models mkdir models
if not exist backtest mkdir backtest
if not exist monitor mkdir monitor
if not exist learning mkdir learning
if not exist utils mkdir utils

echo.
echo 創建設定檔...
if not exist config\config.json (
    echo 創建預設設定檔...
    (
        echo {
        echo     "project_name": "幣圈交易輔助系統",
        echo     "version": "3.0.0",
        echo     "author": "交易者",
        echo     "description": "加密貨幣交易輔助系統",
        echo     "okx": {
        echo         "api_key": "",
        echo         "secret_key": "",
        echo         "passphrase": "",
        echo         "test_net": true,
        echo         "use_virtual_account": true
        echo     },
        echo     "database": {
        echo         "path": "data/",
        echo         "auto_backup": true
        echo     },
        echo     "smc_strategy": {
        echo         "enabled_pairs": ["BTC-USDT", "ETH-USDT", "SOL-USDT"],
        echo         "timeframe": "1h"
        echo     },
        echo     "discord": {
        echo         "webhook_url": "",
        echo         "enabled": false
        echo     },
        echo     "monitor": {
        echo         "enabled": true,
        echo         "check_interval_seconds": 60
        echo     },
        echo     "learning": {
        echo         "enabled": true,
        echo         "model_path": "models/"
        echo     },
        echo     "copy_trading": {
        echo         "enabled": false,
        echo         "max_copied_traders": 3,
        echo         "auto_follow": true,
        echo         "risk_multiplier": 1.0
        echo     }
        echo }
    ) > config\config.json
    echo ✓ 已創建設定檔
) else (
    echo ✓ 設定檔已存在
)

echo.
echo 測試系統導入...
python -c "
import sys
try:
    import requests, pandas, numpy, ccxt, sklearn
    print('✓ 所有核心套件導入成功')
    
    # 測試設定檔讀取
    import json
    with open('config/config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    print('✓ 設定檔讀取成功')
    
    print('✓ 系統測試完成 - 準備就緒！')
except Exception as e:
    print(f'❌ 測試失敗: {e}')
    sys.exit(1)
"

echo.
echo ========================================
echo   安裝完成！
echo ========================================
echo.
echo 下一步：
echo 1. 編輯 config\config.json 文件
echo 2. 填入您的 OKX API 資訊
echo 3. 執行 start.py 啟動程式
echo.
echo 啟動命令：python start.py
echo.
pause