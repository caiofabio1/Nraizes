import os
import requests
import base64
import sys
from dotenv import load_dotenv

# Path to .env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.credentials', 'bling_api_tokens.env')

def exchange_code(auth_code):
    load_dotenv(env_path, override=True)
    
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    
    print(f"DEBUG: Loaded CLIENT_ID: {client_id[:5]}... (len={len(client_id) if client_id else 0})")
    print(f"DEBUG: Loaded CLIENT_SECRET: {client_secret[:5]}... (len={len(client_secret) if client_secret else 0})")
    
    if not all([client_id, client_secret, auth_code]):
        print("Missing credentials or auth code.")
        return False

    print(f"Exchanging code: {auth_code}...")
    
    # Prepare Auth Header
    credentials = f"{client_id}:{client_secret}"
    encoded_creds = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_creds}"
    }
    
    data = {
        "grant_type": "authorization_code",
        "code": auth_code
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
            
            print("Tokens obtained successfully!")
            
            # Update .env file
            update_env_file(env_path, "ACCESS_TOKEN", new_access_token)
            update_env_file(env_path, "REFRESH_TOKEN", new_refresh_token)
            
            return True
        else:
            print(f"Failed to exchange code. Status: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"Error during exchange: {e}")
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
    if len(sys.argv) > 1:
        code = sys.argv[1]
    else:
        code = input("Enter Authorization Code: ").strip()
    
    exchange_code(code)
