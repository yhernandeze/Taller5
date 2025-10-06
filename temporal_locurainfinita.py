import requests
 
url = "http://10.43.100.103:8080/data?group_number=6"
 
try:
    r = requests.get(url, timeout=10)
    print(f"Status Code: {r.status_code}")
    print(f"Content-Type: {r.headers.get('Content-Type')}")
    print("\n--- Contenido ---")
    print(r.text[:500])  # Primeros 500 caracteres
    
except Exception as e:
    print(f"Error: {e}")