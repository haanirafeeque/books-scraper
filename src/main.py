from pathlib import Path
import requests

URL = "https://books.toscrape.com/"
CACHE_FILE = Path("/cache/catalogue-page-1.html")

if CACHE_FILE.exists():
    html = CACHE_FILE.read_text(encoding="utf-8")
    print("CACHE HIT")
    print(f"Response Size : {len(html)} bytes")
else:
    header = {
        "User-Agent" : "FlyRankInternship-A9/1.0 (+https://github.com/haanirafeeque/books-scraper)"
    }
    response = requests.get(URL,headers=header,timeout=10)
    if response.status_code != 200:
        print(f"FAILED TO FETCH : HTTP{response.status_code}")
    else:
        html = response.text
        CACHE_FILE.parent.mkdir(parents=True,exist_ok=True)
        CACHE_FILE.write_text(html,encoding="utf-8")
        print("FETCH")
        print(f"Response Size : {len(html)} bytes")
