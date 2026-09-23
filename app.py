import streamlit as st
import requests
import pandas as pd
import re

st.set_page_config(page_title="Competitor Price Monitor", layout="wide", initial_sidebar_state="collapsed")

# --- LOGIN CONFIG ---
# Set credentials in Streamlit Secrets (for deployed version)
# In Streamlit Cloud: Settings -> Secrets -> Add:
# [auth]
# username = "YOUR_USERNAME"
# password = "YOUR_PASSWORD"
try:
    AUTH_USER = st.secrets["auth"]["username"]
    AUTH_PASS = st.secrets["auth"]["password"]
except Exception:
    st.error("Authentication is not configured. Please contact the administrator.")
    st.stop()

def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

check_login()

def login_page():
    st.markdown("""
        <style>
        .login-container { max-width: 400px; margin: auto; padding-top: 50px; }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔐 Login")
        st.write("Please login to access Price Monitor")
        
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        
        if st.button("Login", use_container_width=True, type="primary"):
            if username == AUTH_USER and password == AUTH_PASS:
                st.session_state.logged_in = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")

def main_app():
    # Logout button in sidebar
    with st.sidebar:
        st.write("Logged in")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        st.divider()
        country = st.selectbox("Target Country Code", ["us", "in", "gb", "ca"], index=0)
        st.markdown("---")
        st.caption("Secure mode: API key loaded from secrets")

    st.title("🛍️ Competitor Price & Product Monitor")
    st.write("Compare real-time prices across Google Shopping vendors securely.")

    # --- SECURE API KEY EXTRACTION ---
    try:
        api_key = st.secrets["SERPER_API_KEY"]
    except KeyError:
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

# --- ROUTING ---
if not st.session_state.logged_in:
    login_page()
else:
    main_app()
