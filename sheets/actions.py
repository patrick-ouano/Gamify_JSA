import re 
import gspread 
import random
import math
import config
from datetime import datetime

master_cache = [""]
# --- HEADER CONFIGURATION ---
MASTER_HEADERS = ['Name', 'Email', 'Year', 'Discord_ID', 'Total_XP', 'Rank']
AUDIT_HEADERS = ['Message_ID','Timestamp','Officer_ID','Recipient_ID','XP_Amount','Reason']
SCHEDULED_QUEST_SHEET = "Scheduled_Quests"
SCHEDULED_QUEST_HEADERS = ["Date", "Type", "Quest_Name"]

def calculate_rank(xp):
    # Calculates the rank name based on XP thresholds.
    sorted_thresholds = sorted(config.RANK_THRESHOLDS.keys(), reverse=True)
    for threshold in sorted_thresholds:
        if xp >= threshold:
            return config.RANK_THRESHOLDS[threshold]
    return "Newcomer"

def get_next_rank_info(xp):
    # Returns the next rank threshold and name, or None if at max rank
    sorted_thresholds = sorted(config.RANK_THRESHOLDS.keys())
    for threshold in sorted_thresholds:
        if xp < threshold:
            return threshold, config.RANK_THRESHOLDS[threshold]
    return None, None  # Already at max rank

def generate_progress_bar(current_xp, current_threshold, next_threshold):
    # Generates a 10-character ASCII progress bar
    if next_threshold is None:
        # Max rank - show full bar
        return "[▰▰▰▰▰▰▰▰▰▰]"
    
    progress_range = next_threshold - current_threshold
    progress_made = current_xp - current_threshold
    progress_percentage = progress_made / progress_range if progress_range > 0 else 0
    
    filled = int(progress_percentage * 10)
    filled = min(filled, 10)  # Cap at 10
    empty = 10 - filled
    
    bar = "[" + "▰" * filled + "▱" * empty + "]"
    return bar

def get_id_from_url(url):
    # Extracts the long alphanumeric ID from a Google Sheet URL 
    try:
        # Regex to find the ID between /d/ and / 
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match: 
            return match.group(1)
        else:
            return None
    except:
        return None
    
def find_email_column(records):
    # Scans the first row of data to find which key looks like an email 
    if not records: 
        return None
    
    # Gets the keys (headers) from the first row
    headers = records[0].keys()

    for header in headers:
        clean_header = header.lower().strip()
        # Looks for email, uf email, email address
        if "email" in clean_header:
            return header
    return None

def find_name_column(records):
    # Scans the first row of data to find which key looks like a name
    if not records:
        return None
    
    # Gets the keys (headers) from the first row
    headers = records[0].keys()

    for header in headers:
        clean_header = header.lower().strip()
        # Looks for name, full name, first name, etc. but excludes username
        if "name" in clean_header and "user" not in clean_header:
            return header
    return None

def find_year_column(records):
    # Scans headers for a year column (Year, Class Year, Graduation Year, etc.)
    if not records:
        return None

    headers = records[0].keys()
    for header in headers:
        clean_header = header.lower().strip()
        if "year" in clean_header:
            return header
    return None

def is_event_processed(log_sheet, event_id):
    # Checks if the event_id already exists in Column A of Attendance_Logs
    try:
        # Get all IDs from the first column
        processed_ids = log_sheet.col_values(1) 
        return event_id in processed_ids
    except:
        return False
    
def log_event_completion(log_sheet, event_id, xp_amount):
    # Writes the receipt to Attendance_Logs so we don't process it again 
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_sheet.append_row([event_id, timestamp, xp_amount])

def is_quest_processed(audit_sheet, message_id):
    # Checks if the message_id already exists in Column A of Audit_Logs
    # Prevents double-dipping when multiple officers react to the same submission
    try:
        processed_ids = audit_sheet.col_values(1)
        return str(message_id) in processed_ids
    except:
        return False
