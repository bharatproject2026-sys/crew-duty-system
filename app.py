import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------- GOOGLE SHEETS CONNECT ----------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["GOOGLE_CREDENTIALS"], scope
)

client = gspread.authorize(creds)
sheet = client.open("CrewData").sheet1

# ---------- UI ----------
st.title("🚆 Crew Night Duty System (Final)")

uploaded_file = st.file_uploader("📤 Upload Excel File", type=["xlsx"])

# ---------- PROCESS ----------
if uploaded_file:
    try:
        # ---------- NEW FILE ----------
        new_df = pd.read_excel(uploaded_file)
        new_df.columns = new_df.columns.str.strip()
        new_df = new_df.iloc[:, [1, 2, 4, 7]]
        new_df.columns = ['Crew Id', 'Crew Name', 'Action', 'DateTime']

        new_df['DateTime'] = pd.to_datetime(new_df['DateTime'], dayfirst=True, errors='coerce')
        new_df = new_df.dropna(subset=['DateTime'])

        # ---------- OLD DATA ----------
        try:
            old_data = sheet.get_all_records()
            old_df = pd.DataFrame(old_data)

            if not old_df.empty:
                old_df['DateTime'] = pd.to_datetime(old_df['DateTime'], errors='coerce')
                old_df = old_df.dropna(subset=['DateTime'])
            else:
                old_df = pd.DataFrame(columns=new_df.columns)

        except:
            old_df = pd.DataFrame(columns=new_df.columns)

        # ---------- MERGE ----------
        df = pd.concat([old_df, new_df])
        df = df.drop_duplicates()

        # ---------- KEEP LAST 20 DAYS ----------
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        last_date = df['DateTime'].max()
        df = df[df['DateTime'] >= last_date - pd.Timedelta(days=20)]

        # ---------- SAVE BACK ----------
        sheet.clear()
        sheet.append_row(['Crew Id', 'Crew Name', 'Action', 'DateTime'])

        df['DateTime'] = df['DateTime'].astype(str)
        sheet.append_rows(df.values.tolist())

        st.success("✅ Data Saved (Last 20 Days)")

        # ---------- PROCESSING ----------
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        df = df.sort_values(['Crew Id', 'DateTime'])

        records = []

        for crew_id, group in df.groupby('Crew Id'):
            sign_on = None
            crew_name = None

            for _, row in group.iterrows():
                if row['Action'] == 'SIGNON':
                    sign_on = row['DateTime']
                    crew_name = row['Crew Name']

                elif row['Action'] == 'SIGNOFF' and sign_on is not None:
                    records.append({
                        'Crew Id': row['Crew Id'],
                        'Crew Name': crew_name,
                        'SignOn': sign_on,
                        'SignOff': row['DateTime']
                    })
                    sign_on = None

        duty_df = pd.DataFrame(records)

        # ---------- NIGHT LOGIC (00:00–05:59) ----------
        def is_night(sign_on, sign_off):
            night_start = sign_on.replace(hour=0, minute=0, second=0)
            night_end = sign_on.replace(hour=5, minute=59, second=59)
            return sign_on <= night_end and sign_off >= night_start

        duty_df['Night'] = duty_df.apply(
            lambda x: is_night(x['SignOn'], x['SignOff']), axis=1
        )

        # ---------- CORRECT NIGHT DATE ----------
        def get_night_date(sign_on, sign_off):
            if sign_off.date() > sign_on.date():
                return sign_off.date()
            else:
                return sign_on.date()

        duty_df['Date'] = duty_df.apply(
            lambda x: get_night_date(x['SignOn'], x['SignOff']),
            axis=1
        )

        # ---------- STREAK + VALIDATION ----------
        final_rows = []

        for crew_id, group in duty_df.groupby('Crew Id'):
            group = group.sort_values('Date').reset_index(drop=True)

            streak = []

            for i in range(len(group)):
                if group.loc[i, 'Night']:

                    if not streak:
                        streak.append(group.loc[i])

                    else:
                        prev = streak[-1]['Date']
                        curr = group.loc[i]['Date']

                        if (curr - prev).days == 1:
                            streak.append(group.loc[i])

                        else:
                            if len(streak) >= 3:
                                last_date = streak[-1]['Date']
                                next_duty = group[group['Date'] > last_date]

                                if next_duty.empty or next_duty.iloc[0]['Night']:
                                    for idx, row in enumerate(streak):
                                        day_num = idx + 1
                                        if 3 <= day_num <= 6:
                                            final_rows.append({
                                                'Crew Id': row['Crew Id'],
                                                'Crew Name': row['Crew Name'],
                                                'Day': f"{day_num}th day",
                                                'Date': row['Date']
                                            })

                            streak = [group.loc[i]]

                else:
                    streak = []

            # FINAL STREAK CHECK
            if len(streak) >= 3:
                last_date = streak[-1]['Date']
                next_duty = group[group['Date'] > last_date]

                if next_duty.empty or next_duty.iloc[0]['Night']:
                    for idx, row in enumerate(streak):
                        day_num = idx + 1
                        if 3 <= day_num <= 6:
                            final_rows.append({
                                'Crew Id': row['Crew Id'],
                                'Crew Name': row['Crew Name'],
                                'Day': f"{day_num}th day",
                                'Date': row['Date']
                            })

        final_df = pd.DataFrame(final_rows)

        # ---------- REPORT ----------
        if not final_df.empty:
            pivot_df = final_df.pivot_table(
                index=['Crew Id', 'Crew Name'],
                columns='Day',
                values='Date',
                aggfunc='first'
            ).reset_index()

            st.subheader("📊 Final Report (3–6 Day Streak)")
            st.dataframe(pivot_df)

            csv = pivot_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Report",
                data=csv,
                file_name="final_report.csv",
                mime="text/csv"
            )

        else:
            st.warning("⚠️ No valid continuous streak found")

        st.success("🎯 Processing Complete")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
