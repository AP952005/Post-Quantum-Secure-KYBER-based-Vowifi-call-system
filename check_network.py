import requests
import sys

def check_registry(url):
    print(f"Checking registry at: {url}")
    try:
        response = requests.get(url, timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code == 200:
             print("SUCCESS: Registry is reachable!")
        else:
             print("WARNING: Registry reachable but returned non-200 status.")
    except requests.exceptions.ConnectionError as e:
        print(f"ERROR: Connection Failed via requests. \n{e}")
    except Exception as e:
         print(f"ERROR: General Error. \n{e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = "http://127.0.0.1:5001"
    check_registry(target)
