import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

# ----------------- الإعدادات الأساسية -----------------
TOKEN = os.getenv("BOT_TOKEN", "8727422134:AAGHpvx-B2iqIRRswcX8e8xEPMLYb5vNDxc")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8176761013"))

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- سيرفر وهمي صغير لإبقاء الاستضافة السحابية متصلة 24/7 ---
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running 24/7 Successfully!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ----------------- إعداد قاعدة البيانات -----------------
def get_db():
    conn = sqlite3.connect("bot_database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            currency TEXT DEFAULT 'USD'
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            api_service_id TEXT DEFAULT '',
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            instructions TEXT NOT NULL
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        cursor.execute("INSERT OR IGNORE INTO settings VALUES ('support_url', 'https://t.me/telegram')")
        cursor.execute("INSERT OR IGNORE INTO settings VALUES ('news_url', 'https://t.me/telegram')")
        conn.commit()

init_db()

def get_user(user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.execute("INSERT INTO users (user_id, balance, currency) VALUES (?, 0.0, 'USD')", (user_id,))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
        return user

# ----------------- لوحات المفاتيح -----------------

def main_menu():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'support_url'")
        support_url = cursor.fetchone()[0]
        cursor.execute("SELECT value FROM settings WHERE key = 'news_url'")
        news_url = cursor.fetchone()[0]

    markup = types.InlineKeyboardMarkup(row_width=2)
    b_shop = types.InlineKeyboardButton("🛍 تسوق في متجرنا", callback_data="user_shop")
    b_deposit = types.InlineKeyboardButton("💰 إيداع رصيد", callback_data="user_deposit")
    b_account = types.InlineKeyboardButton("👤 حسابي الشخصي", callback_data="user_account")
    b_currency = types.InlineKeyboardButton("🌐 تغيير العملة", callback_data="user_currency")
    b_support = types.InlineKeyboardButton("🛠 الدعم الفني", url=support_url)
    b_news = types.InlineKeyboardButton("📢 أخبار البوت", url=news_url)

    markup.add(b_shop)
    markup.add(b_deposit, b_account)
    markup.add(b_currency)
    markup.add(b_support, b_news)
    return markup

def admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b_orders = types.InlineKeyboardButton("📦 الطلبات", callback_data="admin_orders")
    b_finance = types.InlineKeyboardButton("💰 إدارة الأرصدة", callback_data="admin_finance")
    b_products = types.InlineKeyboardButton("🛍 إدارة الأقسام والمنتجات", callback_data="admin_manage_shop")
    b_methods = types.InlineKeyboardButton("💳 طرق الإيداع", callback_data="admin_manage_methods")
    b_links = types.InlineKeyboardButton("🔗 تعديل الروابط", callback_data="admin_manage_links")
    b_broadcast = types.InlineKeyboardButton("📢 إذاعة للمستخدمين", callback_data="admin_broadcast")
    b_back = types.InlineKeyboardButton("🔙 رجوع للواجهة", callback_data="back_to_main")

    markup.add(b_orders, b_finance)
    markup.add(b_products)
    markup.add(b_methods, b_links)
    markup.add(b_broadcast)
    markup.add(b_back)
    return markup

# ----------------- أوامر تلغرام -----------------

@bot.message_handler(commands=['start'])
def start_cmd(message):
    get_user(message.from_user.id)
    bot.send_message(
        message.chat.id,
        "⚡️ <b>أهلاً بك في بوت الشحن المتكامل</b> ⚡️\nاختر الخدمة المطلوبة من القائمة أدناه:",
        reply_markup=main_menu()
    )

@bot.message_handler(commands=['admin'])
def admin_cmd(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(
            message.chat.id,
            "🛡 <b>لوحة تحكم الإدارة الشاملة:</b>\nيمكنك التحكم بالأقسام، المنتجات، والأسعار دون الحاجة لتعديل الكود.",
            reply_markup=admin_panel()
        )
    else:
        bot.reply_to(message, "⛔️ هذا الأمر مخصص لمالك البوت فقط.")

# ----------------- معالجة أزرار المستخدم -----------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("user_") or call.data in ["back_to_main"])
def user_callbacks(call):
    user_id = call.from_user.id

    if call.data == "back_to_main":
        bot.edit_message_text(
            "⚡️ <b>أهلاً بك في بوت الشحن المتكامل</b> ⚡️",
            call.message.chat.id, call.message.message_id,
            reply_markup=main_menu()
        )

    elif call.data == "user_account":
        user = get_user(user_id)
        text = (
            f"👤 <b>معلومات الحساب:</b>\n\n"
            f"🆔 الآيدي: <code>{user['user_id']}</code>\n"
            f"💵 الرصيد الحالي: <b>{user['balance']:.2f}$</b>\n"
            f"🌐 العملة: <b>{user['currency']}</b>"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "user_shop":
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories")
            categories = cursor.fetchall()

        if not categories:
            bot.answer_callback_query(call.id, "المتجر فارغ حالياً، قم بإضافة أقسام من لوحة الأدمن.", show_alert=True)
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        for cat in categories:
            markup.add(types.InlineKeyboardButton(f"📁 {cat['name']}", callback_data=f"cat_{cat['id']}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        bot.edit_message_text("🛍 <b>اختر القسم المطلوب للتسوق:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "user_deposit":
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM payment_methods")
            methods = cursor.fetchall()

        if not methods:
            bot.answer_callback_query(call.id, "لم تتم إضافة طرق شحن بعد. أضفها من لوحة الأدمن.", show_alert=True)
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        for m in methods:
            markup.add(types.InlineKeyboardButton(f"💳 {m['title']}", callback_data=f"pay_{m['id']}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        bot.edit_message_text("💰 <b>اختر وسيلة الإيداع والشحن:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def view_category_products(call):
    cat_id = call.data.split("_")[1]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE category_id = ?", (cat_id,))
        products = cursor.fetchall()

    markup = types.InlineKeyboardMarkup(row_width=1)
    if products:
        for p in products:
            markup.add(types.InlineKeyboardButton(f"{p['name']} | {p['price']}$", callback_data=f"buy_{p['id']}"))
    else:
        markup.add(types.InlineKeyboardButton("لا توجد باقات متوفرة هنا", callback_data="none"))

    markup.add(types.InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="user_shop"))
    bot.edit_message_text("📦 <b>اختر الباقة للشراء:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def show_payment_info(call):
    method_id = call.data.split("_")[1]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payment_methods WHERE id = ?", (method_id,))
        method = cursor.fetchone()

    text = (
        f"💳 <b>طريقة الإيداع: {method['title']}</b>\n\n"
        f"📋 <b>التعليمات:</b>\n{method['instructions']}\n\n"
        f"⚠️ بعد التحويل، يرجى إرسال الإشعار أو رقم المعاملة للدعم لتفعيل الرصيد."
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 رجوع لطرق الدفع", callback_data="user_deposit"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

# ----------------- أوامر لوحة الأدمن -----------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_") or call.data in ["back_to_admin"])
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID:
        return

    if call.data == "back_to_admin":
        bot.edit_message_text("🛡 <b>لوحة تحكم الإدارة الشاملة:</b>", call.message.chat.id, call.message.message_id, reply_markup=admin_panel())

    elif call.data == "admin_manage_shop":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ إضافة قسم جديد (زر)", callback_data="adm_add_cat"),
            types.InlineKeyboardButton("➕ إضافة باقة / منتج داخل قسم", callback_data="adm_add_prod"),
            types.InlineKeyboardButton("🔙 رجوع للوحة التحكم", callback_data="back_to_admin")
        )
        bot.edit_message_text("🛍 <b>إدارة الأقسام والمنتجات:</b>\nاختر العملية المطلوبة:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "admin_manage_methods":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ إضافة طريقة إيداع", callback_data="adm_add_method"),
            types.InlineKeyboardButton("🔙 رجوع للوحة التحكم", callback_data="back_to_admin")
        )
        bot.edit_message_text("💳 <b>إدارة طرق الإيداع:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "admin_manage_links":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✏️ تعديل رابط الدعم الفني", callback_data="adm_edit_support"),
            types.InlineKeyboardButton("✏️ تعديل رابط قناة الأخبار", callback_data="adm_edit_news"),
            types.InlineKeyboardButton("🔙 رجوع للوحة التحكم", callback_data="back_to_admin")
        )
        bot.edit_message_text("🔗 <b>تعديل الروابط الخارجية للبوت:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "admin_finance":
        msg = bot.send_message(call.message.chat.id, "أرسل آيدي المستخدم والمبلغ لإضافته بالشكل التالي:\n<code>ID AMOUNT</code>\nمثال:\n<code>123456789 10</code>")
        bot.register_next_step_handler(msg, process_add_balance)

@bot.callback_query_handler(func=lambda call: call.data == "adm_add_cat")
def adm_add_cat_prompt(call):
    msg = bot.send_message(call.message.chat.id, "أرسل اسم القسم الجديد (مثلاً: <b>ببجي موبايل</b>):")
    bot.register_next_step_handler(msg, save_category)

def save_category(message):
    cat_name = message.text.strip()
    with get_db() as conn:
        conn.cursor().execute("INSERT INTO categories (name) VALUES (?)", (cat_name,))
        conn.commit()
    bot.reply_to(message, f"✅ تم إنشاء القسم: <b>{cat_name}</b> بنجاح.", reply_markup=admin_panel())

@bot.callback_query_handler(func=lambda call: call.data == "adm_add_prod")
def adm_add_prod_prompt(call):
    with get_db() as conn:
        categories = conn.cursor().execute("SELECT * FROM categories").fetchall()
    
    if not categories:
        bot.send_message(call.message.chat.id, "⚠️ يجب إضافة قسم أولاً.")
        return

    text = "اختر رقم القسم لإضافة المنتج إليه:\n\n"
    for c in categories:
        text += f"ID: <code>{c['id']}</code> ➔ <b>{c['name']}</b>\n"
    text += "\nأرسل بالشكل:\n<code>ID_القسم | اسم المنتج | السعر</code>\nمثال:\n<code>1 | 60 شدة | 0.99</code>"
    
    msg = bot.send_message(call.message.chat.id, text)
    bot.register_next_step_handler(msg, save_product)

def save_product(message):
    try:
        cat_id, name, price = [x.strip() for x in message.text.split("|")]
        with get_db() as conn:
            conn.cursor().execute("INSERT INTO products (category_id, name, price) VALUES (?, ?, ?)", (int(cat_id), name, float(price)))
            conn.commit()
        bot.reply_to(message, f"✅ تم إضافة المنتج: <b>{name}</b> بسعر <b>{price}$</b>", reply_markup=admin_panel())
    except Exception:
        bot.reply_to(message, "❌ خطأ في الصيغة. يرجى إرسالها مفصولة برمز |.")

@bot.callback_query_handler(func=lambda call: call.data == "adm_add_method")
def adm_add_method_prompt(call):
    msg = bot.send_message(call.message.chat.id, "أرسل اسم طريقة الدفع والتعليمات مفصولة برمز |\nمثال:\n<code>سيريتل كاش | حول للرقم 09xxxxxxxx ثم ارسل الإشعار</code>")
    bot.register_next_step_handler(msg, save_payment_method)

def save_payment_method(message):
    try:
        title, instructions = [x.strip() for x in message.text.split("|")]
        with get_db() as conn:
            conn.cursor().execute("INSERT INTO payment_methods (title, instructions) VALUES (?, ?)", (title, instructions))
            conn.commit()
        bot.reply_to(message, f"✅ تمت إضافة طريقة الدفع: <b>{title}</b>", reply_markup=admin_panel())
    except Exception:
        bot.reply_to(message, "❌ خطأ في الصيغة! الرجاء وضع الرمز | بين العنوان والتعليمات.")

@bot.callback_query_handler(func=lambda call: call.data in ["adm_edit_support", "adm_edit_news"])
def edit_link_prompt(call):
    link_type = "support_url" if call.data == "adm_edit_support" else "news_url"
    msg = bot.send_message(call.message.chat.id, "أرسل الرابط الجديد كاملاً (يبدأ بـ https://):")
    bot.register_next_step_handler(msg, lambda m: save_link(m, link_type))

def save_link(message, link_type):
    url = message.text.strip()
    with get_db() as conn:
        conn.cursor().execute("UPDATE settings SET value = ? WHERE key = ?", (url, link_type))
        conn.commit()
    bot.reply_to(message, "✅ تم تحديث الرابط بنجاح!", reply_markup=admin_panel())

def process_add_balance(message):
    try:
        user_id, amount = message.text.strip().split()
        user_id = int(user_id)
        amount = float(amount)
        with get_db() as conn:
            conn.cursor().execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            conn.commit()
        bot.reply_to(message, f"✅ تم إضافة <b>{amount}$</b> لحساب المستخدم <code>{user_id}</code>.")
        bot.send_message(user_id, f"🎉 تم إيداع <b>{amount}$</b> في محفظتك بنجاح!")
    except Exception:
        bot.reply_to(message, "❌ فشل التحديث. أرسل الآيدي ثم مسافة ثم المبلغ.")

# ----------------- تشغيل البوت -----------------
if __name__ == "__main__":
    bot.infinity_polling()
        
