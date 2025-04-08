import asyncio
import feedparser
from pyrogram import Client

async def fetch_and_send_news(app: Client, db, global_settings_collection, urls):
    config = global_settings_collection.find_one({"_id": "config"})
    if not config or "news_channel" not in config:
        return

    news_channel = "@" + config["news_channel"]

    for url in urls:
        feed = await asyncio.to_thread(feedparser.parse, url)
        entries = list(feed.entries)[::-1]  # Reverse order to send newest last

        for entry in entries:
            entry_id = entry.get('id', entry.get('link'))

            if not db.sent_news.find_one({"entry_id": entry_id}):
                thumbnail_url = entry.media_thumbnail[0]['url'] if 'media_thumbnail' in entry else None
                msg = f"<b>**{entry.title}**</b>\n\n{entry.summary if 'summary' in entry else ''}\n\n<a href='{entry.link}'>Read more</a>"

                try:
                    await asyncio.sleep(15)  # Delay between messages
                    if thumbnail_url:
                        await app.send_photo(chat_id=news_channel, photo=thumbnail_url, caption=msg)
                    else:
                        await app.send_message(chat_id=news_channel, text=msg)

                    db.sent_news.insert_one({"entry_id": entry_id, "title": entry.title, "link": entry.link})
                    print(f"Sent news: {entry.title}")
                except Exception as e:
                    print(f"Error sending news message: {e}")

async def news_feed_loop(app: Client, db, global_settings_collection, urls):
    while True:
        await fetch_and_send_news(app, db, global_settings_collection, urls)
        await asyncio.sleep(10)  # Check for new news every 10 seconds
