import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Set up page configuration
st.set_page_config(page_title="NSE Sectoral Heatmap Engine", layout="wide")

st.title("📊 NSE Sectoral Heatmap & Stock Trickle-Down Engine")
st.markdown("Identify institutional buying/selling sectors and pinpoint the leading constituent stocks.")

# Custom function to fetch data bypassing basic user-agent blocks
def fetch_nse_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br"
    }
    # Using a session to handle cookies if required by NSE API
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers) # hit main page for session cookies
    response = session.get(url, headers=headers)
    return response.json()

# --- STEP 1: FETCH & FILTER SECTORAL DATA ---
@st.cache_data(ttl=60) # Cache data for 1 minute during live market hours
def get_sector_data():
    raw_data = fetch_nse_data("https://www.nseindia.com/api/allIndices")
    df = pd.DataFrame(raw_data['data'])
    
    # Core Sectoral Indices to monitor
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
    
    # Top metrics display
    top_buying_sector = df_sectors.iloc[0]['index']
    top_buying_val = df_sectors.iloc[0]['percentChange']
    top_selling_sector = df_sectors.iloc[-1]['index']
    top_selling_val = df_sectors.iloc[-1]['percentChange']
    
    col1, col2 = st.columns(2)
    col1.metric(label="🔥 Highest Buying Sector", value=top_buying_sector, delta=f"{top_buying_val}%")
    col2.metric(label="❄️ Highest Selling Sector", value=top_selling_sector, delta=f"{top_selling_val}%", delta_color="inverse")

    st.subheader("Sectoral Performance Heatmap")
    
    # Create an interactive color-coded bar chart (acting as our heatmap)
    fig = px.bar(
        df_sectors, 
        x='index', 
        y='percentChange',
        color='percentChange',
        color_continuous_scale='RdYlGn', # Red to Yellow to Green layout
        color_continuous_midpoint=0,
        labels={'index': 'Sectoral Index', 'percentChange': '% Change'},
        text_auto='.2f'
    )
    fig.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig, use_container_width=True)

    # --- STEP 2: TRICKLE DOWN TO STOCKS ---
    st.markdown("---")
    st.subheader("🎯 Deep Dive: Select Sector to View Constituent Stocks")
    
    # User dropdown to select a specific sector, defaults to the highest buying one
    selected_sector = st.selectbox("Pick a sector to view individual stock momentum:", df_sectors['index'].tolist())
    
    @st.cache_data(ttl=60)
    def get_stock_data(sector_name):
        slug = sector_name.replace(" ", "%20")
        raw_stocks = fetch_nse_data(f"https://www.nseindia.com/api/equity-stockIndices?index={slug}")
        df_stocks = pd.DataFrame(raw_stocks['data'])
        
        # Filter out the summary rows
        df_stocks = df_stocks[df_stocks['symbol'] != sector_name].copy()
        
        # Convert necessary values to numbers
        df_stocks['pChange'] = pd.to_numeric(df_stocks['pChange'])
        df_stocks['totalTradedValue'] = pd.to_numeric(df_stocks['totalTradedValue'])
        df_stocks['lastPrice'] = pd.to_numeric(df_stocks['lastPrice'])
        
        return df_stocks[['symbol', 'identifier', 'lastPrice', 'pChange', 'totalTradedValue']]

    df_stocks = get_stock_data(selected_sector)
    
    # Split stock layout into Gainers and Losers within that sector
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
    st.error("Error fetching data from NSE. The server might be throttling requests or market data is currently unavailable.")
    st.info("Technical details: Ensure your IP isn't blocked by NSE for frequent API hits.")
