import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Quant Strategy Backtester", layout="wide")

st.title("📈 Quant Strategy Backtester")

# User input section
symbol = st.text_input("Enter stock ticker (e.g., AAPL, TSLA, NVDA):", value="AAPL")
start_date = st.date_input("Select start date:", value=datetime(2023, 1, 1))
end_date = st.date_input("Select end date:", value=datetime(2024, 1, 1))
run_button = st.button("🚀 Run Backtest")

# Strategy function
def generate_signals(df):
    df.columns = df.columns.str.lower()
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma50'] = df['close'].rolling(window=50).mean()
    df.dropna(inplace=True)

    position = 0
    capital = 10000
    history = []
    equity_curve = []

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        date = df.index[i]

        ma20 = row['ma20']
        ma50 = row['ma50']
        prev_ma20 = prev['ma20']
        prev_ma50 = prev['ma50']
        price = row['close']

        if pd.notna(ma20) and pd.notna(ma50) and pd.notna(prev_ma20) and pd.notna(prev_ma50):
            if ma20 > ma50 and prev_ma20 <= prev_ma50 and position == 0:
                position = capital // price
                capital -= position * price
                history.append((date, 'BUY', price, capital))

            elif ma20 < ma50 and prev_ma20 >= prev_ma50 and position > 0:
                capital += position * price
                history.append((date, 'SELL', price, capital))
                position = 0

        equity = capital + (position * price if position > 0 else 0)
        equity_curve.append((date, equity))

    if position > 0:
        final_price = df.iloc[-1]['close']
        capital += position * final_price
        history.append((df.index[-1], 'SELL-END', final_price, capital))

    result_df = pd.DataFrame(history, columns=['Date', 'Action', 'Price', 'Capital'])
    equity_df = pd.DataFrame(equity_curve, columns=['Date', 'Equity']).set_index('Date')
    return result_df, equity_df

# Main backtesting logic
if run_button:
    try:
        df = yf.download(symbol, start=start_date, end=end_date)
        if df.empty:
            st.error("Failed to retrieve data. Please check the ticker symbol.")
        else:
            st.success("✅ Data loaded successfully. Running strategy...")
            result, equity = generate_signals(df)

            st.subheader("📄 Trade Log")
            st.dataframe(result)

            st.subheader("💰 Equity Curve")
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(equity.index, equity['Equity'], label='Equity Curve', color='blue')
            ax.set_title(f"Equity Curve: {symbol}")
            ax.set_xlabel("Date")
            ax.set_ylabel("Total Equity ($)")
            ax.grid(True)
            st.pyplot(fig)

            net_profit = equity['Equity'].iloc[-1] - 10000
            st.metric(label="📊 Net Profit", value=f"${net_profit:.2f}", delta=f"{(net_profit/10000)*100:.2f}%")
    except Exception as e:
        st.error(f"❌ Error: {e}")
