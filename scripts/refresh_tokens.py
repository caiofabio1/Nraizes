import os
import requests
import base64
from dotenv import load_dotenv

# Path to .env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.credentials', 'bling_api_tokens.env')

def refresh_tokens():
    # Load current env without overriding system env if already set
    # but we reload to be sure
    load_dotenv(env_path, override=True)
    
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    refresh_token = os.getenv("REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        print("Missing credentials in .env file.")
        return False

    print("Attempting to refresh token...")
    
    # Prepare Auth Header
    credentials = f"{client_id}:{client_secret}"
    encoded_creds = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_creds}"
    }
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    try:
        response = requests.post(
            "https://www.bling.com.br/Api/v3/oauth/token",
            headers=headers,
            data=data
        )
        
        if response.status_code == 200:
            tokens = response.json()
            new_access_token = tokens['access_token']
            new_refresh_token = tokens['refresh_token'] 
            # Note: Bling rotates refresh tokens too!
            
            print("Tokens refreshed successfully!")
            
            # Update .env file
            update_env_file(env_path, "ACCESS_TOKEN", new_access_token)
            update_env_file(env_path, "REFRESH_TOKEN", new_refresh_token)
            
            return True
        else:
            print(f"Failed to refresh tokens. Status: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"Error during refresh: {e}")
        return False

def update_env_file(path, key, value):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    new_lines = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
            
    if not found:
        new_lines.append(f"{key}={value}\n")
        
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Updated {key} in {path}")

if __name__ == "__main__":
    refresh_tokens()
