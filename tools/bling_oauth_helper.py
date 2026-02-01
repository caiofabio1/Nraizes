"""
Bling OAuth Helper - Easy Token Management
Run this, access the URL, authorize, and tokens are saved automatically.
"""
from flask import Flask, request, redirect
import requests
import base64
import os

app = Flask(__name__)

CLIENT_ID = '2d11c08a3e3a8e3dff93807f1c62b7b8d2a202cd'
CLIENT_SECRET = '3f9df8b533845c375967a936397d31f4abfcc5d07dc9fb3ccee03dba7266'
REDIRECT_URI = 'http://localhost:8888/callback'
ENV_FILE = r'c:\Users\caiof\NRAIZES\.credentials\bling_api_tokens.env'

@app.route('/')
def home():
    auth_url = f"https://www.bling.com.br/Api/v3/oauth/authorize?response_type=code&client_id={CLIENT_ID}&state=xyz"
    return f'''
    <html>
    <head><title>Bling OAuth</title>
    <style>
        body {{ font-family: Arial; background: #1a1a2e; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
        .container {{ text-align: center; padding: 2rem; background: #16213e; border-radius: 12px; }}
        a {{ display: inline-block; padding: 1rem 2rem; background: #e94560; color: white; text-decoration: none; border-radius: 8px; font-size: 1.2rem; }}
        a:hover {{ background: #ff6b8a; }}
    </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Bling OAuth</h1>
            <p>Clique abaixo para autorizar o acesso à API Bling</p>
            <a href="{auth_url}">Autorizar Bling</a>
        </div>
    </body>
    </html>
    '''

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "❌ Erro: Código não recebido", 400
    
    # Exchange code for tokens
    auth_string = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()
    
    try:
        resp = requests.post(
            'https://www.bling.com.br/Api/v3/oauth/token',
            headers={
                'Authorization': f'Basic {auth_string}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={
                'grant_type': 'authorization_code',
                'code': code
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            tokens = resp.json()
            access_token = tokens.get('access_token')
            refresh_token = tokens.get('refresh_token')
            
            # Update .env file
            update_env_tokens(access_token, refresh_token)
            
            return f'''
            <html>
            <head><title>Sucesso!</title>
            <style>
                body {{ font-family: Arial; background: #1a1a2e; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                .container {{ text-align: center; padding: 2rem; background: #16213e; border-radius: 12px; }}
                .success {{ color: #00d9a5; font-size: 3rem; }}
            </style>
            </head>
            <body>
                <div class="container">
                    <div class="success">✅</div>
                    <h1>Tokens Atualizados!</h1>
                    <p>Access Token: <code>{access_token[:20]}...</code></p>
                    <p>Refresh Token: <code>{refresh_token[:20]}...</code></p>
                    <p>Arquivo atualizado: <code>{ENV_FILE}</code></p>
                    <p><strong>Pode fechar esta janela.</strong></p>
                </div>
            </body>
            </html>
            '''
        else:
            return f"❌ Erro ao trocar código: {resp.status_code} - {resp.text}", 400
            
    except Exception as e:
        return f"❌ Exceção: {e}", 500

def update_env_tokens(access_token, refresh_token):
    """Update the .env file with new tokens"""
    with open(ENV_FILE, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if line.startswith('ACCESS_TOKEN='):
            new_lines.append(f'ACCESS_TOKEN={access_token}\n')
        elif line.startswith('REFRESH_TOKEN='):
            new_lines.append(f'REFRESH_TOKEN={refresh_token}\n')
        else:
            new_lines.append(line)
    
    with open(ENV_FILE, 'w') as f:
        f.writelines(new_lines)
    
    print(f"✅ Tokens salvos em {ENV_FILE}")

if __name__ == '__main__':
    print("=" * 50)
    print("🔐 Bling OAuth Helper")
    print("=" * 50)
    print(f"Acesse: http://localhost:8888")
    print("=" * 50)
    app.run(port=8888, debug=False)
