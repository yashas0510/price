import streamlit as st
import requests
import pandas as pd
import re

# Set page layout to wide
st.set_page_config(page_title="Competitor Price Monitor", layout="wide")

st.title("🛍️ Competitor Price & Product Monitor")
st.write("Compare real-time prices across Google Shopping vendors securely.")

# --- SECURE API KEY EXTRACTION ---
# This automatically reads from .streamlit/secrets.toml locally 
# AND from the dashboard settings when deployed online.
try:
    api_key = st.secrets["SERPER_API_KEY"]
except KeyError:
    st.error("API Key missing! Please set SERPER_API_KEY in your Streamlit Secrets.")
    st.stop()

# Target configuration (Hidden or adjusted via sidebar if needed)
country = st.sidebar.selectbox("Target Country Code", ["us", "in", "gb", "ca"], index=0)

# Main search bar
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
        url = "https://serper.dev"
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
                
                # Show key highlights
                best_deal = df_sorted.iloc[0]
                col1, col2 = st.columns(2)
                col1.metric("Lowest Price Found", best_deal["Price (Raw)"], f"via {best_deal['Merchant / Source']}")
                col2.metric("Total Retailers Crawled", len(df_display))
                
                st.success("Results loaded & sorted successfully!")
                
                # Display final interactive table
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
