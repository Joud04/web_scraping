# Web Scraping Project - Target S19 (Automation Exercise)

## Group Members
- Walid HDILOU
- Joud ATALLAH
- Amine KAOUTAR

## Project Description
This project is a professional-grade web scraper designed to collect product information from the Automation Exercise website. It implements a Breadth-First Search (BFS) crawling strategy to discover categories and handle pagination.

## Technical Stack
- **Language**: Python 3.11
- **Crawling**: [crawl4ai](https://github.com/unclecode/crawl4ai) & Playwright
- **Parsing**: BeautifulSoup4
- **Data Validation**: Pydantic
- **Deployment**: Docker & Docker Compose

## How to Run
1. Build and run the scraper using Docker:
   ```bash
   docker-compose up --build
   ```
2. The output will be generated in the `data/` directory as `sortie.jsonl`.

## Output Format
The data is exported in JSONL format, ensuring each line is a valid JSON object representing a product.
