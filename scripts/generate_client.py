import json
import re
from typing import Dict, Any, List

def to_snake_case(name: str) -> str:
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

def clean_description(desc: str) -> str:
    if not desc:
        return ""
    return desc.replace('\n', ' ').strip()

def generate_client(spec_path: str, output_path: str):
    with open(spec_path, 'r', encoding='utf-8') as f:
        spec = json.load(f)

    # Filter relevant paths to avoid bloat
    relevant_tags = ["Produtos", "Estoques", "Pedidos"]
    
    paths: Dict[str, Any] = spec.get('paths', {})
    
    methods_code = []
    
    print(f"Found {len(paths)} paths total.")
    
    for path, methods in paths.items():
        for method_name, details in methods.items():
            tags = details.get('tags', [])
            if not any(tag in relevant_tags for tag in tags):
                continue
                
            operation_id = details.get('operationId')
            # Fallback if no operationId (Bling spec implies x-api-action but let's use path)
            if not operation_id:
                # /produtos/{id} -> get_produtos_id
                clean_path = path.replace('{', '').replace('}', '').replace('/', '_').strip('_')
                operation_id = f"{method_name}_{clean_path}"
                
            func_name = to_snake_case(operation_id)
            description = clean_description(details.get('description', ''))
            
            # Parameters
            params = details.get('parameters', [])
            args = ["self"]
            query_params = []
            path_params = []
            
            doc_params = []

            for p in params:
                p_name = ""
                p_in = ""
                p_desc = ""
                
                if '$ref' in p:
                    # simplistic handling: extract name from ref URL
                    # e.g., "#/components/parameters/idProduto" -> "idProduto"
                    ref_name = p['$ref'].split('/')[-1]
                    p_name = ref_name
                    # We have to guess 'in' or look it up. 
                    # For path params, the path string usually contains {name}.
                    if f"{{{p_name}}}" in path:
                         p_in = 'path'
                    else:
                         p_in = 'query' # Default assumption
                else:
                    p_name = p['name']
                    p_in = p['in']
                    p_desc = p.get('description', '')

                if p_in == 'path':
                    args.append(f"{p_name}: str")
                    path_params.append(p_name)
                    doc_params.append(f"        {p_name}: {p_desc}")
                elif p_in == 'query':
                    # Still just listing in docstring, handling via **kwargs
                    doc_params.append(f"        {p_name} (query): {p_desc}")

            # Request Body
            has_body = 'requestBody' in details
            if has_body:
                args.append("body: Dict[str, Any]")
                doc_params.append("        body: Payload to send")

            args.append("**kwargs") # catch-all for query params

            # Construct function body
            f_code = f"    def {func_name}({', '.join(args)}) -> Any:\n"
            f_code += f"        \"\"\"\n        {description}\n"
            if doc_params:
                f_code += "\n" + "\n".join(doc_params)
            f_code += "\n        \"\"\"\n"
            
            # URL construction
            # Replace {param} with {param} for f-string if strict, but let's simpler:
            url_fstring = path
            for pp in path_params:
                url_fstring = url_fstring.replace(f"{{{pp}}}", f"{{{pp}}}")
            
            f_code += f"        url = f\"{{self.base_url}}{url_fstring}\"\n"
            
            # Query Params
            f_code += "        params = {k: v for k, v in kwargs.items() if v is not None}\n"
            
            # Call
            method_upper = method_name.upper()
            if has_body:
                f_code += f"        return self._request('{method_upper}', url, params=params, json=body)\n"
            else:
                f_code += f"        return self._request('{method_upper}', url, params=params)\n"
            
            methods_code.append(f_code)

    print(f"Generated {len(methods_code)} methods.")

    client_template = f"""import requests
import os
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load tokens from .credentials/bling_api_tokens.env
cred_path = os.path.join(os.path.dirname(__file__), '.credentials', 'bling_api_tokens.env')
load_dotenv(cred_path)

class BlingClient:
    def __init__(self):
        self.base_url = "https://www.bling.com.br/Api/v3"
        self.access_token = os.getenv("ACCESS_TOKEN")
        self.session = requests.Session()
        self.session.headers.update({{
            "Authorization": f"Bearer {{self.access_token}}",
            "Accept": "application/json"
        }})

    def _request(self, method: str, url: str, **kwargs) -> Any:
        try:
            response = self.session.request(method, url, **kwargs)
            # Handle Token expiration (simplified)
            if response.status_code == 401:
                print("Token expired or invalid. Please refresh tokens using bling_oauth.ps1")
                raise Exception("Unauthorized - Token Expired")
            
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Request Failed: {{e}}")
            if e.response is not None:
                print(f"Response: {{e.response.text}}")
            raise

{chr(10).join(methods_code)}
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(client_template)
    print(f"Client saved to {output_path}")

if __name__ == "__main__":
    generate_client("bling-openapi.json", "bling_client.py")
