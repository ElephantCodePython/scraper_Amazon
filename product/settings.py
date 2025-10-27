# ______ BOT _______
BOT_NAME = "product_amazon"
SPIDER_MODULES = ["product_amazon.spiders"]
NEWSPIDER_MODULE = "product_amazon.spiders"
ADDONS = {}
# Obey robots.txt rules
ROBOTSTXT_OBEY = False
LOG_LEVEL = 'INFO'
# Concurrency and throttling settings
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 4
# Disable cookies (enabled by default)
COOKIES_ENABLED = True
# ---------- Playwright settings ----------
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": False,
    "timeout": 60000
}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 90000
# ___________ Proxy ___________
#
# ( input proxy and token )
#
# PLAYWRIGHT_CONTEXTS = {
#     "proxy_rotating": {
#         "proxy": {
#             "server": "proxy",
#             "username": "token",
#         },
#         "java_script_enabled": True,
#         "ignore_https_errors": True,
#     }
# }
# ---------- Spider middlewares ----------
DOWNLOADER_MIDDLEWARES = {
   "product_amazon.middlewares.FakeHeaders": 300,
}
ITEM_PIPELINES = {
   'product_amazon.pipelines.ProductDatabasePipeline': 200,
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
