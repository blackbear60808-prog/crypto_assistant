# utils/data_visualizer.py
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import io
import base64
from typing import Dict, List, Optional, Tuple

class DataVisualizer:
    def __init__(self, db=None):
        self.db = db
        self.setup_plot_style()
    
    def setup_plot_style(self):
        """設置繪圖風格"""
        plt.style.use('seaborn-v0_8')
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 設置顏色
        self.colors = {
            'bullish': '#26A69A',  # 上漲綠色
            'bearish': '#EF5350',  # 下跌紅色
            'neutral': '#78909C',  # 中性灰色
            'background': '#1E1E1E',  # 背景深色
            'grid': '#424242',  # 網格線
            'text': '#E0E0E0'  # 文字顏色
        }
    
    def create_price_chart(self, symbol: str, ohlcv_data: List, timeframe: str = '1h') -> Figure:
        """創建價格圖表（K線圖）"""
        try:
            if not ohlcv_data:
                return self.create_empty_chart("無數據可用")
            
            # 轉換為DataFrame
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 創建圖表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), 
                                          gridspec_kw={'height_ratios': [3, 1]})
            
            # 繪製K線圖
            self._plot_candlestick(ax1, df, symbol)
            
            # 繪製成交量
            self._plot_volume(ax2, df)
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            print(f"創建價格圖表錯誤: {e}")
            return self.create_empty_chart(f"圖表創建失敗: {str(e)}")
    
    def _plot_candlestick(self, ax, df: pd.DataFrame, symbol: str):
        """繪製K線圖"""
        # 計算上漲下跌
        df['color'] = np.where(df['close'] >= df['open'], 
                              self.colors['bullish'], 
                              self.colors['bearish'])
        
        # 繪製K線
        for i, row in df.iterrows():
            # 繪製實體
            ax.bar(row['timestamp'], 
                  abs(row['close'] - row['open']), 
                  bottom=min(row['open'], row['close']),
                  color=row['color'], 
                  width=0.0001,  # 寬度根據時間間隔調整
                  alpha=0.8)
            
            # 繪製影線
            ax.plot([row['timestamp'], row['timestamp']], 
                   [row['low'], row['high']], 
                   color=row['color'], 
                   linewidth=1)
        
        # 計算移動平均線
        if len(df) >= 20:
            df['ma20'] = df['close'].rolling(20).mean()
            ax.plot(df['timestamp'], df['ma20'], 
                   color='#FFA726', label='MA20', linewidth=2)
        
        if len(df) >= 50:
            df['ma50'] = df['close'].rolling(50).mean()
            ax.plot(df['timestamp'], df['ma50'], 
                   color='#5C6BC0', label='MA50', linewidth=2)
        
        ax.set_title(f'{symbol} 價格走勢', fontsize=16, fontweight='bold')
        ax.set_ylabel('價格 (USDT)', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 格式化x軸
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    def _plot_volume(self, ax, df: pd.DataFrame):
        """繪製成交量"""
        df['volume_color'] = np.where(df['close'] >= df['open'], 
                                     self.colors['bullish'], 
                                     self.colors['bearish'])
        
        ax.bar(df['timestamp'], df['volume'], 
              color=df['volume_color'], alpha=0.6)
        
        ax.set_ylabel('成交量', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # 格式化x軸
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    def create_technical_indicators_chart(self, symbol: str, ohlcv_data: List) -> Figure:
        """創建技術指標圖表"""
        try:
            if not ohlcv_data:
                return self.create_empty_chart("無數據可用")
            
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 創建多子圖
            fig, axes = plt.subplots(4, 1, figsize=(12, 10))
            
            # 1. 價格和移動平均線
            self._plot_price_ma(axes[0], df, symbol)
            
            # 2. RSI
            self._plot_rsi(axes[1], df)
            
            # 3. MACD
            self._plot_macd(axes[2], df)
            
            # 4. 布林帶
            self._plot_bollinger_bands(axes[3], df)
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            print(f"創建技術指標圖表錯誤: {e}")
            return self.create_empty_chart(f"技術指標圖表創建失敗: {str(e)}")
    
    def _plot_price_ma(self, ax, df: pd.DataFrame, symbol: str):
        """繪製價格和移動平均線"""
        # 計算移動平均線
        for period, color, label in [(5, '#FF6B6B', 'MA5'), (20, '#4ECDC4', 'MA20'), (50, '#45B7D1', 'MA50')]:
            if len(df) >= period:
                df[f'ma{period}'] = df['close'].rolling(period).mean()
                ax.plot(df['timestamp'], df[f'ma{period}'], 
                       color=color, label=label, linewidth=1.5)
        
        ax.plot(df['timestamp'], df['close'], 
               color='#2E86AB', label='收盤價', linewidth=1, alpha=0.7)
        
        ax.set_title(f'{symbol} - 價格與移動平均線', fontsize=14)
        ax.set_ylabel('價格', fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    def _plot_rsi(self, ax, df: pd.DataFrame):
        """繪製RSI指標"""
        rsi = self._calculate_rsi(df['close'])
        df['rsi'] = rsi
        
        ax.plot(df['timestamp'], df['rsi'], color='#A23B72', linewidth=1.5)
        ax.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='超買線')
        ax.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='超賣線')
        ax.axhline(y=50, color='gray', linestyle='-', alpha=0.5)
        
        ax.set_title('RSI (相對強弱指數)', fontsize=14)
        ax.set_ylabel('RSI', fontsize=10)
        ax.set_ylim(0, 100)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    def _plot_macd(self, ax, df: pd.DataFrame):
        """繪製MACD指標"""
        macd, signal, histogram = self._calculate_macd(df['close'])
        df['macd'] = macd
        df['signal'] = signal
        df['histogram'] = histogram
        
        ax.plot(df['timestamp'], df['macd'], color='#F18F01', label='MACD', linewidth=1.5)
        ax.plot(df['timestamp'], df['signal'], color='#C73E1D', label='信號線', linewidth=1.5)
        
        # 繪製柱狀圖
        colors = ['#26A69A' if x >= 0 else '#EF5350' for x in df['histogram']]
        ax.bar(df['timestamp'], df['histogram'], color=colors, alpha=0.6, width=0.0001)
        
        ax.set_title('MACD', fontsize=14)
        ax.set_ylabel('MACD', fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    def _plot_bollinger_bands(self, ax, df: pd.DataFrame):
        """繪製布林帶"""
        bb_upper, bb_lower = self._calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_upper
        df['bb_lower'] = bb_lower
        df['bb_middle'] = df['close'].rolling(20).mean()
        
        ax.plot(df['timestamp'], df['close'], color='#2E86AB', label='收盤價', linewidth=1)
        ax.plot(df['timestamp'], df['bb_upper'], color='#EF5350', label='上軌', linewidth=1, alpha=0.7)
        ax.plot(df['timestamp'], df['bb_middle'], color='#78909C', label='中軌', linewidth=1, alpha=0.7)
        ax.plot(df['timestamp'], df['bb_lower'], color='#26A69A', label='下軌', linewidth=1, alpha=0.7)
        
        # 填充布林帶區域
        ax.fill_between(df['timestamp'], df['bb_upper'], df['bb_lower'], 
                       alpha=0.2, color='gray')
        
        ax.set_title('布林帶', fontsize=14)
        ax.set_ylabel('價格', fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    def create_performance_chart(self, equity_curve: List[Dict]) -> Figure:
        """創建績效圖表"""
        try:
            if not equity_curve:
                return self.create_empty_chart("無績效數據")
            
            df = pd.DataFrame(equity_curve)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # 權益曲線
            ax1.plot(df['timestamp'], df['equity'], 
                    color='#2E86AB', linewidth=2, label='帳戶權益')
            ax1.set_title('帳戶權益曲線', fontsize=16, fontweight='bold')
            ax1.set_ylabel('權益 (USDT)', fontsize=12)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 回撤圖
            drawdown = self._calculate_drawdown(df['equity'])
            ax2.fill_between(df['timestamp'], drawdown, 0, 
                           color='#EF5350', alpha=0.3, label='回撤')
            ax2.set_title('資金回撤', fontsize=16, fontweight='bold')
            ax2.set_ylabel('回撤 (%)', fontsize=12)
            ax2.set_xlabel('時間', fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            print(f"創建績效圖表錯誤: {e}")
            return self.create_empty_chart(f"績效圖表創建失敗: {str(e)}")
    
    def create_portfolio_pie_chart(self, portfolio_data: Dict[str, float]) -> Figure:
        """創建投資組合餅圖"""
        try:
            if not portfolio_data:
                return self.create_empty_chart("無投資組合數據")
            
            labels = list(portfolio_data.keys())
            sizes = list(portfolio_data.values())
            
            # 生成顏色
            colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
            
            fig, ax = plt.subplots(figsize=(10, 8))
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, 
                                            autopct='%1.1f%%', startangle=90)
            
            # 美化文字
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            ax.set_title('投資組合分配', fontsize=16, fontweight='bold')
            plt.tight_layout()
            return fig
            
        except Exception as e:
            print(f"創建投資組合餅圖錯誤: {e}")
            return self.create_empty_chart(f"投資組合圖表創建失敗: {str(e)}")
    
    def create_correlation_heatmap(self, symbols: List[str], price_data: Dict) -> Figure:
        """創建相關性熱力圖"""
        try:
            if len(symbols) < 2:
                return self.create_empty_chart("需要至少2個標的進行相關性分析")
            
            # 準備數據
            returns_data = {}
            for symbol in symbols:
                if symbol in price_data and len(price_data[symbol]) > 1:
                    prices = [p['close'] for p in price_data[symbol]]
                    returns = np.diff(prices) / prices[:-1]  # 計算收益率
                    returns_data[symbol] = returns
            
            if len(returns_data) < 2:
                return self.create_empty_chart("數據不足進行相關性分析")
            
            # 創建相關性矩陣
            df = pd.DataFrame(returns_data)
            correlation_matrix = df.corr()
            
            fig, ax = plt.subplots(figsize=(10, 8))
            im = ax.imshow(correlation_matrix, cmap='RdYlBu', vmin=-1, vmax=1)
            
            # 設置刻度
            ax.set_xticks(np.arange(len(symbols)))
            ax.set_yticks(np.arange(len(symbols)))
            ax.set_xticklabels(symbols)
            ax.set_yticklabels(symbols)
            
            # 旋轉刻度標籤
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
            
            # 添加數值標籤
            for i in range(len(symbols)):
                for j in range(len(symbols)):
                    text = ax.text(j, i, f'{correlation_matrix.iloc[i, j]:.2f}',
                                 ha="center", va="center", color="black", fontweight='bold')
            
            ax.set_title('加密貨幣相關性熱力圖', fontsize=16, fontweight='bold')
            fig.colorbar(im, ax=ax)
            plt.tight_layout()
            return fig
            
        except Exception as e:
            print(f"創建相關性熱力圖錯誤: {e}")
            return self.create_empty_chart(f"相關性分析失敗: {str(e)}")
    
    def create_interactive_chart(self, symbol: str, ohlcv_data: List) -> str:
        """創建互動式圖表 (Plotly) - 返回HTML字符串"""
        try:
            if not ohlcv_data:
                return "<div>無數據可用</div>"
            
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 創建子圖
            fig = make_subplots(rows=2, cols=1, 
                              shared_xaxes=True,
                              vertical_spacing=0.1,
                              subplot_titles=(f'{symbol} 價格走勢', '成交量'),
                              row_width=[0.7, 0.3])
            
            # 添加K線圖
            fig.add_trace(go.Candlestick(x=df['timestamp'],
                                       open=df['open'],
                                       high=df['high'],
                                       low=df['low'],
                                       close=df['close'],
                                       name='K線'),
                         row=1, col=1)
            
            # 添加移動平均線
            if len(df) >= 20:
                df['ma20'] = df['close'].rolling(20).mean()
                fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ma20'],
                                       name='MA20', line=dict(color='orange', width=2)),
                            row=1, col=1)
            
            # 添加成交量
            colors = ['green' if close >= open else 'red' 
                     for close, open in zip(df['close'], df['open'])]
            
            fig.add_trace(go.Bar(x=df['timestamp'], y=df['volume'],
                               name='成交量', marker_color=colors),
                         row=2, col=1)
            
            # 更新佈局
            fig.update_layout(
                title=f'{symbol} 技術分析圖',
                xaxis_title='時間',
                yaxis_title='價格 (USDT)',
                height=600,
                showlegend=True,
                template='plotly_white'
            )
            
            # 隱藏範圍滑桿
            fig.update_layout(xaxis_rangeslider_visible=False)
            
            return fig.to_html(include_plotlyjs='cdn', config={'displayModeBar': True})
            
        except Exception as e:
            print(f"創建互動式圖表錯誤: {e}")
            return f"<div>圖表創建失敗: {str(e)}</div>"
    
    def create_empty_chart(self, message: str = "無數據") -> Figure:
        """創建空圖表用於顯示錯誤信息"""
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, message, 
               ha='center', va='center', 
               transform=ax.transAxes, fontsize=16,
               bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
        ax.set_xticks([])
        ax.set_yticks([])
        return fig
    
    def save_chart_to_file(self, fig: Figure, filename: str, dpi: int = 300):
        """保存圖表到文件"""
        try:
            fig.savefig(filename, dpi=dpi, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"圖表已保存: {filename}")
        except Exception as e:
            print(f"保存圖表錯誤: {e}")
    
    def get_chart_as_image(self, fig: Figure) -> str:
        """將圖表轉換為base64編碼的圖片字符串"""
        try:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, 
                       bbox_inches='tight', facecolor='white')
            buf.seek(0)
            image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            buf.close()
            return image_base64
        except Exception as e:
            print(f"圖表轉換錯誤: {e}")
            return ""
    
    # 技術指標計算方法
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """計算RSI指標"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """計算MACD指標"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        macd_histogram = macd - macd_signal
        return macd, macd_signal, macd_histogram
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std: int = 2) -> Tuple[pd.Series, pd.Series]:
        """計算布林帶"""
        sma = prices.rolling(period).mean()
        rolling_std = prices.rolling(period).std()
        upper_band = sma + (rolling_std * std)
        lower_band = sma - (rolling_std * std)
        return upper_band, lower_band
    
    def _calculate_drawdown(self, equity: pd.Series) -> pd.Series:
        """計算資金回撤"""
        peak = equity.expanding().max()
        drawdown = (equity - peak) / peak * 100
        return drawdown
    
    def plot_to_tkinter(self, fig: Figure, master) -> FigureCanvasTkAgg:
        """將matplotlib圖表嵌入到Tkinter視窗"""
        canvas = FigureCanvasTkAgg(fig, master=master)
        canvas.draw()
        return canvas

