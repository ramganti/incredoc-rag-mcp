import gradio as gr
import requests
import json
import os

# --- Configuration ---
MCP_HOST_URL = "http://localhost:4000"
# Find the manifest file relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
MANIFEST_FILE = os.path.join(PROJECT_ROOT, 'manifest.json')

# --- Helper Function to Load Filenames ---
def get_available_documents():
    """
    Reads the manifest.json file and returns a list of document filenames.
    This function is called once when the app starts.
    """
    try:
        with open(MANIFEST_FILE, 'r') as f:
            manifest = json.load(f)
        # Return a list of the keys (filenames) from the manifest
        return list(manifest.keys())
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is empty, return an empty list
        print("Warning: manifest.json not found. The document dropdown will be empty.")
        return []

# --- Main Chat Logic ---
def chat_with_bot(message, history, selected_doc):
    """
    Handles the chat interaction. It's called every time a user sends a message.
    - `message`: The user's question from the textbox.
    - `history`: The existing conversation history (managed by Gradio).
    - `selected_doc`: The filename chosen from the dropdown menu.
    """
    print(f"Sending question: '{message}' for document scope: '{selected_doc}'")

    # Prepare the JSON payload for the backend API call
    payload = {
        "question": message
    }

    # Only add the 'filename' key to the payload if a specific document is chosen.
    # If "All Documents" is selected, we omit the key to trigger a global search.
    if selected_doc and selected_doc != "All Documents":
        payload["filename"] = selected_doc

    try:
        # Call the MCP Host, which will route the request to the doc_chat server
        response = requests.post(
            f"{MCP_HOST_URL}/prompt/doc_chat",
            json=payload,
            timeout=90  # Increased timeout for potentially long LLM responses
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        response_json = response.json()
        
        answer = response_json.get("answer", "Sorry, I could not generate an answer.")
        sources = response_json.get("sources", [])
        
        # Format the response to include the sources for better user feedback
        full_response = answer
        if sources:
            # Create a unique, comma-separated list of source filenames
            source_list = ", ".join(list(set(sources)))
            full_response += f"\n\n*Sources: {source_list}*"

        return full_response

    except requests.exceptions.RequestException as e:
        error_message = f"Error: Could not connect to the backend service. Please ensure all MCP servers and the host are running. Details: {e}"
        print(error_message)
        return error_message
    except json.JSONDecodeError:
        error_message = "Error: Received an invalid (non-JSON) response from the backend."
        print(error_message)
        return error_message

# --- Build the Gradio UI ---

# Get the initial list of documents to populate the dropdown
doc_choices = ["All Documents"] + get_available_documents()

# Use gr.Blocks for a custom layout
with gr.Blocks(theme=gr.themes.Soft(), title="MCP Document Chat") as demo:
    gr.Markdown("# MCP Document Chat Interface")
    gr.Markdown("Ask questions about your documents. Select a specific document from the dropdown to focus your question, or choose 'All Documents' for a global search.")

    with gr.Row():
        # The dropdown component for document selection
        doc_dropdown = gr.Dropdown(
            choices=doc_choices,
            label="Select Document Scope",
            value="All Documents"  # The default selection
        )

    # The main chat interface component
    gr.ChatInterface(
        fn=chat_with_bot,
        chatbot=gr.Chatbot(height=500), # Explicitly define the chatbot for styling
        # Link the dropdown component as an additional input to our chat function
        additional_inputs=[doc_dropdown],
        examples=[
            ["What is covered in the Evidence of Coverage?", "MK002171_EvidenceOfCoverage.pdf"],
            ["What are the general policies for benefits?", "All Documents"]
        ]
    )

if __name__ == "__main__":
    demo.launch()