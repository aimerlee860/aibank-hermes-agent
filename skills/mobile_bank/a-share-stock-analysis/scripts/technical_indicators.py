#!/usr/bin/env python3
"""
技术指标计算脚本
功能：计算股票技术分析中常用的各种技术指标
作者：FI Analisis Team
版本：1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import json
import sys
import os
import warnings
warnings.filterwarnings('ignore')

class TechnicalIndicators:
    """技术指标计算类"""
    
    def __init__(self, data: pd.DataFrame):
        """
        初始化技术指标计算器
        
        Args:
            data: 包含OHLCV数据的DataFrame，必须包含以下列：
                - date: 日期
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量
        """
        self.data = data.copy()
        self.indicators = {}
        self._validate_data()
        
    def _validate_data(self) -> None:
        """验证输入数据的完整性"""
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in self.data.columns]
        
        if missing_columns:
            raise ValueError(f"数据缺少必要列: {missing_columns}")
        
        # 确保数据按日期排序
        if 'date' in self.data.columns:
            self.data = self.data.sort_values('date').reset_index(drop=True)
        
        # 检查数据质量
        if len(self.data) < 5:
            warnings.warn("数据量较少，可能影响技术指标计算的准确性")
        
        # 检查缺失值
        missing_values = self.data[required_columns].isnull().sum().sum()
        if missing_values > 0:
            warnings.warn(f"数据中存在 {missing_values} 个缺失值，建议先进行数据清洗")
    
    def calculate_all_indicators(self, config: Optional[Dict] = None) -> pd.DataFrame:
        """
        计算所有技术指标
        
        Args:
            config: 配置字典，包含各指标的参数
            
        Returns:
            包含所有技术指标的DataFrame
        """
        if config is None:
            config = self.get_default_config()
        
        print("开始计算技术指标...")
        
        # 计算移动平均线
        print("  计算移动平均线...")
        self.calculate_moving_averages(config.get('ma_periods', [5, 10, 20, 30, 60]))
        
        # 计算指数移动平均线
        print("  计算指数移动平均线...")
        self.calculate_ema(config.get('ema_periods', [12, 26]))
        
        # 计算RSI
        print("  计算相对强弱指数(RSI)...")
        self.calculate_rsi(config.get('rsi_period', 14))
        
        # 计算布林带
        print("  计算布林带...")
        self.calculate_bollinger_bands(
            period=config.get('bb_period', 20),
            std_dev=config.get('bb_std_dev', 2)
        )
        
        # 计算MACD
        print("  计算MACD指标...")
        self.calculate_macd(
            fast_period=config.get('macd_fast', 12),
            slow_period=config.get('macd_slow', 26),
            signal_period=config.get('macd_signal', 9)
        )
        
        # 计算成交量指标
        print("  计算成交量指标...")
        self.calculate_volume_indicators()
        
        # 计算价格变化
        print("  计算价格变化指标...")
        self.calculate_price_changes()
        
        # 计算波动率指标
        print("  计算波动率指标...")
        self.calculate_volatility_indicators()
        
        print("技术指标计算完成！")
        return self.data
    
    def calculate_moving_averages(self, periods: List[int]) -> None:
        """计算简单移动平均线"""
        for period in periods:
            column_name = f'MA{period}'
            self.data[column_name] = self.data['close'].rolling(window=period, min_periods=1).mean()
            self.indicators[column_name] = {
                'type': 'moving_average',
                'period': period,
                'description': f'{period}日简单移动平均线',
                'calculation': '收盘价的简单移动平均'
            }
    
    def calculate_ema(self, periods: List[int]) -> None:
        """计算指数移动平均线"""
        for period in periods:
            column_name = f'EMA{period}'
            self.data[column_name] = self.data['close'].ewm(span=period, adjust=False, min_periods=1).mean()
            self.indicators[column_name] = {
                'type': 'exponential_moving_average',
                'period': period,
                'description': f'{period}日指数移动平均线',
                'calculation': '收盘价的指数移动平均'
            }
    
    def calculate_rsi(self, period: int = 14) -> None:
        """计算相对强弱指数(RSI)"""
        delta = self.data['close'].diff()
        
        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # 计算平均增益和平均损失
        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()
        
        # 计算RS
        rs = avg_gain / avg_loss
        rs = rs.replace([np.inf, -np.inf], np.nan)
        
        # 计算RSI
        rsi = 100 - (100 / (1 + rs))
        
        self.data['RSI'] = rsi
        self.indicators['RSI'] = {
            'type': 'rsi',
            'period': period,
            'description': f'{period}日相对强弱指数',
            'calculation': '基于价格变动计算超买超卖',
            'overbought': 70,
            'oversold': 30,
            'neutral': 50
        }
    
    def calculate_bollinger_bands(self, period: int = 20, std_dev: float = 2) -> None:
        """计算布林带"""
        # 计算中轨（移动平均线）
        self.data['BB_middle'] = self.data['close'].rolling(window=period, min_periods=1).mean()
        
        # 计算标准差
        rolling_std = self.data['close'].rolling(window=period, min_periods=1).std()
        
        # 计算上轨和下轨
        self.data['BB_upper'] = self.data['BB_middle'] + (rolling_std * std_dev)
        self.data['BB_lower'] = self.data['BB_middle'] - (rolling_std * std_dev)
        
        # 计算带宽和%b
        band_width = self.data['BB_upper'] - self.data['BB_lower']
        self.data['BB_width'] = band_width / self.data['BB_middle']
        self.data['BB_percent'] = (self.data['close'] - self.data['BB_lower']) / band_width
        
        self.indicators['Bollinger_Bands'] = {
            'type': 'bollinger_bands',
            'period': period,
            'std_dev': std_dev,
            'description': f'布林带（{period}日，{std_dev}倍标准差）',
            'calculation': '基于移动平均线和标准差计算价格通道',
            'components': ['BB_upper', 'BB_middle', 'BB_lower', 'BB_width', 'BB_percent']
        }
    
    def calculate_macd(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> None:
        """计算MACD指标"""
        # 计算快线和慢线EMA
        ema_fast = self.data['close'].ewm(span=fast_period, adjust=False, min_periods=1).mean()
        ema_slow = self.data['close'].ewm(span=slow_period, adjust=False, min_periods=1).mean()
        
        # 计算DIF（差离值）
        self.data['MACD_DIF'] = ema_fast - ema_slow
        
        # 计算DEA（信号线）
        self.data['MACD_DEA'] = self.data['MACD_DIF'].ewm(span=signal_period, adjust=False, min_periods=1).mean()
        
        # 计算MACD柱状图
        self.data['MACD_histogram'] = self.data['MACD_DIF'] - self.data['MACD_DEA']
        
        self.indicators['MACD'] = {
            'type': 'macd',
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period,
            'description': '移动平均收敛发散指标',
            'calculation': '基于两条EMA线的差异计算趋势动量',
            'components': ['MACD_DIF', 'MACD_DEA', 'MACD_histogram']
        }
    
    def calculate_volume_indicators(self) -> None:
        """计算成交量相关指标"""
        # 计算成交量移动平均
        self.data['Volume_MA5'] = self.data['volume'].rolling(window=5, min_periods=1).mean()
        self.data['Volume_MA10'] = self.data['volume'].rolling(window=10, min_periods=1).mean()
        self.data['Volume_MA20'] = self.data['volume'].rolling(window=20, min_periods=1).mean()
        
        # 计算量比（当日成交量/过去5日平均成交量）
        self.data['Volume_Ratio'] = self.data['volume'] / self.data['Volume_MA5']
        
        # 计算成交量变化率
        self.data['Volume_Change'] = self.data['volume'].pct_change() * 100
        
        # 计算OBV（能量潮）
        obv = [0]
        for i in range(1, len(self.data)):
            if self.data['close'].iloc[i] > self.data['close'].iloc[i-1]:
                obv.append(obv[-1] + self.data['volume'].iloc[i])
            elif self.data['close'].iloc[i] < self.data['close'].iloc[i-1]:
                obv.append(obv[-1] - self.data['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        self.data['OBV'] = obv
        
        self.indicators['Volume_Indicators'] = {
            'type': 'volume',
            'description': '成交量相关指标',
            'calculation': '分析成交量变化和能量潮',
            'components': ['Volume_MA5', 'Volume_MA10', 'Volume_MA20', 'Volume_Ratio', 'Volume_Change', 'OBV']
        }
    
    def calculate_price_changes(self) -> None:
        """计算价格变化相关指标"""
        # 计算日收益率
        self.data['Daily_Return'] = self.data['close'].pct_change() * 100
        
        # 计算价格变化
        self.data['Price_Change'] = self.data['close'].diff()
        
        # 计算涨跌幅
        self.data['Change_Pct'] = (self.data['Price_Change'] / self.data['close'].shift(1)) * 100
        
        # 计算高低价差
        self.data['High_Low_Spread'] = self.data['high'] - self.data['low']
        
        # 计算价格位置（相对于当日高低点）
        self.data['Price_Position'] = (self.data['close'] - self.data['low']) / (self.data['high'] - self.data['low'])
        
        self.indicators['Price_Changes'] = {
            'type': 'price_analysis',
            'description': '价格变化分析指标',
            'calculation': '分析价格变动和相对位置',
            'components': ['Daily_Return', 'Price_Change', 'Change_Pct', 'High_Low_Spread', 'Price_Position']
        }
    
    def calculate_volatility_indicators(self) -> None:
        """计算波动率指标"""
        # 计算ATR（平均真实波幅）
        high_low = self.data['high'] - self.data['low']
        high_close = abs(self.data['high'] - self.data['close'].shift(1))
        low_close = abs(self.data['low'] - self.data['close'].shift(1))
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.data['ATR'] = tr.rolling(window=14, min_periods=1).mean()
        
        # 计算历史波动率（20日）
        self.data['Historical_Volatility'] = self.data['Daily_Return'].rolling(window=20, min_periods=1).std() * np.sqrt(252)
        
        self.indicators['Volatility_Indicators'] = {
            'type': 'volatility',
            'description': '波动率分析指标',
            'calculation': '衡量价格波动程度',
            'components': ['ATR', 'Historical_Volatility']
        }
    
    def get_support_resistance_levels(self, window: int = 20) -> Dict:
        """
        识别支撑位和阻力位
        
        Args:
            window: 用于识别局部极值的窗口大小
            
        Returns:
            包含支撑位和阻力位的字典
        """
        if len(self.data) < window:
            return {
                'resistance_levels': [],
                'support_levels': [],
                'current_price': self.data['close'].iloc[-1] if len(self.data) > 0 else None,
                'message': f'数据不足，需要至少{window}个数据点'
            }
        
        data = self.data.copy()
        
        # 识别局部高点和低点
        data['is_local_high'] = (
            (data['high'] == data['high'].rolling(window=window, center=True).max()) &
            (data['high'] > data['high'].shift(1)) &
            (data['high'] > data['high'].shift(-1))
        )
        
        data['is_local_low'] = (
            (data['low'] == data['low'].rolling(window=window, center=True).min()) &
            (data['low'] < data['low'].shift(1)) &
            (data['low'] < data['low'].shift(-1))
        )
        
        # 提取支撑位和阻力位
        resistance_levels = data[data['is_local_high']]['high'].tolist()
        support_levels = data[data['is_local_low']]['low'].tolist()
        
        # 去除重复值并排序
        resistance_levels = sorted(list(set(resistance_levels)), reverse=True)
        support_levels = sorted(list(set(support_levels)))
        
        # 获取当前价格
        current_price = data['close'].iloc[-1] if len(data) > 0 else None
        
        # 计算距离当前价格最近的支撑阻力位
        nearest_resistance = min(resistance_levels, key=lambda x: abs(x - current_price)) if resistance_levels else None
        nearest_support = min(support_levels, key=lambda x: abs(x - current_price)) if support_levels else None
        
        return {
            'resistance_levels': resistance_levels[:10],  # 取前10个阻力位
            'support_levels': support_levels[:10],        # 取前10个支撑位
            'current_price': current_price,
            'nearest_resistance': nearest_resistance,
            'nearest_support': nearest_support,
            'distance_to_resistance': (nearest_resistance - current_price) / current_price * 100 if nearest_resistance else None,
            'distance_to_support': (current_price - nearest_support) / current_price * 100 if nearest_support else None
        }
    
    def get_trend_analysis(self) -> Dict:
        """
        分析趋势方向
        
        Returns:
            趋势分析结果字典
        """
        if len(self.data) < 20:
            return {
                'trend': 'insufficient_data',
                'strength': 0,
                'message': '数据不足，需要至少20个数据点进行趋势分析'
            }
        
        # 使用最近20天的数据判断趋势
        recent_data = self.data.tail(20)
        
        # 计算价格变化
        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        price_change_pct = (price_change / recent_data['close'].iloc[0]) * 100
        
        # 判断趋势方向
        if price_change_pct > 10:
            trend = '强势上涨'
            trend_en = 'strong_uptrend'
            strength = min(abs(price_change_pct) / 20, 1.0)
        elif price_change_pct > 5:
            trend = '上涨'
            trend_en = 'uptrend'
            strength = min(abs(price_change_pct) / 15, 1.0)
        elif price_change_pct > 2:
            trend = '温和上涨'
            trend_en = 'mild_uptrend'
            strength = min(abs(price_change_pct) / 10, 1.0)
        elif price_change_pct < -10:
            trend = '强势下跌'
            trend_en = 'strong_downtrend'
            strength = min(abs(price_change_pct) / 20, 1.0)
        elif price_change_pct < -5:
            trend = '下跌'
            trend_en = 'downtrend'
            strength = min(abs(price_change_pct) / 15, 1.0)
        elif price_change_pct < -2