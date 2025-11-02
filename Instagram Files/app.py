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
import threading
import sys

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

# Try to import pyzipper for encrypted ZIP support
try:
    import pyzipper
    PYZIPPER_AVAILABLE = True
except ImportError:
    PYZIPPER_AVAILABLE = False
    print("Note: pyzipper not available. Encrypted ZIP support disabled.")

# Assuming Instagram_Extractor.py is in the same directory
import Instagram_Extractor

# Flask app setup
app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Global variables for extraction state
extraction_status = "idle"
extraction_output = ""
extraction_data = {}
output_lock = threading.Lock()

def output_callback(message):
    """Callback function to capture extractor output"""
    global extraction_output
    with output_lock:
        extraction_output += message + "\n"
    print(message)

# Flask Routes
@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')

@app.route('/results')
def results():
    """Serve the results HTML page."""
    return render_template('results.html')

@app.route('/extract', methods=['POST'])
def extract_data():
    global extraction_status, extraction_output, extraction_data
    if extraction_status == "running":
        return jsonify({"status": "error", "message": "Extraction already in progress."}), 409

    data = request.json
    input_path = data.get('inputPath')
    case_info = {
        "case_number": data.get('caseNumber'),
        "examiner": data.get('examinerName'),
        "evidence_item": data.get('evidenceItem')
    }

    if not input_path:
        return jsonify({"status": "error", "message": "Input path is required."}), 400

    # Reset state and start extraction in a new thread
    extraction_status = "running"
    extraction_output = ""
    extraction_data = {} # Clear previous data
    
    # Define the target function for the thread
    def extraction_thread_target():
        global extraction_status, extraction_output, extraction_data
        try:
            # Instantiate the MasterExtractor from Instagram_Extractor.py
            master = Instagram_Extractor.MasterExtractor(input_path, case_info=case_info, output_callback=output_callback)
            
            # Run extraction and capture the returned report
            extracted_report = master.run_extraction() 
            
            with output_lock:
                extraction_data = extracted_report # Store the data for UI

            extraction_status = "completed"
            output_callback("Extraction process completed successfully.")
        except Exception as e:
            extraction_status = "failed"
            error_message = f"Extraction process failed: {e}\n{traceback.format_exc()}"
            output_callback(f"❌ {error_message}")
        finally:
            # Clean up temporary files regardless of success or failure
            if 'master' in locals() and master:
                master.cleanup()

    # Start the thread
    extraction_thread = threading.Thread(target=extraction_thread_target)
    extraction_thread.start()

    return jsonify({
        "status": "success",
        "message": "Extraction started successfully. Check logs for progress."
    })

@app.route('/get_status', methods=['GET'])
def get_status():
    """Get the current status and output of the extraction."""
    global extraction_status, extraction_output
    
    current_output = ""
    with output_lock:
        current_output = extraction_output

    status_message = ""
    if extraction_status == "running":
        status_message = "Extraction in progress..."
    elif extraction_status == "completed":
        status_message = "Extraction completed successfully."
    elif extraction_status == "failed":
        status_message = "Extraction failed. Please check the logs for details."
    elif extraction_status == "idle":
        status_message = "No extraction running."

    return jsonify({
        "status": "success",
        "message": status_message,
        "output": current_output,
        "extraction_status": extraction_status
    })

@app.route('/get_extracted_data', methods=['GET'])
def get_extracted_data():
    """Get the extracted data once extraction is completed."""
    global extraction_data, extraction_status
    
    if extraction_status == "running":
        return jsonify({
            "status": "in_progress",
            "message": "Extraction still in progress. Please wait...",
            "extraction_status": extraction_status
        }), 200
    
    if extraction_status != "completed":
        return jsonify({
            "status": "no_data",
            "message": "No extraction completed yet or extraction failed.",
            "extraction_status": extraction_status
        }), 200

    if not extraction_data:
        return jsonify({
            "status": "no_data",
            "message": "Extraction completed but no data was generated.",
            "extraction_status": extraction_status
        }), 200

    return jsonify({
        "status": "success",
        "message": "Data retrieved successfully.",
        "data": extraction_data
    })

@app.route('/reset', methods=['POST'])
def reset_extraction():
    """Reset the extraction state."""
    global extraction_status, extraction_output, extraction_data
    
    extraction_status = "idle"
    extraction_output = ""
    extraction_data = {}
    
    return jsonify({
        "status": "success",
        "message": "Extraction state reset successfully."
    })

if __name__ == '__main__':
    print("Starting Instagram Data Extractor Web Interface...")
    print("Navigate to http://localhost:5007 to access the interface")
    app.run(debug=True, host='0.0.0.0', port=5007)
