import requests
import json

url = "http://192.168.1.73/commands/velocity"
headers = {'Content-Type': 'application/json'}
data = {"linear": 0.1, "angular": 0.0}  # Move forward slowly

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.status_code)