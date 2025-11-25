# modules/technical_indicators.py
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass

@dataclass
class IndicatorConfig:
    """技術指標配置設定"""
    # 移動平均線週期
    sma_periods: List[int] = None
    ema_periods: List[int] = None
    
    # RSI 週期
    rsi_periods: List[int] = None
    
    # MACD 參數
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # 布林帶參數
    bb_period: int = 20
    bb_std: int = 2
    
    # 其他指標週期
    stoch_period: int = 14
    atr_period: int = 14
    adx_period: int = 14
    
    def __post_init__(self):
        if self.sma_periods is None:
            self.sma_periods = [5, 10, 20, 50, 200]
        if self.ema_periods is None:
            self.ema_periods = [12, 26]
        if self.rsi_periods is None:
            self.rsi_periods = [6, 12, 24]

class TechnicalIndicators:
    def __init__(self, config: IndicatorConfig = None):
        """
        初始化技術指標系統
        
        Args:
            config: 指標配置設定
        """
        self.config = config or IndicatorConfig()
        self.logger = self._setup_logger()
        self.indicators_cache = {}
        
    def _setup_logger(self):
        """設置日誌記錄器"""
        logger = logging.getLogger('TechnicalIndicators')
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

    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        驗證輸入數據的完整性
        
        Args:
            df: 輸入的數據框
            
        Returns:
            bool: 數據是否有效
        """
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        
        if not all(col in df.columns for col in required_columns):
            self.logger.error(f"數據缺少必要欄位，需要: {required_columns}")
            return False
            
        if df.isnull().values.any():
            self.logger.warning("數據包含空值，將嘗試填充")
            df.fillna(method='ffill', inplace=True)
            df.fillna(method='bfill', inplace=True)
            
        if len(df) < max(self.config.sma_periods + self.config.ema_periods):
            self.logger.error("數據長度不足，無法計算技術指標")
            return False
            
        return True

    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算所有技術指標 - 主要入口函數
        
        Args:
            df: 包含OHLCV數據的DataFrame
            
        Returns:
            pd.DataFrame: 包含所有技術指標的DataFrame
        """
        try:
            self.logger.info("開始計算技術指標...")
            
            # 驗證數據
            if not self.validate_data(df):
                raise ValueError("數據驗證失敗")
            
            # 複製原始數據避免修改
            result_df = df.copy()
            
            # 計算各類指標
            result_df = self.calculate_trend_indicators(result_df)
            result_df = self.calculate_momentum_indicators(result_df)
            result_df = self.calculate_volatility_indicators(result_df)
            result_df = self.calculate_volume_indicators(result_df)
            result_df = self.calculate_other_indicators(result_df)
            
            # 清理臨時欄位
            result_df = self._clean_temporary_columns(result_df)
            
            self.logger.info("技術指標計算完成")
            return result_df
            
        except Exception as e:
            self.logger.error(f"計算技術指標時發生錯誤: {str(e)}")
            return df

    def calculate_trend_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算趨勢指標 - 優化版本
        
        Args:
            df: 輸入數據框
            
        Returns:
            pd.DataFrame: 包含趨勢指標的數據框
        """
        try:
            self.logger.info("計算趨勢指標...")
            
            # 簡單移動平均線 (SMA)
            for period in self.config.sma_periods:
                df[f'sma_{period}'] = self._calculate_sma(df['close'], period)
                # 計算價格與移動平均線的關係
                df[f'price_vs_sma_{period}'] = (df['close'] - df[f'sma_{period}']) / df[f'sma_{period}'] * 100

            # 指數移動平均線 (EMA)
            for period in self.config.ema_periods:
                df[f'ema_{period}'] = self._calculate_ema(df['close'], period)

            # 雙重指數移動平均線 (DEMA)
            df['dema_12'] = self._calculate_dema(df['close'], 12)
            df['dema_26'] = self._calculate_dema(df['close'], 26)

            # 三重指數移動平均線 (TEMA)
            df['tema_12'] = self._calculate_tema(df['close'], 12)
            df['tema_26'] = self._calculate_tema(df['close'], 26)

            # 布林帶 (Bollinger Bands) - 優化計算
            df = self._calculate_bollinger_bands(df)

            # 抛物轉向指標 (Parabolic SAR) - 改進算法
            df['parabolic_sar'] = self._calculate_enhanced_parabolic_sar(df)

            # 平均方向指數 (ADX) - 包含DI+和DI-
            adx_indicators = self._calculate_adx_system(df, self.config.adx_period)
            df = pd.concat([df, adx_indicators], axis=1)

            # 移動平均線交叉信號
            df = self._calculate_ma_cross_signals(df)

            # 趨勢強度指標
            df['trend_strength'] = self._calculate_trend_strength(df)

            self.logger.info("趨勢指標計算完成")
            return df

        except Exception as e:
            self.logger.error(f"計算趨勢指標錯誤: {str(e)}")
            return df

    def _calculate_sma(self, series: pd.Series, period: int) -> pd.Series:
        """計算簡單移動平均線"""
        return series.rolling(window=period, min_periods=1).mean()

    def _calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """計算指數移動平均線"""
        return series.ewm(span=period, adjust=False).mean()

    def _calculate_dema(self, series: pd.Series, period: int) -> pd.Series:
        """計算雙重指數移動平均線"""
        ema = series.ewm(span=period).mean()
        ema_of_ema = ema.ewm(span=period).mean()
        return 2 * ema - ema_of_ema

    def _calculate_tema(self, series: pd.Series, period: int) -> pd.Series:
        """計算三重指數移動平均線"""
        ema1 = series.ewm(span=period).mean()
        ema2 = ema1.ewm(span=period).mean()
        ema3 = ema2.ewm(span=period).mean()
        return 3 * (ema1 - ema2) + ema3

    def _calculate_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算布林帶 - 優化版本"""
        period = self.config.bb_period
        std_multiplier = self.config.bb_std
        
        middle_band = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        
        df['bb_middle'] = middle_band
        df['bb_upper'] = middle_band + (std * std_multiplier)
        df['bb_lower'] = middle_band - (std * std_multiplier)
        
        # 布林帶寬度 (Band Width)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # 布林帶位置 (%B)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # 布林帶擠壓 (Squeeze)
        df['bb_squeeze'] = (df['bb_width'] - df['bb_width'].rolling(20).min()) / \
                          (df['bb_width'].rolling(20).max() - df['bb_width'].rolling(20).min())
        
        return df

    def _calculate_enhanced_parabolic_sar(self, df: pd.DataFrame, 
                                        acceleration: float = 0.02, 
                                        max_acceleration: float = 0.2) -> pd.Series:
        """
        改進的抛物轉向指標計算
        
        Args:
            df: 包含高低收盤價的數據框
            acceleration: 加速因子
            max_acceleration: 最大加速因子
            
        Returns:
            pd.Series: SAR 值
        """
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        sar = np.zeros(len(high))
        trend = np.zeros(len(high))
        ep = np.zeros(len(high))
        af = np.zeros(len(high))
        
        # 初始化
        sar[0] = low[0] if close[0] > high[0] else high[0]
        trend[0] = 1 if close[0] > high[0] else -1
        ep[0] = high[0] if trend[0] == 1 else low[0]
        af[0] = acceleration
        
        for i in range(1, len(high)):
            # 反轉邏輯
            if trend[i-1] == 1:
                if low[i] < sar[i-1]:
                    trend[i] = -1
                    sar[i] = ep[i-1]
                    ep[i] = low[i]
                    af[i] = acceleration
                else:
                    trend[i] = 1
                    if high[i] > ep[i-1]:
                        ep[i] = high[i]
                        af[i] = min(af[i-1] + acceleration, max_acceleration)
                    else:
                        ep[i] = ep[i-1]
                        af[i] = af[i-1]
                    sar[i] = sar[i-1] + af[i] * (ep[i] - sar[i-1])
                    sar[i] = min(sar[i], low[i-1], low[i])
            else:
                if high[i] > sar[i-1]:
                    trend[i] = 1
                    sar[i] = ep[i-1]
                    ep[i] = high[i]
                    af[i] = acceleration
                else:
                    trend[i] = -1
                    if low[i] < ep[i-1]:
                        ep[i] = low[i]
                        af[i] = min(af[i-1] + acceleration, max_acceleration)
                    else:
                        ep[i] = ep[i-1]
                        af[i] = af[i-1]
                    sar[i] = sar[i-1] + af[i] * (ep[i] - sar[i-1])
                    sar[i] = max(sar[i], high[i-1], high[i])
        
        return pd.Series(sar, index=df.index)

    def _calculate_adx_system(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        計算完整的ADX系統 (包含+DI, -DI, ADX)
        
        Args:
            df: 輸入數據框
            period: 計算週期
            
        Returns:
            pd.DataFrame: 包含ADX系統指標的數據框
        """
        # 計算真實波動幅度 (True Range)
        tr = self._calculate_true_range(df)
        
        # 計算方向移動 (Directional Movement)
        up_move = df['high'].diff()
        down_move = df['low'].diff().abs()
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # 計算平滑值
        tr_smooth = tr.rolling(window=period).mean()
        plus_dm_smooth = pd.Series(plus_dm, index=df.index).rolling(window=period).mean()
        minus_dm_smooth = pd.Series(minus_dm, index=df.index).rolling(window=period).mean()
        
        # 計算方向指標 (Directional Indicators)
        plus_di = 100 * (plus_dm_smooth / tr_smooth)
        minus_di = 100 * (minus_dm_smooth / tr_smooth)
        
        # 計算方向指數 (Directional Index)
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # 計算平均方向指數 (Average Directional Index)
        adx = dx.rolling(window=period).mean()
        
        return pd.DataFrame({
            'adx_plus_di': plus_di,
            'adx_minus_di': minus_di,
            'adx': adx
        }, index=df.index)

    def _calculate_true_range(self, df: pd.DataFrame) -> pd.Series:
        """計算真實波動幅度"""
        high_low = df['high'] - df['low']
        high_close_prev = abs(df['high'] - df['close'].shift(1))
        low_close_prev = abs(df['low'] - df['close'].shift(1))
        
        tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        return tr

    def _calculate_ma_cross_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算移動平均線交叉信號"""
        try:
            # 短期與長期移動平均線交叉
            df['sma_cross_signal'] = 0
            
            # 金叉 (Golden Cross)
            golden_cross = (df['sma_5'] > df['sma_20']) & (df['sma_5'].shift(1) <= df['sma_20'].shift(1))
            df.loc[golden_cross, 'sma_cross_signal'] = 1
            
            # 死叉 (Death Cross)
            death_cross = (df['sma_5'] < df['sma_20']) & (df['sma_5'].shift(1) >= df['sma_20'].shift(1))
            df.loc[death_cross, 'sma_cross_signal'] = -1
            
            # EMA 交叉信號
            df['ema_cross_signal'] = np.where(df['ema_12'] > df['ema_26'], 1, -1)
            
            return df
            
        except Exception as e:
            self.logger.warning(f"計算移動平均線交叉信號時發生錯誤: {str(e)}")
            return df

    def _calculate_trend_strength(self, df: pd.DataFrame) -> pd.Series:
        """計算趨勢強度"""
        try:
            # 使用多個指標綜合判斷趨勢強度
            factors = []
            
            # ADX 趨勢強度
            if 'adx' in df.columns:
                adx_strength = (df['adx'] - 20) / 60  # 歸一化到 0-1
                factors.append(adx_strength.clip(0, 1))
            
            # 移動平均線斜率
            if 'sma_20' in df.columns:
                ma_slope = df['sma_20'].pct_change(5).abs()
                factors.append(ma_slope / ma_slope.rolling(50).max())
            
            # 價格波動率
            price_volatility = df['close'].pct_change().rolling(10).std()
            factors.append(price_volatility / price_volatility.rolling(50).max())
            
            # 綜合趨勢強度
            if factors:
                trend_strength = pd.concat(factors, axis=1).mean(axis=1)
                return trend_strength
            else:
                return pd.Series(0, index=df.index)
                
        except Exception as e:
            self.logger.warning(f"計算趨勢強度時發生錯誤: {str(e)}")
            return pd.Series(0, index=df.index)

    def _clean_temporary_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理臨時計算欄位"""
        columns_to_keep = [col for col in df.columns if not col.startswith('temp_')]
        return df[columns_to_keep]

    def get_indicator_descriptions(self) -> Dict:
        """取得技術指標說明"""
        return {
            'sma': '簡單移動平均線 - 反映價格趨勢方向',
            'ema': '指數移動平均線 - 對近期價格賦予較高權重',
            'dema': '雙重指數移動平均線 - 減少滯後性',
            'tema': '三重指數移動平均線 - 進一步減少滯後性',
            'bb_middle': '布林帶中線 - 移動平均線',
            'bb_upper': '布林帶上軌 - 阻力位參考',
            'bb_lower': '布林帶下軌 - 支撐位參考',
            'bb_width': '布林帶寬度 - 波動率指標',
            'bb_position': '布林帶位置 - 價格在布林帶中的相對位置',
            'parabolic_sar': '抛物轉向指標 - 趨勢反轉信號',
            'adx_plus_di': '正向方向指標 - 上漲趨勢強度',
            'adx_minus_di': '負向方向指標 - 下跌趨勢強度',
            'adx': '平均方向指數 - 整體趨勢強度',
            'trend_strength': '趨勢強度 - 綜合趨勢強度指標'
        }

# 使用範例
if __name__ == "__main__":
    # 創建配置
    config = IndicatorConfig(
        sma_periods=[5, 10, 20, 50, 100],
        ema_periods=[12, 26, 50],
        rsi_periods=[6, 14, 24]
    )
    
    # 初始化技術指標系統
    ti = TechnicalIndicators(config)
    
    # 顯示指標說明
    descriptions = ti.get_indicator_descriptions()
    for name, desc in descriptions.items():
        print(f"{name}: {desc}")
class TechnicalIndicators:
    def calculate_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算動量指標 - 優化版本
        
        Args:
            df: 輸入數據框
            
        Returns:
            pd.DataFrame: 包含動量指標的數據框
        """
        try:
            self.logger.info("計算動量指標...")
            
            # RSI 系列指標
            df = self._calculate_rsi_series(df)
            
            # MACD 系統指標
            df = self._calculate_macd_system(df)
            
            # 隨機指標 (Stochastic)
            df = self._calculate_stochastic_oscillator(df)
            
            # 商品通道指數 (CCI)
            df['cci'] = self._calculate_cci(df, 20)
            
            # 威廉指標 (Williams %R)
            df['williams_r'] = self._calculate_williams_r(df, 14)
            
            # 動量指標 (Momentum)
            df = self._calculate_momentum_indicators_series(df)
            
            # 價格變化率 (ROC)
            df = self._calculate_rate_of_change(df)
            
            # 相對動量指數 (RMI)
            df['rmi_20_5'] = self._calculate_rmi(df, 20, 5)
            
            # 終極震盪指標 (Ultimate Oscillator)
            df['ultimate_oscillator'] = self._calculate_ultimate_oscillator(df)
            
            # 動量轉向指標 (Chande Momentum Oscillator)
            df['cmo'] = self._calculate_cmo(df, 14)
            
            # 動量信號
            df = self._generate_momentum_signals(df)
            
            self.logger.info("動量指標計算完成")
            return df
            
        except Exception as e:
            self.logger.error(f"計算動量指標錯誤: {str(e)}")
            return df

    def _calculate_rsi_series(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算RSI系列指標"""
        for period in self.config.rsi_periods:
            df[f'rsi_{period}'] = self._calculate_enhanced_rsi(df['close'], period)
            
            # RSI 動量
            df[f'rsi_momentum_{period}'] = df[f'rsi_{period}'].diff(3)
            
            # RSI 背離檢測
            df[f'rsi_divergence_{period}'] = self._detect_rsi_divergence(df, period)
        
        # RSI 綜合強度
        rsi_columns = [f'rsi_{p}' for p in self.config.rsi_periods]
        if all(col in df.columns for col in rsi_columns):
            df['rsi_strength'] = df[rsi_columns].mean(axis=1)
            
        return df

    def _calculate_enhanced_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        改進的RSI計算，包含平滑處理
        
        Args:
            prices: 價格序列
            period: 計算週期
            
        Returns:
            pd.Series: RSI 值
        """
        try:
            delta = prices.diff()
            
            # 使用EMA平滑增益和損失
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            
            # 使用Wilder平滑方法 (RSI標準方法)
            avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
            
            # 避免除零
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            
            # 填充初始值
            rsi = rsi.fillna(50)
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"計算RSI錯誤 (週期{period}): {str(e)}")
            return pd.Series(50, index=prices.index)

    def _detect_rsi_divergence(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        檢測RSI背離
        
        Args:
            df: 數據框
            period: RSI週期
            
        Returns:
            pd.Series: 背離信號
        """
        try:
            rsi_col = f'rsi_{period}'
            if rsi_col not in df.columns:
                return pd.Series(0, index=df.index)
                
            # 尋找局部極值
            rsi_highs = self._find_local_extrema(df[rsi_col], 'high', 5)
            rsi_lows = self._find_local_extrema(df[rsi_col], 'low', 5)
            price_highs = self._find_local_extrema(df['close'], 'high', 5)
            price_lows = self._find_local_extrema(df['close'], 'low', 5)
            
            divergence = pd.Series(0, index=df.index)
            
            # 檢測看跌背離 (價格新高，RSI未新高)
            for i in range(1, len(price_highs)):
                if price_highs[i] and rsi_highs[i]:
                    if (df['close'].iloc[i] > df['close'].iloc[i-5:i].max() and 
                        df[rsi_col].iloc[i] < df[rsi_col].iloc[i-5:i].max()):
                        divergence.iloc[i] = -1
            
            # 檢測看漲背離 (價格新低，RSI未新低)
            for i in range(1, len(price_lows)):
                if price_lows[i] and rsi_lows[i]:
                    if (df['close'].iloc[i] < df['close'].iloc[i-5:i].min() and 
                        df[rsi_col].iloc[i] > df[rsi_col].iloc[i-5:i].min()):
                        divergence.iloc[i] = 1
                        
            return divergence
            
        except Exception as e:
            self.logger.warning(f"檢測RSI背離錯誤: {str(e)}")
            return pd.Series(0, index=df.index)

    def _find_local_extrema(self, series: pd.Series, extrema_type: str, window: int) -> pd.Series:
        """尋找局部極值點"""
        if extrema_type == 'high':
            return (series == series.rolling(window, center=True).max()) & (series.notna())
        else:  # 'low'
            return (series == series.rolling(window, center=True).min()) & (series.notna())

    def _calculate_macd_system(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算完整的MACD系統"""
        try:
            fast = self.config.macd_fast
            slow = self.config.macd_slow
            signal = self.config.macd_signal
            
            # 計算MACD
            ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
            ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
            macd = ema_fast - ema_slow
            macd_signal = macd.ewm(span=signal, adjust=False).mean()
            macd_histogram = macd - macd_signal
            
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_histogram'] = macd_histogram
            
            # MACD 動量
            df['macd_momentum'] = macd.diff(3)
            
            # MACD 背離檢測
            df['macd_divergence'] = self._detect_macd_divergence(df)
            
            # MACD 趨勢強度
            df['macd_trend_strength'] = macd_histogram.abs().rolling(10).mean()
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算MACD系統錯誤: {str(e)}")
            return df

    def _detect_macd_divergence(self, df: pd.DataFrame) -> pd.Series:
        """檢測MACD背離"""
        try:
            macd_highs = self._find_local_extrema(df['macd'], 'high', 5)
            macd_lows = self._find_local_extrema(df['macd'], 'low', 5)
            price_highs = self._find_local_extrema(df['close'], 'high', 5)
            price_lows = self._find_local_extrema(df['close'], 'low', 5)
            
            divergence = pd.Series(0, index=df.index)
            
            # MACD看跌背離
            for i in range(1, len(price_highs)):
                if price_highs[i] and macd_highs[i]:
                    if (df['close'].iloc[i] > df['close'].iloc[i-5:i].max() and 
                        df['macd'].iloc[i] < df['macd'].iloc[i-5:i].max()):
                        divergence.iloc[i] = -1
            
            # MACD看漲背離
            for i in range(1, len(price_lows)):
                if price_lows[i] and macd_lows[i]:
                    if (df['close'].iloc[i] < df['close'].iloc[i-5:i].min() and 
                        df['macd'].iloc[i] > df['macd'].iloc[i-5:i].min()):
                        divergence.iloc[i] = 1
                        
            return divergence
            
        except Exception as e:
            self.logger.warning(f"檢測MACD背離錯誤: {str(e)}")
            return pd.Series(0, index=df.index)

    def _calculate_stochastic_oscillator(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算隨機震盪指標"""
        try:
            period = self.config.stoch_period
            
            # 快速隨機指標 (%K, %D)
            lowest_low = df['low'].rolling(window=period).min()
            highest_high = df['high'].rolling(window=period).max()
            
            df['stoch_k'] = 100 * (df['close'] - lowest_low) / (highest_high - lowest_low)
            df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
            
            # 慢速隨機指標 (Slow %D)
            df['stoch_slow_d'] = df['stoch_d'].rolling(window=3).mean()
            
            # 隨機指標動量
            df['stoch_momentum'] = df['stoch_k'] - df['stoch_d']
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算隨機指標錯誤: {str(e)}")
            return df

    def _calculate_cci(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """計算商品通道指數"""
        try:
            tp = (df['high'] + df['low'] + df['close']) / 3
            sma_tp = tp.rolling(window=period).mean()
            
            # 平均偏差
            mad = tp.rolling(window=period).apply(
                lambda x: np.mean(np.abs(x - np.mean(x))), 
                raw=False
            )
            
            cci = (tp - sma_tp) / (0.015 * mad)
            return cci
            
        except Exception as e:
            self.logger.error(f"計算CCI錯誤: {str(e)}")
            return pd.Series(0, index=df.index)

    def _calculate_williams_r(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """計算威廉指標"""
        try:
            highest_high = df['high'].rolling(window=period).max()
            lowest_low = df['low'].rolling(window=period).min()
            
            williams_r = -100 * (highest_high - df['close']) / (highest_high - lowest_low)
            return williams_r
            
        except Exception as e:
            self.logger.error(f"計算威廉指標錯誤: {str(e)}")
            return pd.Series(-50, index=df.index)

    def _calculate_momentum_indicators_series(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算動量指標系列"""
        try:
            # 不同週期的動量
            periods = [5, 10, 20]
            for period in periods:
                df[f'momentum_{period}'] = df['close'] - df['close'].shift(period)
                df[f'momentum_ratio_{period}'] = df['close'] / df['close'].shift(period) - 1
            
            # 動量加速度
            df['momentum_acceleration'] = df['momentum_5'].diff(3)
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算動量指標系列錯誤: {str(e)}")
            return df

    def _calculate_rate_of_change(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算價格變化率系列"""
        try:
            periods = [5, 10, 20]
            for period in periods:
                df[f'roc_{period}'] = ((df['close'] - df['close'].shift(period)) / 
                                     df['close'].shift(period)) * 100
            
            # ROC 動量
            df['roc_momentum'] = df['roc_10'].diff(3)
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算價格變化率錯誤: {str(e)}")
            return df

    def _calculate_rmi(self, df: pd.DataFrame, period: int = 20, momentum_period: int = 5) -> pd.Series:
        """計算相對動量指數"""
        try:
            # RMI 是 RSI 的變體，使用動量而不是單一週期變化
            price_change = df['close'].diff(momentum_period)
            
            gain = price_change.where(price_change > 0, 0)
            loss = -price_change.where(price_change < 0, 0)
            
            avg_gain = gain.ewm(span=period, adjust=False).mean()
            avg_loss = loss.ewm(span=period, adjust=False).mean()
            
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rmi = 100 - (100 / (1 + rs))
            
            return rmi.fillna(50)
            
        except Exception as e:
            self.logger.error(f"計算RMI錯誤: {str(e)}")
            return pd.Series(50, index=df.index)

    def _calculate_ultimate_oscillator(self, df: pd.DataFrame) -> pd.Series:
        """計算終極震盪指標"""
        try:
            # 計算三個不同時間框架的壓力值
            bp1 = df['close'] - pd.concat([
                df['low'], 
                df['close'].shift(1)
            ], axis=1).min(axis=1)
            
            tr1 = pd.concat([
                df['high'] - df['low'],
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            ], axis=1).max(axis=1)
            
            # 7日平均值
            avg7_bp = bp1.rolling(7).sum()
            avg7_tr = tr1.rolling(7).sum()
            
            # 14日平均值
            avg14_bp = bp1.rolling(14).sum()
            avg14_tr = tr1.rolling(14).sum()
            
            # 28日平均值
            avg28_bp = bp1.rolling(28).sum()
            avg28_tr = tr1.rolling(28).sum()
            
            # 計算三個震盪值
            uo1 = avg7_bp / avg7_tr if avg7_tr != 0 else 0
            uo2 = avg14_bp / avg14_tr if avg14_tr != 0 else 0
            uo3 = avg28_bp / avg28_tr if avg28_tr != 0 else 0
            
            # 加權組合
            ultimate_oscillator = 100 * ((4 * uo1) + (2 * uo2) + uo3) / 7
            
            return ultimate_oscillator
            
        except Exception as e:
            self.logger.error(f"計算終極震盪指標錯誤: {str(e)}")
            return pd.Series(50, index=df.index)

    def _calculate_cmo(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """計算錢德動量擺盪指標"""
        try:
            price_change = df['close'].diff()
            
            gain = price_change.where(price_change > 0, 0)
            loss = -price_change.where(price_change < 0, 0)
            
            sum_gain = gain.rolling(period).sum()
            sum_loss = loss.rolling(period).sum()
            
            cmo = 100 * (sum_gain - sum_loss) / (sum_gain + sum_loss)
            
            return cmo.fillna(0)
            
        except Exception as e:
            self.logger.error(f"計算CMO錯誤: {str(e)}")
            return pd.Series(0, index=df.index)

    def _generate_momentum_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成動量信號"""
        try:
            # 綜合動量強度
            momentum_factors = []
            
            if 'rsi_14' in df.columns:
                rsi_strength = (df['rsi_14'] - 50) / 50  # -1 到 1
                momentum_factors.append(rsi_strength)
            
            if 'macd_histogram' in df.columns:
                macd_strength = df['macd_histogram'] / df['macd_histogram'].abs().rolling(50).mean()
                momentum_factors.append(macd_strength.clip(-2, 2))
            
            if 'stoch_k' in df.columns:
                stoch_strength = (df['stoch_k'] - 50) / 50  # -1 到 1
                momentum_factors.append(stoch_strength)
            
            if momentum_factors:
                df['momentum_strength'] = pd.concat(momentum_factors, axis=1).mean(axis=1)
            
            # 動量信號
            df['momentum_signal'] = 0
            df.loc[df['momentum_strength'] > 0.3, 'momentum_signal'] = 1  # 強勢
            df.loc[df['momentum_strength'] < -0.3, 'momentum_signal'] = -1  # 弱勢
            
            return df
            
        except Exception as e:
            self.logger.warning(f"生成動量信號錯誤: {str(e)}")
            return df

    def calculate_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算波動率指標 - 優化版本
        
        Args:
            df: 輸入數據框
            
        Returns:
            pd.DataFrame: 包含波動率指標的數據框
        """
        try:
            self.logger.info("計算波動率指標...")
            
            # 平均真實範圍 (ATR) 系統
            df = self._calculate_atr_system(df)
            
            # 標準差指標
            df = self._calculate_std_indicators(df)
            
            # 波動率指標
            df = self._calculate_volatility_measures(df)
            
            # 真實波動幅度
            df['true_range'] = self._calculate_true_range(df)
            
            # 波動率通道
            df = self._calculate_volatility_channels(df)
            
            # 波動率比率
            df = self._calculate_volatility_ratios(df)
            
            # 波動率狀態
            df = self._assess_volatility_regime(df)
            
            self.logger.info("波動率指標計算完成")
            return df
            
        except Exception as e:
            self.logger.error(f"計算波動率指標錯誤: {str(e)}")
            return df

    def _calculate_atr_system(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算ATR系統指標"""
        try:
            period = self.config.atr_period
            
            # 計算真實範圍
            tr = self._calculate_true_range(df)
            
            # 標準ATR
            df['atr'] = tr.rolling(period).mean()
            
            # ATR百分比 (標準化)
            df['atr_percentage'] = (df['atr'] / df['close']) * 100
            
            # ATR動量
            df['atr_momentum'] = df['atr'].pct_change(5)
            
            # ATR突破水平
            df['atr_upper_band'] = df['close'] + (2 * df['atr'])
            df['atr_lower_band'] = df['close'] - (2 * df['atr'])
            
            # ATR趨勢
            df['atr_trend'] = np.where(df['atr'] > df['atr'].rolling(20).mean(), 1, -1)
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算ATR系統錯誤: {str(e)}")
            return df

    def _calculate_std_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算標準差指標"""
        try:
            periods = [10, 20, 50]
            
            for period in periods:
                # 價格標準差
                df[f'std_{period}'] = df['close'].rolling(period).std()
                
                # 標準化標準差
                df[f'std_percentage_{period}'] = (df[f'std_{period}'] / df['close']) * 100
                
                # 標準差通道
                df[f'std_upper_{period}'] = df['close'].rolling(period).mean() + (2 * df[f'std_{period}'])
                df[f'std_lower_{period}'] = df['close'].rolling(period).mean() - (2 * df[f'std_{period}'])
            
            # 短期/長期標準差比率
            df['std_ratio_10_50'] = df['std_10'] / df['std_50']
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算標準差指標錯誤: {str(e)}")
            return df

    def _calculate_volatility_measures(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算波動率測量"""
        try:
            # 日報酬率
            returns = df['close'].pct_change()
            
            # 歷史波動率 (年化)
            df['volatility_10'] = returns.rolling(10).std() * np.sqrt(365)
            df['volatility_20'] = returns.rolling(20).std() * np.sqrt(365)
            df['volatility_50'] = returns.rolling(50).std() * np.sqrt(365)
            
            # 已實現波動率
            df['realized_volatility_20'] = returns.rolling(20).std() * np.sqrt(365)
            
            # 波動率的波動率
            df['vol_of_vol'] = df['volatility_20'].pct_change().rolling(10).std()
            
            # 偏度和峰度
            df['returns_skew_20'] = returns.rolling(20).skew()
            df['returns_kurtosis_20'] = returns.rolling(20).kurtosis()
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算波動率測量錯誤: {str(e)}")
            return df

    def _calculate_volatility_channels(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算波動率通道"""
        try:
            # Keltner通道 (基於ATR)
            period = 20
            ema = df['close'].ewm(span=period).mean()
            
            if 'atr' in df.columns:
                df['keltner_upper'] = ema + (2 * df['atr'])
                df['keltner_lower'] = ema - (2 * df['atr'])
                df['keltner_middle'] = ema
            
            # Donchian通道
            df['donchian_upper'] = df['high'].rolling(20).max()
            df['donchian_lower'] = df['low'].rolling(20).min()
            df['donchian_middle'] = (df['donchian_upper'] + df['donchian_lower']) / 2
            
            # 通道寬度
            if 'keltner_upper' in df.columns:
                df['keltner_width'] = (df['keltner_upper'] - df['keltner_lower']) / df['keltner_middle']
            
            df['donchian_width'] = (df['donchian_upper'] - df['donchian_lower']) / df['donchian_middle']
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算波動率通道錯誤: {str(e)}")
            return df

    def _calculate_volatility_ratios(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算波動率比率"""
        try:
            returns = df['close'].pct_change()
            
            # 夏普比率 (簡化版)
            df['sharpe_ratio_20'] = (returns.rolling(20).mean() * 365) / (returns.rolling(20).std() * np.sqrt(365))
            
            # 變異係數
            df['coefficient_of_variation'] = df['std_20'] / df['close'].rolling(20).mean()
            
            # 波動率偏斜
            positive_vol = returns[returns > 0].rolling(20).std() * np.sqrt(365)
            negative_vol = (-returns[returns < 0]).rolling(20).std() * np.sqrt(365)
            df['volatility_skew'] = positive_vol - negative_vol
            
            # 平靜/波動比率
            df['calm_to_storm_ratio'] = df['volatility_10'] / df['volatility_50']
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算波動率比率錯誤: {str(e)}")
            return df

    def _assess_volatility_regime(self, df: pd.DataFrame) -> pd.DataFrame:
        """評估波動率狀態"""
        try:
            # 波動率狀態
            volatility_20_ma = df['volatility_20'].rolling(50).mean()
            volatility_ratio = df['volatility_20'] / volatility_20_ma
            
            df['volatility_regime'] = 0  # 正常
            df.loc[volatility_ratio > 1.5, 'volatility_regime'] = 1  # 高波動
            df.loc[volatility_ratio < 0.7, 'volatility_regime'] = -1  # 低波動
            
            # 波動率突破信號
            df['volatility_breakout'] = 0
            df.loc[df['true_range'] > df['true_range'].rolling(20).mean() * 1.5, 'volatility_breakout'] = 1
            df.loc[df['true_range'] < df['true_range'].rolling(20).mean() * 0.5, 'volatility_breakout'] = -1
            
            # 綜合波動率分數
            vol_factors = [
                df['atr_percentage'] / df['atr_percentage'].rolling(50).mean(),
                df['volatility_20'] / df['volatility_20'].rolling(50).mean(),
                df['std_percentage_20'] / df['std_percentage_20'].rolling(50).mean()
            ]
            
            df['volatility_score'] = pd.concat(vol_factors, axis=1).mean(axis=1)
            
            return df
            
        except Exception as e:
            self.logger.warning(f"評估波動率狀態錯誤: {str(e)}")
            return df

    # 更新指標說明方法
    def get_momentum_descriptions(self) -> Dict:
        """取得動量指標說明"""
        return {
            'rsi': '相對強弱指數 - 衡量價格動量強度',
            'macd': '指數平滑異同移動平均線 - 趨勢動量指標',
            'stoch_k': '隨機指標%K - 價格在近期範圍內的位置',
            'stoch_d': '隨機指標%D - %K的移動平均',
            'cci': '商品通道指數 - 衡量價格偏離統計平均的程度',
            'williams_r': '威廉指標 - 超買超賣指標',
            'momentum': '動量指標 - 價格變化速度',
            'roc': '價格變化率 - 價格變動百分比',
            'rmi': '相對動量指數 - RSI的改進版本',
            'ultimate_oscillator': '終極震盪指標 - 多時間框架動量'
        }

    def get_volatility_descriptions(self) -> Dict:
        """取得波動率指標說明"""
        return {
            'atr': '平均真實範圍 - 價格波動性衡量',
            'atr_percentage': 'ATR百分比 - 標準化波動率',
            'volatility_20': '20日歷史波動率 - 年化價格波動',
            'std_20': '20日標準差 - 價格分散程度',
            'true_range': '真實波動幅度 - 單日最大可能波動',
            'keltner_upper': '肯特納通道上軌 - 波動率基礎阻力',
            'keltner_lower': '肯特納通道下軌 - 波動率基礎支撐',
            'volatility_regime': '波動率狀態 - 市場波動環境分類'
        }
class TechnicalIndicators:
    def calculate_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算成交量指標 - 優化版本
        
        Args:
            df: 輸入數據框
            
        Returns:
            pd.DataFrame: 包含成交量指標的數據框
        """
        try:
            self.logger.info("計算成交量指標...")
            
            # 基礎成交量指標
            df = self._calculate_basic_volume_indicators(df)
            
            # 成交量移動平均
            df = self._calculate_volume_moving_averages(df)
            
            # 能量潮 (OBV) 系統
            df = self._calculate_obv_system(df)
            
            # 資金流量指數 (MFI)
            df['mfi'] = self._calculate_mfi(df, 14)
            
            # 成交量加權平均價 (VWAP)
            df['vwap'] = self._calculate_vwap(df)
            
            # 成交量震盪指標
            df = self._calculate_volume_oscillators(df)
            
            # 成交量價格確認
            df = self._calculate_volume_price_confirmation(df)
            
            # 成交量分佈分析
            df = self._calculate_volume_profile_indicators(df)
            
            # 成交量信號
            df = self._generate_volume_signals(df)
            
            self.logger.info("成交量指標計算完成")
            return df
            
        except Exception as e:
            self.logger.error(f"計算成交量指標錯誤: {str(e)}")
            return df

    def _calculate_basic_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算基礎成交量指標"""
        try:
            # 成交量變化率
            df['volume_change'] = df['volume'].pct_change()
            
            # 成交量標準差
            df['volume_std_10'] = df['volume'].rolling(10).std()
            df['volume_std_20'] = df['volume'].rolling(20).std()
            
            # 成交量相對強弱
            df['volume_relative_strength'] = df['volume'] / df['volume'].rolling(50).mean()
            
            # 成交量異常檢測
            volume_ma = df['volume'].rolling(20).mean()
            volume_std = df['volume'].rolling(20).std()
            df['volume_anomaly'] = (df['volume'] - volume_ma) / volume_std
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算基礎成交量指標錯誤: {str(e)}")
            return df

    def _calculate_volume_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算成交量移動平均"""
        try:
            periods = [5, 10, 20, 50]
            
            for period in periods:
                df[f'volume_sma_{period}'] = df['volume'].rolling(period).mean()
                df[f'volume_ema_{period}'] = df['volume'].ewm(span=period).mean()
                
                # 成交量比率
                df[f'volume_ratio_{period}'] = df['volume'] / df[f'volume_sma_{period}']
            
            # 成交量趨勢
            df['volume_trend'] = np.where(
                df['volume_ratio_20'] > 1.2, 1, 
                np.where(df['volume_ratio_20'] < 0.8, -1, 0)
            )
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算成交量移動平均錯誤: {str(e)}")
            return df

    def _calculate_obv_system(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算OBV系統指標"""
        try:
            # 標準OBV
            obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
            df['obv'] = obv
            
            # OBV移動平均
            df['obv_ma_20'] = obv.rolling(20).mean()
            df['obv_ma_50'] = obv.rolling(50).mean()
            
            # OBV動量
            df['obv_momentum'] = obv.diff(5)
            
            # OBV背離
            df['obv_divergence'] = self._detect_obv_divergence(df)
            
            # OBV趨勢
            df['obv_trend'] = np.where(obv > obv.rolling(20).mean(), 1, -1)
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算OBV系統錯誤: {str(e)}")
            return df

    def _detect_obv_divergence(self, df: pd.DataFrame) -> pd.Series:
        """檢測OBV背離"""
        try:
            obv_highs = self._find_local_extrema(df['obv'], 'high', 5)
            obv_lows = self._find_local_extrema(df['obv'], 'low', 5)
            price_highs = self._find_local_extrema(df['close'], 'high', 5)
            price_lows = self._find_local_extrema(df['close'], 'low', 5)
            
            divergence = pd.Series(0, index=df.index)
            
            # OBV看跌背離
            for i in range(1, len(price_highs)):
                if price_highs[i] and obv_highs[i]:
                    if (df['close'].iloc[i] > df['close'].iloc[i-5:i].max() and 
                        df['obv'].iloc[i] < df['obv'].iloc[i-5:i].max()):
                        divergence.iloc[i] = -1
            
            # OBV看漲背離
            for i in range(1, len(price_lows)):
                if price_lows[i] and obv_lows[i]:
                    if (df['close'].iloc[i] < df['close'].iloc[i-5:i].min() and 
                        df['obv'].iloc[i] > df['obv'].iloc[i-5:i].min()):
                        divergence.iloc[i] = 1
                        
            return divergence
            
        except Exception as e:
            self.logger.warning(f"檢測OBV背離錯誤: {str(e)}")
            return pd.Series(0, index=df.index)

    def _calculate_mfi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """計算資金流量指數"""
        try:
            # 典型價格
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            
            # 原始資金流
            raw_money_flow = typical_price * df['volume']
            
            # 正向和負向資金流
            positive_flow = pd.Series(0.0, index=df.index)
            negative_flow = pd.Series(0.0, index=df.index)
            
            for i in range(1, len(df)):
                if typical_price.iloc[i] > typical_price.iloc[i-1]:
                    positive_flow.iloc[i] = raw_money_flow.iloc[i]
                elif typical_price.iloc[i] < typical_price.iloc[i-1]:
                    negative_flow.iloc[i] = raw_money_flow.iloc[i]
            
            # 計算資金流比率
            positive_mf = positive_flow.rolling(period).sum()
            negative_mf = negative_flow.rolling(period).sum()
            
            # 計算MFI
            money_flow_ratio = positive_mf / negative_mf.replace(0, np.nan)
            mfi = 100 - (100 / (1 + money_flow_ratio))
            
            return mfi.fillna(50)
            
        except Exception as e:
            self.logger.error(f"計算MFI錯誤: {str(e)}")
            return pd.Series(50, index=df.index)

    def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """計算成交量加權平均價"""
        try:
            # 累積成交量 * 價格
            cumulative_typical_volume = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum()
            
            # 累積成交量
            cumulative_volume = df['volume'].cumsum()
            
            # VWAP
            vwap = cumulative_typical_volume / cumulative_volume
            
            return vwap
            
        except Exception as e:
            self.logger.error(f"計算VWAP錯誤: {str(e)}")
            return df['close']

    def _calculate_volume_oscillators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算成交量震盪指標"""
        try:
            # 成交量震盪指標 (Volume Oscillator)
            df['volume_oscillator'] = (df['volume_ema_5'] - df['volume_ema_20']) / df['volume_ema_20'] * 100
            
            # 加速成交量震盪指標
            df['volume_acceleration'] = df['volume_oscillator'].diff(3)
            
            # 成交量相對強弱指標
            df['volume_rsi'] = self._calculate_volume_rsi(df, 14)
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算成交量震盪指標錯誤: {str(e)}")
            return df

    def _calculate_volume_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """計算成交量RSI"""
        try:
            volume_change = df['volume'].diff()
            
            volume_gain = volume_change.where(volume_change > 0, 0)
            volume_loss = -volume_change.where(volume_change < 0, 0)
            
            avg_gain = volume_gain.rolling(period).mean()
            avg_loss = volume_loss.rolling(period).mean()
            
            rs = avg_gain / avg_loss.replace(0, np.nan)
            volume_rsi = 100 - (100 / (1 + rs))
            
            return volume_rsi.fillna(50)
            
        except Exception as e:
            self.logger.error(f"計算成交量RSI錯誤: {str(e)}")
            return pd.Series(50, index=df.index)

    def _calculate_volume_price_confirmation(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算成交量價格確認指標"""
        try:
            # 價格成交量趨勢 (PVT)
            pvt = ((df['close'] - df['close'].shift(1)) / df['close'].shift(1)) * df['volume']
            df['pvt'] = pvt.cumsum()
            
            # 成交量確認信號
            price_change = df['close'].pct_change()
            volume_ratio = df['volume_ratio_20']
            
            df['volume_price_confirmation'] = 0
            df.loc[(price_change > 0) & (volume_ratio > 1), 'volume_price_confirmation'] = 1  # 價量齊揚
            df.loc[(price_change < 0) & (volume_ratio > 1), 'volume_price_confirmation'] = -1  # 價跌量增
            df.loc[(price_change > 0) & (volume_ratio < 0.8), 'volume_price_confirmation'] = 2  # 價漲量縮
            df.loc[(price_change < 0) & (volume_ratio < 0.8), 'volume_price_confirmation'] = -2  # 價跌量縮
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算成交量價格確認錯誤: {str(e)}")
            return df

    def _calculate_volume_profile_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算成交量分佈指標"""
        try:
            # 成交量集中度 (簡化版)
            high_volume_threshold = df['volume'].quantile(0.7)
            df['volume_concentration'] = (df['volume'] > high_volume_threshold).astype(int)
            
            # 成交量分佈偏度
            df['volume_skewness'] = df['volume'].rolling(20).skew()
            
            # 大單指標 (基於成交量異常)
            df['large_volume_signal'] = (df['volume_anomaly'] > 2).astype(int)
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算成交量分佈指標錯誤: {str(e)}")
            return df

    def _generate_volume_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成成交量信號"""
        try:
            # 成交量強度
            volume_factors = []
            
            if 'volume_ratio_20' in df.columns:
                volume_factors.append(df['volume_ratio_20'].clip(0, 3))
            
            if 'obv_momentum' in df.columns:
                obv_strength = df['obv_momentum'] / df['obv_momentum'].abs().rolling(50).mean()
                volume_factors.append(obv_strength.clip(-2, 2))
            
            if 'mfi' in df.columns:
                mfi_strength = (df['mfi'] - 50) / 50
                volume_factors.append(mfi_strength)
            
            if volume_factors:
                df['volume_strength'] = pd.concat(volume_factors, axis=1).mean(axis=1)
            
            # 成交量信號
            df['volume_signal'] = 0
            df.loc[df['volume_strength'] > 0.2, 'volume_signal'] = 1  # 成交量強勢
            df.loc[df['volume_strength'] < -0.2, 'volume_signal'] = -1  # 成交量弱勢
            
            return df
            
        except Exception as e:
            self.logger.warning(f"生成成交量信號錯誤: {str(e)}")
            return df

    def calculate_other_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算其他技術指標
        
        Args:
            df: 輸入數據框
            
        Returns:
            pd.DataFrame: 包含其他技術指標的數據框
        """
        try:
            self.logger.info("計算其他技術指標...")
            
            # 一目均衡表 (Ichimoku Cloud)
            df = self._calculate_ichimoku_cloud(df)
            
            # 支撐阻力系統
            df = self._calculate_support_resistance_system(df)
            
            # 斐波那契指標
            df = self._calculate_fibonacci_indicators(df)
            
            # 價格位置指標
            df = self._calculate_price_position_indicators(df)
            
            # 市場狀態指標
            df = self._calculate_market_regime_indicators(df)
            
            # 綜合技術評分
            df = self._calculate_composite_technical_score(df)
            
            self.logger.info("其他技術指標計算完成")
            return df
            
        except Exception as e:
            self.logger.error(f"計算其他技術指標錯誤: {str(e)}")
            return df

    def _calculate_ichimoku_cloud(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算一目均衡表"""
        try:
            # 轉換線 (Tenkan-sen)
            period9_high = df['high'].rolling(9).max()
            period9_low = df['low'].rolling(9).min()
            df['ichimoku_tenkan'] = (period9_high + period9_low) / 2
            
            # 基準線 (Kijun-sen)
            period26_high = df['high'].rolling(26).max()
            period26_low = df['low'].rolling(26).min()
            df['ichimoku_kijun'] = (period26_high + period26_low) / 2
            
            # 先行跨度A (Senkou Span A)
            df['ichimoku_senkou_a'] = ((df['ichimoku_tenkan'] + df['ichimoku_kijun']) / 2).shift(26)
            
            # 先行跨度B (Senkou Span B)
            period52_high = df['high'].rolling(52).max()
            period52_low = df['low'].rolling(52).min()
            df['ichimoku_senkou_b'] = ((period52_high + period52_low) / 2).shift(26)
            
            # 遲行跨度 (Chikou Span)
            df['ichimoku_chikou'] = df['close'].shift(-26)
            
            # 雲層狀態
            df['ichimoku_cloud_position'] = np.where(
                df['close'] > df[['ichimoku_senkou_a', 'ichimoku_senkou_b']].max(axis=1), 1,
                np.where(df['close'] < df[['ichimoku_senkou_a', 'ichimoku_senkou_b']].min(axis=1), -1, 0)
            )
            
            # 雲層厚度
            df['ichimoku_cloud_thickness'] = (df['ichimoku_senkou_a'] - df['ichimoku_senkou_b']).abs()
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算一目均衡表錯誤: {str(e)}")
            return df

    def _calculate_support_resistance_system(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算支撐阻力系統"""
        try:
            # 樞軸點系統
            pivot = (df['high'] + df['low'] + df['close']) / 3
            df['pivot'] = pivot
            
            # 支撐阻力水平
            df['pivot_r1'] = 2 * pivot - df['low']
            df['pivot_s1'] = 2 * pivot - df['high']
            df['pivot_r2'] = pivot + (df['high'] - df['low'])
            df['pivot_s2'] = pivot - (df['high'] - df['low'])
            df['pivot_r3'] = df['high'] + 2 * (pivot - df['low'])
            df['pivot_s3'] = df['low'] - 2 * (df['high'] - pivot)
            
            # 近期高點低點支撐阻力
            df['resistance_20'] = df['high'].rolling(20).max()
            df['support_20'] = df['low'].rolling(20).min()
            
            # 價格相對於支撐阻力的位置
            df['price_vs_resistance'] = (df['close'] - df['resistance_20']) / df['resistance_20'] * 100
            df['price_vs_support'] = (df['close'] - df['support_20']) / df['support_20'] * 100
            
            # 突破信號
            df['resistance_breakout'] = (df['close'] > df['resistance_20']).astype(int)
            df['support_breakdown'] = (df['close'] < df['support_20']).astype(int)
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算支撐阻力系統錯誤: {str(e)}")
            return df

    def _calculate_fibonacci_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算斐波那契指標"""
        try:
            # 近期高低點
            lookback_period = 50
            recent_high = df['high'].rolling(lookback_period).max()
            recent_low = df['low'].rolling(lookback_period).min()
            price_range = recent_high - recent_low
            
            # 斐波那契水平
            fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
            
            for level in fib_levels:
                df[f'fib_{int(level*1000)}'] = recent_high - (price_range * level)
                df[f'fib_retracement_{int(level*1000)}'] = (
                    (df['close'] - (recent_high - price_range * level)) / price_range * 100
                )
            
            # 斐波那契位置
            df['fibonacci_position'] = (df['close'] - recent_low) / price_range
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算斐波那契指標錯誤: {str(e)}")
            return df

    def _calculate_price_position_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算價格位置指標"""
        try:
            # 相對於近期高低點的位置
            lookback_periods = [20, 50, 100, 200]
            
            for period in lookback_periods:
                period_high = df['high'].rolling(period).max()
                period_low = df['low'].rolling(period).min()
                
                df[f'price_position_{period}'] = (
                    (df['close'] - period_low) / (period_high - period_low)
                )
                
                # 價格通道
                df[f'price_channel_high_{period}'] = period_high
                df[f'price_channel_low_{period}'] = period_low
            
            # 綜合價格位置
            position_columns = [f'price_position_{p}' for p in lookback_periods]
            if all(col in df.columns for col in position_columns):
                df['composite_price_position'] = df[position_columns].mean(axis=1)
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算價格位置指標錯誤: {str(e)}")
            return df

    def _calculate_market_regime_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算市場狀態指標"""
        try:
            # 趨勢狀態
            if all(col in df.columns for col in ['sma_20', 'sma_50']):
                df['trend_regime'] = np.where(
                    df['sma_20'] > df['sma_50'], 1, -1  # 多頭趨勢, 空頭趨勢
                )
            
            # 波動率狀態 (之前已計算)
            if 'volatility_regime' not in df.columns:
                df = self._assess_volatility_regime(df)
            
            # 市場狀態綜合評分
            regime_factors = []
            
            if 'trend_regime' in df.columns:
                regime_factors.append(df['trend_regime'])
            
            if 'volatility_regime' in df.columns:
                regime_factors.append(df['volatility_regime'] * 0.5)  # 降低權重
            
            if 'momentum_strength' in df.columns:
                regime_factors.append(df['momentum_strength'])
            
            if regime_factors:
                df['market_regime_score'] = pd.concat(regime_factors, axis=1).mean(axis=1)
                
                # 市場狀態分類
                conditions = [
                    (df['market_regime_score'] > 0.3) & (df['volatility_regime'] == -1),  # 多頭低波動
                    (df['market_regime_score'] > 0.3) & (df['volatility_regime'] == 1),   # 多頭高波動
                    (df['market_regime_score'] < -0.3) & (df['volatility_regime'] == -1), # 空頭低波動
                    (df['market_regime_score'] < -0.3) & (df['volatility_regime'] == 1),  # 空頭高波動
                    (abs(df['market_regime_score']) <= 0.3) & (df['volatility_regime'] == -1),  # 盤整低波動
                    (abs(df['market_regime_score']) <= 0.3) & (df['volatility_regime'] == 1)    # 盤整高波動
                ]
                choices = [1, 2, -1, -2, 0, 3]
                df['market_regime'] = np.select(conditions, choices, default=0)
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算市場狀態指標錯誤: {str(e)}")
            return df

    def _calculate_composite_technical_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算綜合技術評分"""
        try:
            score_factors = []
            weights = []
            
            # 趨勢評分 (權重30%)
            if 'trend_strength' in df.columns:
                score_factors.append(df['trend_strength'])
                weights.append(0.3)
            
            # 動量評分 (權重25%)
            if 'momentum_strength' in df.columns:
                score_factors.append(df['momentum_strength'])
                weights.append(0.25)
            
            # 成交量評分 (權重20%)
            if 'volume_strength' in df.columns:
                score_factors.append(df['volume_strength'])
                weights.append(0.2)
            
            # 波動率評分 (權重15%)
            if 'volatility_score' in df.columns:
                # 波動率適中為佳，過高或過低都不好
                volatility_score = 1 - (df['volatility_score'].abs() / df['volatility_score'].abs().rolling(50).max())
                score_factors.append(volatility_score)
                weights.append(0.15)
            
            # 價格位置評分 (權重10%)
            if 'composite_price_position' in df.columns:
                # 中間位置較安全，極端位置風險高
                price_position_score = 1 - (2 * abs(df['composite_price_position'] - 0.5))
                score_factors.append(price_position_score)
                weights.append(0.1)
            
            if score_factors:
                # 標準化權重
                total_weight = sum(weights)
                normalized_weights = [w / total_weight for w in weights]
                
                # 計算加權平均
                weighted_scores = []
                for factor, weight in zip(score_factors, normalized_weights):
                    # 標準化到0-1範圍
                    normalized_factor = (factor - factor.rolling(100).min()) / (
                        factor.rolling(100).max() - factor.rolling(100).min()
                    ).replace(0, 1)
                    weighted_scores.append(normalized_factor * weight)
                
                df['composite_technical_score'] = pd.concat(weighted_scores, axis=1).sum(axis=1)
                
                # 技術評分信號
                df['technical_signal'] = 0
                df.loc[df['composite_technical_score'] > 0.7, 'technical_signal'] = 1    # 強勢
                df.loc[df['composite_technical_score'] < 0.3, 'technical_signal'] = -1   # 弱勢
                df.loc[df['composite_technical_score'].between(0.4, 0.6), 'technical_signal'] = 0  # 中性
            
            return df
            
        except Exception as e:
            self.logger.error(f"計算綜合技術評分錯誤: {str(e)}")
            return df

    def generate_trading_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成綜合交易信號
        
        Args:
            df: 包含技術指標的數據框
            
        Returns:
            pd.DataFrame: 包含交易信號的數據框
        """
        try:
            self.logger.info("生成交易信號...")
            
            signals = pd.DataFrame(index=df.index)
            
            # 趨勢信號
            signals = self._generate_trend_signals(df, signals)
            
            # 動量信號
            signals = self._generate_momentum_signals(df, signals)
            
            # 成交量信號
            signals = self._generate_volume_based_signals(df, signals)
            
            # 波動率信號
            signals = self._generate_volatility_signals(df, signals)
            
            # 綜合信號
            signals = self._generate_composite_signals(df, signals)
            
            # 風險管理信號
            signals = self._generate_risk_management_signals(df, signals)
            
            self.logger.info("交易信號生成完成")
            return pd.concat([df, signals], axis=1)
            
        except Exception as e:
            self.logger.error(f"生成交易信號錯誤: {str(e)}")
            return df

    def _generate_trend_signals(self, df: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """生成趨勢信號"""
        try:
            signals['trend_signal'] = 0
            signals['trend_strength'] = 0
            
            # 移動平均線趨勢
            if all(col in df.columns for col in ['sma_5', 'sma_20']):
                # 金叉/死叉
                golden_cross = (df['sma_5'] > df['sma_20']) & (df['sma_5'].shift(1) <= df['sma_20'].shift(1))
                death_cross = (df['sma_5'] < df['sma_20']) & (df['sma_5'].shift(1) >= df['sma_20'].shift(1))
                
                signals.loc[golden_cross, 'trend_signal'] = 1
                signals.loc[death_cross, 'trend_signal'] = -1
            
            # 價格位置趨勢
            if 'sma_20' in df.columns:
                price_vs_ma = (df['close'] - df['sma_20']) / df['sma_20'] * 100
                signals.loc[price_vs_ma > 2, 'trend_signal'] = 1
                signals.loc[price_vs_ma < -2, 'trend_signal'] = -1
            
            # 趨勢強度
            if 'trend_strength' in df.columns:
                signals['trend_strength'] = df['trend_strength']
            
            return signals
            
        except Exception as e:
            self.logger.warning(f"生成趨勢信號錯誤: {str(e)}")
            return signals

    def _generate_momentum_signals(self, df: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """生成動量信號"""
        try:
            signals['momentum_signal'] = 0
            signals['momentum_strength'] = 0
            
            # RSI信號
            if 'rsi_14' in df.columns:
                rsi_oversold = (df['rsi_14'] < 30) & (df['rsi_14'].shift(1) >= 30)
                rsi_overbought = (df['rsi_14'] > 70) & (df['rsi_14'].shift(1) <= 70)
                
                signals.loc[rsi_oversold, 'momentum_signal'] = 1
                signals.loc[rsi_overbought, 'momentum_signal'] = -1
            
            # MACD信號
            if all(col in df.columns for col in ['macd', 'macd_signal']):
                macd_bullish = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
                macd_bearish = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
                
                signals.loc[macd_bullish, 'momentum_signal'] = 1
                signals.loc[macd_bearish, 'momentum_signal'] = -1
            
            # 動量強度
            if 'momentum_strength' in df.columns:
                signals['momentum_strength'] = df['momentum_strength']
            
            return signals
            
        except Exception as e:
            self.logger.warning(f"生成動量信號錯誤: {str(e)}")
            return signals

    def _generate_volume_based_signals(self, df: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """生成基於成交量的信號"""
        try:
            signals['volume_signal'] = 0
            
            # 成交量確認
            if 'volume_price_confirmation' in df.columns:
                signals.loc[df['volume_price_confirmation'] == 1, 'volume_signal'] = 1   # 價量齊揚
                signals.loc[df['volume_price_confirmation'] == -1, 'volume_signal'] = -1 # 價跌量增
            
            # OBV趨勢
            if 'obv_trend' in df.columns:
                signals['volume_signal'] = signals['volume_signal'] + df['obv_trend'] * 0.5
            
            return signals
            
        except Exception as e:
            self.logger.warning(f"生成成交量信號錯誤: {str(e)}")
            return signals

    def _generate_volatility_signals(self, df: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """生成波動率信號"""
        try:
            signals['volatility_signal'] = 0
            
            # 波動率突破
            if 'volatility_breakout' in df.columns:
                signals.loc[df['volatility_breakout'] == 1, 'volatility_signal'] = -1  # 高波動時謹慎
                signals.loc[df['volatility_breakout'] == -1, 'volatility_signal'] = 1   # 低波動時積極
            
            # 布林帶擠壓
            if 'bb_squeeze' in df.columns:
                low_squeeze = df['bb_squeeze'] < 0.2
                signals.loc[low_squeeze, 'volatility_signal'] = 1  # 低波動擠壓，可能突破
            
            return signals
            
        except Exception as e:
            self.logger.warning(f"生成波動率信號錯誤: {str(e)}")
            return signals

    def _generate_composite_signals(self, df: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """生成綜合信號"""
        try:
            # 綜合信號計算
            signal_components = []
            weights = []
            
            if 'trend_signal' in signals.columns:
                signal_components.append(signals['trend_signal'])
                weights.append(0.3)
            
            if 'momentum_signal' in signals.columns:
                signal_components.append(signals['momentum_signal'])
                weights.append(0.3)
            
            if 'volume_signal' in signals.columns:
                signal_components.append(signals['volume_signal'])
                weights.append(0.2)
            
            if 'volatility_signal' in signals.columns:
                signal_components.append(signals['volatility_signal'])
                weights.append(0.2)
            
            if signal_components:
                # 計算加權信號
                weighted_signals = []
                for signal, weight in zip(signal_components, weights):
                    weighted_signals.append(signal * weight)
                
                composite_signal = pd.concat(weighted_signals, axis=1).sum(axis=1)
                
                # 信號分類
                signals['composite_signal'] = 0
                signals.loc[composite_signal > 0.3, 'composite_signal'] = 1      # 買入信號
                signals.loc[composite_signal < -0.3, 'composite_signal'] = -1    # 賣出信號
                
                # 信號強度
                signals['signal_strength'] = composite_signal.abs()
            
            # 技術評分信號
            if 'technical_signal' in df.columns:
                signals['technical_signal'] = df['technical_signal']
            
            return signals
            
        except Exception as e:
            self.logger.warning(f"生成綜合信號錯誤: {str(e)}")
            return signals

    def _generate_risk_management_signals(self, df: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """生成風險管理信號"""
        try:
            signals['risk_signal'] = 0
            
            # 波動率風險
            if 'volatility_regime' in df.columns:
                signals.loc[df['volatility_regime'] == 1, 'risk_signal'] = -1  # 高波動時降低風險暴露
            
            # 價格位置風險
            if 'composite_price_position' in df.columns:
                extreme_high = df['composite_price_position'] > 0.8
                extreme_low = df['composite_price_position'] < 0.2
                signals.loc[extreme_high, 'risk_signal'] = -1
                signals.loc[extreme_low, 'risk_signal'] = 1
            
            # 綜合風險評分
            risk_factors = []
            
            if 'volatility_regime' in df.columns:
                risk_factors.append((df['volatility_regime'] == 1).astype(int) * 0.5)
            
            if 'composite_price_position' in df.columns:
                position_risk = (abs(df['composite_price_position'] - 0.5) - 0.3).clip(0, 0.2) * 5
                risk_factors.append(position_risk)
            
            if risk_factors:
                total_risk = pd.concat(risk_factors, axis=1).sum(axis=1)
                signals['risk_score'] = total_risk
                signals.loc[total_risk > 0.5, 'risk_signal'] = -1
            
            return signals
            
        except Exception as e:
            self.logger.warning(f"生成風險管理信號錯誤: {str(e)}")
            return signals

    # 更新指標說明方法
    def get_volume_descriptions(self) -> Dict:
        """取得成交量指標說明"""
        return {
            'volume_ratio_20': '20日成交量比率 - 當前成交量與平均值的比較',
            'obv': '能量潮 - 成交量累積指標',
            'mfi': '資金流量指數 - 成交量加權的RSI',
            'vwap': '成交量加權平均價 - 機構參考價格',
            'pvt': '價格成交量趨勢 - 價量結合指標',
            'volume_price_confirmation': '價量確認 - 價格與成交量的關係'
        }

    def get_other_indicators_descriptions(self) -> Dict:
        """取得其他指標說明"""
        return {
            'ichimoku_tenkan': '一目轉換線 - 短期趨勢',
            'ichimoku_kijun': '一目基準線 - 中期趨勢',
            'ichimoku_senkou_a': '一目先行跨度A - 雲層上邊',
            'ichimoku_senkou_b': '一目先行跨度B - 雲層下邊',
            'pivot': '樞軸點 - 日內交易參考點',
            'composite_technical_score': '綜合技術評分 - 多指標整合評分',
            'market_regime': '市場狀態 - 趨勢和波動率環境分類'
        }

    def get_signal_descriptions(self) -> Dict:
        """取得信號說明"""
        return {
            'trend_signal': '趨勢信號 - 基於移動平均線和趨勢強度',
            'momentum_signal': '動量信號 - 基於RSI、MACD等動量指標',
            'volume_signal': '成交量信號 - 基於價量關係',
            'composite_signal': '綜合信號 - 多指標加權綜合信號',
            'risk_signal': '風險信號 - 風險管理建議'
        }

# 使用範例和測試
if __name__ == "__main__":
    # 創建測試數據
    def create_sample_data():
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        np.random.seed(42)
        
        # 生成模擬價格數據
        prices = [100]
        for i in range(1, len(dates)):
            change = np.random.normal(0, 0.02)
            prices.append(prices[-1] * (1 + change))
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.randint(100000, 1000000, len(dates))
        })
        df.set_index('date', inplace=True)
        return df

    # 測試技術指標系統
    print("🔧 測試技術指標系統...")
    
    # 創建配置
    config = IndicatorConfig()
    
    # 初始化技術指標系統
    ti = TechnicalIndicators(config)
    
    # 生成樣本數據
    sample_data = create_sample_data()
    print(f"📊 樣本數據形狀: {sample_data.shape}")
    
    # 計算所有技術指標
    result_df = ti.calculate_all_indicators(sample_data)
    print(f"📈 計算後數據形狀: {result_df.shape}")
    
    # 生成交易信號
    final_df = ti.generate_trading_signals(result_df)
    print(f"🎯 最終數據形狀: {final_df.shape}")
    
    # 顯示信號統計
    if 'composite_signal' in final_df.columns:
        signal_counts = final_df['composite_signal'].value_counts()
        print(f"📡 交易信號分佈:\n{signal_counts}")
    
    print("✅ 技術指標系統測試完成！")