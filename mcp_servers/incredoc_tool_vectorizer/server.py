import os
import json
from flask import Flask, jsonify, request
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama.embeddings import OllamaEmbeddings # Use OllamaEmbeddings
from pinecone import Pinecone

load_dotenv()
app = Flask(__name__)

# --- Configuration ---
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "mcp-explore-768"

# --- Path Definitions ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
SOURCE_DOCS_DIR = os.path.join(PROJECT_ROOT, 'source_docs')
MANIFEST_FILE = os.path.join(PROJECT_ROOT, 'manifest.json')

# --- Initializations ---
try:
    pc = Pinecone(api_key=PINECONE_API_KEY)
    # Use the correct embedding model
    embedder = OllamaEmbeddings(model="nomic-embed-text")
    print("Successfully initialized Pinecone client and embedding model.")
except Exception as e:
    print(f"Error during initialization: {e}")
    pc = embedder = None

@app.route('/tool/vectorizer', methods=['POST'])
def vectorize_documents():
    if not pc or not embedder:
        return jsonify({"error": "A service is not initialized."}), 500

    try:
        with open(MANIFEST_FILE, 'r') as f:
            manifest = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({"error": "Manifest file not found or is empty. Run intake first."}), 400

    vectorized_files = []
    files_to_process = [
        fname for fname, data in manifest.items() if not data.get('vectorized')
    ]
    print(f"Found {len(files_to_process)} files to vectorize: {files_to_process}")

    for filename in files_to_process:
        file_path = os.path.join(SOURCE_DOCS_DIR, filename)
        if not os.path.exists(file_path):
            continue
        try:
            print(f"Processing: {filename}")
            doc_id = manifest[filename].get('uuid')

            loader = PyPDFLoader(file_path)
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            docs = text_splitter.split_documents(loader.load())
            print(f"Created {len(docs)} chunks for {filename}.")

            # --- Vectorize and Store ---
            index = pc.Index(PINECONE_INDEX_NAME)
            texts = [doc.page_content for doc in docs]
            vectors = embedder.embed_documents(texts) # Use the new embedder
            
            records_to_upsert = []
            for i, doc in enumerate(docs):
                metadata = {
                    "doc_id": doc_id,
                    "source": filename,
                    "text": doc.page_content
                }
                records_to_upsert.append(
                    (f"{doc_id}-{i}", vectors[i], metadata)
                )

            print(f"Upserting {len(records_to_upsert)} vectors...")
            index.upsert(vectors=records_to_upsert)
            print("Upsert complete.")

            manifest[filename]['vectorized'] = True
            manifest[filename]['no_of_chunks'] = len(docs)
            vectorized_files.append(filename)
        except Exception as e:
            error_details = f"An error of type {type(e).__name__} occurred: {str(e)}"
            print(f"Failed to vectorize {filename}: {error_details}")
            return jsonify({"error": f"Failed on file {filename}", "details": error_details}), 500

    with open(MANIFEST_FILE, 'w') as f:
        json.dump(manifest, f, indent=4)

    return jsonify({
        "status": "Vectorization complete.",
        "vectorized": vectorized_files,
        "total_processed": len(vectorized_files)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6002, debug=True)