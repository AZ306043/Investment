#在跑之前要在終端機輸入"pip install yfinance pandas"下載讀取yahoo finance的插件，程式才能用

import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

# ====== 自訂設定區 ======
tickers    = [
    "AL", "SPNT", "YPF", "TDS", "FTAI",
    "EGO", "DORM", "FMS", "PONY", "WRD",
    "AMD", "OGS", "CELH", "IBM", "VNO",
    "GOLD", "KGC", "TSM", "ARMK", "AU"
]
start_date = "2024-12-01"   
end_date   = "2024-12-31"   
top_n      = 6              # 取前 n支 PEG 較高股票

# ====== 1. 計算每支股票的 PEG +年化成長率 ======
peg_dict    = {}
growth_dict = {}
valid_tickers = []

for tk in tickers:
    try:
        info = yf.Ticker(tk).info
    except Exception as e:
        print(f"⚠️ 取得 {tk} 基本面時發生錯誤，已跳過：{e}")
        continue

    pe = info.get("trailingPE") or info.get("forwardPE")
    qg = info.get("earningsQuarterlyGrowth")
    if pe is None or qg is None:
        print(f"⚠️ {tk} 缺少 PE 或 earningsQuarterlyGrowth，已跳過")
        continue

    g   = qg * 4
    peg = pe / g if g != 0 else None
    if peg is None:
        print(f"⚠️ {tk} 的 PEG 計算失敗，已跳過")
        continue

    peg_dict[tk]    = peg
    growth_dict[tk] = g
    valid_tickers.append(tk)

if not valid_tickers:
    raise RuntimeError("沒有任何有效資料可以計算。")

# ====== 2. 按 PEG 排序並取 top_n ======
sorted_pairs = sorted(peg_dict.items(), key=lambda x: x[1], reverse=True)
selected = [tk for tk, _ in sorted_pairs[:top_n]]
print(f"選出前 {top_n} 名 PEG 較高的股票：{selected}")

# ====== 3. 下載並輸出各檔 CSV（含 Growth/PEG summary） ======
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
end_inc = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

for tk in selected:
    try:
        df = yf.download(tk, start=start_date, end=end_inc, timeout=60, threads=False)
    except Exception as e:
        print(f"⚠️ 下載 {tk} 價格時失敗，已跳過：{e}")
        continue

    if df.empty:
        print(f"⚠️ {tk} 在此期間無資料，已跳過")
        continue

   
    df["Avg Growth (ann.)"] = np.nan
    df["PEG Ratio"]         = np.nan
    idx0 = df.index[0]
    df.at[idx0, "Avg Growth (ann.)"] = growth_dict[tk]
    df.at[idx0, "PEG Ratio"]         = peg_dict[tk]

    
    info = yf.Ticker(tk).info
    name = info.get("longName", tk).replace(" ", "_").replace("/", "_")
    fname = f"{name}_{start_date}_{end_date}.csv"
    path = os.path.join(desktop, fname)
    df.to_csv(path)
    print(f"✅ 已存檔：{path}")

# ====== 4. 建立日成長率+區間總成長率表 ======
series_list = []
for tk in selected:
    df = yf.download(tk, start=start_date, end=end_inc, timeout=60, threads=False)
    if df.empty:
        continue

    col = "Adj Close" if "Adj Close" in df.columns else "Close"
    s = df[col].copy()
    s.name = tk
    if len(s) >= 2:
        series_list.append(s)
    else:
        print(f"⚠️ {tk} 的 {col} 資料不足，跳過合併")

if not series_list:
    raise RuntimeError("沒有可用的價格序列，無法產生 returns/cumulative。")

price_df   = pd.concat(series_list, axis=1)
price_df.index.name = "Date"
returns    = price_df.pct_change().dropna(how="all")
cumulative = (price_df.iloc[-1] / price_df.iloc[0] - 1).to_frame(name="Total Growth")

# ====== 5. 輸出成長率 CSV ======
returns_path = os.path.join(desktop, f"returns_{start_date}_{end_date}.csv")
cumul_path   = os.path.join(desktop, f"cumulative_{start_date}_{end_date}.csv")
returns.to_csv(returns_path)
cumulative.to_csv(cumul_path)

print("✅ 已輸出：")
print(f"   - 日成長率：{returns_path}")
print(f"   - 區間總成長率：{cumul_path}")

