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

# Try to import pyzipper for encrypted ZIP support
try:
    import pyzipper
    PYZIPPER_AVAILABLE = True
except ImportError:
    PYZIPPER_AVAILABLE = False

class InstagramExtractorV5Enhanced:
    """
    Instagram Forensic Extractor Version 5.0 Enhanced - Enhanced Media and Session Extraction
    Improved media extraction from chats and enhanced session ID detection.
    """
    
    def __init__(self, input_path, output_dir=None, case_info=None):
        """Initialize the Instagram extractor V5 Enhanced"""
        self.setup_logging()
        
        self.original_input = Path(input_path)
        self.temp_extraction_dir = None
        self.is_zip_input = False
        
        # Handle ZIP file input
        if self.is_zip_file(input_path):
            print(f" Detected ZIP file: {self.original_input.name}")
            self.is_zip_input = True
            self.working_folder = self.extract_zip_safely(input_path)
        else:
            self.working_folder = Path(input_path)
        
        # Setup output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path.cwd() / "instagram_extraction_v5_enhanced_output"
        
        self.output_dir.mkdir(exist_ok=True)
        
        # Create JSON folders structure
        self.json_folders_dir = self.output_dir / "json_folders"
        self.json_folders_dir.mkdir(exist_ok=True)

        # Create downloaded media directory
        self.downloaded_media_dir = self.output_dir / "downloaded_media"
        self.downloaded_media_dir.mkdir(exist_ok=True)
        
        # Create extracted chat media directory
        self.chat_media_dir = self.output_dir / "chat_media"
        self.chat_media_dir.mkdir(exist_ok=True)
        
        # Case information
        self.case_info = case_info or {}
        self.case_info.update({
            "extraction_start": datetime.now().isoformat(),
            "tool_version": "5.0-Enhanced-Media-Session",
            "input_type": "ZIP file" if self.is_zip_input else "Folder",
            "original_source": str(self.original_input),
            "extractor": "Instagram Extractor V5 Enhanced - Media & Session Focus"
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
        
        # Enhanced Session ID tracking with more patterns
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
            "all_session_ids": []  # Enhanced: Store all found session IDs
        }
        
        # To help identify the most frequent user ID for logged_in_user_id (fallback)
        self._potential_user_ids = defaultdict(int) 
        
        # Server ID tracking
        self.server_data = {
            "instagram_servers": [],
            "api_endpoints": [],
            "cdn_servers": [],
            "media_servers": [],
            "websocket_servers": [],
            "other_servers": []
        }
        
        # Enhanced data containers - separate followers and following
        self.chats = []
        self.media = []
        self.chat_media = []  # New: Specific media from chats
        self.followers_list = []
        self.following_list = []
        
        # Enhanced deduplication sets
        self.seen_chat_hashes = set()
        self.seen_media_hashes = set()
        self.seen_chat_media_hashes = set()  # New: For chat-specific media
        self.seen_follower_hashes = set()
        self.seen_following_hashes = set()
        self.seen_session_hashes = set()  # New: For session deduplication
        
        # Complete extracted data organized by folders
        self.folder_data = {}
        
        # All errors
        self.errors = []
        
        # Enhanced media patterns for better detection
        self.media_patterns = {
            'image_extensions': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg'],
            'video_extensions': ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.3gp', '.m4v'],
            'audio_extensions': ['.mp3', '.wav', '.aac', '.m4a', '.ogg', '.flac'],
            'media_urls': [
                r'https?://[^.\s]*\.cdninstagram\.com/[^\s"\'<>]+',
                r'https?://[^.\s]*\.fbcdn\.net/[^\s"\'<>]+',
                r'https?://scontent[^.\s]*\.xx\.fbcdn.net/[^\s"\'<>]+',
                r'https?://[^.\s]*\.instagram\.com/[^\s"\'<>]+\.(jpg|jpeg|png|gif|mp4|mov)',
                r'instagram://media\?id=[0-9_]+',
                r'file://[^\s"\'<>]+\.(jpg|jpeg|png|gif|mp4|mov|webp)'
            ]
        }
        
        # User profile tables - tables that likely contain user profile information
        self.user_profile_tables = [
            'users', 'user_info', 'profile', 'profiles', 'accounts', 'account_info',
            'user_settings', 'user_profile', 'user_profiles', 'user_data',
            'self_profile', 'current_user', 'my_account', 'account_info'
        ]
        
        # Session tables - tables that likely contain session information
        self.session_tables = [
            'sessions', 'session_info', 'auth', 'authentication', 'tokens',
            'cookies', 'login', 'login_info', 'credentials', 'oauth'
        ]
        
        self.logger.info(f"Instagram Extractor V5 Enhanced initialized for: {self.original_input}")
    
    def setup_logging(self):
        """Setup logging system"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logs_dir = Path.cwd() / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(logs_dir / f"instagram_v5_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger("InstagramExtractorV5Enhanced")
    
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
        print(f" Extracting ZIP file: {Path(zip_path).name}")
        
        try:
            self.temp_extraction_dir = tempfile.mkdtemp(prefix="instagram_extract_")
            temp_path = Path(self.temp_extraction_dir)
            
            print(f" Extraction directory: {temp_path}")
            
            zip_size = os.path.getsize(zip_path)
            print(f" ZIP size: {zip_size / (1024*1024):.2f} MB")
            
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
                    print(f" pyzipper failed: {e}")
            
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
                "view_link": None,
                "is_media_file": self.is_media_file(file_path)  # Enhanced: Check if it's a media file
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
    
    def is_media_file(self, file_path):
        """Enhanced: Check if file is a media file"""
        extension = file_path.suffix.lower()
        return (extension in self.media_patterns['image_extensions'] or 
                extension in self.media_patterns['video_extensions'] or 
                extension in self.media_patterns['audio_extensions'])
    
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
                    "instagram_files": 0,
                    "media_files": 0  # Enhanced: Count media files
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
                        
                        if file_info.get("is_media_file"):
                            folder_info["statistics"]["media_files"] += 1
                        
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
                        folder_info["statistics"]["media_files"] += subfolder_info["statistics"]["media_files"]
                        
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
    
    def _set_logged_in_user_id_with_priority(self, user_id, confidence_score, source_description):
        """
        Sets the logged-in user ID if the new confidence score is higher than the current one.
        """
        if user_id is None:
            return

        user_id_str = str(user_id)

        if confidence_score > self.logged_in_user['user_id_confidence']:
            self.logged_in_user['user_id'] = user_id_str
            self.logged_in_user['user_id_confidence'] = confidence_score
            self.logged_in_user['user_id_source'] = source_description
            self.logger.info(f"Updated logged-in user ID to {user_id_str} (Confidence: {confidence_score}, Source: {source_description})")
            print(f"🔍 Found user ID: {user_id_str} (Confidence: {confidence_score}, Source: {source_description})")
        elif confidence_score == self.logged_in_user['user_id_confidence'] and self.logged_in_user['user_id'] is None:
            self.logged_in_user['user_id'] = user_id_str
            self.logged_in_user['user_id_confidence'] = confidence_score
            self.logged_in_user['user_id_source'] = source_description
            self.logger.info(f"Set logged-in user ID to {user_id_str} (Confidence: {confidence_score}, Source: {source_description})")
            print(f"🔍 Found user ID: {user_id_str} (Confidence: {confidence_score}, Source: {source_description})")

    def extract_session_ids(self, text_content, source_file_path=""):
        """Enhanced: Extract session IDs, authentication tokens, and user identifiers from text content"""
        if not isinstance(text_content, str):
            return
        
        # Enhanced Instagram session patterns
        instagram_patterns = [
            (r'sessionid["\']?\s*[:=]\s*["\']?([a-zA-Z0-9%\-_\.]{20,})["\']?', 'sessionid', 100),
            (r'csrftoken["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'csrftoken', 100),
            (r'ds_user_id["\']?\s*[:=]\s*["\']?([0-9]{8,})["\']?', 'ds_user_id', 100),
            (r'shbid["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{10,})["\']?', 'shbid', 80),
            (r'shbts["\']?\s*[:=]\s*["\']?([0-9]{10,})["\']?', 'shbts', 80),
            (r'rur["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{5,})["\']?', 'rur', 80),
            (r'mid["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'mid', 80),
            (r'ig_did["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'ig_did', 75),
            (r'ig_nrcb["\']?\s*[:=]\s*["\']?([0-9]{1,2})["\']?', 'ig_nrcb', 70),
            # Additional patterns for Instagram cookies
            (r'Cookie:.*?sessionid=([a-zA-Z0-9%\-_\.]{20,})', 'sessionid_cookie', 100),
            (r'Set-Cookie:.*?sessionid=([a-zA-Z0-9%\-_\.]{20,})', 'sessionid_set_cookie', 100),
            (r'instagram\.com.*?sessionid=([a-zA-Z0-9%\-_\.]{20,})', 'sessionid_url', 95),
        ]
        
        # Enhanced Facebook session patterns
        facebook_patterns = [
            (r'c_user["\']?\s*[:=]\s*["\']?([0-9]{8,})["\']?', 'c_user', 90),
            (r'xs["\']?\s*[:=]\s*["\']?([a-zA-Z0-9%\-_]{20,})["\']?', 'xs', 80),
            (r'datr["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'datr', 80),
            (r'sb["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'sb', 80),
            (r'fr["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'fr', 80),
            (r'wd["\']?\s*[:=]\s*["\']?([0-9x]+)["\']?', 'wd', 70),
        ]
        
        # Enhanced auth token patterns
        auth_patterns = [
            (r'access_token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_\.]{30,})["\']?', 'access_token', 70),
            (r'bearer["\s]*["\']?([a-zA-Z0-9\-_\.]{30,})["\']?', 'bearer_token', 70),
            (r'authorization["\']?\s*[:=]\s*["\']?bearer\s+([a-zA-Z0-9\-_\.]{30,})["\']?', 'auth_bearer', 70),
            (r'token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_\.]{30,})["\']?', 'generic_token', 60),
            (r'api_key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'api_key', 60),
            (r'client_secret["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'client_secret', 65),
        ]
        
        # Enhanced device session patterns
        device_patterns = [
            (r'device_id["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'device_id', 50),
            (r'android_id["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{16})["\']?', 'android_id', 50),
            (r'uuid["\']?\s*[:=]\s*["\']?([a-fA-F0-9\-]{36})["\']?', 'uuid', 50),
            (r'machine_id["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'machine_id', 50),
            (r'phone_id["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'phone_id', 50),
            (r'advertising_id["\']?\s*[:=]\s*["\']?([a-fA-F0-9\-]{36})["\']?', 'advertising_id', 45),
        ]
        
        # Enhanced CSRF token patterns
        csrf_patterns = [
            (r'csrf_token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'csrf_token', 40),
            (r'_token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', '_token', 40),
            (r'authenticity_token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'authenticity_token', 40),
            (r'X-CSRFToken["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'x_csrf_token', 45),
        ]
        
        # Enhanced user identifier patterns
        user_patterns = [
            (r'user_id["\']?\s*[:=]\s*["\']?([0-9]{8,})["\']?', 'user_id', 30),
            (r'username["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\._]{3,30})["\']?', 'username', 20),
            (r'email["\']?\s*[:=]\s*["\']?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["\']?', 'email', 20),
            (r'(?:phone_number|mobile_number)["\']?\s*[:=]\s*["\']?(\+?\d{10,15})["\']?', 'phone_number', 20),
            (r'facebook_id["\']?\s*[:=]\s*["\']?([0-9]{10,})["\']?', 'facebook_id', 90),
            (r'fb_user_id["\']?\s*[:=]\s*["\']?([0-9]{10,})["\']?', 'facebook_id', 90),
            (r'full_name["\']?\s*[:=]\s*["\']?([^"\']{2,50})["\']?', 'full_name', 20),
            # Additional patterns for user profile data
            (r'"pk":\s*"?([0-9]{8,})"?', 'user_pk', 85),
            (r'"id":\s*"?([0-9]{8,})"?', 'user_id_json', 80),
            (r'"username":\s*"([a-zA-Z0-9\._]{3,30})"', 'username_json', 75),
            (r'"full_name":\s*"([^"]{2,50})"', 'full_name_json', 75),
        ]
        
        # New: Cookie session patterns
        cookie_patterns = [
            (r'Set-Cookie:\s*([^=]+=[^;]+)', 'set_cookie', 30),
            (r'Cookie:\s*([^=]+=[^;]+)', 'cookie', 30),
            (r'HttpOnly[;\s]*([^=]+=[^;]+)', 'http_only_cookie', 35),
        ]
        
        # New: JWT token patterns
        jwt_patterns = [
            (r'eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+', 'jwt_token', 60),
            (r'Bearer\s+(eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+)', 'jwt_bearer', 65),
        ]
        
        # New: OAuth token patterns
        oauth_patterns = [
            (r'oauth_token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'oauth_token', 55),
            (r'oauth_token_secret["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'oauth_token_secret', 55),
            (r'refresh_token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9\-_\.]{20,})["\']?', 'refresh_token', 50),
        ]
        
        # Extract all patterns
        pattern_groups = [
            (instagram_patterns, 'instagram_sessions'),
            (facebook_patterns, 'facebook_sessions'),
            (auth_patterns, 'auth_tokens'),
            (device_patterns, 'device_sessions'),
            (csrf_patterns, 'csrf_tokens'),
            (user_patterns, 'user_identifiers'),
            (cookie_patterns, 'cookie_sessions'),
            (jwt_patterns, 'jwt_tokens'),
            (oauth_patterns, 'oauth_tokens')
        ]
        
        for patterns, session_type in pattern_groups:
            for pattern, token_type, confidence in patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    if len(match) > 3:
                        # Create session hash for deduplication
                        session_hash = hashlib.md5(f"{token_type}:{match}".encode()).hexdigest()
                        
                        if session_hash not in self.seen_session_hashes:
                            session_item = {
                                'type': token_type,
                                'value': match,
                                'pattern': pattern,
                                'found_in': f'content_analysis ({source_file_path})',
                                'timestamp': datetime.now().isoformat(),
                                'confidence': confidence
                            }
                            
                            self.session_data[session_type].append(session_item)
                            self.seen_session_hashes.add(session_hash)
                            
                            # Enhanced: Store all session IDs for logged-in user
                            if token_type in ['sessionid', 'sessionid_cookie', 'sessionid_set_cookie', 'sessionid_url']:
                                self.logged_in_user['all_session_ids'].append({
                                    'session_id': match,
                                    'source': source_file_path,
                                    'timestamp': datetime.now().isoformat()
                                })
                                
                                # Set primary session ID if not already set
                                if not self.logged_in_user['primary_instagram_session_id']:
                                    self.logged_in_user['primary_instagram_session_id'] = match
                                    print(f"🔑 Found primary session ID: {match[:10]}... from {source_file_path}")
                        
                        # Populate logged-in user data and potential user IDs
                        self._populate_logged_in_user_from_extracted_value(token_type, match, confidence, source_file_path)

    def extract_media_from_content(self, content, source_info):
        """Enhanced: Extract media URLs and references from content"""
        if not isinstance(content, str):
            return []
        
        found_media = []
        
        # Extract media URLs using enhanced patterns
        for pattern in self.media_patterns['media_urls']:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                media_item = {
                    'url': match,
                    'type': 'media_url',
                    'source': source_info,
                    'extracted_at': datetime.now().isoformat(),
                    'media_type': self._determine_media_type_from_url(match)
                }
                found_media.append(media_item)
        
        # Extract Instagram media IDs
        media_id_patterns = [
            r'media_id["\']?\s*[:=]\s*["\']?([0-9_]+)["\']?',
            r'instagram://media\?id=([0-9_]+)',
            r'pk["\']?\s*[:=]\s*["\']?([0-9_]+)["\']?',  # Primary key often used for media
        ]
        
        for pattern in media_id_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                media_item = {
                    'media_id': match,
                    'type': 'media_id',
                    'source': source_info,
                    'extracted_at': datetime.now().isoformat()
                }
                found_media.append(media_item)
        
        # Extract file paths that might be media
        file_path_patterns = [
            r'file://[^\s"\'<>]+\.(jpg|jpeg|png|gif|mp4|mov|webp|avi)',
            r'/[^\s"\'<>]*\.(jpg|jpeg|png|gif|mp4|mov|webp|avi)',
            r'[A-Za-z]:\\[^\s"\'<>]*\.(jpg|jpeg|png|gif|mp4|mov|webp|avi)',
        ]
        
        for pattern in file_path_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    file_path = match[0] if len(match) > 1 else match
                else:
                    file_path = match
                
                media_item = {
                    'file_path': file_path,
                    'type': 'local_media_path',
                    'source': source_info,
                    'extracted_at': datetime.now().isoformat(),
                    'media_type': self._determine_media_type_from_path(file_path)
                }
                found_media.append(media_item)
        
        return found_media

    def _determine_media_type_from_url(self, url):
        """Determine media type from URL"""
        url_lower = url.lower()
        if any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            return 'image'
        elif any(ext in url_lower for ext in ['.mp4', '.mov', '.avi', '.webm']):
            return 'video'
        elif any(ext in url_lower for ext in ['.mp3', '.wav', '.aac']):
            return 'audio'
        else:
            return 'unknown'

    def _determine_media_type_from_path(self, path):
        """Determine media type from file path"""
        extension = Path(path).suffix.lower()
        if extension in self.media_patterns['image_extensions']:
            return 'image'
        elif extension in self.media_patterns['video_extensions']:
            return 'video'
        elif extension in self.media_patterns['audio_extensions']:
            return 'audio'
        else:
            return 'unknown'

    def _populate_logged_in_user_from_extracted_value(self, key, value, confidence, source_file_path):
        """Helper to populate logged_in_user from extracted values and track potential user IDs."""
        if key in ['sessionid', 'sessionid_cookie', 'sessionid_set_cookie', 'sessionid_url'] and not self.logged_in_user['primary_instagram_session_id']:
            self.logged_in_user['primary_instagram_session_id'] = value
            self.logger.info(f"Found primary Instagram session ID: {value[:20]}... (Source: {source_file_path})")
        
        # Use the new priority setter for user IDs
        if key in ['user_id', 'ds_user_id', 'c_user', 'facebook_id', 'fb_user_id', 'user_pk', 'user_id_json'] and str(value).isdigit():
            self._set_logged_in_user_id_with_priority(value, confidence, f"Extracted value '{key}' from {source_file_path}")
            self._potential_user_ids[str(value)] += 1

        if key in ['username', 'username_json'] and not self.logged_in_user['username']:
            self.logged_in_user['username'] = value
            print(f"👤 Found username: {value} from {source_file_path}")
        elif key == 'email' and not self.logged_in_user['email']:
            self.logged_in_user['email'] = value
            print(f"📧 Found email: {value} from {source_file_path}")
        elif key == 'phone_number' and not self.logged_in_user['phone_number']:
            self.logged_in_user['phone_number'] = value
            print(f"📱 Found phone number: {value} from {source_file_path}")
        elif key in ['facebook_id', 'fb_user_id'] and value not in self.logged_in_user['linked_facebook_accounts']:
            self.logged_in_user['linked_facebook_accounts'].append(value)
        elif key in ['full_name', 'full_name_json'] and not self.logged_in_user['full_name']:
            self.logged_in_user['full_name'] = value
            print(f"👤 Found full name: {value} from {source_file_path}")
    
    def extract_server_ids(self, text_content):
        """Extract server IDs and endpoints from text content"""
        if not isinstance(text_content, str):
            return
        
        # Instagram API endpoints
        instagram_patterns = [
            r'https?://(?:www\.)?instagram\.com/[^\s"\'<>]+',
            r'https?://(?:www\.)?ig\.me/[^\s"\'<>]+',
            r'https?://(?:graph|api)\.instagram\.com/[^\s"\'<>]+',
            r'instagram://[^\s"\'<>]+',
        ]
        
        # CDN and media servers
        cdn_patterns = [
            r'https?://[^.\s]*\.cdninstagram\.com/[^\s"\'<>]+',
            r'https?://[^.\s]*\.fbcdn\.net/[^\s"\'<>]+',
            r'https?://scontent[^.\s]*\.xx\.fbcdn.net/[^\s"\'<>]+',
            r'https?://[^.\s]*\.instagram\.com/[^\s"\'<>]+',
        ]
        
        # WebSocket servers
        websocket_patterns = [
            r'wss?://[^.\s]*\.instagram\.com[^\s"\'<>]*',
            r'wss?://[^.\s]*\.facebook\.com[^\s"\'<>]*',
        ]
        
        # General API endpoints
        api_patterns = [
            r'https?://[^.\s]*\.facebook\.com/[^\s"\'<>]+',
            r'https?://api\.[^.\s]*\.com/[^\s"\'<>]+',
        ]
        
        # Extract all server patterns
        server_pattern_groups = [
            (instagram_patterns, 'instagram_servers', 'instagram_api'),
            (cdn_patterns, 'cdn_servers', 'cdn_media'),
            (websocket_patterns, 'websocket_servers', 'websocket'),
            (api_patterns, 'api_endpoints', 'api_endpoint')
        ]
        
        for patterns, server_type, server_category in server_pattern_groups:
            for pattern in patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    if match not in [item['url'] for item in self.server_data[server_type]]:
                        self.server_data[server_type].append({
                            'url': match,
                            'type': server_category,
                            'found_in': 'content_analysis',
                            'timestamp': datetime.now().isoformat()
                        })
    
    def parse_sqlite_database(self, db_path):
        """Parse SQLite database with comprehensive data extraction"""
        print(f"🔍 Parsing database: {db_path.name}")
        
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
            
            # Check if this database might contain user profile information
            is_profile_db = any(profile_table in [t.lower() for t in tables] for profile_table in self.user_profile_tables)
            is_session_db = any(session_table in [t.lower() for t in tables] for session_table in self.session_tables)
            
            if is_profile_db:
                print(f"   👤 Potential user profile database detected")
            if is_session_db:
                print(f"   🔑 Potential session database detected")
            
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
                    
                    # Check if this table might contain user profile information
                    table_lower = table.lower()
                    is_profile_table = any(profile_table in table_lower for profile_table in self.user_profile_tables)
                    is_session_table = any(session_table in table_lower for session_table in self.session_tables)
                    
                    if is_profile_table:
                        print(f"   👤 Potential user profile table: {table}")
                    if is_session_table:
                        print(f"   🔑 Potential session table: {table}")
                    
                    # Extract data (limit for performance)
                    if 0 < row_count <= 5000:
                        cursor.execute(f"SELECT * FROM `{table}` LIMIT 1000")
                        rows = cursor.fetchall()
                        
                        for row in rows:
                            row_dict = {}
                            for col, val in zip(columns, row):
                                processed_val = self.process_database_value(val)
                                row_dict[col] = processed_val
                                
                                # Enhanced: Extract session IDs and media from text values
                                if isinstance(processed_val, str):
                                    self.extract_session_ids(processed_val, db_path.name)
                                    # Extract media from database content
                                    media_items = self.extract_media_from_content(processed_val, {
                                        'type': 'database',
                                        'file': db_path.name,
                                        'table': table,
                                        'column': col
                                    })
                                    for media_item in media_items:
                                        self._add_chat_media_item(media_item, db_path.name, table)
                                        
                                elif isinstance(processed_val, dict) and processed_val.get('type') == 'decoded_text':
                                    self.extract_session_ids(processed_val['value'], db_path.name)
                                    # Extract media from decoded text
                                    media_items = self.extract_media_from_content(processed_val['value'], {
                                        'type': 'database_decoded',
                                        'file': db_path.name,
                                        'table': table,
                                        'column': col
                                    })
                                    for media_item in media_items:
                                        self._add_chat_media_item(media_item, db_path.name, table)
                            
                            table_data["rows"].append(row_dict)
                            
                            # Enhanced: Give higher priority to user profile tables
                            if is_profile_table:
                                self._populate_logged_in_user_from_db_row(row_dict, table, db_path.name, is_profile_table=True)
                            else:
                                self._populate_logged_in_user_from_db_row(row_dict, table, db_path.name)
                        
                        print(f"   ✅ Extracted {len(rows)} rows from '{table}'")
                    
                    elif row_count > 5000:
                        # For large tables, get sample data
                        cursor.execute(f"SELECT * FROM `{table}` LIMIT 10")
                        sample_rows = cursor.fetchall()
                        
                        for row in sample_rows:
                            row_dict = {}
                            for col, val in zip(columns, row):
                                processed_val = self.process_database_value(val)
                                row_dict[col] = processed_val
                            table_data["sample_data"].append(row_dict)
                            
                            # Enhanced: Give higher priority to user profile tables
                            if is_profile_table:
                                self._populate_logged_in_user_from_db_row(row_dict, table, db_path.name, is_profile_table=True)
                            else:
                                self._populate_logged_in_user_from_db_row(row_dict, table, db_path.name)
                        
                        table_data["note"] = f"Large table ({row_count} rows) - showing sample data only"
                        print(f"   📊 Large table '{table}' - sample data extracted")
                    
                    db_data["tables"][table] = table_data
                    
                except Exception as e:
                    print(f"   ❌ Error processing table '{table}': {e}")
                    db_data["tables"][table] = {"error": str(e)}
            
            conn.close()
            db_data["parsing_status"] = "success"
            print(f"✅ Database parsing complete: {db_path.name}")
            
        except Exception as e:
            error_msg = f"Database parsing failed: {e}"
            print(f"❌ {error_msg}")
            db_data["error"] = error_msg
            db_data["parsing_status"] = "error"
            self.logger.error(f"Database parsing error for {db_path}: {e}")
        
        return db_data

    def _add_chat_media_item(self, media_item, source_file, source_table):
        """Enhanced: Add media item found in chat context"""
        chat_media_item = {
            "source_folder": "database_extraction",
            "source_file": source_file,
            "source_table": source_table,
            "extracted_at": datetime.now().isoformat(),
            "type": "chat_media",
            "data": media_item
        }
        
        item_hash = self._get_dedupe_hash(chat_media_item["data"])
        if item_hash not in self.seen_chat_media_hashes:
            self.chat_media.append(chat_media_item)
            self.seen_chat_media_hashes.add(item_hash)

    def _populate_logged_in_user_from_db_row(self, row_data, source_table_name=None, source_file_name="", is_profile_table=False):
        """Enhanced: Helper to populate logged_in_user from a database row and track potential user IDs."""
        table_name_lower = source_table_name.lower() if source_table_name else ''
        
        # Track all potential user IDs for later finalization (fallback)
        for key in ['user_id', 'pk', 'id', 'owner_id', 'sender_id', 'receiver_id']:
            if key in row_data and isinstance(row_data[key], (int, str)) and str(row_data[key]).isdigit():
                self._potential_user_ids[str(row_data[key])] += 1
        
        # Determine confidence based on table name
        confidence = 50  # Default confidence for general DB tables
        
        # Enhanced: Higher confidence for profile tables
        if is_profile_table:
            confidence = 90  # Higher confidence for profile tables
            source_desc = f"User profile DB table '{source_table_name}' in {source_file_name}"
        elif any(k in table_name_lower for k in ['self_profile', 'current_user', 'my_account', 'user_info', 'account_info']):
            confidence = 95  # Even higher confidence for explicit self-profile tables
            source_desc = f"Self-profile DB table '{source_table_name}' in {source_file_name}"
        else:
            source_desc = f"DB table '{source_table_name}' in {source_file_name}"
        
        # Attempt to set logged-in user ID with priority
        if 'user_id' in row_data and str(row_data['user_id']).isdigit():
            self._set_logged_in_user_id_with_priority(row_data['user_id'], confidence, source_desc)
        elif 'pk' in row_data and str(row_data['pk']).isdigit() and any(k in table_name_lower for k in ['users', 'accounts']):
             self._set_logged_in_user_id_with_priority(row_data['pk'], confidence, source_desc)
        elif 'id' in row_data and str(row_data['id']).isdigit() and is_profile_table:
             self._set_logged_in_user_id_with_priority(row_data['id'], confidence - 5, source_desc)

        # If this row's user_id matches the currently identified logged-in user, populate profile details
        # OR if this is a profile table and we don't have a user ID yet
        if (self.logged_in_user['user_id'] and 'user_id' in row_data and str(row_data['user_id']) == str(self.logged_in_user['user_id'])) or is_profile_table:
            # Basic profile info
            if 'username' in row_data and not self.logged_in_user['username']:
                self.logged_in_user['username'] = row_data['username']
                print(f"👤 Found username: {row_data['username']} from {source_table_name}")
            if 'full_name' in row_data and not self.logged_in_user['full_name']:
                self.logged_in_user['full_name'] = row_data['full_name']
                print(f"👤 Found full name: {row_data['full_name']} from {source_table_name}")
            if 'email' in row_data and not self.logged_in_user['email']:
                self.logged_in_user['email'] = row_data['email']
                print(f"📧 Found email: {row_data['email']} from {source_table_name}")
            if 'phone_number' in row_data and not self.logged_in_user['phone_number']:
                self.logged_in_user['phone_number'] = row_data['phone_number']
                print(f"📱 Found phone number: {row_data['phone_number']} from {source_table_name}")
            if 'bio' in row_data and not self.logged_in_user['bio']:
                self.logged_in_user['bio'] = row_data['bio']
            if 'website' in row_data and not self.logged_in_user['website']:
                self.logged_in_user['website'] = row_data['website']
            
            # Profile picture
            if 'profile_pic_url' in row_data and row_data['profile_pic_url']:
                if row_data['profile_pic_url'] not in self.logged_in_user['profile_picture_paths']:
                    self.logged_in_user['profile_picture_paths'].append(row_data['profile_pic_url'])
                    if not self.logged_in_user['profile_picture_url']:
                        self.logged_in_user['profile_picture_url'] = row_data['profile_pic_url']
            
            # Account status
            if 'is_private' in row_data:
                self.logged_in_user['is_private'] = row_data['is_private']
            if 'is_verified' in row_data:
                self.logged_in_user['is_verified'] = row_data['is_verified']
            
            # Counts
            if 'follower_count' in row_data:
                self.logged_in_user['followers_count'] = int(row_data['follower_count']) if row_data['follower_count'] is not None else 0
                print(f"👥 Found followers count: {self.logged_in_user['followers_count']} from {source_table_name}")
            if 'following_count' in row_data:
                self.logged_in_user['following_count'] = int(row_data['following_count']) if row_data['following_count'] is not None else 0
                print(f"👤 Found following count: {self.logged_in_user['following_count']} from {source_table_name}")
            if 'media_count' in row_data:
                self.logged_in_user['posts_count'] = int(row_data['media_count']) if row_data['media_count'] is not None else 0
                print(f"📸 Found posts count: {self.logged_in_user['posts_count']} from {source_table_name}")
            
            # Alternative count field names
            if 'followers' in row_data and not self.logged_in_user['followers_count']:
                self.logged_in_user['followers_count'] = int(row_data['followers']) if row_data['followers'] is not None else 0
                print(f"👥 Found followers count: {self.logged_in_user['followers_count']} from {source_table_name}")
            if 'following' in row_data and not self.logged_in_user['following_count']:
                self.logged_in_user['following_count'] = int(row_data['following']) if row_data['following'] is not None else 0
                print(f"👤 Found following count: {self.logged_in_user['following_count']} from {source_table_name}")
            if 'posts' in row_data and not self.logged_in_user['posts_count']:
                self.logged_in_user['posts_count'] = int(row_data['posts']) if row_data['posts'] is not None else 0
                print(f"📸 Found posts count: {self.logged_in_user['posts_count']} from {source_table_name}")
            
            # Facebook linking
            if 'facebook_id' in row_data and row_data['facebook_id']:
                if row_data['facebook_id'] not in self.logged_in_user['linked_facebook_accounts']:
                    self.logged_in_user['linked_facebook_accounts'].append(row_data['facebook_id'])
            
            # Timestamps
            if 'created_at' in row_data:
                self.logged_in_user['account_creation_date'] = row_data['created_at']
            if 'last_login' in row_data:
                self.logged_in_user['last_login'] = row_data['last_login']
            
            # Device info
            if 'device_id' in row_data:
                self.logged_in_user['device_info']['device_id'] = row_data['device_id']
            if 'android_id' in row_data:
                self.logged_in_user['device_info']['android_id'] = row_data['android_id']
            
            # Store any additional user details
            for key, value in row_data.items():
                if key not in ['user_id', 'username', 'full_name', 'email', 'phone_number', 'bio', 'website', 
                              'profile_pic_url', 'is_private', 'is_verified', 'follower_count', 'following_count', 
                              'media_count', 'facebook_id', 'created_at', 'last_login', 'device_id', 'android_id',
                              'followers', 'following', 'posts']:
                    self.logged_in_user['other_user_details'][key] = value
    
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
    
    def parse_xml_file(self, xml_path):
        """Parse XML file with enhanced error handling and encoding support"""
        print(f"🔍 Parsing XML: {xml_path.name}")
        
        xml_data = {
            "file_info": self.get_file_info(xml_path),
            "content": {},
            "raw_text": "",
            "parsing_status": "unknown"
        }
        
        try:
            # Try multiple encodings
            encodings = ['utf-8', 'utf-16', 'utf-16le', 'utf-16be', 'latin-1', 'cp1252', 'iso-8859-1', 'ascii']
            content = None
            used_encoding = None
            
            for encoding in encodings:
                try:
                    with open(xml_path, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read()
                        used_encoding = encoding
                        break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if not content:
                # Final fallback: read as binary and decode with errors='replace'
                with open(xml_path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='replace')
                    used_encoding = 'utf-8-fallback'
            
            xml_data["encoding_used"] = used_encoding
            xml_data["raw_text"] = content[:10000]  # Store first 10000 chars
            
            # Enhanced: Extract session IDs, server IDs, and media from raw content
            self.extract_session_ids(content, xml_path.name)
            self.extract_server_ids(content)
            
            # Enhanced: Extract media from XML content
            media_items = self.extract_media_from_content(content, {
                'type': 'xml_file',
                'file': xml_path.name
            })
            for media_item in media_items:
                self._add_chat_media_item(media_item, xml_path.name, 'xml_content')
            
            # Try to parse as XML
            try:
                # Clean content for XML parsing
                cleaned_content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
                
                # Try parsing with ElementTree
                try:
                    root = ET.fromstring(cleaned_content)
                    xml_data["content"] = self.parse_xml_element(root, xml_path.name)
                    xml_data["parsing_status"] = "success_elementtree"
                except ET.ParseError:
                    # Try with BeautifulSoup as fallback
                    soup = BeautifulSoup(cleaned_content, 'xml')
                    xml_data["content"] = self.parse_soup_element(soup, xml_path.name)
                    xml_data["parsing_status"] = "success_beautifulsoup"
            
            except Exception as parse_error:
                # If XML parsing fails completely, extract as text
                xml_data["content"] = {
                    "raw_content": content,
                    "parsing_error": str(parse_error),
                    "treated_as": "text_file",
                    "text_lines": content.split('\n')[:100]  # First 100 lines
                }
                xml_data["parsing_status"] = "failed_treated_as_text"
            
            print(f"✅ XML processed: {xml_path.name} (encoding: {used_encoding}, status: {xml_data['parsing_status']})")
            
        except Exception as e:
            xml_data["error"] = str(e)
            xml_data["parsing_status"] = "error"
            print(f"❌ XML processing error: {e}")
        
        return xml_data
    
    def parse_xml_element(self, element, source_file_name=""):
        """Parse XML element recursively with enhanced media extraction"""
        result = {}
        
        if element.text and element.text.strip():
            text_content = element.text.strip()
            result["text"] = text_content
            self.extract_session_ids(text_content, source_file_name)
            self.extract_server_ids(text_content)
            
            # Enhanced: Extract media from XML text content
            media_items = self.extract_media_from_content(text_content, {
                'type': 'xml_element_text',
                'file': source_file_name,
                'element': element.tag
            })
            for media_item in media_items:
                self._add_chat_media_item(media_item, source_file_name, f'xml_element_{element.tag}')
        
        if element.attrib:
            result["attributes"] = element.attrib
            for attr_name, attr_value in element.attrib.items():
                if isinstance(attr_value, str):
                    self.extract_session_ids(attr_value, source_file_name)
                    self.extract_server_ids(attr_value)
                    
                    # Enhanced: Extract media from XML attributes
                    media_items = self.extract_media_from_content(attr_value, {
                        'type': 'xml_attribute',
                        'file': source_file_name,
                        'element': element.tag,
                        'attribute': attr_name
                    })
                    for media_item in media_items:
                        self._add_chat_media_item(media_item, source_file_name, f'xml_attr_{element.tag}_{attr_name}')
        
        if element:
            result["children"] = {}
            for child in element:
                if child.tag in result["children"]:
                    if not isinstance(result["children"][child.tag], list):
                        result["children"][child.tag] = [result["children"][child.tag]]
                    result["children"][child.tag].append(self.parse_xml_element(child, source_file_name))
                else:
                    result["children"][child.tag] = self.parse_xml_element(child, source_file_name)
    
        return result
    
    def parse_soup_element(self, soup, source_file_name=""):
        """Parse XML using BeautifulSoup with enhanced media extraction"""
        result = {}
        
        if soup.string:
            result["text"] = soup.string.strip()
            self.extract_session_ids(soup.string.strip(), source_file_name)
            self.extract_server_ids(soup.string.strip())
            
            # Enhanced: Extract media from soup text
            media_items = self.extract_media_from_content(soup.string.strip(), {
                'type': 'xml_soup_text',
                'file': source_file_name
            })
            for media_item in media_items:
                self._add_chat_media_item(media_item, source_file_name, 'xml_soup_content')
        
        if hasattr(soup, 'attrs') and soup.attrs:
            result["attributes"] = soup.attrs
            for attr_name, attr_value in soup.attrs.items():
                if isinstance(attr_value, str):
                    self.extract_session_ids(attr_value, source_file_name)
                    self.extract_server_ids(attr_value)
                    
                    # Enhanced: Extract media from soup attributes
                    media_items = self.extract_media_from_content(attr_value, {
                        'type': 'xml_soup_attribute',
                        'file': source_file_name,
                        'attribute': attr_name
                    })
                    for media_item in media_items:
                        self._add_chat_media_item(media_item, source_file_name, f'xml_soup_attr_{attr_name}')
        
        children = soup.find_all(recursive=False)
        if children:
            result["children"] = {}
            for child in children:
                tag_name = child.name if child.name else 'unknown'
                if tag_name in result["children"]:
                    if not isinstance(result["children"][tag_name], list):
                        result["children"][tag_name] = [result["children"][tag_name]]
                    result["children"][tag_name].append(self.parse_soup_element(child, source_file_name))
                else:
                    result["children"][tag_name] = self.parse_soup_element(child, source_file_name)
        
        return result
    
    def parse_html_file(self, html_path):
        """Parse HTML file with enhanced encoding support and media extraction"""
        print(f"🔍 Parsing HTML: {html_path.name}")
        
        html_data = {
            "file_info": self.get_file_info(html_path),
            "content": {},
            "raw_text": "",
            "parsing_status": "unknown"
        }
        
        try:
            # Try multiple encodings
            encodings = ['utf-8', 'utf-16', 'utf-16le', 'utf-16be', 'latin-1', 'cp1252', 'iso-8859-1', 'ascii']
            content = None
            used_encoding = None
            
            for encoding in encodings:
                try:
                    with open(html_path, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read()
                        used_encoding = encoding
                        break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if not content:
                # Final fallback: read as binary and decode with errors='replace'
                with open(html_path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='replace')
                    used_encoding = 'utf-8-fallback'
            
            html_data["encoding_used"] = used_encoding
            html_data["raw_text"] = content[:10000]  # Store first 10000 chars
            
            # Enhanced: Extract session IDs, server IDs, and media from raw content
            self.extract_session_ids(content, html_path.name)
            self.extract_server_ids(content)
            
            # Enhanced: Extract media from HTML content
            media_items = self.extract_media_from_content(content, {
                'type': 'html_file',
                'file': html_path.name
            })
            for media_item in media_items:
                self._add_chat_media_item(media_item, html_path.name, 'html_content')
            
            try:
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract comprehensive HTML data
                text_content = soup.get_text(strip=True)
                self.extract_session_ids(text_content, html_path.name)
                self.extract_server_ids(text_content)
                
                # Enhanced: Extract media from HTML text content
                media_items = self.extract_media_from_content(text_content, {
                    'type': 'html_text_content',
                    'file': html_path.name
                })
                for media_item in media_items:
                    self._add_chat_media_item(media_item, html_path.name, 'html_text')
                
                # Extract links
                links = []
                for a in soup.find_all('a', href=True):
                    link_data = {
                        "text": a.get_text(strip=True),
                        "href": a.get('href'),
                        "title": a.get('title', ''),
                        "target": a.get('target', '')
                    }
                    links.append(link_data)
                    self.extract_session_ids(a.get('href'), html_path.name)
                    self.extract_server_ids(a.get('href'))
                    
                    # Enhanced: Extract media from links
                    media_items = self.extract_media_from_content(a.get('href'), {
                        'type': 'html_link',
                        'file': html_path.name,
                        'link_text': a.get_text(strip=True)
                    })
                    for media_item in media_items:
                        self._add_chat_media_item(media_item, html_path.name, 'html_link')
                
                # Enhanced: Extract images with better media handling
                images = []
                for img in soup.find_all('img'):
                    img_data = {
                        "alt": img.get('alt', ''),
                        "src": img.get('src', ''),
                        "title": img.get('title', ''),
                        "width": img.get('width', ''),
                        "height": img.get('height', '')
                    }
                    images.append(img_data)
                    if img.get('src'):
                        self.extract_server_ids(img.get('src'))
                        
                        # Enhanced: Add image as media item
                        media_item = {
                            'url': img.get('src'),
                            'type': 'html_image',
                            'alt_text': img.get('alt', ''),
                            'source': {
                                'type': 'html_img_tag',
                                'file': html_path.name
                            },
                            'extracted_at': datetime.now().isoformat(),
                            'media_type': 'image'
                        }
                        self._add_chat_media_item(media_item, html_path.name, 'html_img_tag')
            
                # Enhanced: Extract scripts with media detection
                scripts = []
                for script in soup.find_all('script'):
                    script_data = {}
                    if script.get('src'):
                        script_data['src'] = script.get('src')
                        self.extract_server_ids(script.get('src'))
                    if script.string:
                        script_data['content'] = script.string[:2000]  # Limit content
                        self.extract_session_ids(script.string, html_path.name)
                        self.extract_server_ids(script.string)
                        
                        # Enhanced: Extract media from script content
                        media_items = self.extract_media_from_content(script.string, {
                            'type': 'html_script',
                            'file': html_path.name
                        })
                        for media_item in media_items:
                            self._add_chat_media_item(media_item, html_path.name, 'html_script')
                    scripts.append(script_data)
                
                # Extract meta tags
                meta_tags = []
                for meta in soup.find_all('meta'):
                    meta_data = {}
                    for attr in ['name', 'property', 'content', 'http-equiv', 'charset']:
                        if meta.get(attr):
                            meta_data[attr] = meta.get(attr)
                            self.extract_session_ids(str(meta.get(attr)), html_path.name)
                    if meta_data:
                        meta_tags.append(meta_data)
                
                # Extract forms
                forms = []
                for form in soup.find_all('form'):
                    form_data = {
                        'action': form.get('action', ''),
                        'method': form.get('method', ''),
                        'name': form.get('name', ''),
                        'id': form.get('id', ''),
                        'inputs': []
                    }
                    
                    for input_tag in form.find_all(['input', 'textarea', 'select']):
                        input_data = {
                            'tag': input_tag.name,
                            'type': input_tag.get('type', ''),
                            'name': input_tag.get('name', ''),
                            'value': input_tag.get('value', ''),
                            'id': input_tag.get('id', ''),
                            'placeholder': input_tag.get('placeholder', '')
                        }
                        if input_data['value']:
                            self.extract_session_ids(input_data['value'], html_path.name)
                        form_data['inputs'].append(input_data) 
                    
                    forms.append(form_data) 
                
                html_data["content"] = {
                    "title": soup.title.string if soup.title else "",
                    "text": text_content,
                    "links": links,
                    "images": images,
                    "scripts": scripts,
                    "meta_tags": meta_tags,
                    "forms": forms,
                    "tables": len(soup.find_all('table')),
                    "divs": len(soup.find_all('div')),
                    "spans": len(soup.find_all('span'))
                }
                html_data["parsing_status"] = "success"
                
            except Exception as parse_error:
                # If HTML parsing fails, treat as text
                html_data["content"] = {
                    "raw_content": content,
                    "parsing_error": str(parse_error),
                    "treated_as": "text_file",
                    "text_lines": content.split('\n')[:100]  # First 100 lines
                }
                html_data["parsing_status"] = "failed_treated_as_text"
            
            print(f"✅ HTML processed: {html_path.name} (encoding: {used_encoding}, status: {html_data['parsing_status']})")
            
        except Exception as e:
            html_data["error"] = str(e)
            html_data["parsing_status"] = "error"
            print(f"❌ HTML processing error: {e}")
        
        return html_data
    
    def parse_text_file(self, file_path):
        """Parse text-based files with enhanced media extraction"""
        print(f"🔍 Parsing text file: {file_path.name}")
        
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
            
            # Enhanced: Extract session IDs, server IDs, and media
            self.extract_session_ids(content, file_path.name)
            self.extract_server_ids(content)
            
            # Enhanced: Extract media from text content
            media_items = self.extract_media_from_content(content, {
                'type': 'text_file',
                'file': file_path.name
            })
            for media_item in media_items:
                self._add_chat_media_item(media_item, file_path.name, 'text_content')
            
            text_data["content"] = {
                "encoding_used": used_encoding,
                "text": content[:10000],  # First 10000 chars
                "full_text": content if len(content) < 50000 else None,  # Full text if small
                "line_count": len(content.split('\n')),
                "character_count": len(content),
                "word_count": len(content.split())
            }
            text_data["parsing_status"] = "success"
            
            print(f"✅ Text file processed: {file_path.name}")
            
        except Exception as e:
            text_data["error"] = str(e)
            text_data["parsing_status"] = "error"
            print(f"❌ Text file processing error: {e}")
        
        return text_data
    
    def process_folder_files(self, folder_path, folder_name):
        """Process all files in a specific folder with enhanced media detection"""
        print(f"\n📁 Processing folder: {folder_name}")
        
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
                "file_types": defaultdict(int),
                "media_files_found": 0  # Enhanced: Track media files
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
                    
                    # Enhanced: Track media files
                    if self.is_media_file(file_path):
                        folder_data["statistics"]["media_files_found"] += 1
                    
                    # Process based on file type
                    if file_extension == '.db':
                        file_data = self.parse_sqlite_database(file_path)
                    elif file_extension == '.xml':
                        file_data = self.parse_xml_file(file_path)
                    elif file_extension in ['.html', '.htm']:
                        file_data = self.parse_html_file(file_path)
                    elif file_extension in ['.txt', '.log', '.json', '.js', '.css', '.properties', '.conf']:
                        file_data = self.parse_text_file(file_path)
                    # Handle potential encrypted files and unencrypted media files
                    elif file_extension in ['.crypt', '.enc', '.dat']:
                        file_data = {
                            "file_info": self.get_file_info(file_path),
                            "content": "Encrypted file. This tool does not support decryption of proprietary Instagram media files.",
                            "parsing_status": "encrypted_undecryptable"
                        }
                        self.errors.append({
                            "file": str(file_path),
                            "error": "Proprietary encryption detected, decryption not supported by this tool.",
                            "timestamp": datetime.now().isoformat()
                        })
                    elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi', '.webp']:
                        file_data = {
                            "file_info": self.get_file_info(file_path),
                            "content": "Unencrypted media file.",
                            "parsing_status": "unencrypted_media"
                        }
                        # Enhanced: Add to media artifacts directly with better categorization
                        media_item = {
                            "source_folder": folder_name,
                            "source_file": file_path.name,
                            "extracted_at": datetime.now().isoformat(),
                            "type": "unencrypted_media_file",
                            "data": {
                                "local_file_path": str(file_path),
                                "mime_type": file_data["file_info"]["mime_type"],
                                "size": file_data["file_info"]["size_human"],
                                "media_type": self._determine_media_type_from_path(str(file_path))
                            },
                            "view_link": file_data["file_info"]["view_link"],
                            "status": "found_unencrypted_and_linked"
                        }
                        item_hash = self._get_dedupe_hash(media_item["data"])
                        if item_hash not in self.seen_media_hashes:
                            self.media.append(media_item)
                            self.seen_media_hashes.add(item_hash)
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
            
            print(f"✅ Folder processed: {folder_name}")
            print(f"   📄 Files: {folder_data['statistics']['processed_files']}/{folder_data['statistics']['total_files']}")
            print(f"   🎬 Media files: {folder_data['statistics']['media_files_found']}")
            print(f"   ❌ Errors: {folder_data['statistics']['failed_files']}")
            
        except Exception as e:
            folder_data["error"] = str(e)
            print(f"❌ Folder processing error: {e}")
        
        return folder_data
    
    def save_folder_as_json(self, folder_data):
        """Save folder data as separate JSON file with a descriptive name based on its full relative path."""
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
    
    def _get_dedupe_hash(self, data_dict):
        """Generates a stable hash for a dictionary for deduplication."""
        return hashlib.sha256(json.dumps(data_dict, sort_keys=True, default=str).encode('utf-8')).hexdigest()

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

    def download_media_files(self):
        """Enhanced: Copies identified unencrypted media files to a dedicated output directory."""
        print(f"\n⬇️ Attempting to download unencrypted media files to: {self.downloaded_media_dir}")
        downloaded_count = 0
        skipped_count = 0

        # Download regular media files
        for media_item in self.media:
            if media_item.get("status") == "found_unencrypted_and_linked" and media_item.get("view_link"):
                original_path_str = media_item["view_link"].replace("file:///", "")
                original_path = Path(original_path_str)

                if original_path.is_file() and original_path.exists():
                    try:
                        # Create a unique filename to avoid overwrites, preserving original extension
                        file_hash = hashlib.md5(str(original_path).encode()).hexdigest()[:8]
                        new_filename = f"{original_path.stem}_{file_hash}{original_path.suffix}"
                        destination_path = self.downloaded_media_dir / new_filename
                        
                        shutil.copy2(original_path, destination_path)
                        media_item["downloaded_path"] = str(destination_path)
                        downloaded_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to copy media file {original_path}: {e}")
                        media_item["download_error"] = str(e)
                        skipped_count += 1
                else:
                    skipped_count += 1
            else:
                skipped_count += 1
        
        # Enhanced: Also download chat media files
        chat_media_downloaded = 0
        for chat_media_item in self.chat_media:
            data = chat_media_item.get("data", {})
            if data.get("type") == "local_media_path" and data.get("file_path"):
                original_path = Path(data["file_path"])
                
                if original_path.is_file() and original_path.exists():
                    try:
                        file_hash = hashlib.md5(str(original_path).encode()).hexdigest()[:8]
                        new_filename = f"chat_{original_path.stem}_{file_hash}{original_path.suffix}"
                        destination_path = self.chat_media_dir / new_filename
                        
                        shutil.copy2(original_path, destination_path)
                        chat_media_item["downloaded_path"] = str(destination_path)
                        chat_media_downloaded += 1
                    except Exception as e:
                        self.logger.error(f"Failed to copy chat media file {original_path}: {e}")
                        chat_media_item["download_error"] = str(e)
        
        print(f"✅ Media download complete:")
        print(f"   📸 Regular media: {downloaded_count} files downloaded, {skipped_count} skipped")
        print(f"   💬 Chat media: {chat_media_downloaded} files downloaded")
        if downloaded_count > 0:
            print(f"   📂 Regular media location: {self.downloaded_media_dir}")
        if chat_media_downloaded > 0:
            print(f"   📂 Chat media location: {self.chat_media_dir}")

    def open_file_in_os_default_viewer(self, file_path):
        """Opens a file using the operating system's default viewer."""
        try:
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                os.system(f"open \"{file_path}\"")
            else:  # Linux and other Unix-like systems
                os.system(f"xdg-open \"{file_path}\"")
            print(f"🚀 Attempted to open: {file_path}")
        except Exception as e:
            print(f"❌ Failed to open file {file_path}: {e}")
            print("   Please try opening the file manually using its path.")

    def _finalize_logged_in_user_id(self):
        """
        Finalizes the logged-in user ID. If not already set by a high-confidence source,
        it falls back to the most frequently encountered user ID.
        """
        if self.logged_in_user['user_id'] is None:
            if self._potential_user_ids:
                most_common_id = max(self._potential_user_ids, key=self._potential_user_ids.get)
                self._set_logged_in_user_id_with_priority(most_common_id, 10, "Most frequent ID (fallback)")
            else:
                self.logger.info("No potential user IDs found during initial scan, logged-in user ID remains unidentified.")
        
        if self.logged_in_user['user_id']:
            print(f"\nFinalized Logged-in User ID: {self.logged_in_user['user_id']} (Source: {self.logged_in_user['user_id_source']})")
        else:
            print("\n⚠️ Logged-in User ID could not be definitively identified.")

    def extract_all_data(self):
        """Enhanced: Main extraction method for V5 - Focus on logged-in user with enhanced media and session extraction"""
        print("\n🚀 Starting Instagram V5 Enhanced Analysis - Media & Session Focus...")
        
        # Find Instagram folder
        self.instagram_folder = self.find_instagram_folder()
        
        if not self.instagram_folder:
            print("⚠️ No Instagram folder found")
            return {"status": "no_instagram_data", "message": "No Instagram folder found"}
        
        print(f"\n📁 Processing Instagram folder: {self.instagram_folder}")
        
        # Analyze complete folder structure
        self.analyze_folder_structure()
        
        # Process each folder and create separate JSON files
        self._process_folder_recursive(self.instagram_folder)
        
        # Finalize logged-in user ID after all initial parsing
        self._finalize_logged_in_user_id()

        # Organize extracted data with focus on logged-in user
        self.organize_extracted_data()

        # Calculate user counts (followers/following separately)
        self._calculate_user_counts()
        
        # Enhanced: Prepare statistics with new session types
        session_stats = {
            "total_instagram_sessions": len(self.session_data['instagram_sessions']),
            "total_facebook_sessions": len(self.session_data['facebook_sessions']),
            "total_auth_tokens": len(self.session_data['auth_tokens']),
            "total_device_sessions": len(self.session_data['device_sessions']),
            "total_csrf_tokens": len(self.session_data['csrf_tokens']),
            "total_user_identifiers": len(self.session_data['user_identifiers']),
            "total_api_keys": len(self.session_data['api_keys']),
            "total_other_sessions": len(self.session_data['other_sessions']),
            "total_cookie_sessions": len(self.session_data['cookie_sessions']),
            "total_jwt_tokens": len(self.session_data['jwt_tokens']),
            "total_oauth_tokens": len(self.session_data['oauth_tokens']),
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        server_stats = {
            "total_instagram_servers": len(self.server_data['instagram_servers']),
            "total_api_endpoints": len(self.server_data['api_endpoints']),
            "total_cdn_servers": len(self.server_data['cdn_servers']),
            "total_media_servers": len(self.server_data['media_servers']),
            "total_websocket_servers": len(self.server_data['websocket_servers']),
            "total_other_servers": len(self.server_data['other_servers']),
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        # Enhanced: Save main data files with focus on logged-in user and enhanced media/session data
        
        # 1. LOGGED-IN USER PROFILE (TOP PRIORITY) - Enhanced with all session IDs
        logged_in_user_output = {
            "description": "Complete profile information for the logged-in Instagram user extracted from the device data",
            "logged_in_user": self.logged_in_user,
            "extraction_summary": {
                "user_id_found": bool(self.logged_in_user['user_id']),
                "username_found": bool(self.logged_in_user['username']),
                "email_found": bool(self.logged_in_user['email']),
                "phone_found": bool(self.logged_in_user['phone_number']),
                "session_id_found": bool(self.logged_in_user['primary_instagram_session_id']),
                "all_session_ids_count": len(self.logged_in_user['all_session_ids']),
                "followers_count": self.logged_in_user['followers_count'],
                "following_count": self.logged_in_user['following_count'],
                "posts_count": self.logged_in_user['posts_count'],
                "user_id_confidence": self.logged_in_user['user_id_confidence'],
                "user_id_source": self.logged_in_user['user_id_source']
            }
        }
        self.save_json_data(logged_in_user_output, "logged_in_user_profile.json")
        print(f"✅ Logged-in User Profile saved: logged_in_user_profile.json")

        # 2. Enhanced Session IDs (with primary session highlighted and all session types)
        session_output = {
            "description": "Session identifiers and authentication tokens found during extraction",
            "primary_instagram_session_id": self.logged_in_user['primary_instagram_session_id'],
            "all_session_ids_for_user": self.logged_in_user['all_session_ids'],
            "logged_in_user_id": self.logged_in_user['user_id'],
            "statistics": session_stats,
            "sessions": self.session_data
        }
        self.save_json_data(session_output, "session_ids.json")
        print(f"✅ Session IDs saved: session_ids.json")
        
        # 3. Server IDs
        server_output = {
            "statistics": server_stats,
            "servers": self.server_data
        }
        self.save_json_data(server_output, "server_ids.json")
        print(f"✅ Server IDs saved: server_ids.json")
        
        # 4. Complete file system structure
        self.save_json_data(self.file_system_structure, "file_system_structure.json")
        print(f"✅ File system structure saved: file_system_structure.json")
        
        # 5. Enhanced: Organized data - SEPARATE chats, media, and chat media
        self.save_json_data(self.chats, "chats.json")
        print(f"✅ Chats saved: chats.json ({len(self.chats)} items)")
        
        self.save_json_data(self.media, "media.json")
        print(f"✅ Media saved: media.json ({len(self.media)} items)")
        
        # Enhanced: Save chat media separately
        self.save_json_data(self.chat_media, "chat_media.json")
        print(f"✅ Chat Media saved: chat_media.json ({len(self.chat_media)} items)")
        
        # 6. Complete folder data
        self.save_json_data(self.folder_data, "complete_folder_analysis.json")
        print(f"✅ Complete folder analysis saved: complete_folder_analysis.json")
        
        # Enhanced: Generate final report with logged-in user focus and enhanced media/session stats
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
            "file_system_analysis": {
                "total_folders": self.file_system_structure["total_folders"],
                "total_files": self.file_system_structure["total_files"],
                "file_types": self.file_system_structure["file_types"]
            },
            "folder_json_files": len(self.folder_data),
            "organized_data": {
                "chats": len(self.chats),
                "media": len(self.media),
                "chat_media": len(self.chat_media),  # Enhanced: Include chat media count
                "followers_count_in_profile": self.logged_in_user['followers_count'],
                "following_count_in_profile": self.logged_in_user['following_count']
            },
            "session_data": session_stats,
            "server_data": server_stats,
            "errors": len(self.errors),
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        self.save_json_data(extraction_report, "extraction_report.json")
        
        return extraction_report
    
    def organize_extracted_data(self):
        """Enhanced: Organize extracted data from all folders with focus on logged-in user and enhanced media extraction"""
        print("\n📂 Organizing extracted data with enhanced media and session focus...")
        
        # Process all folder data to extract Instagram artifacts
        for folder_key, folder_data in self.folder_data.items():
            if "files" not in folder_data:
                continue
            
            for file_name, file_data in folder_data["files"].items():
                try:
                    # Process database files
                    if file_data.get("parsing_status") == "success" and "tables" in file_data:
                        self.extract_artifacts_from_database(file_data, folder_key, file_name)
                    
                    # Process XML/HTML files
                    elif file_data.get("parsing_status") in ["success", "success_elementtree", "success_beautifulsoup", "failed_treated_as_text"]:
                        self.extract_artifacts_from_structured_file(file_data, folder_key, file_name)
                    
                    # Process text files
                    elif file_data.get("parsing_status") == "success" and "content" in file_data:
                        self.extract_artifacts_from_text_file(file_data, folder_key, file_name)
                
                except Exception as e:
                    print(f"⚠️ Error organizing data from {folder_key}/{file_name}: {e}")
        
        print(f"   📨 Total chats: {len(self.chats)}")
        print(f"   📸 Total media: {len(self.media)}")
        print(f"   💬 Total chat media: {len(self.chat_media)}")
        print(f"   👥 Total followers (for counts): {len(self.followers_list)}")
        print(f"   👤 Total following (for counts): {len(self.following_list)}")

    def _calculate_user_counts(self):
        """Calculate followers, following, and pending request counts for the logged-in user."""
        print("\n📊 Calculating user profile counts...")
        
        if self.logged_in_user['user_id']:
            logged_in_uid = str(self.logged_in_user['user_id'])
            
            # Update counts based on extracted lists
            self.logged_in_user['followers_count'] = len(self.followers_list)
            self.logged_in_user['following_count'] = len(self.following_list)

            # Try to find more accurate counts from database tables
            for folder_key, folder_data in self.folder_data.items():
                for file_name, file_data in folder_data.get("files", {}).items():
                    if file_data.get("parsing_status") == "success" and "tables" in file_data:
                        for table_name, table_content in file_data["tables"].items():
                            table_name_lower = table_name.lower()
                            
                            # Look for count tables
                            if any(keyword in table_name_lower for keyword in ['count', 'stats', 'profile_info']):
                                if "rows" in table_content:
                                    for row in table_content["rows"]:
                                        # Check if this row belongs to logged-in user
                                        if 'user_id' in row and str(row['user_id']) == logged_in_uid:
                                            if 'follower_count' in row and row['follower_count'] is not None:
                                                self.logged_in_user['followers_count'] = int(row['follower_count'])
                                            if 'following_count' in row and row['following_count'] is not None:
                                                self.logged_in_user['following_count'] = int(row['following_count'])
                                            if 'media_count' in row and row['media_count'] is not None:
                                                self.logged_in_user['posts_count'] = int(row['media_count'])

            # Attempt to find pending requests (heuristic-based)
            pending_incoming_count = 0
            pending_outgoing_count = 0

            # Search through all extracted data for keywords related to pending requests
            for folder_key, folder_data in self.folder_data.items():
                for file_name, file_data in folder_data.get("files", {}).items():
                    content_to_search = ""
                    if file_data.get("parsing_status") == "success" and "tables" in file_data:
                        for table_name, table_content in file_data["tables"].items():
                            if "rows" in table_content:
                                for row in table_content["rows"]:
                                    content_to_search += json.dumps(row, default=str)
                    elif "raw_text" in file_data.get("content", {}):
                        content_to_search = file_data["content"]["raw_text"]
                    elif "text" in file_data.get("content", {}):
                        content_to_search = file_data["content"]["text"]

                    content_to_search_lower = content_to_search.lower()

                    # Look for patterns indicating pending requests
                    if "pending_request" in content_to_search_lower or "follow_request" in content_to_search_lower:
                        if logged_in_uid in content_to_search:
                            if "incoming" in content_to_search_lower or "to_accept" in content_to_search_lower:
                                pending_incoming_count += 1
                            if "outgoing" in content_to_search_lower or "sent_by_you" in content_to_search_lower:
                                pending_outgoing_count += 1
            
            self.logged_in_user['pending_incoming_requests_count'] = pending_incoming_count
            self.logged_in_user['pending_outgoing_requests_count'] = pending_outgoing_count
            
            print(f"   👤 Logged-in User: {self.logged_in_user['username'] or self.logged_in_user['user_id']}")
            print(f"   👥 Followers: {self.logged_in_user['followers_count']}")
            print(f"   👤 Following: {self.logged_in_user['following_count']}")
            print(f"   📸 Posts: {self.logged_in_user['posts_count']}")
            print(f"   📥 Pending Incoming Requests: {self.logged_in_user['pending_incoming_requests_count']}")
            print(f"   📤 Pending Outgoing Requests: {self.logged_in_user['pending_outgoing_requests_count']}")
        else:
            print("   ⚠️ Logged-in user ID not identified, skipping count calculation.")

    def extract_artifacts_from_database(self, db_data, folder_key, file_name):
        """Enhanced: Extract artifacts from database data with focus on logged-in user and enhanced media extraction"""
        for table_name, table_data in db_data.get("tables", {}).items():
            if not isinstance(table_data, dict) or "rows" not in table_data:
                continue
            
            rows = table_data["rows"]
            if not rows:
                continue
            
            table_lower = table_name.lower()
            
            # Check if this is a profile or session table
            is_profile_table = any(profile_table in table_lower for profile_table in self.user_profile_tables)
            is_session_table = any(session_table in table_lower for session_table in self.session_tables)
            
            if is_profile_table:
                print(f"👤 Processing profile table: {table_name} in {file_name}")
            if is_session_table:
                print(f"🔑 Processing session table: {table_name} in {file_name}")
            
            for row in rows:
                artifact_base = {
                    "source_folder": folder_key,
                    "source_file": file_name,
                    "source_table": table_name,
                    "extracted_at": datetime.now().isoformat()
                }
                
                # Enhanced: Extract media from each row's content
                row_content = json.dumps(row, default=str)
                media_items = self.extract_media_from_content(row_content, {
                    'type': 'database_row',
                    'file': file_name,
                    'table': table_name
                })
                for media_item in media_items:
                    self._add_chat_media_item(media_item, file_name, table_name)
                
                # Categorize and deduplicate with focus on logged-in user
                if any(keyword in table_lower for keyword in 
                      ['message', 'thread', 'conversation', 'chat', 'direct', 'dm']):
                    chat_item = {**artifact_base, "type": "direct_message", "data": row}
                    item_hash = self._get_dedupe_hash(chat_item["data"])
                    if item_hash not in self.seen_chat_hashes:
                        # Enhanced: Determine if sent or received by the logged-in user
                        logged_in_uid = self.logged_in_user['user_id']
                        sender_id = str(row.get("sender_id") or row.get("user_id"))
                        
                        if logged_in_uid:
                            if sender_id == str(logged_in_uid):
                                chat_item["direction"] = "sent"
                            elif 'participants' in row and str(logged_in_uid) in str(row['participants']):
                                chat_item["direction"] = "received"
                            elif 'receiver_id' in row and str(row['receiver_id']) == str(logged_in_uid):
                                chat_item["direction"] = "received"
                            else:
                                chat_item["direction"] = "participant"
                        else:
                            chat_item["direction"] = "unknown"

                        # Enhanced: Extract media from chat content
                        chat_content = str(row.get('content', '')) + str(row.get('text', '')) + str(row.get('message', ''))
                        if chat_content:
                            chat_media_items = self.extract_media_from_content(chat_content, {
                                'type': 'chat_message_content',
                                'file': file_name,
                                'table': table_name,
                                'message_id': row.get('id', 'unknown')
                            })
                            for media_item in chat_media_items:
                                media_item['chat_context'] = {
                                    'sender_id': sender_id,
                                    'direction': chat_item["direction"],
                                    'timestamp': row.get('timestamp', 'unknown')
                                }
                                self._add_chat_media_item(media_item, file_name, f"{table_name}_chat_content")

                        self.chats.append(chat_item)
                        self.seen_chat_hashes.add(item_hash)
                
                elif any(keyword in table_lower for keyword in 
                        ['media', 'photo', 'video', 'image', 'picture', 'story', 'post']):
                    media_item = {**artifact_base, "type": "media_metadata", "data": row}
                    item_hash = self._get_dedupe_hash(media_item["data"])
                    if item_hash not in self.seen_media_hashes:
                        # Enhanced: Add view link if a local file path is present and exists
                        local_file_path = row.get("local_file_path") or row.get("file_path") or row.get("path")
                        if local_file_path:
                            resolved_path = Path(local_file_path).resolve()
                            if resolved_path.is_file() and resolved_path.exists():
                                media_item["view_link"] = f"file:///{resolved_path}"
                                media_item["status"] = "found_unencrypted_and_linked"
                            else:
                                media_item["status"] = "path_found_but_file_missing_or_encrypted"
                        else:
                            media_item["status"] = "metadata_only"

                        # Enhanced: Determine media type from database metadata
                        media_type = row.get('media_type') or row.get('type')
                        if media_type:
                            media_item["media_type"] = media_type
                        elif local_file_path:
                            media_item["media_type"] = self._determine_media_type_from_path(local_file_path)

                        self.media.append(media_item)
                        self.seen_media_hashes.add(item_hash)
                    
                    # Link media to logged-in user profile if it belongs to them
                    if self.logged_in_user['user_id'] and 'user_id' in row:
                        if str(row['user_id']) == str(self.logged_in_user['user_id']):
                            self.logged_in_user['posts_media_metadata'].append({
                                "source_file": file_name,
                                "source_table": table_name,
                                "media_id": row.get('media_id'),
                                "url": row.get('url'),
                                "caption": row.get('caption'),
                                "timestamp": row.get('timestamp'),
                                "local_file_path": local_file_path,
                                "view_link": media_item.get("view_link"),
                                "media_type": media_item.get("media_type")
                            })
            
                elif any(keyword in table_lower for keyword in 
                        ['follower', 'following', 'friend', 'user_relation', 'connection']):
                    
                    # Determine if this is a follower or following relationship
                    row_str = str(row).lower()
                    logged_in_uid = str(self.logged_in_user['user_id']) if self.logged_in_user['user_id'] else None
                    
                    # Check if this row involves the logged-in user
                    if logged_in_uid:
                        # Follower: someone who follows the logged-in user
                        if (('follower_id' in row and str(row['follower_id']) != logged_in_uid and 
                             'followed_id' in row and str(row['followed_id']) == logged_in_uid) or
                            ('from_user_id' in row and str(row['from_user_id']) != logged_in_uid and
                             'to_user_id' in row and str(row['to_user_id']) == logged_in_uid and
                             any(keyword in row_str for keyword in ['follow', 'follower']))):
                            
                            follower_item = {**artifact_base, "type": "follower", "data": row}
                            item_hash = self._get_dedupe_hash(follower_item["data"])
                            if item_hash not in self.seen_follower_hashes:
                                self.followers_list.append(follower_item)
                                self.seen_follower_hashes.add(item_hash)
                        
                        # Following: someone the logged-in user follows
                        elif (('follower_id' in row and str(row['follower_id']) == logged_in_uid and 
                               'followed_id' in row and str(row['followed_id']) != logged_in_uid) or
                              ('from_user_id' in row and str(row['from_user_id']) == logged_in_uid and
                               'to_user_id' in row and str(row['to_user_id']) != logged_in_uid and
                               any(keyword in row_str for keyword in ['follow', 'following']))):
                            
                            following_item = {**artifact_base, "type": "following", "data": row}
                            item_hash = self._get_dedupe_hash(following_item["data"])
                            if item_hash not in self.seen_following_hashes:
                                self.following_list.append(following_item)
                                self.seen_following_hashes.add(item_hash)
                    
                    # If we can't determine the relationship clearly, add to both with low confidence
                    else:
                        if any(keyword in row_str for keyword in ['follower', 'followed_by']):
                            follower_item = {**artifact_base, "type": "potential_follower", "confidence": "low", "data": row}
                            item_hash = self._get_dedupe_hash(follower_item["data"])
                            if item_hash not in self.seen_follower_hashes:
                                self.followers_list.append(follower_item)
                                self.seen_follower_hashes.add(item_hash)
                        
                        if any(keyword in row_str for keyword in ['following', 'you_follow']):
                            following_item = {**artifact_base, "type": "potential_following", "confidence": "low", "data": row}
                            item_hash = self._get_dedupe_hash(following_item["data"])
                            if item_hash not in self.seen_following_hashes:
                                self.following_list.append(following_item)
                                self.seen_following_hashes.add(item_hash)

    def extract_artifacts_from_structured_file(self, file_data, folder_key, file_name):
        """Enhanced: Extract artifacts from XML/HTML files with enhanced media extraction"""
        artifact_base = {
            "source_folder": folder_key,
            "source_file": file_name,
            "extracted_at": datetime.now().isoformat()
        }
        
        # Extract user details from structured content
        content_to_search = ""
        if file_data.get("parsing_status") in ["success_elementtree", "success_beautifulsoup"]:
            content_to_search = json.dumps(file_data.get("content", {}), default=str)
        elif file_data.get("parsing_status") == "failed_treated_as_text":
            content_to_search = file_data.get("content", {}).get("raw_content", "")
        
        self.extract_session_ids(content_to_search, file_name)
        
        # Enhanced: Extract media from structured content
        media_items = self.extract_media_from_content(content_to_search, {
            'type': 'structured_file_content',
            'file': file_name
        })
        for media_item in media_items:
            self._add_chat_media_item(media_item, file_name, 'structured_content')
        
        # Check if this looks like a chat/message file
        file_name_lower = file_name.lower()
        if any(keyword in file_name_lower for keyword in ['message', 'chat', 'direct', 'conversation']):
            chat_item = {**artifact_base, "type": "structured_chat", "data": file_data.get("content", {})}
            item_hash = self._get_dedupe_hash(chat_item["data"])
            if item_hash not in self.seen_chat_hashes:
                # Enhanced: Determine if sent or received by the logged-in user
                logged_in_uid = self.logged_in_user['user_id']
                if logged_in_uid and str(logged_in_uid) in content_to_search:
                    chat_item["direction"] = "involved"
                else:
                    chat_item["direction"] = "unknown"

                # Enhanced: Extract media from chat file content
                chat_media_items = self.extract_media_from_content(content_to_search, {
                    'type': 'structured_chat_file',
                    'file': file_name
                })
                for media_item in chat_media_items:
                    media_item['chat_context'] = {
                        'file_type': 'structured_chat',
                        'direction': chat_item["direction"]
                    }
                    self._add_chat_media_item(media_item, file_name, 'structured_chat_content')

                self.chats.append(chat_item)
                self.seen_chat_hashes.add(item_hash)
        
        # Check if this looks like media file
        elif any(keyword in file_name_lower for keyword in ['media', 'photo', 'video', 'image']):
            media_item = {**artifact_base, "type": "structured_media", "data": file_data.get("content", {})}
            item_hash = self._get_dedupe_hash(media_item["data"])
            if item_hash not in self.seen_media_hashes:
                # Enhanced: Add view link if the file itself is a media file
                file_info = file_data.get("file_info", {})
                if file_info.get("mime_type", "").startswith(("image/", "video/")) and file_info.get("path"):
                    media_item["view_link"] = f"file:///{Path(file_info['path']).resolve()}"
                    media_item["status"] = "found_unencrypted_and_linked"
                    media_item["media_type"] = self._determine_media_type_from_path(file_info['path'])
                else:
                    media_item["status"] = "metadata_only"

                self.media.append(media_item)
                self.seen_media_hashes.add(item_hash)
            
            # Link media to logged-in user profile
            if file_data.get("file_info", {}).get("mime_type", "").startswith(("image/", "video/")):
                self.logged_in_user['posts_media_metadata'].append({
                    "source_file": file_name,
                    "path": file_data.get("file_info", {}).get("path"),
                    "mime_type": file_data.get("file_info", {}).get("mime_type"),
                    "view_link": media_item.get("view_link"),
                    "media_type": media_item.get("media_type")
                })
            
            # Check for profile picture patterns
            if re.search(r'(profile_picture|avatar|pfp)\.(jpg|jpeg|png|gif)', file_name_lower):
                file_path = file_data.get("file_info", {}).get("path")
                if file_path and file_path not in self.logged_in_user['profile_picture_paths']:
                    self.logged_in_user['profile_picture_paths'].append(file_path)

    def extract_artifacts_from_text_file(self, file_data, folder_key, file_name):
        """Enhanced: Extract artifacts from text files with enhanced media extraction"""
        artifact_base = {
            "source_folder": folder_key,
            "source_file": file_name,
            "extracted_at": datetime.now().isoformat()
        }
        
        text_content = file_data.get("content", {}).get("text", "")
        self.extract_session_ids(text_content, file_name)
        
        # Enhanced: Extract media from text content
        media_items = self.extract_media_from_content(text_content, {
            'type': 'text_file_content',
            'file': file_name
        })
        for media_item in media_items:
            self._add_chat_media_item(media_item, file_name, 'text_content')
        
        # Check file name for hints about content type
        file_name_lower = file_name.lower()
        if any(keyword in file_name_lower for keyword in ['message', 'chat', 'direct']):
            chat_item = {**artifact_base, "type": "text_chat", "data": file_data.get("content", {})}
            item_hash = self._get_dedupe_hash(chat_item["data"])
            if item_hash not in self.seen_chat_hashes:
                # Enhanced: Determine if sent or received by the logged-in user
                logged_in_uid = self.logged_in_user['user_id']
                if logged_in_uid and str(logged_in_uid) in text_content:
                    chat_item["direction"] = "involved"
                else:
                    chat_item["direction"] = "unknown"

                # Enhanced: Extract media from text chat content
                chat_media_items = self.extract_media_from_content(text_content, {
                    'type': 'text_chat_file',
                    'file': file_name
                })
                for media_item in chat_media_items:
                    media_item['chat_context'] = {
                        'file_type': 'text_chat',
                        'direction': chat_item["direction"]
                    }
                    self._add_chat_media_item(media_item, file_name, 'text_chat_content')

                self.chats.append(chat_item)
                self.seen_chat_hashes.add(item_hash)
        elif any(keyword in file_name_lower for keyword in ['media', 'photo', 'video']):
            media_item = {**artifact_base, "type": "text_media", "data": file_data.get("content", {})}
            item_hash = self._get_dedupe_hash(media_item["data"])
            if item_hash not in self.seen_media_hashes:
                self.media.append(media_item)
                self.seen_media_hashes.add(item_hash)

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
    """Enhanced: Main execution function"""
    print("=" * 80)
    print("📱 Instagram Forensic Extractor V5.0 Enhanced - MEDIA & SESSION FOCUS")
    print("   ✅ Enhanced media extraction from chats and all content")
    print("   ✅ Improved session ID detection with multiple token types")
    print("   ✅ Prioritizes logged-in user's profile and data")
    print("   ✅ Extracts complete user profile information")
    print("   ✅ Supports ZIP files and Android folders")
    print("   ✅ Creates separate JSON files for each folder")
    print("   ✅ Enhanced chat media extraction and organization")
    print("   ✅ All output in JSON format with forensic metadata")
    print("   ⚠️ IMPORTANT: This tool DOES NOT decrypt Instagram's proprietary encrypted media files.")
    print("   ⚠️ Media links provided are for unencrypted, locally accessible files only.")
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
        # Initialize enhanced extractor
        extractor = InstagramExtractorV5Enhanced(input_path, case_info=case_info)
        
        # Perform extraction
        result = extractor.extract_all_data()
        
        # Enhanced: Ask user if they want to download media
        total_media_count = len(extractor.media) + len(extractor.chat_media)
        download_choice = 'n'
        if total_media_count > 0:
            download_choice = input(f"\n⬇️ Do you want to download all identified unencrypted media files ({total_media_count} total) to separate folders? (y/n): ").strip().lower()
            if download_choice == 'y':
                extractor.download_media_files()
            else:
                print("⏩ Skipping media download.")
        else:
            print("\nℹ️ No unencrypted media files found to download.")

        # Enhanced: Print results with focus on logged-in user and enhanced media/session stats
        print("\n" + "="*80)
        print("📊 EXTRACTION COMPLETE - ENHANCED MEDIA & SESSION ANALYSIS")
        print("="*80)
        
        if result["status"] == "success":
            print(f"✅ Status: {result['status']}")
            print(f"📁 Instagram folder: {result['instagram_folder']}")
            
            print(f"\n👤 LOGGED-IN USER PROFILE:")
            user_summary = result["logged_in_user_summary"]
            print(f"   🆔 User ID: {user_summary['user_id'] or 'Not found'}")
            print(f"   Source: {user_summary['user_id_source']}")
            print(f"   Confidence: {user_summary['user_id_confidence']}/100")
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
            
            print(f"\n📊 File System Analysis:")
            for key, value in result["file_system_analysis"].items():
                if isinstance(value, dict):
                    print(f"   {key}: {len(value)} types")
                else:
                    print(f"   {key}: {value}")
            
            print(f"\n📁 Folder JSON Files Created: {result['folder_json_files']}")
            
            print(f"\n🎯 Enhanced organized data:")
            print(f"   📨 Chats: {result['organized_data']['chats']}")
            print(f"   📸 Media: {result['organized_data']['media']}")
            print(f"   💬 Chat Media: {result['organized_data']['chat_media']}")
            print(f"   👥 Followers count: {result['organized_data']['followers_count_in_profile']}")
            print(f"   👤 Following count: {result['organized_data']['following_count_in_profile']}")
            
            print(f"\n🔐 Enhanced session data found:")
            for session_type, count in result["session_data"].items():
                if isinstance(count, int) and count > 0 and not session_type.startswith('total_'):
                    print(f"   {session_type.replace('total_', '').replace('_', ' ')}: {count}")
            
            print(f"\n🌐 Server data found:")
            for server_type, count in result["server_data"].items():
                if isinstance(count, int) and count > 0 and not server_type.startswith('total_'):
                    print(f"   {server_type.replace('total_', '').replace('_', ' ')}: {count}")
            
            print(f"\n❌ Errors: {result['errors']}")
            print(f"📂 Output directory: {extractor.output_dir}")
            
            print(f"\n📄 Enhanced main JSON files created:")
            print(f"   👤 logged_in_user_profile.json (TOP PRIORITY)")
            print(f"   🔐 session_ids.json (Enhanced with all session types)")
            print(f"   🌐 server_ids.json")
            print(f"   📁 file_system_structure.json")
            print(f"   📨 chats.json")
            print(f"   📸 media.json")
            print(f"   💬 chat_media.json (NEW: Media extracted from chats)")
            print(f"   📋 complete_folder_analysis.json")
            print(f"   📊 extraction_report.json")
            
            print(f"\n📁 Individual folder JSON files:")
            print(f"   📂 Location: {extractor.json_folders_dir}")
            print(f"   📄 Count: {result['folder_json_files']} files")
            
            print(f"\n🖼️ Enhanced Media Viewing Instructions:")
            print(f"   📸 Regular Media: Check 'media.json' for entries with 'status': 'found_unencrypted_and_linked'")
            print(f"   💬 Chat Media: Check 'chat_media.json' for media extracted from chat conversations")
            print(f"   🔗 View Links: Copy 'view_link' values and paste into your browser's address bar")
            print(f"   📂 Downloaded Files: Media files are also copied to dedicated folders if download was selected")
            if download_choice == 'y':
                print(f"      📸 Regular media: {extractor.downloaded_media_dir}")
                print(f"      💬 Chat media: {extractor.chat_media_dir}")
            print(f"   ⚠️ IMPORTANT: Encrypted Instagram media files use proprietary encryption and CANNOT be decrypted.")

            # Enhanced: Direct Media Access Examples
            if total_media_count > 0:
                print("\n✨ **Enhanced Direct Media Access Examples:**")
                count = 0
                
                # Show regular media examples
                for media_item in extractor.media:
                    if media_item.get("status") == "found_unencrypted_and_linked":
                        print(f"   📸 Regular Media: {media_item.get('view_link')}")
                        if media_item.get("downloaded_path"):
                            print(f"      Downloaded: {media_item.get('downloaded_path')}")
                        count += 1
                        if count >= 3:
                            break
                
                # Show chat media examples
                for chat_media_item in extractor.chat_media:
                    if chat_media_item.get("downloaded_path"):
                        print(f"   💬 Chat Media: {chat_media_item.get('downloaded_path')}")
                        count += 1
                        if count >= 5:
                            break
                
                if count == 0:
                    print("   No unencrypted media files with accessible paths were found.")
            
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
