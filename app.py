
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

st.set_page_config(
    page_title="Bitcoin Market Replay",
    page_icon="₿",
    layout="wide"
)

st.title("₿ Bitcoin Historical Market Replay")
st.caption("過去のビットコイン相場を再生して売買を練習するシミュレーター")


# -------------------------
# 価格データ取得
# -------------------------
@st.cache_data(ttl=300)
def get_btc_data():

    url = "https://query1.finance.yahoo.com/v8/finance/chart/BTC-JPY"

    params = {
        "range": "60d",
        "interval": "1h"
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    result = data["chart"]["result"][0]

    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]

    df = pd.DataFrame({
        "time": pd.to_datetime(timestamps, unit="s"),
        "open": quote["open"],
        "high": quote["high"],
        "low": quote["low"],
        "close": quote["close"],
        "volume": quote["volume"]
    })

    df = df.dropna().reset_index(drop=True)

    return df


# -------------------------
# データ取得エラー処理
# -------------------------
try:
    df = get_btc_data()

except Exception as e:
    st.error("価格データを取得できませんでした。時間をおいて再度お試しください。")
    st.caption(str(e))
    st.stop()


if df.empty:
    st.error("価格データがありません。")
    st.stop()


# -------------------------
# シミュレーション設定
# -------------------------
if "cash" not in st.session_state:
    st.session_state.cash = 1_000_000

if "btc" not in st.session_state:
    st.session_state.btc = 0.0

if "trades" not in st.session_state:
    st.session_state.trades = []

if "replay_index" not in st.session_state:
    st.session_state.replay_index = min(50, len(df) - 1)


# -------------------------
# 再生位置
# -------------------------
st.subheader("⏳ 過去チャートの再生")

max_index = len(df) - 1

st.session_state.replay_index = min(
    st.session_state.replay_index,
    max_index
)

index = st.slider(
    "時間を進める / 戻す",
    min_value=0,
    max_value=max_index,
    value=st.session_state.replay_index,
    key="timeline"
)

st.session_state.replay_index = index

visible = df.iloc[:index + 1].copy()
current = visible.iloc[-1]

price = float(current["close"])


# -------------------------
# 資産情報
# -------------------------
total_assets = st.session_state.cash + st.session_state.btc * price

col1, col2, col3, col4 = st.columns(4)

col1.metric("BTC価格", f"¥{price:,.0f}")
col2.metric("現金残高", f"¥{st.session_state.cash:,.0f}")
col3.metric("保有BTC", f"{st.session_state.btc:.6f} BTC")
col4.metric("総資産（評価額）", f"¥{total_assets:,.0f}")

st.caption("※初期資金100万円。BTC価格は日本円建てです。")


# -------------------------
# チャート
# -------------------------
st.subheader("📈 Bitcoin価格チャート")

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=visible["time"],
    open=visible["open"],
    high=visible["high"],
    low=visible["low"],
    close=visible["close"],
    name="BTC"
))

fig.update_layout(
    template="plotly_dark",
    height=550,
    xaxis_title="Time",
    yaxis_title="Price (JPY)",
    xaxis_rangeslider_visible=False
)

st.plotly_chart(fig, use_container_width=True)

st.write(
    "現在の再生時刻：",
    current["time"].strftime("%Y-%m-%d %H:%M")
)


# -------------------------
# 売買シミュレーション
# -------------------------
st.subheader("💰 売買シミュレーション")

buy_col, sell_col = st.columns(2)


# -------------------------
# 購入
# -------------------------
with buy_col:

    st.markdown("### 🟢 BTCを購入")

    buy_amount = st.number_input(
        "購入するBTC数量",
        min_value=0.000001,
        value=0.001,
        step=0.001,
        format="%.6f",
        key="buy_amount"
    )

    if st.button("購入する", use_container_width=True):

        cost = price * buy_amount

        if cost <= st.session_state.cash:

            st.session_state.cash -= cost
            st.session_state.btc += buy_amount

            st.session_state.trades.append({
                "日時": current["time"],
                "売買": "購入",
                "価格": price,
                "数量": buy_amount
            })

            st.success(f"{buy_amount:.6f} BTCを購入しました。")

        else:
            st.error("現金残高が足りません。")


# -------------------------
# 売却
# -------------------------
with sell_col:

    st.markdown("### 🔴 BTCを売却")

    sell_amount = st.number_input(
        "売却するBTC数量",
        min_value=0.000001,
        value=0.001,
        step=0.001,
        format="%.6f",
        key="sell_amount"
    )

    if st.button("売却する", use_container_width=True):

        if sell_amount <= st.session_state.btc:

            proceeds = price * sell_amount

            st.session_state.cash += proceeds
            st.session_state.btc -= sell_amount

            st.session_state.trades.append({
                "日時": current["time"],
                "売買": "売却",
                "価格": price,
                "数量": sell_amount
            })

            st.success(f"{sell_amount:.6f} BTCを売却しました。")

        else:
            st.error("保有BTCが足りません。")


# -------------------------
# 取引履歴
# -------------------------
st.subheader("📋 売買履歴")

if st.session_state.trades:

    history = pd.DataFrame(st.session_state.trades)

    st.dataframe(
        history,
        use_container_width=True
    )

else:

    st.info("まだ取引履歴はありません。")


# -------------------------
# リセット
# -------------------------
if st.button("シミュレーションをリセット"):

    st.session_state.cash = 1_000_000
    st.session_state.btc = 0.0
    st.session_state.trades = []
    st.session_state.replay_index = min(50, len(df) - 1)

    st.rerun()
