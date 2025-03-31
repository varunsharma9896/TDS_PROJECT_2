import requests

url = "http://127.0.0.1:8000/api/"
file = {"files": open("abcd.zip", "rb")}
response = requests.post(url, files=file)
print(response.json())
