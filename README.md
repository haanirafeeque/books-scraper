# Books Scraper

A Python web scraper built as part of the internship assignment using
Requests, BeautifulSoup, and Pydantic.

## Target Classification

### Target

Books to Scrape

https://books.toscrape.com/

Books to Scrape is a sandbox website designed for practicing web
scraping.

### Scope

This scraper collects data from the first 3 catalogue pages only.

The expected scope is:

- 3 catalogue pages
- 60 books

### Data Collected

For each book, the scraper collects:

- title
- product_url
- price_text
- availability_text
- rating_text
- description
- source_page
- fetched_at

### robots.txt

Requested:

https://books.toscrape.com/robots.txt

Result:

HTTP 404 Not Found.

No robots.txt file was found at the requested location.

I will not reuse this code on another site without checking its rules and terms first.

---

## Installation

This project uses Python and uv.

Install the dependencies with:

```bash
uv sync