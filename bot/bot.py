import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام، من ربات PRX11 هستم.\n\n"
        "/hiddify\n"
        "/insta\n"
        "/vmess\n"
        "/vless\n"
        "/ss\n"
        "/trojan\n"
        "/links\n"
    )


async def links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "لیست لینک‌ها:\n\n" + "\n".join(
        [f"{k}: {v}" for k, v in SUB_LINKS.items()]
    )
    await update.message.reply_text(msg)


async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE, key="hiddify"):
    await update.message.reply_text(SUB_LINKS[key])


async def hiddify(update: Update, ctx): await handler(update, ctx, "hiddify")
async def insta(update: Update, ctx): await handler(update, ctx, "insta")
async def vmess(update: Update, ctx): await handler(update, ctx, "vmess")
async def vless(update: Update, ctx): await handler(update, ctx, "vless")
async def ss(update: Update, ctx): await handler(update, ctx, "ss")
async def trojan(update: Update, ctx): await handler(update, ctx, "trojan")


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set!")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("links", links))

    app.add_handler(CommandHandler("hiddify", hiddify))
    app.add_handler(CommandHandler("insta", insta))
    app.add_handler(CommandHandler("vmess", vmess))
    app.add_handler(CommandHandler("vless", vless))
    app.add_handler(CommandHandler("ss", ss))
    app.add_handler(CommandHandler("trojan", trojan))

    # IMPORTANT: Do NOT use asyncio.run()
    app.run_polling(stop_signals=None)


if __name__ == "__main__":
    main()
