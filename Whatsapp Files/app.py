from flask import Flask, render_template, request, jsonify, send_file, make_response
import os
import sqlite3
import tempfile
import shutil
from datetime import datetime
import pyzipper
import subprocess
import traceback
import io
import json
import zipfile

app = Flask(__name__)

MEDIA_FOLDER = os.path.join('static', 'media')
os.makedirs(MEDIA_FOLDER, exist_ok=True)

MEDIA_EXTENSIONS = [
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
    ".mp4", ".webm", ".ogg", ".3gp", ".mov", ".avi", ".mkv",
    ".mp3", ".wav", ".m4a", ".aac", ".opus", ".amr", ".oga", ".ptt",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".vcf", ".zip", ".rar", ".7z", ".txt", ".csv", ".apk"
]

def find_in_zip(zipf, name_contains):
    for info in zipf.infolist():
        if name_contains.lower() in info.filename.lower():
            return info
    return None

def build_media_index(zipf):
    index = {}
    for info in zipf.infolist():
        base = os.path.basename(info.filename)
        if base and base not in index:
            index[base] = info.filename
    return index

def extract_file_from_zip(zipf, info, temp_dir):
    out_path = os.path.join(temp_dir, os.path.basename(info.filename))
    with zipf.open(info) as src, open(out_path, 'wb') as dst:
        shutil.copyfileobj(src, dst)
    return out_path

def extract_media_from_zip(zipf, media_path_in_zip, media_filename):
    safe_filename = media_filename.replace(":", "_").replace("/", "_")
    dest_path = os.path.join(MEDIA_FOLDER, safe_filename)
    if os.path.exists(dest_path):
        return f"/static/media/{safe_filename}"
    try:
        with zipf.open(media_path_in_zip) as src, open(dest_path, 'wb') as dst:
            shutil.copyfileobj(src, dst)
        return f"/static/media/{safe_filename}"
    except Exception as e:
        print(f"Failed to extract the media {media_filename}: {e}")
        return None

# NEW: Media file scanning function
def get_media_files_from_zip(zipf):
    """Extract all media files information from the ZIP"""
    media_files = []
    
    for info in zipf.infolist():
        if info.is_dir():
            continue
            
        filename = os.path.basename(info.filename)
        if not filename:
            continue
            
        # Check if it's a media file
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext in MEDIA_EXTENSIONS:
            # Get file size
            file_size = info.file_size
            
            # Get modification date
            try:
                mod_date = datetime(*info.date_time)
            except:
                mod_date = datetime.now()
            
            # Determine media type
            media_type = "Unknown"
            if file_ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
                media_type = "Image"
            elif file_ext in [".mp4", ".webm", ".ogg", ".3gp", ".mov", ".avi", ".mkv"]:
                media_type = "Video"
            elif file_ext in [".mp3", ".wav", ".m4a", ".aac", ".opus", ".amr", ".oga", ".ptt"]:
                media_type = "Audio"
            elif file_ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]:
                media_type = "Document"
            elif file_ext in [".zip", ".rar", ".7z"]:
                media_type = "Archive"
            elif file_ext in [".txt", ".csv"]:
                media_type = "Text"
            elif file_ext == ".vcf":
                media_type = "Contact"
            elif file_ext == ".apk":
                media_type = "App"
            
            media_files.append({
                'filename': filename,
                'path_in_zip': info.filename,
                'size': file_size,
                'size_formatted': format_file_size(file_size),
                'date': mod_date.isoformat(),
                'date_formatted': mod_date.strftime('%Y-%m-%d %H:%M:%S'),
                'type': media_type,
                'extension': file_ext
            })
    
    # Sort by date (newest first)
    media_files.sort(key=lambda x: x['date'], reverse=True)
    return media_files

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def parse_contacts_db(contacts_db_path):
    number_to_name = {}
    conn = None
    try:
        conn = sqlite3.connect(contacts_db_path)
        cursor = conn.cursor()
        tried = False
        try:
            cursor.execute("""
                SELECT data1, display_name
                FROM view_data
                WHERE mimetype_id = (
                    SELECT _id FROM mimetype WHERE mimetype = 'vnd.android.cursor.item/phone_v2'
                )
            """)
            tried = True
        except Exception:
            try:
                cursor.execute("""
                    SELECT data1, display_name
                    FROM data
                    JOIN raw_contacts ON data.raw_contact_id = raw_contacts._id
                    WHERE data.mimetype_id = (
                        SELECT _id FROM mimetype WHERE mimetype = 'vnd.android.cursor.item/phone_v2'
                    )
                """)
                tried = True
            except Exception:
                try:
                    cursor.execute("""
                        SELECT data1, display_name
                        FROM data
                        LEFT JOIN raw_contacts ON data.raw_contact_id = raw_contacts._id
                        WHERE data1 IS NOT NULL AND display_name IS NOT NULL
                    """)
                    tried = True
                except Exception as e:
                    print(f"Could not parse contacts db: {e}")
        if tried:
            for number, name in cursor.fetchall():
                if number:
                    norm = ''.join(filter(str.isdigit, number))
                    if len(norm) > 8:
                        number_to_name[norm[-10:]] = name
    except Exception as e:
        print(f"Error reading contacts DB: {e}")
    finally:
        if conn:
            conn.close()
    return number_to_name

