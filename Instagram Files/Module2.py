#!/usr/bin/env python3
"""
Instagram Data Extractor v7.0 - Ultimate User Focus
Specialized in aggressive extraction of user IDs, followers, following counts, and session IDs
"""

import os
import json
import sqlite3
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import base64
import hashlib
import logging
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import re
from collections import defaultdict
import zipfile
import mimetypes
import traceback
import platform
import urllib.parse
import sys

# Try to import pyzipper for encrypted ZIP support
try:
    import pyzipper
    PYZIPPER_AVAILABLE = True
except ImportError:
    PYZIPPER_AVAILABLE = False
    print("Note: pyzipper not available. Encrypted ZIP support disabled.")

class InstagramDataExtractorV7:
    """
    Instagram Data Extractor Version 7.0 - Ultimate User Focus
    Specialized in aggressive extraction of user IDs, followers, following counts, and session IDs
    """
    
    def __init__(self, input_path, output_dir=None, case_info=None):
        """Initialize the Instagram Data Extractor V7"""
        self.setup_logging()
        
        self.original_input = Path(input_path)
        self.temp_extraction_dir = None
        self.is_zip_input = False
        
        # Handle ZIP file input
        if self.is_zip_file(input_path):
            print(f"📦 Detected ZIP file: {self.original_input.name}")
            self.is_zip_input = True
            self.working_folder = self.extract_zip_safely(input_path)
        else:
            self.working_folder = Path(input_path)
        
        # Setup output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path.cwd() / "instagram_extraction_v7_output"
        
        self.output_dir.mkdir(exist_ok=True)
        
        # Create JSON folders structure
        self.json_folders_dir = self.output_dir / "json_folders"
        self.json_folders_dir.mkdir(exist_ok=True)

        # Create user data directory
        self.user_data_dir = self.output_dir / "user_data"
        self.user_data_dir.mkdir(exist_ok=True)
        
        # Case information
        self.case_info = case_info or {}
        self.case_info.update({
            "extraction_start": datetime.now().isoformat(),
            "tool_version": "7.0-Ultimate-User-Focus",
            "input_type": "ZIP file" if self.is_zip_input else "Folder",
            "original_source": str(self.original_input),
            "extractor": "Instagram Data Extractor V7 - Ultimate User Focus"
        })
        
        # Data containers
        self.instagram_folder = None
        
        # Complete file system structure
        self.file_system_structure = {
            "folders": {},
            "total_files": 0,
            "total_folders": 0,
            "file_types": defaultdict(int),
            "folder_summary": {}
        }
        
        # Session data tracking
        self.session_data = {
            "instagram_sessions": [],
            "facebook_sessions": [],
            "auth_tokens": [],
            "device_sessions": [],
            "csrf_tokens": [],
            "user_identifiers": [],
            "api_keys": [],
            "other_sessions": [],
            "cookie_sessions": [],
            "jwt_tokens": [],
            "oauth_tokens": [],
            "refresh_tokens": []
        }
        
        # MAIN USER PROFILE DATA - Focus on the logged-in user
        self.logged_in_user = {
            "user_id": None, 
            "username": None,
            "full_name": None,
            "email": None,
            "phone_number": None,
            "profile_picture_url": None,
            "bio": None,
            "website": None,
            "is_private": None,
            "is_verified": None,
            "followers_count": 0,
            "following_count": 0,
            "posts_count": 0,
            "linked_facebook_accounts": [],
            "primary_instagram_session_id": None,
            "device_info": {},
            "account_creation_date": None,
            "last_login": None,
            "profile_picture_paths": [],
            "posts_media_metadata": [],
            "stories_media_metadata": [],
            "pending_incoming_requests_count": 0,
            "pending_outgoing_requests_count": 0,
            "authentication_details": {},
            "privacy_settings": {},
            "notification_settings": {},
            "other_user_details": {},
            "user_id_confidence": 0,
            "user_id_source": "Not identified",
            "all_session_ids": [],  # Store all found session IDs
            "extraction_sources": [],  # Track where data was found
            "discovery_timeline": []  # Track when data was discovered
        }
        
        # ULTRA-AGGRESSIVE tracking for user data discovery
        self._all_found_user_ids = {}  # user_id -> {count, sources, confidence, first_seen}
        self._all_found_usernames = {}  # username -> {count, sources, first_seen}
        self._all_found_emails = {}  # email -> {count, sources, first_seen}
        self._all_found_session_ids = {}  # session_id -> {count, sources, first_seen, type}
        self._follower_following_data = []  # All follower/following relationships
        self._follower_count_sources = []  # Track all sources of follower counts
        self._following_count_sources = []  # Track all sources of following counts
        self._posts_count_sources = []  # Track all sources of posts counts
        
        # Complete extracted data organized by folders
        self.folder_data = {}
        
        # All errors
        self.errors = []
        
        # ULTRA-AGGRESSIVE PATTERN MATCHING
        
        # User ID patterns - EXPANDED
        self.user_id_patterns = [
            # Direct user ID patterns
            r'"user_id":\s*"?([0-9]{5,})"?',
            r'"id":\s*"?([0-9]{5,})"?',
            r'"pk":\s*"?([0-9]{5,})"?',
            r'user_id["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            r'ds_user_id["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            r'c_user["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            r'owner_id["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            r'account_id["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            r'profile_id["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            r'uid["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            r'userid["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            r'user_pk["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            r'viewer_id["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            r'actor_id["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            r'self_id["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            r'my_id["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            # Database field patterns
            r'PRIMARY KEY.*?([0-9]{5,})',
            r'UNIQUE.*?([0-9]{5,})',
            # URL patterns
            r'\/users\/([0-9]{5,})\/',
            r'user_id=([0-9]{5,})',
            r'userid=([0-9]{5,})',
            r'uid=([0-9]{5,})',
            # JSON patterns
            r'"userId":\s*"?([0-9]{5,})"?',
            r'"user":\s*\{[^\}]*"id":\s*"?([0-9]{5,})"?',
            r'"viewer":\s*\{[^\}]*"id":\s*"?([0-9]{5,})"?',
            r'"owner":\s*\{[^\}]*"id":\s*"?([0-9]{5,})"?',
            r'"profile":\s*\{[^\}]*"id":\s*"?([0-9]{5,})"?',
        ]
        
        # Username patterns - EXPANDED
        self.username_patterns = [
            r'"username":\s*"([a-zA-Z0-9\._]{3,30})"',
            r'username["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\._]{3,30})["\']?',
            r'@([a-zA-Z0-9\._]{3,30})',
            r'instagram\.com/([a-zA-Z0-9\._]{3,30})/?',
            r'ig\.me/([a-zA-Z0-9\._]{3,30})',
            r'insta\.gram/([a-zA-Z0-9\._]{3,30})',
            r'"user":\s*\{[^\}]*"username":\s*"([a-zA-Z0-9\._]{3,30})"',
            r'"viewer":\s*\{[^\}]*"username":\s*"([a-zA-Z0-9\._]{3,30})"',
            r'"owner":\s*\{[^\}]*"username":\s*"([a-zA-Z0-9\._]{3,30})"',
            r'"profile":\s*\{[^\}]*"username":\s*"([a-zA-Z0-9\._]{3,30})"',
            r'user_name["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\._]{3,30})["\']?',
            r'userName["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\._]{3,30})["\']?',
            r'login["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\._]{3,30})["\']?',
            r'account_name["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\._]{3,30})["\']?',
        ]
        
        # Session ID patterns - EXPANDED
        self.session_id_patterns = [
            # Instagram session patterns
            r'sessionid["\']?\s*[:=]\s*["\']?([a-zA-Z0-9%\-_\.]{10,})["\']?',
            r'csrftoken["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{10,})["\']?',
            r'ds_user_id["\']?\s*[:=]\s*["\']?([0-9]{5,})["\']?',
            r'shbid["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{10,})["\']?',
            r'mid["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{10,})["\']?',
            r'ig_did["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{10,})["\']?',
            # Cookie patterns
            r'Cookie:.*?sessionid=([a-zA-Z0-9%\-_\.]{10,})',
            r'Set-Cookie:.*?sessionid=([a-zA-Z0-9%\-_\.]{10,})',
            # URL patterns
            r'instagram\.com.*?sessionid=([a-zA-Z0-9%\-_\.]{10,})',
            # JSON patterns
            r'"session_id":\s*"([a-zA-Z0-9%\-_\.]{10,})"',
            r'"sessionId":\s*"([a-zA-Z0-9%\-_\.]{10,})"',
            r'"session":\s*\{[^\}]*"id":\s*"([a-zA-Z0-9%\-_\.]{10,})"',
            # Database patterns
            r'INSERT INTO\s+sessions.*?VALUES.*?[\'"]([a-zA-Z0-9%\-_\.]{10,})[\'"]',
            r'UPDATE\s+sessions.*?SET.*?[\'"]([a-zA-Z0-9%\-_\.]{10,})[\'"]',
        ]
        
        # Count patterns - EXPANDED
        self.count_patterns = [
            # Follower count patterns
            r'"follower_count":\s*"?([0-9]+)"?',
            r'"followers_count":\s*"?([0-9]+)"?',
            r'"followers":\s*"?([0-9]+)"?',
            r'follower_count["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'followers["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'followerCount["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'follower_cnt["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'followers_cnt["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'"user":\s*\{[^\}]*"follower_count":\s*([0-9]+)',
            r'"profile":\s*\{[^\}]*"followers":\s*([0-9]+)',
            # Following count patterns
            r'"following_count":\s*"?([0-9]+)"?',
            r'"followings_count":\s*"?([0-9]+)"?',
            r'"following":\s*"?([0-9]+)"?',
            r'following_count["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'following["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'followingCount["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'following_cnt["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'followings_cnt["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'"user":\s*\{[^\}]*"following_count":\s*([0-9]+)',
            r'"profile":\s*\{[^\}]*"following":\s*([0-9]+)',
            # Media/Posts count patterns
            r'"media_count":\s*"?([0-9]+)"?',
            r'"posts_count":\s*"?([0-9]+)"?',
            r'"posts":\s*"?([0-9]+)"?',
            r'media_count["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'posts["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'postCount["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'post_count["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'media_cnt["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'posts_cnt["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
            r'"user":\s*\{[^\}]*"media_count":\s*([0-9]+)',
            r'"profile":\s*\{[^\}]*"posts":\s*([0-9]+)',
        ]
        
        # User profile tables - tables that likely contain user profile information
        self.user_profile_tables = [
            'users', 'user_info', 'profile', 'profiles', 'accounts', 'account_info',
            'user_settings', 'user_profile', 'user_profiles', 'user_data',
            'self_profile', 'current_user', 'my_account', 'account_info',
            'user', 'profile_info', 'account', 'auth_user', 'instagram_user',
            'user_metadata', 'profile_metadata', 'account_metadata',
            'user_stats', 'profile_stats', 'account_stats',
            'user_details', 'profile_details', 'account_details',
            'user_config', 'profile_config', 'account_config',
            'user_preferences', 'profile_preferences', 'account_preferences',
            'user_state', 'profile_state', 'account_state',
            'user_status', 'profile_status', 'account_status',
            'user_record', 'profile_record', 'account_record',
            'user_entry', 'profile_entry', 'account_entry',
            'user_summary', 'profile_summary', 'account_summary',
            'user_information', 'profile_information', 'account_information',
            'user_counts', 'profile_counts', 'account_counts',
            'user_metrics', 'profile_metrics', 'account_metrics',
            'user_analytics', 'profile_analytics', 'account_analytics',
            'user_statistics', 'profile_statistics', 'account_statistics',
            'instagram_profile', 'instagram_account', 'ig_user', 'ig_profile',
            'ig_account', 'insta_user', 'insta_profile', 'insta_account'
        ]
        
        self.logger.info(f"Instagram Data Extractor V7 initialized for: {self.original_input}")
    
    def setup_logging(self):
        """Setup logging system"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logs_dir = Path.cwd() / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(logs_dir / f"instagram_v7_ultimate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger("InstagramDataExtractorV7")
    
    def is_zip_file(self, file_path):
        """Detect if input is a ZIP file"""
        path = Path(file_path)
        
        if not path.exists() or not path.is_file():
            return False
        
        if path.suffix.lower() in ['.zip', '.7z']:
            return True
        
        try:
            with open(path, 'rb') as f:
                signature = f.read(4)
                return signature in [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08']
        except Exception:
            return False
    
    def safe_path_create(self, zip_path, base_temp_path):
        """Create Windows-safe extraction paths"""
        safe_path = zip_path.replace('\\', '/').replace('//', '/')
        parts = safe_path.split('/')
        safe_parts = []
        
        for part in parts:
            if len(part) > 50:
                hash_part = hashlib.md5(part.encode()).hexdigest()[:8]
                safe_part = f"{part[:20]}_{hash_part}_{part[-20:]}"
                safe_parts.append(safe_part)
            else:
                safe_parts.append(part)
        
        safe_relative = '/'.join(safe_parts)
        full_path = os.path.join(base_temp_path, safe_relative.replace('/', os.sep))
        
        if len(full_path) > 200:
            path_hash = hashlib.md5(zip_path.encode()).hexdigest()
            filename = os.path.basename(zip_path)[:50]
            safe_relative = f"long_paths/{path_hash[:8]}/{filename}"
            full_path = os.path.join(base_temp_path, safe_relative.replace('/', os.sep))
        
        return full_path
    
    def extract_zip_safely(self, zip_path):
        """Extract ZIP file with Windows path length handling"""
        print(f"📦 Extracting ZIP file: {Path(zip_path).name}")
        
        try:
            self.temp_extraction_dir = tempfile.mkdtemp(prefix="instagram_extract_")
            temp_path = Path(self.temp_extraction_dir)
            
            print(f"📁 Extraction directory: {temp_path}")
            
            zip_size = os.path.getsize(zip_path)
            print(f"📊 ZIP size: {zip_size / (1024*1024):.2f} MB")
            
            extracted_count = 0
            skipped_count = 0
            
            if PYZIPPER_AVAILABLE:
                try:
                    with pyzipper.AESZipFile(zip_path, 'r') as zipf:
                        file_list = zipf.namelist()
                        print(f"📋 Files in ZIP: {len(file_list)}")
                        
                        for i, file_info in enumerate(zipf.infolist()):
                            if i % 2000 == 0 and i > 0:
                                print(f"📊 Progress: {i}/{len(file_list)} ({extracted_count} extracted, {skipped_count} skipped)")
                            
                            if file_info.filename.endswith('/'):
                                continue
                            
                            try:
                                safe_path = self.safe_path_create(file_info.filename, str(temp_path))
                                os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                                
                                with zipf.open(file_info) as source, open(safe_path, 'wb') as target:
                                    shutil.copyfileobj(source, target)
                                extracted_count += 1
                                
                            except Exception as e:
                                skipped_count += 1
                                if skipped_count <= 5:
                                    print(f"⚠️ Skipped: {file_info.filename[:50]}... ({str(e)[:50]})")
                        
                        print(f"✅ Extraction complete: {extracted_count} files extracted, {skipped_count} skipped")
                        return temp_path
                        
                except Exception as e:
                    print(f"⚠️ pyzipper failed: {e}")
            
            # Fallback to standard zipfile
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                file_list = zipf.namelist()
                print(f"📋 Files in ZIP: {len(file_list)}")
                
                for i, file_info in enumerate(zipf.infolist()):
                    if i % 2000 == 0 and i > 0:
                        print(f"📊 Progress: {i}/{len(file_list)} ({extracted_count} extracted, {skipped_count} skipped)")
                    
                    if file_info.filename.endswith('/'):
                        continue
                    
                    try:
                        safe_path = self.safe_path_create(file_info.filename, str(temp_path))
                        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                        
                        with zipf.open(file_info) as source, open(safe_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                        extracted_count += 1
                        
                    except Exception as e:
                        skipped_count += 1
                        if skipped_count <= 5:
                            print(f"⚠️ Skipped: {file_info.filename[:50]}... ({str(e)[:50]})")
        
            print(f"✅ Extraction complete: {extracted_count} files extracted, {skipped_count} skipped")
            return temp_path
            
        except Exception as e:
            error_msg = f"ZIP extraction failed: {e}"
            print(f"❌ {error_msg}")
            self.logger.error(error_msg)
            
            if self.temp_extraction_dir and os.path.exists(self.temp_extraction_dir):
                shutil.rmtree(self.temp_extraction_dir, ignore_errors=True)
            
            raise RuntimeError(error_msg)
    
    def find_instagram_folder(self):
        """Intelligently locate Instagram app folder"""
        print("\n🎯 Locating Instagram folder...")
        
        candidates = []
        
        # Strategy 1: Look for databases folder with Instagram DBs
        for path in self.working_folder.rglob('databases'):
            if path.is_dir():
                db_files = list(path.glob('*.db'))
                instagram_dbs = []
                
                for db in db_files:
                    if any(keyword in db.name.lower() for keyword in 
                          ['direct', 'recent_searches', 'crypto', 'reverb', 'instagram']):
                        instagram_dbs.append(db)
                
                if instagram_dbs:
                    score = len(instagram_dbs) * 10
                    candidates.append((path.parent, score, "databases_folder", instagram_dbs))
                    print(f"✅ Databases folder: {path} ({len(instagram_dbs)} Instagram DBs)")
        
        # Strategy 2: Look for Instagram app folders
        app_patterns = ['com.instagram.android', 'instagram', 'Instagram']
        
        for pattern in app_patterns:
            for path in self.working_folder.rglob(pattern):
                if path.is_dir():
                    db_count = len(list(path.rglob('*.db')))
                    xml_count = len(list(path.rglob('*.xml')))
                    html_count = len(list(path.rglob('*.html')))
                    
                    total_files = db_count + xml_count + html_count
                    
                    if total_files > 0:
                        pattern_scores = {
                            'com.instagram.android': 8,
                            'instagram': 6,
                            'Instagram': 4
                        }
                        score = pattern_scores.get(pattern, 2) + total_files
                        candidates.append((path, score, f"app_folder_{pattern}", []))
                        print(f"✅ App folder: {path} ({db_count} DBs, {xml_count} XMLs, {html_count} HTMLs)")
        
        # Strategy 3: Look for folders containing Instagram databases
        for db_file in self.working_folder.rglob('*.db'):
            if any(keyword in db_file.name.lower() for keyword in ['instagram', 'direct', 'recent_searches']):
                parent_dir = db_file.parent.parent  # Go up two levels to get app folder
                if not any(candidate[0] == parent_dir for candidate in candidates):
                    db_count = len(list(parent_dir.rglob('*.db')))
                    score = db_count + 2
                    candidates.append((parent_dir, score, "db_parent", [db_file]))
                    print(f"✅ DB parent folder: {parent_dir}")
        
        # Select best candidate
        if candidates:
            best_candidate = max(candidates, key=lambda x: x[1])
            selected_path = best_candidate[0]
            
            print(f"\n🎯 Selected Instagram folder: {selected_path}")
            print(f"   Strategy: {best_candidate[2]}")
            print(f"   Score: {best_candidate[1]}")
            
            self.logger.info(f"Selected Instagram folder: {selected_path}")
            return selected_path
        
        print("⚠️ No Instagram folder found, analyzing entire directory")
        return self.working_folder
    
    def ultra_aggressive_user_data_extraction(self, content, source_info):
        """ULTRA-AGGRESSIVE extraction of user data from any content"""
        if not isinstance(content, str) or len(content) < 10:
            return
        
        source_desc = f"{source_info.get('type', 'unknown')}:{source_info.get('file', 'unknown')}"
        timestamp = datetime.now().isoformat()
        
        print(f"🔍 ULTRA-AGGRESSIVE SCAN: {source_desc}")
        
        # 1. EXTRACT ALL USER IDs with real-time feedback
        for pattern in self.user_id_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else (match[1] if len(match) > 1 else '')
                
                if match and str(match).isdigit() and len(str(match)) >= 5:
                    user_id = str(match)
                    if user_id not in self._all_found_user_ids:
                        self._all_found_user_ids[user_id] = {
                            'count': 0, 
                            'sources': [], 
                            'confidence': 0, 
                            'first_seen': timestamp
                        }
                    
                    self._all_found_user_ids[user_id]['count'] += 1
                    self._all_found_user_ids[user_id]['sources'].append(source_desc)
                    self._all_found_user_ids[user_id]['confidence'] += 10
                    
                    print(f"🆔 FOUND USER ID: {user_id} in {source_desc} (Count: {self._all_found_user_ids[user_id]['count']})")
        
        # 2. EXTRACT ALL SESSION IDs with real-time feedback
        for pattern in self.session_id_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(str(match)) >= 10:
                    session_id = str(match)
                    if session_id not in self._all_found_session_ids:
                        self._all_found_session_ids[session_id] = {
                            'count': 0, 
                            'sources': [], 
                            'first_seen': timestamp,
                            'type': 'session_token'
                        }
                    
                    self._all_found_session_ids[session_id]['count'] += 1
                    self._all_found_session_ids[session_id]['sources'].append(source_desc)
                    
                    print(f"🔑 FOUND SESSION ID: {session_id[:20]}... in {source_desc} (Count: {self._all_found_session_ids[session_id]['count']})")
        
        # 3. EXTRACT USERNAMES with real-time feedback
        for pattern in self.username_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) >= 3 and not match.isdigit():
                    username = str(match).lower()
                    if username not in self._all_found_usernames:
                        self._all_found_usernames[username] = {
                            'count': 0, 
                            'sources': [], 
                            'first_seen': timestamp
                        }
                    
                    self._all_found_usernames[username]['count'] += 1
                    self._all_found_usernames[username]['sources'].append(source_desc)
                    
                    print(f"👤 FOUND USERNAME: {username} in {source_desc} (Count: {self._all_found_usernames[username]['count']})")
        
        # 4. EXTRACT COUNTS with real-time feedback and source tracking
        for pattern in self.count_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if str(match).isdigit():
                    count_value = int(match)
                    if 'follower' in pattern.lower():
                        self._follower_count_sources.append({
                            'count': count_value,
                            'source': source_desc,
                            'timestamp': timestamp,
                            'pattern': pattern
                        })
                        if count_value > self.logged_in_user['followers_count']:
                            self.logged_in_user['followers_count'] = count_value
                            print(f"👥 FOUND FOLLOWERS COUNT: {count_value} in {source_desc}")
                    elif 'following' in pattern.lower():
                        self._following_count_sources.append({
                            'count': count_value,
                            'source': source_desc,
                            'timestamp': timestamp,
                            'pattern': pattern
                        })
                        if count_value > self.logged_in_user['following_count']:
                            self.logged_in_user['following_count'] = count_value
                            print(f"👤 FOUND FOLLOWING COUNT: {count_value} in {source_desc}")
                    elif any(word in pattern.lower() for word in ['media', 'post']):
                        self._posts_count_sources.append({
                            'count': count_value,
                            'source': source_desc,
                            'timestamp': timestamp,
                            'pattern': pattern
                        })
                        if count_value > self.logged_in_user['posts_count']:
                            self.logged_in_user['posts_count'] = count_value
                            print(f"📸 FOUND POSTS COUNT: {count_value} in {source_desc}")
        
        # 5. EXTRACT EMAILS with real-time feedback
        email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        email_matches = re.findall(email_pattern, content, re.IGNORECASE)
        for email in email_matches:
            if email not in self._all_found_emails:
                self._all_found_emails[email] = {
                    'count': 0, 
                    'sources': [], 
                    'first_seen': timestamp
                }
            
            self._all_found_emails[email]['count'] += 1
            self._all_found_emails[email]['sources'].append(source_desc)
            
            print(f"📧 FOUND EMAIL: {email} in {source_desc} (Count: {self._all_found_emails[email]['count']})")
        
        # 6. EXTRACT FOLLOWER/FOLLOWING RELATIONSHIPS with real-time feedback
        relationship_patterns = [
            r'"follower_id":\s*"?([0-9]+)"?.*?"followed_id":\s*"?([0-9]+)"?',
            r'"from_user_id":\s*"?([0-9]+)"?.*?"to_user_id":\s*"?([0-9]+)"?',
            r'follower_id["\']?\s*[:=]\s*["\']?([0-9]+)["\']?.*?followed_id["\']?\s*[:=]\s*["\']?([0-9]+)["\']?',
        ]
        
        for pattern in relationship_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if len(match) == 2 and all(str(m).isdigit() for m in match):
                    follower_id, followed_id = str(match[0]), str(match[1])
                    relationship = {
                        'follower_id': follower_id,
                        'followed_id': followed_id,
                        'source': source_desc,
                        'timestamp': timestamp,
                        'type': 'follow_relationship'
                    }
                    self._follower_following_data.append(relationship)
                    print(f"👥 FOUND RELATIONSHIP: {follower_id} follows {followed_id} in {source_desc}")
    
    def finalize_user_data(self):
        """Finalize user data from all collected information with detailed analysis"""
        print(f"\n🎯 FINALIZING USER DATA WITH DETAILED ANALYSIS...")
        print(f"   Found {len(self._all_found_user_ids)} unique user IDs")
        print(f"   Found {len(self._all_found_usernames)} unique usernames")
        print(f"   Found {len(self._all_found_emails)} unique emails")
        print(f"   Found {len(self._all_found_session_ids)} unique session IDs")
        print(f"   Found {len(self._follower_following_data)} follower/following relationships")
        print(f"   Found {len(self._follower_count_sources)} follower count sources")
        print(f"   Found {len(self._following_count_sources)} following count sources")
        print(f"   Found {len(self._posts_count_sources)} posts count sources")
        
        # 1. DETERMINE PRIMARY USER ID with detailed analysis
        if self._all_found_user_ids:
            # Sort by confidence and count
            sorted_user_ids = sorted(
                self._all_found_user_ids.items(),
                key=lambda x: (x[1]['confidence'], x[1]['count']),
                reverse=True
            )
            
            primary_user_id, primary_data = sorted_user_ids[0]
            self.logged_in_user['user_id'] = primary_user_id
            self.logged_in_user['user_id_confidence'] = primary_data['confidence']
            self.logged_in_user['user_id_source'] = f"Aggregated from {len(primary_data['sources'])} sources"
            
            print(f"\n🆔 PRIMARY USER ID ANALYSIS:")
            print(f"   Selected: {primary_user_id}")
            print(f"   Confidence: {primary_data['confidence']}")
            print(f"   Found in {len(primary_data['sources'])} sources")
            print(f"   First seen: {primary_data['first_seen']}")
            print(f"   Sources: {', '.join(primary_data['sources'][:5])}...")
            
            # Show top 5 candidates
            print(f"\n   Top 5 User ID Candidates:")
            for i, (uid, data) in enumerate(sorted_user_ids[:5]):
                print(f"   {i+1}. {uid} (Confidence: {data['confidence']}, Count: {data['count']})")
        
        # 2. DETERMINE PRIMARY USERNAME with detailed analysis
        if self._all_found_usernames:
            sorted_usernames = sorted(
                self._all_found_usernames.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )
            
            primary_username, username_data = sorted_usernames[0]
            self.logged_in_user['username'] = primary_username
            
            print(f"\n👤 PRIMARY USERNAME ANALYSIS:")
            print(f"   Selected: {primary_username}")
            print(f"   Found {username_data['count']} times")
            print(f"   First seen: {username_data['first_seen']}")
            
            # Show top 5 candidates
            print(f"\n   Top 5 Username Candidates:")
            for i, (username, data) in enumerate(sorted_usernames[:5]):
                print(f"   {i+1}. {username} (Count: {data['count']})")
        
        # 3. DETERMINE PRIMARY EMAIL with detailed analysis
        if self._all_found_emails:
            sorted_emails = sorted(
                self._all_found_emails.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )
            
            primary_email, email_data = sorted_emails[0]
            self.logged_in_user['email'] = primary_email
            
            print(f"\n📧 PRIMARY EMAIL ANALYSIS:")
            print(f"   Selected: {primary_email}")
            print(f"   Found {email_data['count']} times")
            print(f"   First seen: {email_data['first_seen']}")
            
            # Show top 5 candidates
            print(f"\n   Top 5 Email Candidates:")
            for i, (email, data) in enumerate(sorted_emails[:5]):
                print(f"   {i+1}. {email} (Count: {data['count']})")
        
        # 4. DETERMINE PRIMARY SESSION ID with detailed analysis
        if self._all_found_session_ids:
            sorted_sessions = sorted(
                self._all_found_session_ids.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )
            
            primary_session, session_data = sorted_sessions[0]
            self.logged_in_user['primary_instagram_session_id'] = primary_session
            
            # Store all session IDs
            for session_id, data in self._all_found_session_ids.items():
                self.logged_in_user['all_session_ids'].append({
                    'session_id': session_id,
                    'count': data['count'],
                    'sources': data['sources'],
                    'first_seen': data['first_seen'],
                    'type': data['type']
                })
            
            print(f"\n🔑 PRIMARY SESSION ID ANALYSIS:")
            print(f"   Selected: {primary_session[:20]}...")
            print(f"   Found {session_data['count']} times")
            print(f"   First seen: {session_data['first_seen']}")
            print(f"   Total session IDs found: {len(self._all_found_session_ids)}")
            
            # Show top 5 candidates
            print(f"\n   Top 5 Session ID Candidates:")
            for i, (session_id, data) in enumerate(sorted_sessions[:5]):
                print(f"   {i+1}. {session_id[:20]}... (Count: {data['count']})")
        
        # 5. ANALYZE FOLLOWER/FOLLOWING COUNTS with detailed source analysis
        print(f"\n📊 COUNT ANALYSIS:")
        
        # Analyze follower counts
        if self._follower_count_sources:
            sorted_follower_counts = sorted(self._follower_count_sources, key=lambda x: x['count'], reverse=True)
            highest_follower_count = sorted_follower_counts[0]
            self.logged_in_user['followers_count'] = highest_follower_count['count']
            
            print(f"   👥 Followers Analysis:")
            print(f"      Highest count: {highest_follower_count['count']}")
            print(f"      Source: {highest_follower_count['source']}")
            print(f"      Total sources: {len(self._follower_count_sources)}")
            
            # Show top 5 follower counts
            print(f"      Top 5 Follower Counts:")
            for i, count_data in enumerate(sorted_follower_counts[:5]):
                print(f"      {i+1}. {count_data['count']} from {count_data['source']}")
        
        # Analyze following counts
        if self._following_count_sources:
            sorted_following_counts = sorted(self._following_count_sources, key=lambda x: x['count'], reverse=True)
            highest_following_count = sorted_following_counts[0]
            self.logged_in_user['following_count'] = highest_following_count['count']
            
            print(f"   👤 Following Analysis:")
            print(f"      Highest count: {highest_following_count['count']}")
            print(f"      Source: {highest_following_count['source']}")
            print(f"      Total sources: {len(self._following_count_sources)}")
            
            # Show top 5 following counts
            print(f"      Top 5 Following Counts:")
            for i, count_data in enumerate(sorted_following_counts[:5]):
                print(f"      {i+1}. {count_data['count']} from {count_data['source']}")
        
        # Analyze posts counts
        if self._posts_count_sources:
            sorted_posts_counts = sorted(self._posts_count_sources, key=lambda x: x['count'], reverse=True)
            highest_posts_count = sorted_posts_counts[0]
            self.logged_in_user['posts_count'] = highest_posts_count['count']
            
            print(f"   📸 Posts Analysis:")
            print(f"      Highest count: {highest_posts_count['count']}")
            print(f"      Source: {highest_posts_count['source']}")
            print(f"      Total sources: {len(self._posts_count_sources)}")
            
            # Show top 5 posts counts
            print(f"      Top 5 Posts Counts:")
            for i, count_data in enumerate(sorted_posts_counts[:5]):
                print(f"      {i+1}. {count_data['count']} from {count_data['source']}")
        
        # 6. CALCULATE FOLLOWER/FOLLOWING COUNTS FROM RELATIONSHIPS
        if self._follower_following_data and self.logged_in_user['user_id']:
            user_id = self.logged_in_user['user_id']
            
            # Count followers (people who follow this user)
            followers = set()
            following = set()
            
            for relationship in self._follower_following_data:
                if relationship['followed_id'] == user_id:
                    followers.add(relationship['follower_id'])
                elif relationship['follower_id'] == user_id:
                    following.add(relationship['followed_id'])
            
            print(f"\n   👥 Relationship-based Analysis:")
            print(f"      Calculated followers from relationships: {len(followers)}")
            print(f"      Calculated following from relationships: {len(following)}")
            
            # Use relationship counts if they're higher
            if len(followers) > self.logged_in_user['followers_count']:
                self.logged_in_user['followers_count'] = len(followers)
                print(f"      Updated followers count to: {len(followers)} (from relationships)")
            
            if len(following) > self.logged_in_user['following_count']:
                self.logged_in_user['following_count'] = len(following)
                print(f"      Updated following count to: {len(following)} (from relationships)")
        
        # 7. STORE ALL FINDINGS with detailed metadata
        self.logged_in_user['extraction_sources'] = {
            'all_user_ids_found': dict(self._all_found_user_ids),
            'all_usernames_found': dict(self._all_found_usernames),
            'all_emails_found': dict(self._all_found_emails),
            'all_session_ids_found': dict(self._all_found_session_ids),
            'total_relationships_found': len(self._follower_following_data),
            'follower_count_sources': self._follower_count_sources,
            'following_count_sources': self._following_count_sources,
            'posts_count_sources': self._posts_count_sources
        }
        
        # 8. CREATE DISCOVERY TIMELINE
        all_discoveries = []
        
        # Add user ID discoveries
        for uid, data in self._all_found_user_ids.items():
            all_discoveries.append({
                'type': 'user_id',
                'value': uid,
                'timestamp': data['first_seen'],
                'confidence': data['confidence']
            })
        
        # Add username discoveries
        for username, data in self._all_found_usernames.items():
            all_discoveries.append({
                'type': 'username',
                'value': username,
                'timestamp': data['first_seen'],
                'count': data['count']
            })
        
        # Add email discoveries
        for email, data in self._all_found_emails.items():
            all_discoveries.append({
                'type': 'email',
                'value': email,
                'timestamp': data['first_seen'],
                'count': data['count']
            })
        
        # Add session ID discoveries
        for session_id, data in self._all_found_session_ids.items():
            all_discoveries.append({
                'type': 'session_id',
                'value': session_id[:20] + '...',
                'timestamp': data['first_seen'],
                'count': data['count']
            })
        
        # Sort by timestamp
        all_discoveries.sort(key=lambda x: x['timestamp'])
        self.logged_in_user['discovery_timeline'] = all_discoveries
        
        print(f"\n📅 DISCOVERY TIMELINE:")
        print(f"   Total discoveries: {len(all_discoveries)}")
        if all_discoveries:
            print(f"   First discovery: {all_discoveries[0]['timestamp']}")
            print(f"   Last discovery: {all_discoveries[-1]['timestamp']}")
    
    def get_file_info(self, file_path):
        """Get comprehensive file information"""
        try:
            stat = file_path.stat()
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            file_info = {
                "name": file_path.name,
                "path": str(file_path),
                "relative_path": str(file_path.relative_to(self.instagram_folder)) if self.instagram_folder else str(file_path.relative_to(self.working_folder)),
                "size": stat.st_size,
                "size_human": self.human_readable_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "extension": file_path.suffix.lower(),
                "mime_type": mime_type,
                "hash": self.calculate_file_hash(file_path),
                "is_instagram_related": self.is_instagram_related_file(file_path),
                "view_link": None
            }
            
            # Add view_link for accessible files
            if file_path.is_file() and file_path.exists():
                file_info["view_link"] = f"file:///{file_path.resolve()}"
            
            return file_info
            
        except Exception as e:
            return {
                "name": file_path.name,
                "path": str(file_path),
                "error": str(e)
            }
    
    def human_readable_size(self, size):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def is_instagram_related_file(self, file_path):
        """Check if file is Instagram-related"""
        file_str = str(file_path).lower()
        instagram_keywords = [
            'instagram', 'direct', 'message', 'chat', 'story', 'feed',
            'media', 'photo', 'video', 'user', 'profile', 'follower',
            'following', 'search', 'recent', 'crypto', 'reverb'
        ]
        
        return any(keyword in file_str for keyword in instagram_keywords)
    
    def analyze_folder_structure(self):
        """Analyze complete folder structure"""
        print("\n📁 Analyzing complete folder structure...")
        
        def analyze_directory(directory_path, relative_path=""):
            """Recursively analyze directory structure"""
            folder_info = {
                "path": str(directory_path),
                "relative_path": relative_path,
                "name": directory_path.name,
                "files": [],
                "subfolders": {},
                "statistics": {
                    "total_files": 0,
                    "total_size": 0,
                    "file_types": defaultdict(int),
                    "instagram_files": 0
                }
            }
            
            try:
                # Process files in current directory
                for item in directory_path.iterdir():
                    if item.is_file():
                        file_info = self.get_file_info(item)
                        folder_info["files"].append(file_info)
                        
                        # Update statistics
                        folder_info["statistics"]["total_files"] += 1
                        folder_info["statistics"]["total_size"] += file_info.get("size", 0)
                        folder_info["statistics"]["file_types"][file_info.get("extension", "no_ext")] += 1
                        
                        # Update global statistics
                        self.file_system_structure["total_files"] += 1
                        self.file_system_structure["file_types"][file_info.get("extension", "no_ext")] += 1
                    
                    elif item.is_dir():
                        # Recursively analyze subdirectories
                        subfolder_relative = f"{relative_path}/{item.name}" if relative_path else item.name
                        subfolder_info = analyze_directory(item, subfolder_relative)
                        folder_info["subfolders"][item.name] = subfolder_info
                        
                        # Add subfolder statistics to current folder
                        folder_info["statistics"]["total_files"] += subfolder_info["statistics"]["total_files"]
                        folder_info["statistics"]["total_size"] += subfolder_info["statistics"]["total_size"]
                        folder_info["statistics"]["instagram_files"] += subfolder_info["statistics"]["instagram_files"]
                        
                        self.file_system_structure["total_folders"] += 1
            
            except PermissionError:
                folder_info["error"] = "Permission denied"
            except Exception as e:
                folder_info["error"] = str(e)
            
            # Convert defaultdict to regular dict for JSON serialization
            folder_info["statistics"]["file_types"] = dict(folder_info["statistics"]["file_types"])
            folder_info["statistics"]["total_size_human"] = self.human_readable_size(folder_info["statistics"]["total_size"])
            
            return folder_info
        
        # Start analysis from Instagram folder
        self.file_system_structure["folders"] = analyze_directory(self.instagram_folder)
        self.file_system_structure["file_types"] = dict(self.file_system_structure["file_types"])
        
        print(f"✅ Folder structure analysis complete:")
        print(f"   📁 Total folders: {self.file_system_structure['total_folders']}")
        print(f"   📄 Total files: {self.file_system_structure['total_files']}")
        print(f"   📊 File types: {len(self.file_system_structure['file_types'])}")
    
    def parse_sqlite_database(self, db_path):
        """Parse SQLite database with ULTRA-AGGRESSIVE user data extraction"""
        print(f"🔍 ULTRA-AGGRESSIVE DB SCAN: {db_path.name}")
        
        db_data = {
            "file_info": self.get_file_info(db_path),
            "tables": {},
            "metadata": {},
            "parsing_status": "unknown"
        }
        
        try:
            # Verify SQLite format
            with open(db_path, 'rb') as f:
                header = f.read(16)
                if not header.startswith(b'SQLite format 3'):
                    db_data["error"] = "Not a valid SQLite database"
                    db_data["parsing_status"] = "invalid_format"
                    return db_data
            
            # Connect and analyze
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Get table list
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"   📊 Tables found: {len(tables)}")
            
            # Check for user profile tables
            profile_tables = [t for t in tables if any(pt in t.lower() for pt in self.user_profile_tables)]
            if profile_tables:
                print(f"   👤 Potential user profile tables: {profile_tables}")
            
            for table in tables:
                if not re.match(r'^[a-zA-Z0-9_-]+$', table):
                    print(f"   ⚠️ Skipping invalid table name: {table}")
                    continue
                
                try:
                    # Get table structure
                    cursor.execute(f"PRAGMA table_info(`{table}`)")
                    columns_info = cursor.fetchall()
                    columns = [col[1] for col in columns_info]
                    
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                    row_count = cursor.fetchone()[0]
                    
                    print(f"   📋 Table '{table}': {len(columns)} columns, {row_count} rows")
                    
                    table_data = {
                        "columns": columns,
                        "row_count": row_count,
                        "rows": [],
                        "sample_data": []
                    }
                    
                    # ULTRA-AGGRESSIVE EXTRACTION - Get more data
                    limit = min(row_count, 20000)  # Increased limit for ultra-aggressive extraction
                    if row_count > 0:
                        cursor.execute(f"SELECT * FROM `{table}` LIMIT {limit}")
                        rows = cursor.fetchall()
                        
                        for row in rows:
                            row_dict = {}
                            for col, val in zip(columns, row):
                                processed_val = self.process_database_value(val)
                                row_dict[col] = processed_val
                                
                                # ULTRA-AGGRESSIVE SCAN of each value
                                if isinstance(processed_val, str):
                                    self.ultra_aggressive_user_data_extraction(processed_val, {
                                        'type': 'database_cell',
                                        'file': db_path.name,
                                        'table': table,
                                        'column': col
                                    })
                                elif isinstance(processed_val, dict) and processed_val.get('type') == 'decoded_text':
                                    self.ultra_aggressive_user_data_extraction(processed_val['value'], {
                                        'type': 'database_decoded',
                                        'file': db_path.name,
                                        'table': table,
                                        'column': col
                                    })
                            
                            table_data["rows"].append(row_dict)
                            
                            # ULTRA-AGGRESSIVE SCAN of entire row as JSON
                            row_json = json.dumps(row_dict, default=str)
                            self.ultra_aggressive_user_data_extraction(row_json, {
                                'type': 'database_row',
                                'file': db_path.name,
                                'table': table
                            })
                        
                        print(f"   ✅ ULTRA-AGGRESSIVELY SCANNED {len(rows)} rows from '{table}'")
                    
                    db_data["tables"][table] = table_data
                    
                except Exception as e:
                    print(f"   ❌ Error processing table '{table}': {e}")
                    db_data["tables"][table] = {"error": str(e)}
            
            conn.close()
            db_data["parsing_status"] = "success"
            print(f"✅ ULTRA-AGGRESSIVE DB SCAN complete: {db_path.name}")
            
        except Exception as e:
            error_msg = f"Database parsing failed: {e}"
            print(f"❌ {error_msg}")
            db_data["error"] = error_msg
            db_data["parsing_status"] = "error"
            self.logger.error(f"Database parsing error for {db_path}: {e}")
        
        return db_data
    
    def process_database_value(self, value):
        """Process database values with enhanced handling"""
        if isinstance(value, bytes):
            try:
                # Try to decode as UTF-8 text first
                decoded = value.decode('utf-8')
                return {
                    "type": "decoded_text",
                    "value": decoded,
                    "original_type": "bytes"
                }
            except UnicodeDecodeError:
                # Handle binary data
                if len(value) > 100:
                    return {
                        "type": "binary_data",
                        "size_bytes": len(value),
                        "preview": f"Binary data ({len(value)} bytes)",
                        "hash": hashlib.md5(value).hexdigest()
                    }
                else:
                    return {
                        "type": "binary_small",
                        "value": base64.b64encode(value).decode('utf-8'),
                        "size": len(value)
                    }
        
        elif isinstance(value, (int, str)):
            # Try timestamp conversion
            timestamp_result = self.detect_timestamp(value)
            if timestamp_result:
                return timestamp_result
        
        return value
    
    def detect_timestamp(self, value):
        """Detect and convert various timestamp formats"""
        try:
            if isinstance(value, str):
                if value.startswith('0x'):
                    value = int(value, 16)
                elif value.isdigit():
                    value = int(value)
                else:
                    return None
            
            if not isinstance(value, int):
                return None
            
            # Check different timestamp ranges
            if 1000000000 < value < 4102444800:  # Unix seconds
                dt = datetime.fromtimestamp(value)
            elif 1000000000000 < value < 4102444800000:  # Unix milliseconds
                dt = datetime.fromtimestamp(value / 1000)
            elif 1000000000000000 < value < 4102444800000000:  # Unix microseconds
                dt = datetime.fromtimestamp(value / 1000000)
            else:
                return None
            
            return {
                "type": "timestamp",
                "raw_value": value,
                "timestamp_type": "unix_epoch",
                "datetime_iso": dt.isoformat(),
                "datetime_readable": dt.strftime('%Y-%m-%d %H:%M:%S'),
                "timezone": "UTC"
            }
            
        except (ValueError, TypeError, OSError):
            return None
    
    def parse_text_file(self, file_path):
        """Parse text-based files with ULTRA-AGGRESSIVE user data extraction"""
        print(f"🔍 ULTRA-AGGRESSIVE TEXT SCAN: {file_path.name}")
        
        text_data = {
            "file_info": self.get_file_info(file_path),
            "content": {},
            "parsing_status": "unknown"
        }
        
        try:
            # Try multiple encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252', 'iso-8859-1']
            content = None
            used_encoding = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read()
                        used_encoding = encoding
                        break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if not content:
                # Final fallback
                with open(file_path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='replace')
                    used_encoding = 'utf-8-fallback'
            
            # ULTRA-AGGRESSIVE SCAN of text content
            self.ultra_aggressive_user_data_extraction(content, {
                'type': 'text_file',
                'file': file_path.name
            })
            
            text_data["content"] = {
                "encoding_used": used_encoding,
                "text": content[:10000],  # First 10000 chars
                "full_text": content if len(content) < 50000 else None,  # Full text if small
                "line_count": len(content.split('\n')),
                "character_count": len(content),
                "word_count": len(content.split())
            }
            text_data["parsing_status"] = "success"
            
            print(f"✅ ULTRA-AGGRESSIVE TEXT SCAN complete: {file_path.name}")
            
        except Exception as e:
            text_data["error"] = str(e)
            text_data["parsing_status"] = "error"
            print(f"❌ Text file processing error: {e}")
        
        return text_data
    
    def process_folder_files(self, folder_path, folder_name):
        """Process all files in a specific folder with ULTRA-AGGRESSIVE scanning"""
        print(f"\n📁 ULTRA-AGGRESSIVE FOLDER SCAN: {folder_name}")
        
        folder_data = {
            "folder_info": {
                "name": folder_name,
                "path": str(folder_path),
                "relative_path": str(folder_path.relative_to(self.instagram_folder)) if self.instagram_folder else str(folder_path.relative_to(self.working_folder)),
            },
            "files": {},
            "statistics": {
                "total_files": 0,
                "processed_files": 0,
                "failed_files": 0,
                "file_types": defaultdict(int)
            }
        }
        
        try:
            # Get all files in folder (non-recursive for this specific folder)
            files = [f for f in folder_path.iterdir() if f.is_file()]
            folder_data["statistics"]["total_files"] = len(files)
            
            for file_path in files:
                try:
                    file_extension = file_path.suffix.lower()
                    folder_data["statistics"]["file_types"][file_extension] += 1
                    
                    # Process based on file type with ULTRA-AGGRESSIVE scanning
                    if file_extension == '.db':
                        file_data = self.parse_sqlite_database(file_path)
                    elif file_extension in ['.txt', '.log', '.json', '.js', '.css', '.properties', '.conf', '.xml', '.html', '.htm']:
                        file_data = self.parse_text_file(file_path)
                    else:
                        # For other files, just get file info
                        file_data = {
                            "file_info": self.get_file_info(file_path),
                            "content": "Binary or unsupported file type",
                            "parsing_status": "skipped"
                        }
                    
                    folder_data["files"][file_path.name] = file_data
                    folder_data["statistics"]["processed_files"] += 1
                    
                except Exception as e:
                    error_info = {
                        "file_info": {"name": file_path.name, "path": str(file_path)},
                        "error": str(e),
                        "parsing_status": "error"
                    }
                    folder_data["files"][file_path.name] = error_info
                    folder_data["statistics"]["failed_files"] += 1
                    self.errors.append({
                        "file": str(file_path),
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
            
            # Convert defaultdict to regular dict
            folder_data["statistics"]["file_types"] = dict(folder_data["statistics"]["file_types"])
            
            print(f"✅ ULTRA-AGGRESSIVE FOLDER SCAN complete: {folder_name}")
            print(f"   📄 Files: {folder_data['statistics']['processed_files']}/{folder_data['statistics']['total_files']}")
            print(f"   ❌ Errors: {folder_data['statistics']['failed_files']}")
            
        except Exception as e:
            folder_data["error"] = str(e)
            print(f"❌ Folder processing error: {e}")
        
        return folder_data
    
    def save_folder_as_json(self, folder_data):
        """Save folder data as separate JSON file"""
        folder_info = folder_data.get("folder_info", {})
        
        # Get the full path relative to the initial working folder
        full_relative_path = Path(folder_info.get("path", "")).relative_to(self.working_folder)
        
        # Convert path to a safe filename by replacing path separators with double underscores
        json_filename_base = str(full_relative_path).replace(os.sep, '__').replace('/', '__')
        
        # If it's the root working folder itself, use its name
        if not json_filename_base:
            json_filename_base = self.working_folder.name
        
        # Clean up any remaining invalid characters and ensure it's not too long
        safe_json_filename_base = re.sub(r'[^\w\-_\.]', '_', json_filename_base)
        if len(safe_json_filename_base) > 200:
            hash_suffix = hashlib.md5(safe_json_filename_base.encode()).hexdigest()[:8]
            safe_json_filename_base = f"{safe_json_filename_base[:190]}_{hash_suffix}"

        json_filename = f"{safe_json_filename_base}.json"
        json_path = self.json_folders_dir / json_filename
        
        # Add forensic metadata
        forensic_data = {
            "forensic_metadata": {
                "extraction_timestamp": datetime.now().isoformat(),
                "tool_version": self.case_info["tool_version"],
                "case_info": self.case_info,
                "folder_name": folder_info.get("name", "unknown"),
                "folder_relative_path": folder_info.get("relative_path", ""),
                "file_hash": None
            },
            "data": folder_data
        }
        
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(forensic_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Calculate hash after saving
            forensic_data["forensic_metadata"]["file_hash"] = self.calculate_file_hash(json_path)
            
            # Save again with hash
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(forensic_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"💾 Saved folder JSON: {json_filename}")
            return json_path
            
        except Exception as e:
            print(f"❌ Error saving folder JSON: {e}")
            return None
    
    def calculate_file_hash(self, file_path):
        """Calculate SHA-256 hash of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Hash calculation failed for {file_path}: {e}")
            return None
    
    def save_json_data(self, data, filename):
        """Save data as JSON with forensic metadata"""
        output_path = self.output_dir / filename
        
        forensic_data = {
            "forensic_metadata": {
                "extraction_timestamp": datetime.now().isoformat(),
                "tool_version": self.case_info["tool_version"],
                "case_info": self.case_info,
                "file_hash": None
            },
            "data": data
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(forensic_data, f, indent=2, ensure_ascii=False, default=str)
        
        # Calculate hash after saving
        forensic_data["forensic_metadata"]["file_hash"] = self.calculate_file_hash(output_path)
        
        # Save again with hash
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(forensic_data, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"Saved: {output_path}")
        return output_path
    
    def _process_folder_recursive(self, folder_path):
        """Recursively process folders and save their data."""
        folder_name = folder_path.name if folder_path.name else "root"
        
        # Process current folder
        folder_data = self.process_folder_files(folder_path, folder_name)
        
        # Save folder as separate JSON file
        self.save_folder_as_json(folder_data)
        
        # Store in main folder data
        full_relative_path_key = str(Path(folder_data["folder_info"]["path"]).relative_to(self.working_folder))
        if not full_relative_path_key:
            full_relative_path_key = self.working_folder.name
        self.folder_data[full_relative_path_key] = folder_data
        
        # Process subfolders
        try:
            for item in folder_path.iterdir():
                if item.is_dir():
                    self._process_folder_recursive(item)
        except PermissionError:
            print(f"⚠️ Permission denied accessing subfolders in {folder_path}")
        except Exception as e:
            print(f"⚠️ Error processing subfolders in {folder_path}: {e}")

    def extract_all_data(self):
        """ULTRA-AGGRESSIVE extraction method for V7 - ULTIMATE USER FOCUS"""
        print("\n🚀 Starting Instagram Data Extractor V7 ULTRA-AGGRESSIVE USER ANALYSIS...")
        
        # Find Instagram folder
        self.instagram_folder = self.find_instagram_folder()
        
        if not self.instagram_folder:
            print("⚠️ No Instagram folder found")
            return {"status": "no_instagram_data", "message": "No Instagram folder found"}
        
        print(f"\n📁 Processing Instagram folder: {self.instagram_folder}")
        
        # Analyze complete folder structure
        self.analyze_folder_structure()
        
        # Process each folder and create separate JSON files with ULTRA-AGGRESSIVE scanning
        self._process_folder_recursive(self.instagram_folder)
        
        # FINALIZE all user data from ULTRA-AGGRESSIVE scanning
        self.finalize_user_data()
        
        # Enhanced: Prepare statistics
        session_stats = {
            "total_session_ids_found": len(self._all_found_session_ids),
            "primary_session_id": self.logged_in_user['primary_instagram_session_id'],
            "all_session_ids": list(self._all_found_session_ids.keys()),
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        # Enhanced: Save main data files with focus on logged-in user
        
        # 1. LOGGED-IN USER PROFILE (TOP PRIORITY)
        logged_in_user_output = {
            "description": "ULTRA-AGGRESSIVE extraction of logged-in Instagram user profile",
            "logged_in_user": self.logged_in_user,
            "extraction_summary": {
                "user_id_found": bool(self.logged_in_user['user_id']),
                "username_found": bool(self.logged_in_user['username']),
                "email_found": bool(self.logged_in_user['email']),
                "session_id_found": bool(self.logged_in_user['primary_instagram_session_id']),
                "all_session_ids_count": len(self.logged_in_user['all_session_ids']),
                "followers_count": self.logged_in_user['followers_count'],
                "following_count": self.logged_in_user['following_count'],
                "posts_count": self.logged_in_user['posts_count'],
                "user_id_confidence": self.logged_in_user['user_id_confidence'],
                "user_id_source": self.logged_in_user['user_id_source'],
                "total_user_ids_found": len(self._all_found_user_ids),
                "total_usernames_found": len(self._all_found_usernames),
                "total_emails_found": len(self._all_found_emails),
                "total_session_ids_found": len(self._all_found_session_ids),
                "discovery_timeline_entries": len(self.logged_in_user['discovery_timeline'])
            }
        }
        self.save_json_data(logged_in_user_output, "logged_in_user_profile.json")
        print(f"✅ Logged-in User Profile saved: logged_in_user_profile.json")

        # 2. Enhanced Session IDs
        session_output = {
            "description": "All session identifiers found during ULTRA-AGGRESSIVE extraction",
            "primary_instagram_session_id": self.logged_in_user['primary_instagram_session_id'],
            "all_session_ids_for_user": self.logged_in_user['all_session_ids'],
            "logged_in_user_id": self.logged_in_user['user_id'],
            "statistics": session_stats,
            "all_found_sessions": dict(self._all_found_session_ids)
        }
        self.save_json_data(session_output, "session_ids.json")
        print(f"✅ Session IDs saved: session_ids.json")
        
        # 3. User IDs Analysis
        user_ids_output = {
            "description": "Detailed analysis of all user IDs found during extraction",
            "primary_user_id": self.logged_in_user['user_id'],
            "primary_user_id_confidence": self.logged_in_user['user_id_confidence'],
            "primary_user_id_source": self.logged_in_user['user_id_source'],
            "total_user_ids_found": len(self._all_found_user_ids),
            "all_user_ids": dict(self._all_found_user_ids)
        }
        self.save_json_data(user_ids_output, "user_ids_analysis.json")
        print(f"✅ User IDs Analysis saved: user_ids_analysis.json")
        
        # 4. Counts Analysis
        counts_output = {
            "description": "Detailed analysis of follower, following, and posts counts",
            "followers_count": self.logged_in_user['followers_count'],
            "following_count": self.logged_in_user['following_count'],
            "posts_count": self.logged_in_user['posts_count'],
            "follower_count_sources": self._follower_count_sources,
            "following_count_sources": self._following_count_sources,
            "posts_count_sources": self._posts_count_sources,
            "relationships_data": self._follower_following_data
        }
        self.save_json_data(counts_output, "counts_analysis.json")
        print(f"✅ Counts Analysis saved: counts_analysis.json")
        
        # 5. Discovery Timeline
        timeline_output = {
            "description": "Chronological timeline of all user data discoveries",
            "timeline": self.logged_in_user['discovery_timeline'],
            "total_discoveries": len(self.logged_in_user['discovery_timeline'])
        }
        self.save_json_data(timeline_output, "discovery_timeline.json")
        print(f"✅ Discovery Timeline saved: discovery_timeline.json")
        
        # 6. Complete file system structure
        self.save_json_data(self.file_system_structure, "file_system_structure.json")
        print(f"✅ File system structure saved: file_system_structure.json")
        
        # 7. Complete folder data
        self.save_json_data(self.folder_data, "complete_folder_analysis.json")
        print(f"✅ Complete folder analysis saved: complete_folder_analysis.json")
        
        # 8. User Data Summary (HTML)
        self.generate_user_data_html_summary()
        print(f"✅ User Data HTML Summary saved: user_data_summary.html")
        
        # Enhanced: Generate final report with ULTRA-AGGRESSIVE extraction results
        extraction_report = {
            "status": "success",
            "instagram_folder": str(self.instagram_folder),
            "logged_in_user_summary": {
                "user_id": self.logged_in_user['user_id'],
                "username": self.logged_in_user['username'],
                "full_name": self.logged_in_user['full_name'],
                "email": self.logged_in_user['email'],
                "phone_number": self.logged_in_user['phone_number'],
                "followers_count": self.logged_in_user['followers_count'],
                "following_count": self.logged_in_user['following_count'],
                "posts_count": self.logged_in_user['posts_count'],
                "is_private": self.logged_in_user['is_private'],
                "is_verified": self.logged_in_user['is_verified'],
                "primary_session_id": self.logged_in_user['primary_instagram_session_id'],
                "all_session_ids_count": len(self.logged_in_user['all_session_ids']),
                "user_id_confidence": self.logged_in_user['user_id_confidence'],
                "user_id_source": self.logged_in_user['user_id_source']
            },
            "ultra_aggressive_extraction_stats": {
                "total_user_ids_found": len(self._all_found_user_ids),
                "total_usernames_found": len(self._all_found_usernames),
                "total_emails_found": len(self._all_found_emails),
                "total_session_ids_found": len(self._all_found_session_ids),
                "total_relationships_found": len(self._follower_following_data),
                "total_follower_count_sources": len(self._follower_count_sources),
                "total_following_count_sources": len(self._following_count_sources),
                "total_posts_count_sources": len(self._posts_count_sources),
                "discovery_timeline_entries": len(self.logged_in_user['discovery_timeline'])
            },
            "file_system_analysis": {
                "total_folders": self.file_system_structure["total_folders"],
                "total_files": self.file_system_structure["total_files"],
                "file_types": self.file_system_structure["file_types"]
            },
            "folder_json_files": len(self.folder_data),
            "errors": len(self.errors),
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        self.save_json_data(extraction_report, "extraction_report.json")
        
        return extraction_report
    
    def generate_user_data_html_summary(self):
        """Generate an HTML summary of user data for easy viewing"""
        html_path = self.output_dir / "user_data_summary.html"
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram User Data Summary</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3 {{
            color: #405DE6;
        }}
        .header {{
            background: linear-gradient(45deg, #405DE6, #5851DB, #833AB4, #C13584, #E1306C, #FD1D1D, #F56040, #F77737, #FCAF45, #FFDC80);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .section {{
            background-color: #f9f9f9;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .data-item {{
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }}
        .data-label {{
            font-weight: bold;
            color: #555;
        }}
        .data-value {{
            margin-left: 10px;
        }}
        .highlight {{
            background-color: #FFF3CD;
            padding: 5px;
            border-radius: 3px;
        }}
        .timeline {{
            margin-top: 20px;
        }}
        .timeline-item {{
            padding: 10px;
            margin-bottom: 10px;
            border-left: 3px solid #405DE6;
            background-color: #f0f0f0;
        }}
        .counts {{
            display: flex;
            justify-content: space-around;
            text-align: center;
            margin: 20px 0;
        }}
        .count-box {{
            background-color: #fff;
            border-radius: 10px;
            padding: 20px;
            width: 30%;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .count-number {{
            font-size: 36px;
            font-weight: bold;
            color: #405DE6;
        }}
        .count-label {{
            font-size: 16px;
            color: #888;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Instagram User Data Summary</h1>
        <p>Extraction Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="section">
        <h2>User Profile</h2>
        <div class="data-item">
            <span class="data-label">User ID:</span>
            <span class="data-value highlight">{self.logged_in_user['user_id'] or 'Not found'}</span>
            <span class="data-value">(Confidence: {self.logged_in_user['user_id_confidence']}/100)</span>
        </div>
        <div class="data-item">
            <span class="data-label">Username:</span>
            <span class="data-value highlight">{self.logged_in_user['username'] or 'Not found'}</span>
        </div>
        <div class="data-item">
            <span class="data-label">Full Name:</span>
            <span class="data-value">{self.logged_in_user['full_name'] or 'Not found'}</span>
        </div>
        <div class="data-item">
            <span class="data-label">Email:</span>
            <span class="data-value highlight">{self.logged_in_user['email'] or 'Not found'}</span>
        </div>
        <div class="data-item">
            <span class="data-label">Phone Number:</span>
            <span class="data-value">{self.logged_in_user['phone_number'] or 'Not found'}</span>
        </div>
        <div class="data-item">
            <span class="data-label">Private Account:</span>
            <span class="data-value">{str(self.logged_in_user['is_private']) if self.logged_in_user['is_private'] is not None else 'Unknown'}</span>
        </div>
        <div class="data-item">
            <span class="data-label">Verified Account:</span>
            <span class="data-value">{str(self.logged_in_user['is_verified']) if self.logged_in_user['is_verified'] is not None else 'Unknown'}</span>
        </div>
        
        <div class="counts">
            <div class="count-box">
                <div class="count-number">{self.logged_in_user['followers_count']}</div>
                <div class="count-label">Followers</div>
            </div>
            <div class="count-box">
                <div class="count-number">{self.logged_in_user['following_count']}</div>
                <div class="count-label">Following</div>
            </div>
            <div class="count-box">
                <div class="count-number">{self.logged_in_user['posts_count']}</div>
                <div class="count-label">Posts</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>Session Information</h2>
        <div class="data-item">
            <span class="data-label">Primary Session ID:</span>
            <span class="data-value highlight">{self.logged_in_user['primary_instagram_session_id'][:20] + '...' if self.logged_in_user['primary_instagram_session_id'] else 'Not found'}</span>
        </div>
        <div class="data-item">
            <span class="data-label">Total Session IDs Found:</span>
            <span class="data-value">{len(self.logged_in_user['all_session_ids'])}</span>
        </div>
        
        <h3>Top 5 Session IDs</h3>
        <table>
            <tr>
                <th>Session ID</th>
                <th>Count</th>
                <th>First Seen</th>
            </tr>
"""
        
        # Add top 5 session IDs
        sorted_sessions = sorted(self._all_found_session_ids.items(), key=lambda x: x[1]['count'], reverse=True)
        for i, (session_id, data) in enumerate(sorted_sessions[:5]):
            html_content += f"""
            <tr>
                <td>{session_id[:20]}...</td>
                <td>{data['count']}</td>
                <td>{data['first_seen']}</td>
            </tr>"""
        
        html_content += """
        </table>
    </div>
    
    <div class="section">
        <h2>User ID Analysis</h2>
        <div class="data-item">
            <span class="data-label">Total User IDs Found:</span>
            <span class="data-value">{}</span>
        </div>
        
        <h3>Top 10 User IDs</h3>
        <table>
            <tr>
                <th>User ID</th>
                <th>Confidence</th>
                <th>Count</th>
                <th>First Seen</th>
            </tr>
""".format(len(self._all_found_user_ids))
        
        # Add top 10 user IDs
        sorted_user_ids = sorted(self._all_found_user_ids.items(), key=lambda x: (x[1]['confidence'], x[1]['count']), reverse=True)
        for i, (user_id, data) in enumerate(sorted_user_ids[:10]):
            html_content += f"""
            <tr>
                <td>{user_id}</td>
                <td>{data['confidence']}</td>
                <td>{data['count']}</td>
                <td>{data['first_seen']}</td>
            </tr>"""
        
        html_content += """
        </table>
    </div>
    
    <div class="section">
        <h2>Discovery Timeline</h2>
        <p>Chronological order of data discoveries during extraction:</p>
        <div class="timeline">
"""
        
        # Add timeline items
        for item in self.logged_in_user['discovery_timeline'][:20]:  # Show first 20 items
            html_content += f"""
            <div class="timeline-item">
                <strong>{item['timestamp']}</strong>: Found {item['type']} - {item['value']}
            </div>"""
        
        html_content += """
        </div>
    </div>
    
    <div class="section">
        <h2>Extraction Statistics</h2>
        <div class="data-item">
            <span class="data-label">Total User IDs Found:</span>
            <span class="data-value">{}</span>
        </div>
        <div class="data-item">
            <span class="data-label">Total Usernames Found:</span>
            <span class="data-value">{}</span>
        </div>
        <div class="data-item">
            <span class="data-label">Total Emails Found:</span>
            <span class="data-value">{}</span>
        </div>
        <div class="data-item">
            <span class="data-label">Total Session IDs Found:</span>
            <span class="data-value">{}</span>
        </div>
        <div class="data-item">
            <span class="data-label">Total Relationships Found:</span>
            <span class="data-value">{}</span>
        </div>
        <div class="data-item">
            <span class="data-label">Total Files Analyzed:</span>
            <span class="data-value">{}</span>
        </div>
        <div class="data-item">
            <span class="data-label">Total Folders Analyzed:</span>
            <span class="data-value">{}</span>
        </div>
    </div>
    
    <div class="section">
        <h2>Output Files</h2>
        <ul>
            <li><strong>logged_in_user_profile.json</strong> - Complete user profile data</li>
            <li><strong>session_ids.json</strong> - All session IDs found during extraction</li>
            <li><strong>user_ids_analysis.json</strong> - Detailed analysis of all user IDs</li>
            <li><strong>counts_analysis.json</strong> - Analysis of follower, following, and posts counts</li>
            <li><strong>discovery_timeline.json</strong> - Chronological timeline of all discoveries</li>
            <li><strong>extraction_report.json</strong> - Complete extraction report</li>
            <li><strong>file_system_structure.json</strong> - Analysis of file system structure</li>
            <li><strong>complete_folder_analysis.json</strong> - Detailed analysis of all folders</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>About This Report</h2>
        <p>This report was generated by Instagram Data Extractor V7.0 - Ultimate User Focus.</p>
        <p>Extraction Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Tool Version: 7.0-Ultimate-User-Focus</p>
    </div>
</body>
</html>
""".format(
            len(self._all_found_user_ids),
            len(self._all_found_usernames),
            len(self._all_found_emails),
            len(self._all_found_session_ids),
            len(self._follower_following_data),
            self.file_system_structure["total_files"],
            self.file_system_structure["total_folders"]
        )
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_extraction_dir and os.path.exists(self.temp_extraction_dir):
            try:
                print(f"🧹 Cleaning up temporary files...")
                shutil.rmtree(self.temp_extraction_dir)
                print("✅ Cleanup complete")
            except Exception as e:
                print(f"⚠️ Cleanup warning: {e}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        if hasattr(self, 'temp_extraction_dir'):
            self.cleanup()


def main():
    """ULTRA-AGGRESSIVE extraction main function"""
    print("=" * 80)
    print("📱 Instagram Data Extractor V7.0 - ULTIMATE USER FOCUS")
    print("   🎯 ULTRA-AGGRESSIVE extraction of user ID, followers, following, session IDs")
    print("   🔍 Enhanced pattern matching for maximum data recovery")
    print("   📊 Comprehensive user profile reconstruction")
    print("   🔐 Complete session and authentication data extraction")
    print("   📈 Detailed analysis with confidence scoring")
    print("   📅 Discovery timeline tracking")
    print("   📊 HTML summary report generation")
    print("=" * 80)

    # Get input path
    input_path = input("📂 Enter path to dump folder or ZIP file: ").strip().strip('"')

    if not input_path or not os.path.exists(input_path):
        print("❌ Invalid path provided.")
        return

    # Optional case information
    print("\n📋 Case Information (optional):")
    case_number = input("Case number: ").strip()
    examiner_name = input("Examiner name: ").strip()
    evidence_item = input("Evidence item: ").strip()

    case_info = {}
    if case_number:
        case_info["case_number"] = case_number
    if examiner_name:
        case_info["examiner"] = examiner_name
    if evidence_item:
        case_info["evidence_item"] = evidence_item

    try:
        # Initialize ULTRA-AGGRESSIVE extractor
        extractor = InstagramDataExtractorV7(input_path, case_info=case_info)
        
        # Perform ULTRA-AGGRESSIVE extraction
        result = extractor.extract_all_data()
        
        # Enhanced: Print results with ULTRA-AGGRESSIVE extraction stats
        print("\n" + "="*80)
        print("📊 ULTRA-AGGRESSIVE EXTRACTION COMPLETE - ULTIMATE USER FOCUS RESULTS")
        print("="*80)
        
        if result["status"] == "success":
            print(f"✅ Status: {result['status']}")
            print(f"📁 Instagram folder: {result['instagram_folder']}")
            
            print(f"\n👤 LOGGED-IN USER PROFILE (ULTRA-AGGRESSIVE EXTRACTION):")
            user_summary = result["logged_in_user_summary"]
            print(f"   🆔 User ID: {user_summary['user_id'] or 'Not found'}")
            print(f"   👤 Username: {user_summary['username'] or 'Not found'}")
            print(f"   📧 Email: {user_summary['email'] or 'Not found'}")
            print(f"   📱 Phone: {user_summary['phone_number'] or 'Not found'}")
            print(f"   👥 Followers: {user_summary['followers_count']}")
            print(f"   👤 Following: {user_summary['following_count']}")
            print(f"   📸 Posts: {user_summary['posts_count']}")
            print(f"   🔒 Private: {user_summary['is_private']}")
            print(f"   ✅ Verified: {user_summary['is_verified']}")
            print(f"   🔐 Primary Session ID: {user_summary['primary_session_id'][:20] + '...' if user_summary['primary_session_id'] else 'Not found'}")
            print(f"   🔐 All Session IDs Found: {user_summary['all_session_ids_count']}")
            print(f"   📊 User ID Confidence: {user_summary['user_id_confidence']}/100")
            print(f"   📍 User ID Source: {user_summary['user_id_source']}")
            
            print(f"\n🎯 ULTRA-AGGRESSIVE EXTRACTION STATISTICS:")
            agg_stats = result["ultra_aggressive_extraction_stats"]
            print(f"   🆔 Total User IDs Found: {agg_stats['total_user_ids_found']}")
            print(f"   👤 Total Usernames Found: {agg_stats['total_usernames_found']}")
            print(f"   📧 Total Emails Found: {agg_stats['total_emails_found']}")
            print(f"   🔐 Total Session IDs Found: {agg_stats['total_session_ids_found']}")
            print(f"   👥 Total Relationships Found: {agg_stats['total_relationships_found']}")
            print(f"   📊 Total Follower Count Sources: {agg_stats['total_follower_count_sources']}")
            print(f"   📊 Total Following Count Sources: {agg_stats['total_following_count_sources']}")
            print(f"   📊 Total Posts Count Sources: {agg_stats['total_posts_count_sources']}")
            print(f"   📅 Discovery Timeline Entries: {agg_stats['discovery_timeline_entries']}")
            
            print(f"\n📊 File System Analysis:")
            for key, value in result["file_system_analysis"].items():
                if isinstance(value, dict):
                    print(f"   {key}: {len(value)} types")
                else:
                    print(f"   {key}: {value}")
            
            print(f"\n📁 Folder JSON Files Created: {result['folder_json_files']}")
            print(f"❌ Errors: {result['errors']}")
            print(f"📂 Output directory: {extractor.output_dir}")
            
            print(f"\n📄 Main JSON files created:")
            print(f"   👤 logged_in_user_profile.json (ULTRA-AGGRESSIVE USER FOCUS)")
            print(f"   🔐 session_ids.json (ALL SESSION DATA)")
            print(f"   🆔 user_ids_analysis.json (DETAILED USER ID ANALYSIS)")
            print(f"   📊 counts_analysis.json (FOLLOWER/FOLLOWING/POSTS COUNTS)")
            print(f"   📅 discovery_timeline.json (CHRONOLOGICAL DISCOVERY TIMELINE)")
            print(f"   📁 file_system_structure.json")
            print(f"   📋 complete_folder_analysis.json")
            print(f"   📊 extraction_report.json")
            print(f"   🌐 user_data_summary.html (INTERACTIVE HTML SUMMARY)")
            
            print(f"\n📁 Individual folder JSON files:")
            print(f"   📂 Location: {extractor.json_folders_dir}")
            print(f"   📄 Count: {result['folder_json_files']} files")
            
            # Show detailed findings if available
            if user_summary['user_id']:
                print(f"\n✨ **KEY FINDINGS:**")
                print(f"   🎯 Successfully identified primary user: {user_summary['user_id']}")
                if user_summary['username']:
                    print(f"   👤 Username: @{user_summary['username']}")
                if user_summary['email']:
                    print(f"   📧 Email: {user_summary['email']}")
                if user_summary['primary_session_id']:
                    print(f"   🔐 Active session found: {user_summary['primary_session_id'][:10]}...")
                print(f"   📊 Social stats: {user_summary['followers_count']} followers, {user_summary['following_count']} following, {user_summary['posts_count']} posts")
                print(f"   📊 User ID confidence: {user_summary['user_id_confidence']}/100")
            else:
                print(f"\n⚠️ **EXTRACTION CHALLENGES:**")
                print(f"   🔍 User ID not definitively identified")
                print(f"   📊 Found {agg_stats['total_user_ids_found']} potential user IDs")
                print(f"   💡 Check user_ids_analysis.json for all candidates")
            
            print(f"\n📊 **INTERACTIVE SUMMARY:**")
            print(f"   🌐 Open user_data_summary.html in your browser for an interactive summary")
            print(f"   📂 Location: {extractor.output_dir / 'user_data_summary.html'}")
            
        else:
            print(f"⚠️ Status: {result['status']}")
            print(f"💬 Message: {result['message']}")
        
        print(f"\n📄 All results saved in: {extractor.output_dir}")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")

    finally:
        # Cleanup
        if 'extractor' in locals():
            extractor.cleanup()


if __name__ == "__main__":
    main()
