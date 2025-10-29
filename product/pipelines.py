import sqlite3
from scrapy.exceptions import DropItem

class AsinValidationPipeline:
    def process_item(self, item, spider):
        if not item.get('asin'):
            raise DropItem(f"remove item : {item.get('url')}")
        else:
            return item


class ProductAmazonPipeline:
    def open_spider(self, spider):
        self.connection = sqlite3.connect("products.db")
        self.cursor = self.connection.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                price TEXT,
                stars TEXT,
                rating TEXT,
                information TEXT,
                img TEXT,
                category TEXT,
                asin TEXT UNIQUE,
                url TEXT
            )
        """)
        self.connection.commit()

    def close_spider(self, spider):
        self.connection.close()

    def process_item(self, item, spider):
        self.cursor.execute("""
            INSERT OR IGNORE INTO products
            (title, price, stars, rating, information, img, category, asin, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.get('title',''),
            item.get('price',''),
            item.get('stars',''),
            item.get('rating',''),
            str(item.get('information','')),
            item.get('img',''),
            item.get('category',''),
            item.get('asin',''),
            item.get('url','')
        ))
        self.connection.commit()
        return item


