import os
import qrcode
import io
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

CDN_BASE = "https://cdn.jsdelivr.net/gh/proxystore11/v2ray-config-collector/output/subscriptions/"

SUB_LINKS = {
    "hiddify": ("🌀 Hiddify (100)", CDN_BASE + "prx11-hiddify.txt"),
    "insta": ("🎬 Instagram/YouTube", CDN_BASE + "prx11-insta-youto.txt"),
    "vmess": ("🔵 VMESS", CDN_BASE + "prx11-vmess.txt"),
    "vless": ("🟩 VLESS", CDN_BASE + "prx11-vless.txt"),
    "ss": ("⚪ Shadowsocks", CDN_BASE + "prx11-ss.txt"),
    "trojan": ("🔺 TROJAN", CDN_BASE + "prx11-trojan.txt"),
}

# --------------- KEYBOARDS ----------------

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(name, callback_data=key)]
        for key, (name, _) in SUB_LINKS.items()
    ] + [
        [InlineKeyboardButton("📦 Send All Links", callback_data="all")],
        [InlineKeyboardButton("📄 دریافت پنل HTML", callback_data="html")]
    ])


# --------------- QR CODE ----------------

def generate_qr(url: str):
    img = qrcode.make(url)
    bio = io.BytesIO()
    bio.name = "qr.png"
    img.save(bio, "PNG")
    bio.seek(0)
    return bio


# --------------- HANDLERS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "سلام 👋\n"
        "به ربات پیشرفته PRX11 خوش آمدید.\n\n"
        "از دکمه‌های زیر استفاده کنید:"
    )
    await update.message.reply_text(text, reply_markup=main_menu())


async def send_link(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    name, url = SUB_LINKS[key]
    qr = generate_qr(url)

    await update.callback_query.answer()
    await update.callback_query.message.reply_photo(
        photo=qr,
        caption=f"{name}\n\n{url}",
        reply_markup=main_menu()
    )


async def send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    msg = "📦 *ALL LINKS*\n\n" + "\n".join(
        [f"{name}: `{url}`" for name, url in SUB_LINKS.values()]
    )

    await update.callback_query.message.reply_text(
        msg, parse_mode="Markdown", reply_markup=main_menu()
    )


async def send_html(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    path = "docs/index.html"
    if not os.path.exists(path):
        await update.callback_query.message.reply_text("فایل HTML پیدا نشد.")
        return

    await update.callback_query.message.reply_document(
        document=InputFile(path),
        caption="پنل HTML PRX11"
    )


# --------------- AUTO-REPLY ----------------

async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.lower()

    for key, (name, url) in SUB_LINKS.items():
        if key in text:
            qr = generate_qr(url)
            await update.message.reply_photo(
                photo=qr,
                caption=f"{name}\n\n{url}",
                reply_markup=main_menu()
            )
            return

    # Default response
    await update.message.reply_text(
        "متوجه نشدم. از /start استفاده کن.",
        reply_markup=main_menu()
    )


# --------------- BUTTON HANDLER ----------------

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if data in SUB_LINKS:
        await send_link(update, context, data)
    elif data == "all":
        await send_all(update, context)
    elif data == "html":
        await send_html(update, context)


# --------------- MAIN ----------------

def main():

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN env is not set")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))

    app.run_polling(stop_signals=None)


if __name__ == "__main__":
    main()