def is_manual_xp_given(audit_sheet,recipient_id, xp,reason,timestamp):
    try:
        records = audit_sheet.get_all_records(expected_headers=AUDIT_HEADERS)
        for i, row in enumerate(records):
            table_recipient_id = str(row.get("Recipient_ID", 0))
            table_xp = int(row.get("XP_Amount",0))
            table_reason = str(row.get("Reason",""))
            table_timestamp = str(row.get("Timestamp","0000-00-00"))[:10]
            if(table_recipient_id  == recipient_id and table_xp == xp and table_reason == reason and table_timestamp == timestamp):
                return True
        return False


    except:
        return False




def log_quest_approval(audit_sheet, message_id, officer_id, recipient_id, xp_amount, reason):
    # Logs the quest approval to Audit_Logs for transparency and tracking
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    audit_sheet.append_row([
        str(message_id),
        timestamp,
        str(officer_id),
        str(recipient_id),
        xp_amount,
        reason
    ])

def process_event_data(client, master_sheet_id, event_sheet_url, xp_amount):
    # Opens Event Sheet -> Opens Master Roster -> 
    # Awards XP to exising members -> Auto-enrolls new members

    # 1. Gets the Event ID
    event_id = get_id_from_url(event_sheet_url)
    if not event_id:
        return "❌Error: Could not parse Sheet ID From that URL."
    
    # 2. Opens the Master Roster & Attendance Log
    try: 
        master_wb = client.open_by_key(master_sheet_id)
        master_sheet = master_wb.worksheet("Master_Roster")
        log_sheet = master_wb.worksheet("Attendance_Logs")
    except Exception as e: 
        return f"❌Error opening Master Roster: {e}"
    
    # 3. Checks if Event Sheet has been processed
    if is_event_processed(log_sheet, event_id):
        return "⚠️ STOP: This event sheet has already been processed! Check 'Attendance_Logs' for details."

    # 4. Opens the Event Sheet
    try: 
        event_sheet = client.open_by_key(event_id).sheet1
        event_records = event_sheet.get_all_records()
    except Exception as e: 
        return f"❌Error opening Event Sheet: {e}"
    
    # 2. Opens the Master Roster
    try: 
        master_wb = client.open_by_key(master_sheet_id)
        master_sheet = master_wb.worksheet("Master_Roster")
        master_records = master_sheet.get_all_records(expected_headers=MASTER_HEADERS)
    except Exception as e: 
        return f"❌Error opening Master Roster: {e}"

    # 3. Finds the Email Column in the Event Sheet
    email_col_name = find_email_column(event_records)
    if not email_col_name: 
        return "❌Error: Could not find a column name 'Email' in the event sheet. "
    
    # 4. Finds the Name Column in the Event Sheet
    name_col_name = find_name_column(event_records)
    year_col_name = find_year_column(event_records)
    
        # 6. Creates a lookup directory for Master Roster with current XP
    # Format: {'email@ufl.edu': {'row_num': int, 'current_xp': int}}
    master_records = master_sheet.get_all_records()
    master_map = {}
    for i, row in enumerate(master_records):
        email = str(row.get("Email", "")).strip().lower()
        if email:
            try:
                current_xp = int(row.get("Total_XP", 0))
            except:
                current_xp = 0
            discord_id = str(row.get("Discord_ID",0))
            master_map[email] = {
                'row_num': i + 2,  # Row number (1-indexed, row 1 is header)
                'current_xp': current_xp,
                'discord_id': discord_id,
                'year': row.get("Year", "")
            }

    # 7. Collect all updates for batch processing
    batch_updates = []  # List of {'range': 'E5:F5', 'values': [[xp, rank]]}
    new_members = []    # List of [name, email, year, discord_id, xp, rank]
    
    new_members_count = 0
    existing_members_count = 0

    # Process Attendees - collect updates, don't execute yet
    for row in event_records:
        attendee_email = str(row[email_col_name]).strip().lower()
        attendee_name = row.get(name_col_name, "Unknown") if name_col_name else "Unknown"
        event_year = str(row.get(year_col_name, "")).strip() if year_col_name else ""

        # If email is empty, skip
        if not attendee_email:
            continue

        if attendee_email in master_map:
            # Scenario A: The Regular (Update XP)
            member_info = master_map[attendee_email]
            row_num = member_info['row_num']
            current_xp = member_info['current_xp']
            discord_id = member_info['discord_id']
            attendee_year = event_year if event_year else member_info.get('year', "")
            
            new_xp = current_xp + xp_amount
            new_rank = calculate_rank(new_xp)

            # Add to batch update list (column A is 1, F is 6)
            batch_updates.append({
                'range': f'A{row_num}:F{row_num}',
                'values': [[attendee_name,attendee_email,attendee_year,discord_id,new_xp, new_rank]]
            })
            
            existing_members_count += 1
            print(f"Updated {attendee_email}: {current_xp} -> {new_xp}")

        else:
            # Scenario B: The Newcomer (Auto-Enroll)
            new_row = [attendee_name, attendee_email, event_year, "", xp_amount, "Newcomer"]
            new_members.append(new_row)
            new_members_count += 1
            print(f"Added {attendee_email}!")

    # 8. Execute batch operations
    if batch_updates:
        master_sheet.batch_update(batch_updates)
        print(f"Batch updated {len(batch_updates)} existing members")
    
    if new_members:
        master_sheet.append_rows(new_members)
        print(f"Batch added {len(new_members)} new members")

    # 9. Log the transaction so it doesn't happen again
    log_event_completion(log_sheet, event_id, xp_amount)

    return f"✅  Success! Processed Sheet ID {event_id[:5]}... Updated {existing_members_count} and added {new_members_count}."
