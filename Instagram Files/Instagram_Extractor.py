import os
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
import re
import hashlib
import sys
import tempfile
import traceback
import time

# --- Configuration ---
# Set the names of your extractor scripts here
V5_SCRIPT_NAME = 'Module1.py'
V7_SCRIPT_NAME = 'Module2.py'

class MasterExtractor:
    """
    Orchestrates the execution of V5 and V7 Instagram extractors,
    and merges their outputs into a final, consolidated report.
    """

    def __init__(self, input_path, case_info=None, output_callback=None):
        """
        Initializes the master extractor.

        Args:
            input_path (str): The path to the Instagram data dump (folder or ZIP).
            case_info (dict, optional): A dictionary with case information.
            output_callback (function, optional): Callback function for output messages.
        """
        self.input_path = Path(input_path).resolve()
        self.case_info = case_info or {}
        self.output_callback = output_callback or print

        # Define output directories
        self.base_output_dir = Path.cwd() / f"instagram_master_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.v5_output_dir = self.base_output_dir / "v5_temp_output"
        self.v7_output_dir = self.base_output_dir / "v7_temp_output"
        self.final_output_dir = self.base_output_dir / "final_report"

        # Create directories
        self.v5_output_dir.mkdir(parents=True, exist_ok=True)
        self.v7_output_dir.mkdir(parents=True, exist_ok=True)
        self.final_output_dir.mkdir(parents=True, exist_ok=True)

        self.output_callback(f" Master output will be saved to: {self.base_output_dir}")

        # Initialize the consolidated report structure
        self.consolidated_report = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "orchestrator_version": "1.0.0",
                "input_path": str(self.input_path),
                "case_info": self.case_info
            },
            "summary": {
                "total_media_count": 0,
                "total_messages_count": 0,
                "total_users_analyzed": 0,
                "total_sessions_found": 0
            },
            "v5_report": {
                "status": "not_run",
                "media": [],
                "messages": [],
                "user_profile": {},
                "session_data": {},
                "errors": []
            },
            "v7_report": {
                "status": "not_run", 
                "users": [],
                "logged_in_user": {},
                "session_data": {},
                "extraction_stats": {},
                "errors": []
            },
            "merged_files": {
                "chats": [],
                "media": [],
                "chat_media": [],
                "session_ids": {},
                "logged_in_user_profile": {},
                "complete_folder_analysis": {},
                "extraction_report": {},
                "master": {}
            },
            "issues": []
        }

    def _sanitize_script(self, original_script_path):
        """
        Reads a script, removes characters that cause UnicodeEncodeError on Windows,
        and saves it to a temporary file outside the main project directory.
        """
        try:
            # This regex pattern matches a wide range of emoji characters.
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"  # emoticons
                "\U0001F300-\U0001F5FF"  # symbols & pictographs
                "\U0001F680-\U0001F6FF"  # transport & map symbols
                "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                "\U00002702-\U000027B0"
                "\U000024C2-\U0001F251"
                "]+",
                flags=re.UNICODE,
            )
        
            # Create sanitized script in a temporary directory to avoid Flask file watcher
            temp_dir = Path(tempfile.gettempdir()) / "instagram_extractor_temp"
            temp_dir.mkdir(exist_ok=True)
            sanitized_script_path = temp_dir / f"sanitized_{original_script_path.name}"
        
            with open(original_script_path, 'r', encoding='utf-8') as f_in:
                content = f_in.read()
        
            # Remove the emojis from the content
            sanitized_content = emoji_pattern.sub('', content)
        
            with open(sanitized_script_path, 'w', encoding='utf-8') as f_out:
                f_out.write(sanitized_content)
            
            self.output_callback(f"ℹ️ Created sanitized script: {sanitized_script_path.name}")
            return sanitized_script_path

        except Exception as e:
            self.output_callback(f"ERROR sanitizing script {original_script_path.name}: {e}")
            return None

    def _run_script(self, script_name, output_dir):
        """
        Executes a given extractor script using subprocess.

        Args:
            script_name (str): The filename of the script to run.
            output_dir (Path): The directory to save the script's output.

        Returns:
            Path: The actual output directory created by the script, or None if failed.
        """
        script_path = Path.cwd() / script_name
        if not script_path.exists():
            self.output_callback(f"❌ ERROR: Script not found: {script_name}")
            return None

        self.output_callback(f"\n{'='*30}")
        self.output_callback(f"🚀 Running {script_name}...")
        self.output_callback(f"   Input: {self.input_path}")
        self.output_callback(f"   Output: {output_dir}")
        self.output_callback(f"{'='*30}")

        # To run the scripts, we simulate user input for the path
        # and case info by piping it to the script's stdin.
        input_data = f"{self.input_path}\n"
        input_data += f"{self.case_info.get('case_number', '')}\n"
        input_data += f"{self.case_info.get('examiner', '')}\n"
        input_data += f"{self.case_info.get('evidence_item', '')}\n"
        # For V5, we need to answer the media download prompt
        if "Module1.py" in script_name: # Check for Module1.py specifically
            input_data += "n\n" # Assuming 'no' to media download to speed up

        try:
            # Create a copy of the current environment and force UTF-8 encoding
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # We need to change the working directory for the subprocess
            # so it can find its output directory correctly.
            process = subprocess.run(
                ['python', script_path],
                input=input_data,
                encoding='utf-8',
                capture_output=True,
                check=True,
                cwd=output_dir,
                env=env # Pass the modified environment to the subprocess
            )
            self.output_callback(f"✅ {script_name} finished successfully.")
            
            # The scripts create their own subdirectories, we need to find the actual output path
            # The script output is typically in a timestamped folder inside output_dir
            # We need to find the most recently created directory within output_dir
            subdirs = [d for d in output_dir.iterdir() if d.is_dir()]
            if subdirs:
                actual_output = max(subdirs, key=os.path.getmtime)
                return actual_output
            else:
                self.output_callback(f"⚠️ No output directory found for {script_name}")
                return None
                
        except subprocess.CalledProcessError as e:
            self.output_callback(f"❌ ERROR running {script_name}:")
            # Print stdout and stderr from the failed process for better debugging
            self.output_callback("--- STDOUT ---")
            self.output_callback(e.stdout)
            self.output_callback("--- STDERR ---")
            self.output_callback(e.stderr)
            return None
        except FileNotFoundError:
            self.output_callback(f"❌ ERROR: 'python' command not found. Is Python installed and in your PATH?")
            return None
        except Exception as e:
            self.output_callback(f"❌ An unexpected error occurred while running {script_name}: {e}")
            return None

    def _load_json(self, file_path):
        """Safely loads a JSON file."""
        if not file_path or not file_path.exists():
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.output_callback(f"⚠️ Warning: Could not read or parse JSON file {file_path}. Error: {e}")
            return None

    def _intelligent_merge_profiles(self, v5_profile, v7_profile):
        """
        Intelligently merges two user profile dictionaries, prioritizing the best data.
        """
        # If one profile is missing, return the other
        if not v5_profile:
            return v7_profile
        if not v7_profile:
            return v5_profile

        # Start with a copy of the V5 profile, then intelligently update it from V7
        merged = v5_profile.copy()

        # --- Specific fix for username ---
        v5_username = v5_profile.get('username')
        v7_username = v7_profile.get('username')
        # Define common invalid usernames that are likely parsing artifacts
        invalid_usernames = {'api', 'user', 'profile', 'data', 'json', 'media'}
        
        # Prefer V7 username if it's valid (not None and not in the invalid list)
        if v7_username and v7_username.lower() not in invalid_usernames:
            merged['username'] = v7_username
        # Otherwise, use V5 username if it's valid
        elif v5_username and v5_username.lower() not in invalid_usernames:
            merged['username'] = v5_username

        # Simple fields (excluding username): Prefer V7 if it has a value, otherwise keep V5
        for key in ['full_name', 'email', 'phone_number', 'bio', 'website', 'primary_instagram_session_id', 'is_private', 'is_verified', 'account_creation_date', 'last_login']:
            if v7_profile.get(key):
                merged[key] = v7_profile[key]

        # Numerical counts: Take the higher value
        for key in ['followers_count', 'following_count', 'posts_count', 'pending_incoming_requests_count', 'pending_outgoing_requests_count']:
            v5_val = v5_profile.get(key, 0) or 0
            v7_val = v7_profile.get(key, 0) or 0
            merged[key] = max(v5_val, v7_val)

        # Confidence: Take the one with the higher confidence score
        v5_confidence = v5_profile.get('user_id_confidence', 0) or 0
        v7_confidence = v7_profile.get('user_id_confidence', 0) or 0
        if v7_confidence >= v5_confidence:
            merged['user_id'] = v7_profile.get('user_id')
            merged['user_id_confidence'] = v7_profile.get('user_id_confidence')
            merged['user_id_source'] = v7_profile.get('user_id_source')

        # Combine lists and remove duplicates
        for key in ['linked_facebook_accounts', 'profile_picture_paths', 'all_session_ids', 'posts_media_metadata', 'stories_media_metadata']:
            v5_list = v5_profile.get(key, []) or []
            v7_list = v7_profile.get(key, []) or []
            combined_list = v5_list + v7_list
            
            # Deduplicate list of dicts (more complex) or simple items
            if combined_list and isinstance(combined_list[0], dict):
                # Use a tuple of items to make dicts hashable for deduplication
                seen = set()
                unique_list = []
                for d in combined_list:
                    # Create a frozenset of items for hashability
                    try:
                        # Sort items to handle dicts with same content but different order
                        t = frozenset(sorted(d.items()))
                        if t not in seen:
                            seen.add(t)
                            unique_list.append(d)
                    except TypeError: # Handle unhashable types like lists in dicts
                        # Fallback for unhashable items (e.g., lists within dicts)
                        if d not in unique_list:
                            unique_list.append(d)
                merged[key] = unique_list
            elif combined_list:
                # Simple deduplication for lists of strings/numbers
                merged[key] = list(dict.fromkeys(combined_list)) # Preserves order and is fast
            else:
                merged[key] = []

        # Deep merge nested dictionaries
        for key in ['device_info', 'authentication_details', 'privacy_settings', 'notification_settings', 'other_user_details']:
             merged[key] = self._deep_merge_dicts(v5_profile.get(key, {}), v7_profile.get(key, {}))

        return merged

    def _deep_merge_dicts(self, d1, d2):
        """Recursively merges two dictionaries."""
        d1 = d1 or {}
        d2 = d2 or {}
        for k, v in d2.items():
            if k in d1 and isinstance(d1.get(k), dict) and isinstance(v, dict):
                d1[k] = self._deep_merge_dicts(d1[k], v)
            elif k in d1 and isinstance(d1.get(k), list) and isinstance(v, list):
                # Avoid duplicate entries in lists
                for item in v:
                    if item not in d1[k]:
                        d1[k].append(item)
            else:
                d1[k] = v
        return d1

    def _save_final_json(self, data, filename):
        """Saves the final merged JSON data."""
        output_path = self.final_output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        self.output_callback(f"💾 Saved final merged file: {filename}")

    def merge_and_generate_reports(self, v5_path, v7_path):
        """
        Merges the JSON outputs from both scripts into the final report files.
        """
        self.output_callback(f"\n{'='*30}")
        self.output_callback("🔄 Merging reports and generating final JSON files...")
        self.output_callback(f"{'='*30}")

        # 1. Copy V5-specific files directly
        self.output_callback("   -> Copying V5 specific files...")
        v5_files_to_copy = ['chats.json', 'media.json', 'chat_media.json', 'server_ids.json']
        for filename in v5_files_to_copy:
            src = v5_path / filename
            if src.exists():
                shutil.copy(src, self.final_output_dir / filename)
                self.output_callback(f"   Copied: {filename}")
                
                # Load and store in consolidated report
                file_data = self._load_json(self.final_output_dir / filename)
                if file_data and 'data' in file_data:
                    if filename == 'chats.json':
                        self.consolidated_report["merged_files"]["chats"] = file_data['data']
                        self.consolidated_report["summary"]["total_messages_count"] = len(file_data['data'])
                    elif filename == 'media.json':
                        self.consolidated_report["merged_files"]["media"] = file_data['data']
                        self.consolidated_report["summary"]["total_media_count"] = len(file_data['data'])
                    elif filename == 'chat_media.json':
                        self.consolidated_report["merged_files"]["chat_media"] = file_data['data']
            else:
                self.output_callback(f"   ⚠️ V5 file not found, skipping: {filename}")

        # 2. Handle session_ids.json merging
        self.output_callback("\n   -> Merging session_ids.json from V5 and V7...")
        v5_session_data = self._load_json(v5_path / 'session_ids.json')
        v7_session_data = self._load_json(v7_path / 'session_ids.json')

        merged_sessions_list = []
        seen_session_keys = set() 

        # Process V5 sessions (from 'sessions' categorized dict)
        if v5_session_data and 'data' in v5_session_data and 'sessions' in v5_session_data['data']:
            for session_type_key, sessions_list in v5_session_data['data']['sessions'].items():
                if isinstance(sessions_list, list):
                    for item in sessions_list:
                        if 'value' in item and 'type' in item:
                            session_key = (item['value'], item['type'])
                            if session_key not in seen_session_keys:
                                merged_sessions_list.append(item)
                                seen_session_keys.add(session_key)
        
        # Process V7 sessions (from 'all_found_sessions' dict)
        if v7_session_data and 'data' in v7_session_data and 'all_found_sessions' in v7_session_data['data']:
            for session_value, session_details in v7_session_data['data']['all_found_sessions'].items():
                standardized_item = {
                    'type': session_details.get('type', 'unknown'),
                    'value': session_value,
                    'pattern': session_details.get('pattern', 'N/A'),
                    'found_in': ', '.join(session_details.get('sources', ['unknown'])),
                    'timestamp': session_details.get('first_seen', datetime.now().isoformat()),
                    'confidence': session_details.get('confidence', 0)
                }
                session_key = (standardized_item['value'], standardized_item['type'])
                if session_key not in seen_session_keys:
                    merged_sessions_list.append(standardized_item)
                    seen_session_keys.add(session_key)

        # Process V7 sessions (from 'all_session_ids_for_user' list)
        if v7_session_data and 'data' in v7_session_data and 'all_session_ids_for_user' in v7_session_data['data']:
            for item in v7_session_data['data']['all_session_ids_for_user']:
                if 'session_id' in item and 'type' in item:
                    # Standardize 'session_id' to 'value' for consistency
                    standardized_item = {
                        'type': item.get('type', 'unknown'),
                        'value': item['session_id'],
                        'pattern': item.get('pattern', 'N/A'),
                        'found_in': ', '.join(item.get('sources', ['unknown'])),
                        'timestamp': item.get('first_seen', datetime.now().isoformat()),
                        'confidence': item.get('confidence', 0)
                    }
                    session_key = (standardized_item['value'], standardized_item['type'])
                    if session_key not in seen_session_keys:
                        merged_sessions_list.append(standardized_item)
                        seen_session_keys.add(session_key)

        # Create final merged session document
        final_session_doc = {
            "forensic_metadata": {
                "extraction_timestamp": datetime.now().isoformat(),
                "tool_version": "Master Extractor v1.0",
                "merger_notes": "Combined and deduplicated session data from V5 and V7 extractors.",
                "case_info": self.case_info
            },
            "data": {
                "description": "Combined and deduplicated session identifiers and authentication tokens from V5 and V7 extractions",
                "primary_instagram_session_id": (v7_session_data.get('data', {}).get('primary_instagram_session_id') if v7_session_data else None) or \
                                                (v5_session_data.get('data', {}).get('primary_instagram_session_id') if v5_session_data else None),
                "logged_in_user_id": (v7_session_data.get('data', {}).get('logged_in_user_id') if v7_session_data else None) or \
                                     (v5_session_data.get('data', {}).get('logged_in_user_id') if v5_session_data else None),
                "all_unique_sessions": merged_sessions_list,
                "total_sessions_found": len(merged_sessions_list)
            }
        }
        self._save_final_json(final_session_doc, 'session_ids.json')
        self.consolidated_report["merged_files"]["session_ids"] = final_session_doc['data']
        self.consolidated_report["summary"]["total_sessions_found"] = len(merged_sessions_list)
        self.output_callback("   ✅ Merged session_ids.json saved.")

        # 3. Merge common files (logged_in_user_profile, complete_folder_analysis, extraction_report)
        self.output_callback("\n   -> Merging common files...")
        v5_profile_data = self._load_json(v5_path / 'logged_in_user_profile.json')
        v7_profile_data = self._load_json(v7_path / 'logged_in_user_profile.json')
        v5_report = self._load_json(v5_path / 'extraction_report.json')
        v7_report = self._load_json(v7_path / 'extraction_report.json')
        v5_analysis = self._load_json(v5_path / 'complete_folder_analysis.json')
        v7_analysis = self._load_json(v7_path / 'complete_folder_analysis.json')

        # Intelligently merge the logged-in user profiles
        self.output_callback("   -> Intelligently merging user profiles...")
        v5_profile = v5_profile_data.get('data', {}).get('logged_in_user', {}) if v5_profile_data else {}
        v7_profile = v7_profile_data.get('data', {}).get('logged_in_user', {}) if v7_profile_data else {}
        intelligently_merged_profile = self._intelligent_merge_profiles(v5_profile, v7_profile)

        # Get the summary from the most complete profile (likely V7)
        final_summary = (v7_profile_data.get('data', {}).get('extraction_summary', {})) if v7_profile_data else (v5_profile_data.get('data', {}).get('extraction_summary', {}))

        final_profile_doc = {
            "forensic_metadata": {
                "extraction_timestamp": datetime.now().isoformat(),
                "tool_version": "Master Extractor v1.0",
                "merger_notes": "Intelligently merged from V5 and V7. V7 data is prioritized for details, highest values for counts, and lists are combined.",
                "case_info": self.case_info
            },
            "data": {
                "logged_in_user": intelligently_merged_profile,
                "extraction_summary": final_summary
            }
        }
        self._save_final_json(final_profile_doc, 'logged_in_user_profile.json')
        self.consolidated_report["merged_files"]["logged_in_user_profile"] = final_profile_doc['data']
        self.consolidated_report["summary"]["total_users_analyzed"] = 1 if intelligently_merged_profile else 0

        # Merge Complete Folder Analysis
        merged_analysis = v5_analysis['data'] if v5_analysis and 'data' in v5_analysis else {}
        if v7_analysis and 'data' in v7_analysis:
            merged_analysis = self._deep_merge_dicts(merged_analysis, v7_analysis['data'])
        final_analysis_doc = {
            "forensic_metadata": {
                "extraction_timestamp": datetime.now().isoformat(),
                "tool_version": "Master Extractor v1.0",
                "merger_notes": "Merged from V5 and V7 folder analysis.",
                "case_info": self.case_info
            },
            "data": merged_analysis
        }
        self._save_final_json(final_analysis_doc, 'complete_folder_analysis.json')
        self.consolidated_report["merged_files"]["complete_folder_analysis"] = final_analysis_doc['data']

        # Create new combined Extraction Report
        final_report = {
            "forensic_metadata": {
                "extraction_timestamp": datetime.now().isoformat(),
                "tool_version": "Master Extractor v1.0",
                "merger_notes": "Combined report from V5 and V7 extractor runs.",
                "case_info": self.case_info
            },
            "data": {
                "v5_report_summary": v5_report['data'] if v5_report else "Not available",
                "v7_report_summary": v7_report['data'] if v7_report else "Not available",
                "final_user_profile_summary": final_summary
            }
        }
        self._save_final_json(final_report, 'extraction_report.json')
        self.consolidated_report["merged_files"]["extraction_report"] = final_report['data']

        # 4. Create the new master.json
        self.output_callback("\n   -> Creating master.json summary...")
        master_data = {
            "master_summary": "High-level summary from both V5 and V7 extractions.",
            "user_profile": intelligently_merged_profile,
            "key_session_info": {
                "primary_session_id": intelligently_merged_profile.get('primary_instagram_session_id'),
                "total_sessions_found": len(merged_sessions_list),
            },
            "data_summary": {
                "chats_found": len(self.consolidated_report["merged_files"]["chats"]),
                "media_found": len(self.consolidated_report["merged_files"]["media"]),
                "chat_media_found": len(self.consolidated_report["merged_files"]["chat_media"]),
            },
            "report_location": str(self.final_output_dir / 'extraction_report.json')
        }
        final_master_doc = {
            "forensic_metadata": {
                "extraction_timestamp": datetime.now().isoformat(),
                "tool_version": "Master Extractor v1.0",
                "case_info": self.case_info
            },
            "data": master_data
        }
        self._save_final_json(final_master_doc, 'master.json')
        self.consolidated_report["merged_files"]["master"] = final_master_doc['data']

        self.output_callback(f"\n✅ Merging complete. Final report is in: {self.final_output_dir}")

    def run_extraction(self):
        """Execute the extraction and merging process."""
        sanitized_v5_path = None
        sanitized_v7_path = None
        
        try:
            self.output_callback("=== Starting Master Instagram Extraction ===")
            
            # Sanitize scripts before running to remove problematic characters
            sanitized_v5_path = self._sanitize_script(Path(V5_SCRIPT_NAME))
            sanitized_v7_path = self._sanitize_script(Path(V7_SCRIPT_NAME))

            if not sanitized_v5_path or not sanitized_v7_path:
                self.output_callback("❌ Script sanitization failed. Aborting.")
                self.consolidated_report["issues"].append("Script sanitization failed")
                return self.consolidated_report

            # Run V5 using the sanitized script
            v5_actual_output_dir = self._run_script(sanitized_v5_path.name, self.v5_output_dir)
            if v5_actual_output_dir:
                self.consolidated_report["v5_report"]["status"] = "success"
            else:
                self.output_callback("❌ V5 script failed to run.")
                self.consolidated_report["v5_report"]["status"] = "failed"
                self.consolidated_report["issues"].append("V5 script execution failed")

            # Run V7 using the sanitized script
            v7_actual_output_dir = self._run_script(sanitized_v7_path.name, self.v7_output_dir)
            if v7_actual_output_dir:
                self.consolidated_report["v7_report"]["status"] = "success"
            else:
                self.output_callback("❌ V7 script failed to run.")
                self.consolidated_report["v7_report"]["status"] = "failed"
                self.consolidated_report["issues"].append("V7 script execution failed")

            # Merge results if at least one succeeded
            if v5_actual_output_dir or v7_actual_output_dir:
                self.merge_and_generate_reports(
                    v5_actual_output_dir or Path(), 
                    v7_actual_output_dir or Path()
                )
            
            self.output_callback("=== Master Instagram Extraction Complete ===")
            
            return self.consolidated_report
            
        except Exception as e:
            error_msg = f"Master extractor execution failed: {e}\n{traceback.format_exc()}"
            self.output_callback(f"❌ {error_msg}")
            self.consolidated_report["issues"].append(f"Master extractor fatal error: {e}")
            return self.consolidated_report
        finally:
            # Cleanup sanitized script files (this is more critical)
            self.output_callback("🧹 Cleaning up temporary script files...")
            if sanitized_v5_path and sanitized_v5_path.exists():
                try:
                    sanitized_v5_path.unlink()
                    self.output_callback(f"   Removed {sanitized_v5_path.name}")
                except Exception as e:
                    self.output_callback(f"   ⚠️ Could not remove {sanitized_v5_path.name}: {e}")
            if sanitized_v7_path and sanitized_v7_path.exists():
                try:
                    sanitized_v7_path.unlink()
                    self.output_callback(f"   Removed {sanitized_v7_path.name}")
                except Exception as e:
                    self.output_callback(f"   ⚠️ Could not remove {sanitized_v7_path.name}: {e}")
        
            # Try cleanup but don't let it affect the main process
            try:
                self.cleanup()
            except Exception as cleanup_error:
                self.output_callback(f"   ⚠️ Cleanup encountered issues but extraction completed successfully")

    def cleanup(self):
        """Clean up temporary directories with better error handling."""
        self.output_callback("--- Cleaning up temporary files ---")
        
        # Wait a moment for any file handles to be released
        time.sleep(2)
        
        # Clean up temporary output directories
        for temp_dir in [self.v5_output_dir, self.v7_output_dir]:
            if temp_dir.exists():
                try:
                    # Try a simple removal first
                    shutil.rmtree(temp_dir)
                    self.output_callback(f"🗑️ Removed temporary directory: {temp_dir.name}")
                except OSError as e:
                    # If simple removal fails, try alternative approaches
                    self.output_callback(f"   ⚠️ Standard removal failed for {temp_dir.name}, trying alternative cleanup...")
                    
                    # Try to make the directory and all contents writable
                    try:
                        for root, dirs, files in os.walk(temp_dir):
                            for d in dirs:
                                try:
                                    os.chmod(os.path.join(root, d), 0o777)
                                except:
                                    pass
                            for f in files:
                                try:
                                    file_path = os.path.join(root, f)
                                    os.chmod(file_path, 0o777)
                                    os.remove(file_path)
                                except:
                                    pass
                        
                        # Try to remove empty directories
                        for root, dirs, files in os.walk(temp_dir, topdown=False):
                            for d in dirs:
                                try:
                                    os.rmdir(os.path.join(root, d))
                                except:
                                    pass
                        
                        # Finally try to remove the main directory
                        os.rmdir(temp_dir)
                        self.output_callback(f"🗑️ Successfully cleaned up {temp_dir.name} using alternative method")
                        
                    except Exception as cleanup_error:
                        # If all cleanup attempts fail, just log it and continue
                        self.output_callback(f"   ⚠️ Could not fully clean up {temp_dir.name}: {cleanup_error}")
                        self.output_callback(f"   📝 Note: Temporary files remain at {temp_dir}")
                        self.output_callback(f"   💡 You can manually delete this folder later if needed")
        
        self.output_callback("--- Cleanup Complete ---")


