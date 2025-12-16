import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. We removed the 'drive' scope. We only ask for 'spreadsheets' now.
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets"]

try:
    print("Attempting to connect using ONLY Sheets API...")
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_key.json", scope)
    client = gspread.authorize(creds)
    
    # 2. PASTE YOUR FULL URL BELOW inside the quotes
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1tNo2v2FWJUEj5cPg0MWk4UuqiCYNx9S63_-Ok3f54CM/edit?gid=1864674223#gid=1864674223"
    
    # 3. Open by URL (Skips the Drive API search)
    sheet = client.open_by_url(SHEET_URL)
    
    print("✅ SUCCESS! Access granted to:", sheet.title)
    print("We successfully bypassed the Drive API error.")

except Exception as e:
    print("\n❌ FAILED")
    print("Error:", e)