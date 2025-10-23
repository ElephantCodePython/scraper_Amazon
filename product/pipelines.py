import aiosqlite
import json
import logging

class ProductDatabasePipeline:
    async def open_spider(self, spider):
        self.db = await aiosqlite.connect("products.db")
        async with self.db.execute('''
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
        '''):
            pass
        await self.db.commit()
        logging.info("Database connection opened and table created.")

    async def close_spider(self, spider):
        await self.db.close()
        logging.info("Database connection closed.")

    async def process_item(self, item, spider):
        try:
            information_json = json.dumps(item.get('information', []))

            async with self.db.execute('''
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
            )):
                pass
            await self.db.commit()
            logging.info(f"Item stored in database: {item.get('title', '')}")
        except Exception as e:
            logging.error(f"Failed to store item: {e}")

        return item



