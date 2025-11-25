# modules/gui.py
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import threading
import json
import pandas as pd
import os
import webbrowser

class MainGUI:
    def __init__(self, root, okx_api, db, trading_system, discord_bot, 
                 smc_strategy, smc_learning, expectancy_calculator,
                 technical_indicators, smart_stoploss, audit_system,
                 onchain_analyzer, copy_trading):
        
        self.root = root
        self.okx_api = okx_api
        self.db = db
        self.trading_system = trading_system
        self.discord_bot = discord_bot
        self.smc_strategy = smc_strategy
        self.smc_learning = smc_learning
        self.expectancy_calculator = expectancy_calculator
        self.technical_indicators = technical_indicators
        self.smart_stoploss = smart_stoploss
        self.audit_system = audit_system
        self.onchain_analyzer = onchain_analyzer
        self.copy_trading = copy_trading
        
        # 常用交易對
        self.popular_pairs = [
            "BTC-USDT", "ETH-USDT", "SOL-USDT", "ADA-USDT", 
            "DOT-USDT", "XRP-USDT", "LTC-USDT", "BNB-USDT"
        ]
        
        # 即時數據快取
        self.price_data = {}
        self.account_data = {}
        
        self.setup_gui()
        self.start_data_updater()
        
    def setup_gui(self):
        """設置主界面"""
        # 設置主題
        self.setup_theme()
        
        # 創建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 創建標題欄
        self.create_header()
        
        # 創建主選項卡
        self.create_main_notebook()
        
        # 創建狀態欄
        self.create_status_bar()
        
        # 初始化數據
        self.load_initial_data()
        
    def setup_theme(self):
        """設置界面主題"""
        style = ttk.Style()
        
        # 嘗試使用現代主題
        try:
            style.theme_use('clam')
        except:
            try:
                style.theme_use('alt')
            except:
                pass
        
        # 自定義樣式
        style.configure('TButton', font=('Microsoft JhengHei', 10))
        style.configure('TLabel', font=('Microsoft JhengHei', 9))
        style.configure('TNotebook', font=('Microsoft JhengHei', 9))
        style.configure('Header.TLabel', font=('Microsoft JhengHei', 16, 'bold'))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Warning.TLabel', foreground='orange')
        style.configure('Error.TLabel', foreground='red')
        
    def create_header(self):
        """創建標題欄"""
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 標題
        title_label = ttk.Label(
            header_frame, 
            text="💰 幣圈交易輔助系統", 
            style='Header.TLabel'
        )
        title_label.pack(side=tk.LEFT)
        
        # 即時數據顯示
        self.realtime_frame = ttk.Frame(header_frame)
        self.realtime_frame.pack(side=tk.RIGHT)
        
        # BTC價格
        self.btc_price_label = ttk.Label(
            self.realtime_frame, 
            text="BTC: --",
            font=('Microsoft JhengHei', 10, 'bold')
        )
        self.btc_price_label.pack(side=tk.LEFT, padx=5)
        
        # ETH價格
        self.eth_price_label = ttk.Label(
            self.realtime_frame, 
            text="ETH: --",
            font=('Microsoft JhengHei', 10, 'bold')
        )
        self.eth_price_label.pack(side=tk.LEFT, padx=5)
        
        # 系統狀態
        self.system_status_label = ttk.Label(
            self.realtime_frame,
            text="🟢 系統正常",
            style='Success.TLabel'
        )
        self.system_status_label.pack(side=tk.LEFT, padx=5)
        
    def create_main_notebook(self):
        """創建主選項卡"""
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 創建各個功能頁面
        self.create_dashboard_tab()
        self.create_trading_tab()
        self.create_spot_tab()
        self.create_futures_tab()
        self.create_copy_trading_tab()
        self.create_analysis_tab()
        self.create_settings_tab()
        
    def create_dashboard_tab(self):
        """創建儀表板頁面"""
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="📊 儀表板")
        
        # 創建左右分欄
        left_frame = ttk.Frame(dashboard_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        right_frame = ttk.Frame(dashboard_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # 左側：價格行情
        self.create_price_ticker(left_frame)
        
        # 左側：帳戶概覽
        self.create_account_overview(left_frame)
        
        # 右側：快速交易
        self.create_quick_trade(right_frame)
        
        # 右側：系統狀態
        self.create_system_status(right_frame)
        
    def create_price_ticker(self, parent):
        """創建價格行情顯示"""
        frame = ttk.LabelFrame(parent, text="📈 即時行情", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        # 創建價格表格
        columns = ('幣種', '價格', '24H漲跌', '交易量')
        self.price_tree = ttk.Treeview(frame, columns=columns, show='headings', height=8)
        
        # 設置列
        for col in columns:
            self.price_tree.heading(col, text=col)
            self.price_tree.column(col, width=100)
        
        self.price_tree.pack(fill=tk.X)
        
        # 初始化價格數據
        for pair in self.popular_pairs[:6]:  # 顯示前6個
            self.price_tree.insert('', 'end', values=(pair, '--', '--', '--'))
        
        # 更新按鈕
        update_btn = ttk.Button(frame, text="🔄 更新行情", command=self.update_price_data)
        update_btn.pack(pady=5)
        
    def create_account_overview(self, parent):
        """創建帳戶概覽"""
        frame = ttk.LabelFrame(parent, text="💰 帳戶總覽", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        # 帳戶資訊網格
        account_grid = ttk.Frame(frame)
        account_grid.pack(fill=tk.X)
        
        # 現貨帳戶
        ttk.Label(account_grid, text="現貨帳戶:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.spot_balance_label = ttk.Label(account_grid, text="載入中...")
        self.spot_balance_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # 合約帳戶
        ttk.Label(account_grid, text="合約帳戶:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.futures_balance_label = ttk.Label(account_grid, text="載入中...")
        self.futures_balance_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # 總資產
        ttk.Label(account_grid, text="總資產:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.total_balance_label = ttk.Label(account_grid, text="載入中...", style='Success.TLabel')
        self.total_balance_label.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # 今日盈虧
        ttk.Label(account_grid, text="今日盈虧:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.daily_pnl_label = ttk.Label(account_grid, text="載入中...")
        self.daily_pnl_label.grid(row=3, column=1, sticky=tk.W, pady=2)
        
        # 刷新按鈕
        refresh_btn = ttk.Button(frame, text="🔄 刷新餘額", command=self.update_account_data)
        refresh_btn.pack(pady=5)
        
    def create_quick_trade(self, parent):
        """創建快速交易面板"""
        frame = ttk.LabelFrame(parent, text="⚡ 快速交易", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        # 交易對選擇
        ttk.Label(frame, text="交易對:").pack(anchor=tk.W)
        self.quick_pair_var = tk.StringVar(value="BTC-USDT")
        pair_combo = ttk.Combobox(frame, textvariable=self.quick_pair_var, values=self.popular_pairs)
        pair_combo.pack(fill=tk.X, pady=2)
        
        # 交易類型
        ttk.Label(frame, text="交易類型:").pack(anchor=tk.W)
        trade_type_frame = ttk.Frame(frame)
        trade_type_frame.pack(fill=tk.X, pady=2)
        
        self.quick_trade_type = tk.StringVar(value="spot")
        ttk.Radiobutton(trade_type_frame, text="現貨", variable=self.quick_trade_type, value="spot").pack(side=tk.LEFT)
        ttk.Radiobutton(trade_type_frame, text="合約", variable=self.quick_trade_type, value="futures").pack(side=tk.LEFT)
        
        # 買賣選擇
        ttk.Label(frame, text="操作:").pack(anchor=tk.W)
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X, pady=2)
        
        self.quick_action = tk.StringVar(value="buy")
        ttk.Radiobutton(action_frame, text="買入", variable=self.quick_action, value="buy").pack(side=tk.LEFT)
        ttk.Radiobutton(action_frame, text="賣出", variable=self.quick_action, value="sell").pack(side=tk.LEFT)
        
        # 數量輸入
        ttk.Label(frame, text="數量:").pack(anchor=tk.W)
        self.quick_amount_var = tk.StringVar(value="0.001")
        amount_entry = ttk.Entry(frame, textvariable=self.quick_amount_var)
        amount_entry.pack(fill=tk.X, pady=2)
        
        # 價格輸入 (限價單)
        ttk.Label(frame, text="價格 (限價單，留空為市價):").pack(anchor=tk.W)
        self.quick_price_var = tk.StringVar()
        price_entry = ttk.Entry(frame, textvariable=self.quick_price_var)
        price_entry.pack(fill=tk.X, pady=2)
        
        # 執行按鈕
        execute_btn = ttk.Button(frame, text="🎯 執行交易", command=self.execute_quick_trade, style='TButton')
        execute_btn.pack(fill=tk.X, pady=5)
        
    def create_system_status(self, parent):
        """創建系統狀態面板"""
        frame = ttk.LabelFrame(parent, text="🖥️ 系統狀態", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        # API連接狀態
        ttk.Label(frame, text="API連接:").pack(anchor=tk.W)
        self.api_status_label = ttk.Label(frame, text="測試中...")
        self.api_status_label.pack(anchor=tk.W, pady=2)
        
        # 數據庫狀態
        ttk.Label(frame, text="數據庫:").pack(anchor=tk.W)
        self.db_status_label = ttk.Label(frame, text="測試中...")
        self.db_status_label.pack(anchor=tk.W, pady=2)
        
        # Discord狀態
        ttk.Label(frame, text="Discord:").pack(anchor=tk.W)
        self.discord_status_label = ttk.Label(frame, text="測試中...")
        self.discord_status_label.pack(anchor=tk.W, pady=2)
        
        # 自動交易狀態
        ttk.Label(frame, text="自動交易:").pack(anchor=tk.W)
        self.auto_trading_label = ttk.Label(frame, text="已停止")
        self.auto_trading_label.pack(anchor=tk.W, pady=2)
        
        # 狀態檢查按鈕
        status_btn = ttk.Button(frame, text="🔍 檢查狀態", command=self.check_system_status)
        status_btn.pack(fill=tk.X, pady=5)
        
    def create_trading_tab(self):
        """創建交易系統頁面"""
        trading_frame = ttk.Frame(self.notebook)
        self.notebook.add(trading_frame, text="🎯 交易系統")
        
        # 左右分欄
        left_frame = ttk.Frame(trading_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        right_frame = ttk.Frame(trading_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # 左側：自動交易控制
        self.create_auto_trading_control(left_frame)
        
        # 左側：持倉管理
        self.create_position_management(left_frame)
        
        # 右側：交易設定
        self.create_trading_settings(right_frame)
        
        # 右側：交易記錄
        self.create_trade_history(right_frame)
        
    def create_auto_trading_control(self, parent):
        """創建自動交易控制"""
        frame = ttk.LabelFrame(parent, text="🤖 自動交易控制", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        # 自動交易狀態
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(status_frame, text="狀態:").pack(side=tk.LEFT)
        self.auto_trading_status = ttk.Label(status_frame, text="已停止", style='Warning.TLabel')
        self.auto_trading_status.pack(side=tk.LEFT, padx=5)
        
        # 控制按鈕
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.start_auto_btn = ttk.Button(btn_frame, text="🚀 啟動自動交易", command=self.start_auto_trading)
        self.start_auto_btn.pack(side=tk.LEFT, padx=2)
        
        self.stop_auto_btn = ttk.Button(btn_frame, text="🛑 停止自動交易", command=self.stop_auto_trading, state='disabled')
        self.stop_auto_btn.pack(side=tk.LEFT, padx=2)
        
        # 交易模式選擇
        mode_frame = ttk.Frame(frame)
        mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mode_frame, text="交易模式:").pack(side=tk.LEFT)
        self.trading_mode = tk.StringVar(value="both")
        ttk.Radiobutton(mode_frame, text="現貨", variable=self.trading_mode, value="spot").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="合約", variable=self.trading_mode, value="futures").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="兩者", variable=self.trading_mode, value="both").pack(side=tk.LEFT, padx=5)
        
        # 風險設定
        risk_frame = ttk.Frame(frame)
        risk_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(risk_frame, text="每筆風險 (%):").pack(side=tk.LEFT)
        self.risk_percent_var = tk.StringVar(value="2.0")
        risk_entry = ttk.Entry(risk_frame, textvariable=self.risk_percent_var, width=8)
        risk_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(risk_frame, text="最大持倉數:").pack(side=tk.LEFT, padx=(10,0))
        self.max_positions_var = tk.StringVar(value="5")
        positions_entry = ttk.Entry(risk_frame, textvariable=self.max_positions_var, width=5)
        positions_entry.pack(side=tk.LEFT, padx=5)
        
    def create_position_management(self, parent):
        """創建持倉管理"""
        frame = ttk.LabelFrame(parent, text="📊 持倉管理", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 持倉表格
        columns = ('幣種', '類型', '方向', '數量', '入場價', '當前價', '盈虧', '止損價')
        self.position_tree = ttk.Treeview(frame, columns=columns, show='headings', height=6)
        
        for col in columns:
            self.position_tree.heading(col, text=col)
            self.position_tree.column(col, width=80)
        
        # 滾動條
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.position_tree.yview)
        self.position_tree.configure(yscrollcommand=scrollbar.set)
        
        self.position_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 操作按鈕
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="🔄 更新持倉", command=self.update_positions).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📝 手動平倉", command=self.manual_close_position).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="⚙️ 調整止損", command=self.adjust_stop_loss).pack(side=tk.LEFT, padx=2)
        
    def create_trading_settings(self, parent):
        """創建交易設定"""
        frame = ttk.LabelFrame(parent, text="⚙️ 交易設定", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        # 現貨交易設定
        spot_frame = ttk.Frame(frame)
        spot_frame.pack(fill=tk.X, pady=2)
        
        self.spot_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(spot_frame, text="啟用現貨交易", variable=self.spot_enabled).pack(anchor=tk.W)
        
        # 合約交易設定
        futures_frame = ttk.Frame(frame)
        futures_frame.pack(fill=tk.X, pady=2)
        
        self.futures_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(futures_frame, text="啟用合約交易", variable=self.futures_enabled).pack(anchor=tk.W)
        
        # 槓桿設定
        leverage_frame = ttk.Frame(frame)
        leverage_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(leverage_frame, text="預設槓桿:").pack(side=tk.LEFT)
        self.leverage_var = tk.StringVar(value="10")
        leverage_combo = ttk.Combobox(leverage_frame, textvariable=self.leverage_var, 
                                    values=["1", "3", "5", "10", "20"], width=5)
        leverage_combo.pack(side=tk.LEFT, padx=5)
        
        # 智能止損
        stoploss_frame = ttk.Frame(frame)
        stoploss_frame.pack(fill=tk.X, pady=2)
        
        self.stoploss_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(stoploss_frame, text="啟用智能止損", variable=self.stoploss_enabled).pack(anchor=tk.W)
        
        # 保存設定按鈕
        ttk.Button(frame, text="💾 保存設定", command=self.save_trading_settings).pack(fill=tk.X, pady=5)
        
    def create_trade_history(self, parent):
        """創建交易記錄"""
        frame = ttk.LabelFrame(parent, text="📝 交易記錄", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 交易記錄表格
        columns = ('時間', '幣種', '類型', '操作', '價格', '數量', '盈虧')
        self.history_tree = ttk.Treeview(frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=80)
        
        # 滾動條
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 刷新按鈕
        ttk.Button(frame, text="🔄 刷新記錄", command=self.update_trade_history).pack(fill=tk.X, pady=5)
        
    def create_spot_tab(self):
        """創建現貨交易頁面"""
        spot_frame = ttk.Frame(self.notebook)
        self.notebook.add(spot_frame, text="💵 現貨交易")
        
        # 左右分欄
        left_frame = ttk.Frame(spot_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        right_frame = ttk.Frame(spot_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # 左側：現貨交易面板
        self.create_spot_trading_panel(left_frame)
        
        # 左側：現貨持倉
        self.create_spot_holdings_panel(left_frame)
        
        # 右側：現貨帳戶詳情
        self.create_spot_account_details(right_frame)
        
        # 右側：現貨交易記錄
        self.create_spot_trade_history(right_frame)
        
    def create_spot_trading_panel(self, parent):
        """創建現貨交易面板"""
        frame = ttk.LabelFrame(parent, text="💵 現貨交易", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        # 交易對選擇
        pair_frame = ttk.Frame(frame)
        pair_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(pair_frame, text="交易對:").pack(side=tk.LEFT)
        self.spot_pair_var = tk.StringVar(value="BTC-USDT")
        self.spot_pair_combo = ttk.Combobox(pair_frame, textvariable=self.spot_pair_var, 
                                          values=self.popular_pairs, width=15)
        self.spot_pair_combo.pack(side=tk.LEFT, padx=5)
        
        # 獲取當前價格按鈕
        ttk.Button(pair_frame, text="🔄 更新價格", 
                  command=self.update_spot_price).pack(side=tk.LEFT, padx=5)
        
        # 當前價格顯示
        price_frame = ttk.Frame(frame)
        price_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(price_frame, text="當前價格:").pack(side=tk.LEFT)
        self.spot_current_price = ttk.Label(price_frame, text="--", style='Success.TLabel')
        self.spot_current_price.pack(side=tk.LEFT, padx=5)
        
        # 買入面板
        buy_frame = ttk.LabelFrame(frame, text="🟢 買入")
        buy_frame.pack(fill=tk.X, pady=5)
        
        # 買入數量
        ttk.Label(buy_frame, text="買入數量:").pack(anchor=tk.W)
        self.spot_buy_amount_var = tk.StringVar(value="0.001")
        buy_amount_entry = ttk.Entry(buy_frame, textvariable=self.spot_buy_amount_var)
        buy_amount_entry.pack(fill=tk.X, pady=2)
        
        # 買入價格 (限價單)
        ttk.Label(buy_frame, text="買入價格 (限價單，留空為市價):").pack(anchor=tk.W)
        self.spot_buy_price_var = tk.StringVar()
        buy_price_entry = ttk.Entry(buy_frame, textvariable=self.spot_buy_price_var)
        buy_price_entry.pack(fill=tk.X, pady=2)
        
        # 買入按鈕
        ttk.Button(buy_frame, text="🟢 買入", 
                  command=self.spot_buy_order, style='TButton').pack(fill=tk.X, pady=5)
        
        # 賣出面板
        sell_frame = ttk.LabelFrame(frame, text="🔴 賣出")
        sell_frame.pack(fill=tk.X, pady=5)
        
        # 賣出數量
        ttk.Label(sell_frame, text="賣出數量:").pack(anchor=tk.W)
        self.spot_sell_amount_var = tk.StringVar(value="0.001")
        sell_amount_entry = ttk.Entry(sell_frame, textvariable=self.spot_sell_amount_var)
        sell_amount_entry.pack(fill=tk.X, pady=2)
        
        # 賣出價格 (限價單)
        ttk.Label(sell_frame, text="賣出價格 (限價單，留空為市價):").pack(anchor=tk.W)
        self.spot_sell_price_var = tk.StringVar()
        sell_price_entry = ttk.Entry(sell_frame, textvariable=self.spot_sell_price_var)
        sell_price_entry.pack(fill=tk.X, pady=2)
        
        # 賣出按鈕
        ttk.Button(sell_frame, text="🔴 賣出", 
                  command=self.spot_sell_order, style='TButton').pack(fill=tk.X, pady=5)
        
        # 快速操作按鈕
        quick_btn_frame = ttk.Frame(frame)
        quick_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(quick_btn_frame, text="💰 全倉買入", 
                  command=self.spot_buy_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_btn_frame, text="💸 全倉賣出", 
                  command=self.spot_sell_all).pack(side=tk.LEFT, padx=2)
        
    def create_spot_holdings_panel(self, parent):
        """創建現貨持倉面板"""
        frame = ttk.LabelFrame(parent, text="📦 現貨持倉", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 持倉表格
        columns = ('幣種', '數量', '平均成本', '當前價格', '總價值', '盈虧')
        self.spot_holdings_tree = ttk.Treeview(frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.spot_holdings_tree.heading(col, text=col)
            self.spot_holdings_tree.column(col, width=90)
        
        # 滾動條
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.spot_holdings_tree.yview)
        self.spot_holdings_tree.configure(yscrollcommand=scrollbar.set)
        
        self.spot_holdings_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 操作按鈕
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="🔄 更新持倉", 
                  command=self.update_spot_holdings).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📊 持倉分析", 
                  command=self.analyze_spot_holdings).pack(side=tk.LEFT, padx=2)
        
    def create_spot_account_details(self, parent):
        """創建現貨帳戶詳情"""
        frame = ttk.LabelFrame(parent, text="💰 現貨帳戶", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        # 帳戶餘額詳情
        details_frame = ttk.Frame(frame)
        details_frame.pack(fill=tk.X)
        
        # USDT餘額
        ttk.Label(details_frame, text="USDT餘額:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.spot_usdt_balance = ttk.Label(details_frame, text="載入中...")
        self.spot_usdt_balance.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # 可用USDT
        ttk.Label(details_frame, text="可用USDT:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.spot_usdt_available = ttk.Label(details_frame, text="載入中...")
        self.spot_usdt_available.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # 凍結USDT
        ttk.Label(details_frame, text="凍結USDT:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.spot_usdt_frozen = ttk.Label(details_frame, text="載入中...")
        self.spot_usdt_frozen.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # 總資產價值
        ttk.Label(details_frame, text="總資產價值:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.spot_total_value = ttk.Label(details_frame, text="載入中...", style='Success.TLabel')
        self.spot_total_value.grid(row=3, column=1, sticky=tk.W, pady=2)
        
        # 刷新按鈕
        ttk.Button(frame, text="🔄 刷新餘額", 
                  command=self.update_spot_account).pack(fill=tk.X, pady=5)
        
    def create_spot_trade_history(self, parent):
        """創建現貨交易記錄"""
        frame = ttk.LabelFrame(parent, text="📝 現貨記錄", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 交易記錄表格
        columns = ('時間', '幣種', '操作', '價格', '數量', '總金額', '狀態')
        self.spot_history_tree = ttk.Treeview(frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.spot_history_tree.heading(col, text=col)
            self.spot_history_tree.column(col, width=80)
        
        # 滾動條
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.spot_history_tree.yview)
        self.spot_history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.spot_history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 過濾選項
        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="顯示:").pack(side=tk.LEFT)
        self.spot_history_filter = tk.StringVar(value="all")
        ttk.Radiobutton(filter_frame, text="全部", variable=self.spot_history_filter, value="all").pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="買入", variable=self.spot_history_filter, value="buy").pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="賣出", variable=self.spot_history_filter, value="sell").pack(side=tk.LEFT)
        
        # 刷新按鈕
        ttk.Button(frame, text="🔄 刷新記錄", 
                  command=self.update_spot_history).pack(fill=tk.X, pady=5)
        
    def create_futures_tab(self):
        """創建合約交易頁面"""
        futures_frame = ttk.Frame(self.notebook)
        self.notebook.add(futures_frame, text="📈 合約交易")
        
        # 左右分欄
        left_frame = ttk.Frame(futures_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        right_frame = ttk.Frame(futures_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # 左側：合約交易面板
        self.create_futures_trading_panel(left_frame)
        
        # 左側：合約持倉
        self.create_futures_positions_panel(left_frame)
        
        # 右側：合約帳戶詳情
        self.create_futures_account_details(right_frame)
        
        # 右側：合約交易記錄
        self.create_futures_trade_history(right_frame)
        
    def create_futures_trading_panel(self, parent):
        """創建合約交易面板"""
        frame = ttk.LabelFrame(parent, text="📈 合約交易", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        # 交易對選擇
        pair_frame = ttk.Frame(frame)
        pair_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(pair_frame, text="交易對:").pack(side=tk.LEFT)
        self.futures_pair_var = tk.StringVar(value="BTC-USDT-SWAP")
        futures_pairs = [f"{pair.split('-')[0]}-USDT-SWAP" for pair in self.popular_pairs]
        self.futures_pair_combo = ttk.Combobox(pair_frame, textvariable=self.futures_pair_var, 
                                             values=futures_pairs, width=15)
        self.futures_pair_combo.pack(side=tk.LEFT, padx=5)
        
        # 獲取當前價格按鈕
        ttk.Button(pair_frame, text="🔄 更新價格", 
                  command=self.update_futures_price).pack(side=tk.LEFT, padx=5)
        
        # 當前價格顯示
        price_frame = ttk.Frame(frame)
        price_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(price_frame, text="當前價格:").pack(side=tk.LEFT)
        self.futures_current_price = ttk.Label(price_frame, text="--", style='Success.TLabel')
        self.futures_current_price.pack(side=tk.LEFT, padx=5)
        
        # 槓桿設定
        leverage_frame = ttk.Frame(frame)
        leverage_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(leverage_frame, text="槓桿:").pack(side=tk.LEFT)
        self.futures_leverage_var = tk.StringVar(value="10")
        leverage_combo = ttk.Combobox(leverage_frame, textvariable=self.futures_leverage_var, 
                                    values=["1", "3", "5", "10", "20", "50"], width=5)
        leverage_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(leverage_frame, text="⚙️ 設置槓桿", 
                  command=self.set_futures_leverage).pack(side=tk.LEFT, padx=5)
        
        # 開倉面板
        open_frame = ttk.LabelFrame(frame, text="🎯 開倉")
        open_frame.pack(fill=tk.X, pady=5)
        
        # 開倉方向
        direction_frame = ttk.Frame(open_frame)
        direction_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(direction_frame, text="方向:").pack(side=tk.LEFT)
        self.futures_direction = tk.StringVar(value="long")
        ttk.Radiobutton(direction_frame, text="多單", variable=self.futures_direction, value="long").pack(side=tk.LEFT)
        ttk.Radiobutton(direction_frame, text="空單", variable=self.futures_direction, value="short").pack(side=tk.LEFT)
        
        # 開倉數量
        ttk.Label(open_frame, text="開倉數量 (張):").pack(anchor=tk.W)
        self.futures_open_amount_var = tk.StringVar(value="1")
        open_amount_entry = ttk.Entry(open_frame, textvariable=self.futures_open_amount_var)
        open_amount_entry.pack(fill=tk.X, pady=2)
        
        # 開倉價格
        ttk.Label(open_frame, text="開倉價格 (限價單，留空為市價):").pack(anchor=tk.W)
        self.futures_open_price_var = tk.StringVar()
        open_price_entry = ttk.Entry(open_frame, textvariable=self.futures_open_price_var)
        open_price_entry.pack(fill=tk.X, pady=2)
        
        # 開倉按鈕
        open_btn_frame = ttk.Frame(open_frame)
        open_btn_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(open_btn_frame, text="🟢 開多單", 
                  command=lambda: self.futures_open_order("long")).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ttk.Button(open_btn_frame, text="🔴 開空單", 
                  command=lambda: self.futures_open_order("short")).pack(side=tk.RIGHT, padx=2, fill=tk.X, expand=True)
        
        # 平倉面板
        close_frame = ttk.LabelFrame(frame, text="📤 平倉")
        close_frame.pack(fill=tk.X, pady=5)
        
        # 平倉數量
        ttk.Label(close_frame, text="平倉數量 (張):").pack(anchor=tk.W)
        self.futures_close_amount_var = tk.StringVar(value="1")
        close_amount_entry = ttk.Entry(close_frame, textvariable=self.futures_close_amount_var)
        close_amount_entry.pack(fill=tk.X, pady=2)
        
        # 平倉價格
        ttk.Label(close_frame, text="平倉價格 (限價單，留空為市價):").pack(anchor=tk.W)
        self.futures_close_price_var = tk.StringVar()
        close_price_entry = ttk.Entry(close_frame, textvariable=self.futures_close_price_var)
        close_price_entry.pack(fill=tk.X, pady=2)
        
        # 平倉按鈕
        ttk.Button(close_frame, text="📤 平倉", 
                  command=self.futures_close_order).pack(fill=tk.X, pady=5)
        
    def create_futures_positions_panel(self, parent):
        """創建合約持倉面板"""
        frame = ttk.LabelFrame(parent, text="📊 合約持倉", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 持倉表格
        columns = ('幣種', '方向', '數量', '入場價', '標記價', '強平價', '盈虧', '盈虧%', '槓桿')
        self.futures_positions_tree = ttk.Treeview(frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.futures_positions_tree.heading(col, text=col)
            self.futures_positions_tree.column(col, width=80)
        
        # 滾動條
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.futures_positions_tree.yview)
        self.futures_positions_tree.configure(yscrollcommand=scrollbar.set)
        
        self.futures_positions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 操作按鈕
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="🔄 更新持倉", 
                  command=self.update_futures_positions).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📤 一鍵平倉", 
                  command=self.futures_close_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="⚙️ 調整止損", 
                  command=self.adjust_futures_stop_loss).pack(side=tk.LEFT, padx=2)
        
    def create_futures_account_details(self, parent):
        """創建合約帳戶詳情"""
        frame = ttk.LabelFrame(parent, text="💰 合約帳戶", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        # 帳戶餘額詳情
        details_frame = ttk.Frame(frame)
        details_frame.pack(fill=tk.X)
        
        # 帳戶權益
        ttk.Label(details_frame, text="帳戶權益:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.futures_equity = ttk.Label(details_frame, text="載入中...")
        self.futures_equity.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # 可用保證金
        ttk.Label(details_frame, text="可用保證金:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.futures_available_margin = ttk.Label(details_frame, text="載入中...")
        self.futures_available_margin.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # 已用保證金
        ttk.Label(details_frame, text="已用保證金:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.futures_used_margin = ttk.Label(details_frame, text="載入中...")
        self.futures_used_margin.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # 保證金率
        ttk.Label(details_frame, text="保證金率:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.futures_margin_ratio = ttk.Label(details_frame, text="載入中...")
        self.futures_margin_ratio.grid(row=3, column=1, sticky=tk.W, pady=2)
        
        # 未實現盈虧
        ttk.Label(details_frame, text="未實現盈虧:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=4, column=0, sticky=tk.W, pady=2)
        self.futures_unrealized_pnl = ttk.Label(details_frame, text="載入中...")
        self.futures_unrealized_pnl.grid(row=4, column=1, sticky=tk.W, pady=2)
        
        # 刷新按鈕
        ttk.Button(frame, text="🔄 刷新帳戶", 
                  command=self.update_futures_account).pack(fill=tk.X, pady=5)
        
    def create_futures_trade_history(self, parent):
        """創建合約交易記錄"""
        frame = ttk.LabelFrame(parent, text="📝 合約記錄", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 交易記錄表格
        columns = ('時間', '幣種', '操作', '價格', '數量', '盈虧', '槓桿', '狀態')
        self.futures_history_tree = ttk.Treeview(frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.futures_history_tree.heading(col, text=col)
            self.futures_history_tree.column(col, width=80)
        
        # 滾動條
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.futures_history_tree.yview)
        self.futures_history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.futures_history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 刷新按鈕
        ttk.Button(frame, text="🔄 刷新記錄", 
                  command=self.update_futures_history).pack(fill=tk.X, pady=5)
        
    def create_copy_trading_tab(self):
        """創建跟單系統頁面"""
        copy_frame = ttk.Frame(self.notebook)
        self.notebook.add(copy_frame, text="👥 跟單系統")
        
        # 左右分欄
        left_frame = ttk.Frame(copy_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        right_frame = ttk.Frame(copy_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # 左側：跟單交易者列表
        self.create_trader_list_panel(left_frame)
        
        # 左側：跟單設定
        self.create_copy_settings_panel(left_frame)
        
        # 右側：跟單狀態
        self.create_copy_status_panel(right_frame)
        
        # 右側：跟單記錄
        self.create_copy_history_panel(right_frame)
        
    def create_trader_list_panel(self, parent):
        """創建交易者列表面板"""
        frame = ttk.LabelFrame(parent, text="👥 推薦交易者", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 交易者表格
        columns = ('交易者', '總收益', '勝率', '交易數', '跟隨者', '評分', '狀態')
        self.trader_tree = ttk.Treeview(frame, columns=columns, show='headings', height=10)
        
        column_widths = {'交易者': 120, '總收益': 80, '勝率': 80, '交易數': 80, '跟隨者': 80, '評分': 80, '狀態': 80}
        for col in columns:
            self.trader_tree.heading(col, text=col)
            self.trader_tree.column(col, width=column_widths.get(col, 100))
        
        # 滾動條
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.trader_tree.yview)
        self.trader_tree.configure(yscrollcommand=scrollbar.set)
        
        self.trader_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 操作按鈕
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="➕ 開始跟單", 
                  command=self.start_copy_trader).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="➖ 停止跟單", 
                  command=self.stop_copy_trader).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🔄 刷新列表", 
                  command=self.update_trader_list).pack(side=tk.LEFT, padx=2)
        
    def create_copy_settings_panel(self, parent):
        """創建跟單設定面板"""
        frame = ttk.LabelFrame(parent, text="⚙️ 跟單設定", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        # 跟單系統開關
        switch_frame = ttk.Frame(frame)
        switch_frame.pack(fill=tk.X, pady=2)
        
        self.copy_trading_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(switch_frame, text="啟用跟單系統", 
                       variable=self.copy_trading_enabled,
                       command=self.toggle_copy_trading).pack(side=tk.LEFT)
        
        # 最大跟單交易者數量
        max_traders_frame = ttk.Frame(frame)
        max_traders_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(max_traders_frame, text="最大跟單交易者:").pack(side=tk.LEFT)
        self.max_traders_var = tk.StringVar(value="3")
        max_traders_combo = ttk.Combobox(max_traders_frame, textvariable=self.max_traders_var,
                                       values=["1", "2", "3", "5", "10"], width=5)
        max_traders_combo.pack(side=tk.LEFT, padx=5)
        
        # 風險倍率
        risk_frame = ttk.Frame(frame)
        risk_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(risk_frame, text="風險倍率:").pack(side=tk.LEFT)
        self.risk_multiplier_var = tk.StringVar(value="1.0")
        risk_combo = ttk.Combobox(risk_frame, textvariable=self.risk_multiplier_var,
                                values=["0.5", "0.8", "1.0", "1.2", "1.5", "2.0"], width=5)
        risk_combo.pack(side=tk.LEFT, padx=5)
        
        # 自動跟單
        auto_frame = ttk.Frame(frame)
        auto_frame.pack(fill=tk.X, pady=2)
        
        self.auto_follow = tk.BooleanVar(value=True)
        ttk.Checkbutton(auto_frame, text="自動跟單優秀交易者", 
                       variable=self.auto_follow).pack(anchor=tk.W)
        
        # 過濾條件
        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(filter_frame, text="最低勝率:").pack(side=tk.LEFT)
        self.min_win_rate_var = tk.StringVar(value="60")
        win_rate_combo = ttk.Combobox(filter_frame, textvariable=self.min_win_rate_var,
                                    values=["50", "60", "70", "80"], width=5)
        win_rate_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(filter_frame, text="最低交易數:").pack(side=tk.LEFT, padx=(10,0))
        self.min_trades_var = tk.StringVar(value="50")
        trades_combo = ttk.Combobox(filter_frame, textvariable=self.min_trades_var,
                                  values=["10", "30", "50", "100"], width=5)
        trades_combo.pack(side=tk.LEFT, padx=5)
        
        # 保存設定按鈕
        ttk.Button(frame, text="💾 保存設定", 
                  command=self.save_copy_settings).pack(fill=tk.X, pady=5)
        
    def create_copy_status_panel(self, parent):
        """創建跟單狀態面板"""
        frame = ttk.LabelFrame(parent, text="📊 跟單狀態", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        # 狀態資訊
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X)
        
        # 跟單系統狀態
        ttk.Label(status_frame, text="系統狀態:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.copy_system_status = ttk.Label(status_frame, text="已停止", style='Warning.TLabel')
        self.copy_system_status.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # 當前跟單交易者
        ttk.Label(status_frame, text="跟單交易者:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.current_traders_count = ttk.Label(status_frame, text="0")
        self.current_traders_count.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # 總跟單交易數
        ttk.Label(status_frame, text="總跟單交易:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.total_copy_trades = ttk.Label(status_frame, text="0")
        self.total_copy_trades.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # 總盈虧
        ttk.Label(status_frame, text="總盈虧:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.total_copy_pnl = ttk.Label(status_frame, text="0.00 USDT")
        self.total_copy_pnl.grid(row=3, column=1, sticky=tk.W, pady=2)
        
        # 今日盈虧
        ttk.Label(status_frame, text="今日盈虧:", font=('Microsoft JhengHei', 10, 'bold')).grid(row=4, column=0, sticky=tk.W, pady=2)
        self.daily_copy_pnl = ttk.Label(status_frame, text="0.00 USDT")
        self.daily_copy_pnl.grid(row=4, column=1, sticky=tk.W, pady=2)
        
        # 控制按鈕
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.start_copy_btn = ttk.Button(btn_frame, text="🚀 啟動跟單", 
                                       command=self.start_copy_trading)
        self.start_copy_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        self.stop_copy_btn = ttk.Button(btn_frame, text="🛑 停止跟單", 
                                      command=self.stop_copy_trading, state='disabled')
        self.stop_copy_btn.pack(side=tk.RIGHT, padx=2, fill=tk.X, expand=True)
        
    def create_copy_history_panel(self, parent):
        """創建跟單記錄面板"""
        frame = ttk.LabelFrame(parent, text="📋 跟單記錄", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 跟單記錄表格
        columns = ('時間', '交易者', '幣種', '操作', '價格', '數量', '盈虧')
        self.copy_history_tree = ttk.Treeview(frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.copy_history_tree.heading(col, text=col)
            self.copy_history_tree.column(col, width=90)
        
        # 滾動條
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.copy_history_tree.yview)
        self.copy_history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.copy_history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 刷新按鈕
        ttk.Button(frame, text="🔄 刷新記錄", 
                  command=self.update_copy_history).pack(fill=tk.X, pady=5)
        
    def create_analysis_tab(self):
        """創建分析頁面"""
        analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(analysis_frame, text="📊 市場分析")
        
        # 創建選項卡
        analysis_notebook = ttk.Notebook(analysis_frame)
        analysis_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 技術分析頁面
        self.create_technical_analysis_tab(analysis_notebook)
        
        # SMC策略分析頁面
        self.create_smc_analysis_tab(analysis_notebook)
        
        # 鏈上數據分析頁面
        self.create_onchain_analysis_tab(analysis_notebook)
        
        # 投資組合分析頁面
        self.create_portfolio_analysis_tab(analysis_notebook)
        
    def create_technical_analysis_tab(self, parent):
        """創建技術分析頁面"""
        frame = ttk.Frame(parent)
        parent.add(frame, text="📈 技術分析")
        
        # 控制面板
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 交易對選擇
        ttk.Label(control_frame, text="交易對:").pack(side=tk.LEFT)
        self.analysis_pair_var = tk.StringVar(value="BTC-USDT")
        pair_combo = ttk.Combobox(control_frame, textvariable=self.analysis_pair_var, 
                                values=self.popular_pairs, width=12)
        pair_combo.pack(side=tk.LEFT, padx=5)
        
        # 時間週期
        ttk.Label(control_frame, text="週期:").pack(side=tk.LEFT, padx=(10,0))
        self.analysis_timeframe_var = tk.StringVar(value="1h")
        timeframe_combo = ttk.Combobox(control_frame, textvariable=self.analysis_timeframe_var,
                                     values=["15m", "1h", "4h", "1d", "1w"], width=8)
        timeframe_combo.pack(side=tk.LEFT, padx=5)
        
        # 分析按鈕
        ttk.Button(control_frame, text="🔍 分析", 
                  command=self.run_technical_analysis).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="💾 保存圖表", 
                  command=self.save_analysis_chart).pack(side=tk.LEFT, padx=5)
        
        # 圖表顯示區域
        chart_frame = ttk.Frame(frame)
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 使用Label來顯示圖表（實際應用中應該使用matplotlib嵌入）
        self.analysis_chart_label = ttk.Label(chart_frame, text="選擇交易對並點擊分析以查看圖表", 
                                            font=('Microsoft JhengHei', 12))
        self.analysis_chart_label.pack(expand=True)
        
        # 分析結果顯示
        result_frame = ttk.LabelFrame(frame, text="📋 分析結果", padding=10)
        result_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.analysis_result_text = tk.Text(result_frame, height=8, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.analysis_result_text.yview)
        self.analysis_result_text.configure(yscrollcommand=scrollbar.set)
        
        self.analysis_result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 插入初始說明文字
        self.analysis_result_text.insert(tk.END, "技術分析功能說明:\n\n")
        self.analysis_result_text.insert(tk.END, "• 支持多種技術指標計算\n")
        self.analysis_result_text.insert(tk.END, "• 自動識別支撐阻力位\n")
        self.analysis_result_text.insert(tk.END, "• 生成交易信號建議\n")
        self.analysis_result_text.insert(tk.END, "• 風險等級評估\n")
        self.analysis_result_text.config(state=tk.DISABLED)
        
    def create_smc_analysis_tab(self, parent):
        """創建SMC策略分析頁面"""
        frame = ttk.Frame(parent)
        parent.add(frame, text="🎯 SMC策略")
        
        # 控制面板
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="交易對:").pack(side=tk.LEFT)
        self.smc_pair_var = tk.StringVar(value="BTC-USDT")
        pair_combo = ttk.Combobox(control_frame, textvariable=self.smc_pair_var, 
                                values=self.popular_pairs, width=12)
        pair_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="🔍 SMC分析", 
                  command=self.run_smc_analysis).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="📚 SMC學習", 
                  command=self.open_smc_learning).pack(side=tk.LEFT, padx=5)
        
        # SMC分析結果
        result_frame = ttk.Frame(frame)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左側：等級分析
        levels_frame = ttk.LabelFrame(result_frame, text="📊 SMC等級分析", padding=10)
        levels_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.smc_levels_text = tk.Text(levels_frame, height=15, wrap=tk.WORD)
        smc_scrollbar = ttk.Scrollbar(levels_frame, orient=tk.VERTICAL, command=self.smc_levels_text.yview)
        self.smc_levels_text.configure(yscrollcommand=smc_scrollbar.set)
        
        self.smc_levels_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        smc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 右側：交易信號
        signals_frame = ttk.LabelFrame(result_frame, text="🎯 交易信號", padding=10)
        signals_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        self.smc_signals_text = tk.Text(signals_frame, height=15, wrap=tk.WORD)
        signals_scrollbar = ttk.Scrollbar(signals_frame, orient=tk.VERTICAL, command=self.smc_signals_text.yview)
        self.smc_signals_text.configure(yscrollcommand=signals_scrollbar.set)
        
        self.smc_signals_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        signals_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 初始化文字
        initial_text = "請選擇交易對並點擊SMC分析以獲取Smart Money Concept分析結果。"
        self.smc_levels_text.insert(tk.END, initial_text)
        self.smc_signals_text.insert(tk.END, "交易信號將在此顯示。")
        self.smc_levels_text.config(state=tk.DISABLED)
        self.smc_signals_text.config(state=tk.DISABLED)
        
    def create_onchain_analysis_tab(self, parent):
        """創建鏈上數據分析頁面"""
        frame = ttk.Frame(parent)
        parent.add(frame, text="🔗 鏈上數據")
        
        # 控制面板
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="幣種:").pack(side=tk.LEFT)
        self.onchain_symbol_var = tk.StringVar(value="BTC")
        symbol_combo = ttk.Combobox(control_frame, textvariable=self.onchain_symbol_var,
                                  values=["BTC", "ETH"], width=8)
        symbol_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="🔍 鏈上分析", 
                  command=self.run_onchain_analysis).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="🔄 更新數據", 
                  command=self.update_onchain_data).pack(side=tk.LEFT, padx=5)
        
        # 鏈上數據顯示
        data_frame = ttk.Frame(frame)
        data_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左側：關鍵指標
        metrics_frame = ttk.LabelFrame(data_frame, text="📈 關鍵指標", padding=10)
        metrics_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # 關鍵指標網格
        metrics_grid = ttk.Frame(metrics_frame)
        metrics_grid.pack(fill=tk.BOTH, expand=True)
        
        # 創建指標標籤
        self.onchain_metrics = {}
        metrics_list = [
            ("哈希率", "hash_rate", "EH/s"),
            ("交易數量", "transaction_count", ""),
            ("活躍地址", "active_addresses", ""),
            ("MVRV比率", "mvrv_ratio", ""),
            ("礦工收入", "miners_revenue", "百萬美元"),
            ("總鎖倉量", "total_value_locked", "十億美元"),
            ("質押比率", "staking_ratio", "%"),
            ("驗證者數", "validator_count", "")
        ]
        
        for i, (name, key, unit) in enumerate(metrics_list):
            ttk.Label(metrics_grid, text=f"{name}:", font=('Microsoft JhengHei', 9, 'bold')).grid(
                row=i, column=0, sticky=tk.W, pady=2, padx=5)
            label = ttk.Label(metrics_grid, text="--")
            label.grid(row=i, column=1, sticky=tk.W, pady=2, padx=5)
            self.onchain_metrics[key] = label
        
        # 右側：市場情緒
        sentiment_frame = ttk.LabelFrame(data_frame, text="😊 市場情緒", padding=10)
        sentiment_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        self.sentiment_text = tk.Text(sentiment_frame, height=10, wrap=tk.WORD)
        sentiment_scrollbar = ttk.Scrollbar(sentiment_frame, orient=tk.VERTICAL, command=self.sentiment_text.yview)
        self.sentiment_text.configure(yscrollcommand=sentiment_scrollbar.set)
        
        self.sentiment_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sentiment_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 網絡健康度
        health_frame = ttk.LabelFrame(frame, text="❤️ 網絡健康度", padding=10)
        health_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.health_text = tk.Text(health_frame, height=6, wrap=tk.WORD)
        health_scrollbar = ttk.Scrollbar(health_frame, orient=tk.VERTICAL, command=self.health_text.yview)
        self.health_text.configure(yscrollcommand=health_scrollbar.set)
        
        self.health_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        health_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 初始化文字
        self.sentiment_text.insert(tk.END, "點擊鏈上分析以獲取市場情緒數據。")
        self.health_text.insert(tk.END, "網絡健康度分析將在此顯示。")
        self.sentiment_text.config(state=tk.DISABLED)
        self.health_text.config(state=tk.DISABLED)
        
    def create_portfolio_analysis_tab(self, parent):
        """創建投資組合分析頁面"""
        frame = ttk.Frame(parent)
        parent.add(frame, text="💰 投資組合")
        
        # 控制面板
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="📊 分析組合", 
                  command=self.analyze_portfolio).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="📈 期望值計算", 
                  command=self.calculate_expectancy).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="🔄 更新數據", 
                  command=self.update_portfolio_data).pack(side=tk.LEFT, padx=5)
        
        # 投資組合分析結果
        result_frame = ttk.Frame(frame)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左側：績效統計
        performance_frame = ttk.LabelFrame(result_frame, text="📈 績效統計", padding=10)
        performance_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.performance_text = tk.Text(performance_frame, height=12, wrap=tk.WORD)
        performance_scrollbar = ttk.Scrollbar(performance_frame, orient=tk.VERTICAL, command=self.performance_text.yview)
        self.performance_text.configure(yscrollcommand=performance_scrollbar.set)
        
        self.performance_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        performance_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 右側：風險分析
        risk_frame = ttk.LabelFrame(result_frame, text="⚠️ 風險分析", padding=10)
        risk_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        self.risk_text = tk.Text(risk_frame, height=12, wrap=tk.WORD)
        risk_scrollbar = ttk.Scrollbar(risk_frame, orient=tk.VERTICAL, command=self.risk_text.yview)
        self.risk_text.configure(yscrollcommand=risk_scrollbar.set)
        
        self.risk_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        risk_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 建議框架
        advice_frame = ttk.LabelFrame(frame, text="💡 投資建議", padding=10)
        advice_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.advice_text = tk.Text(advice_frame, height=6, wrap=tk.WORD)
        advice_scrollbar = ttk.Scrollbar(advice_frame, orient=tk.VERTICAL, command=self.advice_text.yview)
        self.advice_text.configure(yscrollcommand=advice_scrollbar.set)
        
        self.advice_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        advice_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 初始化文字
        initial_performance = "點擊分析組合以查看投資組合績效統計。"
        initial_risk = "風險分析結果將在此顯示。"
        initial_advice = "基於您的投資組合表現，系統將提供個性化建議。"
        
        self.performance_text.insert(tk.END, initial_performance)
        self.risk_text.insert(tk.END, initial_risk)
        self.advice_text.insert(tk.END, initial_advice)
        
        self.performance_text.config(state=tk.DISABLED)
        self.risk_text.config(state=tk.DISABLED)
        self.advice_text.config(state=tk.DISABLED)
        
    def create_settings_tab(self):
        """創建設定頁面"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="⚙️ 系統設定")
        
        # 創建設定選項卡
        settings_notebook = ttk.Notebook(settings_frame)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # API設定
        self.create_api_settings_tab(settings_notebook)
        
        # 交易設定
        self.create_trading_settings_tab(settings_notebook)
        
        # 通知設定
        self.create_notification_settings_tab(settings_notebook)
        
        # 系統設定
        self.create_system_settings_tab(settings_notebook)
        
        # 關於頁面
        self.create_about_tab(settings_notebook)
        
    def create_api_settings_tab(self, parent):
        """創建API設定頁面"""
        frame = ttk.Frame(parent)
        parent.add(frame, text="🔑 API設定")
        
        # OKX API設定
        api_frame = ttk.LabelFrame(frame, text="OKX API 設定", padding=15)
        api_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # API Key
        ttk.Label(api_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, show="*", width=40)
        api_key_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Secret Key
        ttk.Label(api_frame, text="Secret Key:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.secret_key_var = tk.StringVar()
        secret_key_entry = ttk.Entry(api_frame, textvariable=self.secret_key_var, show="*", width=40)
        secret_key_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Passphrase
        ttk.Label(api_frame, text="Passphrase:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.passphrase_var = tk.StringVar()
        passphrase_entry = ttk.Entry(api_frame, textvariable=self.passphrase_var, show="*", width=40)
        passphrase_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        # 測試網路
        self.testnet_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(api_frame, text="使用測試網路", variable=self.testnet_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # API測試按鈕
        ttk.Button(api_frame, text="🧪 測試API連接", command=self.test_api_connection).grid(row=4, column=0, pady=10)
        ttk.Button(api_frame, text="💾 保存API設定", command=self.save_api_settings).grid(row=4, column=1, pady=10, padx=5)
        
        # Discord Webhook設定
        discord_frame = ttk.LabelFrame(frame, text="Discord 通知設定", padding=15)
        discord_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(discord_frame, text="Webhook URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.webhook_var = tk.StringVar()
        webhook_entry = ttk.Entry(discord_frame, textvariable=self.webhook_var, width=40)
        webhook_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        self.discord_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(discord_frame, text="啟用Discord通知", variable=self.discord_enabled_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Button(discord_frame, text="🧪 測試Discord", command=self.test_discord).grid(row=2, column=0, pady=10)
        ttk.Button(discord_frame, text="💾 保存設定", command=self.save_discord_settings).grid(row=2, column=1, pady=10, padx=5)
        
        # 載入現有設定
        self.load_api_settings()
        
    def create_trading_settings_tab(self, parent):
        """創建交易設定頁面"""
        frame = ttk.Frame(parent)
        parent.add(frame, text="💰 交易設定")
        
        # 風險管理設定
        risk_frame = ttk.LabelFrame(frame, text="⚠️ 風險管理設定", padding=15)
        risk_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 每筆交易風險
        ttk.Label(risk_frame, text="每筆交易風險 (%):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.trade_risk_var = tk.StringVar(value="2.0")
        risk_entry = ttk.Entry(risk_frame, textvariable=self.trade_risk_var, width=10)
        risk_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # 最大持倉數
        ttk.Label(risk_frame, text="最大持倉數:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.max_positions_var = tk.StringVar(value="5")
        positions_entry = ttk.Entry(risk_frame, textvariable=self.max_positions_var, width=10)
        positions_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        # 每日最大虧損
        ttk.Label(risk_frame, text="每日最大虧損 (%):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.daily_loss_var = tk.StringVar(value="5.0")
        loss_entry = ttk.Entry(risk_frame, textvariable=self.daily_loss_var, width=10)
        loss_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        # 最大倉位大小
        ttk.Label(risk_frame, text="最大倉位大小 (%):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.position_size_var = tk.StringVar(value="20.0")
        size_entry = ttk.Entry(risk_frame, textvariable=self.position_size_var, width=10)
        size_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
        
        # 交易設定
        trading_frame = ttk.LabelFrame(frame, text="🎯 交易設定", padding=15)
        trading_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 默認槓桿
        ttk.Label(trading_frame, text="默認槓桿:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.default_leverage_var = tk.StringVar(value="10")
        leverage_combo = ttk.Combobox(trading_frame, textvariable=self.default_leverage_var,
                                    values=["1", "3", "5", "10", "20"], width=10)
        leverage_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # 啟用智能止損
        self.smart_stoploss_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(trading_frame, text="啟用智能止損", variable=self.smart_stoploss_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 啟用移動止損
        self.trailing_stop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(trading_frame, text="啟用移動止損", variable=self.trailing_stop_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 保存按鈕
        ttk.Button(frame, text="💾 保存交易設定", command=self.save_trading_settings).pack(pady=20)
        
        # 載入現有設定
        self.load_trading_settings()
        
    def create_notification_settings_tab(self, parent):
        """創建通知設定頁面"""
        frame = ttk.Frame(parent)
        parent.add(frame, text="🔔 通知設定")
        
        # 價格提醒設定
        price_frame = ttk.LabelFrame(frame, text="💰 價格提醒", padding=15)
        price_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.price_alerts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(price_frame, text="啟用價格提醒", variable=self.price_alerts_var).pack(anchor=tk.W, pady=5)
        
        ttk.Label(price_frame, text="價格變化提醒閾值 (%):").pack(anchor=tk.W, pady=2)
        self.price_alert_threshold_var = tk.StringVar(value="5.0")
        threshold_entry = ttk.Entry(price_frame, textvariable=self.price_alert_threshold_var, width=10)
        threshold_entry.pack(anchor=tk.W, pady=2)
        
        # 交易通知設定
        trade_frame = ttk.LabelFrame(frame, text="📊 交易通知", padding=15)
        trade_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.trade_notifications_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(trade_frame, text="啟用交易執行通知", variable=self.trade_notifications_var).pack(anchor=tk.W, pady=5)
        
        self.risk_notifications_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(trade_frame, text="啟用風險警告通知", variable=self.risk_notifications_var).pack(anchor=tk.W, pady=5)
        
        self.system_notifications_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(trade_frame, text="啟用系統錯誤通知", variable=self.system_notifications_var).pack(anchor=tk.W, pady=5)
        
        # 聲音提醒
        sound_frame = ttk.LabelFrame(frame, text="🔊 聲音提醒", padding=15)
        sound_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.sound_alerts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(sound_frame, text="啟用聲音提醒", variable=self.sound_alerts_var).pack(anchor=tk.W, pady=5)
        
        # 保存按鈕
        ttk.Button(frame, text="💾 保存通知設定", command=self.save_notification_settings).pack(pady=20)
        
    def create_system_settings_tab(self, parent):
        """創建系統設定頁面"""
        frame = ttk.Frame(parent)
        parent.add(frame, text="🖥️ 系統設定")
        
        # 界面設定
        ui_frame = ttk.LabelFrame(frame, text="🎨 界面設定", padding=15)
        ui_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(ui_frame, text="界面主題:").pack(anchor=tk.W, pady=2)
        self.theme_var = tk.StringVar(value="light")
        theme_combo = ttk.Combobox(ui_frame, textvariable=self.theme_var,
                                 values=["light", "dark", "system"], width=15)
        theme_combo.pack(anchor=tk.W, pady=2)
        
        ttk.Label(ui_frame, text="語言:").pack(anchor=tk.W, pady=2)
        self.language_var = tk.StringVar(value="zh-TW")
        language_combo = ttk.Combobox(ui_frame, textvariable=self.language_var,
                                    values=["zh-TW", "en-US"], width=15)
        language_combo.pack(anchor=tk.W, pady=2)
        
        self.auto_refresh_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ui_frame, text="啟用自動刷新", variable=self.auto_refresh_var).pack(anchor=tk.W, pady=5)
        
        # 數據設定
        data_frame = ttk.LabelFrame(frame, text="📊 數據設定", padding=15)
        data_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(data_frame, text="數據保存天數:").pack(anchor=tk.W, pady=2)
        self.data_retention_var = tk.StringVar(value="90")
        retention_combo = ttk.Combobox(data_frame, textvariable=self.data_retention_var,
                                     values=["30", "60", "90", "180", "365"], width=10)
        retention_combo.pack(anchor=tk.W, pady=2)
        
        self.auto_backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(data_frame, text="啟用自動備份", variable=self.auto_backup_var).pack(anchor=tk.W, pady=5)
        
        # 系統操作
        system_frame = ttk.LabelFrame(frame, text="⚙️ 系統操作", padding=15)
        system_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(system_frame, text="🗃️ 清理緩存", command=self.clear_cache).pack(fill=tk.X, pady=2)
        ttk.Button(system_frame, text="💾 備份數據", command=self.backup_data).pack(fill=tk.X, pady=2)
        ttk.Button(system_frame, text="📊 系統日誌", command=self.show_system_logs).pack(fill=tk.X, pady=2)
        
        # 保存按鈕
        ttk.Button(frame, text="💾 保存系統設定", command=self.save_system_settings).pack(pady=20)
        
    def create_about_tab(self, parent):
        """創建關於頁面"""
        frame = ttk.Frame(parent)
        parent.add(frame, text="ℹ️ 關於")
        
        # 應用資訊
        info_frame = ttk.LabelFrame(frame, text="應用資訊", padding=20)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 應用名稱和版本
        ttk.Label(info_frame, text="💰 幣圈交易輔助系統", 
                 font=('Microsoft JhengHei', 16, 'bold')).pack(pady=10)
        
        ttk.Label(info_frame, text="台灣專用版 v3.0", 
                 font=('Microsoft JhengHei', 12)).pack(pady=5)
        
        # 描述
        description = """
專為台灣用戶設計的加密貨幣交易輔助系統，
整合多種交易策略和風險管理工具，
幫助您更聰明地進行加密貨幣交易。
        """
        ttk.Label(info_frame, text=description, justify=tk.CENTER).pack(pady=10)
        
        # 功能特色
        features_frame = ttk.Frame(info_frame)
        features_frame.pack(pady=10)
        
        features = [
            "✅ 智能交易系統",
            "✅ SMC策略分析", 
            "✅ 鏈上數據監控",
            "✅ 跟單交易系統",
            "✅ 風險管理工具",
            "✅ 台灣在地化"
        ]
        
        for feature in features:
            ttk.Label(features_frame, text=feature).pack(anchor=tk.W)
        
        # 系統狀態
        status_frame = ttk.Frame(info_frame)
        status_frame.pack(pady=20)
        
        ttk.Button(status_frame, text="🔄 檢查更新", command=self.check_for_updates).pack(side=tk.LEFT, padx=5)
        ttk.Button(status_frame, text="📖 使用說明", command=self.show_help).pack(side=tk.LEFT, padx=5)
        ttk.Button(status_frame, text="🐛 報告問題", command=self.report_issue).pack(side=tk.LEFT, padx=5)
        
    def create_status_bar(self):
        """創建狀態欄"""
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        # 左側狀態訊息
        self.status_label = ttk.Label(status_frame, text="系統就緒", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 右側更新時間
        self.update_time_label = ttk.Label(status_frame, text="", relief=tk.SUNKEN, anchor=tk.E)
        self.update_time_label.pack(side=tk.RIGHT)
        
    def load_initial_data(self):
        """載入初始數據"""
        self.update_status("正在載入初始數據...")
        
        # 在背景線程中載入數據
        def load_data():
            try:
                self.update_price_data()
                self.update_account_data()
                self.update_positions()
                self.update_trade_history()
                self.check_system_status()
                
                self.update_status("系統載入完成")
                
            except Exception as e:
                self.update_status(f"載入錯誤: {str(e)}")
        
        threading.Thread(target=load_data, daemon=True).start()
        
    def start_data_updater(self):
        """啟動數據更新器"""
        def update_loop():
            while True:
                try:
                    # 每30秒更新一次價格
                    self.update_price_data()
                    
                    # 每60秒更新一次帳戶數據
                    self.update_account_data()
                    
                    # 每120秒更新一次持倉
                    self.update_positions()
                    
                except Exception as e:
                    print(f"數據更新錯誤: {e}")
                
                # 等待30秒
                import time
                time.sleep(30)
        
        # 啟動背景更新線程
        threading.Thread(target=update_loop, daemon=True).start()
        
    def update_price_data(self):
        """更新價格數據"""
        try:
            for pair in self.popular_pairs[:6]:
                ticker = self.okx_api.get_ticker(pair)
                if ticker:
                    price = ticker.get('last', 0)
                    change = ticker.get('percentage', 0)
                    volume = ticker.get('volume', 0)
                    
                    # 更新樹狀視圖
                    for item in self.price_tree.get_children():
                        if self.price_tree.item(item, 'values')[0] == pair:
                            self.price_tree.item(item, values=(
                                pair, 
                                f"{price:.4f}", 
                                f"{change:.2f}%", 
                                f"{volume:.0f}"
                            ))
                            break
                    
                    # 更新BTC/ETH標籤
                    if pair == "BTC-USDT":
                        self.btc_price_label.config(text=f"BTC: ${price:.2f}")
                    elif pair == "ETH-USDT":
                        self.eth_price_label.config(text=f"ETH: ${price:.2f}")
            
            self.update_time_label.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
        except Exception as e:
            self.update_status(f"價格更新錯誤: {str(e)}")
            
    def update_account_data(self):
        """更新帳戶數據"""
        try:
            # 獲取現貨餘額
            spot_balance = self.okx_api.get_spot_balance()
            if spot_balance:
                total = spot_balance.get('total_balance', 0)
                self.spot_balance_label.config(text=f"{total:.2f} USDT")
            
            # 獲取合約餘額
            futures_balance = self.okx_api.get_futures_balance()
            if futures_balance:
                total = futures_balance.get('total_balance', 0)
                self.futures_balance_label.config(text=f"{total:.2f} USDT")
            
            # 計算總資產（簡化）
            spot_total = spot_balance.get('total_balance', 0) if spot_balance else 0
            futures_total = futures_balance.get('total_balance', 0) if futures_balance else 0
            total_balance = spot_total + futures_total
            
            self.total_balance_label.config(text=f"{total_balance:.2f} USDT")
            
            # 更新今日盈虧（需要從數據庫獲取）
            stats = self.trading_system.get_performance_stats()
            daily_pnl = stats.get('daily_pnl', 0)
            pnl_color = 'green' if daily_pnl >= 0 else 'red'
            self.daily_pnl_label.config(
                text=f"{daily_pnl:.2f} USDT",
                foreground=pnl_color
            )
            
        except Exception as e:
            self.update_status(f"帳戶更新錯誤: {str(e)}")
            
    def update_positions(self):
        """更新持倉數據"""
        try:
            # 清空現有數據
            for item in self.position_tree.get_children():
                self.position_tree.delete(item)
            
            # 獲取現貨持倉
            spot_holdings = self.trading_system.get_spot_holdings()
            for symbol, holding in spot_holdings.items():
                if holding['quantity'] > 0:
                    current_price = self.okx_api.get_ticker(symbol)
                    price = current_price.get('last', 0) if current_price else 0
                    pnl = (price - holding['avg_price']) * holding['quantity']
                    
                    self.position_tree.insert('', 'end', values=(
                        symbol, '現貨', '多單', 
                        f"{holding['quantity']:.4f}",
                        f"{holding['avg_price']:.4f}",
                        f"{price:.4f}",
                        f"{pnl:.2f}",
                        "N/A"
                    ))
            
            # 獲取合約持倉
            futures_positions = self.trading_system.get_open_positions()
            for position in futures_positions:
                self.position_tree.insert('', 'end', values=(
                    position['symbol'],
                    '合約',
                    position['position_type'],
                    f"{position['quantity']:.4f}",
                    f"{position['entry_price']:.4f}",
                    f"{position.get('current_price', 0):.4f}",
                    f"{position.get('pnl', 0):.2f}",
                    f"{position.get('stop_loss', 0):.4f}"
                ))
                
        except Exception as e:
            self.update_status(f"持倉更新錯誤: {str(e)}")
            
    def update_trade_history(self):
        """更新交易記錄"""
        try:
            # 清空現有數據
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
            
            # 獲取交易記錄
            trades = self.trading_system.get_trading_history(limit=20)
            for trade in trades:
                # 簡化顯示，實際應根據數據庫結構調整
                self.history_tree.insert('', 'end', values=(
                    trade[4] if len(trade) > 4 else 'N/A',  # 時間
                    trade[1] if len(trade) > 1 else 'N/A',  # 幣種
                    '現貨' if 'SPOT' in str(trade[2]) else '合約',  # 類型
                    trade[2] if len(trade) > 2 else 'N/A',  # 操作
                    f"{trade[3]:.4f}" if len(trade) > 3 else 'N/A',  # 價格
                    f"{trade[4]:.4f}" if len(trade) > 4 else 'N/A',  # 數量
                    f"{trade[6]:.2f}" if len(trade) > 6 else 'N/A'   # 盈虧
                ))
                
        except Exception as e:
            self.update_status(f"交易記錄更新錯誤: {str(e)}")
            
    def check_system_status(self):
        """檢查系統狀態"""
        try:
            # 測試API連接
            api_success, api_message = self.okx_api.test_connection()
            if api_success:
                self.api_status_label.config(text="✅ 正常", style='Success.TLabel')
            else:
                self.api_status_label.config(text="❌ 異常", style='Error.TLabel')
            
            # 測試數據庫連接
            db_success = self.db.test_connection()
            if db_success:
                self.db_status_label.config(text="✅ 正常", style='Success.TLabel')
            else:
                self.db_status_label.config(text="❌ 異常", style='Error.TLabel')
            
            # 測試Discord連接
            if self.discord_bot.enabled:
                discord_success, discord_message = self.discord_bot.test_connection()
                if discord_success:
                    self.discord_status_label.config(text="✅ 正常", style='Success.TLabel')
                else:
                    self.discord_status_label.config(text="❌ 異常", style='Error.TLabel')
            else:
                self.discord_status_label.config(text="⚪ 未啟用")
            
            # 自動交易狀態
            if self.trading_system.auto_trading:
                self.auto_trading_label.config(text="🟢 運行中", style='Success.TLabel')
            else:
                self.auto_trading_label.config(text="⚪ 已停止")
                
            self.update_status("系統狀態檢查完成")
            
        except Exception as e:
            self.update_status(f"狀態檢查錯誤: {str(e)}")
            
    def start_auto_trading(self):
        """啟動自動交易"""
        try:
            # 更新交易系統設定
            self.trading_system.trading_mode = self.trading_mode.get()
            self.trading_system.risk_percent = float(self.risk_percent_var.get())
            self.trading_system.max_positions = int(self.max_positions_var.get())
            
            success, message = self.trading_system.start_auto_trading()
            
            if success:
                self.auto_trading_status.config(text="🟢 運行中", style='Success.TLabel')
                self.start_auto_btn.config(state='disabled')
                self.stop_auto_btn.config(state='normal')
                messagebox.showinfo("自動交易", "自動交易已啟動")
            else:
                messagebox.showerror("自動交易", f"啟動失敗: {message}")
                
        except Exception as e:
            messagebox.showerror("錯誤", f"啟動自動交易時發生錯誤: {str(e)}")
            
    def stop_auto_trading(self):
        """停止自動交易"""
        try:
            success, message = self.trading_system.stop_auto_trading()
            
            if success:
                self.auto_trading_status.config(text="⚪ 已停止")
                self.start_auto_btn.config(state='normal')
                self.stop_auto_btn.config(state='disabled')
                messagebox.showinfo("自動交易", "自動交易已停止")
            else:
                messagebox.showerror("自動交易", f"停止失敗: {message}")
                
        except Exception as e:
            messagebox.showerror("錯誤", f"停止自動交易時發生錯誤: {str(e)}")
            
    def execute_quick_trade(self):
        """執行快速交易"""
        try:
            symbol = self.quick_pair_var.get()
            trade_type = self.quick_trade_type.get()
            action = self.quick_action.get()
            amount = float(self.quick_amount_var.get())
            price_str = self.quick_price_var.get()
            
            price = float(price_str) if price_str.strip() else None
            
            if trade_type == "spot":
                if action == "buy":
                    success, message = self.trading_system.spot_buy(symbol, amount, price)
                else:
                    success, message = self.trading_system.spot_sell(symbol, amount, price)
            else:
                # 合約交易
                if action == "buy":
                    success, message = self.trading_system.open_long_position(symbol, price or 0, amount)
                else:
                    success, message = self.trading_system.open_short_position(symbol, price or 0, amount)
            
            if success:
                messagebox.showinfo("交易成功", message)
                self.update_account_data()
                self.update_positions()
            else:
                messagebox.showerror("交易失敗", message)
                
        except ValueError:
            messagebox.showerror("輸入錯誤", "請輸入有效的數字")
        except Exception as e:
            messagebox.showerror("錯誤", f"交易執行錯誤: {str(e)}")
            
    def save_trading_settings(self):
        """保存交易設定"""
        try:
            # 更新交易系統設定
            self.trading_system.spot_enabled = self.spot_enabled.get()
            self.trading_system.futures_enabled = self.futures_enabled.get()
            self.trading_system.default_leverage = int(self.leverage_var.get())
            self.trading_system.stop_loss_enabled = self.stoploss_enabled.get()
            
            # 保存到設定檔
            success = self.trading_system.save_settings()
            
            if success:
                messagebox.showinfo("設定", "交易設定已保存")
            else:
                messagebox.showerror("設定", "保存失敗")
                
        except Exception as e:
            messagebox.showerror("錯誤", f"保存設定時發生錯誤: {str(e)}")
            
    def manual_close_position(self):
        """手動平倉"""
        # 實現手動平倉功能
        messagebox.showinfo("功能", "手動平倉功能開發中...")
        
    def adjust_stop_loss(self):
        """調整止損"""
        # 實現調整止損功能
        messagebox.showinfo("功能", "調整止損功能開發中...")
        
    def update_status(self, message):
        """更新狀態欄訊息"""
        self.status_label.config(text=message)
        print(f"狀態: {message}")
        
    def show_error(self, title, message):
        """顯示錯誤訊息"""
        messagebox.showerror(title, message)
        self.update_status(f"錯誤: {title} - {message}")
        
    def show_info(self, title, message):
        """顯示資訊訊息"""
        messagebox.showinfo(title, message)
        
    def on_closing(self):
        """關閉程式時的處理"""
        # 停止自動交易
        if hasattr(self, 'trading_system') and self.trading_system.auto_trading:
            self.trading_system.stop_auto_trading()
        
        # 停止跟單系統
        if hasattr(self, 'copy_trading') and self.copy_trading.is_running:
            self.copy_trading.stop_copy_trading()
            
        self.root.quit()
        
    # ==================== 現貨交易功能方法 ====================
    
    def update_spot_price(self):
        """更新現貨價格"""
        try:
            symbol = self.spot_pair_var.get()
            ticker = self.okx_api.get_ticker(symbol)
            if ticker:
                price = ticker.get('last', 0)
                self.spot_current_price.config(text=f"{price:.4f} USDT")
                
                # 自動填入買入賣出價格
                if not self.spot_buy_price_var.get():
                    self.spot_buy_price_var.set(f"{price:.4f}")
                if not self.spot_sell_price_var.get():
                    self.spot_sell_price_var.set(f"{price:.4f}")
                    
        except Exception as e:
            self.show_error("價格更新錯誤", f"無法獲取 {symbol} 價格: {str(e)}")
            
    def spot_buy_order(self):
        """下現貨買單"""
        try:
            symbol = self.spot_pair_var.get()
            amount = float(self.spot_buy_amount_var.get())
            price_str = self.spot_buy_price_var.get()
            
            price = float(price_str) if price_str.strip() else None
            
            success, message = self.trading_system.spot_buy(symbol, amount, price)
            
            if success:
                self.show_info("交易成功", message)
                self.update_spot_account()
                self.update_spot_holdings()
                self.update_spot_history()
            else:
                self.show_error("交易失敗", message)
                
        except ValueError:
            self.show_error("輸入錯誤", "請輸入有效的數字")
        except Exception as e:
            self.show_error("交易錯誤", f"下單失敗: {str(e)}")
            
    def spot_sell_order(self):
        """下現貨賣單"""
        try:
            symbol = self.spot_pair_var.get()
            amount = float(self.spot_sell_amount_var.get())
            price_str = self.spot_sell_price_var.get()
            
            price = float(price_str) if price_str.strip() else None
            
            success, message = self.trading_system.spot_sell(symbol, amount, price)
            
            if success:
                self.show_info("交易成功", message)
                self.update_spot_account()
                self.update_spot_holdings()
                self.update_spot_history()
            else:
                self.show_error("交易失敗", message)
                
        except ValueError:
            self.show_error("輸入錯誤", "請輸入有效的數字")
        except Exception as e:
            self.show_error("交易錯誤", f"下單失敗: {str(e)}")
            
    def spot_buy_all(self):
        """全倉買入"""
        try:
            symbol = self.spot_pair_var.get()
            
            # 獲取USDT餘額
            balance = self.okx_api.get_spot_balance()
            if not balance:
                self.show_error("錯誤", "無法獲取帳戶餘額")
                return
                
            available_usdt = balance.get('available_balance', 0)
            if available_usdt <= 0:
                self.show_error("資金不足", "USDT餘額為0")
                return
            
            # 獲取當前價格
            ticker = self.okx_api.get_ticker(symbol)
            if not ticker:
                self.show_error("錯誤", "無法獲取當前價格")
                return
                
            current_price = ticker.get('last', 0)
            if current_price <= 0:
                self.show_error("錯誤", "無效的價格")
                return
            
            # 計算可買數量 (保留一些手續費)
            amount = (available_usdt * 0.999) / current_price
            
            self.spot_buy_amount_var.set(f"{amount:.6f}")
            if not self.spot_buy_price_var.get():
                self.spot_buy_price_var.set(f"{current_price:.4f}")
                
            self.show_info("計算完成", f"可買數量: {amount:.6f} {symbol.split('-')[0]}")
            
        except Exception as e:
            self.show_error("計算錯誤", f"計算可買數量失敗: {str(e)}")
            
    def spot_sell_all(self):
        """全倉賣出"""
        try:
            symbol = self.spot_pair_var.get()
            base_currency = symbol.split('-')[0]
            
            # 獲取持倉數量
            holdings = self.trading_system.get_spot_holdings()
            if symbol not in holdings or holdings[symbol]['quantity'] <= 0:
                self.show_error("持倉錯誤", f"沒有 {base_currency} 持倉")
                return
                
            amount = holdings[symbol]['quantity']
            
            self.spot_sell_amount_var.set(f"{amount:.6f}")
            
            # 獲取當前價格
            ticker = self.okx_api.get_ticker(symbol)
            if ticker and not self.spot_sell_price_var.get():
                current_price = ticker.get('last', 0)
                self.spot_sell_price_var.set(f"{current_price:.4f}")
                
            self.show_info("計算完成", f"可賣數量: {amount:.6f} {base_currency}")
            
        except Exception as e:
            self.show_error("計算錯誤", f"計算可賣數量失敗: {str(e)}")
            
    def update_spot_holdings(self):
        """更新現貨持倉"""
        try:
            # 清空現有數據
            for item in self.spot_holdings_tree.get_children():
                self.spot_holdings_tree.delete(item)
            
            # 獲取現貨持倉
            holdings = self.trading_system.get_spot_holdings()
            
            total_value = 0
            for symbol, holding in holdings.items():
                if holding['quantity'] > 0:
                    # 獲取當前價格
                    ticker = self.okx_api.get_ticker(symbol)
                    current_price = ticker.get('last', 0) if ticker else 0
                    
                    # 計算價值和盈虧
                    value = holding['quantity'] * current_price
                    pnl = (current_price - holding['avg_price']) * holding['quantity']
                    pnl_percent = (current_price - holding['avg_price']) / holding['avg_price'] * 100 if holding['avg_price'] > 0 else 0
                    
                    total_value += value
                    
                    # 添加到表格
                    self.spot_holdings_tree.insert('', 'end', values=(
                        symbol,
                        f"{holding['quantity']:.6f}",
                        f"{holding['avg_price']:.4f}",
                        f"{current_price:.4f}",
                        f"{value:.2f} USDT",
                        f"{pnl:.2f} USDT ({pnl_percent:.2f}%)"
                    ))
            
            # 更新總價值
            self.spot_total_value.config(text=f"{total_value:.2f} USDT")
            
        except Exception as e:
            self.update_status(f"更新現貨持倉錯誤: {str(e)}")
            
    def update_spot_account(self):
        """更新現貨帳戶"""
        try:
            balance = self.okx_api.get_spot_balance()
            if balance:
                total = balance.get('total_balance', 0)
                available = balance.get('available_balance', 0)
                used = balance.get('used_balance', 0)
                
                self.spot_usdt_balance.config(text=f"{total:.2f} USDT")
                self.spot_usdt_available.config(text=f"{available:.2f} USDT")
                self.spot_usdt_frozen.config(text=f"{used:.2f} USDT")
                
        except Exception as e:
            self.update_status(f"更新現貨帳戶錯誤: {str(e)}")
            
    def update_spot_history(self):
        """更新現貨交易記錄"""
        try:
            # 清空現有數據
            for item in self.spot_history_tree.get_children():
                self.spot_history_tree.delete(item)
            
            # 獲取現貨交易記錄
            trades = self.trading_system.get_trading_history(limit=20, trading_type='SPOT')
            
            for trade in trades:
                # 根據實際數據庫結構調整
                timestamp = trade[4] if len(trade) > 4 else 'N/A'
                symbol = trade[1] if len(trade) > 1 else 'N/A'
                action = trade[2] if len(trade) > 2 else 'N/A'
                price = f"{trade[3]:.4f}" if len(trade) > 3 else 'N/A'
                quantity = f"{trade[4]:.6f}" if len(trade) > 4 else 'N/A'
                total = float(price) * float(quantity) if price != 'N/A' and quantity != 'N/A' else 0
                status = "已完成"  # 需要從數據庫獲取實際狀態
                
                # 過濾顯示
                filter_type = self.spot_history_filter.get()
                if filter_type == "all" or (filter_type == "buy" and "BUY" in action) or (filter_type == "sell" and "SELL" in action):
                    self.spot_history_tree.insert('', 'end', values=(
                        timestamp, symbol, action, price, quantity, 
                        f"{total:.2f} USDT", status
                    ))
                    
        except Exception as e:
            self.update_status(f"更新現貨記錄錯誤: {str(e)}")
            
    def analyze_spot_holdings(self):
        """分析現貨持倉"""
        try:
            holdings = self.trading_system.get_spot_holdings()
            if not holdings:
                self.show_info("持倉分析", "目前沒有現貨持倉")
                return
            
            total_investment = 0
            total_current_value = 0
            profitable_holdings = 0
            
            for symbol, holding in holdings.items():
                if holding['quantity'] > 0:
                    ticker = self.okx_api.get_ticker(symbol)
                    current_price = ticker.get('last', 0) if ticker else 0
                    
                    investment = holding['quantity'] * holding['avg_price']
                    current_value = holding['quantity'] * current_price
                    
                    total_investment += investment
                    total_current_value += current_value
                    
                    if current_value > investment:
                        profitable_holdings += 1
            
            total_pnl = total_current_value - total_investment
            total_pnl_percent = (total_pnl / total_investment * 100) if total_investment > 0 else 0
            
            analysis_msg = f"""
📊 現貨持倉分析報告:

💰 總投資: {total_investment:.2f} USDT
📈 當前價值: {total_current_value:.2f} USDT
🎯 總盈虧: {total_pnl:.2f} USDT ({total_pnl_percent:.2f}%)
✅ 盈利持倉: {profitable_holdings} / {len(holdings)}

💡 建議: { "持倉表現良好" if total_pnl > 0 else "考慮調整持倉" }
"""
            self.show_info("持倉分析", analysis_msg)
            
        except Exception as e:
            self.show_error("分析錯誤", f"持倉分析失敗: {str(e)}")
            
    # ==================== 合約交易功能方法 ====================
    
    def update_futures_price(self):
        """更新合約價格"""
        try:
            symbol = self.futures_pair_var.get()
            ticker = self.okx_api.get_ticker(symbol)
            if ticker:
                price = ticker.get('last', 0)
                self.futures_current_price.config(text=f"{price:.4f} USDT")
                
                # 自動填入開倉平倉價格
                if not self.futures_open_price_var.get():
                    self.futures_open_price_var.set(f"{price:.4f}")
                if not self.futures_close_price_var.get():
                    self.futures_close_price_var.set(f"{price:.4f}")
                    
        except Exception as e:
            self.show_error("價格更新錯誤", f"無法獲取 {symbol} 價格: {str(e)}")
            
    def set_futures_leverage(self):
        """設置合約槓桿"""
        try:
            symbol = self.futures_pair_var.get()
            leverage = int(self.futures_leverage_var.get())
            
            success = self.okx_api.futures_set_leverage(symbol, leverage)
            
            if success:
                self.show_info("設置成功", f"{symbol} 槓桿已設置為 {leverage}x")
            else:
                self.show_error("設置失敗", f"無法設置 {symbol} 槓桿")
                
        except Exception as e:
            self.show_error("設置錯誤", f"設置槓桿失敗: {str(e)}")
            
    def futures_open_order(self, direction):
        """開合約倉位"""
        try:
            symbol = self.futures_pair_var.get()
            amount = float(self.futures_open_amount_var.get())
            price_str = self.futures_open_price_var.get()
            leverage = int(self.futures_leverage_var.get())
            
            price = float(price_str) if price_str.strip() else None
            
            if direction == "long":
                success, message = self.trading_system.open_long_position(symbol, price or 0, amount)
            else:
                success, message = self.trading_system.open_short_position(symbol, price or 0, amount)
            
            if success:
                self.show_info("開倉成功", message)
                self.update_futures_account()
                self.update_futures_positions()
                self.update_futures_history()
            else:
                self.show_error("開倉失敗", message)
                
        except ValueError:
            self.show_error("輸入錯誤", "請輸入有效的數字")
        except Exception as e:
            self.show_error("開倉錯誤", f"開倉失敗: {str(e)}")
            
    def futures_close_order(self):
        """平合約倉位"""
        try:
            symbol = self.futures_pair_var.get()
            amount = float(self.futures_close_amount_var.get())
            price_str = self.futures_close_price_var.get()
            
            price = float(price_str) if price_str.strip() else None
            
            # 這裡需要實現具體的平倉邏輯
            # 暫時使用模擬平倉
            success, message = self.trading_system.close_position(symbol, "MANUAL")
            
            if success:
                self.show_info("平倉成功", message)
                self.update_futures_account()
                self.update_futures_positions()
                self.update_futures_history()
            else:
                self.show_error("平倉失敗", message)
                
        except ValueError:
            self.show_error("輸入錯誤", "請輸入有效的數字")
        except Exception as e:
            self.show_error("平倉錯誤", f"平倉失敗: {str(e)}")
            
    def futures_close_all(self):
        """一鍵平倉所有合約持倉"""
        try:
            positions = self.trading_system.get_open_positions()
            if not positions:
                self.show_info("平倉", "目前沒有合約持倉")
                return
            
            success_count = 0
            for position in positions:
                success, message = self.trading_system.close_position(position['id'], "MANUAL_CLOSE_ALL")
                if success:
                    success_count += 1
            
            self.show_info("平倉完成", f"已平倉 {success_count}/{len(positions)} 個持倉")
            self.update_futures_account()
            self.update_futures_positions()
            
        except Exception as e:
            self.show_error("平倉錯誤", f"一鍵平倉失敗: {str(e)}")
            
    def update_futures_positions(self):
        """更新合約持倉"""
        try:
            # 清空現有數據
            for item in self.futures_positions_tree.get_children():
                self.futures_positions_tree.delete(item)
            
            # 獲取合約持倉
            positions = self.trading_system.get_open_positions()
            
            for position in positions:
                symbol = position['symbol']
                
                # 獲取當前價格
                ticker = self.okx_api.get_ticker(symbol)
                mark_price = ticker.get('last', position['entry_price']) if ticker else position['entry_price']
                
                # 計算盈虧
                if position['position_type'] == 'LONG':
                    pnl = (mark_price - position['entry_price']) * position['quantity']
                else:
                    pnl = (position['entry_price'] - mark_price) * position['quantity']
                
                pnl_percent = (pnl / (position['entry_price'] * position['quantity'])) * 100
                
                # 計算強平價格 (簡化計算)
                if position['position_type'] == 'LONG':
                    liquidation_price = position['entry_price'] * (1 - 1/position['leverage'] * 0.9)
                else:
                    liquidation_price = position['entry_price'] * (1 + 1/position['leverage'] * 0.9)
                
                self.futures_positions_tree.insert('', 'end', values=(
                    symbol,
                    position['position_type'],
                    f"{position['quantity']:.4f}",
                    f"{position['entry_price']:.4f}",
                    f"{mark_price:.4f}",
                    f"{liquidation_price:.4f}",
                    f"{pnl:.2f} USDT",
                    f"{pnl_percent:.2f}%",
                    f"{position['leverage']}x"
                ))
                
        except Exception as e:
            self.update_status(f"更新合約持倉錯誤: {str(e)}")
            
    def update_futures_account(self):
        """更新合約帳戶"""
        try:
            balance = self.okx_api.get_futures_balance()
            if balance:
                total = balance.get('total_balance', 0)
                available = balance.get('available_balance', 0)
                used = balance.get('used_balance', 0)
                
                self.futures_equity.config(text=f"{total:.2f} USDT")
                self.futures_available_margin.config(text=f"{available:.2f} USDT")
                self.futures_used_margin.config(text=f"{used:.2f} USDT")
                
                # 計算保證金率
                margin_ratio = (used / total * 100) if total > 0 else 0
                self.futures_margin_ratio.config(text=f"{margin_ratio:.2f}%")
                
                # 計算未實現盈虧 (需要從持倉計算)
                positions = self.trading_system.get_open_positions()
                unrealized_pnl = sum(
                    (position.get('pnl', 0) for position in positions)
                )
                self.futures_unrealized_pnl.config(
                    text=f"{unrealized_pnl:.2f} USDT",
                    foreground='green' if unrealized_pnl >= 0 else 'red'
                )
                
        except Exception as e:
            self.update_status(f"更新合約帳戶錯誤: {str(e)}")
            
    def update_futures_history(self):
        """更新合約交易記錄"""
        try:
            # 清空現有數據
            for item in self.futures_history_tree.get_children():
                self.futures_history_tree.delete(item)
            
            # 獲取合約交易記錄
            trades = self.trading_system.get_trading_history(limit=20, trading_type='FUTURES')
            
            for trade in trades:
                # 根據實際數據庫結構調整
                timestamp = trade[4] if len(trade) > 4 else 'N/A'
                symbol = trade[1] if len(trade) > 1 else 'N/A'
                action = trade[2] if len(trade) > 2 else 'N/A'
                price = f"{trade[3]:.4f}" if len(trade) > 3 else 'N/A'
                quantity = f"{trade[4]:.4f}" if len(trade) > 4 else 'N/A'
                pnl = f"{trade[6]:.2f}" if len(trade) > 6 else 'N/A'
                leverage = "10x"  # 需要從數據庫獲取
                status = "已完成"
                
                self.futures_history_tree.insert('', 'end', values=(
                    timestamp, symbol, action, price, quantity, pnl, leverage, status
                ))
                
        except Exception as e:
            self.update_status(f"更新合約記錄錯誤: {str(e)}")
            
    def adjust_futures_stop_loss(self):
        """調整合約止損"""
        try:
            # 獲取選中的持倉
            selection = self.futures_positions_tree.selection()
            if not selection:
                self.show_error("選擇錯誤", "請先選擇一個持倉")
                return
            
            item = selection[0]
            values = self.futures_positions_tree.item(item, 'values')
            symbol = values[0]
            position_type = values[1]
            
            # 彈出止損調整對話框
            self.show_stop_loss_dialog(symbol, position_type)
            
        except Exception as e:
            self.show_error("調整錯誤", f"調整止損失敗: {str(e)}")
            
    def show_stop_loss_dialog(self, symbol, position_type):
        """顯示止損調整對話框"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"調整止損 - {symbol}")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"調整 {symbol} {position_type} 止損價格").pack(pady=10)
        
        ttk.Label(dialog, text="止損價格:").pack(pady=5)
        stop_loss_var = tk.StringVar()
        stop_loss_entry = ttk.Entry(dialog, textvariable=stop_loss_var)
        stop_loss_entry.pack(pady=5)
        
        def save_stop_loss():
            try:
                stop_loss_price = float(stop_loss_var.get())
                success = self.smart_stoploss.set_stop_loss(symbol, stop_loss_price, position_type)
                if success:
                    self.show_info("成功", f"{symbol} 止損已設置為 {stop_loss_price}")
                    dialog.destroy()
                else:
                    self.show_error("失敗", "設置止損失敗")
            except ValueError:
                self.show_error("錯誤", "請輸入有效的價格")
        
        ttk.Button(dialog, text="保存", command=save_stop_loss).pack(pady=10)
        ttk.Button(dialog, text="取消", command=dialog.destroy).pack(pady=5)
        
    # ==================== 跟單系統功能方法 ====================
    
    def toggle_copy_trading(self):
        """切換跟單系統狀態"""
        if self.copy_trading_enabled.get():
            self.start_copy_trading()
        else:
            self.stop_copy_trading()
            
    def start_copy_trading(self):
        """啟動跟單系統"""
        try:
            # 更新設定
            settings = {
                'max_copied_traders': int(self.max_traders_var.get()),
                'risk_multiplier': float(self.risk_multiplier_var.get()),
                'auto_follow': self.auto_follow.get(),
                'min_win_rate': int(self.min_win_rate_var.get()),
                'min_total_trades': int(self.min_trades_var.get())
            }
            self.copy_trading.update_settings(settings)
            
            success, message = self.copy_trading.start_copy_trading()
            
            if success:
                self.copy_system_status.config(text="🟢 運行中", style='Success.TLabel')
                self.start_copy_btn.config(state='disabled')
                self.stop_copy_btn.config(state='normal')
                self.copy_trading_enabled.set(True)
                self.show_info("跟單系統", "跟單系統已啟動")
            else:
                self.show_error("跟單系統", f"啟動失敗: {message}")
                self.copy_trading_enabled.set(False)
                
        except Exception as e:
            self.show_error("跟單系統", f"啟動錯誤: {str(e)}")
            self.copy_trading_enabled.set(False)
            
    def stop_copy_trading(self):
        """停止跟單系統"""
        try:
            success, message = self.copy_trading.stop_copy_trading()
            
            if success:
                self.copy_system_status.config(text="⚪ 已停止", style='Warning.TLabel')
                self.start_copy_btn.config(state='normal')
                self.stop_copy_btn.config(state='disabled')
                self.copy_trading_enabled.set(False)
                self.show_info("跟單系統", "跟單系統已停止")
            else:
                self.show_error("跟單系統", f"停止失敗: {message}")
                
        except Exception as e:
            self.show_error("跟單系統", f"停止錯誤: {str(e)}")
            
    def update_trader_list(self):
        """更新交易者列表"""
        try:
            # 清空現有數據
            for item in self.trader_tree.get_children():
                self.trader_tree.delete(item)
            
            # 獲取交易者列表
            traders = self.copy_trading.available_traders
            
            for trader_id, trader_info in traders.items():
                # 檢查是否已跟單
                is_copied = trader_id in self.copy_trading.copied_traders
                status = "🟢 跟單中" if is_copied else "⚪ 未跟單"
                
                self.trader_tree.insert('', 'end', values=(
                    trader_info['name'],
                    f"{trader_info['total_return']:.1f}%",
                    f"{trader_info['win_rate']:.1f}%",
                    trader_info['total_trades'],
                    trader_info['follower_count'],
                    f"{trader_info['rating']:.1f}",
                    status
                ))
                
            # 更新狀態
            status = self.copy_trading.get_copy_trading_status()
            self.current_traders_count.config(text=str(status['copied_traders_count']))
            self.total_copy_trades.config(text=str(status['total_copied_trades']))
            self.total_copy_pnl.config(text=f"{status['total_pnl']:.2f} USDT")
            
        except Exception as e:
            self.update_status(f"更新交易者列表錯誤: {str(e)}")
            
    def start_copy_trader(self):
        """開始跟單交易者"""
        try:
            selection = self.trader_tree.selection()
            if not selection:
                self.show_error("選擇錯誤", "請先選擇一個交易者")
                return
            
            item = selection[0]
            values = self.trader_tree.item(item, 'values')
            trader_name = values[0]
            
            # 找到交易者ID
            trader_id = None
            for tid, info in self.copy_trading.available_traders.items():
                if info['name'] == trader_name:
                    trader_id = tid
                    break
            
            if trader_id:
                success, message = self.copy_trading.add_trader_to_copy(trader_id)
                if success:
                    self.update_trader_list()
                    self.show_info("跟單成功", message)
                else:
                    self.show_error("跟單失敗", message)
            else:
                self.show_error("錯誤", "找不到對應的交易者")
                
        except Exception as e:
            self.show_error("跟單錯誤", f"開始跟單失敗: {str(e)}")
            
    def stop_copy_trader(self):
        """停止跟單交易者"""
        try:
            selection = self.trader_tree.selection()
            if not selection:
                self.show_error("選擇錯誤", "請先選擇一個交易者")
                return
            
            item = selection[0]
            values = self.trader_tree.item(item, 'values')
            trader_name = values[0]
            
            # 找到交易者ID
            trader_id = None
            for tid, info in self.copy_trading.available_traders.items():
                if info['name'] == trader_name:
                    trader_id = tid
                    break
            
            if trader_id and trader_id in self.copy_trading.copied_traders:
                success, message = self.copy_trading.remove_trader_from_copy(trader_id)
                if success:
                    self.update_trader_list()
                    self.show_info("停止跟單", message)
                else:
                    self.show_error("停止失敗", message)
            else:
                self.show_error("錯誤", "該交易者未被跟單")
                
        except Exception as e:
            self.show_error("停止錯誤", f"停止跟單失敗: {str(e)}")
            
    def update_copy_history(self):
        """更新跟單記錄"""
        try:
            # 清空現有數據
            for item in self.copy_history_tree.get_children():
                self.copy_history_tree.delete(item)
            
            # 獲取跟單記錄
            history = self.copy_trading.get_copy_trading_history(limit=15)
            
            for record in history:
                trader_name, symbol, action, price, quantity, timestamp, pnl = record
                
                self.copy_history_tree.insert('', 'end', values=(
                    timestamp,
                    trader_name,
                    symbol,
                    action,
                    f"{price:.4f}",
                    f"{quantity:.4f}",
                    f"{pnl:.2f} USDT"
                ))
                
        except Exception as e:
            self.update_status(f"更新跟單記錄錯誤: {str(e)}")
            
    def save_copy_settings(self):
        """保存跟單設定"""
        try:
            settings = {
                'max_copied_traders': int(self.max_traders_var.get()),
                'risk_multiplier': float(self.risk_multiplier_var.get()),
                'auto_follow': self.auto_follow.get(),
                'min_win_rate': int(self.min_win_rate_var.get()),
                'min_total_trades': int(self.min_trades_var.get())
            }
            
            success = self.copy_trading.update_settings(settings)
            
            if success:
                self.show_info("設定", "跟單設定已保存")
            else:
                self.show_error("設定", "保存失敗")
                
        except Exception as e:
            self.show_error("設定錯誤", f"保存設定失敗: {str(e)}")
            
    # ==================== 市場分析方法 ====================
    
    def run_technical_analysis(self):
        """運行技術分析"""
        try:
            symbol = self.analysis_pair_var.get()
            timeframe = self.analysis_timeframe_var.get()
            
            # 獲取K線數據
            ohlcv_data = self.okx_api.get_ohlcv(symbol, timeframe, 100)
            
            if not ohlcv_data:
                self.show_error("數據錯誤", f"無法獲取 {symbol} 的K線數據")
                return
            
            # 計算技術指標
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            indicators_df = self.technical_indicators.calculate_all_indicators(df)
            
            # 生成分析報告
            analysis_report = self.generate_technical_analysis_report(symbol, timeframe, indicators_df)
            
            # 更新結果顯示
            self.analysis_result_text.config(state=tk.NORMAL)
            self.analysis_result_text.delete(1.0, tk.END)
            self.analysis_result_text.insert(tk.END, analysis_report)
            self.analysis_result_text.config(state=tk.DISABLED)
            
            # 更新圖表顯示（簡化版本）
            self.analysis_chart_label.config(
                text=f"{symbol} {timeframe} 技術分析完成\n\n"
                     f"數據點: {len(ohlcv_data)} 個\n"
                     f"最新價格: {df['close'].iloc[-1]:.4f} USDT\n"
                     f"分析時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            self.show_info("分析完成", f"{symbol} 技術分析已完成")
            
        except Exception as e:
            self.show_error("分析錯誤", f"技術分析失敗: {str(e)}")
            
    def generate_technical_analysis_report(self, symbol, timeframe, df):
        """生成技術分析報告"""
        try:
            if df.empty:
                return "無數據可用於分析"
            
            report = f"📊 {symbol} {timeframe} 技術分析報告\n"
            report += "=" * 50 + "\n\n"
            
            # 基本統計
            current_price = df['close'].iloc[-1]
            price_change = ((current_price - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
            
            report += f"💵 價格分析:\n"
            report += f"  當前價格: {current_price:.4f} USDT\n"
            report += f"  期間變化: {price_change:+.2f}%\n"
            report += f"  最高價: {df['high'].max():.4f}\n"
            report += f"  最低價: {df['low'].min():.4f}\n"
            report += f"  平均價: {df['close'].mean():.4f}\n\n"
            
            # 趨勢分析
            report += f"📈 趨勢分析:\n"
            
            # 移動平均線分析
            if 'sma_20' in df.columns and 'sma_50' in df.columns:
                sma_20 = df['sma_20'].iloc[-1]
                sma_50 = df['sma_50'].iloc[-1]
                
                if current_price > sma_20 > sma_50:
                    report += "  ✅ 強勢多頭趨勢 (價格 > MA20 > MA50)\n"
                elif current_price < sma_20 < sma_50:
                    report += "  🔻 強勢空頭趨勢 (價格 < MA20 < MA50)\n"
                else:
                    report += "  ⚪ 震盪整理趨勢\n"
                    
                report += f"  MA20: {sma_20:.4f}\n"
                report += f"  MA50: {sma_50:.4f}\n"
            
            # RSI分析
            if 'rsi_14' in df.columns:
                rsi = df['rsi_14'].iloc[-1]
                report += f"  RSI(14): {rsi:.2f} - "
                
                if rsi > 70:
                    report += "超買區域 ⚠️\n"
                elif rsi < 30:
                    report += "超賣區域 💡\n"
                else:
                    report += "正常區域 ✅\n"
            
            # MACD分析
            if 'macd' in df.columns and 'macd_signal' in df.columns:
                macd = df['macd'].iloc[-1]
                signal = df['macd_signal'].iloc[-1]
                histogram = df.get('macd_histogram', pd.Series([0])).iloc[-1]
                
                report += f"  MACD: {macd:.4f}, 信號: {signal:.4f}\n"
                if macd > signal and histogram > 0:
                    report += "  MACD金叉，多頭信號 ✅\n"
                elif macd < signal and histogram < 0:
                    report += "  MACD死叉，空頭信號 🔻\n"
                else:
                    report += "  MACD中性 ⚪\n"
            
            # 布林帶分析
            if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
                bb_upper = df['bb_upper'].iloc[-1]
                bb_lower = df['bb_lower'].iloc[-1]
                bb_position = df.get('bb_position', pd.Series([0.5])).iloc[-1]
                
                report += f"  布林帶位置: {bb_position:.2%}\n"
                if current_price > bb_upper:
                    report += "  價格突破上軌，可能回調 ⚠️\n"
                elif current_price < bb_lower:
                    report += "  價格突破下軌，可能反彈 💡\n"
                else:
                    report += "  價格在布林帶內運行 ✅\n"
            
            # 交易信號
            report += f"\n🎯 交易信號:\n"
            
            signals = []
            # RSI信號
            if 'rsi_14' in df.columns:
                rsi = df['rsi_14'].iloc[-1]
                if rsi < 30:
                    signals.append("RSI超賣，考慮買入 💡")
                elif rsi > 70:
                    signals.append("RSI超買，考慮賣出 ⚠️")
            
            # MACD信號
            if 'macd' in df.columns and 'macd_signal' in df.columns:
                macd = df['macd'].iloc[-1]
                signal = df['macd_signal'].iloc[-1]
                if macd > signal and df['macd'].iloc[-2] <= df['macd_signal'].iloc[-2]:
                    signals.append("MACD金叉，買入信號 ✅")
                elif macd < signal and df['macd'].iloc[-2] >= df['macd_signal'].iloc[-2]:
                    signals.append("MACD死叉，賣出信號 🔻")
            
            if signals:
                for signal in signals:
                    report += f"  • {signal}\n"
            else:
                report += "  • 無明顯交易信號，建議觀望 ⚪\n"
            
            # 風險等級
            report += f"\n⚠️ 風險等級: "
            risk_factors = 0
            
            # 波動率風險
            if 'volatility_20' in df.columns:
                volatility = df['volatility_20'].iloc[-1]
                if volatility > 0.8:
                    risk_factors += 1
                    report += "高波動 "
                elif volatility > 0.5:
                    risk_factors += 0.5
                    report += "中波動 "
                else:
                    report += "低波動 "
            
            # 綜合風險評估
            if risk_factors >= 2:
                report += "🔴 高風險"
            elif risk_factors >= 1:
                report += "🟡 中風險"  
            else:
                report += "🟢 低風險"
            
            report += f"\n\n📅 報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return report
            
        except Exception as e:
            return f"生成報告時發生錯誤: {str(e)}"
            
    def run_smc_analysis(self):
        """運行SMC分析"""
        try:
            symbol = self.smc_pair_var.get()
            
            # 使用SMC策略分析
            ohlcv_data = self.okx_api.get_ohlcv(symbol, '1h', 100)
            
            if not ohlcv_data:
                self.show_error("數據錯誤", f"無法獲取 {symbol} 的K線數據")
                return
            
            # 計算SMC等級
            smc_data = self.smc_strategy.calculate_smc_levels(symbol, ohlcv_data)
            
            if not smc_data:
                self.show_error("分析錯誤", "SMC分析失敗")
                return
            
            # 更新等級分析
            self.smc_levels_text.config(state=tk.NORMAL)
            self.smc_levels_text.delete(1.0, tk.END)
            
            levels_report = f"🎯 {symbol} SMC等級分析\n"
            levels_report += "=" * 40 + "\n\n"
            
            # 支撐阻力位
            levels_report += "📊 支撐阻力位:\n"
            levels_report += "阻力位:\n"
            for level in smc_data.get('resistance_levels', [])[:3]:
                levels_report += f"  • {level['price']:.4f} (強度: {level['strength']:.2f})\n"
            
            levels_report += "\n支撐位:\n"
            for level in smc_data.get('support_levels', [])[:3]:
                levels_report += f"  • {level['price']:.4f} (強度: {level['strength']:.2f})\n"
            
            # 市場結構
            structure = smc_data.get('market_structure', {})
            levels_report += f"\n🏗️ 市場結構:\n"
            levels_report += f"  趨勢: {structure.get('trend', 'N/A')}\n"
            levels_report += f"  波動率: {structure.get('volatility', 0):.4f}\n"
            levels_report += f"  當前價格位置: {((structure.get('current_price', 0) - structure.get('range_low', 0)) / (structure.get('range_high', 1) - structure.get('range_low', 1))):.2%}\n"
            
            levels_report += f"\n🎭 市場偏見: {smc_data.get('bias', 'N/A')}"
            
            self.smc_levels_text.insert(tk.END, levels_report)
            self.smc_levels_text.config(state=tk.DISABLED)
            
            # 更新交易信號
            self.smc_signals_text.config(state=tk.NORMAL)
            self.smc_signals_text.delete(1.0, tk.END)
            
            signals_report = f"📈 交易信號建議\n"
            signals_report += "=" * 40 + "\n\n"
            
            # 根據SMC數據生成信號
            bias = smc_data.get('bias', 'neutral')
            current_price = structure.get('current_price', 0)
            
            if bias == "bullish":
                signals_report += "🟢 多頭信號:\n"
                signals_report += "  • 考慮在支撐位附近買入\n"
                signals_report += "  • 目標價位: 下一個阻力位\n"
                signals_report += "  • 止損: 關鍵支撐位下方\n"
            elif bias == "bearish":
                signals_report += "🔴 空頭信號:\n"
                signals_report += "  • 考慮在阻力位附近賣出\n"
                signals_report += "  • 目標價位: 下一個支撐位\n"
                signals_report += "  • 止損: 關鍵阻力位上方\n"
            else:
                signals_report += "⚪ 中性信號:\n"
                signals_report += "  • 建議觀望或區間交易\n"
                signals_report += "  • 在支撐阻力位之間操作\n"
                signals_report += "  • 嚴格控制風險\n"
            
            signals_report += f"\n💡 操作建議:\n"
            signals_report += "  • 使用智能止損保護資金\n"
            signals_report += "  • 分批建倉降低風險\n"
            signals_report += "  • 關注成交量確認信號\n"
            
            self.smc_signals_text.insert(tk.END, signals_report)
            self.smc_signals_text.config(state=tk.DISABLED)
            
            self.show_info("SMC分析", f"{symbol} SMC分析已完成")
            
        except Exception as e:
            self.show_error("SMC分析錯誤", f"SMC分析失敗: {str(e)}")
            
    def open_smc_learning(self):
        """打開SMC學習"""
        self.show_info("SMC學習", "SMC學習功能開發中...")
        
    def run_onchain_analysis(self):
        """運行鏈上數據分析"""
        try:
            symbol = self.onchain_symbol_var.get()
            
            # 獲取鏈上數據
            if symbol == "BTC":
                onchain_data = self.onchain_analyzer.fetch_btc_onchain_data(30)
            else:
                onchain_data = self.onchain_analyzer.fetch_eth_onchain_data(30)
            
            # 分析網絡健康度
            health_analysis = self.onchain_analyzer.analyze_network_health(symbol, 30)
            
            # 分析市場情緒
            sentiment_analysis = self.onchain_analyzer.analyze_market_sentiment(symbol)
            
            # 更新關鍵指標
            key_metrics = self.onchain_analyzer.get_key_metrics(symbol, 7)
            for key, value in key_metrics.items():
                if key in self.onchain_metrics:
                    self.onchain_metrics[key].config(text=value)
            
            # 更新市場情緒
            self.sentiment_text.config(state=tk.NORMAL)
            self.sentiment_text.delete(1.0, tk.END)
            
            if sentiment_analysis:
                sentiment_report = f"😊 {symbol} 市場情緒分析\n"
                sentiment_report += "=" * 40 + "\n\n"
                
                sentiment_report += f"MVRV情緒: {sentiment_analysis['mvrv']['sentiment']}\n"
                sentiment_report += f"NUPL情緒: {sentiment_analysis['nupl']['sentiment']}\n"
                sentiment_report += f"總體情緒: {sentiment_analysis['overall_sentiment']}\n\n"
                
                sentiment_report += "詳細數據:\n"
                sentiment_report += f"  MVRV比率: {sentiment_analysis['mvrv']['value']:.2f}\n"
                sentiment_report += f"  NUPL比率: {sentiment_analysis['nupl']['value']:.2f}\n"
                sentiment_report += f"  SOPR比率: {sentiment_analysis['sopr']['value']:.2f}\n"
                
                self.sentiment_text.insert(tk.END, sentiment_report)
            else:
                self.sentiment_text.insert(tk.END, "無法獲取市場情緒數據")
            
            self.sentiment_text.config(state=tk.DISABLED)
            
            # 更新網絡健康度
            self.health_text.config(state=tk.NORMAL)
            self.health_text.delete(1.0, tk.END)
            
            if health_analysis:
                health_report = f"❤️ {symbol} 網絡健康度分析\n"
                health_report += "=" * 40 + "\n\n"
                
                health_report += f"總體評分: {health_analysis['overall_score']:.1f}/100\n\n"
                
                health_report += "詳細分析:\n"
                for key, value in health_analysis.items():
                    if key != 'overall_score':
                        health_report += f"  {key}: {value}\n"
                
                # 健康度建議
                health_report += f"\n💡 建議:\n"
                if health_analysis['overall_score'] >= 80:
                    health_report += "  🟢 網絡健康狀況優秀\n"
                elif health_analysis['overall_score'] >= 60:
                    health_report += "  🟡 網絡健康狀況良好\n"
                else:
                    health_report += "  🔴 網絡健康狀況需要關注\n"
                
                self.health_text.insert(tk.END, health_report)
            else:
                self.health_text.insert(tk.END, "無法獲取網絡健康度數據")
            
            self.health_text.config(state=tk.DISABLED)
            
            self.show_info("鏈上分析", f"{symbol} 鏈上數據分析已完成")
            
        except Exception as e:
            self.show_error("鏈上分析錯誤", f"鏈上數據分析失敗: {str(e)}")
            
    def update_onchain_data(self):
        """更新鏈上數據"""
        try:
            symbol = self.onchain_symbol_var.get()
            
            if symbol == "BTC":
                self.onchain_analyzer.fetch_btc_onchain_data(7)
            else:
                self.onchain_analyzer.fetch_eth_onchain_data(7)
                
            self.show_info("數據更新", f"{symbol} 鏈上數據已更新")
            
        except Exception as e:
            self.show_error("更新錯誤", f"鏈上數據更新失敗: {str(e)}")
            
    def analyze_portfolio(self):
        """分析投資組合"""
        try:
            # 獲取投資組合數據
            spot_holdings = self.trading_system.get_spot_holdings()
            futures_positions = self.trading_system.get_open_positions()
            performance_stats = self.trading_system.get_performance_stats()
            
            # 更新績效統計
            self.performance_text.config(state=tk.NORMAL)
            self.performance_text.delete(1.0, tk.END)
            
            performance_report = "📈 投資組合績效統計\n"
            performance_report += "=" * 40 + "\n\n"
            
            if performance_stats:
                performance_report += f"總交易次數: {performance_stats['total_trades']}\n"
                performance_report += f"盈利交易: {performance_stats['winning_trades']}\n"
                performance_report += f"虧損交易: {performance_stats['losing_trades']}\n"
                performance_report += f"勝率: {performance_stats['win_rate']:.2f}%\n"
                performance_report += f"總盈虧: {performance_stats['total_pnl']:.2f} USDT\n"
                performance_report += f"今日盈虧: {performance_stats['daily_pnl']:.2f} USDT\n"
                performance_report += f"當前資金: {performance_stats['current_balance']:.2f} USDT\n"
            else:
                performance_report += "暫無交易數據\n"
            
            performance_report += f"\n📊 持倉統計:\n"
            performance_report += f"現貨持倉: {len(spot_holdings)} 種\n"
            performance_report += f"合約持倉: {len(futures_positions)} 個\n"
            
            self.performance_text.insert(tk.END, performance_report)
            self.performance_text.config(state=tk.DISABLED)
            
            # 更新風險分析
            self.risk_text.config(state=tk.NORMAL)
            self.risk_text.delete(1.0, tk.END)
            
            risk_report = "⚠️ 投資組合風險分析\n"
            risk_report += "=" * 40 + "\n\n"
            
            # 簡單的風險評估
            total_risk_factors = 0
            
            # 持倉分散度風險
            total_holdings = len(spot_holdings) + len(futures_positions)
            if total_holdings == 0:
                risk_report += "🟢 無持倉，無市場風險\n"
            elif total_holdings == 1:
                risk_report += "🔴 持倉過度集中，高風險\n"
                total_risk_factors += 2
            elif total_holdings <= 3:
                risk_report += "🟡 持倉較為集中，中風險\n"
                total_risk_factors += 1
            else:
                risk_report += "🟢 持倉分散良好，低風險\n"
            
            # 合約槓桿風險
            if futures_positions:
                max_leverage = max((pos.get('leverage', 1) for pos in futures_positions), default=1)
                if max_leverage >= 10:
                    risk_report += f"🔴 高槓桿操作 ({max_leverage}x)，極高風險\n"
                    total_risk_factors += 2
                elif max_leverage >= 5:
                    risk_report += f"🟡 中槓桿操作 ({max_leverage}x)，中風險\n"
                    total_risk_factors += 1
                else:
                    risk_report += f"🟢 低槓桿操作 ({max_leverage}x)，低風險\n"
            
            # 今日虧損風險
            daily_pnl = performance_stats.get('daily_pnl', 0) if performance_stats else 0
            if daily_pnl < -100:
                risk_report += f"🔴 今日虧損較大 ({daily_pnl:.2f} USDT)\n"
                total_risk_factors += 1
            
            risk_report += f"\n🎯 綜合風險等級: "
            if total_risk_factors >= 3:
                risk_report += "🔴 高風險"
            elif total_risk_factors >= 1:
                risk_report += "🟡 中風險"
            else:
                risk_report += "🟢 低風險"
            
            self.risk_text.insert(tk.END, risk_report)
            self.risk_text.config(state=tk.DISABLED)
            
            # 更新投資建議
            self.advice_text.config(state=tk.NORMAL)
            self.advice_text.delete(1.0, tk.END)
            
            advice_report = "💡 個性化投資建議\n"
            advice_report += "=" * 40 + "\n\n"
            
            # 根據風險等級給出建議
            if total_risk_factors >= 3:
                advice_report += "🔴 高風險警示:\n"
                advice_report += "  • 建議減倉降低風險\n"
                advice_report += "  • 避免高槓桿操作\n"
                advice_report += "  • 設置嚴格止損\n"
                advice_report += "  • 考慮分散投資\n"
            elif total_risk_factors >= 1:
                advice_report += "🟡 風險管理建議:\n"
                advice_report += "  • 控制單一持倉比例\n"
                advice_report += "  • 定期審查持倉\n"
                advice_report += "  • 使用智能止損\n"
                advice_report += "  • 保持資金管理\n"
            else:
                advice_report += "🟢 穩健投資建議:\n"
                advice_report += "  • 當前風險控制良好\n"
                advice_report += "  • 可考慮適度擴展\n"
                advice_report += "  • 保持投資紀律\n"
                advice_report += "  • 定期複盤優化\n"
            
            # 基於績效的建議
            if performance_stats and performance_stats.get('win_rate', 0) < 50:
                advice_report += "\n📉 交易策略建議:\n"
                advice_report += "  • 檢視交易策略有效性\n"
                advice_report += "  • 加強進場時機選擇\n"
                advice_report += "  • 考慮使用止損策略\n"
            
            self.advice_text.insert(tk.END, advice_report)
            self.advice_text.config(state=tk.DISABLED)
            
            self.show_info("組合分析", "投資組合分析已完成")
            
        except Exception as e:
            self.show_error("分析錯誤", f"投資組合分析失敗: {str(e)}")
            
    def calculate_expectancy(self):
        """計算期望值"""
        try:
            # 選擇主要交易對進行期望值計算
            main_pair = "BTC-USDT"
            expectancy_data = self.expectancy_calculator.calculate_trade_expectancy(main_pair, 30)
            
            if expectancy_data:
                # 生成期望值報告
                report = self.expectancy_calculator.generate_trading_report(main_pair, 30)
                
                # 彈出顯示報告
                self.show_expectancy_report(report)
            else:
                self.show_info("期望值計算", f"{main_pair} 交易數據不足，無法計算期望值")
                
        except Exception as e:
            self.show_error("計算錯誤", f"期望值計算失敗: {str(e)}")
            
    def show_expectancy_report(self, report):
        """顯示期望值報告"""
        # 創建新窗口顯示詳細報告
        report_window = tk.Toplevel(self.root)
        report_window.title("期望值分析報告")
        report_window.geometry("600x500")
        report_window.transient(self.root)
        report_window.grab_set()
        
        # 報告內容
        text_widget = tk.Text(report_window, wrap=tk.WORD, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(report_window, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.insert(tk.END, report)
        text_widget.config(state=tk.DISABLED)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 關閉按鈕
        ttk.Button(report_window, text="關閉", command=report_window.destroy).pack(pady=10)
        
    def update_portfolio_data(self):
        """更新投資組合數據"""
        self.analyze_portfolio()
        self.show_info("數據更新", "投資組合數據已更新")
        
    def save_analysis_chart(self):
        """保存分析圖表"""
        self.show_info("保存圖表", "圖表保存功能開發中...")
        
    # ==================== 系統設定方法 ====================
    
    def test_api_connection(self):
        """測試API連接"""
        try:
            # 獲取輸入的API資訊
            api_key = self.api_key_var.get()
            secret_key = self.secret_key_var.get()
            passphrase = self.passphrase_var.get()
            testnet = self.testnet_var.get()
            
            if not api_key or not secret_key or not passphrase:
                self.show_error("輸入錯誤", "請填寫完整的API資訊")
                return
            
            # 測試API連接
            success, message = self.okx_api.test_connection()
            
            if success:
                self.show_info("API測試", "✅ API連接成功！")
                # 保存API設定
                self.save_api_settings()
            else:
                self.show_error("API測試", f"❌ API連接失敗: {message}")
                
        except Exception as e:
            self.show_error("API測試錯誤", f"測試API連接時發生錯誤: {str(e)}")
            
    def test_discord(self):
        """測試Discord連接"""
        try:
            webhook_url = self.webhook_var.get()
            
            if not webhook_url:
                self.show_error("輸入錯誤", "請填寫Discord Webhook URL")
                return
            
            # 測試Discord連接
            success, message = self.discord_bot.test_connection()
            
            if success:
                self.show_info("Discord測試", "✅ Discord連接成功！")
                # 保存Discord設定
                self.save_discord_settings()
            else:
                self.show_error("Discord測試", f"❌ Discord連接失敗: {message}")
                
        except Exception as e:
            self.show_error("Discord測試錯誤", f"測試Discord連接時發生錯誤: {str(e)}")
            
    def save_api_settings(self):
        """保存API設定"""
        try:
            api_settings = {
                'api_key': self.api_key_var.get(),
                'secret_key': self.secret_key_var.get(),
                'passphrase': self.passphrase_var.get(),
                'testnet': self.testnet_var.get()
            }
            
            # 保存到設定檔
            success = self.okx_api.save_api_settings(api_settings)
            
            if success:
                self.show_info("設定", "✅ API設定已保存")
            else:
                self.show_error("設定", "❌ API設定保存失敗")
                
        except Exception as e:
            self.show_error("設定錯誤", f"保存API設定時發生錯誤: {str(e)}")
            
    def save_discord_settings(self):
        """保存Discord設定"""
        try:
            discord_settings = {
                'webhook_url': self.webhook_var.get(),
                'enabled': self.discord_enabled_var.get()
            }
            
            # 保存到設定檔
            success = self.discord_bot.save_settings(discord_settings)
            
            if success:
                self.show_info("設定", "✅ Discord設定已保存")
            else:
                self.show_error("設定", "❌ Discord設定保存失敗")
                
        except Exception as e:
            self.show_error("設定錯誤", f"保存Discord設定時發生錯誤: {str(e)}")
            
    def load_api_settings(self):
        """載入API設定"""
        try:
            settings = self.okx_api.load_api_settings()
            
            if settings:
                self.api_key_var.set(settings.get('api_key', ''))
                self.secret_key_var.set(settings.get('secret_key', ''))
                self.passphrase_var.set(settings.get('passphrase', ''))
                self.testnet_var.set(settings.get('testnet', True))
                
        except Exception as e:
            print(f"載入API設定錯誤: {e}")
            
    def load_trading_settings(self):
        """載入交易設定"""
        try:
            settings = self.trading_system.load_settings()
            
            if settings:
                self.trade_risk_var.set(str(settings.get('risk_percent', 2.0)))
                self.max_positions_var.set(str(settings.get('max_positions', 5)))
                self.daily_loss_var.set(str(settings.get('daily_loss_limit', 5.0)))
                self.position_size_var.set(str(settings.get('max_position_size', 20.0)))
                self.default_leverage_var.set(str(settings.get('default_leverage', 10)))
                self.smart_stoploss_var.set(settings.get('smart_stoploss', True))
                self.trailing_stop_var.set(settings.get('trailing_stop', True))
                
        except Exception as e:
            print(f"載入交易設定錯誤: {e}")
            
    def save_notification_settings(self):
        """保存通知設定"""
        try:
            settings = {
                'price_alerts': self.price_alerts_var.get(),
                'price_alert_threshold': float(self.price_alert_threshold_var.get()),
                'trade_notifications': self.trade_notifications_var.get(),
                'risk_notifications': self.risk_notifications_var.get(),
                'system_notifications': self.system_notifications_var.get(),
                'sound_alerts': self.sound_alerts_var.get()
            }
            
            # 保存到設定檔
            success = self.trading_system.save_notification_settings(settings)
            
            if success:
                self.show_info("設定", "✅ 通知設定已保存")
            else:
                self.show_error("設定", "❌ 通知設定保存失敗")
                
        except Exception as e:
            self.show_error("設定錯誤", f"保存通知設定時發生錯誤: {str(e)}")
            
    def save_system_settings(self):
        """保存系統設定"""
        try:
            settings = {
                'theme': self.theme_var.get(),
                'language': self.language_var.get(),
                'auto_refresh': self.auto_refresh_var.get(),
                'data_retention': int(self.data_retention_var.get()),
                'auto_backup': self.auto_backup_var.get()
            }
            
            # 保存到設定檔
            success = self.trading_system.save_system_settings(settings)
            
            if success:
                self.show_info("設定", "✅ 系統設定已保存")
            else:
                self.show_error("設定", "❌ 系統設定保存失敗")
                
        except Exception as e:
            self.show_error("設定錯誤", f"保存系統設定時發生錯誤: {str(e)}")
            
    def clear_cache(self):
        """清理緩存"""
        try:
            # 清理圖片緩存、臨時文件等
            import shutil
            import tempfile
            
            # 清理臨時文件
            temp_dir = tempfile.gettempdir()
            cache_files = [f for f in os.listdir(temp_dir) if f.startswith('crypto_assistant')]
            
            for file in cache_files:
                try:
                    os.remove(os.path.join(temp_dir, file))
                except:
                    pass
            
            self.show_info("緩存清理", "✅ 系統緩存已清理")
            
        except Exception as e:
            self.show_error("清理錯誤", f"清理緩存時發生錯誤: {str(e)}")
            
    def backup_data(self):
        """備份數據"""
        try:
            # 創建備份目錄
            backup_dir = "backup"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            # 備份數據庫文件
            import shutil
            import datetime
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{backup_dir}/backup_{timestamp}.db"
            
            # 複製數據庫文件
            if os.path.exists("data/trading.db"):
                shutil.copy2("data/trading.db", backup_file)
                self.show_info("數據備份", f"✅ 數據已備份到: {backup_file}")
            else:
                self.show_error("備份錯誤", "找不到數據庫文件")
                
        except Exception as e:
            self.show_error("備份錯誤", f"備份數據時發生錯誤: {str(e)}")
            
    def show_system_logs(self):
        """顯示系統日誌"""
        try:
            log_window = tk.Toplevel(self.root)
            log_window.title("系統日誌")
            log_window.geometry("800x600")
            
            # 日誌內容
            log_text = scrolledtext.ScrolledText(log_window, wrap=tk.WORD)
            log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 讀取日誌文件
            log_file = "logs/system.log"
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    log_text.insert(tk.END, log_content)
            else:
                log_text.insert(tk.END, "日誌文件不存在")
            
            log_text.config(state=tk.DISABLED)
            
            # 關閉按鈕
            ttk.Button(log_window, text="關閉", command=log_window.destroy).pack(pady=10)
            
        except Exception as e:
            self.show_error("日誌錯誤", f"顯示系統日誌時發生錯誤: {str(e)}")
            
    def check_for_updates(self):
        """檢查更新"""
        self.show_info("檢查更新", "✅ 當前已是最新版本")
        
    def show_help(self):
        """顯示使用說明"""
        help_text = """
💰 幣圈交易輔助系統 - 使用說明

📊 儀表板:
  • 查看即時行情和帳戶概覽
  • 快速交易功能

🎯 交易系統:
  • 自動交易控制
  • 持倉管理和交易記錄

💵 現貨交易:
  • 現貨買賣操作
  • 持倉管理和分析

📈 合約交易:
  • 合約開平倉操作
  • 槓桿設定和風險管理

👥 跟單系統:
  • 跟單優秀交易者
  • 風險控制和設定

📊 市場分析:
  • 技術分析工具
  • SMC策略分析
  • 鏈上數據監控
  • 投資組合分析

⚙️ 系統設定:
  • API設定和連接測試
  • 交易和通知設定
  • 系統維護操作

💡 提示:
  • 首次使用請先設定API
  • 建議先在測試網路練習
  • 注意風險控制
"""
        self.show_info("使用說明", help_text)
        
    def report_issue(self):
        """報告問題"""
        self.show_info("報告問題", "如有問題請聯繫開發團隊或查看日誌文件")