from pathlib import Path
from time import monotonic, sleep
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/"
CACHE_DIR = Path("cache")

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/YOUR_USERNAME/YOUR_REPO)"

last_request_time = None


def fetch_page(url: str, cache_file: Path) -> str:
    global last_request_time

    if cache_file.exists():
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

    return html


def discover_pages():
    current_url = BASE_URL
    catalogue_pages = []
    all_book_urls = []

    for page_number in range(1, 4):
        cache_file = CACHE_DIR / f"catalogue-page-{page_number}.html"

        html = fetch_page(current_url, cache_file)

        soup = BeautifulSoup(html, "html.parser")

        catalogue_pages.append(current_url)


        for book in soup.select("article.product_pod h3 a"):
            href = book.get("href")

            if href:
                absolute_url = urljoin(current_url, href)
                all_book_urls.append(absolute_url)

        next_link = soup.select_one("li.next a")

        if next_link is None:
            break

        next_href = next_link.get("href")

        if not next_href:
            break

        current_url = urljoin(current_url, next_href)

    unique_book_urls = list(dict.fromkeys(all_book_urls))

    return catalogue_pages, all_book_urls, unique_book_urls


def main():
    catalogue_pages, discovered_urls, unique_urls = discover_pages()

    print(
        f"catalogue_pages={len(catalogue_pages)}, "
        f"discovered={len(discovered_urls)}, "
        f"unique_urls={len(unique_urls)}"
    )


if __name__ == "__main__":
    main()