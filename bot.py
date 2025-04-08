from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler
import feedparser
import config
import re
import time

app = Client("CanderellaNews", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN)

mongo = MongoClient(config.MONGO_URI)
db = mongo['CanderellaNews']
admins_col = db['admins']
rss_col = db['rss']
channels_col = db['channels']
posted_col = db['posted']

scheduler = BackgroundScheduler()
scheduler.start()

def clean_md(text):
    escape_chars = r"\_*[]()~`>#+-=|{}.!<>"
    return re.sub(f"([{re.escape(escape_chars)}])", r'\\\1', text)

def is_admin(user_id: int) -> bool:
    return user_id == config.OWNER_ID or admins_col.find_one({"user_id": user_id})

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_photo(
        photo=config.START_PIC,
        caption="**› Welcome to Canderella News Bot!**\n\nUse /help to explore all available commands.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Add to Group", url=f"https://t.me/{app.me.username}?startgroup=true")],
            [InlineKeyboardButton("Channel", url="https://t.me/Anime_World_Editz")]
        ])
    )

@app.on_message(filters.command("help"))
async def help_cmd(client, message: Message):
    await message.reply_photo(
        photo=config.START_PIC,
        caption="**› Help Menu**\n\n"
                "`/addadmin <user_id>` – Add a new admin\n"
                "`/removeadmin <user_id>` – Remove an admin\n"
                "`/adminslist` – List all admins\n\n"
                "`/addrss <url>` – Add RSS feed\n"
                "`/removerss <url>` – Remove RSS feed\n"
                "`/listrss` – List RSS feeds\n\n"
                "`/news` – Fetch and post latest news\n",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Developer", url="https://t.me/RexySama")]
        ])
    )

@app.on_message(filters.command("addadmin") & filters.private)
async def addadmin(client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("You are not authorized.")
    if len(message.command) < 2:
        return await message.reply("Usage: /addadmin <user_id>")
    try:
        uid = int(message.command[1])
        if admins_col.find_one({"user_id": uid}):
            return await message.reply("Already an admin.")
        admins_col.insert_one({"user_id": uid})
        await message.reply(f"`{uid}` added as admin.", parse_mode="markdown")
    except:
        await message.reply("Invalid ID.")

@app.on_message(filters.command("removeadmin") & filters.private)
async def removeadmin(client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("You are not authorized.")
    if len(message.command) < 2:
        return await message.reply("Usage: /removeadmin <user_id>")
    try:
        uid = int(message.command[1])
        res = admins_col.delete_one({"user_id": uid})
        if res.deleted_count == 0:
            return await message.reply("User not found.")
        await message.reply(f"`{uid}` removed from admin list.", parse_mode="markdown")
    except:
        await message.reply("Invalid ID.")

@app.on_message(filters.command("adminslist"))
async def adminslist(client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("You are not authorized.")
    admins = admins_col.find()
    text = "**› Admins List:**\n\n"
    for a in admins:
        text += f"- `{a['user_id']}`\n"
    await message.reply(text, parse_mode="markdown")

@app.on_message(filters.command("addrss"))
async def addrss(client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("You are not authorized.")
    if len(message.command) < 2:
        return await message.reply("Usage: /addrss <rss_url>")
    url = message.command[1]
    if rss_col.find_one({"url": url}):
        return await message.reply("RSS already exists.")
    rss_col.insert_one({"url": url})
    await message.reply(f"Added RSS:\n`{url}`", parse_mode="markdown")

@app.on_message(filters.command("removerss"))
async def removerss(client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("You are not authorized.")
    if len(message.command) < 2:
        return await message.reply("Usage: /removerss <rss_url>")
    url = message.command[1]
    res = rss_col.delete_one({"url": url})
    if res.deleted_count == 0:
        return await message.reply("RSS not found.")
    await message.reply(f"Removed RSS:\n`{url}`", parse_mode="markdown")

@app.on_message(filters.command("listrss"))
async def listrss(client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("You are not authorized.")
    feeds = rss_col.find()
    text = "**› RSS Feeds:**\n\n"
    for feed in feeds:
        text += f"- `{feed['url']}`\n"
    await message.reply(text, parse_mode="markdown")

@app.on_message(filters.command("news"))
async def post_news_command(client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("You are not authorized.")
    await fetch_and_post_news()

async def fetch_and_post_news():
    feeds = rss_col.find()
    for feed in feeds:
        url = feed['url']
        parsed = feedparser.parse(url)
        if not parsed.entries:
            continue
        entry = parsed.entries[0]
        link = entry.link
        if posted_col.find_one({"link": link}):
            continue
        title = clean_md(entry.title)
        summary = clean_md(entry.get("summary", ""))
        img_url = ""
        if 'media_content' in entry:
            img_url = entry.media_content[0]['url']
        elif 'links' in entry:
            for link_obj in entry.links:
                if link_obj.type.startswith("image"):
                    img_url = link_obj.href
                    break
        text = f"**› {title}**\n\n> {summary[:500]}...\n\n[Read More]({entry.link})"
        for channel in channels_col.find():
            try:
                await app.send_photo(
                    chat_id=channel['chat_id'],
                    photo=img_url or config.START_PIC,
                    caption=text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Read Full Article", url=entry.link)]
                    ]),
                    parse_mode="markdown"
                )
            except Exception as e:
                print(f"Failed to post to {channel['chat_id']}: {e}")
        posted_col.insert_one({"link": link, "time": time.time()})

# Auto post news every 10 minutes
scheduler.add_job(fetch_and_post_news, "interval", minutes=10)

app.run()
