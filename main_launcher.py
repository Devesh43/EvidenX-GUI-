from flask import Flask, render_template, jsonify
import subprocess
import threading
import time
import requests
import os
import webbrowser
from pathlib import Path

app = Flask(__name__)

# Server status tracking
server_status = {
    'whatsapp': False,
    'signal': False,
    'instagram': False # Added Instagram status
}

def check_server_status(port, server_name):
    """Check if a server is running on given port"""
    try:
        response = requests.get(f'http://localhost:{port}', timeout=2)
        server_status[server_name] = True
        return True
    except:
        server_status[server_name] = False
        return False

def start_whatsapp_server():
    """Start WhatsApp extractor server on port 5000"""
    try:
        whatsapp_path = Path('Whatsapp Files')
        if whatsapp_path.exists():
            # Change to WhatsApp directory and start server
            original_dir = os.getcwd()
            os.chdir(whatsapp_path)
            
            # Start the server in background
            if os.name == 'nt':  # Windows
                subprocess.Popen(['python', 'app.py'], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:  # Linux/Mac
                subprocess.Popen(['python3', 'app.py'], shell=False)
            
            os.chdir(original_dir)
            
            # Wait and check if server started
            for i in range(10):  # Try for 10 seconds
                time.sleep(1)
                if check_server_status(5000, 'whatsapp'):
                    print("✅ WhatsApp Extractor started successfully on port 5000")
                    break
            else:
                print(" WhatsApp Extractor may not have started properly")
        else:
            print(" WhatsApp Files folder not found")
    except Exception as e:
        print(f"❌ Error starting WhatsApp server: {e}")

def start_signal_server():
    """Start Signal extractor server on port 5001"""
    try:
        signal_path = Path('Signal Files')
        if signal_path.exists():
            # Change to Signal directory and start server
            original_dir = os.getcwd()
            os.chdir(signal_path)
            
            # Start the server in background
            if os.name == 'nt':  # Windows
                subprocess.Popen(['python', 'app.py'], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:  # Linux/Mac
                subprocess.Popen(['python3', 'app.py'], shell=False)
            
            os.chdir(original_dir)
            
            # Wait and check if server started
            for i in range(10):  # Try for 10 seconds
                time.sleep(1)
                if check_server_status(5001, 'signal'):
                    print("✅ Signal Extractor started successfully on port 5001")
                    break
            else:
                print("⚠️ Signal Extractor may not have started properly")
        else:
            print(" Signal Files folder not found !")
    except Exception as e:
        print(f"❌ Error starting Signal server: {e}")

def start_instagram_server():
    """Start Instagram extractor server on port 5007""" # Changed port to 5007
    try:
        instagram_path = Path('Instagram Files') # Assuming 'Instagram Files' folder
        if instagram_path.exists():
            # Change to Instagram directory and start server
            original_dir = os.getcwd()
            os.chdir(instagram_path)
            
            # Start the server in background
            if os.name == 'nt':  # Windows
                subprocess.Popen(['python', 'app.py'], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:  # Linux/Mac
                subprocess.Popen(['python3', 'app.py'], shell=False)
            
            os.chdir(original_dir)
            
            # Wait and check if server started
            for i in range(10):  # Try for 10 seconds
                time.sleep(1)
                if check_server_status(5007, 'instagram'): # Changed port to 5007
                    print("✅ Instagram Extractor started successfully on port 5007") # Changed port to 5007
                    break
            else:
                print("⚠️ Instagram Extractor may not have started properly")
        else:
            print("❌ Instagram Files folder not found")
    except Exception as e:
        print(f"❌ Error starting Instagram server: {e}")

@app.route('/')
def index():
    return render_template('launcher.html')

@app.route('/start-whatsapp')
def start_whatsapp():
    if not server_status['whatsapp']:
        print("🚀 Starting WhatsApp Extractor...")
        threading.Thread(target=start_whatsapp_server, daemon=True).start()
        return jsonify({'status': 'starting', 'url': 'http://localhost:5000', 'message': 'WhatsApp Extractor is starting...'})
    else:
        return jsonify({'status': 'running', 'url': 'http://localhost:5000', 'message': 'WhatsApp Extractor is already running'})

@app.route('/start-signal')
def start_signal():
    if not server_status['signal']:
        print("🚀 Starting Signal Extractor...")
        threading.Thread(target=start_signal_server, daemon=True).start()
        return jsonify({'status': 'starting', 'url': 'http://localhost:5001', 'message': 'Signal Extractor is starting...'})
    else:
        return jsonify({'status': 'running', 'url': 'http://localhost:5001', 'message': 'Signal Extractor is already running'})

@app.route('/start-instagram') # New route for Instagram
def start_instagram():
    if not server_status['instagram']:
        print("🚀 Starting Instagram Extractor...")
        threading.Thread(target=start_instagram_server, daemon=True).start()
        return jsonify({'status': 'starting', 'url': 'http://localhost:5007', 'message': 'Instagram Extractor is starting...'}) # Changed port to 5007
    else:
        return jsonify({'status': 'running', 'url': 'http://localhost:5007', 'message': 'Instagram Extractor is already running'}) # Changed port to 5007

@app.route('/status')
def get_status():
    # Check current status for all extractors
    check_server_status(5000, 'whatsapp')
    check_server_status(5001, 'signal')
    check_server_status(5007, 'instagram') # Changed port to 5007
    return jsonify(server_status)

def open_browser():
    """Open browser after a short delay"""
    time.sleep(2)  # Wait for Flask to start
    webbrowser.open('http://localhost:8000')

if __name__ == '__main__':
    print("=" * 60)
    print("🔒 IFSO/NCFL Delhi Police Special Cell Data Extractor")
    print("=" * 60)
    print("🚀 Starting Main Launcher...")
    print("🌐 Main Interface: http://localhost:8000")
    print("📱 WhatsApp Extractor: http://localhost:5000 (starts on demand)")
    print("💬 Signal Extractor: http://localhost:5001 (starts on demand)")
    print("📸 Instagram Extractor: http://localhost:5007 (starts on demand)") # Changed port to 5007
    print("=" * 60)
    print("✅ Opening browser automatically...")
    print("💡 Click the extractor buttons to launch them in new tabs")
    print("=" * 60)
    
    # Start browser opening in background
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start Flask app
    try:
        app.run(debug=False, port=8000, host='0.0.0.0', use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down launcher...")
    except Exception as e:
        print(f"❌ Error starting launcher: {e}")
        input("Press Enter to exit...")
