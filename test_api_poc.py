import httpx
import json

# Configuration - ASSUMES BACKEND IS RUNNING LOCALLY ON PORT 8000
API_URL = "http://localhost:8000"

def run_api_poc():
    """Performs a Proof-of-Concept test against the core API endpoints."""
    print("--- Starting API PoC Test ---")
    client = httpx.Client(base_url=API_URL)
    
    try:
        # 1. Health Check
        print("[+] Checking /health endpoint...")
        response = client.get("/health")
        if response.status_code == 200 and response.json().get("status") == "OK":
            print(f"✅ Success: API is healthy. Status: OK.")
        else:
            print(f"❌ Failure: Health check failed. Status Code: {response.status_code}. Response: {response.text[:100]}...")

        # 2. Fetch all Games (Requires authentication/developer setup in a real scenario, but testing basic GET structure)
        print("\n[+] Attempting to fetch list of games from /games...")
        try:
            # Assuming a simple list endpoint exists for now
            response = client.get("/api/v1/games/") 
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    print(f"✅ Success: Retrieved {len(data)} games.")
                    print(f"   Example Game Title: {data[0].get('title', 'N/A')}")
                elif isinstance(data, dict) and 'games' in data: # Handle wrapped list structure
                     games = data['games']
                     if games:
                         print(f"✅ Success: Retrieved {len(games)} games.")
                         print(f"   Example Game Title: {games[0].get('title', 'N/A')}")
                     else:
                        print("⚠️ Warning: Endpoint returned success but no games found in the list.")
                else:
                    print("❌ Failure: Could not parse expected game data structure from response.")

            elif response.status_code == 404:
                 print("⚠️ Warning: The '/api/v1/games/' endpoint might not exist yet, which is acceptable for PoC.")
            else:
                print(f"❌ Failure: Failed to list games. Status Code: {response.status_code}. Response: {response.text[:100]}...")

        except httpx.ConnectError:
             print("\n🛑 FATAL ERROR: Could not connect to the API backend.")
             print("   Please ensure 'docker compose up -d build' has been run successfully in a separate terminal.")


    finally:
        client.close()
        print("\n--- API PoC Test Finished ---")

if __name__ == "__main__":
    # Note: This script requires the backend to be running and accessible at http://localhost:8000
    run_api_poc()