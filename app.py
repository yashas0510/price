import streamlit as st
import requests
import pandas as pd
import re

st.set_page_config(page_title="Competitor Price Monitor", layout="wide", initial_sidebar_state="collapsed")

# --- SECRETS CONFIG ---
# Only SERPER_API_KEY is required (Streamlit Secrets, never hardcoded).
# In Streamlit Cloud: Settings -> Secrets -> Add:
# SERPER_API_KEY = "YOUR_KEY_HERE"

def get_serper_key():
    # Top-level key (canonical layout): SERPER_API_KEY = "..."
    try:
        return st.secrets["SERPER_API_KEY"]
    except KeyError:
        pass
    # Tolerate key nested under [auth] (TOML puts every key after
    # an [auth] header into that table unless a new header starts).
    try:
        return st.secrets["auth"]["SERPER_API_KEY"]
    except KeyError:
        return None

def main_app():
    with st.sidebar:
        country = st.selectbox("Target Country Code", ["us", "in", "gb", "ca"], index=0)
        st.markdown("---")
        st.caption("Secure mode: API key loaded from secrets")

    st.title("🛍️ Competitor Price & Product Monitor")
    st.write("Compare real-time prices across Google Shopping vendors securely.")

    # --- SECURE API KEY EXTRACTION (Streamlit Secrets only, never env/hardcoded) ---
    api_key = get_serper_key()
    if not api_key:
        st.error("Service is not configured. Please contact the administrator.")
        st.stop()

    product_query = st.text_input("Enter product name (e.g., Sony WH-1000XM4)", "")

    def clean_price(price_str):
        try:
            numbers = re.findall(r"[-+]?\d*\.\d+|\d+", price_str.replace(",", ""))
            if numbers:
                return float(numbers[0])
        except:
            pass
        return 0.0

    if st.button("Compare Prices") and product_query:
        with st.spinner("Fetching best deals from Google Shopping..."):
            url = "https://google.serper.dev/shopping"
            payload = {
                "q": product_query,
                "gl": country,
                "hl": "en"
            }
            headers = {
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            }
            
            try:
                response = requests.post(url, json=payload, headers=headers)
                data = response.json()
                
                if "shopping" in data and len(data["shopping"]) > 0:
                    raw_results = data["shopping"]
                    processed_list = []
                    
                    for item in raw_results:
                        raw_price = item.get("price", "N/A")
                        
                        processed_list.append({
                            "Merchant / Source": item.get("source", "Unknown"),
                            "Product Title": item.get("title", "No Title"),
                            "Price (Raw)": raw_price,
                            "Price_Numeric": clean_price(raw_price),
                            "Delivery": item.get("delivery", "Not specified"),
                            "Product Link": item.get("link", "#")
                        })
                    
                    df = pd.DataFrame(processed_list)
                    df_sorted = df.sort_values(by="Price_Numeric", ascending=True)
                    df_display = df_sorted.drop(columns=["Price_Numeric"])
                    
                    best_deal = df_sorted.iloc[0]
                    col1, col2 = st.columns(2)
                    col1.metric("Lowest Price Found", best_deal["Price (Raw)"], f"via {best_deal['Merchant / Source']}")
                    col2.metric("Total Retailers Crawled", len(df_display))
                    
                    st.success("Results loaded & sorted successfully!")
                    
                    st.dataframe(
                        df_display, 
                        column_config={
                            "Product Link": st.column_config.LinkColumn("View Deal On Store")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                else:
                    st.warning("No shopping data found for this product query.")
                    
            except Exception as e:
                st.error(f"An error occurred: {e}")

# --- APP ---
main_app()
