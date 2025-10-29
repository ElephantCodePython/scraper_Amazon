import scrapy
from scrapy_playwright.page import PageMethod
import logging
from selectolax.lexbor import LexborHTMLParser
from product_amazon.items import ProductItem
from urllib.parse import urljoin
import re
import json

asin_pattern_ = re.compile(r"(?:dp/|gp/product/|gp/aw/d/|gp/offer-listing/|exec/obidos/ASIN/|product-reviews/|asin=)([A-Z0-9]{10})")

def build_product_url(base_url, asin):
    try:
        asin_pattern = asin_pattern_
        match = asin_pattern.search(base_url)
        if match:
            return asin_pattern.sub(match.group(0).replace(match.group(1), asin), base_url)
    except Exception as e:
        logging.error(f'error build_product_url is {e}')
        return None

def extract_asin(url):
    pattern = asin_pattern_
    match = pattern.search(url)
    if match:
        return match.group(1)
    return None


class ProductSpider(scrapy.Spider):
    name = "product"
    allowed_domains = ["www.amazon.com"]
    asins_seen_global = set()

    def start_requests(self):
        urls = {'gaming':'https://www.amazon.com/s?k=gaming'}

        for category,url in urls.items():
            yield scrapy.Request(url=url, meta=dict(playwright=True,playwright_include_page=True,name=category,
                # playwright_context="proxy_rotating",
                playwright_page_methods=[PageMethod('wait_for_load_state', 'networkidle', timeout=90000)]),
                callback=self.parse,errback=self.error_handler)
            logging.info(f'request url {url}')


    def error_handler(self, failure):
        request = failure.request
        self.logger.warning(f"url : {request.url}")
        self.logger.warning(f"error : {repr(failure.value)}")
        retry_count = request.meta.get("retry_count", 0)
        if retry_count < 3:
            new_request = request.copy()
            new_request.meta["retry_count"] = retry_count + 1
            new_request.dont_filter = True
            self.logger.info(f"Retrying {request.url} (attempt {retry_count + 1})")
            yield new_request
        else:
            self.logger.error(f"Giving up on {request.url} after {retry_count} retries")


    async def parse(self, response):
        page = response.meta.get('playwright_page')
        category_name = response.meta['name']
        base_url = 'https://www.amazon.com/'
        if not page:
            self.logger.error("Playwright page not found in response.meta")
            return
        try:
            count, max_count = 0, 14
            while count < max_count:
                old_height = await page.evaluate("document.body.scrollHeight")
                for _ in range(12):
                    await page.keyboard.press("ArrowDown")
                await page.wait_for_timeout(500)
                new_height = await page.evaluate("document.body.scrollHeight")
                if old_height == new_height:
                    count += 1
                else:
                    count = 0

            html_content = await page.content()
            html_tree = LexborHTMLParser(html_content)

            product_elements = html_tree.css('div[data-asin]')
            for product in product_elements:
                link_element = product.css_first('a[class*="link-normal"]')
                if link_element and link_element.attributes.get('href'):
                    price_element = product.css_first('span.a-price-whole')
                    price = price_element.text(strip=True) if price_element else ''
                    product_url = urljoin(base_url, link_element.attributes.get('href'))
                    yield scrapy.Request(url=product_url, meta=dict(playwright=True, name=category_name, price=price,
                        playwright_include_page=True,
                        # playwright_context="proxy_rotating",
                        playwright_page_methods=[PageMethod('wait_for_load_state','domcontentloaded',
                        timeout=90000)]), callback=self.parse_product_page, errback=self.error_handler)

            # next_button = html_tree.css_first('a[class*="s-pagination-next"]')
            # if next_button and next_button.attributes.get('href'):
            #     next_page_url = urljoin(base_url, next_button.attributes.get('href'))
            #     logging.info(f'next page is {next_page_url}')
            #     yield scrapy.Request(url=next_page_url, meta=dict(playwright=True, name=category_name,
            #         playwright_include_page=True,
            #         playwright_page_methods=[PageMethod('wait_for_load_state', 'networkidle',
            #         timeout=90000)]),callback=self.parse,errback=self.error_handler)

        except Exception as e:
            self.logger.error(f'{e}')

        else:
            self.logger.info("finish page")

        finally:
            await page.close()

    async def parse_product_page(self, response):
        page = response.meta.get('playwright_page')
        category_name = response.meta['name']
        fallback_price = response.meta.get('price')
        base_url = response.url
        try:
            # asins 1
            asins = []
            async def handle_response(response):
                if "ajax" in response.url:
                    try:
                        json_data = await response.json()
                        asin = json_data.get("ASIN")
                        if asin:
                            self.logger.info(f'asin with handle-response : {asin}')
                            asins.append(asin)
                    except:
                        pass

            page.on("response", handle_response)
            self.logger.info('finish handle_response')
            await page.wait_for_load_state('networkidle', timeout=15000)

            # scroll
            for _ in range(14):
                for _ in range(15):
                    await page.keyboard.press("ArrowDown")
                await page.wait_for_timeout(500)


            # html
            html_content = await page.content()
            html_tree = LexborHTMLParser(html_content)

            # extract product
            current_asin = extract_asin(response.url)

            item = ProductItem()
            try:
                price_whole_el = html_tree.css_first('span.a-price-whole')
                price_fraction_el = html_tree.css_first('span.a-price-fraction')
                price_whole = price_whole_el.text(strip=True) if price_whole_el else '0'
                price_fraction = price_fraction_el.text(strip=True) if price_fraction_el else '00'
                price = f"{price_whole}.{price_fraction}" if price_whole else fallback_price
                if '0.00' in price:
                    price = ''
                item['price'] = price

                title_element = html_tree.css_first('span[id*="productTitle"]')
                item['title'] = title_element.text(strip=True) if title_element else ''

                stars_element = html_tree.css_first('span.a-icon-alt')
                item['stars'] = stars_element.text(strip=True) if stars_element else ''

                rating_element = html_tree.css_first('span#acrCustomerReviewText')
                item['rating'] = rating_element.text(strip=True) if rating_element else ''

                overview_elements = html_tree.css('div[id*="productOverview_feature"]')

                item['information'] = [[tr.text(deep=True, strip=True, separator=" | ") for tr in info.css('tr')]
                                       for info in overview_elements]

                img_elements = html_tree.css_first('div[id="imgTagWrapperId"] > img')
                item['img'] = img_elements.attributes.get('src') if img_elements else ''


            except Exception as e:
                logging.error(f"Error in extract_product_details: {e}")

            item['category'] = category_name
            item['url'] = response.url
            item['asin'] = current_asin

            yield item

            # asin 2
            current_asin = extract_asin(response.url)
            if current_asin and current_asin not in self.asins_seen_global:
                self.asins_seen_global.add(current_asin)
                self.logger.info(f'asin response url :{current_asin}')

            #asin 3
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
                                        self.logger.info(f'asin script : {asin_value}')
                                        asins.append(asin_value)
                    except :
                        continue

            # asin 4
            asin_elements = html_tree.css('li[data-asin]')
            for asin_element in asin_elements:
                asin_value = asin_element.attributes.get('data-asin')
                if asin_value and asin_value not in self.asins_seen_global:
                    self.logger.info(f'extraction asin : {asin_value}')
                    asins.append(asin_value)


            for asin_value in asins:
                if asin_value not in self.asins_seen_global:
                    self.asins_seen_global.add(asin_value)
                    new_url = build_product_url(base_url,asin_value)
                    if new_url:
                        self.logger.info(f'request url in asins_seen_global : {asin_value}')
                        yield scrapy.Request(url=new_url, meta=dict(playwright=True,name=category_name,
                            playwright_include_page=True,
                            # playwright_context="proxy_rotating",
                            playwright_page_methods=[PageMethod('wait_for_load_state', 'domcontentloaded',
                            timeout=90000)]), callback=self.parse_product_page, errback=self.error_handler)

        except Exception as e:
            self.logger.error(f"Error in parse_product_page for {response.url}: {e}")

        finally:
            if page:
                page.remove_listener("response", handle_response)
            if page and not page.is_closed():
                await page.close()

# scrapy crawl product 