# 使用示例
if __name__ == "__main__":
    # 測試數據可視化
    visualizer = DataVisualizer()
    
    # 生成測試數據
    dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='D')
    np.random.seed(42)
    
    test_data = []
    price = 100
    for date in dates:
        change = np.random.normal(0, 2)
        price += change
        high = price + abs(np.random.normal(0, 1))
        low = price - abs(np.random.normal(0, 1))
        open_price = price - np.random.normal(0, 0.5)
        volume = np.random.randint(1000, 10000)
        
        test_data.append([
            int(date.timestamp() * 1000),  # timestamp
            open_price,                    # open
            high,                          # high  
            low,                           # low
            price,                         # close
            volume                         # volume
        ])
    
    # 測試各種圖表
    print("測試價格圖表...")
    fig1 = visualizer.create_price_chart("BTC-USDT", test_data)
    visualizer.save_chart_to_file(fig1, "test_price_chart.png")
    
    print("測試技術指標圖表...")
    fig2 = visualizer.create_technical_indicators_chart("BTC-USDT", test_data)
    visualizer.save_chart_to_file(fig2, "test_technical_chart.png")
    
    print("測試互動式圖表...")
    html_content = visualizer.create_interactive_chart("BTC-USDT", test_data)
    with open("test_interactive_chart.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("所有測試完成！")