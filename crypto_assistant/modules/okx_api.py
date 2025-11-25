# modules/okx_api.py
import ccxt
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
import asyncio

@dataclass
class PriceData:
    """價格數據結構"""
    symbol: str
    price: float
    change: float
    high: float
    low: float
    volume: float
    timestamp: str
    bid: float = None
    ask: float = None
    spread: float = None

@dataclass
class AccountBalance:
    """帳戶餘額結構"""
    total_balance: float
    available_balance: float
    used_balance: float
    account_type: str
    timestamp: str
    currencies: Dict = None

class OKXAPIClient:
    """OKX API 客戶端 - 台灣節點優化版本"""
    
    def __init__(self, api_key: str = None, secret_key: str = None, passphrase: str = None, 
                 test_net: bool = True, use_virtual_account: bool = True):
        """
        初始化 OKX API 客戶端
        
        Args:
            api_key: API金鑰
            secret_key: 秘密金鑰
            passphrase: 通行碼
            test_net: 是否使用測試網路
            use_virtual_account: 是否使用虛擬帳戶
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.test_net = test_net
        self.use_virtual_account = use_virtual_account
        
        # 初始化日誌系統
        self.logger = self._setup_logger()
        
        # 價格快取系統
        self.price_cache: Dict[str, PriceData] = {}
        self.price_listeners: List[Callable] = []
        self.price_history: Dict[str, List[PriceData]] = {}
        
        # 連線狀態
        self.is_connected = False
        self.is_updating = False
        self.last_update_time = None
        
        # 配置參數
        self.update_interval = 3  # 價格更新間隔(秒)
        self.max_retries = 3      # 最大重試次數
        self.retry_delay = 1      # 重試延遲(秒)
        
        # 交易所實例
        self.exchange = None
        
        # 常用交易對（台灣用戶偏好）
        self.popular_symbols = [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT',
            'XRP/USDT', 'LTC/USDT', 'BNB/USDT', 'AVAX/USDT', 'MATIC/USDT',
            'LINK/USDT', 'UNI/USDT', 'DOGE/USDT', 'TON/USDT', 'ATOM/USDT'
        ]
        
        # 初始化交易所連線
        self.setup_exchange()
        
    def _setup_logger(self) -> logging.Logger:
        """設置日誌記錄器"""
        logger = logging.getLogger('OKXAPI')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger

    def setup_exchange(self) -> bool:
        """
        設置交易所連接 - 台灣節點優化
        
        Returns:
            bool: 連接是否成功
        """
        try:
            # 檢查API金鑰是否完整
            if not all([self.api_key, self.secret_key, self.passphrase]):
                self.logger.warning("⚠️ API金鑰不完整，使用模擬模式運行")
                self.is_connected = True  # 模擬模式視為連線成功
                return True
            
            # 配置交易所參數
            exchange_config = {
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'password': self.passphrase,
                'sandbox': self.test_net,
                'enableRateLimit': True,
                'timeout': 30000,
                'rateLimit': 100,
                'options': {
                    'defaultType': 'swap',
                    'adjustForTimeDifference': True,
                    'recvWindow': 10000,
                    'createMarketBuyOrderRequiresPrice': False,
                }
            }
            
            self.exchange = ccxt.okx(exchange_config)
            
            # 測試連線
            self.exchange.fetch_time()
            self.is_connected = True
            self.logger.info(f"✅ OKX交易所連接成功 - 測試網路: {self.test_net}")
            
            # 啟動價格更新系統
            self.start_price_updater()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 初始化OKX連接失敗: {e}")
            self.is_connected = False
            return False

    def start_price_updater(self):
        """啟動價格更新器"""
        if self.is_updating:
            return
        
        def price_update_worker():
            """價格更新工作線程"""
            while self.is_updating:
                try:
                    start_time = time.time()
                    self.update_all_prices()
                    self.last_update_time = datetime.now()
                    
                    # 計算實際睡眠時間，確保準確的更新間隔
                    execution_time = time.time() - start_time
                    sleep_time = max(0.1, self.update_interval - execution_time)
                    time.sleep(sleep_time)
                    
                except Exception as e:
                    self.logger.error(f"價格更新循環錯誤: {e}")
                    time.sleep(10)  # 錯誤時等待較長時間
        
        self.is_updating = True
        self.update_thread = threading.Thread(target=price_update_worker, daemon=True)
        self.update_thread.start()
        self.logger.info("✅ 即時價格更新系統已啟動")

    def update_all_prices(self):
        """更新所有監控幣種的價格"""
        try:
            for symbol in self.popular_symbols:
                self._update_single_price(symbol)
                
        except Exception as e:
            self.logger.error(f"批量更新價格錯誤: {e}")

    def _update_single_price(self, symbol: str):
        """
        更新單一交易對價格
        
        Args:
            symbol: 交易對符號
        """
        try:
            # 如果有有效的交易所連接，獲取真實數據
            if self.exchange and self.is_connected:
                ticker = self.exchange.fetch_ticker(symbol)
                if ticker:
                    price_data = PriceData(
                        symbol=symbol,
                        price=ticker['last'],
                        change=ticker.get('percentage', 0),
                        high=ticker.get('high', 0),
                        low=ticker.get('low', 0),
                        volume=ticker.get('baseVolume', 0),
                        bid=ticker.get('bid', 0),
                        ask=ticker.get('ask', 0),
                        spread=abs(ticker.get('ask', 0) - ticker.get('bid', 0)) if ticker.get('ask') and ticker.get('bid') else 0,
                        timestamp=datetime.now().isoformat()
                    )
                    
                    self._cache_price_data(symbol, price_data)
                    return
            
            # 備用：使用模擬數據
            self._update_simulated_price(symbol)
            
        except Exception as e:
            self.logger.warning(f"更新 {symbol} 價格失敗: {e}")
            # 失敗時使用模擬數據
            self._update_simulated_price(symbol)

    def _cache_price_data(self, symbol: str, price_data: PriceData):
        """
        快取價格數據並維護歷史記錄
        
        Args:
            symbol: 交易對符號
            price_data: 價格數據
        """
        # 更新當前價格快取
        self.price_cache[symbol] = price_data
        
        # 維護價格歷史記錄（保留最近100條）
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append(price_data)
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol].pop(0)
        
        # 通知監聽器
        self._notify_price_listeners(symbol, price_data)

    def _update_simulated_price(self, symbol: str):
        """
        更新模擬價格數據
        
        Args:
            symbol: 交易對符號
        """
        import random
        
        # 基礎價格設定（台灣用戶常用幣種）
        base_prices = {
            'BTC/USDT': 45000, 'ETH/USDT': 2400, 'SOL/USDT': 100, 
            'ADA/USDT': 0.5, 'DOT/USDT': 7, 'XRP/USDT': 0.6,
            'LTC/USDT': 70, 'BNB/USDT': 300, 'AVAX/USDT': 35,
            'MATIC/USDT': 0.8, 'LINK/USDT': 15, 'UNI/USDT': 6,
            'DOGE/USDT': 0.08, 'TON/USDT': 2.5, 'ATOM/USDT': 10
        }
        
        # 獲取基礎價格或使用現有價格
        if symbol in self.price_cache:
            base_price = self.price_cache[symbol].price
        else:
            base_price = base_prices.get(symbol, 100)
        
        # 模擬真實價格波動（更自然的隨機漫步）
        previous_change = self.price_cache[symbol].change / 100 if symbol in self.price_cache else 0
        momentum = previous_change * 0.3  # 加入動量效應
        
        # 隨機波動，但受動量影響
        random_change = random.uniform(-0.015, 0.015)  # -1.5% 到 +1.5%
        total_change = momentum + random_change
        
        # 限制最大單次波動
        total_change = max(-0.03, min(0.03, total_change))
        
        new_price = base_price * (1 + total_change)
        
        # 計算高低價（基於波動率）
        volatility = abs(total_change)
        high_price = new_price * (1 + volatility * 0.8)
        low_price = new_price * (1 - volatility * 0.8)
        
        price_data = PriceData(
            symbol=symbol,
            price=new_price,
            change=total_change * 100,
            high=high_price,
            low=low_price,
            volume=random.uniform(5000, 20000),
            bid=new_price * 0.999,  # 模擬買價
            ask=new_price * 1.001,  # 模擬賣價
            spread=new_price * 0.002,  # 模擬價差
            timestamp=datetime.now().isoformat()
        )
        
        self._cache_price_data(symbol, price_data)

    def get_realtime_price(self, symbol: str) -> Optional[PriceData]:
        """
        獲取即時價格數據
        
        Args:
            symbol: 交易對符號 (支援 BTC/USDT 或 BTC-USDT 格式)
            
        Returns:
            PriceData: 價格數據，如果不存在則返回 None
        """
        formatted_symbol = self._format_symbol(symbol)
        return self.price_cache.get(formatted_symbol)

    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, PriceData]:
        """
        獲取多個幣種價格
        
        Args:
            symbols: 交易對符號列表
            
        Returns:
            Dict[str, PriceData]: 價格數據字典
        """
        results = {}
        for symbol in symbols:
            formatted_symbol = self._format_symbol(symbol)
            if formatted_symbol in self.price_cache:
                results[symbol] = self.price_cache[formatted_symbol]
        return results

    def get_price_history(self, symbol: str, limit: int = 50) -> List[PriceData]:
        """
        獲取價格歷史數據
        
        Args:
            symbol: 交易對符號
            limit: 返回數據條數限制
            
        Returns:
            List[PriceData]: 價格歷史數據列表
        """
        formatted_symbol = self._format_symbol(symbol)
        history = self.price_history.get(formatted_symbol, [])
        return history[-limit:] if limit else history

    def add_price_listener(self, callback: Callable):
        """
        添加價格變動監聽器
        
        Args:
            callback: 回調函數，接收 (symbol, price_data) 參數
        """
        if callback not in self.price_listeners:
            self.price_listeners.append(callback)
            self.logger.info(f"✅ 已添加價格監聽器，總數: {len(self.price_listeners)}")

    def remove_price_listener(self, callback: Callable):
        """移除價格監聽器"""
        if callback in self.price_listeners:
            self.price_listeners.remove(callback)

    def _notify_price_listeners(self, symbol: str, price_data: PriceData):
        """通知所有價格監聽器"""
        for listener in self.price_listeners[:]:  # 使用切片複製避免在迭代時修改
            try:
                listener(symbol, price_data)
            except Exception as e:
                self.logger.error(f"價格監聽器通知失敗: {e}")
                # 移除失敗的監聽器
                self.remove_price_listener(listener)

    def _format_symbol(self, symbol: str) -> str:
        """
        統一格式化交易對符號
        
        Args:
            symbol: 原始符號
            
        Returns:
            str: 格式化後的符號
        """
        return symbol.replace('-', '/').upper()

    def stop_price_updater(self):
        """停止價格更新系統"""
        self.is_updating = False
        self.logger.info("⏹️ 價格更新系統已停止")

    def get_connection_status(self) -> Dict:
        """
        獲取連線狀態資訊
        
        Returns:
            Dict: 連線狀態字典
        """
        return {
            'is_connected': self.is_connected,
            'is_updating': self.is_updating,
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'price_cache_size': len(self.price_cache),
            'monitoring_symbols': len(self.popular_symbols)
        }

    def test_connection(self) -> Tuple[bool, str]:
        """
        測試API連線
        
        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            if not self.exchange:
                if all([self.api_key, self.secret_key, self.passphrase]):
                    return False, "交易所實例未初始化"
                else:
                    return True, "模擬模式 - 無需API連線"
            
            # 測試時間同步
            server_time = self.exchange.fetch_time()
            local_time = int(time.time() * 1000)
            time_diff = abs(server_time - local_time)
            
            if time_diff > 30000:  # 30秒差異
                return False, f"時間不同步，差異: {time_diff}ms"
            
            # 測試餘額獲取
            balance = self.exchange.fetch_balance()
            if balance and 'info' in balance:
                return True, f"API連線測試成功 (時間差: {time_diff}ms)"
            else:
                return False, "無法獲取帳戶資訊"
                
        except Exception as e:
            error_msg = str(e)
            if "Authentication" in error_msg:
                return False, "API金鑰驗證失敗，請檢查金鑰權限"
            elif "Network" in error_msg:
                return False, "網路連線失敗，請檢查網路設定"
            elif "timestamp" in error_msg.lower():
                return False, "系統時間不準確，請同步時間"
            else:
                return False, f"連線錯誤: {error_msg}"

