import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Quant Strategy Backtester", layout="wide")

st.title("📈 Quant Strategy Backtester")

# === User Inputs ===
symbol = st.text_input("Enter stock ticker (e.g., AAPL, TSLA, NVDA):", value="AAPL")
start_date = st.date_input("Select start date:", value=datetime(2023, 1, 1))
end_date = st.date_input("Select end date:", value=datetime(2024, 1, 1))
strategy_option = st.selectbox("Choose Strategy:", ["MA Crossover", "RSI"])
run_button = st.button("🚀 Run Backtest")

# === Strategy Logic ===
def generate_signals(df, strategy="MA Crossover"):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = df.columns.str.lower()

    capital = 10000
    position = 0
    history = []
    equity_curve = []

    if strategy == "MA Crossover":
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma50'] = df['close'].rolling(50).mean()
        df.dropna(inplace=True)

        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            date = df.index[i]

            if pd.notna(row['ma20']) and pd.notna(row['ma50']) and pd.notna(prev['ma20']) and pd.notna(prev['ma50']):
                if row['ma20'] > row['ma50'] and prev['ma20'] <= prev['ma50'] and position == 0:
                    position = capital // row['close']
                    capital -= position * row['close']
                    history.append((date, 'BUY', row['close'], capital))

                elif row['ma20'] < row['ma50'] and prev['ma20'] >= prev['ma50'] and position > 0:
                    capital += position * row['close']
                    history.append((date, 'SELL', row['close'], capital))
                    position = 0

            equity = capital + (position * row['close'] if position > 0 else 0)
            equity_curve.append((date, equity))

    elif strategy == "RSI":
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df.dropna(inplace=True)

        for i in range(1, len(df)):
            row = df.iloc[i]
            date = df.index[i]

            if row['rsi'] < 30 and position == 0:
                position = capital // row['close']
                capital -= position * row['close']
                history.append((date, 'BUY', row['close'], capital))

            elif row['rsi'] > 70 and position > 0:
                capital += position * row['close']
                history.append((date, 'SELL', row['close'], capital))
                position = 0

            equity = capital + (position * row['close'] if position > 0 else 0)
            equity_curve.append((date, equity))

    if position > 0:
        final_price = df.iloc[-1]['close']
        capital += position * final_price
        history.append((df.index[-1], 'SELL-END', final_price, capital))

    result_df = pd.DataFrame(history, columns=['Date', 'Action', 'Price', 'Capital'])
    equity_df = pd.DataFrame(equity_curve, columns=['Date', 'Equity']).set_index('Date')
    return result_df, equity_df

# === Main Backtest Execution ===
if run_button:
    try:
        df = yf.download(symbol, start=start_date, end=end_date)
        if df.empty:
            st.error("Failed to retrieve data. Please check the ticker symbol.")
        else:
            st.success("✅ Data loaded successfully. Running strategy...")
            result, equity = generate_signals(df, strategy_option)

            st.subheader("📄 Trade Log")
            st.dataframe(result)

            st.subheader("💰 Equity Curve")
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(equity.index, equity['Equity'], label='Equity Curve', color='blue')
            for idx, row in result.iterrows():
                color = 'green' if row['Action'].startswith('BUY') else 'red'
                ax.scatter(row['Date'], row['Price'], color=color, label=row['Action'], alpha=0.7)
            ax.set_title(f"Equity Curve: {symbol} ({strategy_option})")
            ax.set_xlabel("Date")
            ax.set_ylabel("Total Equity ($)")
            ax.grid(True)
            st.pyplot(fig)

            net_profit = equity['Equity'].iloc[-1] - 10000
            days = (equity.index[-1] - equity.index[0]).days
            annualized_return = ((equity['Equity'].iloc[-1] / 10000) ** (365 / days) - 1) * 100 if days > 0 else 0

            st.metric(label="📊 Net Profit", value=f"${net_profit:.2f}", delta=f"{(net_profit/10000)*100:.2f}%")
            st.metric(label="📈 Annualized Return", value=f"{annualized_return:.2f}%")
    except Exception as e:
        st.error(f"❌ Error: {e}")
