from pathlib import Path


class BursaFetcher:
    BASE_URL = "https://www.bursamalaysia.com/market_information/announcements/company_announcement"

    async def find_latest_filing(self, ticker: str) -> str | None:
        raise NotImplementedError(
            f"Live Bursa fetch is not ready for ticker {ticker}. "
            "Use one of the pre-cached demo companies."
        )

    async def download_pdf(self, url: str, output_path: Path) -> Path:
        raise NotImplementedError(
            f"Live Bursa PDF download is not ready for {url}. "
            "Place the PDF in data/demo_filings/ and run make extract."
        )