def get_table_columns(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    return [row[1] for row in cursor.fetchall()]

def get_jid_map(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT _id, raw_string FROM jid")
    return {row[0]: row[1] for row in cursor.fetchall()}

def get_chat_info(conn, jid_map):
    cursor = conn.cursor()
    cursor.execute("SELECT _id, jid_row_id, subject FROM chat")
    chat_map = {}
    for chat_id, jid_row_id, subject in cursor.fetchall():
        jid_str = jid_map.get(jid_row_id, None)
        name = subject or jid_str or f"Chat {chat_id}"
        chat_map[chat_id] = name
    return chat_map

def extract_number_from_jid(jid):
    if jid and '@' in jid and jid.split('@')[0].isdigit():
        return jid.split('@')[0][-10:]
    return None

def get_group_participants_enhanced(db_path, jid_map, contacts_map):
    """Enhanced group participant extraction that shows ALL participants including unknown numbers"""
    print("Extracting group participants (enhanced)...")
    
    group_participants = {}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all group chats first
        cursor.execute("SELECT _id, jid_row_id, subject FROM chat")
        all_chats = cursor.fetchall()
        
        group_chats = []
        for chat_id, jid_row_id, subject in all_chats:
            jid_str = jid_map.get(jid_row_id, "")
            
            if jid_str and '@g.us' in jid_str:
                group_name = subject or jid_str
                group_chats.append((chat_id, jid_row_id, group_name, jid_str))
        
        print(f"Found {len(group_chats)} groups")
        
        if not group_chats:
            return group_participants
        
        # Try multiple methods to get ALL participants
        for chat_id, jid_row_id, group_name, group_jid in group_chats:
            participants = []
            seen_numbers = set()
            
            try:
                # Method 1: Check group_participant table if it exists
                try:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='group_participant'")
                    if cursor.fetchone():
                        cursor.execute("""
                            SELECT gjid FROM group_participant 
                            WHERE group_jid_row_id = ?
                        """, (jid_row_id,))
                        
                        for (gjid_row_id,) in cursor.fetchall():
                            participant_jid = jid_map.get(gjid_row_id, "")
                            if participant_jid and '@s.whatsapp.net' in participant_jid:
                                number = participant_jid.split('@')[0]
                                if number not in seen_numbers:
                                    seen_numbers.add(number)
                                    contact_name = contacts_map.get(number[-10:], "") if len(number) >= 10 else ""
                                    participants.append({
                                        "number": number,
                                        "name": contact_name or number,
                                        "jid": participant_jid
                                    })
                except Exception:
                    pass
                
                # Method 2: Analyze messages for senders (fallback)
                if not participants:
                    cursor.execute("PRAGMA table_info(message)")
                    msg_columns = [row[1] for row in cursor.fetchall()]
                    
                    chat_col = None
                    sender_col = None
                    
                    for col in msg_columns:
                        if 'chat' in col.lower() and ('row_id' in col.lower() or 'id' in col.lower()):
                            chat_col = col
                        elif 'sender' in col.lower() and 'jid' in col.lower():
                            sender_col = col
                    
                    if chat_col and sender_col:
                        # Try with chat_id first
                        query = f"SELECT DISTINCT {sender_col} FROM message WHERE {chat_col} = ? AND {sender_col} IS NOT NULL"
                        cursor.execute(query, (chat_id,))
                        sender_rows = cursor.fetchall()
                        
                        if not sender_rows:
                            # Try with jid_row_id
                            cursor.execute(query, (jid_row_id,))
                            sender_rows = cursor.fetchall()
                        
                        for (sender_jid_row_id,) in sender_rows:
                            if sender_jid_row_id:
                                sender_jid = jid_map.get(sender_jid_row_id, "")
                                
                                if sender_jid and '@s.whatsapp.net' in sender_jid:
                                    number = sender_jid.split('@')[0]
                                    if number not in seen_numbers:
                                        seen_numbers.add(number)
                                        contact_name = contacts_map.get(number[-10:], "") if len(number) >= 10 else ""
                                        
                                        participants.append({
                                            "number": number,
                                            "name": contact_name or number,
                                            "jid": sender_jid
                                        })
                
                # Sort participants by name/number
                participants.sort(key=lambda x: (x['name'] or x['number']).lower())
                group_participants[group_name] = participants
                
            except Exception as e:
                print(f"Error processing this group called {group_name}: {e}")
                group_participants[group_name] = []
        
        conn.close()
        print(f"Group participant extraction complete - found participants in {len([g for g in group_participants.values() if g])} groups")
        
    except Exception as e:
        print(f"Error in group participant extraction: {e}")
    
    return group_participants

def extract_call_logs(db_path, jid_map, contacts_map):
    """Extract call logs from database with FIXED call direction logic"""
    print("📞 Extracting call logs...")
    
    call_logs = []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if call_log table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='call_log'")
        if not cursor.fetchone():
            print("⚠️ No call_log table found in database")
            conn.close()
            return call_logs
    
        # Get call_log table structure
        cursor.execute("PRAGMA table_info(call_log)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"📊 Call log columns: {columns}")
        
        # Find relevant columns
        def find_col(*names):
            for name in names:
                if name in columns:
                    return name
            return None
        
        jid_col = find_col('jid_row_id', 'remote_jid', 'jid')
        timestamp_col = find_col('timestamp', 'call_timestamp', 'time')
        duration_col = find_col('duration', 'call_duration')
        call_result_col = find_col('call_result', 'call_type', 'type', 'result')
        video_call_col = find_col('video_call', 'is_video', 'video')
        from_me_col = find_col('from_me', 'outgoing')
        
        print(f"📊 Column mapping:")
        print(f"   JID: {jid_col}")
        print(f"   Timestamp: {timestamp_col}")
        print(f"   Duration: {duration_col}")
        print(f"   Call Result: {call_result_col}")
        print(f"   Video: {video_call_col}")
        print(f"   From Me: {from_me_col}")
        
        # Build query based on available columns
        select_cols = []
        if jid_col: select_cols.append(jid_col)
        if timestamp_col: select_cols.append(timestamp_col)
        if duration_col: select_cols.append(duration_col)
        if call_result_col: select_cols.append(call_result_col)
        if video_call_col: select_cols.append(video_call_col)
        if from_me_col: select_cols.append(from_me_col)
        
        if not select_cols:
            print("⚠️ Could not identify call log columns")
            conn.close()
            return call_logs
        
        query = f"SELECT {', '.join(select_cols)} FROM call_log ORDER BY {timestamp_col or 'ROWID'} DESC"
        print(f"📊 Executing query: {query}")
        cursor.execute(query)
        rows = cursor.fetchall()
        
        print(f"📊 Found {len(rows)} call log entries")
        
        for row in rows:
            try:
                call_data = {}
                col_idx = 0
                
                # Extract JID and resolve contact
                if jid_col:
                    jid_row_id = row[col_idx]
                    jid_str = jid_map.get(jid_row_id, "Unknown")
                    
                    # Extract phone number and get contact name
                    phone_number = extract_number_from_jid(jid_str)
                    contact_name = ""
                    if phone_number and phone_number in contacts_map:
                        contact_name = contacts_map[phone_number]
                    
                    call_data['contact_name'] = contact_name or phone_number or jid_str
                    call_data['contact_number'] = phone_number or jid_str
                    call_data['contact_jid'] = jid_str
                    col_idx += 1
                
                # Extract timestamp
                if timestamp_col:
                    timestamp = row[col_idx]
                    try:
                        # Handle different timestamp formats
                        if timestamp > 1000000000000:  # Milliseconds
                            timestamp_ms = timestamp
                            timestamp = timestamp / 1000
                        else:
                            timestamp_ms = timestamp * 1000
                        
                        dt = datetime.fromtimestamp(timestamp)
                        call_data['timestamp'] = int(timestamp_ms)
                        call_data['date'] = dt.strftime('%Y-%m-%d')
                        call_data['time'] = dt.strftime('%H:%M:%S')
                        call_data['datetime'] = dt.isoformat()
                    except Exception as e:
                        print(f"Error processing timestamp {timestamp}: {e}")
                        call_data['timestamp'] = int(datetime.now().timestamp() * 1000)
                        call_data['date'] = "Unknown"
                        call_data['time'] = "Unknown"
                col_idx += 1
            
                # Extract duration
                if duration_col:
                    duration = row[col_idx] or 0
                    call_data['duration_seconds'] = duration
                    
                    # Format duration as MM:SS
                    if duration and duration > 0:
                        minutes = duration // 60
                        seconds = duration % 60
                        call_data['duration'] = f"{minutes:02d}:{seconds:02d}"
                    else:
                        call_data['duration'] = "0:00"
                else:
                    call_data['duration'] = "0:00"
                    call_data['duration_seconds'] = 0
                col_idx += 1
            
                # FIXED: Extract call result/type with proper logic
                call_result = None
                from_me = False
                
                if call_result_col:
                    call_result = row[col_idx]
                    col_idx += 1
                
                if from_me_col:
                    from_me = bool(row[col_idx])
                    col_idx += 1
                
                # FIXED: Proper call status determination
                if from_me:
                    # If from_me is True, it's always outgoing
                    call_data['call_status'] = "Outgoing"
                    call_data['from_me'] = True
                else:
                    # If from_me is False, check call_result for missed/incoming
                    call_data['from_me'] = False
                    
                    # Map call result codes to readable names
                    if call_result == 0 or call_result == 3:  # Missed or cancelled
                        call_data['call_status'] = "Missed"
                    elif call_result == 1:  # Incoming answered
                        call_data['call_status'] = "Incoming"
                    elif call_result == 4:  # Unavailable
                        call_data['call_status'] = "Missed"
                    elif call_result == 5:  # Busy
                        call_data['call_status'] = "Missed"
                    else:
                        # Default logic: if not from me and has duration, it's incoming
                        if call_data.get('duration_seconds', 0) > 0:
                            call_data['call_status'] = "Incoming"
                        else:
                            call_data['call_status'] = "Missed"
            
                # Extract video call flag
                if video_call_col:
                    is_video = row[col_idx - (1 if from_me_col else 0)]
                    call_data['is_video_call'] = bool(is_video)
                    call_data['call_type'] = "Video Call" if is_video else "Voice Call"
                else:
                    call_data['is_video_call'] = False
                    call_data['call_type'] = "Voice Call"
                
                call_logs.append(call_data)
                
            except Exception as e:
                print(f"⚠️ Error processing call log entry: {e}")
                continue
        
        conn.close()
        print(f"✅ Successfully extracted {len(call_logs)} call logs")
        
        # Print sample for debugging
        if call_logs:
            print("📊 Sample call logs:")
            for i, sample in enumerate(call_logs[:3]):
                print(f"   Call {i+1}:")
                for key, value in sample.items():
                    print(f"     {key}: {value}")
        
    except Exception as e:
        print(f"❌ Error extracting call logs: {e}")
        print(traceback.format_exc())
    
    return call_logs

def find_media_in_row(row, colnames, media_index):
    for col, val in zip(colnames, row):
        if not isinstance(val, str):
            continue
        val_strip = val.strip()
        for ext in MEDIA_EXTENSIONS:
            if val_strip.lower().endswith(ext):
                media_basename = os.path.basename(val_strip)
                if media_basename in media_index:
                    return media_basename
    return None

def parse_messages_grouped_by_chat_and_date(db_path, contacts_map, zipf, media_index, call_logs):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    msg_cols = get_table_columns(conn, 'message')
    colnames = msg_cols
    cursor.execute(f"SELECT * FROM message ORDER BY ROWID ASC")
    rows = cursor.fetchall()
    conn.close()

    def find_col(*names):
        for name in names:
            if name in colnames:
                return colnames.index(name)
        return None

    jid_idx = find_col('chat_row_id', 'key_remote_jid', 'jid')
    text_idx = find_col('text_data', 'data', 'message_text')
    ts_idx = find_col('timestamp')
    dir_idx = find_col('key_from_me', 'from_me')
    sender_idx = find_col('sender_jid_row_id', 'remote_resource', 'sender_jid')
    msg_type_idx = find_col('message_type', 'type')

    conn = sqlite3.connect(db_path)
    jid_map = get_jid_map(conn)
    chat_map = get_chat_info(conn, jid_map)
    conn.close()

    chat_meta = {}
    for chat_id, chat_name in chat_map.items():
        phone_number = extract_number_from_jid(chat_name)
        if '@g.us' in chat_name:
            chat_meta[chat_id] = {
                "display": chat_name,
                "type": "group",
                "sort_key": chat_name.lower()
            }
        elif phone_number and phone_number in contacts_map:
            contact_name = contacts_map[phone_number]
            chat_meta[chat_id] = {
                "display": f"{contact_name} ({chat_name})",
                "type": "contact",
                "sort_key": contact_name.lower()
            }
        else:
            chat_meta[chat_id] = {
                "display": chat_name,
                "type": "number",
                "sort_key": chat_name.lower()
            }

    # Create a map of call logs by contact for integration
    call_logs_by_jid = {}
    call_logs_by_number = {}
    
    for call in call_logs:
        contact_jid = call.get('contact_jid', '')
        contact_number = call.get('contact_number', '')
        
        if contact_jid:
            if contact_jid not in call_logs_by_jid:
                call_logs_by_jid[contact_jid] = []
            call_logs_by_jid[contact_jid].append(call)
        
        if contact_number:
            if contact_number not in call_logs_by_number:
                call_logs_by_number[contact_number] = []
            call_logs_by_number[contact_number].append(call)

    data = {}
    call_messages_integrated = 0
    
    for row in rows:
        chat_id = row[jid_idx] if jid_idx is not None else None
        text = row[text_idx] if text_idx is not None else ""
        ts = row[ts_idx] if ts_idx is not None else None
        direction = row[dir_idx] if dir_idx is not None else 0
        sender_id = row[sender_idx] if sender_idx is not None else None
        msg_type = row[msg_type_idx] if msg_type_idx is not None else 0
        
        if ts is None or chat_id not in chat_meta:
            continue
            
        try:
            date_str = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d')
        except Exception as e:
            print(f"Bad timestamp {ts}: {e}")
            continue

        chat_display = chat_meta[chat_id]["display"]

        if sender_id is None or sender_id == '':
            sender_name = "You" if direction == 1 else chat_display
        else:
            resolved = jid_map.get(sender_id)
            sender_name = "You" if direction == 1 else (resolved if resolved else chat_display)

        media_basename = find_media_in_row(row, colnames, media_index)
        media_url = None
        if media_basename:
            media_path_in_zip = media_index[media_basename]
            media_url = extract_media_from_zip(zipf, media_path_in_zip, media_basename)

        if chat_display not in data:
            data[chat_display] = {}
        if date_str not in data[chat_display]:
            data[chat_display][date_str] = []
        
        text_content = ""
        is_call_message = False
        call_info = None
        
        # Enhanced call message detection and integration
        call_keywords = ['missed call', 'call ended', 'calling', 'call duration', 'video call', 'voice call', 
                        'llamada perdida', 'llamada finalizada', 'videollamada', 'audio call', 'call', 'missed']

        # Check if this is a call message by message type or content
        if (msg_type in [8, 10, 11, 12] or  # Common call message types in WhatsApp DB
            (text and any(call_word in str(text).lower() for call_word in call_keywords)) or
            (text and ('call' in str(text).lower() or 'missed' in str(text).lower()))):
            
            is_call_message = True
            call_messages_integrated += 1
            
            # Try to find matching call log
            chat_jid = jid_map.get(chat_id, "")
            chat_number = extract_number_from_jid(chat_jid)
            
            matching_call = None
            
            # Look for matching call log by JID first
            if chat_jid in call_logs_by_jid:
                for call in call_logs_by_jid[chat_jid]:
                    time_diff = abs(call['timestamp'] - ts)
                    if time_diff < 600000:  # Within 10 minutes (increased tolerance)
                        matching_call = call
                        break
            
            # Look for matching call log by number if no JID match
            if not matching_call and chat_number and chat_number in call_logs_by_number:
                for call in call_logs_by_number[chat_number]:
                    time_diff = abs(call['timestamp'] - ts)
                    if time_diff < 600000:  # Within 10 minutes
                        matching_call = call
                        break
            
            if matching_call:
                # Store call information for frontend rendering
                call_info = {
                    'type': matching_call['call_type'],
                    'status': matching_call['call_status'],
                    'duration': matching_call['duration'],
                    'is_video': matching_call['is_video_call'],
                    'from_me': matching_call.get('from_me', direction == 1)
                }
                
                # Set text content for call message based on status and direction
                if matching_call['call_status'] == 'Missed':
                    if matching_call.get('from_me', direction == 1):
                        text_content = f"{'Video call' if matching_call['is_video_call'] else 'Voice call'} • No answer"
                    else:
                        text_content = f"Missed {'video call' if matching_call['is_video_call'] else 'voice call'}"
                elif matching_call['call_status'] == 'Outgoing':
                    text_content = f"{'Video call' if matching_call['is_video_call'] else 'Voice call'}"
                    if matching_call['duration'] != "0:00":
                        text_content += f" • {matching_call['duration']}"
                    else:
                        text_content += " • No answer"
                elif matching_call['call_status'] == 'Incoming':
                    text_content = f"{'Video call' if matching_call['is_video_call'] else 'Voice call'}"
                    if matching_call['duration'] != "0:00":
                        text_content += f" • {matching_call['duration']}"
            else:
                # Fallback for call messages without matching call log
                call_info = {
                    'type': 'Video Call' if ('video' in str(text).lower()) else 'Voice Call',
                    'status': 'Missed' if ('missed' in str(text).lower()) else ('Outgoing' if direction == 1 else 'Incoming'),
                    'duration': '0:00',
                    'is_video': 'video' in str(text).lower(),
                    'from_me': direction == 1
                }
                
                if 'missed' in str(text).lower():
                    text_content = f"Missed {'video call' if call_info['is_video'] else 'voice call'}"
                elif direction == 1:  # Outgoing
                    text_content = f"{'Video call' if call_info['is_video'] else 'Voice call'} • No answer"
                else:  # Incoming
                    text_content = f"{'Video call' if call_info['is_video'] else 'Voice call'}"
        else:
            if text:
                try:
                    if isinstance(text, bytes):
                        text_content = text.decode('utf-8', errors='replace')
                    else:
                        text_content = str(text)
                except (UnicodeDecodeError, UnicodeEncodeError):
                    text_content = str(text).encode('utf-8', errors='replace').decode('utf-8', errors='replace')

        # Store message with call info (make sure this is at the end of the message processing loop)
        message_data = [ts // 1000, text_content, direction, sender_name, media_url, is_call_message]
        if is_call_message and 'call_info' in locals():
            message_data.append(call_info)

        data[chat_display][date_str].append(message_data)

    print(f"Integrated {call_messages_integrated} call messages with call logs")

    chat_list = []
    for chat_id, meta in chat_meta.items():
        chat_display = meta["display"]
        if chat_display in data:
            chat_list.append({
                "display": chat_display,
                "type": meta["type"],
                "sort_key": meta["sort_key"]
            })
    return {"messages": data, "chat_list": chat_list}

def decrypt_database(key_file, encrypted_db, output_db='msgstore.db'):
    cmd = ['wadecrypt', key_file, encrypted_db, output_db]
    print(f"Running decryption command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Decryption failed:", result.stderr)
        raise RuntimeError("Decryption failed.")
    print("Decryption successful.")
    return output_db

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    try:
        root_folder = request.json.get('root_folder')
        zip_path = None
        for dirpath, dirnames, filenames in os.walk(root_folder):
            for fname in filenames:
                if fname.lower().endswith('.zip'):
                    zip_path = os.path.join(dirpath, fname)
                    break
            if zip_path:
                break
        if not zip_path:
            return jsonify({'error': 'No .zip file found in the provided folder.'}), 400

        with pyzipper.AESZipFile(zip_path, 'r') as zipf:
            db_info = find_in_zip(zipf, "msgstore.db.crypt")
            key_info = find_in_zip(zipf, "com.whatsapp/files/key")
            contacts_info = find_in_zip(zipf, "contacts2.db") or find_in_zip(zipf, "contacts.db")
            if not db_info or not key_info:
                return jsonify({'error': 'Could not find WhatsApp database or key in the ZIP file.'}), 400

            contacts_map = {}
            with tempfile.TemporaryDirectory() as temp_dir:
                db_file = extract_file_from_zip(zipf, db_info, temp_dir)
                key_file = extract_file_from_zip(zipf, key_info, temp_dir)
                if contacts_info:
                    contacts_db_file = extract_file_from_zip(zipf, contacts_info, temp_dir)
                    try:
                        contacts_map = parse_contacts_db(contacts_db_file)
                        print(f"Loaded {len(contacts_map)} contacts")
                    except Exception as e:
                        print(f"Contacts parse failed: {e}")
                
                decrypted_db = decrypt_database(key_file, db_file)
                conn = sqlite3.connect(decrypted_db)
                jid_map = get_jid_map(conn)
                print(f"Loaded {len(jid_map)} JID mappings")
                conn.close()
                
                media_index = build_media_index(zipf)
                print(f"Built media index with {len(media_index)} files")
                
                # Use the FIXED call logs extraction method
                call_logs = extract_call_logs(decrypted_db, jid_map, contacts_map)
                
                # Use enhanced group participants function
                group_participants = get_group_participants_enhanced(decrypted_db, jid_map, contacts_map)
                
                data = parse_messages_grouped_by_chat_and_date(decrypted_db, contacts_map, zipf, media_index, call_logs)
                data["group_participants"] = group_participants
                data["contacts"] = contacts_map
                data["call_logs"] = call_logs
                
                print(f"Final data summary:")
                print(f"  - Chats: {len(data['chat_list'])}")
                print(f"  - Call logs: {len(call_logs)}")
                print(f"  - Groups: {len(group_participants)}")
                print(f"  - Contacts: {len(contacts_map)}")
                
                # Clean up decrypted database
                if os.path.exists(decrypted_db):
                    os.remove(decrypted_db)
                
                return jsonify(data)
                
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# NEW: Media viewer endpoint
@app.route('/view-media', methods=['POST'])
def view_media():
    try:
        root_folder = request.json.get('root_folder')
        zip_path = None
        for dirpath, dirnames, filenames in os.walk(root_folder):
            for fname in filenames:
                if fname.lower().endswith('.zip'):
                    zip_path = os.path.join(dirpath, fname)
                    break
            if zip_path:
                break
        if not zip_path:
            return jsonify({'error': 'No .zip file found in the provided folder.'}), 400

        with pyzipper.AESZipFile(zip_path, 'r') as zipf:
            media_files = get_media_files_from_zip(zipf)
            
            # Group by type for better organization
            media_by_type = {}
            for media in media_files:
                media_type = media['type']
                if media_type not in media_by_type:
                    media_by_type[media_type] = []
                media_by_type[media_type].append(media)
            
            # Calculate statistics
            total_files = len(media_files)
            total_size = sum(media['size'] for media in media_files)
            
            return jsonify({
                'media_files': media_files,
                'media_by_type': media_by_type,
                'statistics': {
                    'total_files': total_files,
                    'total_size': total_size,
                    'total_size_formatted': format_file_size(total_size),
                    'types': {media_type: len(files) for media_type, files in media_by_type.items()}
                }
            })
                
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# NEW: Download selected media files
@app.route('/download-media', methods=['POST'])
def download_media():
    try:
        root_folder = request.json.get('root_folder')
        media_files = request.json.get('media_files', [])  # List of files to download
        
        if not media_files:
            return jsonify({'error': 'No media files specified for download.'}), 400
        
        zip_path = None
        for dirpath, dirnames, filenames in os.walk(root_folder):
            for fname in filenames:
                if fname.lower().endswith('.zip'):
                    zip_path = os.path.join(dirpath, fname)
                    break
            if zip_path:
                break
        if not zip_path:
            return jsonify({'error': 'No .zip file found in the provided folder.'}), 400

        # Create a temporary ZIP file with selected media
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            temp_zip_path = temp_zip.name
        
        with pyzipper.AESZipFile(zip_path, 'r') as source_zipf:
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as target_zipf:
                for media_file in media_files:
                    try:
                        # Extract file from source ZIP and add to target ZIP
                        file_data = source_zipf.read(media_file['path_in_zip'])
                        # Use original filename to preserve structure
                        target_zipf.writestr(media_file['filename'], file_data)
                    except Exception as e:
                        print(f"Failed to add {media_file['filename']} to ZIP: {e}")
                        continue
        
        # Send the ZIP file
        return send_file(
            temp_zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'whatsapp_media_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        )
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# NEW: Download single media file
@app.route('/download-single-media', methods=['POST'])
def download_single_media():
    try:
        root_folder = request.json.get('root_folder')
        media_file = request.json.get('media_file')  # Single file info
        
        if not media_file:
            return jsonify({'error': 'No media file specified for download.'}), 400
        
        zip_path = None
        for dirpath, dirnames, filenames in os.walk(root_folder):
            for fname in filenames:
                if fname.lower().endswith('.zip'):
                    zip_path = os.path.join(dirpath, fname)
                    break
            if zip_path:
                break
        if not zip_path:
            return jsonify({'error': 'No .zip file found in the provided folder.'}), 400

        with pyzipper.AESZipFile(zip_path, 'r') as zipf:
            try:
                # Extract the specific file
                file_data = zipf.read(media_file['path_in_zip'])
                
                # Create a temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(file_data)
                    temp_file_path = temp_file.name
                
                # Determine MIME type based on extension
                file_ext = media_file['extension'].lower()
                mime_type = 'application/octet-stream'  # Default
                
                if file_ext in ['.jpg', '.jpeg']:
                    mime_type = 'image/jpeg'
                elif file_ext == '.png':
                    mime_type = 'image/png'
                elif file_ext == '.gif':
                    mime_type = 'image/gif'
                elif file_ext == '.mp4':
                    mime_type = 'video/mp4'
                elif file_ext == '.mp3':
                    mime_type = 'audio/mpeg'
                elif file_ext == '.pdf':
                    mime_type = 'application/pdf'
                
                return send_file(
                    temp_file_path,
                    mimetype=mime_type,
                    as_attachment=True,
                    download_name=media_file['filename']
                )
                
            except Exception as e:
                return jsonify({'error': f'Failed to extract file: {str(e)}'}), 500
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/call-logs', methods=['POST'])
def call_logs():
    try:
        root_folder = request.json.get('root_folder')
        zip_path = None
        for dirpath, dirnames, filenames in os.walk(root_folder):
            for fname in filenames:
                if fname.lower().endswith('.zip'):
                    zip_path = os.path.join(dirpath, fname)
                    break
            if zip_path:
                break
        if not zip_path:
            return jsonify({'error': 'No .zip file found in the provided folder.'}), 400

        with pyzipper.AESZipFile(zip_path, 'r') as zipf:
            db_info = find_in_zip(zipf, "msgstore.db.crypt")
            key_info = find_in_zip(zipf, "com.whatsapp/files/key")
            contacts_info = find_in_zip(zipf, "contacts2.db") or find_in_zip(zipf, "contacts.db")
            if not db_info or not key_info:
                return jsonify({'error': 'Could not find WhatsApp database or key in the ZIP file.'}), 400

            contacts_map = {}
            with tempfile.TemporaryDirectory() as temp_dir:
                db_file = extract_file_from_zip(zipf, db_info, temp_dir)
                key_file = extract_file_from_zip(zipf, key_info, temp_dir)
                if contacts_info:
                    contacts_db_file = extract_file_from_zip(zipf, contacts_info, temp_dir)
                    try:
                        contacts_map = parse_contacts_db(contacts_db_file)
                    except Exception as e:
                        print(f"Contacts parse failed: {e}")
                
                decrypted_db = decrypt_database(key_file, db_file)
                conn = sqlite3.connect(decrypted_db)
                jid_map = get_jid_map(conn)
                conn.close()
                
                call_logs = extract_call_logs(decrypted_db, jid_map, contacts_map)
                
                # Clean up decrypted database
                if os.path.exists(decrypted_db):
                    os.remove(decrypted_db)
                
                fmt = request.args.get('format', 'json')
                if fmt == 'html':
                    html = generate_call_logs_html(call_logs)
                    response = make_response(html)
                    response.headers["Content-Disposition"] = "attachment; filename=call_logs.html"
                    response.headers["Content-Type"] = "text/html; charset=utf-8"
                    return response
                else:
                    buf = io.BytesIO()
                    buf.write(json.dumps(call_logs, indent=2, ensure_ascii=False).encode('utf-8'))
                    buf.seek(0)
                    return send_file(
                        buf, mimetype='application/json',
                        as_attachment=True, download_name='call_logs.json'
                    )
                
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def generate_call_logs_html(call_logs):
    """Generate HTML export for call logs"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp Call Logs</title>
    <style>
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
            background: #0b141a;
            color: #e9edef;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: #111b21;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #00a884;
            border-bottom: 2px solid #00a884;
            padding-bottom: 10px;
            text-align: center;
        }}
        .stats {{
            background: #202c33;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            text-align: center;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #202c33;
            border-radius: 8px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #374045;
        }}
        th {{
            background: #00a884;
            color: #111b21;
            font-weight: 600;
        }}
        tr:hover {{
            background: #2a3942;
        }}
        .call-type {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .outgoing {{ color: #00a884; }}
        .incoming {{ color: #53bdeb; }}
        .missed {{ color: #ff6b6b; }}
        .duration {{ font-weight: 500; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📞 WhatsApp Call Logs</h1>
        <div class="stats">
            <h3>Total Calls: {len(call_logs)}</h3>
            <p>Export generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Date & Time</th>
                    <th>Contact</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Duration</th>
                </tr>
            </thead>
            <tbody>"""
    
    for call in call_logs:
        try:
            dt = datetime.fromtimestamp(call['timestamp'] / 1000)
            date_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            date_time = str(call['timestamp'])
        
        call_icon = "📹" if call['call_type'] == "Video Call" else "📞"
        
        html += f"""
                <tr>
                    <td>{date_time}</td>
                    <td>{call['contact_name']}</td>
                    <td class="call-type">{call_icon} {call['call_type']}</td>
                    <td class="{call['call_status'].lower()}">{call['call_status']}</td>
                    <td class="duration">{call['duration']}</td>
                </tr>"""
    
    html += """
            </tbody>
        </table>
    </div>
</body>
</html>"""
    
    return html

@app.route('/contacts', methods=['POST'])
def contacts():
    try:
        root_folder = request.json.get('root_folder')
        zip_path = None
        for dirpath, dirnames, filenames in os.walk(root_folder):
            for fname in filenames:
                if fname.lower().endswith('.zip'):
                    zip_path = os.path.join(dirpath, fname)
                    break
            if zip_path:
                break
        if not zip_path:
            return jsonify({'error': 'No .zip file found in the provided folder.'}), 400

        with pyzipper.AESZipFile(zip_path, 'r') as zipf:
            contacts_info = find_in_zip(zipf, "contacts2.db") or find_in_zip(zipf, "contacts.db")
            contacts_map = {}
            with tempfile.TemporaryDirectory() as temp_dir:
                if contacts_info:
                    contacts_db_file = extract_file_from_zip(zipf, contacts_info, temp_dir)
                    try:
                        contacts_map = parse_contacts_db(contacts_db_file)
                    except Exception as e:
                        print(f"Contacts parse failed: {e}")
                contacts_list = []
                for number, name in contacts_map.items():
                    contacts_list.append({"number": number, "name": name})
                contacts_list.sort(key=lambda x: (x['name'] or x['number']).lower())
                fmt = request.args.get('format', 'json')
                if fmt == 'html':
                    html = """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <title>WhatsApp Contacts</title>
                        <style>
                            body { background: #181f23; color: #e9edef; font-family: 'Segoe UI', sans-serif; }
                            table { border-collapse: collapse; width: 100%; background: #111b21; color: #e9edef;}
                            th, td { border: 1px solid #374045; padding: 8px 12px; text-align: left; }
                            th { background: #00a884; color: #111b21; }
                        </style>
                    </head>
                    <body>
                        <h2>WhatsApp Contacts</h2>
                        <table>
                            <thead>
                                <tr><th>Number</th><th>Name</th></tr>
                            </thead>
                            <tbody>
                    """
                    for c in contacts_list:
                        html += f"<tr><td>{c['number']}</td><td>{c['name'] or c['number']}</td></tr>"
                    html += """
                            </tbody>
                        </table>
                    </body>
                    </html>
                    """
                    response = make_response(html)
                    response.headers["Content-Disposition"] = "attachment; filename=contacts.html"
                    response.headers["Content-Type"] = "text/html"
                    return response
                else:
                    buf = io.BytesIO()
                    buf.write(json.dumps(contacts_list, indent=2).encode())
                    buf.seek(0)
                    return send_file(
                        buf, mimetype='application/json',
                        as_attachment=True, download_name='contacts.json'
                    )
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/download-all', methods=['POST'])
def download_all():
    try:
        print("Starting download-all process...")
        root_folder = request.json.get('root_folder')
        zip_path = None
        for dirpath, dirnames, filenames in os.walk(root_folder):
            for fname in filenames:
                if fname.lower().endswith('.zip'):
                    zip_path = os.path.join(dirpath, fname)
                    break
            if zip_path:
                break
        if not zip_path:
            return jsonify({'error': 'No .zip file found in the provided folder.'}), 400

        print(f"Found ZIP file: {zip_path}")
        
        with pyzipper.AESZipFile(zip_path, 'r') as zipf:
            db_info = find_in_zip(zipf, "msgstore.db.crypt")
            key_info = find_in_zip(zipf, "com.whatsapp/files/key")
            contacts_info = find_in_zip(zipf, "contacts2.db") or find_in_zip(zipf, "contacts.db")
            if not db_info or not key_info:
                return jsonify({'error': 'Could not find WhatsApp database or key in the ZIP file.'}), 400

            print("Extracting files from ZIP...")
            contacts_map = {}
            with tempfile.TemporaryDirectory() as temp_dir:
                db_file = extract_file_from_zip(zipf, db_info, temp_dir)
                key_file = extract_file_from_zip(zipf, key_info, temp_dir)
                if contacts_info:
                    contacts_db_file = extract_file_from_zip(zipf, contacts_info, temp_dir)
                    try:
                        print("Parsing contacts...")
                        contacts_map = parse_contacts_db(contacts_db_file)
                        print(f"Loaded {len(contacts_map)} contacts")
                    except Exception as e:
                        print(f"Contacts parse failed: {e}")
                
                print("Decrypting database...")
                decrypted_db = decrypt_database(key_file, db_file)
                
                print("Loading JID mappings...")
                conn = sqlite3.connect(decrypted_db)
                jid_map = get_jid_map(conn)
                conn.close()
                print(f"Loaded {len(jid_map)} JID mappings")
                
                print("Building media index...")
                media_index = build_media_index(zipf)
                print(f"Built media index with {len(media_index)} files")
                
                print("Extracting call logs...")
                call_logs = extract_call_logs(decrypted_db, jid_map, contacts_map)
                
                print("Extracting group participants...")
                group_participants = get_group_participants_enhanced(decrypted_db, jid_map, contacts_map)
                print(f"Found {len(group_participants)} groups")
                
                print("Parsing messages...")
                data = parse_messages_grouped_by_chat_and_date(decrypted_db, contacts_map, zipf, media_index, call_logs)
                print(f"Parsed {len(data['chat_list'])} chats")
                
                # Clean up decrypted database
                if os.path.exists(decrypted_db):
                    os.remove(decrypted_db)
                
                # Prepare complete data package
                complete_data = {
                    "messages": data["messages"],
                    "chat_list": data["chat_list"],
                    "group_participants": group_participants,
                    "contacts": contacts_map,
                    "call_logs": call_logs,
                    "export_info": {
                        "export_date": datetime.now().isoformat(),
                        "total_chats": len(data["chat_list"]),
                        "total_groups": len(group_participants),
                        "total_contacts": len(contacts_map),
                        "total_calls": len(call_logs)
                    }
                }
                
                fmt = request.args.get('format', 'json')
                print(f"Generating {fmt} export...")
                
                if fmt == 'html':
                    html = generate_complete_html_export(complete_data)
                    response = make_response(html)
                    response.headers["Content-Disposition"] = "attachment; filename=whatsapp_complete_export.html"
                    response.headers["Content-Type"] = "text/html; charset=utf-8"
                    print("HTML export ready for download")
                    return response
                else:
                    buf = io.BytesIO()
                    buf.write(json.dumps(complete_data, indent=2, ensure_ascii=False).encode('utf-8'))
                    buf.seek(0)
                    print("JSON export ready for download")
                    return send_file(
                        buf, mimetype='application/json',
                        as_attachment=True, download_name='whatsapp_complete_export.json'
                    )
                
    except Exception as e:
        print(f"Error in download_all: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

def generate_complete_html_export(data):
    """Generate a complete HTML export of all WhatsApp data with size limits"""
    print("Generating HTML export...")
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>WhatsApp Complete Export</title>
        <style>
            body {{
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
                background: #0b141a;
                color: #e9edef;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: #111b21;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            }}
            h1, h2, h3 {{
                color: #00a884;
                border-bottom: 2px solid #00a884;
                padding-bottom: 10px;
            }}
            .export-info {{
                background: #202c33;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
                border-left: 4px solid #00a884;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            .stat-card {{
                background: #00a884;
                color: #111b21;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
            }}
            .call-logs-table {{
                width: 100%;
                border-collapse: collapse;
                background: #202c33;
                border-radius: 8px;
                overflow: hidden;
                margin-top: 20px;
            }}
            .call-logs-table th, .call-logs-table td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #374045;
            }}
            .call-logs-table th {{
                background: #00a884;
                color: #111b21;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📱 WhatsApp Complete Export</h1>
            
            <div class="export-info">
                <h3>📊 Export Information</h3>
                <div class="stats">
                    <div class="stat-card">
                        <div style="font-size: 2em;">💬</div>
                        <div>{data['export_info']['total_chats']}</div>
                        <div>Total Chats</div>
                    </div>
                    <div class="stat-card">
                        <div style="font-size: 2em;">👥</div>
                        <div>{data['export_info']['total_groups']}</div>
                        <div>Groups</div>
                    </div>
                    <div class="stat-card">
                        <div style="font-size: 2em;">📞</div>
                        <div>{data['export_info']['total_contacts']}</div>
                        <div>Contacts</div>
                    </div>
                    <div class="stat-card">
                        <div style="font-size: 2em;">📱</div>
                        <div>{data['export_info']['total_calls']}</div>
                        <div>Call Logs</div>
                    </div>
                </div>
                <p><strong>Export Date:</strong> {data['export_info']['export_date']}</p>
            </div>

            <section id="call-logs">
                <h2>📱 Call Logs ({len(data['call_logs'])})</h2>
                <table class="call-logs-table">
                    <thead>
                        <tr>
                            <th>Date & Time</th>
                            <th>Contact</th>
                            <th>Type</th>
                            <th>Status</th>
                            <th>Duration</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # Add call logs (limit to prevent huge files)
    for call in data['call_logs'][:100]:  # Limit to 100 calls
        try:
            dt = datetime.fromtimestamp(call['timestamp'] / 1000)
            date_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            date_time = str(call['timestamp'])
        
        call_icon = "📹" if call['call_type'] == "Video Call" else "📞"
        
        html += f"""
                        <tr>
                            <td>{date_time}</td>
                            <td>{call['contact_name']}</td>
                            <td>{call_icon} {call['call_type']}</td>
                            <td>{call['call_status']}</td>
                            <td>{call['duration']}</td>
                        </tr>
        """
    
    if len(data['call_logs']) > 100:
        html += f"""
                        <tr>
                            <td colspan="5" style="text-align: center; font-style: italic;">
                                ... and {len(data['call_logs']) - 100} more call logs
                            </td>
                        </tr>
        """
    
    html += """
                    </tbody>
                </table>
            </section>
            
            <div class="export-info">
                <p><strong>Export completed successfully.</strong></p>
                <p><em>Call logs extracted with FIXED categorization logic.</em></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    print(f"HTML export generated with {len(data['call_logs'])} call logs")
    return html



if __name__ == '__main__':
    print("🚀 Starting WhatsApp Extractor on port 5000...")
    app.run(debug=True, port=5000, host='0.0.0.0')
