import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import time

# Set up page configuration
st.set_page_config(page_title="NSE Sectoral Heatmap Engine", layout="wide")

st.title("📊 NSE Sectoral Heatmap & Stock Trickle-Down Engine")
st.markdown("Identify institutional buying/selling sectors and pinpoint the leading constituent stocks.")

# Hardened session handler to bypass cloud server blocks
def fetch_nse_data_hardened(url):
    # Spoofing a standard desktop browser exactly
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.nseindia.com/",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    session = requests.Session()
    # Step 1: Hit the main page first to establish valid user cookies
    base_response = session.get("https://www.nseindia.com", headers=headers, timeout=10)
    
    # Step 2: Small delay to mimic human behavior
    time.sleep(1)
    
    # Step 3: Fetch the actual API data using the active session cookies
    response = session.get(url, headers=headers, timeout=15)
    
    if response.status_code == 401 or response.status_code == 403:
        raise Exception("NSE blocked the connection request.")
        
    return response.json()

# --- STEP 1: FETCH & FILTER SECTORAL DATA ---
@st.cache_data(ttl=120) # Increased cache to 2 mins to prevent aggressive hitting from the server
def get_sector_data():
    raw_data = fetch_nse_data_hardened("https://www.nseindia.com/api/allIndices")
    df = pd.DataFrame(raw_data['data'])
    
    # Core Sectoral Indices
    sectoral_list = [
        'NIFTY BANK', 'NIFTY AUTO', 'NIFTY FINANCIAL SERVICES', 
        'NIFTY FMCG', 'NIFTY IT', 'NIFTY MEDIA', 'NIFTY METAL', 
        'NIFTY PHARMA', 'NIFTY REALTY', 'NIFTY PRIVATE BANK', 
        'NIFTY PSU BANK', 'NIFTY HEALTHCARE INDEX', 'NIFTY OIL & GAS'
    ]
    df_sectors = df[df['index'].isin(sectoral_list)].copy()
    df_sectors['percentChange'] = pd.to_numeric(df_sectors['percentChange'])
    df_sectors['totalTradedValue'] = pd.to_numeric(df_sectors['totalTradedValue'])
    return df_sectors.sort_values(by='percentChange', ascending=False)

try:
    df_sectors = get_sector_data()
    
    # Metrics
    top_buying_sector = df_sectors.iloc[0]['index']
    top_buying_val = df_sectors.iloc[0]['percentChange']
    top_selling_sector = df_sectors.iloc[-1]['index']
    top_selling_val = df_sectors.iloc[-1]['percentChange']
    
    col1, col2 = st.columns(2)
    col1.metric(label="🔥 Highest Buying Sector", value=top_buying_sector, delta=f"{top_buying_val}%")
    col2.metric(label="❄️ Highest Selling Sector", value=top_selling_sector, delta=f"{top_selling_val}%", delta_color="inverse")

    st.subheader("Sectoral Performance Heatmap")
    
    fig = px.bar(
        df_sectors, 
        x='index', 
        y='percentChange',
        color='percentChange',
        color_continuous_scale='RdYlGn',
        color_continuous_midpoint=0,
        labels={'index': 'Sectoral Index', 'percentChange': '% Change'},
        text_auto='.2f'
    )
    fig.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig, use_container_width=True)

    # --- STEP 2: TRICKLE DOWN TO STOCKS ---
    st.markdown("---")
    st.subheader("🎯 Deep Dive: Select Sector to View Constituent Stocks")
    
    selected_sector = st.selectbox("Pick a sector to view individual stock momentum:", df_sectors['index'].tolist())
    
    @st.cache_data(ttl=120)
    def get_stock_data(sector_name):
        slug = sector_name.replace(" ", "%20")
        raw_stocks = fetch_nse_data_hardened(f"https://www.nseindia.com/api/equity-stockIndices?index={slug}")
        df_stocks = pd.DataFrame(raw_stocks['data'])
        
        df_stocks = df_stocks[df_stocks['symbol'] != sector_name].copy()
        df_stocks['pChange'] = pd.to_numeric(df_stocks['pChange'])
        df_stocks['totalTradedValue'] = pd.to_numeric(df_stocks['totalTradedValue'])
        df_stocks['lastPrice'] = pd.to_numeric(df_stocks['lastPrice'])
        
        return df_stocks[['symbol', 'lastPrice', 'pChange', 'totalTradedValue']]

    df_stocks = get_stock_data(selected_sector)
    
    stock_col1, stock_col2 = st.columns(2)
    
    with stock_col1:
        st.write(f"### 📈 Heavy Buying in {selected_sector}")
        top_gainers = df_stocks.sort_values(by='pChange', ascending=False).head(5)
        st.dataframe(top_gainers, use_container_width=True, hide_index=True)
        
    with stock_col2:
        st.write(f"### 📉 Heavy Selling in {selected_sector}")
        top_losers = df_stocks.sort_values(by='pChange', ascending=True).head(5)
        st.dataframe(top_losers, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("NSE Firewall is currently blocking this cloud server region.")
    st.info("💡 Pro-Tip: Wait 1 minute and refresh the page. If the cloud IP remains blocked, we can shift the data pipeline to use a third-party Google Sheets backend.")
