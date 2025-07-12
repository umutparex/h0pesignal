# src/analysis_engine.py

import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Any
from scipy.signal import find_peaks

class AnalysisEngine:
    """
    Tüm teknik analizleri pandas_ta kütüphanesi ile manuel olarak yapan,
    hatalardan arındırılmış, risk yönetimi ve trend uyumu odaklı Zirve Sürümü motoru.
    """
    def __init__(self, config: dict):
        self.config = config
        self.indicator_settings = self.config.get("indicator_settings", {})
        self.score_weights = self.config.get("skor_agirliklar", {})

    def run_full_analysis(self, klines_df: pd.DataFrame, market_data: Dict) -> Dict[str, Any]:
        if klines_df is None or len(klines_df) < self.indicator_settings.get("min_data_points", 200):
            return self._generate_empty_result("Yetersiz veri")

        # --- 1. Teknik Göstergeleri Hesapla ---
        try:
            # Her indikatörü tek tek çağırarak tam kontrol sağlıyoruz.
            klines_df.ta.ema(length=20, append=True)
            klines_df.ta.ema(length=50, append=True)
            klines_df.ta.ema(length=200, append=True)
            klines_df.ta.macd(append=True)
            klines_df.ta.rsi(append=True)
            klines_df.ta.stochrsi(append=True)
            klines_df.ta.bbands(append=True)
            klines_df.ta.cci(append=True)
            klines_df.ta.adx(append=True)
            klines_df.ta.supertrend(append=True)
            klines_df.ta.willr(append=True)
            klines_df.ta.obv(append=True)
            klines_df.ta.ichimoku(append=True)
            klines_df.ta.cdl_pattern(name="all", append=True)
            
            # HATA DÜZELTİLDİ: VWAP'ı pandas_ta'dan çağırmak yerine tamamen manuel olarak hesaplıyoruz.
            klines_df = self._calculate_manual_vwap(klines_df)
            
        except Exception as e:
            return self._generate_empty_result(f"İndikatör Hesaplama Hatası: {e}")

        # --- 2. Analiz Sonuçlarını Topla ---
        analysis_results = {}
        last_row = klines_df.iloc[-1]
        prev_row = klines_df.iloc[-2]

        try:
            analysis_results.update(self.analyze_ema(last_row))
            analysis_results.update(self.analyze_macd(last_row))
            analysis_results.update(self.analyze_rsi(last_row))
            analysis_results.update(self.analyze_stoch_rsi(last_row))
            analysis_results.update(self.analyze_bollinger_bands(last_row))
            analysis_results.update(self.analyze_cci(last_row))
            analysis_results.update(self.analyze_adx(last_row))
            analysis_results.update(self.analyze_williams_r(last_row))
            analysis_results.update(self.analyze_supertrend(last_row))
            analysis_results.update(self.analyze_vwap(last_row))
            analysis_results.update(self.analyze_ichimoku(last_row))
            analysis_results.update(self.analyze_obv(last_row, prev_row))
            analysis_results.update(self.analyze_candlestick(last_row))
            analysis_results.update(self.analyze_divergence(klines_df))
            analysis_results.update(self.analyze_classical_patterns(klines_df))
            analysis_results.update(self.analyze_funding_rate(market_data))
        except Exception as e:
            return self._generate_empty_result(f"Analiz Yorumlama Hatası: {e}")

        # --- 3. Puanlama, Filtreleme ve Sınıflandırma ---
        score = self.calculate_confluence_score(analysis_results)
        is_safe, reason = self._is_signal_safe(score, last_row)
        
        if not is_safe:
            strategy = f"Riskli ({reason})"
        else:
            strategy = self.classify_signal_strategy(score, analysis_results)

        final_score = score if is_safe else int(score / 2)
        summary = self.generate_summary_details(analysis_results)

        return {
            "score": final_score, "strategy": strategy, "fiyat": float(last_row["close"]),
            "details": analysis_results, "detay_str": summary
        }
    
    def _calculate_manual_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        """Günlük sıfırlanan VWAP'ı manuel olarak hesaplar."""
        df['TPV'] = ((df['high'] + df['low'] + df['close']) / 3) * df['volume']
        df['Cumulative TPV'] = df.groupby(df['timestamp'].dt.date)['TPV'].cumsum()
        df['Cumulative Volume'] = df.groupby(df['timestamp'].dt.date)['volume'].cumsum()
        df['VWAP_D'] = df['Cumulative TPV'] / df['Cumulative Volume']
        df.drop(['TPV', 'Cumulative TPV', 'Cumulative Volume'], axis=1, inplace=True)
        return df

    # --- Analiz Metotları ---
    def analyze_candlestick(self, last: pd.Series) -> Dict:
        pattern_cols = [col for col in last.index if col.startswith('CDL_')]
        pattern_name = "Yok"
        signal = 0
        for col in pattern_cols:
            if last[col] != 0:
                pattern_name = col.replace('CDL_', '')
                signal = 1 if last[col] > 0 else -1
                break
        return {"candlestick": {"value": pattern_name, "signal": signal}}

    def analyze_divergence(self, df: pd.DataFrame) -> Dict:
        if 'RSI_14' not in df.columns: return {"divergence": {"value": "Yok", "signal": 0}}
        rsi = df['RSI_14'].dropna()
        price = df['low'].loc[rsi.index]
        rsi_troughs, _ = find_peaks(-rsi, distance=10, width=1)
        price_troughs, _ = find_peaks(-price, distance=10, width=1)
        
        signal = 0; value = "Yok"
        if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
            if price.iloc[price_troughs[-1]] < price.iloc[price_troughs[-2]] and rsi.iloc[rsi_troughs[-1]] > rsi.iloc[rsi_troughs[-2]]:
                signal = 1; value = "Pozitif Uyumsuzluk"
        
        price_high = df['high'].loc[rsi.index]
        rsi_peaks, _ = find_peaks(rsi, distance=10, width=1)
        price_peaks, _ = find_peaks(price_high, distance=10, width=1)

        if signal == 0 and len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
            if price_high.iloc[price_peaks[-1]] > price_high.iloc[price_peaks[-2]] and rsi.iloc[rsi_peaks[-1]] < rsi.iloc[rsi_peaks[-2]]:
                signal = -1; value = "Negatif Uyumsuzluk"
        return {"divergence": {"value": value, "signal": signal}}

    def analyze_classical_patterns(self, df: pd.DataFrame) -> Dict:
        return {"patterns": {"value": "Geliştirilecek", "signal": 0}}
        
    def analyze_vwap(self, last: pd.Series) -> Dict:
        signal = 1 if last['close'] > last.get('VWAP_D', last['close']) else -1
        return {"vwap": {"value": "Üstünde" if signal == 1 else "Altında", "signal": signal}}

    def analyze_ema(self, last: pd.Series) -> Dict:
        periods = self.indicator_settings.get("ema", {}).get("periods", [50, 200])
        signal_sum = sum(1 if last['close'] > last.get(f'EMA_{p}', last['close']) else -1 for p in periods)
        signal = 1 if signal_sum > 0 else -1 if signal_sum < 0 else 0
        return {"ema": {"value": f"Fiyat > EMA{periods[0]}" if signal == 1 else f"Fiyat < EMA{periods[0]}", "signal": signal}}

    def analyze_macd(self, last: pd.Series) -> Dict:
        signal = 1 if last.get('MACD_12_26_9', 0) > last.get('MACDs_12_26_9', 0) else -1
        return {"macd": {"value": round(last.get('MACD_12_26_9', 0), 2), "signal": signal}}

    def analyze_rsi(self, last: pd.Series) -> Dict:
        rsi_val = last.get('RSI_14', 50)
        params = self.indicator_settings.get("rsi", {})
        signal = -1 if rsi_val > params.get("overbought", 70) else 1 if rsi_val < params.get("oversold", 30) else 0
        return {"rsi": {"value": round(rsi_val, 2), "signal": signal}}

    def analyze_stoch_rsi(self, last: pd.Series) -> Dict:
        stoch_rsi_k = last.get('STOCHRSIk_14_14_3_3', 50)
        signal = -1 if stoch_rsi_k > 80 else 1 if stoch_rsi_k < 20 else 0
        return {"stoch_rsi": {"value": round(stoch_rsi_k, 2), "signal": signal}}

    def analyze_bollinger_bands(self, last: pd.Series) -> Dict:
        signal = 1 if last['close'] < last.get('BBL_20_2.0', last['close']) else -1 if last['close'] > last.get('BBU_20_2.0', last['close']) else 0
        return {"bollinger_bands": {"value": "Alt Bant Altı" if signal == 1 else "Üst Bant Üstü" if signal == -1 else "Bant İçi", "signal": signal}}

    def analyze_cci(self, last: pd.Series) -> Dict:
        cci_val = last.get('CCI_20_0.015', 0)
        signal = -1 if cci_val > 100 else 1 if cci_val < -100 else 0
        return {"cci": {"value": round(cci_val, 2), "signal": signal}}

    def analyze_adx(self, last: pd.Series) -> Dict:
        adx_val = last.get('ADX_14', 0)
        plus_di = last.get('DMP_14', 0)
        minus_di = last.get('DMN_14', 0)
        trend_direction = 1 if plus_di > minus_di else -1
        signal = trend_direction if adx_val > self.indicator_settings.get("adx", {}).get("threshold", 25) else 0
        return {"adx": {"value": round(adx_val, 2), "signal": signal}}

    def analyze_williams_r(self, last: pd.Series) -> Dict:
        wr_val = last.get('WILLR_14', -50)
        signal = 1 if wr_val < -80 else -1 if wr_val > -20 else 0
        return {"williams_r": {"value": round(wr_val, 2), "signal": signal}}

    def analyze_supertrend(self, last: pd.Series) -> Dict:
        signal = 1 if last.get('SUPERTd_7_3.0', 0) == 1 else -1
        return {"supertrend": {"value": "AL" if signal == 1 else "SAT", "signal": signal}}

    def analyze_ichimoku(self, last: pd.Series) -> Dict:
        is_above_cloud = last['close'] > last.get('ISA_9_26_52', last['close']) and last['close'] > last.get('ISB_9_26_52', last['close'])
        is_below_cloud = last['close'] < last.get('ISA_9_26_52', last['close']) and last['close'] < last.get('ISB_9_26_52', last['close'])
        signal = 1 if is_above_cloud else -1 if is_below_cloud else 0
        return {"ichimoku": {"value": "Bulut Üstü" if signal == 1 else "Bulut Altı" if signal == -1 else "Bulut İçi", "signal": signal}}

    def analyze_obv(self, last: pd.Series, prev: pd.Series) -> Dict:
        signal = 1 if last.get('OBV', 0) > prev.get('OBV', 0) else -1
        return {"obv": {"value": f"{last.get('OBV', 0):.0f}", "signal": signal}}
    
    def analyze_funding_rate(self, market_data: Dict) -> Dict:
        fr = market_data.get("funding_rate")
        if fr is None: return {"funding_rate": {"value": "N/A", "signal": 0}}
        signal = -1 if fr > 0.01 else 1 if fr < -0.01 else 0
        return {"funding_rate": {"value": f"{fr:.4f}%", "signal": signal}}

    def _is_signal_safe(self, score: int, last: pd.Series) -> (bool, str):
        if score == 0: return True, ""
        long_term_ema_key = f'EMA_{max(self.indicator_settings.get("ema", {}).get("periods", [200]))}'
        long_term_ema_value = last.get(long_term_ema_key)
        if long_term_ema_value is None: return True, ""
        if score > 0 and last['close'] < long_term_ema_value: return False, "Trend Karşıtı"
        if score < 0 and last['close'] > long_term_ema_value: return False, "Trend Karşıtı"
        return True, "Trend Uyumlu"

    def calculate_confluence_score(self, analysis_results: dict) -> int:
        return int(sum(result.get('signal', 0) * self.score_weights.get(indicator, 1) for indicator, result in analysis_results.items()))

    def classify_signal_strategy(self, score: int, analysis: dict) -> str:
        thresholds = self.config.get("strategy_thresholds", {})
        abs_score = abs(score)
        if analysis.get("divergence", {}).get("signal") != 0 or analysis.get("candlestick", {}).get("signal") != 0: return "Dönüş Formasyonu"
        if abs_score >= thresholds.get("reversal_swing", 12): return "Güçlü Swing"
        if abs_score >= thresholds.get("trend_continuation", 8) and analysis.get("adx",{}).get("signal") != 0: return "Trend Takip"
        if abs_score >= thresholds.get("momentum_scalp", 5): return "Momentum Scalp"
        return "Zayıf Sinyal"
    
    def generate_summary_details(self, analysis: Dict[str, Any]) -> str:
        contributions = [(ind.upper(), res.get('signal', 0) * self.score_weights.get(ind, 1)) for ind, res in analysis.items() if res.get('signal', 0) != 0]
        contributions.sort(key=lambda x: abs(x[1]), reverse=True)
        top_3 = [f"{n}({'+' if v > 0 else ''}{v:.0f})" for n, v in contributions[:3]]
        return ", ".join(top_3) if top_3 else "Belirgin Sinyal Yok"

    def _generate_empty_result(self, reason: str) -> Dict[str, Any]:
        return {"score": 0, "strategy": reason, "fiyat": 0, "details": {}, "detay_str": reason}
