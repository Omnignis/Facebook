import streamlit as st
import os
import requests
from supabase import create_client

st.set_page_config(page_title="Omnignis Analytics Hub", layout="centered")
st.title("⛪ Church Social Media Attendance Portal")

# 1. Connect to your Supabase Vault
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Use Service Role key to save data safely
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Default profile user for this session
user_email = "pastor@gstomball.org"

# ==========================================
# PHASE 2: THE OAUTH CALLBACK HANDLER TRAP
# ==========================================
# Look directly at the URL address bar using Streamlit's built-in parameters feature
url_parameters = st.query_params

if "code" in url_parameters:
    # We caught a callback from Facebook or Google!
    secure_code = url_parameters["code"]
    
    with st.spinner("Securely shaking hands with the platform and saving keys..."):
        # Check if this code is from Facebook
        if "fb_success" not in st.session_state: 
            # 1. Exchange the temporary code for a User Access Token
            token_url = "https://graph.facebook.com/v20.0/oauth/access_token"
            token_params = {
                "client_id": os.getenv("FB_CLIENT_ID"),
                "client_secret": os.getenv("FB_CLIENT_SECRET"),
                "redirect_uri": "https://omnignis.com/", # Must match your App settings exactly
                "code": secure_code
            }
            res = requests.get(token_url, params=token_params).json()
            user_token = res.get("access_token")
            
            if user_token:
                # 2. Convert the User Token into your Page Access Token and Page ID
                accounts_url = "https://graph.facebook.com/v20.0/me/accounts"
                accounts_res = requests.get(accounts_url, params={"access_token": user_token}).json()
                
                page_data = accounts_res.get("data", [{}])[0] 
                page_token = page_data.get("access_token")
                page_id = page_data.get("id")
                
                if page_token and page_id:
                    # 3. Store the credentials inside your Supabase vault table
                    supabase.table("church_profiles").upsert({
                        "user_email": user_email, 
                        "fb_page_token": page_token,
                        "fb_page_id": page_id
                    }).execute()
                    
                    st.success("🎉 Facebook Page Linked Successfully!")
                    
    # Clean up the URL bar so the user can use the dashboard normally
    st.query_params.clear()

# ==========================================
# PHASE 3: THE USER DASHBOARD FRONTEND
# ==========================================
# Fetch current integration statuses out of Supabase to update the screen display
db_query = supabase.table("church_profiles").select("*").eq("user_email", user_email).execute()
profile = db_query.data[0] if db_query.data else {}

st.subheader("Integration Status")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Facebook Integration")
    if profile.get("fb_page_token"):
        st.success("✅ Facebook Page Connected")
    else:
        # Construct the official link sending them to login securely on Facebook
        fb_auth_url = (
            f"https://www.facebook.com/v20.0/dialog/oauth?"
            f"client_id={os.getenv('FB_CLIENT_ID')}"
            f"&redirect_uri=https://omnignis.com/"
            f"&state={user_email}"
            f"&scope=pages_read_engagement,pages_read_user_content,read_insights"
        )
        st.markdown(f'<a href="{fb_auth_url}" target="_blank"><button style="background-color:#1877F2;color:white;border:none;padding:10px 20px;border-radius:5px;cursor:pointer;">Connect Facebook Page</button></a>', unsafe_url=True)

with col2:
    st.markdown("### YouTube Integration")
    if profile.get("yt_refresh_token"):
        st.success("✅ YouTube Channel Connected")
    else:
        st.info("YouTube connection link configuration setup goes here.")

st.write("---")
st.subheader("Reporting Utilities")
if profile.get("fb_page_token"):
    st.button("🔄 Trigger Manual Attendance Run Report")
else:
    st.warning("Connect your accounts above to begin generating automated reports.")
