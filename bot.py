import os
import telebot
from telebot import types

# استبدل هذه القيم ببياناتك المستخرجة مسبقاً
TOKEN = os.getenv("BOT_TOKEN", "ضع_توكن_بوتك_هنا")
ADMIN_ID = int(os.getenv("ADMIN_ID", "ضع_ايدي_حسابك_هنا"))

bot = telebot.TeleBot(TOKEN)

# قائمة المستخدم الرئيسية
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b_shop = types.InlineKeyboardButton("🛍 تسوق في متجرنا", callback_data="user_shop")
    b_deposit = types.InlineKeyboardButton("💰 إيداع رصيد", callback_data="user_deposit")
    b_account = types.InlineKeyboardButton("👤 حسابي الشخصي", callback_data="user_account")
    b_currency = types.InlineKeyboardButton("🌐 تغيير العملة", callback_data="user_currency")
    b_support = types.InlineKeyboardButton("🛠 الدعم الفني", url="https://t.me/telegram")
    b_news = types.InlineKeyboardButton("📢 أخبار البوت", url="https://t.me/telegram")
    
    markup.add(b_shop)
    markup.add(b_deposit, b_account)
    markup.add(b_currency)
    markup.add(b_support, b_news)
    return markup

# لوحة تحكم الأدمن
def admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b_orders = types.InlineKeyboardButton("📦 الطلبات", callback_data="admin_orders")
    b_finance = types.InlineKeyboardButton("💰 المالية", callback_data="admin_finance")
    b_stats = types.InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")
    b_users = types.InlineKeyboardButton("👥 المستخدمون", callback_data="admin_users")
    b_broadcast = types.InlineKeyboardButton("📢 التواصل والإشعارات", callback_data="admin_broadcast")
    b_products = types.InlineKeyboardButton("🛍 المنتجات", callback_data="admin_products")
    b_settings = types.InlineKeyboardButton("⚙️ الإعدادات", callback_data="admin_settings")
    b_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
    
    markup.add(b_orders, b_finance)
    markup.add(b_stats, b_users)
    markup.add(b_broadcast, b_products)
    markup.add(b_settings)
    markup.add(b_back)
    return markup

# قسم الطلبات داخل لوحة الأدمن
def admin_orders_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b_dep_orders = types.InlineKeyboardButton("💳 طلبات الإيداع", callback_data="admin_dep_orders")
    b_ship_orders = types.InlineKeyboardButton("📦 طلبات الشحن", callback_data="admin_ship_orders")
    b_failed = types.InlineKeyboardButton("❗️ الطلبات الفاشلة", callback_data="admin_failed_orders")
    b_search = types.InlineKeyboardButton("🔍 بحث عن طلب", callback_data="admin_search_order")
    b_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")
    
    markup.add(b_dep_orders, b_ship_orders)
    markup.add(b_failed)
    markup.add(b_search)
    markup.add(b_back)
    return markup

# تشغيل أمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "⚡️ **أهلاً بك في بوت الشحن** ⚡️",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# تشغيل أمر /admin
@bot.message_handler(commands=['admin'])
def handle_admin(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(
            message.chat.id,
            "🛡 **لوحة التحكم:**",
            reply_markup=admin_panel(),
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(message, "⛔️ عذراً، هذا الأمر مخصص لمدير البوت فقط.")

# التفاعل مع الأزرار
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "admin_orders":
        bot.edit_message_text("📦 **قسم الطلبات**\n\nاختر نوع الطلب:", call.message.chat.id, call.message.message_id, reply_markup=admin_orders_menu(), parse_mode="Markdown")
    elif call.data == "back_to_admin":
        bot.edit_message_text("🛡 **لوحة التحكم:**", call.message.chat.id, call.message.message_id, reply_markup=admin_panel(), parse_mode="Markdown")
    elif call.data == "back_to_main":
        bot.edit_message_text("⚡️ **أهلاً بك في بوت الشحن** ⚡️", call.message.chat.id, call.message.message_id, reply_markup=main_menu(), parse_mode="Markdown")
    elif call.data == "user_account":
        bot.answer_callback_query(call.id, f"معرف حسابك: {call.from_user.id}\nرصيدك: 0.00$", show_alert=True)
    elif call.data == "user_deposit":
        bot.answer_callback_query(call.id, "قسم الإيداع قيد التجهيز", show_alert=False)
    elif call.data == "user_shop":
        bot.answer_callback_query(call.id, "جاري تحميل قائمة المنتجات...", show_alert=False)

if __name__ == "__main__":
    bot.infinity_polling()
  
