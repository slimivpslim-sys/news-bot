import os
import asyncio
import feedparser
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Ваш числовой ID из @userinfobot (чтобы бот был доступен ТОЛЬКО вам)
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# RSS-ленты топ-изданий США и Европы
RSS_FEEDS = {
    "New York Times": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "The Guardian": "https://www.theguardian.com/world/rss",
    "BBC News": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Financial Times": "https://www.ft.com/rss/home/international",
    "Le Monde": "https://www.lemonde.fr/rss/une.xml"
}

async def fetch_latest_news():
    """Сбор и формирование новостной выжимки"""
    fresh_articles = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]: # По 2 статьи от каждого издания
                title = entry.get('title', 'Без заголовка')
                link = entry.get('link', '#')
                summary = entry.get('summary', entry.get('description', 'Нет описания'))
                
                image_url = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600"
                if 'media_content' in entry and entry.media_content:
                    image_url = entry.media_content[0].get('url', image_url)
                elif 'enclosures' in entry and entry.enclosures:
                    image_url = entry.enclosures[0].get('href', image_url)

                fresh_articles.append({
                    "source": source,
                    "title": title,
                    "link": link,
                    "summary": summary[:250] + "...",
                    "image": image_url
                })
        except Exception:
            continue
    return fresh_articles

async def news_scheduler():
    """Фоновый цикл: отправка сводки каждые 2 часа (7200 секунд)"""
    await asyncio.sleep(10) # Ожидание старта бота
    while True:
        if ADMIN_ID != 0:
            try:
                articles = await fetch_latest_news()
                if articles:
                    await bot.send_message(
                        chat_id=ADMIN_ID,
                        text="⏰ <b>Автоматическая сводка новостей (каждые 2 часа):</b>",
                        parse_mode="HTML"
                    )
                    # Шлем топ-4 статьи из свежих
                    for art in articles[:4]:
                        text = (
                            f"📰 <b>[{art['source']}]</b>\n"
                            f"<b>{art['title']}</b>\n\n"
                            f"📝 {art['summary']}\n\n"
                            f"🔗 <a href='{art['link']}'>Читать оригинал</a>"
                        )
                        try:
                            await bot.send_photo(chat_id=ADMIN_ID, photo=art['image'], caption=text, parse_mode="HTML")
                        except Exception:
                            await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="HTML")
                        await asyncio.sleep(1)
            except Exception as e:
                print(f"Ошибка рассылки: {e}")
        
        # Ждем 2 часа (2 часа * 60 минут * 60 секунд = 7200 секунд)
        await asyncio.sleep(7200)

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Этот бот является личным новостным ассистентом.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📰 Получить сводку прямо сейчас", callback_data="get_news")
    ]])
    await message.answer(
        "👋 Привет! Твой личный новостной бот активен.\n"
        "Я автоматически присылаю свежие выжимки из западных СМИ каждые 2 часа.",
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data == "get_news")
async def manual_news(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    
    await callback.message.answer("🔍 Собираю свежие публикации...")
    articles = await fetch_latest_news()
    for art in articles[:5]:
        text = (
            f"📰 <b>[{art['source']}]</b>\n"
            f"<b>{art['title']}</b>\n\n"
            f"📝 {art['summary']}\n\n"
            f"🔗 <a href='{art['link']}'>Читать оригинал</a>"
        )
        try:
            await bot.send_photo(chat_id=callback.from_user.id, photo=art['image'], caption=text, parse_mode="HTML")
        except Exception:
            await bot.send_message(chat_id=callback.from_user.id, text=text, parse_mode="HTML")
        await asyncio.sleep(0.5)

async def main():
    # Запускаем фоновую задачу рассылки и саму работу бота одновременно
    asyncio.create_task(news_scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.main() if hasattr(asyncio, 'main') else asyncio.run(main())
