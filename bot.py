import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

# ----------------- الإعدادات الأساسية -----------------
# ضع التوكن الخاص بك والآيدي هنا
TOKEN = os.getenv("BOT_TOKEN", "8727422134:AAGHpvx-B2iqIRRswcX8e8xEPMLYb5vNDxc")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8176761013"))

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- سيرفر وهمي لإبقاء الاستضافة السحابية متصلة 24/7 ---
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Revix Pro Bot Running 24/7!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ----------------- قاعدة البيانات -----------------
def get_db():
    conn = sqlite3.connect("store_data.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        # المستخدمين
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0.0,
            currency TEXT DEFAULT 'USD',
            is_banned INTEGER DEFAULT 0
        )''')
        # الأقسام
        c.execute('''CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )''')
        # المنتجات
        c.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            input_hint TEXT DEFAULT 'معرف اللاعب (ID)'
        )''')
        # طرق الدفع
        c.execute('''CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            details TEXT NOT NULL
        )''')
        # الطلبات
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT, -- deposit أو charge
            item_name TEXT,
            target_id TEXT,
            amount REAL,
            status TEXT DEFAULT 'pending' -- pending, completed, failed
        )''')
        # الإعدادات وأسعار الصرف
        c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
        c.execute("INSERT OR IGNORE INTO settings VALUES ('support_url', 'https://t.me/telegram')")
        c.execute("INSERT OR IGNORE INTO settings VALUES ('news_url', 'https://t.me/telegram')")
        c.execute("INSERT OR IGNORE INTO settings VALUES ('rate_USD', '1.0')")
        c.execute("INSERT OR IGNORE INTO settings VALUES ('rate_SYP', '15000.0')")
        c.execute("INSERT OR IGNORE INTO settings VALUES ('rate_SAR', '3.75')")
        conn.commit()

init_db()

def get_user(user_id, username=""):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        u = c.fetchone()
        if not u:
            c.execute("INSERT INTO users (user_id, username, balance, currency) VALUES (?, ?, 0.0, 'USD')", (user_id, username))
            conn.commit()
            c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            u = c.fetchone()
        return u

def get_setting(key, default=""):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = ?", (key,))
        res = c.fetchone()
        return res[0] if res else default

def convert_currency(amount_usd, target_currency):
    rate = float(get_setting(f"rate_{target_currency}", 1.0))
    return amount_usd * rate

# ----------------- لوحات المفاتيح (Keyboards) -----------------

def user_main_markup():
    support_url = get_setting('support_url')
    news_url = get_setting('news_url')
    markup = types.InlineKeyboardMarkup(row_width=2)
    b_shop = types.InlineKeyboardButton("🛍 تسوق في متجرنا", callback_data="u_shop")
    b_deposit = types.InlineKeyboardButton("💰 إيداع رصيد", callback_data="u_deposit")
    b_acc = types.InlineKeyboardButton("👤 حسابي الشخصي", callback_data="u_acc")
    b_curr = types.InlineKeyboardButton("🌐 تغيير العملة", callback_data="u_curr")
    b_sup = types.InlineKeyboardButton("🛠 الدعم الفني", url=support_url)
    b_news = types.InlineKeyboardButton("📢 أخبار البوت", url=news_url)
    
    markup.add(b_shop)
    markup.add(b_deposit, b_acc)
    markup.add(b_curr)
    markup.add(b_sup, b_news)
    return markup

def admin_main_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b_ord = types.InlineKeyboardButton("📦 الطلبات", callback_data="a_orders")
    b_fin = types.InlineKeyboardButton("💰 المالية", callback_data="a_finance")
    b_sta = types.InlineKeyboardButton("📊 الإحصائيات", callback_data="a_stats")
    b_usr = types.InlineKeyboardButton("👥 المستخدمون", callback_data="a_users")
    b_prd = types.InlineKeyboardButton("🛍 المنتجات", callback_data="a_products")
    b_com = types.InlineKeyboardButton("📢 التواصل والإشعارات", callback_data="a_broadcast")
    b_set = types.InlineKeyboardButton("⚙️ الإعدادات", callback_data="a_settings")
    b_bck = types.InlineKeyboardButton("🔙 رجوع", callback_data="back_home")
    
    markup.add(b_ord, b_fin)
    markup.add(b_sta, b_usr)
    markup.add(b_prd, b_com)
    markup.add(b_set)
    markup.add(b_bck)
    return markup

def admin_orders_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b_dep = types.InlineKeyboardButton("💳 طلبات الإيداع", callback_data="a_view_dep_orders")
    b_shp = types.InlineKeyboardButton("📦 طلبات الشحن", callback_data="a_view_shp_orders")
    b_fal = types.InlineKeyboardButton("❗️ الطلبات الفاشلة", callback_data="a_view_fail_orders")
    b_src = types.InlineKeyboardButton("🔍 بحث عن طلب", callback_data="a_search_order")
    b_bck = types.InlineKeyboardButton("🔙 رجوع", callback_data="back_admin")
    markup.add(b_dep, b_shp)
    markup.add(b_fal)
    markup.add(b_src)
    markup.add(b_bck)
    return markup

# ----------------- أوامر البدء -----------------

@bot.message_handler(commands=['start'])
def start_handler(message):
    user = get_user(message.from_user.id, message.from_user.username)
    if user['is_banned'] == 1:
        bot.send_message(message.chat.id, "⛔️ حسابك محظور من استخدام البوت.")
        return
    bot.send_message(
        message.chat.id,
        "⚡️ <b>أهلاً بك في بوت الشحن</b> ⚡️",
        reply_markup=user_main_markup()
    )

@bot.message_handler(commands=['admin'])
def admin_handler(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "🛡 <b>لوحة التحكم:</b>", reply_markup=admin_main_markup())
    else:
        bot.reply_to(message, "⛔️ هذا الأمر مخصص للإدارة فقط.")

# ----------------- قسم المستخدم -----------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("u_") or call.data == "back_home")
def user_flow(call):
    uid = call.from_user.id
    user = get_user(uid, call.from_user.username)
    curr = user['currency']

    if call.data == "back_home":
        bot.edit_message_text("⚡️ <b>أهلاً بك في بوت الشحن</b> ⚡️", call.message.chat.id, call.message.message_id, reply_markup=user_main_markup())

    elif call.data == "u_acc":
        bal_curr = convert_currency(user['balance'], curr)
        text = (
            f"👤 <b>حسابي الشخصي</b>\n\n"
            f"🆔 الآيدي: <code>{uid}</code>\n"
            f"💵 الرصيد: <b>{bal_curr:,.2f} {curr}</b> (${user['balance']:.2f})\n"
            f"🌐 العملة المختارة: <b>{curr}</b>"
        )
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_home"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "u_curr":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🇺🇸 USD ($)", callback_data="set_curr_USD"),
            types.InlineKeyboardButton("🇸🇾 SYP (ل.س)", callback_data="set_curr_SYP"),
            types.InlineKeyboardButton("🇸🇦 SAR (ر.س)", callback_data="set_curr_SAR"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_home")
        )
        bot.edit_message_text("🌐 <b>اختر العملة المناسبة لعرض الأسعار:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "u_shop":
        with get_db() as conn:
            cats = conn.cursor().execute("SELECT * FROM categories").fetchall()
        if not cats:
            bot.answer_callback_query(call.id, "المتجر فارغ حالياً.", show_alert=True)
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        for c in cats:
            markup.add(types.InlineKeyboardButton(f"🎁 {c['name']}", callback_data=f"open_cat_{c['id']}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_home"))
        bot.edit_message_text("🛍 <b>اختر القسم المطلوب للتسوق:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "u_deposit":
        with get_db() as conn:
            methods = conn.cursor().execute("SELECT * FROM payment_methods").fetchall()
        if not methods:
            bot.answer_callback_query(call.id, "لا تتوفر وسائل دفع حالياً.", show_alert=True)
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        for m in methods:
            markup.add(types.InlineKeyboardButton(f"💳 {m['title']}", callback_data=f"open_pm_{m['id']}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_home"))
        bot.edit_message_text("💰 <b>اختر وسيلة الإيداع وشحن الرصيد:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

# تغيير العملة
@bot.callback_query_handler(func=lambda call: call.data.startswith("set_curr_"))
def change_curr(call):
    new_curr = call.data.split("_")[2]
    with get_db() as conn:
        conn.cursor().execute("UPDATE users SET currency = ? WHERE user_id = ?", (new_curr, call.from_user.id))
        conn.commit()
    bot.answer_callback_query(call.id, f"✅ تم تغيير العملة إلى {new_curr}")
    start_handler(call.message)

# تصفح أقسام ومنتجات المتجر
@bot.callback_query_handler(func=lambda call: call.data.startswith("open_cat_"))
def show_cat_prods(call):
    cat_id = call.data.split("_")[2]
    user = get_user(call.from_user.id)
    curr = user['currency']

    with get_db() as conn:
        prods = conn.cursor().execute("SELECT * FROM products WHERE category_id = ?", (cat_id,)).fetchall()

    markup = types.InlineKeyboardMarkup(row_width=1)
    for p in prods:
        p_price = convert_currency(p['price'], curr)
        markup.add(types.InlineKeyboardButton(f"{p['name']} ➔ {p_price:,.2f} {curr}", callback_data=f"buy_p_{p['id']}"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="u_shop"))
    bot.edit_message_text("📦 <b>اختر الباقة للشحن المباشر:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

# الشراء وإدخال الآيدي
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_p_"))
def process_buy_prod(call):
    pid = call.data.split("_")[2]
    user = get_user(call.from_user.id)
    with get_db() as conn:
        p = conn.cursor().execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()

    if user['balance'] < p['price']:
        bot.answer_callback_query(call.id, f"⚠️ رصيدك غير كافٍ! سعر الباقة ${p['price']} ورصيدك ${user['balance']:.2f}", show_alert=True)
        return

    msg = bot.send_message(call.message.chat.id, f"🎯 لتأكيد طلب باقة <b>{p['name']}</b>:\nأرسل الآن <b>{p['input_hint']}</b> الخاص بك في المحادثة:")
    bot.register_next_step_handler(msg, complete_order, p)

def complete_order(message, product):
    uid = message.from_user.id
    target_id = message.text.strip()
    user = get_user(uid)

    if user['balance'] < product['price']:
        bot.reply_to(message, "❌ رصيدك أصبح غير كافٍ، تم إلغاء العملية.")
        return

    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (product['price'], uid))
        c.execute("INSERT INTO orders (user_id, type, item_name, target_id, amount, status) VALUES (?, 'charge', ?, ?, ?, 'pending')",
                  (uid, product['name'], target_id, product['price']))
        order_id = c.lastrowid
        conn.commit()

    bot.send_message(uid, f"✅ <b>تم استلام طلبك بنجاح!</b>\n📦 الطلب: {product['name']}\n🆔 الحساب المستهدف: <code>{target_id}</code>\n🔢 رقم الطلب: <code>#{order_id}</code>\nسيصلك إشعار فور تنفيذه.", reply_markup=user_main_markup())

    # إشعار الأدمن فورياً مع أزرار التحكم
    adm_markup = types.InlineKeyboardMarkup(row_width=2)
    adm_markup.add(
        types.InlineKeyboardButton("✅ تم التنفيذ", callback_data=f"adm_done_ord_{order_id}"),
        types.InlineKeyboardButton("❌ إلغاء وإرجاع الرصيد", callback_data=f"adm_fail_ord_{order_id}")
    )
    bot.send_message(
        ADMIN_ID,
        f"🚨 <b>طلب شحن جديد #{order_id}</b>\n👤 المستخدم: <code>{uid}</code>\n📦 الباقة: <b>{product['name']}</b>\n🎮 الآيدي: <code>{target_id}</code>\n💵 السعر: ${product['price']}",
        reply_markup=adm_markup
    )

# ----------------- نظام الإيداع بالصور والإيصالات -----------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("open_pm_"))
def deposit_method_details(call):
    mid = call.data.split("_")[2]
    with get_db() as conn:
        m = conn.cursor().execute("SELECT * FROM payment_methods WHERE id = ?", (mid,)).fetchone()

    text = (
        f"💳 <b>طريقة الإيداع: {m['title']}</b>\n\n"
        f"📋 <b>بيانات التحويل:</b>\n{m['details']}\n\n"
        f"📌 بعد إتمام التحويل، اضغط الزر أدناه لإرسال الإيصال وتأكيد الإيداع."
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📤 إرسال إشعار الدفع الآن", callback_data=f"dep_send_{mid}"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="u_deposit"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("dep_send_"))
def prompt_receipt(call):
    msg = bot.send_message(call.message.chat.id, "💵 اكتب المبلغ المحول بالدولار ($) أولاً:\n(مثال: <code>5</code> أو <code>10.5</code>)")
    bot.register_next_step_handler(msg, step_get_amount)

def step_get_amount(message):
    try:
        amount = float(message.text.strip())
        msg = bot.send_message(message.chat.id, "📸 ممتاز، الآن <b>أرسل صورة إشعار التحويل (سكرين شوت)</b> هنا:")
        bot.register_next_step_handler(msg, step_get_photo, amount)
    except:
        bot.reply_to(message, "❌ خطأ في كتابة المبلغ، أعد المحاولة من قائمة الإيداع.")

def step_get_photo(message, amount):
    if not message.photo:
        bot.reply_to(message, "❌ يرجى إرسال صورة للإشعار حصراً.")
        return

    photo_id = message.photo[-1].file_id
    uid = message.from_user.id

    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO orders (user_id, type, item_name, target_id, amount, status) VALUES (?, 'deposit', 'طلب إيداع', ?, ?, 'pending')",
                  (uid, "تحويل يدوي", amount))
        dep_id = c.lastrowid
        conn.commit()

    bot.reply_to(message, f"✅ تم إرسال إشعار الدفع للإدارة (طلب رقم #{dep_id}).\nسيتم فحص الإيصال وإضافة الرصيد لحسابك قريباً.")

    # إرسال الصورة للأدمن مع زري الموافقة والرفض
    adm_markup = types.InlineKeyboardMarkup(row_width=2)
    adm_markup.add(
        types.InlineKeyboardButton("✅ قبول وإيداع الرصيد", callback_data=f"acc_dep_{dep_id}"),
        types.InlineKeyboardButton("❌ رفض الإيصال", callback_data=f"rej_dep_{dep_id}")
    )
    bot.send_photo(
        ADMIN_ID,
        photo_id,
        caption=f"💳 <b>طلب إيداع جديد #{dep_id}</b>\n👤 من: <code>{uid}</code>\n💵 المبلغ: <b>${amount}</b>",
        reply_markup=adm_markup
    )

# معالجة قبول أو رفض الإيداع والشحن من قبل الأدمن
@bot.callback_query_handler(func=lambda call: call.data.startswith(("acc_dep_", "rej_dep_", "adm_done_ord_", "adm_fail_ord_")))
def handle_admin_actions(call):
    if call.from_user.id != ADMIN_ID:
        return

    action, _, oid = call.data.rpartition("_")
    oid = int(oid)

    with get_db() as conn:
        c = conn.cursor()
        order = c.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
        if not order or order['status'] != 'pending':
            bot.answer_callback_query(call.id, "تم اتخاذ إجراء مسبق على هذا الطلب!", show_alert=True)
            return

        if "acc_dep" in call.data:
            c.execute("UPDATE orders SET status = 'completed' WHERE id = ?", (oid,))
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (order['amount'], order['user_id']))
            conn.commit()
            bot.send_message(order['user_id'], f"🎉 <b>تم تأكيد إيداعك بنجاح!</b>\nتمت إضافة <b>${order['amount']}</b> إلى رصيدك.")
            bot.edit_message_caption(f"✅ تم قبول الإيداع #{oid} وإضافة ${order['amount']} للمستخدم.", call.message.chat.id, call.message.message_id)

        elif "rej_dep" in call.data:
            c.execute("UPDATE orders SET status = 'failed' WHERE id = ?", (oid,))
            conn.commit()
            bot.send_message(order['user_id'], f"❌ نعتذر، تم رفض طلب الإيداع #{oid}. تواصل مع الدعم الفني لمزيد من التفاصيل.")
            bot.edit_message_caption(f"❌ تم رفض الإيداع #{oid}.", call.message.chat.id, call.message.message_id)

        elif "adm_done_ord" in call.data:
            c.execute("UPDATE orders SET status = 'completed' WHERE id = ?", (oid,))
            conn.commit()
            bot.send_message(order['user_id'], f"✅ <b>تم تنفيذ طلب الشحن بنجاح!</b>\n📦 الطلب: {order['item_name']}\n🎮 الآيدي: <code>{order['target_id']}</code>\nشكراً لتعاملك معنا!")
            bot.edit_message_text(f"✅ تم تأكيد إكمال الطلب #{oid}.", call.message.chat.id, call.message.message_id)

        elif "adm_fail_ord" in call.data:
            c.execute("UPDATE orders SET status = 'failed' WHERE id = ?", (oid,))
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (order['amount'], order['user_id']))
            conn.commit()
            bot.send_message(order['user_id'], f"⚠️ تعذر تنفيذ طلب الشحن #{oid}.\nتمت إعادة المبلغ (${order['amount']}) إلى محفظتك بالكامل.")
            bot.edit_message_text(f"❌ تم إلغاء الطلب #{oid} واسترجاع الرصيد للعميل.", call.message.chat.id, call.message.message_id)

# ----------------- لوحة تحكم الأدمن التفصيلية -----------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("a_") or call.data == "back_admin")
def admin_nav(call):
    if call.from_user.id != ADMIN_ID:
        return

    if call.data == "back_admin":
        bot.edit_message_text("🛡 <b>لوحة التحكم:</b>", call.message.chat.id, call.message.message_id, reply_markup=admin_main_markup())

    elif call.data == "a_orders":
        bot.edit_message_text("📦 <b>قسم الطلبات:</b>\nاختر نوع الطلب:", call.message.chat.id, call.message.message_id, reply_markup=admin_orders_markup())

    elif call.data == "a_stats":
        with get_db() as conn:
            c = conn.cursor()
            u_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            ord_count = c.execute("SELECT COUNT(*) FROM orders WHERE type = 'charge' AND status = 'completed'").fetchone()[0]
            sales = c.execute("SELECT SUM(amount) FROM orders WHERE type = 'charge' AND status = 'completed'").fetchone()[0] or 0.0
            deps = c.execute("SELECT SUM(amount) FROM orders WHERE type = 'deposit' AND status = 'completed'").fetchone()[0] or 0.0

