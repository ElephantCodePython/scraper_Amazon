"""
Note:
Some documentation and comments were written with the assistance of Google's Gemini AI model
to improve code readability and consistency.
"""
"""
Amazon Product Scraper using Scrapy and Playwright.

This spider is designed for educational purposes, demonstrating how to handle
dynamic content on Amazon's product listing and detail pages by integrating
Playwright for full page rendering and Selectolax for efficient HTML parsing.

Features:
- Uses Playwright to load JavaScript-rendered content.
- Implements network interception (XHR/Fetch) to discover hidden product ASINs.
- Includes a 3-retry mechanism for handling transient request failures.
"""
import scrapy
from scrapy_playwright.page import PageMethod
from selectolax.lexbor import LexborHTMLParser
from urllib.parse import urljoin
import logging
from product.items import ProductItem
import re
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# extract data product
def extract_product_details(html_tree, fallback_price):
    """
    Extracts core product details (price, title, rating, etc.) from the product page HTML tree.

    :param html_tree: The parsed HTML tree (LexborHTMLParser) of the product page.
    :type html_tree: LexborHTMLParser
    :param fallback_price: Price passed from the listing page, used as a fallback if not found.
    :type fallback_price: str
    :returns: Populated ProductItem.
    :rtype: ProductItem
    """
    item = ProductItem()
    try:
        # price
        price_whole_el = html_tree.css_first('span.a-price-whole')
        price_fraction_el = html_tree.css_first('span.a-price-fraction')
        price_whole = price_whole_el.text(strip=True) if price_whole_el else '0'
        price_fraction = price_fraction_el.text(strip=True) if price_fraction_el else '00'
        price = f"{price_whole}.{price_fraction}" if price_whole else fallback_price
        if '0.00' in price:
            price = ''
        item['price'] = price
        # title
        title_element = html_tree.css_first('span[id*="productTitle"]')
        item['title'] = title_element.text(strip=True) if title_element else ''
        # stars
        stars_element = html_tree.css_first('span.a-icon-alt')
        item['stars'] = stars_element.text(strip=True) if stars_element else ''
        # rating
        rating_element = html_tree.css_first('span#acrCustomerReviewText')
        item['rating'] = rating_element.text(strip=True) if rating_element else ''
        # overview
        overview_elements = html_tree.css('div[id*="productOverview_feature"]')
        # Extract tables of product information
        item['information'] = [ [tr.text(deep=True, strip=True, separator=" | ") for tr in info.css('tr')]
            for info in overview_elements ]
        # image
        img_elements = html_tree.css_first('div[id="imgTagWrapperId"] > img')
        item['img'] = img_elements.attributes.get('src') if img_elements else ''

        return item

    except Exception as e:
        logging.error(f"Error in extract_product_details: {e}")
        return item


asin_pattern_ = re.compile(r"(?:dp|gp/product|gp/aw/d|gp/offer-listing|exec/obidos/ASIN|product-reviews|asin=)([A-Z0-9]{10})")

# create url
def build_product_url(base_url, asin):
    """
    Creates a new product URL by replacing the ASIN in the base URL, allowing for crawling variations.

    :param base_url: The original URL containing an ASIN.
    :type base_url: str
    :param asin: The new 10-character ASIN to insert.
    :type asin: str
    :returns: The new product URL, or None if the pattern is not found.
    :rtype: str or None
    """
    try:
        asin_pattern = asin_pattern_
        match = asin_pattern.search(base_url)
        if match:
            return asin_pattern.sub(match.group(0).replace(match.group(1), asin), base_url)
    except Exception as e:
        logging.error(f'error build_product_url is {e}')
        return None

# extract asin
def extract_asin(url):
    """
    Extracts the 10-character ASIN (Amazon Standard Identification Number) from a given URL.

    :param url: The URL string.
    :type url: str
    :returns: The ASIN string, or None.
    :rtype: str or None
    """
    pattern = asin_pattern_
    match = pattern.search(url)
    if match:
        return match.group(1)
    return None


