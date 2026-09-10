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


def fetch_page(url: str, cache_file: Path) -> str:
    global last_request_time

    if cache_file.exists():
        print(f"CACHE HIT: {cache_file}")
        return cache_file.read_text(encoding="utf-8")


    if last_request_time is not None:
        elapsed = monotonic() - last_request_time

        if elapsed < 0.5:
            sleep(0.5 - elapsed)

    headers = {
        "User-Agent": USER_AGENT
    }

    last_request_time = monotonic()
    
    response = requests.get(
        url,
        headers=headers,
        timeout=10,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch {url}: HTTP {response.status_code}"
        )

    html = response.text

    cache_file.parent.mkdir(parents=True, exist_ok=True)    
    cache_file.write_text(html, encoding="utf-8")
    print(f"FETCH: {url}")

    return html


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
    catalogue_pages, discovered_books, unique_books = discover_pages()

    print(
        f"catalogue_pages={len(catalogue_pages)}, "
        f"discovered={len(discovered_books)}, "
        f"unique_urls={len(unique_books)}"
    )

    records = []

    for book in unique_books:
        record = extract_book(book)
        records.append(record)

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

if __name__ == "__main__":
    main()