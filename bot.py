"""
Telegram Reseller Shop Bot — starter template
------------------------------------------------
Connects a Telegram bot to a reseller products API so users can browse
products and (once you wire up the order endpoint) purchase them.

Fill in the CONFIG section below, then run:
    pip install python-telegram-bot requests
    python bot.py
"""

import logging
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ---------------------------------------------------------------------------
# CONFIG — fill these in
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = "PASTE_YOUR_BOTFATHER_TOKEN_HERE"

API_BASE_URL = "https://ventetelegrambotrailway-production.up.railway.app/api"
API_KEY = "PASTE_YOUR_RESELLER_API_KEY_HERE"  # from step 2 in the setup guide

# Confirm this path matches the Swagger docs exactly (case, plural/singular, etc.)
PRODUCTS_ENDPOINT = f"{API_BASE_URL}/reseller/products"

# You'll need to confirm the real path/method for placing an order once you
# check the Swagger "Orders" section — this is a guess based on convention.
ORDER_ENDPOINT = f"{API_BASE_URL}/reseller/orders"

# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def api_headers():
    """Most reseller APIs use one of these two auth styles — keep whichever
    one matches what the Swagger 'Authorize' button expects, delete the other."""
    return {
        "Authorization": f"Bearer {API_KEY}",
        # "X-API-Key": API_KEY,
    }


def fetch_products():
    """Calls the reseller API and returns the product list (or None on error)."""
    try:
        resp = requests.get(PRODUCTS_ENDPOINT, headers=api_headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch products: {e}")
        return None


def place_order(product_id, quantity=1):
    """Places an order for a product and returns the API response
    (which should contain the delivered account/key on success)."""
    payload = {"product_id": product_id, "quantity": quantity}
    try:
        resp = requests.post(
            ORDER_ENDPOINT, json=payload, headers=api_headers(), timeout=20
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"Failed to place order: {e}")
        return None


# ---------------------------------------------------------------------------
# Telegram handlers
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛍️ المنتجات (Products)", callback_data="products")],
    ]
    await update.message.reply_text(
        "أهلاً! اختر خياراً:", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    products = fetch_products()
    if not products:
        await query.edit_message_text("⚠️ تعذر تحميل المنتجات حالياً. حاول لاحقاً.")
        return

    # NOTE: adjust these field names once you see the real JSON shape
    # returned by the API — this assumes a list of dicts with id/name/price.
    items = products if isinstance(products, list) else products.get("data", [])

    keyboard = []
    for item in items:
        name = item.get("name", "Unnamed product")
        price = item.get("price", "?")
        pid = item.get("id")
        label = f"{name} | ${price}"
        keyboard.append(
            [InlineKeyboardButton(label, callback_data=f"buy:{pid}")]
        )

    if not keyboard:
        await query.edit_message_text("لا توجد منتجات متاحة حالياً.")
        return

    await query.edit_message_text(
        "اختر منتجاً:", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = query.data.split(":", 1)[1]
    await query.edit_message_text("⏳ جاري تنفيذ الطلب...")

    result = place_order(product_id)
    if not result:
        await query.edit_message_text("❌ فشل تنفيذ الطلب. حاول مرة أخرى أو تواصل مع الدعم.")
        return

    # Adjust based on what the order endpoint actually returns
    delivered = result.get("account") or result.get("data") or result
    await query.edit_message_text(f"✅ تم الشراء بنجاح!\n\n{delivered}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")


def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_products, pattern="^products$"))
    app.add_handler(CallbackQueryHandler(handle_purchase, pattern="^buy:"))
    app.add_error_handler(error_handler)

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
