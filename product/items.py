import scrapy

class ProductItem(scrapy.Item):
    category = scrapy.Field()
    url = scrapy.Field()
    price = scrapy.Field()
    title = scrapy.Field()
    stars = scrapy.Field()
    rating = scrapy.Field()
    information = scrapy.Field()


