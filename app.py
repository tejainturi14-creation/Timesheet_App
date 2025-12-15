import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# We use Streamlit Secrets for security (explained in Step 4)
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_db_connection():
    # Load credentials from Streamlit Secrets
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    # Open the Google Sheet
    sheet = client.open("Timesheet_DB")
    return sheet

def load_data(worksheet_name):
    sheet = get_db_connection()
    worksheet = sheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def submit_timesheet(data_list):
    sheet = get_db_connection()
    worksheet = sheet.worksheet("Submissions")
    
    # Append each row to the Google Sheet
    for row in data_list:
        # Convert row dict to list in specific order
        row_values = [
            row['username'], 
            str(row['date_logged']), 
            row['hours_worked'], 
            row['tasks'], 
            row['vacation_hours']
        ]
        worksheet.append_row(row_values)

# --- APP LOGIC ---
def main():
    st.set_page_config(page_title="Cloud Timesheet Portal")

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    # --- LOGIN SCREEN ---
    if not st.session_state['logged_in']:
        st.title("🔒 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            try:
                users_df = load_data("Employees")
                # Ensure columns exist and match
                user = users_df[(users_df['Username'].astype(str) == username) & 
                                (users_df['Password'].astype(str) == password)]
                
                if not user.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
            except Exception as e:
                st.error(f"Database Error: {e}")

    # --- MAIN DASHBOARD ---
    else:
        st.sidebar.write(f"User: **{st.session_state['username']}**")
        if st.sidebar.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()

        st.header("Weekly Timesheet Submission")
        
        # Load Holidays
        try:
            holidays_df = load_data("Holidays")
            # Standardize date format for comparison
            holidays_df['Date'] = pd.to_datetime(holidays_df['Date'])
            holiday_dates = holidays_df['Date'].dt.date.tolist()
        except:
            holiday_dates = [] # Fallback if sheet is empty

        week_start = st.date_input("Week Start Date", datetime.today())
        
        with st.form("entry_form"):
            submission_data = []
            for i in range(5):
                current_date = week_start + timedelta(days=i)
                date_obj = current_date.date() if isinstance(current_date, datetime) else current_date
                day_label = current_date.strftime("%A %Y-%m-%d")
                
                st.markdown(f"**{day_label}**")
                
                # Holiday Check (Comparing date objects)
                is_holiday = False
                for h_date in holiday_dates:
                    # Handle both timestamp and date objects safely
                    check_date = h_date.date() if hasattr(h_date, 'date') else h_date
                    if check_date == date_obj:
                        is_holiday = True
                        break

                if is_holiday:
                    st.info(f"🏖️ Holiday: Auto-filling Vacation")
                    hours = 0.0
                    tasks = "Public Holiday"
                    vacation = 8.0
                else:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    hours = col1.number_input("Hours", 0.0, 24.0, key=f"h_{i}")
                    tasks = col2.text_input("Tasks", key=f"t_{i}")
                    vacation = col3.number_input("Vacation", 0.0, 24.0, key=f"v_{i}")

                submission_data.append({
                    "username": st.session_state['username'],
                    "date_logged": date_obj,
                    "hours_worked": hours,
                    "tasks": tasks,
                    "vacation_hours": vacation
                })
                st.divider()

            if st.form_submit_button("Submit"):
                with st.spinner("Saving to Google Cloud..."):
                    submit_timesheet(submission_data)
                st.success("Submitted successfully!")

if __name__ == "__main__":
    main()