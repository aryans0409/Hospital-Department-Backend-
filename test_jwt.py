import subprocess
import time
import urllib.request
import urllib.error
import json
# Start uvicorn server in a subprocess on port 8080
server_process = subprocess.Popen(
    [r".venv\Scripts\python.exe", "-c", "import uvicorn; from main import app; uvicorn.run(app, host='127.0.0.1', port=8080)"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

print("Starting FastAPI server on http://127.0.0.1:8080...")
time.sleep(3)

def make_request(url, method="GET", data=None, token=None):
    req = urllib.request.Request(url, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
        req_data = json.dumps(data).encode("utf-8")
    else:
        req_data = None
    
    if token is not None:
        req.add_header("Authorization", f"Bearer {token}")
        
    try:
        with urllib.request.urlopen(req, data=req_data, timeout=3) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
        except Exception:
            err_body = e.reason
        return e.code, err_body
    except Exception as e:
        return 0, str(e)

try:
    print("\n--- Test 1: GET / (Public, should succeed without JWT) ---")
    status, body = make_request("http://127.0.0.1:8080/")
    print(f"Status: {status}\nBody: {body}")

    print("\n--- Test 2: GET /patient/P0001 (Private, should fail with 401) ---")
    status, body = make_request("http://127.0.0.1:8080/patient/P0001")
    print(f"Status: {status}\nBody: {body}")

    print("\n--- Test 3: POST /login (Invalid credentials, should fail) ---")
    status, body = make_request("http://127.0.0.1:8080/login", method="POST", data={"username": "admin", "password": "wrongpassword"})
    print(f"Status: {status}\nBody: {body}")

    print("\n--- Test 4: POST /login (Valid credentials, should return token) ---")
    status, body = make_request("http://127.0.0.1:8080/login", method="POST", data={"username": "admin", "password": "admin123"})
    print(f"Status: {status}\nBody: {body}")
    
    token = None
    if status == 200 and "access_token" in body:
        token = body["access_token"]
        print("Token obtained successfully!")

    if token:
        print("\n--- Test 5: GET /patient/P0001 (Private with JWT, should succeed) ---")
        status, body = make_request("http://127.0.0.1:8080/patient/P0001", token=token)
        print(f"Status: {status}\nBody: {body}")

        print("\n--- Test 6: POST /add (Add patient with valid payload, should succeed) ---")
        patient_payload = {
            "patient_id": "P0099",
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1990-01-01",
            "gender": "Male",
            "admission_date": "2026-06-19",
            "discharge_date": None,
            "diagnosis": "Healthy",
            "ward": "General",
            "bed": "G-99",
            "attending_physician": "Dr. Mehta",
            "contact_phone": "+91-9999999999",
            "emergency_contact_name": "Jane Doe",
            "emergency_contact_phone": "+91-8888888888",
            "status": "admitted"
        }
        status, body = make_request("http://127.0.0.1:8080/add", method="POST", data=patient_payload, token=token)
        print(f"Status: {status}\nBody: {body}")

        print("\n--- Test 7: POST /add (Add patient with invalid payload, should fail with 400 validation error) ---")
        bad_payload = {
            "patient_id": "P0099",
            # Missing first_name and last_name
            "dob": "1990-01-01",
            "gender": "Male",
            "admission_date": "2026-06-19",
            "diagnosis": "Healthy",
            "ward": "General",
            "bed": "G-99",
            "attending_physician": "Dr. Mehta",
            "contact_phone": "+91-9999999999",
            "status": "admitted"
        }
        status, body = make_request("http://127.0.0.1:8080/add", method="POST", data=bad_payload, token=token)
        print(f"Status: {status}\nBody: {body}")

        print("\n--- Test 8: POST /decode (Decode valid JWT, should succeed) ---")
        status, body = make_request("http://127.0.0.1:8080/decode", method="POST", data={"token": token})
        print(f"Status: {status}\nBody: {body}")

finally:
    print("\nStopping server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        server_process.kill()
    print("Server stopped.")