def get_join(client, master_sheet_id, email, discord_id, display_name=""):
    sheet = client.open_by_key(master_sheet_id)
    master = sheet.worksheet("Master_Roster")
    email = email.strip().lower()
    discord_id = str(discord_id).strip()
    display_name = str(display_name or "").strip()

    records = master.get_all_records()
    for i, row in enumerate(records):

        row_discord_id = str(row.get("Discord_ID", "")).strip()
        
        # Case 1: Email and Discord account are already linked.
        if row_discord_id == discord_id:
            update_master_cache(client, master_sheet_id)
            return "✨ **You're already in!** This Discord account is already registered in our system."

        if row.get("Email", "").strip().lower() == email:
            
            # Case 2: Email is in Master Roster but is not linked to a Discord account.
            if row_discord_id == "":
                row_number = i + 2
                master.update_cell(row_number, 4, discord_id)
                # Fill blank Name from Discord if the roster row has no name yet
                if display_name and not str(row.get("Name", "")).strip():
                    master.update_cell(row_number, 1, display_name)
                update_master_cache(client, master_sheet_id)
                return "🔗 **Account Linked!** We've successfully connected your Discord to your JSA records. Welcome!"
            
            # Case 3: Email is linked to another Discord account.
            return "⚠️ **Oops!** That email is already connected to a different Discord account."

    # Case 4: Email is not in Master Roster. 
    new_row = [
        display_name, # Name (from Discord display name)
        email, # Email
        "", # Year
        discord_id, # Discord ID
        0, # Total XP
        "Newcomer" # Rank
    ]
    master.append_row(new_row)
    update_master_cache(client, master_sheet_id)
    return "🎉 **Welcome aboard!** You've been successfully registered in the JSA XP system. Time to start earning! 🚀"