def main():
    """Main function for command-line execution."""
    print("=" * 60)
    print("      MASTER INSTAGRAM EXTRACTOR ORCHESTRATOR")
    print("=" * 60)
    print("This script will run both V5 and V7 extractors sequentially")
    print("and merge their results into a final report.")
    print("-" * 60)

    # Get input path from user
    input_path_str = input("📂 Enter the path to the Instagram data dump (folder or ZIP): ").strip().strip('"')
    if not Path(input_path_str).exists():
        print("❌ ERROR: The provided path does not exist.")
        return

    # Optional: Get case info from user
    print("\n📋 Case Information (optional, press Enter to skip):")
    case_number = input("   Case Number: ").strip()
    examiner_name = input("   Examiner Name: ").strip()
    evidence_item = input("   Evidence Item: ").strip()

    case_info = {
        "case_number": case_number,
        "examiner": examiner_name,
        "evidence_item": evidence_item
    }

    # Initialize and run the master extractor
    master = MasterExtractor(input_path_str, case_info)
    result = master.run_extraction()
    
    if result.get("issues"):
        print("Extraction completed with issues:")
        for issue in result["issues"]:
            print(f"  - {issue}")
    else:
        print("Extraction completed successfully!")

    print(f"\n📂 Your final, merged report is located in:")
    print(f"   {master.final_output_dir.resolve()}")


if __name__ == "__main__":
    main()
