import os
from flask import Flask, jsonify, request
from dotenv import load_dotenv

from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_ollama.llms import OllamaLLM
from langchain_pinecone import PineconeVectorStore
from langchain.chains import RetrievalQA

load_dotenv()
app = Flask(__name__)

# --- Configuration ---
PINECONE_INDEX_NAME = "mcp-explore-768"

# --- Initializations ---
try:
    embedder = OllamaEmbeddings(model="nomic-embed-text")
    llm = OllamaLLM(model="mistral")
    vectorstore = PineconeVectorStore(
        index_name=PINECONE_INDEX_NAME,
        embedding=embedder,
        pinecone_api_key=os.environ.get("PINECONE_API_KEY")
    )
    print("Successfully initialized all models and clients.")
except Exception as e:
    print(f"An error occurred during initialization: {e}")
    embedder = llm = vectorstore = None

@app.route('/prompt/doc_chat', methods=['POST'])
def chat():
    if not all([embedder, llm, vectorstore]):
         return jsonify({"error": "A service is not initialized."}), 500

    try:
        data = request.get_json()
        question = data.get('question')
        # Expecting 'filename' in the request body now, not 'doc_id'
        filename = data.get('filename')

        if not question:
            return jsonify({"error": "A 'question' must be provided."}), 400

        # --- Dynamic Retriever Logic ---
        search_kwargs = {"k": 5}

        # If a filename is provided, add a filter to the search
        if filename:
            print(f"Applying filter for document: {filename}")
            search_kwargs["filter"] = {"source": {"$eq": filename}}
        else:
            print("No document filter applied. Performing global search.")

        retriever = vectorstore.as_retriever(
            search_kwargs=search_kwargs
        )
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            return_source_documents=True
        )

        print("Retrieving context and generating answer...")
        result = qa_chain.invoke({"query": question})
        
        answer = result.get("result", "No answer could be generated.")
        sources = list({doc.metadata.get("source", "unknown") for doc in result["source_documents"]})
        
        print(f"Generated answer: {answer}")
        
        return jsonify({
            "answer": answer,
            "sources": sources
        })
    except Exception as e:
        error_details = f"An error of type {type(e).__name__} occurred: {str(e)}"
        print(error_details)
        return jsonify({"error": "An internal error occurred.", "details": error_details}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6003, debug=True)