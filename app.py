# ---------- LOAD EXCEL ----------
new_df = pd.read_excel(uploaded_file)

new_df.columns = new_df.columns.str.strip()
new_df = new_df.iloc[:, [1, 2, 4, 7]]
new_df.columns = ['Crew Id', 'Crew Name', 'Action', 'DateTime']

new_df['DateTime'] = pd.to_datetime(new_df['DateTime'], dayfirst=True, errors='coerce')
new_df = new_df.dropna(subset=['DateTime'])

# ---------- LOAD OLD DATA FROM GOOGLE SHEET ----------
try:
    old_data = sheet.get_all_records()
    old_df = pd.DataFrame(old_data)

    if not old_df.empty:
        old_df['DateTime'] = pd.to_datetime(old_df['DateTime'])
    else:
        old_df = pd.DataFrame(columns=new_df.columns)

except:
    old_df = pd.DataFrame(columns=new_df.columns)

# ---------- MERGE OLD + NEW ----------
df = pd.concat([old_df, new_df])

# Remove duplicates
df = df.drop_duplicates()

# ---------- KEEP LAST 20 DAYS ----------
df['DateTime'] = pd.to_datetime(df['DateTime'])

last_date = df['DateTime'].max()
df = df[df['DateTime'] >= last_date - pd.Timedelta(days=20)]

# ---------- SAVE BACK TO GOOGLE SHEET ----------
sheet.clear()

# Add header
sheet.append_row(['Crew Id', 'Crew Name', 'Action', 'DateTime'])

# Convert to string
df['DateTime'] = df['DateTime'].astype(str)

sheet.append_rows(df.values.tolist())

st.success("✅ Data Updated (Last 20 Days Stored)")

# ---------- CONTINUE PROCESS ----------
df['DateTime'] = pd.to_datetime(df['DateTime'])
