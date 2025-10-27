import scrapy

class ProductItem(scrapy.Item):
    asin = scrapy.Field()
    title = scrapy.Field()
    price = scrapy.Field()
    stars = scrapy.Field()
    rating = scrapy.Field()
    information = scrapy.Field()
    img = scrapy.Field()
    category = scrapy.Field()
    url = scrapy.Field()