def get_leaderboard(client, master_sheet_id, top=10, mode="regular"):
    sheet = client.open_by_key(master_sheet_id)
    #master = sheet.worksheet("Master_Roster")
    #records = master_cache.get_all_records()
    records = master_cache

    leaderboard_data = []
    for row in records:
        name = str(row.get("Name", "Unknown")).strip()
        xp_val = row.get("Total_XP", 0)
        rank_name = str(row.get("Rank", "Unknown")).strip()
        is_board = str(row.get("Board_Member", "N")).strip().upper() == "Y"

        # Filtering Logic
        if mode == "regular" and is_board:
            continue
        if mode == "board" and not is_board:
            continue

        
        try:
            xp = int(xp_val)
        except:
            xp = 0
        leaderboard_data.append((name, xp, rank_name,is_board))

    leaderboard_data.sort(key=lambda x: x[1], reverse=True)
    return leaderboard_data

def _find_cached_member(discord_id):
    records = master_cache
    if not isinstance(records, list):
        return None
    for row in records:
        if not isinstance(row, dict):
            continue
        if str(row.get("Discord_ID", "")).strip() == discord_id:
            return row
    return None

def get_xp(client, master_sheet_id, discord_id):
    discord_id = str(discord_id).strip()
    row = _find_cached_member(discord_id)
    if row is None:
        update_master_cache(client, master_sheet_id)
        row = _find_cached_member(discord_id)
    if row is None:
        return "Your Discord account was not found in JSA's XP system.\nPlease register using the join command (Ex: !join email@ufl.edu)."

    try:
        xp = int(row.get("Total_XP", 0))
    except:
        xp = 0

    rank = row.get("Rank", "Unknown")

    # Calculate progress to next rank
    sorted_thresholds = sorted(config.RANK_THRESHOLDS.keys())
    current_threshold = 0
    for threshold in sorted_thresholds:
        if xp >= threshold:
            current_threshold = threshold
        else:
            break

    next_threshold, next_rank_name = get_next_rank_info(xp)

    if next_threshold is None:
        # At max rank
        progress_bar = generate_progress_bar(xp, current_threshold, None)
        return (
            f"Your rank is **{rank}** and you currently have **{xp} XP**!\n"
            f"Progress: {progress_bar}\n"
            f"🏆 **You've reached the maximum rank!**"
        )

    xp_needed = next_threshold - xp
    progress_bar = generate_progress_bar(xp, current_threshold, next_threshold)
    return (
        f"Your rank is **{rank}** and you currently have **{xp} XP**!\n"
        f"Progress to **{next_rank_name}**: {progress_bar}\n"
        f"**{xp_needed} XP** needed to rank up!"
    )
def update_master_cache(client,master_sheet_id):
    try:
        sheet = client.open_by_key(master_sheet_id)
        global master_cache
        temp_cache = sheet.worksheet("Master_Roster")
        master_cache = temp_cache.get_all_records(expected_headers=MASTER_HEADERS)
    except Exception as e:
        return f"Error accessing sheet {e}"

def award_quest_xp(client, master_sheet_id, discord_id, xp_amount, officer_id=None, message_id=None, reason=None):
    # Finds a user by Discord ID and adds XP to Master Roster
    # Optional audit logging when officer_id, message_id, and reason are provided
    try: 
        sheet = client.open_by_key(master_sheet_id)
        master = sheet.worksheet("Master_Roster")
        records = master.get_all_records(expected_headers=MASTER_HEADERS)
        global master_cache
        master_cache = records
        # If message_id is provided, check for duplicate approval (prevents double-dipping)
        if message_id is not None:
            try:
                audit_sheet = sheet.worksheet("Audit_Logs")
                if is_quest_processed(audit_sheet, message_id):
                    return "⚠️ Already Approved: This submission has already been verified by an officer."
            except Exception as e:
                # If Audit_Logs doesn't exist, continue without duplicate check
                print(f"Warning: Could not access Audit_Logs: {e}")
                audit_sheet = None
        else:
            audit_sheet = None
            
    except Exception as e:
        return f"❌ Error accessing Sheet: {e}"
    
    for i, row in enumerate(records):
        # Finds the row matching the user's Discord ID
        if str(row.get("Discord_ID", "")).strip() == str(discord_id):
            row_num = i + 2 # Accounts for header and 1-indexing
            
            # Calculates new XP
            try:
                current_xp = int(row.get("Total_XP", 0))
            except:
                current_xp = 0
            
            new_xp = current_xp + xp_amount
            new_rank = calculate_rank(new_xp)

            # Updates XP and Rank
            master.update_cell(row_num, 5, new_xp)
            master.update_cell(row_num, 6, new_rank)
            
            # Log to Audit_Logs if audit parameters are provided
            if audit_sheet is not None and message_id is not None and officer_id is not None:
                log_quest_approval(audit_sheet, message_id, officer_id, discord_id, xp_amount, reason or "Manual XP Award")

            return f"Added {xp_amount} XP! New Total: {new_xp} ({new_rank})"

    return "❌ User not found in roster. Please use /join first."

