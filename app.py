if len(streak) >= 3:
    last_date = streak[-1]['Date']
    next_duty = group[group['Date'] > last_date]

    if next_duty.empty:
        valid_crews.append(crew_id)

        for idx, row in enumerate(streak):
            day_num = idx + 1
            if 3 <= day_num <= 6:
                final_rows.append({
                    'Crew Id': row['Crew Id'],
                    'Crew Name': row['Crew Name'],
                    'Day': f"{day_num}th day",
                    'Date': row['Date']
                })

    else:
        next_row = next_duty.iloc[0]

        if next_row['Night'] == True:
            valid_crews.append(crew_id)

            for idx, row in enumerate(streak):
                day_num = idx + 1
                if 3 <= day_num <= 6:
                    final_rows.append({
                        'Crew Id': row['Crew Id'],
                        'Crew Name': row['Crew Name'],
                        'Day': f"{day_num}th day",
                        'Date': row['Date']
                    })
