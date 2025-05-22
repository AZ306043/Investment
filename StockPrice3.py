import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta

# ====== 參數設定 ======
industry_tickers = {
    "半導體業": [
        '2330.TW','2454.TW','2303.TW','3711.TW','2379.TW',
        '3034.TW','6415.TW','3529.TW','2449.TW','5347.TW',
        '5274.TW','3443.TW','3661.TW','5269.TW','6488.TW'
    ],
    "金融保險": [
        '2881.TW','2882.TW','2891.TW','2886.TW','2884.TW',
        '2885.TW','2880.TW','5880.TW','2892.TW','2883.TW',
        '2890.TW','5876.TW','2887.TW','2888.TW','2801.TW'
    ],
    "電腦及週邊設備業": [
        '2382.TW','2357.TW','3231.TW','2395.TW','2301.TW',
        '3017.TW','2376.TW','2356.TW','2377.TW','2324.TW'
    ],
    "電子零組件業": [
        '2308.TW','2327.TW','2383.TW','2059.TW','3037.TW',
        '3533.TW','2385.TW','2368.TW','3044.TW','2313.TW'
    ],
    "其他電子業": [
        '2317.TW','2474.TW','2360.TW','2404.TW','2354.TW',
        '6139.TW','6196.TW','3324.TW','2312.TW','3030.TW'
    ],
    "通信網路業": [
        '2412.TW','3045.TW','2345.TW','4904.TW','6285.TW',
        '2498.TW','5388.TW','2439.TW','3363.TW','3491.TW'
    ],
    "航運業": [
        '2603.TW','2615.TW','2609.TW','2618.TW','2610.TW',
        '2606.TW','2607.TW','2208.TW','2608.TW','2605.TW'
    ],
    "光電業": [
        '3008.TW','8069.TWO','3481.TW','2409.TW','6176.TW',
        '3406.TW','3019.TW','2393.TW','5371.TWO','6116.TW'
    ],
    "電機機械": [
        '1519.TW','1504.TW','2371.TW','1503.TW','1513.TW',
        '1560.TW','1514.TW','4506.TWO','4532.TW','8255.TWO'
    ],
    "建材營造": [
        '2542.TW','2539.TW','2540.TW','2504.TW','5522.TW',
        '2543.TW','2548.TW','1808.TW','2520.TW','2530.TW'
    ],
}

industry_metric = {
    "半導體業":         "trailingPE",
    "金融保險":         "priceToBook",
    "電腦及週邊設備業": "trailingPE",
    "電子零組件業":     "trailingPE",
    "其他電子業":       "trailingPE",
    "通信網路業":       "DDM_total_return",
    "航運業":           "priceToBook",
    "光電業":           "trailingPE",
    "電機機械":         "trailingPE",
    "建材營造":         "priceToBook",
}

metric_ascending = {
    "trailingPE":        True,   
    "priceToBook":       True,   
    "DDM_total_return":  False,  
}

start_date = "2020-01-01"
end_date   = "2024-12-31"
end_inc    = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))\
             .strftime("%Y-%m-%d")

selected = []

# ====== 各產業篩選確保 2 支資料完整的股票 ======
# 10日容錯
min_days_required = 252 * 10 - 10

for industry, tickers in industry_tickers.items():
    metric = industry_metric[industry]
    asc    = metric_ascending[metric]
    records = []

    for tk in tickers:
        try:
            info = yf.Ticker(tk).info
        except:
            continue
        if metric == "DDM_total_return":
            dy = info.get("dividendYield")
            qg = info.get("earningsQuarterlyGrowth")
            if dy is None or qg is None:
                continue
            val = dy + qg * 4
        else:
            val = info.get(metric)
        if val is None:
            continue
        records.append({"ticker": tk, "value": val})

    if not records:
        print(f"⚠️ {industry}：無基本面資料，跳過")
        continue

    df_meta = pd.DataFrame(records).sort_values("value", ascending=asc)

    # 選出2支並檢查資料完整度
    chosen = []
    for tk in df_meta["ticker"]:
        if len(chosen) >= 2:
            break
        df_tmp = yf.download(tk, start=start_date, end=end_inc, threads=False)
        if df_tmp.empty:
            continue
        col = "Adj Close" if "Adj Close" in df_tmp.columns else "Close"
        s = df_tmp[col].dropna()
        if s.shape[0] >= min_days_required:
            chosen.append(tk)
    if len(chosen) < 2:
        print(f"⚠️ {industry}：資料不足，實際選出 {len(chosen)} 支")
    else:
        print(f"{industry} → 選出：{chosen}")
    selected += chosen

# ====== 下載並存每檔股票的歷史股價 ======
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
for tk in selected:
    df = yf.download(tk, start=start_date, end=end_inc, threads=False)
    if df.empty:
        continue
    df.to_csv(os.path.join(desktop, f"{tk}_{start_date}_{end_date}.csv"))

# ====== 合併日報酬率表並輸出 ======
series_list = []
for tk in selected:
    df = yf.download(tk, start=start_date, end=end_inc, threads=False)
    if df.empty:
        continue
    col = "Adj Close" if "Adj Close" in df.columns else "Close"
    s = df[col].copy()
    s.name = tk
    if s.dropna().shape[0] >= 2:
        series_list.append(s)

if not series_list:
    raise RuntimeError("無可用價格序列，無法計算報酬率。")

price_df = pd.concat(series_list, axis=1)
price_df.index.name = "Date"

returns = price_df.pct_change()

returns = returns.dropna(how='all')

returns = returns.fillna(0)


returns = returns.loc[:, (returns != 0).any(axis=0)]

# 輸出個股日報酬率
stocks_csv = os.path.join(desktop, f"taiwan_stocks_returns_{start_date}_{end_date}.csv")
returns.to_csv(stocks_csv)
print(f"✅ 個股日報酬率：{stocks_csv}")

# ====== 加權指數報酬率 ======
idx = yf.download("^TWII", start=start_date, end=end_inc, threads=False)
if not idx.empty:
    col    = "Adj Close" if "Adj Close" in idx.columns else "Close"
    idx_r  = idx[col].pct_change().dropna()
    idx_csv= os.path.join(desktop, f"taiwan_index_returns_{start_date}_{end_date}.csv")
    idx_r.to_csv(idx_csv)
    print(f"✅ 指數報酬率：{idx_csv}")