class ProSpider(scrapy.Spider):
    """Scrapy Spider for crawling Amazon products using the Playwright integration."""
    name = "pro"
    allowed_domains = ["www.amazon.com"]
    # Global set to keep track of all ASINs that have been seen or queued
    asins_seen_global = set()

    # 1- start_requests -> url in urls -> request to parse
    def start_requests(self):
        """Initializes crawling by sending requests for defined category URLs."""
        urls = {
            'gaming' : 'https://www.amazon.com/s?k=gaming&_encoding=UTF8&content-id=amzn1.sym.edf433e2-b6d4-408e-986d-75239a5ced10&pd_rd_r=33de1a70-642b-4578-80d7-1eacda236ded&pd_rd_w=C9OQP&pd_rd_wg=YcFXd&pf_rd_p=edf433e2-b6d4-408e-986d-75239a5ced10&pf_rd_r=QQRKBXSWQCW6SHC5HJF9&ref=pd_hp_d_atf_unk',
            # 'home' : 'https://www.amazon.com/s?k=home&_encoding=UTF8&content-id=amzn1.sym.4da186f5-145b-4e27-9ae2-777c48d6d9cd&pd_rd_r=441a3564-99d6-41f1-9a40-88de7137cce9&pd_rd_w=GnCQb&pd_rd_wg=0sGas&pf_rd_p=4da186f5-145b-4e27-9ae2-777c48d6d9cd&pf_rd_r=6Q8HQPNCF3ZTYF2GASHZ&ref=pd_hp_d_atf_unk',
        }
        for category_name, category_url in urls.items():
            # Request uses Playwright and waits for networkidle state for full page load
            yield scrapy.Request(url=category_url, meta=dict(playwright=True, playwright_include_page=True, name=category_name,
                playwright_page_methods=[PageMethod('wait_for_load_state', 'networkidle', timeout=90000)]),
                callback=self.parse,errback=self.error_handler)

    # errback
    def error_handler(self, failure):
        """Implements a simple retry mechanism (up to 3 times) for failed requests."""
        request = failure.request
        self.logger.warning(f"url : {request.url}")
        self.logger.warning(f"error : {repr(failure.value)}")
        retry_count = request.meta.get("retry_count", 0)
        # Check retry limit
        if retry_count < 3:
            new_request = request.copy()
            new_request.meta["retry_count"] = retry_count + 1
            new_request.dont_filter = True # Ensure the request is processed again
            self.logger.info(f"Retrying {request.url} (attempt {retry_count + 1})")
            yield new_request
        else:
            self.logger.error(f"Giving up on {request.url} after {retry_count} retries")


    # 2- (Start Request ->) parse -> scroll to load content -> (extract product links -> request parse_product_page) ->
    # (++ Continue explanation ++) -> find next page link and request to parse again
    async def parse(self, response):
        """
        Parses the product listing page, extracts individual product URLs, and queues the next page.
        Requires Playwright to handle dynamic loading.
        """
        page = response.meta.get('playwright_page')
        category_name = response.meta['name']
        base_url = "https://www.amazon.com/"
        html_tree = ''
        if not page:
            logging.error("Playwright page not found in response.meta")
            return
        try:
            if category_name in ["gaming", "home"]:
                # scroll to next (Scroll to the pagination container to ensure the "Next" button loads)
                pagination_container = await page.locator('div[aria-label*="pagination"]')
                if pagination_container:
                    await pagination_container.scroll_into_view_if_needed(timeout=30000)
                else:
                    logging.warning(f'not find pagination_container in url : {response.url}')
                html_content = await page.content()
                html_tree = LexborHTMLParser(html_content)

                # extract links products -> request to parse_product_page
                product_elements = html_tree.css('div[data-asin]')
                for product in product_elements:
                    link_element = product.css_first('a[class*="link-normal"]')
                    if link_element and link_element.attributes.get('href'):
                        price_element = product.css_first('span.a-price-whole')
                        price = price_element.text(strip=True) if price_element else ''
                        product_url = urljoin(base_url, link_element.attributes.get('href'))
                        # Queue request for the detail page
                        yield scrapy.Request(url=product_url,meta=dict(playwright=True, name=category_name, price=price,
                            playwright_include_page=True,
                            playwright_page_methods=[PageMethod('wait_for_load_state', 'domcontentloaded',timeout=90000)]),
                            callback=self.parse_product_page, errback=self.error_handler)

                # find link next page and request to parse agin
                next_button = html_tree.css_first('a[class*="pagination-button"][class*="pagination-next"]')
                if next_button and next_button.attributes.get('href'):
                    next_page_url = urljoin(base_url, next_button.attributes.get('href'))
                    # Queue request for the next listing page
                    yield scrapy.Request(url=next_page_url, meta=dict(playwright=True, name=category_name,
                        playwright_include_page=True,
                        playwright_page_methods=[PageMethod('wait_for_load_state', 'networkidle', timeout=90000)]),
                        callback=self.parse, errback=self.error_handler)

        except Exception as e:
            logging.error(f"Error in parse: {e}")

        finally:
            # Close the Playwright page
            if page and not page.is_closed():
                await page.close()


    # 3- (parse ->) parse_product_page -> scroll to product_information -> html in selectolax -> extaract data -> save asin ->
    # (++ to continue explaining ++) -> find asin -> create url new and request
    async def parse_product_page(self, response):
        """
        Parses a single product page, extracts data, and actively searches for related
        ASIN variations via network intercepts, scripts, and HTML to queue new requests.
        """
        page = response.meta.get('playwright_page')
        category_name = response.meta['name']
        fallback_price = response.meta.get('price')
        base_url = response.url
        try:
            # List to collect newly discovered ASINs from all sources (XHR, scripts, HTML)
            asins = []

            # find asin and append in asins_seen
            # find asin in Fetch/XHR
            async def handle_response(response):
                """Callback to intercept network responses and extract ASIN from AJAX/Fetch calls."""
                if "ajax" in response.url:
                    try:
                        json_data = await response.json()
                        asin = json_data.get("ASIN")
                        if asin:
                            asins.append(asin)
                    except:
                        pass # Ignore non-JSON responses

            # Attach the response handler
            page.on("response", handle_response)
            # Wait for network activity to settle after initial load
            await page.wait_for_load_state('networkidle', timeout=15000)

            # scroll and html parse in selectolax
            # Scroll to product information to trigger dynamic loading of details
            product_information = await page.locator('div[id*="productDetails_feature"]')
            if product_information:
                await product_information.scroll_into_view_if_needed(timeout=15000)

            html_content = await page.content()
            html_tree = LexborHTMLParser(html_content)

            # extract information product
            item = extract_product_details(html_tree, fallback_price)
            item['category'] = category_name
            item['url'] = response.url
            yield item

            # asins_seen -> save asins in asin_seen
            # Track the current product's ASIN
            current_asin = extract_asin(response.url)
            if current_asin and current_asin not in self.asins_seen_global:
                self.asins_seen_global.add(current_asin)

            # find asin and append in asins_seen
            # find in script (Search for variation data embedded in JSON script tags)
            # asins = [] # NOTE: The 'asins' list is defined outside this block and handled by handle_response
            for script in html_tree.css("script"):
                text = script.text(deep=True,strip=True) or ""
                if "sortedDimValuesForAllDims" in text:
                    try:
                        data = json.loads(text)
                        for dim, values in data.get("sortedDimValuesForAllDims", {}).items():
                            for v in values:
                                if "defaultAsin" in v:
                                    asin_value = v["defaultAsin"]
                                    if asin_value and asin_value not in self.asins_seen_global:
                                        asins.append(asin_value)
                    except :
                        continue

            # find in html (Search for ASINs in HTML attributes for variation selectors)
            asin_elements = html_tree.css('li[data-asin]')
            for asin_element in asin_elements:
                asin_value = asin_element.attributes.get('data-asin')
                if asin_value and asin_value not in self.asins_seen_global:
                    asins.append(asin_value)


            # create url new and request (Queue newly discovered ASINs)
            for asin_value in asins:
                if asin_value not in self.asins_seen_global:
                    self.asins_seen_global.add(asin_value)
                    new_url = build_product_url(base_url,asin_value)
                    if new_url:
                        # Queue request for the product variation page
                        yield scrapy.Request(url=new_url, meta=dict(playwright=True,
                            name=category_name, playwright_include_page=True,
                            playwright_page_methods=[PageMethod('wait_for_load_state', 'domcontentloaded', timeout=90000)]),
                            callback=self.parse_product_page, errback=self.error_handler)

        except Exception as e:
            logging.error(f"Error in parse_product_page for {response.url}: {e}")

        finally:
            # Remove the network listener to prevent resource leakage
            if page:
                page.remove_listener("response", handle_response)
            # Close the Playwright page
            if page and not page.is_closed():
                await page.close()


# Scrapy execution command example:
# scrapy crawl pro
