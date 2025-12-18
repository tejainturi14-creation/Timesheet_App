import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta, date

# --- CONFIGURATION ---
def get_db_connection():
    # 1. Create a dictionary from the secrets
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # 2. Auto-Repair the Private Key (Fixes Streamlit Cloud "Invalid JWT" error)
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets"]
    
    # 3. Authenticate
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1tNo2v2FWJUEj5cPg0MWk4UuqiCYNx9S63_-Ok3f54CM/edit"
    return client.open_by_url(SHEET_URL)

def load_data(worksheet_name):
    try:
        sheet = get_db_connection()
        worksheet = sheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def get_user_history(username):
    df = load_data("Submissions")
    if df.empty: return {}
    user_df = df[df['Username'] == username].copy()
    if user_df.empty: return {}
    
    user_df['Date'] = pd.to_datetime(user_df['Date']).dt.strftime('%Y-%m-%d')
    
    history = {}
    for _, row in user_df.iterrows():
        history[row['Date']] = {
            'hours': row['Hours'],
            'tasks': row['Tasks'],
            'vacation': row['Vacation']
        }
    return history

def update_weekly_summary(username, week_start, total_hours, total_vacation):
    """Updates the Weekly_Summaries tab."""
    try:
        sheet = get_db_connection()
        try:
            worksheet = sheet.worksheet("Weekly_Summaries")
        except:
            worksheet = sheet.add_worksheet("Weekly_Summaries", 1000, 4)
            worksheet.append_row(["Username", "Week_Start", "Total_Hours", "Total_Vacation"])
            
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        week_str = week_start.strftime('%Y-%m-%d')
        
        row_index = None
        if not df.empty:
            matches = df[(df['Username'] == username) & (df['Week_Start'] == week_str)]
            if not matches.empty:
                row_index = matches.index[0] + 2 
        
        if row_index:
            worksheet.update_cell(row_index, 3, total_hours)
            worksheet.update_cell(row_index, 4, total_vacation)
        else:
            worksheet.append_row([username, week_str, total_hours, total_vacation])
    except Exception as e:
        print(f"Summary Update Failed: {e}")

def save_clean_data(new_entries, username, week_start):
    sheet = get_db_connection()
    worksheet = sheet.worksheet("Submissions")
    
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    
    new_dates = [entry['date_logged'].strftime('%Y-%m-%d') for entry in new_entries]
    
    if not df.empty:
        condition = ~((df['Username'] == username) & (df['Date'].isin(new_dates)))
        df = df[condition]
    
    new_rows = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    week_total_hours = 0
    week_total_vacation = 0
    
    for entry in new_entries:
        week_total_hours += entry['hours_worked']
        week_total_vacation += entry['vacation_hours']
        new_rows.append({
            'Username': entry['username'],
            'Date': entry['date_logged'].strftime('%Y-%m-%d'),
            'Hours': entry['hours_worked'],
            'Tasks': entry['tasks'],
            'Vacation': entry['vacation_hours'],
            'Timestamp': timestamp
        })
    
    new_df = pd.DataFrame(new_rows)
    final_df = pd.concat([df, new_df], ignore_index=True)
    
    worksheet.clear()
    cols = ['Username', 'Date', 'Hours', 'Tasks', 'Vacation', 'Timestamp']
    final_data = [cols] + final_df[cols].values.tolist()
    worksheet.update(final_data)
    
    update_weekly_summary(username, week_start, week_total_hours, week_total_vacation)

