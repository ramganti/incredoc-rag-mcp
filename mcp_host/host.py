from flask import Flask, request, Response
import requests

app = Flask(__name__)

# This registry maps the first part of a URL path to the
# address of the microservice that handles it.
SERVICE_REGISTRY = {
    "resource": "http://localhost:6001",
    "tool": "http://localhost:6002",
    "prompt": "http://localhost:6003"
}

@app.route('/<service>/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(service, path):
    """
    This function acts as a reverse proxy. It:
    1. Determines the destination service from the URL's 'service' part.
    2. Forwards the entire request (method, headers, data) to that service.
    3. Streams the response from the service back to the original client.
    """
    if service in SERVICE_REGISTRY:
        # Construct the full destination URL
        destination_url = f"{SERVICE_REGISTRY[service]}/{service}/{path}"
        
        print(f"Proxying request for '/{service}/{path}' to {destination_url}")

        try:
            # Make a request to the downstream service
            resp = requests.request(
                method=request.method,
                url=destination_url,
                headers={key: value for (key, value) in request.headers if key != 'Host'},
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,
                stream=True,  # Use stream=True to handle large responses efficiently
                timeout=20 # Add a timeout
            )

            # Create a new Flask response to send back to the original client
            # It copies the status code, headers, and content from the downstream response
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [(name, value) for (name, value) in resp.raw.headers.items()
                       if name.lower() not in excluded_headers]

            response = Response(resp.iter_content(chunk_size=1024), resp.status_code, headers)
            return response

        except requests.exceptions.RequestException as e:
            print(f"Error connecting to downstream service: {e}")
            return "Downstream service connection error", 502

    else:
        # If the service name in the URL isn't in our registry, return a 404
        return "Service not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)