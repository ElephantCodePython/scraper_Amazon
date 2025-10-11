import aiosqlite
import json
import logging

class ProductDatabasePipeline:
    async def open_spider(self, spider):
        self.db = await aiosqlite.connect("products.db")
        self.cursor = await self.db.cursor()
        await self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                price TEXT,
                stars TEXT,
                rating TEXT,
                category TEXT,
                img TEXT,
                information TEXT
            )
        ''')
        await self.db.commit()
        logging.info("Database connection opened and table created.")

    async def close_spider(self, spider):
        await self.db.close()
        logging.info("Database connection closed.")

    async def process_item(self, item, spider):
        try:
            information_json = json.dumps(item.get('information', []))

            await self.cursor.execute('''
                INSERT OR REPLACE INTO products (url, title, price, stars, rating, category, img, information)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.get('url', ''),
                item.get('title', ''),
                item.get('price', ''),
                item.get('stars', ''),
                item.get('rating', ''),
                item.get('category', ''),
                item.get('img', ''),
                information_json
            ))
            await self.db.commit()
            logging.info(f"Item stored in database: {item['title']}")
        except Exception as e:
            logging.error(f"Failed to store item: {e}")

        return item