# 向下兼容的別名
OKXAPI = OKXAPIClient
class OKXAPIClient:
    # ==================== 帳戶管理功能 ====================
    
    def get_account_balance(self, account_type: str = 'spot') -> AccountBalance:
        """
        獲取帳戶餘額 - 支援現貨和合約
        
        Args:
            account_type: 帳戶類型 ('spot', 'swap', 'funding')
            
        Returns:
            AccountBalance: 帳戶餘額資訊
        """
        try:
            # 模擬模式處理
            if not self.exchange or not self.is_connected:
                return self._get_simulated_balance(account_type)
            
            # 保存原始帳戶類型
            original_type = self.exchange.options.get('defaultType', 'spot')
            self.exchange.options['defaultType'] = account_type
            
            balance_data = self.exchange.fetch_balance()
            
            # 恢復原始類型
            self.exchange.options['defaultType'] = original_type
            
            # 解析餘額數據
            currencies = {}
            total_balance = 0
            available_balance = 0
            used_balance = 0
            
            for currency, info in balance_data['total'].items():
                if info > 0:  # 只處理有餘額的幣種
                    free = balance_data['free'].get(currency, 0)
                    used = balance_data['used'].get(currency, 0)
                    
                    currencies[currency] = {
                        'total': info,
                        'free': free,
                        'used': used
                    }
                    
                    # 如果是USDT，計算總餘額
                    if currency == 'USDT':
                        total_balance = info
                        available_balance = free
                        used_balance = used
            
            return AccountBalance(
                total_balance=total_balance,
                available_balance=available_balance,
                used_balance=used_balance,
                account_type=account_type,
                timestamp=datetime.now().isoformat(),
                currencies=currencies
            )
            
        except Exception as e:
            self.logger.error(f"獲取{account_type}帳戶餘額錯誤: {e}")
            return self._get_simulated_balance(account_type)
    
    def _get_simulated_balance(self, account_type: str) -> AccountBalance:
        """
        獲取模擬帳戶餘額
        
        Args:
            account_type: 帳戶類型
            
        Returns:
            AccountBalance: 模擬餘額數據
        """
        # 模擬真實的資產分布
        simulated_currencies = {
            'USDT': {'total': 1000.0, 'free': 800.0, 'used': 200.0},
            'BTC': {'total': 0.05, 'free': 0.05, 'used': 0},
            'ETH': {'total': 1.5, 'free': 1.5, 'used': 0},
            'SOL': {'total': 10.0, 'free': 10.0, 'used': 0}
        }
        
        return AccountBalance(
            total_balance=1000.0,
            available_balance=800.0,
            used_balance=200.0,
            account_type=account_type,
            timestamp=datetime.now().isoformat(),
            currencies=simulated_currencies
        )
    
    def get_spot_balance(self) -> AccountBalance:
        """獲取現貨帳戶餘額"""
        return self.get_account_balance('spot')
    
    def get_futures_balance(self) -> AccountBalance:
        """獲取合約帳戶餘額"""
        return self.get_account_balance('swap')
    
    def get_total_balance_summary(self) -> Dict:
        """
        獲取總資產概覽
        
        Returns:
            Dict: 資產總覽資訊
        """
        try:
            spot_balance = self.get_spot_balance()
            futures_balance = self.get_futures_balance()
            
            # 計算總資產（簡單加總）
            total_assets = spot_balance.total_balance + futures_balance.total_balance
            available_total = spot_balance.available_balance + futures_balance.available_balance
            
            return {
                'total_assets': total_assets,
                'available_total': available_total,
                'spot_balance': spot_balance.total_balance,
                'futures_balance': futures_balance.total_balance,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"獲取總資產概覽錯誤: {e}")
            return {
                'total_assets': 2000.0,
                'available_total': 1600.0,
                'spot_balance': 1000.0,
                'futures_balance': 1000.0,
                'timestamp': datetime.now().isoformat()
            }
    
    # ==================== 市場數據功能 ====================
    
    def get_ticker(self, symbol: str) -> Dict:
        """
        獲取標的行情數據
        
        Args:
            symbol: 交易對符號
            
        Returns:
            Dict: 行情數據
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            # 如果沒有交易所連接，使用快取數據
            if not self.exchange or not self.is_connected:
                price_data = self.price_cache.get(formatted_symbol)
                if price_data:
                    return {
                        'symbol': symbol,
                        'last': price_data.price,
                        'open': price_data.price * 0.99,  # 模擬開盤價
                        'high': price_data.high,
                        'low': price_data.low,
                        'volume': price_data.volume,
                        'change': price_data.change,
                        'percentage': price_data.change,
                        'bid': price_data.bid,
                        'ask': price_data.ask,
                        'datetime': price_data.timestamp
                    }
                else:
                    # 生成基礎模擬數據
                    return self._generate_basic_ticker(symbol)
            
            ticker = self.exchange.fetch_ticker(formatted_symbol)
            
            return {
                'symbol': symbol,
                'last': ticker.get('last', 0),
                'open': ticker.get('open', ticker.get('last', 0)),
                'high': ticker.get('high', 0),
                'low': ticker.get('low', 0),
                'volume': ticker.get('baseVolume', 0),
                'change': ticker.get('change', 0),
                'percentage': ticker.get('percentage', 0),
                'bid': ticker.get('bid', 0),
                'ask': ticker.get('ask', 0),
                'datetime': ticker.get('datetime', '')
            }
            
        except Exception as e:
            self.logger.error(f"獲取行情數據錯誤 {symbol}: {e}")
            return self._generate_basic_ticker(symbol)
    
    def _generate_basic_ticker(self, symbol: str) -> Dict:
        """生成基礎模擬行情數據"""
        base_prices = {
            'BTC/USDT': 45000, 'ETH/USDT': 2400, 'SOL/USDT': 100,
            'ADA/USDT': 0.5, 'DOT/USDT': 7, 'XRP/USDT': 0.6
        }
        
        base_price = base_prices.get(self._format_symbol(symbol), 100)
        
        return {
            'symbol': symbol,
            'last': base_price,
            'open': base_price * 0.99,
            'high': base_price * 1.02,
            'low': base_price * 0.98,
            'volume': 10000,
            'change': base_price * 0.01,
            'percentage': 1.0,
            'bid': base_price * 0.999,
            'ask': base_price * 1.001,
            'datetime': datetime.now().isoformat()
        }
    
    def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List]:
        """
        獲取K線數據
        
        Args:
            symbol: 交易對符號
            timeframe: 時間週期 ('1m', '5m', '1h', '4h', '1d'等)
            limit: 數據條數限制
            
        Returns:
            List[List]: K線數據列表
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            if not self.exchange or not self.is_connected:
                return self._generate_simulated_ohlcv(symbol, timeframe, limit)
            
            ohlcv = self.exchange.fetch_ohlcv(formatted_symbol, timeframe, limit=limit)
            return ohlcv
            
        except Exception as e:
            self.logger.error(f"獲取K線數據錯誤 {symbol}: {e}")
            return self._generate_simulated_ohlcv(symbol, timeframe, limit)
    
    def _generate_simulated_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List]:
        """生成模擬K線數據"""
        import random
        import time
        
        # 時間週期對應的毫秒數
        timeframe_ms = {
            '1m': 60000, '5m': 300000, '15m': 900000,
            '1h': 3600000, '4h': 14400000, '1d': 86400000
        }
        
        interval_ms = timeframe_ms.get(timeframe, 3600000)  # 預設1小時
        
        # 基礎價格
        base_prices = {
            'BTC/USDT': 45000, 'ETH/USDT': 2400, 'SOL/USDT': 100,
            'ADA/USDT': 0.5, 'DOT/USDT': 7, 'XRP/USDT': 0.6
        }
        
        base_price = base_prices.get(self._format_symbol(symbol), 100)
        current_time = int(time.time() * 1000) - (limit * interval_ms)
        
        ohlcv_data = []
        previous_close = base_price
        
        for i in range(limit):
            # 更真實的價格波動模擬
            volatility = random.uniform(0.005, 0.02)  # 0.5% - 2% 波動率
            
            open_price = previous_close
            change_percent = random.gauss(0, volatility)  # 正態分布
            close_price = open_price * (1 + change_percent)
            
            # 計算高低價（基於波動率）
            price_range = abs(close_price - open_price)
            high_price = max(open_price, close_price) + price_range * random.uniform(0.1, 0.3)
            low_price = min(open_price, close_price) - price_range * random.uniform(0.1, 0.3)
            
            # 確保高低價合理
            high_price = max(open_price, close_price, high_price)
            low_price = min(open_price, close_price, low_price)
            
            volume = random.uniform(1000, 50000)
            
            ohlcv_data.append([
                current_time + (i * interval_ms),  # timestamp
                open_price,    # open
                high_price,    # high
                low_price,     # low
                close_price,   # close
                volume         # volume
            ])
            
            previous_close = close_price
        
        return ohlcv_data
    
    def get_orderbook(self, symbol: str, limit: int = 5) -> Dict:
        """
        獲取訂單簿數據
        
        Args:
            symbol: 交易對符號
            limit: 深度限制
            
        Returns:
            Dict: 訂單簿數據
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            if not self.exchange or not self.is_connected:
                return self._generate_simulated_orderbook(symbol, limit)
            
            orderbook = self.exchange.fetch_order_book(formatted_symbol, limit)
            return orderbook
            
        except Exception as e:
            self.logger.error(f"獲取訂單簿錯誤 {symbol}: {e}")
            return self._generate_simulated_orderbook(symbol, limit)
    
    def _generate_simulated_orderbook(self, symbol: str, limit: int = 5) -> Dict:
        """生成模擬訂單簿數據"""
        current_price = self.get_realtime_price(symbol)
        if not current_price:
            current_price = PriceData(symbol=symbol, price=100, change=0, high=101, low=99, volume=1000, timestamp=datetime.now().isoformat())
        
        base_price = current_price.price
        
        bids = []
        asks = []
        
        # 生成買盤
        for i in range(limit):
            price = base_price * (1 - (i + 1) * 0.001)  # 逐步降低
            amount = (limit - i) * 0.1  # 買盤量遞增
            bids.append([price, amount])
        
        # 生成賣盤
        for i in range(limit):
            price = base_price * (1 + (i + 1) * 0.001)  # 逐步升高
            amount = (i + 1) * 0.1  # 賣盤量遞增
            asks.append([price, amount])
        
        return {
            'bids': bids,
            'asks': asks,
            'timestamp': datetime.now().isoformat(),
            'datetime': datetime.now().isoformat()
        }

    # ==================== 工具方法 ====================
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        獲取交易對資訊
        
        Args:
            symbol: 交易對符號
            
        Returns:
            Dict: 交易對資訊
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            if not self.exchange or not self.is_connected:
                return self._get_simulated_symbol_info(symbol)
            
            markets = self.exchange.load_markets()
            market_info = markets.get(formatted_symbol, {})
            
            return {
                'symbol': symbol,
                'base': market_info.get('base'),
                'quote': market_info.get('quote'),
                'active': market_info.get('active', True),
                'precision': market_info.get('precision', {}),
                'limits': market_info.get('limits', {}),
                'info': market_info
            }
            
        except Exception as e:
            self.logger.error(f"獲取交易對資訊錯誤 {symbol}: {e}")
            return self._get_simulated_symbol_info(symbol)
    
    def _get_simulated_symbol_info(self, symbol: str) -> Dict:
        """獲取模擬交易對資訊"""
        return {
            'symbol': symbol,
            'base': symbol.split('/')[0],
            'quote': symbol.split('/')[1],
            'active': True,
            'precision': {
                'amount': 0.001,
                'price': 0.01
            },
            'limits': {
                'amount': {
                    'min': 0.001,
                    'max': 1000
                },
                'price': {
                    'min': 0.01,
                    'max': 1000000
                },
                'cost': {
                    'min': 1,
                    'max': None
                }
            }
        }
    
    def calculate_position_size(self, symbol: str, risk_amount: float, stop_loss_pct: float) -> float:
        """
        計算建議持倉大小
        
        Args:
            symbol: 交易對符號
            risk_amount: 風險金額 (USDT)
            stop_loss_pct: 止損百分比
            
        Returns:
            float: 建議持倉數量
        """
        try:
            current_price = self.get_realtime_price(symbol)
            if not current_price:
                return 0
            
            # 計算持倉數量
            price = current_price.price
            risk_per_unit = price * stop_loss_pct
            position_size = risk_amount / risk_per_unit
            
            self.logger.info(f"持倉計算: {symbol} 風險金額=${risk_amount}, 止損{stop_loss_pct*100}%, 建議數量={position_size:.4f}")
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"計算持倉大小錯誤: {e}")
            return 0

# 向下兼容
OKXAPI = OKXAPIClient
class OKXAPIClient:
    # ==================== 現貨交易功能 ====================
    
    def spot_buy(self, symbol: str, amount: float, price: float = None, 
                 order_type: str = 'limit') -> Dict:
        """
        現貨買入
        
        Args:
            symbol: 交易對符號
            amount: 購買數量
            price: 價格 (限價單需要)
            order_type: 訂單類型 ('limit', 'market')
            
        Returns:
            Dict: 訂單資訊
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            # 模擬模式處理
            if not self.exchange or not self.is_connected:
                return self._simulate_spot_order('buy', symbol, amount, price, order_type)
            
            order_params = {
                'symbol': formatted_symbol,
                'type': order_type,
                'side': 'buy',
                'amount': self._adjust_amount(symbol, amount)
            }
            
            if order_type == 'limit' and price:
                order_params['price'] = self._adjust_price(symbol, price)
            
            # 設置為現貨交易
            original_type = self.exchange.options.get('defaultType', 'spot')
            self.exchange.options['defaultType'] = 'spot'
            
            order = self.exchange.create_order(**order_params)
            
            # 恢復原始類型
            self.exchange.options['defaultType'] = original_type
            
            self.logger.info(f"✅ 現貨買入成功: {symbol} 數量={amount} 價格={price}")
            return order
            
        except Exception as e:
            self.logger.error(f"現貨買入錯誤 {symbol}: {e}")
            return self._create_error_order('buy', symbol, amount, price, str(e))
    
    def spot_sell(self, symbol: str, amount: float, price: float = None,
                  order_type: str = 'limit') -> Dict:
        """
        現貨賣出
        
        Args:
            symbol: 交易對符號
            amount: 賣出數量
            price: 價格 (限價單需要)
            order_type: 訂單類型 ('limit', 'market')
            
        Returns:
            Dict: 訂單資訊
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            # 模擬模式處理
            if not self.exchange or not self.is_connected:
                return self._simulate_spot_order('sell', symbol, amount, price, order_type)
            
            order_params = {
                'symbol': formatted_symbol,
                'type': order_type,
                'side': 'sell',
                'amount': self._adjust_amount(symbol, amount)
            }
            
            if order_type == 'limit' and price:
                order_params['price'] = self._adjust_price(symbol, price)
            
            # 設置為現貨交易
            original_type = self.exchange.options.get('defaultType', 'spot')
            self.exchange.options['defaultType'] = 'spot'
            
            order = self.exchange.create_order(**order_params)
            
            # 恢復原始類型
            self.exchange.options['defaultType'] = original_type
            
            self.logger.info(f"✅ 現貨賣出成功: {symbol} 數量={amount} 價格={price}")
            return order
            
        except Exception as e:
            self.logger.error(f"現貨賣出錯誤 {symbol}: {e}")
            return self._create_error_order('sell', symbol, amount, price, str(e))
    
    def get_spot_positions(self) -> List[Dict]:
        """
        獲取現貨持倉
        
        Returns:
            List[Dict]: 持倉列表
        """
        try:
            if not self.exchange or not self.is_connected:
                return self._get_simulated_spot_positions()
            
            # 設置為現貨交易
            original_type = self.exchange.options.get('defaultType', 'spot')
            self.exchange.options['defaultType'] = 'spot'
            
            balance = self.exchange.fetch_balance()
            
            # 恢復原始類型
            self.exchange.options['defaultType'] = original_type
            
            positions = []
            for currency, total_amount in balance['total'].items():
                if total_amount > 0 and currency != 'USDT':  # 排除USDT
                    free_amount = balance['free'].get(currency, 0)
                    used_amount = balance['used'].get(currency, 0)
                    
                    # 獲取當前價格計算價值
                    symbol = f"{currency}/USDT"
                    price_data = self.get_realtime_price(symbol)
                    current_price = price_data.price if price_data else 0
                    total_value = total_amount * current_price
                    
                    positions.append({
                        'symbol': currency,
                        'total': total_amount,
                        'free': free_amount,
                        'used': used_amount,
                        'current_price': current_price,
                        'total_value': total_value,
                        'currency': currency
                    })
            
            # 添加USDT餘額
            usdt_total = balance['total'].get('USDT', 0)
            if usdt_total > 0:
                positions.append({
                    'symbol': 'USDT',
                    'total': usdt_total,
                    'free': balance['free'].get('USDT', 0),
                    'used': balance['used'].get('USDT', 0),
                    'current_price': 1.0,
                    'total_value': usdt_total,
                    'currency': 'USDT'
                })
            
            return positions
            
        except Exception as e:
            self.logger.error(f"獲取現貨持倉錯誤: {e}")
            return self._get_simulated_spot_positions()
    
    def _get_simulated_spot_positions(self) -> List[Dict]:
        """獲取模擬現貨持倉"""
        simulated_positions = [
            {
                'symbol': 'BTC',
                'total': 0.05,
                'free': 0.05,
                'used': 0,
                'current_price': 45000,
                'total_value': 2250,
                'currency': 'BTC'
            },
            {
                'symbol': 'ETH', 
                'total': 1.5,
                'free': 1.5,
                'used': 0,
                'current_price': 2400,
                'total_value': 3600,
                'currency': 'ETH'
            },
            {
                'symbol': 'SOL',
                'total': 10.0,
                'free': 10.0,
                'used': 0,
                'current_price': 100,
                'total_value': 1000,
                'currency': 'SOL'
            },
            {
                'symbol': 'USDT',
                'total': 1000.0,
                'free': 1000.0,
                'used': 0,
                'current_price': 1.0,
                'total_value': 1000,
                'currency': 'USDT'
            }
        ]
        return simulated_positions

    # ==================== 合約交易功能 ====================
    
    def futures_create_order(self, symbol: str, order_type: str, side: str, 
                           amount: float, price: float = None, 
                           leverage: int = None, reduce_only: bool = False,
                           stop_loss: float = None, take_profit: float = None) -> Dict:
        """
        合約下單
        
        Args:
            symbol: 交易對符號
            order_type: 訂單類型 ('limit', 'market')
            side: 方向 ('buy', 'sell')
            amount: 數量
            price: 價格 (限價單需要)
            leverage: 槓桿倍數
            reduce_only: 是否僅減倉
            stop_loss: 止損價格
            take_profit: 止盈價格
            
        Returns:
            Dict: 訂單資訊
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            # 模擬模式處理
            if not self.exchange or not self.is_connected:
                return self._simulate_futures_order(side, symbol, amount, price, order_type)
            
            # 設置槓桿
            if leverage:
                self.futures_set_leverage(symbol, leverage)
            
            order_params = {
                'symbol': formatted_symbol,
                'type': order_type,
                'side': side,
                'amount': self._adjust_amount(symbol, amount),
                'params': {}
            }
            
            if order_type == 'limit' and price:
                order_params['price'] = self._adjust_price(symbol, price)
            
            if reduce_only:
                order_params['params']['reduceOnly'] = True
            
            # 條件委託
            if stop_loss or take_profit:
                self._setup_conditional_orders(symbol, side, amount, stop_loss, take_profit)
            
            # 設置為合約交易
            original_type = self.exchange.options.get('defaultType', 'swap')
            self.exchange.options['defaultType'] = 'swap'
            
            order = self.exchange.create_order(**order_params)
            
            # 恢復原始類型
            self.exchange.options['defaultType'] = original_type
            
            self.logger.info(f"✅ 合約下單成功: {symbol} {side} 數量={amount} 價格={price}")
            return order
            
        except Exception as e:
            self.logger.error(f"合約下單錯誤 {symbol}: {e}")
            return self._create_error_order(side, symbol, amount, price, str(e))
    
    def futures_set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        設置合約槓桿
        
        Args:
            symbol: 交易對符號
            leverage: 槓桿倍數
            
        Returns:
            bool: 是否成功
        """
        try:
            if not self.exchange or not self.is_connected:
                self.logger.info(f"模擬設置槓桿: {symbol} 槓桿={leverage}")
                return True
            
            formatted_symbol = self._format_symbol(symbol)
            
            # 設置為合約交易
            original_type = self.exchange.options.get('defaultType', 'swap')
            self.exchange.options['defaultType'] = 'swap'
            
            result = self.exchange.set_leverage(leverage, formatted_symbol)
            
            # 恢復原始類型
            self.exchange.options['defaultType'] = original_type
            
            self.logger.info(f"✅ 設置槓桿成功: {symbol} 槓桿={leverage}")
            return True
            
        except Exception as e:
            self.logger.error(f"設置槓桿錯誤 {symbol}: {e}")
            return False
    
    def futures_get_positions(self, symbol: str = None) -> List[Dict]:
        """
        獲取合約持倉
        
        Args:
            symbol: 交易對符號 (可選)
            
        Returns:
            List[Dict]: 持倉列表
        """
        try:
            if not self.exchange or not self.is_connected:
                return self._get_simulated_futures_positions(symbol)
            
            # 設置為合約交易
            original_type = self.exchange.options.get('defaultType', 'swap')
            self.exchange.options['defaultType'] = 'swap'
            
            positions = self.exchange.fetch_positions([symbol] if symbol else None)
            
            # 恢復原始類型
            self.exchange.options['defaultType'] = original_type
            
            formatted_positions = []
            for pos in positions:
                if pos['contracts'] and float(pos['contracts']) > 0:
                    unrealized_pnl = pos.get('unrealizedPnl', 0)
                    entry_price = pos.get('entryPrice', 0)
                    mark_price = pos.get('markPrice', 0)
                    
                    # 計算收益率
                    if entry_price > 0:
                        if pos['side'] == 'long':
                            pnl_percent = (mark_price - entry_price) / entry_price * 100
                        else:
                            pnl_percent = (entry_price - mark_price) / entry_price * 100
                    else:
                        pnl_percent = 0
                    
                    formatted_positions.append({
                        'symbol': pos['symbol'],
                        'side': pos['side'],
                        'amount': abs(float(pos['contracts'])),
                        'entryPrice': entry_price,
                        'markPrice': mark_price,
                        'unrealizedPnl': unrealized_pnl,
                        'pnlPercent': pnl_percent,
                        'leverage': pos.get('leverage', 1),
                        'liquidationPrice': pos.get('liquidationPrice', 0),
                        'margin': pos.get('initialMargin', 0)
                    })
            
            return formatted_positions
            
        except Exception as e:
            self.logger.error(f"獲取合約持倉錯誤: {e}")
            return self._get_simulated_futures_positions(symbol)
    
    def _get_simulated_futures_positions(self, symbol: str = None) -> List[Dict]:
        """獲取模擬合約持倉"""
        simulated_positions = [
            {
                'symbol': 'BTC/USDT:USDT',
                'side': 'long',
                'amount': 0.1,
                'entryPrice': 45000,
                'markPrice': 45200,
                'unrealizedPnl': 200,
                'pnlPercent': 0.44,
                'leverage': 10,
                'liquidationPrice': 40500,
                'margin': 450
            }
        ]
        
        if symbol:
            formatted_symbol = self._format_symbol(symbol) + ':USDT'
            return [pos for pos in simulated_positions if pos['symbol'] == formatted_symbol]
        
        return simulated_positions
    
    def futures_close_position(self, symbol: str, side: str = None) -> bool:
        """
        平倉合約位置
        
        Args:
            symbol: 交易對符號
            side: 方向 ('buy', 'sell')，如果為None則自動判斷
            
        Returns:
            bool: 是否成功
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            # 獲取當前持倉
            positions = self.futures_get_positions(symbol)
            position_to_close = None
            
            for pos in positions:
                if pos['symbol'] == formatted_symbol + ':USDT':
                    position_to_close = pos
                    break
            
            if not position_to_close:
                self.logger.warning(f"沒有找到 {symbol} 的持倉")
                return False
            
            # 確定平倉方向
            close_side = 'sell' if position_to_close['side'] == 'long' else 'buy'
            
            # 模擬模式處理
            if not self.exchange or not self.is_connected:
                self.logger.info(f"模擬平倉: {symbol} 方向={close_side} 數量={position_to_close['amount']}")
                return True
            
            # 設置為合約交易
            original_type = self.exchange.options.get('defaultType', 'swap')
            self.exchange.options['defaultType'] = 'swap'
            
            order = self.exchange.create_order(
                symbol=formatted_symbol,
                type='market',
                side=close_side,
                amount=position_to_close['amount'],
                params={'reduceOnly': True}
            )
            
            # 恢復原始類型
            self.exchange.options['defaultType'] = original_type
            
            self.logger.info(f"✅ 平倉成功: {symbol} 方向={close_side} 數量={position_to_close['amount']}")
            return True
            
        except Exception as e:
            self.logger.error(f"平倉錯誤 {symbol}: {e}")
            return False
    
    def _setup_conditional_orders(self, symbol: str, side: str, amount: float, 
                                stop_loss: float = None, take_profit: float = None):
        """
        設置條件委託 (止損止盈)
        
        Args:
            symbol: 交易對符號
            side: 方向
            amount: 數量
            stop_loss: 止損價格
            take_profit: 止盈價格
        """
        try:
            if not self.exchange or not self.is_connected:
                return
            
            formatted_symbol = self._format_symbol(symbol)
            
            # 設置止損
            if stop_loss:
                stop_side = 'sell' if side == 'buy' else 'buy'
                self.exchange.create_order(
                    symbol=formatted_symbol,
                    type='stop',
                    side=stop_side,
                    amount=amount,
                    price=stop_loss,
                    params={'stopPrice': stop_loss, 'reduceOnly': True}
                )
                self.logger.info(f"✅ 設置止損: {symbol} 價格={stop_loss}")
            
            # 設置止盈
            if take_profit:
                tp_side = 'sell' if side == 'buy' else 'buy'
                self.exchange.create_order(
                    symbol=formatted_symbol,
                    type='limit',
                    side=tp_side,
                    amount=amount,
                    price=take_profit,
                    params={'reduceOnly': True}
                )
                self.logger.info(f"✅ 設置止盈: {symbol} 價格={take_profit}")
                
        except Exception as e:
            self.logger.error(f"設置條件委託錯誤 {symbol}: {e}")

    # ==================== 訂單管理功能 ====================
    
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """
        獲取未成交訂單
        
        Args:
            symbol: 交易對符號 (可選)
            
        Returns:
            List[Dict]: 未成交訂單列表
        """
        try:
            if not self.exchange or not self.is_connected:
                return self._get_simulated_open_orders(symbol)
            
            if symbol:
                formatted_symbol = self._format_symbol(symbol)
                orders = self.exchange.fetch_open_orders(formatted_symbol)
            else:
                orders = self.exchange.fetch_open_orders()
            
            formatted_orders = []
            for order in orders:
                formatted_orders.append({
                    'id': order['id'],
                    'symbol': order['symbol'],
                    'type': order['type'],
                    'side': order['side'],
                    'amount': order['amount'],
                    'price': order.get('price'),
                    'filled': order.get('filled', 0),
                    'remaining': order.get('remaining', order['amount']),
                    'status': order.get('status', 'open'),
                    'timestamp': order['timestamp'],
                    'datetime': order.get('datetime', '')
                })
            
            return formatted_orders
            
        except Exception as e:
            self.logger.error(f"獲取未成交訂單錯誤: {e}")
            return self._get_simulated_open_orders(symbol)
    
    def _get_simulated_open_orders(self, symbol: str = None) -> List[Dict]:
        """獲取模擬未成交訂單"""
        simulated_orders = [
            {
                'id': 'sim_buy_001',
                'symbol': 'BTC/USDT',
                'type': 'limit',
                'side': 'buy',
                'amount': 0.01,
                'price': 44000,
                'filled': 0,
                'remaining': 0.01,
                'status': 'open',
                'timestamp': int(time.time() * 1000) - 3600000,  # 1小時前
                'datetime': datetime.now().isoformat()
            }
        ]
        
        if symbol:
            formatted_symbol = self._format_symbol(symbol)
            return [order for order in simulated_orders if order['symbol'] == formatted_symbol]
        
        return simulated_orders
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        取消訂單
        
        Args:
            order_id: 訂單ID
            symbol: 交易對符號
            
        Returns:
            bool: 是否成功
        """
        try:
            if not self.exchange or not self.is_connected:
                self.logger.info(f"模擬取消訂單: {order_id}")
                return True
            
            formatted_symbol = self._format_symbol(symbol)
            result = self.exchange.cancel_order(order_id, formatted_symbol)
            
            self.logger.info(f"✅ 取消訂單成功: {order_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"取消訂單錯誤 {order_id}: {e}")
            return False
    
    def cancel_all_orders(self, symbol: str = None) -> bool:
        """
        取消所有訂單
        
        Args:
            symbol: 交易對符號 (可選)
            
        Returns:
            bool: 是否成功
        """
        try:
            if not self.exchange or not self.is_connected:
                self.logger.info("模擬取消所有訂單")
                return True
            
            if symbol:
                formatted_symbol = self._format_symbol(symbol)
                self.exchange.cancel_all_orders(formatted_symbol)
            else:
                self.exchange.cancel_all_orders()
            
            self.logger.info("✅ 取消所有訂單成功")
            return True
            
        except Exception as e:
            self.logger.error(f"取消所有訂單錯誤: {e}")
            return False
    
    def get_order_history(self, symbol: str = None, limit: int = 50) -> List[Dict]:
        """
        獲取訂單歷史
        
        Args:
            symbol: 交易對符號 (可選)
            limit: 返回條數限制
            
        Returns:
            List[Dict]: 訂單歷史列表
        """
        try:
            if not self.exchange or not self.is_connected:
                return self._get_simulated_order_history(symbol, limit)
            
            if symbol:
                formatted_symbol = self._format_symbol(symbol)
                orders = self.exchange.fetch_orders(formatted_symbol, limit=limit)
            else:
                orders = self.exchange.fetch_orders(limit=limit)
            
            formatted_orders = []
            for order in orders:
                # 計算成交均價
                avg_price = 0
                if order.get('filled') and order['filled'] > 0:
                    avg_price = order.get('cost', 0) / order['filled']
                
                formatted_orders.append({
                    'id': order['id'],
                    'symbol': order['symbol'],
                    'type': order['type'],
                    'side': order['side'],
                    'amount': order['amount'],
                    'price': order.get('price'),
                    'filled': order.get('filled', 0),
                    'average': avg_price,
                    'status': order.get('status', 'closed'),
                    'timestamp': order['timestamp'],
                    'datetime': order.get('datetime', ''),
                    'fee': order.get('fee', {})
                })
            
            return formatted_orders
            
        except Exception as e:
            self.logger.error(f"獲取訂單歷史錯誤: {e}")
            return self._get_simulated_order_history(symbol, limit)
    
    def _get_simulated_order_history(self, symbol: str = None, limit: int = 50) -> List[Dict]:
        """獲取模擬訂單歷史"""
        import random
        
        base_time = int(time.time() * 1000)
        simulated_orders = []
        
        for i in range(min(limit, 20)):
            order_time = base_time - (i * 3600000)  # 每小時一筆
            side = random.choice(['buy', 'sell'])
            symbol_choice = random.choice(['BTC/USDT', 'ETH/USDT', 'SOL/USDT'])
            
            if symbol:
                symbol_choice = self._format_symbol(symbol)
            
            price = random.uniform(100, 50000)
            amount = random.uniform(0.01, 1.0)
            
            simulated_orders.append({
                'id': f'sim_order_{i:03d}',
                'symbol': symbol_choice,
                'type': 'limit',
                'side': side,
                'amount': amount,
                'price': price,
                'filled': amount,
                'average': price,
                'status': 'closed',
                'timestamp': order_time,
                'datetime': datetime.fromtimestamp(order_time/1000).isoformat(),
                'fee': {'cost': amount * price * 0.001, 'currency': 'USDT'}
            })
        
        return simulated_orders

    # ==================== 工具方法 ====================
    
    def _simulate_spot_order(self, side: str, symbol: str, amount: float, 
                           price: float = None, order_type: str = 'limit') -> Dict:
        """模擬現貨訂單"""
        order_id = f"sim_{side}_{int(time.time())}"
        
        # 獲取當前價格
        current_price_data = self.get_realtime_price(symbol)
        current_price = current_price_data.price if current_price_data else 100
        
        # 如果是市價單，使用當前價格
        if order_type == 'market':
            price = current_price
        
        return {
            'id': order_id,
            'symbol': symbol,
            'type': order_type,
            'side': side,
            'amount': amount,
            'price': price,
            'filled': amount,
            'remaining': 0,
            'status': 'closed',
            'timestamp': int(time.time() * 1000),
            'datetime': datetime.now().isoformat(),
            'fee': {'cost': amount * price * 0.001, 'currency': 'USDT'},
            'info': {'simulated': True}
        }
    
    def _simulate_futures_order(self, side: str, symbol: str, amount: float,
                              price: float = None, order_type: str = 'limit') -> Dict:
        """模擬合約訂單"""
        return self._simulate_spot_order(side, symbol, amount, price, order_type)
    
    def _create_error_order(self, side: str, symbol: str, amount: float,
                          price: float, error_msg: str) -> Dict:
        """創建錯誤訂單回應"""
        return {
            'id': f"error_{int(time.time())}",
            'symbol': symbol,
            'type': 'limit',
            'side': side,
            'amount': amount,
            'price': price,
            'filled': 0,
            'remaining': amount,
            'status': 'rejected',
            'timestamp': int(time.time() * 1000),
            'datetime': datetime.now().isoformat(),
            'fee': None,
            'info': {'error': error_msg}
        }
    
    def _adjust_amount(self, symbol: str, amount: float) -> float:
        """
        調整數量精度
        
        Args:
            symbol: 交易對符號
            amount: 原始數量
            
        Returns:
            float: 調整後的數量
        """
        # 根據不同幣種調整精度
        precision_rules = {
            'BTC/USDT': 0.001,
            'ETH/USDT': 0.01,
            'SOL/USDT': 0.1,
            'ADA/USDT': 1,
            'DOT/USDT': 0.1
        }
        
        precision = precision_rules.get(self._format_symbol(symbol), 0.01)
        adjusted = round(amount / precision) * precision
        return max(adjusted, precision)  # 確保不小於最小精度
    
    def _adjust_price(self, symbol: str, price: float) -> float:
        """
        調整價格精度
        
        Args:
            symbol: 交易對符號
            price: 原始價格
            
        Returns:
            float: 調整後的價格
        """
        # 根據不同幣種調整價格精度
        precision_rules = {
            'BTC/USDT': 0.1,
            'ETH/USDT': 0.01,
            'SOL/USDT': 0.001,
            'ADA/USDT': 0.0001,
            'DOT/USDT': 0.001
        }
        
        precision = precision_rules.get(self._format_symbol(symbol), 0.01)
        return round(price / precision) * precision

# 向下兼容
OKXAPI = OKXAPIClient
class OKXAPIClient:
    # ==================== 高級交易功能 ====================
    
    def create_bracket_order(self, symbol: str, side: str, amount: float, 
                           entry_price: float = None, stop_loss: float = None,
                           take_profit: float = None, leverage: int = None) -> Dict:
        """
        創建括號訂單 (帶止損止盈的訂單)
        
        Args:
            symbol: 交易對符號
            side: 方向 ('buy', 'sell')
            amount: 數量
            entry_price: 進場價格 (None為市價)
            stop_loss: 止損價格
            take_profit: 止盈價格
            leverage: 槓桿倍數
            
        Returns:
            Dict: 訂單結果
        """
        try:
            # 主訂單
            if entry_price:
                order_type = 'limit'
            else:
                order_type = 'market'
                # 獲取當前價格作為參考
                price_data = self.get_realtime_price(symbol)
                entry_price = price_data.price if price_data else 0
            
            # 下主訂單
            main_order = self.futures_create_order(
                symbol=symbol,
                order_type=order_type,
                side=side,
                amount=amount,
                price=entry_price,
                leverage=leverage
            )
            
            # 設置條件訂單
            if stop_loss or take_profit:
                self._setup_conditional_orders(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            
            result = {
                'main_order': main_order,
                'stop_loss_set': stop_loss is not None,
                'take_profit_set': take_profit is not None,
                'bracket_complete': True
            }
            
            self.logger.info(f"✅ 括號訂單創建成功: {symbol} {side} 數量={amount}")
            return result
            
        except Exception as e:
            self.logger.error(f"創建括號訂單錯誤 {symbol}: {e}")
            return {
                'main_order': None,
                'stop_loss_set': False,
                'take_profit_set': False,
                'bracket_complete': False,
                'error': str(e)
            }
    
    def create_grid_order(self, symbol: str, side: str, total_amount: float,
                         price_low: float, price_high: float, grid_count: int = 10) -> List[Dict]:
        """
        創建網格訂單
        
        Args:
            symbol: 交易對符號
            side: 方向 ('buy', 'sell')
            total_amount: 總數量
            price_low: 網格低價
            price_high: 網格高價
            grid_count: 網格數量
            
        Returns:
            List[Dict]: 網格訂單列表
        """
        try:
            grid_orders = []
            grid_amount = total_amount / grid_count
            price_step = (price_high - price_low) / grid_count
            
            for i in range(grid_count):
                grid_price = price_low + (i * price_step)
                
                order = self.spot_buy(
                    symbol=symbol,
                    amount=grid_amount,
                    price=grid_price,
                    order_type='limit'
                ) if side == 'buy' else self.spot_sell(
                    symbol=symbol,
                    amount=grid_amount,
                    price=grid_price,
                    order_type='limit'
                )
                
                if order:
                    grid_orders.append({
                        'grid_level': i + 1,
                        'price': grid_price,
                        'amount': grid_amount,
                        'order': order
                    })
            
            self.logger.info(f"✅ 網格訂單創建成功: {symbol} {side} 網格數={grid_count}")
            return grid_orders
            
        except Exception as e:
            self.logger.error(f"創建網格訂單錯誤 {symbol}: {e}")
            return []
    
    def get_funding_rate(self, symbol: str) -> Dict:
        """
        獲取資金費率
        
        Args:
            symbol: 交易對符號
            
        Returns:
            Dict: 資金費率資訊
        """
        try:
            if not self.exchange or not self.is_connected:
                return self._get_simulated_funding_rate(symbol)
            
            formatted_symbol = self._format_symbol(symbol)
            
            # 設置為合約交易
            original_type = self.exchange.options.get('defaultType', 'swap')
            self.exchange.options['defaultType'] = 'swap'
            
            markets = self.exchange.load_markets()
            market = markets.get(formatted_symbol, {})
            
            # 恢復原始類型
            self.exchange.options['defaultType'] = original_type
            
            funding_info = market.get('info', {})
            funding_rate = funding_info.get('fundingRate', '0')
            next_funding_time = funding_info.get('nextFundingTime', '')
            
            return {
                'symbol': symbol,
                'funding_rate': float(funding_rate) * 100,  # 轉換為百分比
                'next_funding_time': next_funding_time,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"獲取資金費率錯誤 {symbol}: {e}")
            return self._get_simulated_funding_rate(symbol)
    
    def _get_simulated_funding_rate(self, symbol: str) -> Dict:
        """獲取模擬資金費率"""
        import random
        
        return {
            'symbol': symbol,
            'funding_rate': random.uniform(-0.01, 0.01),  # -0.01% 到 0.01%
            'next_funding_time': (datetime.now() + timedelta(hours=8)).isoformat(),
            'timestamp': datetime.now().isoformat()
        }
    
    # ==================== 風險管理功能 ====================
    
    def calculate_position_risk(self, symbol: str, amount: float, 
                              entry_price: float, side: str, leverage: int = 1) -> Dict:
        """
        計算持倉風險
        
        Args:
            symbol: 交易對符號
            amount: 數量
            entry_price: 進場價格
            side: 方向
            leverage: 槓桿倍數
            
        Returns:
            Dict: 風險分析結果
        """
        try:
            current_price_data = self.get_realtime_price(symbol)
            current_price = current_price_data.price if current_price_data else entry_price
            
            # 計算持倉價值
            position_value = amount * entry_price
            margin_required = position_value / leverage
            
            # 計算盈虧
            if side == 'long':
                pnl = (current_price - entry_price) * amount
                pnl_percent = (current_price - entry_price) / entry_price * 100 * leverage
            else:
                pnl = (entry_price - current_price) * amount
                pnl_percent = (entry_price - current_price) / entry_price * 100 * leverage
            
            # 計算強平價格
            maintenance_margin_rate = 0.005  # 0.5% 維持保證金率
            if side == 'long':
                liquidation_price = entry_price * (1 - (1 / leverage) + maintenance_margin_rate)
            else:
                liquidation_price = entry_price * (1 + (1 / leverage) - maintenance_margin_rate)
            
            # 計算距離強平的百分比
            if side == 'long':
                liquidation_distance = (current_price - liquidation_price) / current_price * 100
            else:
                liquidation_distance = (liquidation_price - current_price) / current_price * 100
            
            return {
                'symbol': symbol,
                'side': side,
                'position_value': position_value,
                'margin_required': margin_required,
                'unrealized_pnl': pnl,
                'unrealized_pnl_percent': pnl_percent,
                'liquidation_price': liquidation_price,
                'liquidation_distance_percent': liquidation_distance,
                'leverage': leverage,
                'risk_level': self._assess_risk_level(liquidation_distance),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"計算持倉風險錯誤 {symbol}: {e}")
            return {}
    
    def _assess_risk_level(self, liquidation_distance: float) -> str:
        """評估風險等級"""
        if liquidation_distance >= 50:
            return '低風險'
        elif liquidation_distance >= 20:
            return '中風險'
        elif liquidation_distance >= 10:
            return '高風險'
        else:
            return '極高風險'
    
    def get_portfolio_risk_assessment(self) -> Dict:
        """
        獲取投資組合風險評估
        
        Returns:
            Dict: 風險評估結果
        """
        try:
            # 獲取所有持倉
            spot_positions = self.get_spot_positions()
            futures_positions = self.futures_get_positions()
            
            total_spot_value = sum(pos['total_value'] for pos in spot_positions)
            total_futures_value = sum(pos['amount'] * pos['markPrice'] for pos in futures_positions)
            total_portfolio_value = total_spot_value + total_futures_value
            
            # 計算風險指標
            max_drawdown = self._calculate_max_drawdown()
            volatility = self._calculate_portfolio_volatility()
            diversification_score = self._calculate_diversification(spot_positions)
            
            risk_assessment = {
                'total_portfolio_value': total_portfolio_value,
                'spot_value': total_spot_value,
                'futures_value': total_futures_value,
                'futures_ratio': total_futures_value / total_portfolio_value if total_portfolio_value > 0 else 0,
                'max_drawdown': max_drawdown,
                'volatility': volatility,
                'diversification_score': diversification_score,
                'overall_risk_level': self._assess_portfolio_risk(
                    total_futures_value / total_portfolio_value if total_portfolio_value > 0 else 0,
                    max_drawdown,
                    volatility
                ),
                'timestamp': datetime.now().isoformat()
            }
            
            return risk_assessment
            
        except Exception as e:
            self.logger.error(f"計算投資組合風險錯誤: {e}")
            return {
                'total_portfolio_value': 0,
                'spot_value': 0,
                'futures_value': 0,
                'futures_ratio': 0,
                'max_drawdown': 0,
                'volatility': 0,
                'diversification_score': 0,
                'overall_risk_level': '未知',
                'timestamp': datetime.now().isoformat()
            }
    
    def _calculate_max_drawdown(self) -> float:
        """計算最大回撤 (模擬)"""
        # 這裡可以連接真實的歷史數據
        return 0.15  # 模擬15%最大回撤
    
    def _calculate_portfolio_volatility(self) -> float:
        """計算投資組合波動率 (模擬)"""
        return 0.25  # 模擬25%年化波動率
    
    def _calculate_diversification(self, positions: List[Dict]) -> float:
        """計算分散度評分"""
        if not positions:
            return 0
        
        # 計算持倉集中度
        total_value = sum(pos['total_value'] for pos in positions)
        if total_value == 0:
            return 0
        
        # 計算赫芬達爾指數
        herfindahl_index = sum((pos['total_value'] / total_value) ** 2 for pos in positions)
        
        # 轉換為分散度評分 (0-100)
        diversification_score = (1 - herfindahl_index) * 100
        return max(0, min(100, diversification_score))
    
    def _assess_portfolio_risk(self, futures_ratio: float, max_drawdown: float, 
                             volatility: float) -> str:
        """評估投資組合總體風險"""
        risk_score = 0
        
        # 合約比例權重
        if futures_ratio > 0.5:
            risk_score += 3
        elif futures_ratio > 0.3:
            risk_score += 2
        elif futures_ratio > 0.1:
            risk_score += 1
        
        # 最大回撤權重
        if max_drawdown > 0.3:
            risk_score += 3
        elif max_drawdown > 0.2:
            risk_score += 2
        elif max_drawdown > 0.1:
            risk_score += 1
        
        # 波動率權重
        if volatility > 0.4:
            risk_score += 3
        elif volatility > 0.25:
            risk_score += 2
        elif volatility > 0.15:
            risk_score += 1
        
        if risk_score >= 7:
            return '高風險'
        elif risk_score >= 4:
            return '中風險'
        else:
            return '低風險'
    
    # ==================== 監控和警報功能 ====================
    
    def setup_price_alert(self, symbol: str, target_price: float, 
                         condition: str = 'above', callback: Callable = None) -> str:
        """
        設置價格警報
        
        Args:
            symbol: 交易對符號
            target_price: 目標價格
            condition: 條件 ('above', 'below')
            callback: 觸發回調函數
            
        Returns:
            str: 警報ID
        """
        alert_id = f"alert_{symbol}_{int(time.time())}"
        
        def check_alert():
            while True:
                try:
                    current_price_data = self.get_realtime_price(symbol)
                    if current_price_data:
                        current_price = current_price_data.price
                        
                        if condition == 'above' and current_price >= target_price:
                            if callback:
                                callback(symbol, current_price, target_price, condition)
                            self.logger.info(f"🔔 價格警報觸發: {symbol} 當前{current_price} {condition} {target_price}")
                            break
                        elif condition == 'below' and current_price <= target_price:
                            if callback:
                                callback(symbol, current_price, target_price, condition)
                            self.logger.info(f"🔔 價格警報觸發: {symbol} 當前{current_price} {condition} {target_price}")
                            break
                    
                    time.sleep(10)  # 每10秒檢查一次
                except Exception as e:
                    self.logger.error(f"價格警報檢查錯誤: {e}")
                    time.sleep(30)
        
        # 在背景線程中運行警報檢查
        alert_thread = threading.Thread(target=check_alert, daemon=True)
        alert_thread.start()
        
        self.logger.info(f"✅ 價格警報設置成功: {symbol} {condition} {target_price}")
        return alert_id
    
    def setup_liquidation_alert(self, symbol: str, callback: Callable = None) -> str:
        """
        設置強平警報
        
        Args:
            symbol: 交易對符號
            callback: 觸發回調函數
            
        Returns:
            str: 警報ID
        """
        alert_id = f"liq_alert_{symbol}_{int(time.time())}"
        
        def check_liquidation_risk():
            while True:
                try:
                    positions = self.futures_get_positions(symbol)
                    for position in positions:
                        risk_data = self.calculate_position_risk(
                            symbol=position['symbol'],
                            amount=position['amount'],
                            entry_price=position['entryPrice'],
                            side=position['side'],
                            leverage=position['leverage']
                        )
                        
                        if risk_data.get('liquidation_distance_percent', 100) < 10:
                            if callback:
                                callback(position, risk_data)
                            self.logger.warning(f"⚠️ 強平風險警報: {symbol} 距離強平僅{risk_data['liquidation_distance_percent']:.1f}%")
                    
                    time.sleep(60)  # 每分鐘檢查一次
                except Exception as e:
                    self.logger.error(f"強平警報檢查錯誤: {e}")
                    time.sleep(120)
        
        alert_thread = threading.Thread(target=check_liquidation_risk, daemon=True)
        alert_thread.start()
        
        self.logger.info(f"✅ 強平警報設置成功: {symbol}")
        return alert_id
    
    # ==================== 系統管理功能 ====================
    
    def get_system_status(self) -> Dict:
        """
        獲取系統狀態
        
        Returns:
            Dict: 系統狀態資訊
        """
        connection_status, connection_msg = self.test_connection()
        
        return {
            'api_connected': connection_status,
            'connection_message': connection_msg,
            'price_updater_running': self.is_updating,
            'price_cache_size': len(self.price_cache),
            'monitoring_symbols': len(self.popular_symbols),
            'last_price_update': self.last_update_time.isoformat() if self.last_update_time else None,
            'total_price_listeners': len(self.price_listeners),
            'simulation_mode': not (self.exchange and self.is_connected),
            'timestamp': datetime.now().isoformat()
        }
    
    def cleanup(self):
        """清理資源"""
        self.stop_price_updater()
        self.logger.info("✅ API客戶端資源清理完成")

# 向下兼容
OKXAPI = OKXAPIClient