# --- APP LOGIC ---
def main():
    st.set_page_config(page_title="Digital Minds Timesheet", layout="wide", page_icon="📝")

    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
    
    # --- LOGIN SCREEN ---
    if not st.session_state['logged_in']:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            # Try to show logo
            try:
                st.image("logo.png", use_container_width=True)
            except:
                st.header("Digital Minds Global Technologies")
            
            st.title("🔒 Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                try:
                    users_df = load_data("Employees")
                    if not users_df.empty:
                        user = users_df[(users_df['Username'].astype(str) == username) & 
                                        (users_df['Password'].astype(str) == password)]
                        if not user.empty:
                            st.session_state['logged_in'] = True
                            st.session_state['username'] = username
                            st.session_state['name'] = user.iloc[0]['Name']
                            st.rerun()
                        else: st.error("Invalid Username or Password")
                    else: st.error("Database empty.")
                except Exception as e: st.error(f"Login Error: {e}")

    # --- MAIN DASHBOARD ---
    else:
        # --- SIDEBAR BRANDING ---
        with st.sidebar:
            try:
                st.image("logo.png", use_container_width=True)
            except:
                pass
            
            st.markdown("### Digital Minds Global Technologies")
            st.write("---")
            st.write(f"👋 Hi, **{st.session_state['name']}**")
            
            if st.button("Logout"):
                st.session_state['logged_in'] = False
                st.rerun()
            
            st.write("---")
            st.markdown("**Contact HR**")
            st.caption("📧 hr@digitalmindsglobal.com")
            st.caption("📞 (281) 954-0065")
            st.info("⚠️ If there are any discrepancies, please contact HR immediately.")

        # --- ADMIN VIEW ---
        if st.session_state['username'] == 'admin':
            st.title("👑 HR Dashboard")
            summary_df = load_data("Weekly_Summaries")
            
            tab1, tab2 = st.tabs(["📊 Weekly Totals", "📝 Detailed Logs"])
            with tab1:
                if not summary_df.empty:
                    st.dataframe(summary_df, use_container_width=True)
                else: st.info("No summaries generated yet.")
            with tab2:
                df = load_data("Submissions")
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                else: st.info("No detailed records found.")

        # --- EMPLOYEE VIEW ---
        else:
            st.title("📝 Weekly Timesheet")
            
            try:
                holidays_df = load_data("Holidays")
                holidays_df['Date'] = pd.to_datetime(holidays_df['Date'])
                holiday_dates = holidays_df['Date'].dt.date.tolist()
            except: holiday_dates = []

            today = date.today()
            last_monday = today - timedelta(days=today.weekday())
            c1, c2 = st.columns(2)
            with c1: selected_date = st.date_input("Select Week", last_monday)
            
            week_start = selected_date - timedelta(days=selected_date.weekday())
            if selected_date != week_start: st.caption(f"ℹ️ Snapped to Monday: {week_start}")

            user_history = get_user_history(st.session_state['username'])
            current_week_total = 0
            for i in range(5):
                d_str = (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
                if d_str in user_history:
                    current_week_total += float(user_history[d_str]['hours'])
            
            st.metric("Total Hours This Week", f"{current_week_total} hrs")
            st.divider()

            with st.form("entry_form"):
                submission_data = []
                current_real_monday = today - timedelta(days=today.weekday())
                last_week_monday = current_real_monday - timedelta(days=7)
                is_future_week = week_start > current_real_monday
                
                if is_future_week:
                    st.warning("🚫 This week is in the future. You cannot submit timesheets yet.")

                for i in range(5):
                    current_date = week_start + timedelta(days=i)
                    date_obj = current_date
                    date_str = date_obj.strftime("%Y-%m-%d")
                    day_label = date_obj.strftime("%A, %b %d")
                    
                    st.markdown(f"##### {day_label}")

                    default_h, default_t, default_v = 0.0, "", 0.0
                    status_msg = ""
                    
                    if date_str in user_history:
                        prev = user_history[date_str]
                        default_h, default_t, default_v = float(prev['hours']), prev['tasks'], float(prev['vacation'])
                        status_msg = "✅ Submitted"

                    if is_future_week:
                        st.info("Locked (Future Date)")
                    elif any([h == date_obj for h in holiday_dates]):
                        st.info(f"🏖️ Holiday (8h Vacation) - Read Only")
                        submission_data.append({
                            "username": st.session_state['username'], "date_logged": date_obj,
                            "hours_worked": 0.0, "tasks": "Public Holiday", "vacation_hours": 8.0
                        })
                    elif week_start < last_week_monday:
                        st.warning(f"🔒 Locked (Past Grace Period) | Hours: {default_h}")
                    else:
                        if status_msg: st.caption(status_msg)
                        c1, c2, c3 = st.columns([1, 2, 1])
                        hours = c1.number_input("Hours", 0.0, 24.0, value=default_h, step=0.5, key=f"h_{date_str}")
                        tasks = c2.text_input("Tasks", value=default_t, key=f"t_{date_str}")
                        vacation = c3.number_input("Vacation", 0.0, 24.0, value=default_v, step=0.5, key=f"v_{date_str}")
                        
                        submission_data.append({
                            "username": st.session_state['username'], "date_logged": date_obj,
                            "hours_worked": hours, "tasks": tasks, "vacation_hours": vacation
                        })
                    st.divider()

                if is_future_week:
                    st.form_submit_button("Submit / Update Timesheet", disabled=True)
                else:
                    if st.form_submit_button("Submit / Update Timesheet"):
                        with st.spinner("Updating Database..."):
                            save_clean_data(submission_data, st.session_state['username'], week_start)
                        st.success("✅ Saved! Database updated.")
                        st.rerun()

if __name__ == "__main__":
    main()
