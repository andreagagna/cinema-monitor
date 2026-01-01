import logging
import random
import time
import urllib.parse
from typing import Tuple

from playwright.sync_api import Browser, Page, sync_playwright

from legacy.seat_counter import SeatDetectionConfig
from legacy.seat_counter import count_seats_from_image as detect_seats
from src.config import AppConfig

logger = logging.getLogger(__name__)


class CinemaMonitor:
    def __init__(self, config: AppConfig):
        self.config = config
        self.target_color = (76, 175, 80)  # Green
        self.tolerance = 40

    def parse_date_from_url(self, url):
        """Extracts the date from the URL 'at' parameter."""
        try:
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.fragment)  # It's in the fragment
            if "at" in params:
                return params["at"][0]
            # Also check query params just in case
            params_query = urllib.parse.parse_qs(parsed.query)
            if "at" in params_query:
                return params_query["at"][0]
        except Exception as e:
            print(f"Error parsing date: {e}")
        return None

    def count_seats_from_image(self, image_path):
        """Counts available seats (green blobs) from the screenshot."""
        try:
            cfg = SeatDetectionConfig(target_color=self.target_color, tolerance=self.tolerance)
            count, _ = detect_seats(image_path, cfg)
            return count
        except Exception as e:
            logger.exception("Error counting seats from %s: %s", image_path, e)
            return 0

    def _prepare_browser(self, playwright) -> Tuple[Browser, Page]:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return browser, context.new_page()

    def _load_showtime_page(self, page: Page, movie_url: str) -> None:
        page.goto(movie_url)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(random.uniform(1, 3))
        self._accept_cookies(page)

    def _accept_cookies(self, page: Page) -> None:
        try:
            cookie_btn = (
                page.get_by_text("Reject All Cookies", exact=False)
                .or_(page.get_by_text("Odmítnout vše", exact=False))
                .first
            )
            if cookie_btn and cookie_btn.is_visible():
                cookie_btn.click()
                time.sleep(0.5)
                logger.info("Cookie banner dismissed")
        except Exception:
            logger.debug("No cookie banner displayed")

    def _select_showtime(self, page: Page) -> bool:
        showtime_btn = page.locator("a.btn-primary").filter(has_text=":").first
        try:
            showtime_btn.wait_for(timeout=5000)
        except Exception:
            return False

        if not showtime_btn.is_visible():
            return False

        logger.info("Selecting showtime: %s", showtime_btn.inner_text())
        showtime_btn.click()
        return True

    def _handle_guest_flow(self, page: Page) -> None:
        try:
            guest_btn = page.locator("button[data-automation-id='guest-button']")
            guest_btn.wait_for(timeout=3000)
            if guest_btn.is_visible():
                logger.info("Guest modal detected; continuing as guest")
                guest_btn.click()
        except Exception:
            logger.debug("Guest modal not shown")

    def _capture_seatmap(self, page: Page, screenshot_path: str = "latest_check.png") -> str:
        logger.info("Waiting for seat map to render")
        page.wait_for_selector(".seatmap", timeout=15000)
        time.sleep(1)  # allow rendering
        page.screenshot(path=screenshot_path)
        return screenshot_path

    def check_availability(self, movie_url):
        """Checks for available seats for the given movie URL."""
        logger.info("Checking availability for %s", movie_url)
        date = self.parse_date_from_url(movie_url)
        logger.info("Target Date: %s", date)

        with sync_playwright() as p:
            browser, page = self._prepare_browser(p)
            try:
                self._load_showtime_page(page, movie_url)
                if not self._select_showtime(page):
                    logger.warning("No showtime button found for %s", movie_url)
                    return {"status": "no_showtime", "seats": 0, "date": date}
                self._handle_guest_flow(page)

                screenshot_path = self._capture_seatmap(page)
                seats = self.count_seats_from_image(screenshot_path)
                logger.info("Available seats detected: %s", seats)

                return {
                    "status": "available" if seats > 0 else "full",
                    "seats": seats,
                    "date": date,
                    "screenshot": screenshot_path,
                }
            except Exception as e:
                logger.exception("Check failed: %s", e)
                return {"status": "error", "seats": 0, "error": str(e)}
            finally:
                browser.close()


if __name__ == "__main__":
    monitor = CinemaMonitor(AppConfig.from_env())
    result = monitor.check_availability(monitor.config.movie_url())
    print(result)
