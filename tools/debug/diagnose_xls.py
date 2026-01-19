import os

file_path = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos.xls'

def check_header():
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
        print(f"First 16 bytes: {header}")
        
        if header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            print("Type: OLE Compound File (Legacy XLS)")
        elif header.startswith(b'PK\x03\x04'):
            print("Type: ZIP Archive (Likely XLSX renamed to XLS)")
        elif header.startswith(b'<?xml'):
            print("Type: XML File")
        elif header.startswith(b'<html') or b'<html' in header.lower():
            print("Type: HTML File")
        else:
            print("Type: Unknown binary/text")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_header()
