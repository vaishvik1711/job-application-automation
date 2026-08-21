"""
Browser automation using Playwright for job application submission.
"""
import asyncio
import random
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from config import load_settings
from utils.logger import get_logger
from utils.helpers import clean_text

logger = get_logger(__name__)


@dataclass
class BrowserConfig:
    """Browser configuration settings."""
    headless: bool = True
    slow_mo: int = 100
    timeout: int = 30000
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1366, "height": 768})
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    locale: str = "en-CA"
    timezone_id: str = "America/Toronto"
    proxy: Optional[Dict[str, str]] = None
    record_video_dir: Optional[str] = None
    record_har_path: Optional[str] = None


@dataclass
class ApplicationResult:
    """Result of an application attempt."""
    success: bool
    job_id: int
    application_id: Optional[int] = None
    error: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)
    steps_completed: List[str] = field(default_factory=list)
    requires_human: bool = False
    human_intervention_reason: Optional[str] = None


class BrowserAutomation:
    """
    Main browser automation class for job applications.
    Uses Playwright for reliable browser automation with anti-detection measures.
    """

    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._settings = load_settings()

    async def __aenter__(self) -> "BrowserAutomation":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Start the browser."""
        self._playwright = await async_playwright().start()

        # Launch browser with anti-detection measures
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ]
        )

        # Create context with realistic settings
        self._context = await self._browser.new_context(
            viewport=self.config.viewport,
            user_agent=self.config.user_agent,
            locale=self.config.locale,
            timezone_id=self.config.timezone_id,
            proxy=self.config.proxy,
            record_video_dir=self.config.record_video_dir,
            record_har_path=self.config.record_har_path,
            # Additional anti-detection
            java_script_enabled=True,
            accept_downloads=True,
            ignore_https_errors=True,
        )

        # Add stealth scripts
        await self._context.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Override navigator.plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Override navigator.languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-CA', 'en-US', 'en']
            });
        """)

        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.config.timeout)

        logger.info("Browser started successfully")

    async def close(self):
        """Close the browser."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser closed")

    @property
    def page(self) -> Page:
        """Get the current page."""
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    async def navigate(self, url: str, wait_until: str = "networkidle") -> bool:
        """Navigate to a URL with error handling."""
        try:
            response = await self._page.goto(url, wait_until=wait_until, timeout=self.config.timeout)
            if response and response.status >= 400:
                logger.warning(f"Navigation returned status {response.status}: {url}")
                return False
            return True
        except Exception as e:
            logger.error(f"Navigation failed for {url}: {e}")
            return False

    async def wait_for_selector(self, selector: str, timeout: int = 10000, state: str = "visible") -> bool:
        """Wait for a selector to appear."""
        try:
            await self._page.wait_for_selector(selector, timeout=timeout, state=state)
            return True
        except Exception:
            return False

    async def fill_field(self, selector: str, value: str, delay: int = 50) -> bool:
        """Fill a form field with human-like typing."""
        try:
            await self._page.fill(selector, "")
            await self._page.type(selector, value, delay=delay)
            return True
        except Exception as e:
            logger.error(f"Failed to fill {selector}: {e}")
            return False

    async def click_element(self, selector: str, delay: int = 100) -> bool:
        """Click an element with optional delay."""
        try:
            await self._page.click(selector, delay=delay)
            return True
        except Exception as e:
            logger.error(f"Failed to click {selector}: {e}")
            return False

    async def select_option(self, selector: str, value: str) -> bool:
        """Select an option from a dropdown.

        Tries exact value, then visible label, then a case-insensitive
        partial match over both — ATS selects routinely use terse values
        ('yes'/'no') while profiles carry prose ('Canadian citizen').
        """
        for attempt in ({"value": value}, {"label": value}):
            try:
                await self._page.select_option(selector, **attempt)
                return True
            except Exception:
                continue
        try:
            matched = await self._page.eval_on_selector(
                selector,
                """(sel, wanted) => {
                    const w = String(wanted).toLowerCase().trim();
                    for (const opt of sel.options) {
                        const hay = (opt.value + ' ' + opt.textContent).toLowerCase();
                        if (!opt.value && !opt.textContent.trim()) continue;
                        if (hay.includes(w) || (w.includes(opt.value.toLowerCase()) && opt.value)) {
                            sel.value = opt.value;
                            sel.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                }""",
                value,
            )
            if matched:
                return True
        except Exception as e:
            logger.debug(f"Fuzzy select failed on {selector}: {e}")
        logger.error(f"Failed to select option in {selector}: no match for {value!r}")
        return False

    async def upload_file(self, selector: str, file_path: str) -> bool:
        """Upload a file."""
        try:
            await self._page.set_input_files(selector, file_path)
            return True
        except Exception as e:
            logger.error(f"Failed to upload file to {selector}: {e}")
            return False

    async def take_screenshot(self, path: str, full_page: bool = True) -> bool:
        """Take a screenshot."""
        try:
            await self._page.screenshot(path=path, full_page=full_page)
            return True
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return False

    async def get_page_content(self) -> str:
        """Get the page HTML content."""
        return await self._page.content()

    async def evaluate(self, script: str) -> Any:
        """Evaluate JavaScript in the page context."""
        return await self._page.evaluate(script)

    async def wait_random(self, min_ms: int = 500, max_ms: int = 2000):
        """Wait for a random duration to mimic human behavior."""
        delay = random.randint(min_ms, max_ms)
        await asyncio.sleep(delay / 1000)

    async def scroll_to_bottom(self, step: int = 500, delay: int = 200):
        """Scroll to bottom of page gradually."""
        await self._page.evaluate(f"""
            (() => {{
                return new Promise((resolve) => {{
                    const scrollStep = {step};
                    const scrollDelay = {delay};
                    const scroll = () => {{
                        window.scrollBy(0, scrollStep);
                        if (window.innerHeight + window.scrollY < document.body.offsetHeight) {{
                            setTimeout(scroll, scrollDelay);
                        }} else {{
                            resolve();
                        }}
                    }};
                    scroll();
                }});
            }})()
        """)

    async def detect_captcha(self) -> bool:
        """Detect if a CAPTCHA is present."""
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            ".g-recaptcha",
            ".h-captcha",
            "#recaptcha",
            "[data-sitekey]",
            ".captcha",
        ]

        for selector in captcha_selectors:
            if await self._page.query_selector(selector):
                return True
        return False

    async def detect_cloudflare(self) -> bool:
        """Detect Cloudflare challenge."""
        content = await self.get_page_content()
        return "cloudflare" in content.lower() and ("challenge" in content.lower() or "checking your browser" in content.lower())

    async def handle_popups(self):
        """Handle common popups (cookies, newsletter, etc.)."""
        popup_selectors = [
            "button:has-text('Accept')",
            "button:has-text('Accept All')",
            "button:has-text('I Agree')",
            "button:has-text('Allow All')",
            "[id*='cookie'] button",
            "[class*='cookie'] button",
            "button[aria-label*='close' i]",
            ".modal-close",
            ".popup-close",
        ]

        for selector in popup_selectors:
            try:
                element = await self._page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    await asyncio.sleep(0.5)
            except Exception:
                pass

    async def wait_for_navigation(self, timeout: int = 30000):
        """Wait for navigation to complete."""
        try:
            await self._page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception:
            pass


async def create_browser_automation(config: Optional[BrowserConfig] = None) -> BrowserAutomation:
    """Factory function to create and start browser automation."""
    automation = BrowserAutomation(config)
    await automation.start()
    return automation