import requests

url = "https://bing-web-search1.p.rapidapi.com/search"  # ✅ correct path!
query = "machine learning"
headers = {
    "X-RapidAPI-Key": "4de2a67504mshbead1d7f14f4773p15b0ddjsn825b5608a30b",
    "X-RapidAPI-Host": "bing-web-search1.p.rapidapi.com"
}
params = {"q": query, "count": 3, "textFormat": "Raw", "safeSearch": "Moderate"}

res = requests.get(url, headers=headers, params=params)
print(res.status_code)
print(res.json())
