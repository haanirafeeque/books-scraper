from pathlib import Path
from time import monotonic, sleep
from urllib.parse import urljoin
from pydantic import BaseModel, HttpUrl
from datetime import datetime, timezone


import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/"
CACHE_DIR = Path("cache")
OUTPUT_DIR = Path("output")


USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/haanirafeeque/books-scraper)"

last_request_time = None
pages_fetched=0
cache_hits=0


def fetch_page(url: str, cache_file: Path) -> str:
    global last_request_time, pages_fetched, cache_hits

    if cache_file.exists():
        cache_hits += 1
        return cache_file.read_text(encoding="utf-8")

    headers = {
        "User-Agent": USER_AGENT
    }

    for attempt in range(2):
        if last_request_time is not None:
            elapsed = monotonic() - last_request_time

            if elapsed < 0.5:
                sleep(0.5 - elapsed)

        last_request_time = monotonic()

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=10,
            )
        except requests.RequestException:
            if attempt == 0:
                sleep(1)
                continue

            raise

        if response.status_code == 200:
            pages_fetched += 1
            html = response.content.decode("utf-8")

            cache_file.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            cache_file.write_text(
                html,
                encoding="utf-8"
            )

            return html

        if response.status_code in (500, 502, 503, 504):
            if attempt == 0:
                sleep(1)
                continue

        raise RuntimeError(
            f"HTTP {response.status_code}: {url}"
        )

    raise RuntimeError(f"Failed to fetch: {url}")

def discover_pages():
    current_url = BASE_URL
    catalogue_pages = []
    all_books = []

    for page_number in range(1, 4):
        cache_file = CACHE_DIR / f"catalogue-page-{page_number}.html"

        html = fetch_page(current_url, cache_file)

        soup = BeautifulSoup(html, "html.parser")

        catalogue_pages.append(current_url)

        for book in soup.select("article.product_pod h3 a"):
            href = book.get("href")

            if href:
                absolute_url = urljoin(current_url, href)

                all_books.append({
                    "product_url": absolute_url,
                    "source_page": current_url
                })

        next_link = soup.select_one("li.next a")

        if next_link is None:
            break

        next_href = next_link.get("href")

        if not next_href:
            break

        current_url = urljoin(current_url, next_href)

    unique_books = list({
        book["product_url"]: book
        for book in all_books
    }.values())

    return catalogue_pages, all_books, unique_books



def extract_book(book):
    url = book["product_url"]

    cache_file = CACHE_DIR / "details" / (
        book["product_url"].split("/")[-2] + ".html"
    )

    html = fetch_page(url, cache_file)

    soup = BeautifulSoup(html, "html.parser")

    product = soup.select_one("div.product_main")

    title = product.select_one("h1").get_text(strip=True)

    price = product.select_one(
        "p.price_color"
    ).get_text(strip=True)

    availability = product.select_one(
        "p.availability"
    ).get_text(" ", strip=True)

    rating = product.select_one(
        "p.star-rating"
    )

    rating = rating.get("class")[1] if rating else None

    description_element = soup.select_one(
        "#product_description + p"
    )

    description = (
        description_element.get_text(
            " ",
            strip=True
        )
        if description_element
        else None
    )

    return {
        "title": title,
        "product_url": url,
        "price_text": price,
        "availability_text": availability,
        "rating_text": rating,
        "description": description,
        "source_page": book["source_page"],
        "fetched_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


class Book(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str | None
    description: str | None
    source_page: HttpUrl
    fetched_at: str

def clean_price(price_text):
    return float(
        price_text.replace("Â£", "").replace("£", "").strip()
    )#Here when converting records i encountered an encoding probem which converts the gbp to Â£ so i replace that do it according to how the encoding is


def normalize_book(record):
    record["price_gbp"] = clean_price(
        record["price_text"]
    )

    return Book(**record)

def main():
    start_time = datetime.now(timezone.utc)
    start = monotonic()
    catalogue_pages, discovered_books, unique_books = discover_pages()
    unique_books.append({
    "product_url": "https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html",
    "source_page": BASE_URL
    })
    """
    checking if the loop contiunues after a broken url and yes the url was given by chatgpt :>"""

    print(
        f"catalogue_pages={len(catalogue_pages)}, "
        f"discovered={len(discovered_books)}, "
        f"unique_urls={len(unique_books)}"
    )
    
    records = []
    failed_pages = []
    for book in unique_books:
        try:
            record = extract_book(book)
            records.append(record)

        except Exception as error:
            failed_pages.append({
                "url": book["product_url"],
                "error": str(error)
            })

            print(
                f"FAILED: {book['product_url']}"
            )

    good_books = []
    errors = []

    for record in records:
        try:
            book = normalize_book(record)
            good_books.append(book.model_dump(mode="json"))

        except Exception as error:
            print("ERROR:", error)
            errors.append({
                "record": record,
                "error": str(error)
            })

    OUTPUT_DIR.mkdir(exist_ok=True)

    with open(
        OUTPUT_DIR / "books.json",
        "w",
        encoding="utf-8"
    ) as file:
        import json

        json.dump(
            good_books,
            file,
            indent=2,
            ensure_ascii=False
        )

    with open(
        OUTPUT_DIR / "errors.json",
        "w",
        encoding="utf-8"
    ) as file:
        import json

        json.dump(
            errors,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(f"Valid books: {len(good_books)}")
    print(f"Errors: {len(errors)}")
    duration = monotonic() - start

    run_report = {
    "start_time": start_time.isoformat(),
    "duration_seconds": round(duration, 2),
    "pages_fetched": pages_fetched,
    "cache_hits": cache_hits,
    "valid_records": len(good_books),
    "invalid_records": len(errors),
    "failed_pages": len(failed_pages),
} 

    with open(
    OUTPUT_DIR / "run-report.json",
    "w",
    encoding="utf-8"
    ) as file:
        json.dump(
        run_report,
        file,
        indent=2
    )

if __name__ == "__main__":
    main()