import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import traceback

st.set_page_config(page_title="Debug Mode")
st.title("🕵️‍♂️ Database Diagnostic")

def run_test():
    try:
        # 1. CONNECT
        st.info("Attempting to connect to Google Cloud...")
        creds_dict = st.secrets["gcp_service_account"]
        SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        
        # 2. OPEN SHEET (Using your confirmed URL)
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1tNo2v2FWJUEj5cPg0MWk4UuqiCYNx9S63_-Ok3f54CM/edit"
        sheet = client.open_by_url(SHEET_URL)
        st.success(f"✅ Connected to Sheet: {sheet.title}")

        # 3. READ EMPLOYEES TAB
        st.info("Looking for 'Employees' tab...")
        worksheet = sheet.worksheet("Employees")
        st.success("✅ Found 'Employees' tab")
        
        # 4. CHECK DATA
        st.info("Reading data...")
        raw_data = worksheet.get_all_records()
        
        if not raw_data:
            st.warning("⚠️ The 'Employees' tab appears to be empty or headers are missing!")
        else:
            st.write("👇 Here is exactly what Python sees:")
            st.json(raw_data) # This prints the raw data
            
            df = pd.DataFrame(raw_data)
            st.write("👇 Interpreted Columns:")
            st.write(df.columns.tolist())
            
            # Check for 'Username' specifically
            if 'Username' in df.columns:
                st.success("✅ Column 'Username' found!")
            else:
                st.error(f"❌ CRITICAL: Could not find 'Username' column. Found these instead: {df.columns.tolist()}")

    except Exception as e:
        st.error("❌ CRASHED")
        st.code(traceback.format_exc()) # Prints the FULL error message

if st.button("Run Diagnostic"):
    run_test()