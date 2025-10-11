# ---------- Bot information ----------
BOT_NAME = "product"
SPIDER_MODULES = ["product.spiders"]
NEWSPIDER_MODULE = "product.spiders"
ADDONS = {}

# ---------- Robots.txt ----------
ROBOTSTXT_OBEY = False

# ---------- Concurrency and throttling ----------
CONCURRENT_REQUESTS = 2
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 4
RANDOMIZE_DOWNLOAD_DELAY = True

# ---------- Cookies ----------
COOKIES_ENABLED = True

# ---------- Playwright settings ----------
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": False,
    "timeout": 60000
}

# ---------- Spider middlewares ----------
SPIDER_MIDDLEWARES = {
   "product.middlewares.FakeHeaders": 300,
   "product.middlewares.ProxyMiddleware": 200
}

# ---------- Item pipelines ----------
ITEM_PIPELINES = {
   "product.pipelines.ProductDatabasePipeline": 300,
}

# ---------- AutoThrottle ----------
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 60


# ---------- Timeouts / retries ----------
DOWNLOAD_TIMEOUT = 60
RETRY_ENABLED = True
RETRY_TIMES = 5
RETRY_HTTP_CODES = [429, 500, 502, 503, 504, 522, 524]

# ---------- Feed encoding ----------
FEED_EXPORT_ENCODING = "utf-8"