def get_random_quest(client, master_sheet_id, sheet_name):
    # Picks a random quest from the specified sheet and avoids back-to-back repeats
    try:
        spreadsheet = client.open_by_key(master_sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        headers = worksheet.row_values(1)
        
        # Ensure the 'Last_Used' column exists in your sheet headers
        if "Last_Used" not in headers:
            return None
        last_used_col_idx = headers.index("Last_Used") + 1

        if not records:
            return None

        # Sort quests by Last_Used timestamp (most recent first)
        # We add the original row index (i+2) to each record for updating later
        indexed_records = []
        for i, r in enumerate(records):
            indexed_records.append({"data": r, "row_num": i + 2})

        indexed_records.sort(key=lambda x: str(x["data"].get("Last_Used", "")), reverse=True)
        quest_cooldown = config.DAILY_QUEST_COOLDOWN
        if(sheet_name == "Weekly_Quests"):
            quest_cooldown = config.WEEKLY_QUEST_COOLDOWN
        # Exclude the last 7(daily quest cooldown) recently used quests
        pool = indexed_records[quest_cooldown:] if len(indexed_records) > 1 else indexed_records
        #here we're going to create weights, the formula we use is going to be ln(i+1)^2
        #this is so that quests that haven't shown up in a long time have a drastically higher chance of showing up
        #basically the higher the distribution constant is, the less skewed the weights
        distributionConstant = 7
        weights = []
        for i in range(len(pool)):
            weight = math.log(i+distributionConstant)**2
            #If the weight was in the last 25(dailies)/7(weeklies) the chance of pulling it is cut into thirds
            if(i<(len(pool)/2)):
                weight /= 4
            weights.append(weight)
        summedweights = sum(weights)
        #here we normalize the weights so it's easy to understand for testing but this could be removed
        for i in range(len(pool)):
            weights[i] = (weights[i]/summedweights)
        selection = random.choices(range(len(pool)),weights=weights,k=1)[0]
        selection = (pool[selection])
        # Update the timestamp in the sheet
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.update_cell(selection["row_num"], last_used_col_idx, now_str)

        return selection["data"]
    except Exception as e:
        print(f"Error fetching quest from {sheet_name}: {e}")
        return None

def _find_quest_row(client, master_sheet_id, sheet_name, quest_name):
    # Looks up a quest by name without updating Last_Used
    try:
        spreadsheet = client.open_by_key(master_sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        headers = worksheet.row_values(1)

        if "Last_Used" not in headers:
            return None
        last_used_col_idx = headers.index("Last_Used") + 1

        for i, row in enumerate(records):
            if str(row.get("Quest Name", "")).strip().lower() == quest_name.strip().lower():
                return {
                    "data": row,
                    "row_num": i + 2,
                    "worksheet": worksheet,
                    "last_used_col_idx": last_used_col_idx,
                }
        return None
    except Exception as e:
        print(f"Error finding quest in {sheet_name}: {e}")
        return None

def find_quest(client, master_sheet_id, sheet_name, quest_name):
    # Returns the quest row if it exists, without marking it used
    found = _find_quest_row(client, master_sheet_id, sheet_name, quest_name)
    return found["data"] if found else None

def get_specific_quest(client, master_sheet_id, sheet_name, quest_name):
    # Fetches a specific quest by its name from the sheet and marks it used
    found = _find_quest_row(client, master_sheet_id, sheet_name, quest_name)
    if not found:
        return None
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    found["worksheet"].update_cell(found["row_num"], found["last_used_col_idx"], now_str)
    return found["data"]

def _normalize_date(value):
    # Sheets may return dates as strings, serials, or datetime-like objects
    if value is None:
        return ""
    if hasattr(value, "date") and callable(value.date):
        try:
            return value.date().isoformat()
        except Exception:
            pass
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return s

def _get_scheduled_worksheet(client, master_sheet_id):
    spreadsheet = client.open_by_key(master_sheet_id)
    titles = [ws.title for ws in spreadsheet.worksheets()]
    if SCHEDULED_QUEST_SHEET not in titles:
        worksheet = spreadsheet.add_worksheet(title=SCHEDULED_QUEST_SHEET, rows=100, cols=3)
        worksheet.append_row(SCHEDULED_QUEST_HEADERS)
        return worksheet

    worksheet = spreadsheet.worksheet(SCHEDULED_QUEST_SHEET)
    headers = worksheet.row_values(1)
    if not headers:
        worksheet.append_row(SCHEDULED_QUEST_HEADERS)
    return worksheet

def set_scheduled_quest(client, master_sheet_id, date_str, sheet_name, quest_name):
    # Saves a quest for a date/type, replacing any existing entry for that slot
    try:
        worksheet = _get_scheduled_worksheet(client, master_sheet_id)
        records = worksheet.get_all_records()
        headers = worksheet.row_values(1)
        if "Quest_Name" not in headers:
            return None
        quest_name_col = headers.index("Quest_Name") + 1

        for i, row in enumerate(records):
            if _normalize_date(row.get("Date", "")) == date_str and str(row.get("Type", "")).strip() == sheet_name:
                worksheet.update_cell(i + 2, quest_name_col, quest_name)
                return "replaced"
        worksheet.append_row([date_str, sheet_name, quest_name], value_input_option="RAW")
        return "created"
    except Exception as e:
        print(f"Error saving scheduled quest: {e}")
        return None

def get_scheduled_quest(client, master_sheet_id, date_str, sheet_name):
    # Returns the queued quest for a date/type, or None
    try:
        worksheet = _get_scheduled_worksheet(client, master_sheet_id)
        records = worksheet.get_all_records()
        for row in records:
            if _normalize_date(row.get("Date", "")) == date_str and str(row.get("Type", "")).strip() == sheet_name:
                return row
        return None
    except Exception as e:
        print(f"Error reading scheduled quest: {e}")
        return None

def clear_scheduled_quest(client, master_sheet_id, date_str, sheet_name):
    # Removes the queued quest for a date/type after it posts
    try:
        worksheet = _get_scheduled_worksheet(client, master_sheet_id)
        records = worksheet.get_all_records()
        for i, row in enumerate(records):
            if _normalize_date(row.get("Date", "")) == date_str and str(row.get("Type", "")).strip() == sheet_name:
                worksheet.delete_rows(i + 2)
                return True
        return False
    except Exception as e:
        print(f"Error clearing scheduled quest: {e}")
        return False

def list_scheduled_quests(client, master_sheet_id, today_str):
    # Returns upcoming scheduled quests (today or later)
    try:
        worksheet = _get_scheduled_worksheet(client, master_sheet_id)
        records = worksheet.get_all_records()
        upcoming = []
        for row in records:
            row_date = _normalize_date(row.get("Date", ""))
            if row_date and row_date >= today_str:
                upcoming.append({
                    "Date": row_date,
                    "Type": row.get("Type", ""),
                    "Quest_Name": row.get("Quest_Name", ""),
                })
        upcoming.sort(key=lambda r: (_normalize_date(r.get("Date", "")), str(r.get("Type", ""))))
        return upcoming
    except Exception as e:
        print(f"Error listing scheduled quests: {e}")
        return []

# wordle_claim_exists (function to return if the wordle is already claimed 
def wordle_claim_exists(client, master_sheet_id, puzzle, discord_id):
    sheet = client.open_by_key(master_sheet_id)
    wordle_sheet = sheet.worksheet("Wordle_Claims")

    # converts the puzzle and discord_id to strings
    puzzle = str(puzzle).strip()
    discord_id = str(discord_id).strip()

    # loop through each row and see if the puzzle has already been claimed by a corresponding discord id 
    rows = wordle_sheet.get_all_values()
    for row in rows[1:]:
        if len(row) >= 2 and row[0].strip() == puzzle and row[1].strip() == discord_id:
            return True
    return False

# log the wordle claim 
def log_wordle_claim(client, master_sheet_id, puzzle, discord_id):
    sheet = client.open_by_key(master_sheet_id)
    wordle_sheet = sheet.worksheet("Wordle_Claims")

    # logs the wordle claim 
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    wordle_sheet.append_row([str(puzzle), str(discord_id), timestamp], value_input_option = "RAW")
#logs manual xp to audit log
def grant_manual_xp(client,master_sheet_id,recipient_id,xp_amount,reason,officer_id):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        sheet = client.open_by_key(master_sheet_id)

        master = sheet.worksheet("Master_Roster")
        records = master.get_all_records(expected_headers=MASTER_HEADERS)
        global master_cache
        master_cache = records
        try:
            audit_sheet = sheet.worksheet("Audit_Logs")

            if not(is_manual_xp_given(audit_sheet,recipient_id,xp_amount,reason,timestamp[:10])):
                log_quest_approval(audit_sheet,-1,officer_id,recipient_id,xp_amount,reason)
            else:
                return f"⚠️ Already Approved: XP has already been granted to this user for {reason}."
        except Exception as e:
            print(f"Warning: Could not access Audit_logs: {e}")
            audit_sheet = None

    except Exception as e:
        return f"❌ Error accessing Sheet: {e}"
    for i, row in enumerate(records):

        if str(row.get("Discord_ID","")).strip() == str(recipient_id):
            row_num = i+2
            try:
                current_xp = int(row.get("Total_XP",0))
            except:
                current_xp = 0

            new_xp = current_xp + xp_amount
            new_rank = calculate_rank(new_xp)

            master.update_cell(row_num,5,new_xp)
            master.update_cell(row_num,6,new_rank)
            return f"Added {xp_amount} XP to <@{recipient_id}> for {reason}."



# compares the two sheets and checks if the member is a board member, if so, add y/n to board member column
def check_if_board_member(client, master_sheet_id):
    sheet = client.open_by_key(master_sheet_id)
    master = sheet.worksheet("Master_Roster")
    board_members = sheet.worksheet("Board_Roster")

    # 1. Retrieve all data from master sheet and board members sheet
    master_records = master.get_all_records()
    board_records = board_members.get_all_records()

    # 2. Build a lookup set of board member emails
    board_emails = {
        row["Email"].strip().lower()
        for row in board_records
        if row.get("Email")
    }

    # 3. Find the column inded for board_member
    headers = master.row_values(1)
    board_col = headers.index("Board_Member") + 1
    email_col = headers.index("Email") + 1

    updates = []

    # 4. Decide Y/N for each row
    for i, row in enumerate(master_records, start=2):
        email = row.get("Email", "").strip().lower()

        is_board = "Y" if email in board_emails else "N"

        # need to ascii align to get capital letters (get values like D1, D2...DX)
        updates.append({
            "range": f"{chr(64 + board_col)}{i}",
            "values": [[is_board]]
        })

    # 5. Batch update for efficiency
    master.batch_update(updates)
