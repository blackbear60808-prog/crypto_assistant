# modules/discord_bot.py
import requests
import json
from datetime import datetime
from typing import Dict  # 添加 Dict 導入

class DiscordBot:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url)
        
    def send_message(self, message, level="info"):
        """發送 Discord 訊息"""
        if not self.enabled:
            return False
            
        try:
            # 根據等級設置顏色
            colors = {
                'critical': 0xFF0000,  # 紅色 - 嚴重錯誤
                'warning': 0xFFA500,   # 橙色 - 警告
                'info': 0x00FF00,      # 綠色 - 一般資訊
                'success': 0x00FF00,   # 綠色 - 成功
                'error': 0xFF0000,     # 紅色 - 錯誤
                'buy': 0x00FF00,       # 綠色 - 買入信號
                'sell': 0xFF0000,      # 紅色 - 賣出信號
                'neutral': 0x808080,   # 灰色 - 中性
                'smc_analysis': 0x0099FF  # 藍色 - SMC 分析
            }
            
            # 等級對應的標題
            titles = {
                'critical': '🚨 嚴重警報',
                'warning': '⚠️ 警告',
                'info': 'ℹ️ 資訊',
                'success': '✅ 成功',
                'error': '❌ 錯誤',
                'buy': '🟢 買入信號',
                'sell': '🔴 賣出信號',
                'neutral': '⚪ 中性',
                'smc_analysis': '📊 SMC 市場分析'
            }
            
            embed = {
                "title": titles.get(level, "ℹ️ 訊息"),
                "description": message,
                "color": colors.get(level, 0x808080),
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "幣圈交易輔助系統"
                }
            }
            
            payload = {
                "embeds": [embed],
                "username": "Crypto Assistant",
                "avatar_url": "https://cdn-icons-png.flaticon.com/512/825/825540.png"
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(self.webhook_url, data=json.dumps(payload), headers=headers)
            
            if response.status_code == 204:
                print(f"✓ Discord 訊息發送成功: {message}")
                return True
            else:
                print(f"❌ Discord 訊息發送失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"發送 Discord 訊息錯誤: {e}")
            return False
    
    def send_trading_signal(self, symbol, signal, price, confidence, reason=""):
        """發送交易信號"""
        message = f"**{symbol}**\n"
        message += f"**信號**: {signal}\n"
        message += f"**當前價格**: {price:.4f} USDT\n"
        message += f"**置信度**: {confidence:.2%}\n"
        if reason:
            message += f"**理由**: {reason}"
            
        level = "buy" if signal.lower() in ["buy", "long"] else "sell" if signal.lower() in ["sell", "short"] else "neutral"
        return self.send_message(message, level)
    
    def send_smc_analysis(self, symbol: str, smc_data: Dict):
        """發送 SMC 分析結果到 Discord"""
        if not self.enabled:
            return False
            
        try:
            # 創建嵌入訊息
            embed = {
                "title": f"📊 SMC 市場分析 - {symbol}",
                "description": "智能市場結構分析報告",
                "color": 0x0099FF,  # 藍色
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "幣圈交易輔助系統 - SMC 策略"
                },
                "fields": []
            }

            # 市場概況
            market_structure = smc_data.get('market_structure', {})
            trend = market_structure.get('trend', {})
            embed["fields"].append({
                "name": "📈 市場概況",
                "value": f"**趨勢**: {trend.get('overall', '未知')}\n"
                        f"**波動率**: {market_structure.get('volatility', 0):.2%}\n"
                        f"**市場狀態**: {market_structure.get('market_regime', '正常波動')}",
                "inline": True
            })

            # 交易信號
            signals = smc_data.get('trading_signals', {})
            bias = smc_data.get('bias', '中性')
            embed["fields"].append({
                "name": "🎯 交易信號",
                "value": f"**動作**: {signals.get('action', '持有')}\n"
                        f"**置信度**: {signals.get('confidence', 0):.1%}\n"
                        f"**偏見**: {bias}",
                "inline": True
            })

            # 關鍵價位
            current_price = smc_data.get('current_price', 0)
            support_levels = smc_data.get('support_levels', [])[:2]  # 前2個
            resistance_levels = smc_data.get('resistance_levels', [])[:2]  # 前2個
            
            support_text = "\n".join([f"${level['price']:.4f} ({level.get('strength', 0):.1%})" for level in support_levels]) or "無明顯支撐"
            resistance_text = "\n".join([f"${level['price']:.4f} ({level.get('strength', 0):.1%})" for level in resistance_levels]) or "無明顯阻力"
            
            embed["fields"].append({
                "name": "🛡️ 關鍵支撐",
                "value": support_text,
                "inline": True
            })
            embed["fields"].append({
                "name": "🎯 關鍵阻力",
                "value": resistance_text,  # 修復：添加遺漏的引號
                "inline": True
            })

            # 技術指標
            momentum = market_structure.get('momentum', {})
            embed["fields"].append({
                "name": "📊 技術指標",
                "value": f"**RSI**: {momentum.get('rsi', 0):.1f} ({momentum.get('rsi_momentum', '中性')})\n"
                        f"**MACD**: {momentum.get('macd_momentum', '中性')}",
                "inline": False
            })

            payload = {
                "embeds": [embed],
                "username": "Crypto Assistant - SMC",
                "avatar_url": "https://cdn-icons-png.flaticon.com/512/825/825540.png"
            }

            headers = {'Content-Type': 'application/json'}
            response = requests.post(self.webhook_url, data=json.dumps(payload, ensure_ascii=False), headers=headers)
            
            if response.status_code == 204:
                print(f"✓ SMC 分析發送成功: {symbol}")
                return True
            else:
                print(f"❌ SMC 分析發送失敗: {response.status_code}")
                return False

        except Exception as e:
            print(f"發送 SMC 分析到 Discord 錯誤: {e}")
            return False
    
    def send_smc_trading_recommendation(self, symbol: str, recommendation: Dict):
        """發送 SMC 交易建議"""
        if not self.enabled:
            return False
            
        try:
            color = 0x00FF00 if recommendation['action'] in ['考慮買入', '買入'] else 0xFF0000 if recommendation['action'] in ['考慮賣出', '賣出'] else 0xFFFF00
            
            embed = {
                "title": f"🚨 SMC 交易建議 - {symbol}",
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "幣圈交易輔助系統 - SMC 策略"
                },
                "fields": [
                    {
                        "name": "📈 動作",
                        "value": recommendation['action'],
                        "inline": True
                    },
                    {
                        "name": "🎯 置信度", 
                        "value": f"{recommendation.get('confidence', 0):.1%}",
                        "inline": True
                    },
                    {
                        "name": "⚠️ 風險等級",
                        "value": recommendation.get('risk_level', '中等'),
                        "inline": True
                    }
                ]
            }
            
            # 關鍵價位
            key_levels = recommendation.get('key_levels', {})
            if key_levels.get('nearest_support'):
                embed["fields"].append({
                    "name": "🛡️ 最近支撐",
                    "value": f"${key_levels['nearest_support']['price']:.4f}",
                    "inline": True
                })
            
            if key_levels.get('nearest_resistance'):
                embed["fields"].append({
                    "name": "🎯 最近阻力",
                    "value": f"${key_levels['nearest_resistance']['price']:.4f}",
                    "inline": True
                })

            # 信號理由
            reasoning = recommendation.get('reasoning', [])
            if reasoning:
                embed["fields"].append({
                    "name": "💡 信號理由",
                    "value": ", ".join(reasoning[:3]),
                    "inline": False
                })

            payload = {
                "embeds": [embed],
                "username": "Crypto Assistant - SMC",
                "avatar_url": "https://cdn-icons-png.flaticon.com/512/825/825540.png"
            }

            headers = {'Content-Type': 'application/json'}
            response = requests.post(self.webhook_url, data=json.dumps(payload, ensure_ascii=False), headers=headers)
            
            if response.status_code == 204:
                print(f"✓ SMC 交易建議發送成功: {symbol}")
                return True
            else:
                print(f"❌ SMC 交易建議發送失敗: {response.status_code}")
                return False

        except Exception as e:
            print(f"發送 SMC 交易建議到 Discord 錯誤: {e}")
            return False
    
    def send_account_alert(self, alert_type, data):
        """發送帳戶警報"""
        message = f"**帳戶警報 - {alert_type}**\n"
        
        if alert_type == "balance_change":
            message += f"餘額變化: {data.get('change', 0):.2%}\n"
            message += f"當前餘額: {data.get('current_balance', 0):.2f} USDT\n"
            message += f"之前餘額: {data.get('previous_balance', 0):.2f} USDT"
            
        elif alert_type == "large_move":
            message += f"**{data.get('symbol', '')}** 大幅波動\n"
            message += f"變化: {data.get('change', 0):.2%}\n"
            message += f"當前價格: {data.get('current_price', 0):.4f} USDT"
            
        elif alert_type == "system":
            message += f"系統訊息: {data.get('message', '')}"
            
        return self.send_message(message, "warning")
    
    def send_backtest_result(self, symbol, results):
        """發送回測結果"""
        message = f"**回測結果 - {symbol}**\n"
        message += f"初始資金: {results.get('initial_balance', 0):.2f} USDT\n"
        message += f"最終資金: {results.get('final_balance', 0):.2f} USDT\n"
        message += f"總回報: {results.get('total_return', 0):.2%}\n"
        message += f"最大回撤: {results.get('max_drawdown', 0):.2%}\n"
        message += f"夏普比率: {results.get('sharpe_ratio', 0):.2f}\n"
        message += f"勝率: {results.get('win_rate', 0):.2%}"
        
        level = "success" if results.get('total_return', 0) > 0 else "warning"
        return self.send_message(message, level)
    
    def test_connection(self):
        """測試 Discord 連接"""
        if not self.enabled:
            return False, "Discord 未啟用"
            
        try:
            result = self.send_message("🔗 Discord 連接測試成功！", "success")
            if result:
                return True, "Discord 連接測試成功"
            else:
                return False, "Discord 連接測試失敗"
        except Exception as e:
            return False, f"Discord 連接測試錯誤: {str(e)}"