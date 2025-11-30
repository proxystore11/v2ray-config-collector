import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

CDN_BASE = os.getenv(
    "CDN_BASE",
    "https://cdn.jsdelivr.net/gh/proxystore11/v2ray-config-collector/output/subscriptions/"
)

SUB_LINKS = {
    "hiddify": CDN_BASE + "prx11-hiddify.txt",
    "insta": CDN_BASE + "prx11-insta-youto.txt",
    "vmess": CDN_BASE + "prx11-vmess.txt",
    "vless": CDN_BASE + "prx11-vless.txt",
    "ss": CDN_BASE + "prx11-ss.txt",
    "trojan": CDN_BASE + "prx11-trojan.txt",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "سلام 👋\n"
        "من ربات PRX11 هستم.\n\n"
        "دستورات:\n"
        "/hiddify - اشتراک Hiddify (100)\n"
        "/insta - اشتراک Instagram / YouTube\n"
        "/vmess - لینک VMESS\n"
        "/vless - لینک VLESS\n"
        "/ss - لینک Shadowsocks\n"
        "/trojan - لینک TROJAN\n"
        "/links - لیست کامل لینک‌ها\n"
    )
    await update.message.reply_text(text)


async def send_link(update: Update, key: str) -> None:
    url = SUB_LINKS.get(key)
    if not url:
        await update.message.reply_text("لینک یافت نشد.")
        return
    await update.message.reply_text(url)


async def hiddify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_link(update, "hiddify")


async def insta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_link(update, "insta")


async def vmess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_link(update, "vmess")


async def vless(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_link(update, "vless")


async def ss(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_link(update, "ss")


async def trojan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_link(update, "trojan")


async def links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "لینک‌های PRX11:\n\n" + "\n".join(
        [f"{k}: {v}" for k, v in SUB_LINKS.items()]
    )
    await update.message.reply_text(text)


async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN env is not set")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hiddify", hiddify))
    app.add_handler(CommandHandler("insta", insta))
    app.add_handler(CommandHandler("vmess", vmess))
    app.add_handler(CommandHandler("vless", vless))
    app.add_handler(CommandHandler("ss", ss))
    app.add_handler(CommandHandler("trojan", trojan))
    app.add_handler(CommandHandler("links", links))

    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
