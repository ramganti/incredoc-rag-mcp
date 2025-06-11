from flask import Flask, jsonify
import os
import json
import uuid
from datetime import datetime

app = Flask(__name__)

# --- CORRECT, ROBUST PATH DEFINITIONS ---

# Get the directory containing the current script (e.g., .../mcp_servers/incredoc_resource_doc_intake)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Go up two levels to find the project root directory (e.g., .../incredoc_rag)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

# Construct the final, correct paths relative to the project root
SOURCE_DOCS_DIR = os.path.join(PROJECT_ROOT, 'source_docs')
MANIFEST_FILE = os.path.join(PROJECT_ROOT, 'manifest.json')

def get_file_checksum(file_path):
    """Generates a UUID as a checksum for a file."""
    return str(uuid.uuid4())

@app.route('/resource/incredoc.resource.doc_intake', methods=['POST'])
def intake_documents():
    """
    This endpoint scans the SOURCE_DOCS_DIR for PDF files.
    - If a file is NEW, it gets a unique ID, timestamp, and is marked for processing.
    - If a file is NOT new, it is skipped.
    """
    # ... (pathing and initial print statements) ...
    try:
        with open(MANIFEST_FILE, 'r') as f:
            manifest = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        manifest = {}

    processed_files = []
    skipped_files = []
    
    for filename in os.listdir(SOURCE_DOCS_DIR):
        file_path = os.path.join(SOURCE_DOCS_DIR, filename)
        
        # We only care about files, and only if they are PDFs
        if os.path.isfile(file_path) and filename.lower().endswith('.pdf'):
            if filename not in manifest:
                print(f"Found new PDF file: {filename}")
                # If new, create a record for it
                manifest[filename] = {
                    'uuid': str(uuid.uuid4()),
                    'last_updated': datetime.utcnow().isoformat() + "Z",
                    'vectorized': False,
                    'no_of_chunks': 0  # Initialize chunk count
                }
                processed_files.append(filename)
            else:
                skipped_files.append(filename)

    with open(MANIFEST_FILE, 'w') as f:
        json.dump(manifest, f, indent=4)
        print(f"Manifest updated at {MANIFEST_FILE}")

    response_data = {
        "status": "Intake scan complete.",
        "processed": processed_files,
        "skipped": skipped_files
    }
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(port=6001)