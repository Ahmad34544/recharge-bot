import os
import sqlite3
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

# ----------------- الإعدادات الأساسية -----------------
TOKEN = "8727422134:AAGHpvx-B2iqIRRswcX8e8xEPMLYb5vNDxc"
ADMIN_ID = 8176761013

bot = telebot.TeleBot(TOKEN, parse_mode="HTML", threaded=True)

# --- سيرفر HTTP مدمج لإبقاء الاستضافة حية ---
class FastHealthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Bot Engine is Active & Running Super Fast!")
    def log_message(self, format, *args):
        return  # تعطيل سجلات HTTP لتوفير السرعة

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), FastHealthServer)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

# ----------------- إعداد قاعدة بيانات سريعة (WAL Mode) -----------------
def get_db():
    conn = sqlite3.connect("store_v3.db", timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")  # يمنع البطء والتشنج نهائياً
    return conn

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0.0,
            currency TEXT DEFAULT 'USD',
            is_banned INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS api_providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            api_url TEXT NOT NULL,
            api_key TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            input_hint TEXT DEFAULT 'معرف اللاعب (ID)',
            api_provider_id INTEGER DEFAULT 0,
            api_service_id TEXT DEFAULT '',
            is_auto INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            details TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            item_name TEXT,
            target_id TEXT,
            amount REAL,
            status TEXT DEFAULT 'pending',
            api_order_id TEXT DEFAULT ''
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
        c.execute("INSERT OR IGNORE INTO settings VALUES ('support_url', 'https://t.me/telegram')")
        c.execute("INSERT OR IGNORE INTO settings VALUES ('news_url', 'https://t.me/telegram')")
        c.execute("INSERT OR IGNORE INTO settings VALUES ('rate_USD', '1.0')")
        c.execute("INSERT OR IGNORE INTO settings VALUES ('rate_SYP', '15000.0')")
        c.execute("INSERT OR IGNORE INTO settings VALUES ('rate_SAR', '3.75')")
        conn.commit()

init_db()

# --- وظائف مساعدة فائقة السرعة ---
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

# ----------------- لوحات المفاتيح السريعة -----------------

def user_main_markup():
    support_url = get_setting('support_url')
    news_url = get_setting('news_url')
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("🛍 تسوق في متجرنا", callback_data="u_shop"))
    m.add(
        types.InlineKeyboardButton("💰 إيداع رصيد", callback_data="u_deposit"),
        types.InlineKeyboardButton("👤 حسابي الشخصي", callback_data="u_acc")
    )
    m.add(types.InlineKeyboardButton("🌐 تغيير العملة", callback_data="u_curr"))
    m.add(
        types.InlineKeyboardButton("🛠 الدعم الفني", url=support_url),
        types.InlineKeyboardButton("📢 أخبار البوت", url=news_url)
    )
    return m

def admin_main_markup():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("📦 الطلبات", callback_data="a_orders"),
        types.InlineKeyboardButton("💰 المالية والأرصدة", callback_data="a_finance")
    )
    m.add(
        types.InlineKeyboardButton("📊 الإحصائيات", callback_data="a_stats"),
        types.InlineKeyboardButton("👥 المستخدمون", callback_data="a_users")
    )
    m.add(
        types.InlineKeyboardButton("🛍 إدارة المنتجات", callback_data="a_prods"),
        types.InlineKeyboardButton("🔌 ربط سيرفر API", callback_data="a_api")
    )
    m.add(types.InlineKeyboardButton("⚙️ الإعدادات والأسعار", callback_data="a_settings"))
    m.add(types.InlineKeyboardButton("🔙 إغلاق اللوحة", callback_data="back_home"))
    return m

# ----------------- أوامر التشغيل -----------------

@bot.message_handler(commands=['start'])
def start_cmd(message):
    get_user(message.from_user.id, message.from_user.username)
    bot.send_message(
        message.chat.id,
        "⚡️ <b>أهلاً بك في بوت الشحن</b> ⚡️\nاختر الخدمة المطلوبة من القائمة أدناه:",
        reply_markup=user_main_markup()
    )

@bot.message_handler(commands=['admin'])
def admin_cmd(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "🛡 <b>لوحة تحكم المدير:</b>", reply_markup=admin_main_markup())
    else:
        bot.reply_to(message, "⛔️ هذا الأمر مخصص لمدير البوت فقط.")

# ----------------- أحداث المستخدم الفورية -----------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("u_") or call.data == "back_home")
def user_click_handler(call):
    # الرد الفوري لإزالة علامة التحميل المزعجة
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    user = get_user(uid, call.from_user.username)
    curr = user['currency']

    if call.data == "back_home":
        bot.edit_message_text("⚡️ <b>أهلاً بك في بوت الشحن</b> ⚡️", call.message.chat.id, call.message.message_id, reply_markup=user_main_markup())

    elif call.data == "u_acc":
        bal_curr = convert_currency(user['balance'], curr)
        text = (
            f"👤 <b>بيانات الحساب:</b>\n\n"
            f"🆔 الآيدي: <code>{uid}</code>\n"
            f"💵 الرصيد: <b>{bal_curr:,.2f} {curr}</b> (${user['balance']:.2f})\n"
            f"🌐 العملة الحالية: <b>{curr}</b>"
        )
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_home"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "u_curr":
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(
            types.InlineKeyboardButton("🇺🇸 USD ($)", callback_data="set_c_USD"),
            types.InlineKeyboardButton("🇸🇾 SYP (ل.س)", callback_data="set_c_SYP"),
            types.InlineKeyboardButton("🇸🇦 SAR (ر.س)", callback_data="set_c_SAR"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_home")
        )
        bot.edit_message_text("🌐 <b>اختر العملة المفضلة لعرض الأسعار:</b>", call.message.chat.id, call.message.message_id, reply_markup=m)

    elif call.data == "u_shop":
        with get_db() as conn:
            cats = conn.cursor().execute("SELECT * FROM categories").fetchall()
        if not cats:
            bot.send_message(call.message.chat.id, "المتجر قيد التحديث حالياً، تفضل بزيارتنا لاحقاً.")
            return
        m = types.InlineKeyboardMarkup(row_width=1)
        for c in cats:
            m.add(types.InlineKeyboardButton(f"🎁 {c['name']}", callback_data=f"open_cat_{c['id']}"))
        m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_home"))
        bot.edit_message_text("🛍 <b>اختر القسم المطلوب:</b>", call.message.chat.id, call.message.message_id, reply_markup=m)

    elif call.data == "u_deposit":
        with get_db() as conn:
            methods = conn.cursor().execute("SELECT * FROM payment_methods").fetchall()
        if not methods:
            bot.send_message(call.message.chat.id, "طرق الإيداع قيد الصيانة حالياً.")
            return
        m = types.InlineKeyboardMarkup(row_width=1)
        for pm in methods:
            m.add(types.InlineKeyboardButton(f"💳 {pm['title']}", callback_data=f"open_pm_{pm['id']}"))
        m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_home"))
        bot.edit_message_text("💰 <b>اختر وسيلة شحن الرصيد:</b>", call.message.chat.id, call.message.message_id, reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_c_"))
def change_user_currency(call):
    bot.answer_callback_query(call.id, "✅ تم تغيير العملة بنجاح!")
    new_c = call.data.split("_")[2]
    with get_db() as conn:
        conn.cursor().execute("UPDATE users SET currency = ? WHERE user_id = ?", (new_c, call.from_user.id))
        conn.commit()
    user_click_handler(call)

# تصفح باقات الأقسام
@bot.callback_query_handler(func=lambda call: call.data.startswith("open_cat_"))
def show_category_packages(call):
    bot.answer_callback_query(call.id)
    cid = call.data.split("_")[2]
    user = get_user(call.from_user.id)
    curr = user['currency']

    with get_db() as conn:
        prods = conn.cursor().execute("SELECT * FROM products WHERE category_id = ?", (cid,)).fetchall()

    m = types.InlineKeyboardMarkup(row_width=1)
    for p in prods:
        p_price = convert_currency(p['price'], curr)
        m.add(types.InlineKeyboardButton(f"{p['name']} ➔ {p_price:,.2f} {curr}", callback_data=f"order_prod_{p['id']}"))
    m.add(types.InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="u_shop"))
    bot.edit_message_text("📦 <b>اختر الباقة المطلوبة:</b>", call.message.chat.id, call.message.message_id, reply_markup=m)

# معالجة طلب الباقة والشحن الفوري عبر الـ API
@bot.callback_query_handler(func=lambda call: call.data.startswith("order_prod_"))
def ask_player_id(call):
    bot.answer_callback_query(call.id)
    pid = call.data.split("_")[2]
    user = get_user(call.from_user.id)

    with get_db() as conn:
        p = conn.cursor().execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()

    if user['balance'] < p['price']:
        bot.send_message(call.message.chat.id, f"⚠️ <b>رصيدك غير كافٍ!</b>\nسعر الباقة: ${p['price']}\nرصيدك الحالي: ${user['balance']:.2f}\nيرجى شحن حسابك أولاً.")
        return

    msg = bot.send_message(call.message.chat.id, f"🎯 لتأكيد شحن باقة <b>{p['name']}</b>:\nأرسل الآن <b>{p['input_hint']}</b> في المحادثة:")
    bot.register_next_step_handler(msg, execute_order_workflow, p)

def execute_order_workflow(message, product):
    uid = message.from_user.id
    target_id = message.text.strip()
    user = get_user(uid)

    if user['balance'] < product['price']:
        bot.reply_to(message, "❌ رصيدك أصبح غير كافٍ لإتمام العملية.")
        return

    # خصم الرصيد مبدئياً وتسجيل الطلب
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (product['price'], uid))
        c.execute("INSERT INTO orders (user_id, type, item_name, target_id, amount, status) VALUES (?, 'charge', ?, ?, ?, 'processing')",
                  (uid, product['name'], target_id, product['price']))
        order_id = c.lastrowid
        conn.commit()

    wait_msg = bot.send_message(uid, "⏳ <b>جاري معالجة الطلب وإرساله للسيرفر...</b>")

    # إذا كان المنتج مرتبطاً بـ API خارجي ➔ تنفيذ فوري آلي
    if product['is_auto'] == 1 and product['api_provider_id'] > 0:
        with get_db() as conn:
            provider = conn.cursor().execute("SELECT * FROM api_providers WHERE id = ?", (product['api_provider_id'],)).fetchone()

        if provider:
            try:
                # إرسال طلب الشحن المباشر للسيرفر الخارجي
                payload = {
                    'key': provider['api_key'],
                    'action': 'add',
                    'service': product['api_service_id'],
                    'link': target_id,
                    'quantity': 1
                }
                res = requests.post(provider['api_url'], data=payload, timeout=25).json()

                if "order" in res:
                    ext_id = res["order"]
                    with get_db() as conn:
                        conn.cursor().execute("UPDATE orders SET status = 'completed', api_order_id = ? WHERE id = ?", (str(ext_id), order_id))
                        conn.commit()
                    bot.delete_message(uid, wait_msg.message_id)
                    bot.send_message(uid, f"✅ <b>تم شحن حسابك بنجاح وبشكل فوري!</b>\n📦 الباقة: {product['name']}\n🎮 الآيدي: <code>{target_id}</code>\n🔢 رقم الشحنة: <code>#{ext_id}</code>", reply_markup=user_main_markup())
                    bot.send_message(ADMIN_ID, f"⚡️ <b>شحن فوري ناجح #{order_id}</b> عبر API!\nالمستخدم: <code>{uid}</code>\nالهدف: <code>{target_id}</code>\nرقم السيرفر: #{ext_id}")
                    return
            except Exception as e:
                pass  # إذا فشل API ننتقل للتنفيذ اليدوي أو استرداد الرصيد

    # في حال كان التنفيذ يدوياً أو تعذر الـ API:
    with get_db() as conn:
        conn.cursor().execute("UPDATE orders SET status = 'pending' WHERE id = ?", (order_id,))
        conn.commit()

    bot.delete_message(uid, wait_msg.message_id)
    bot.send_message(uid, f"✅ <b>تم استلام طلبك رقم #{order_id}</b>\nسيتم مراجعته وتأكيده خلال دقائق قليلة.", reply_markup=user_main_markup())

    # إشعار الأدمن بأزرار الموافقة والرفض
    adm_m = types.InlineKeyboardMarkup(row_width=2)
    adm_m.add(
        types.InlineKeyboardButton("✅ تم الشحن", callback_data=f"adm_ok_{order_id}"),
        types.InlineKeyboardButton("❌ إلغاء ورد الرصيد", callback_data=f"adm_no_{order_id}")
    )
    bot.send_message(
        ADMIN_ID,
        f"🚨 <b>طلب شحن جديد #{order_id}</b>\n👤 العميل: <code>{uid}</code>\n📦 الباقة: <b>{product['name']}</b>\n🎮 الآيدي: <code>{target_id}</code>\n💵 السعر: ${product['price']}",
        reply_markup=adm_m
    )

# ----------------- تفاصيل وطرق الإيداع المتقدمة -----------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("open_pm_"))
def deposit_method_step(call):
    bot.answer_callback_query(call.id)
    mid = call.data.split("_")[2]
    with get_db() as conn:
        m = conn.cursor().execute("SELECT * FROM payment_methods WHERE id = ?", (mid,)).fetchone()

    text = (
        f"💳 <b>طريقة الإيداع: {m['title']}</b>\n\n"
        f"📋 <b>تعليمات الدفع والتحويل:</b>\n{m['details']}\n\n"
        f"📌 بعد التحويل، اضغط الزر أدناه لإرسال الإيصال وتأكيد الإيداع."
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📤 إرسال إشعار الدفع الآن", callback_data=f"up_receipt_{mid}"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="u_deposit"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("up_receipt_"))
def start_receipt_upload(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💵 اكتب المبلغ المحول بالدولار ($):\n(مثال: <code>10</code> أو <code>25.5</code>)")
    bot.register_next_step_handler(msg, get_receipt_amount)

def get_receipt_amount(message):
    try:
        amount = float(message.text.strip())
        msg = bot.send_message(message.chat.id, "📸 أرسل الآن <b>صورة إشعار التحويل (سكرين شوت)</b>:")
        bot.register_next_step_handler(msg, save_receipt_photo, amount)
    except:
        bot.reply_to(message, "❌ خطأ في كتابة المبلغ، أعد المحاولة من زر الإيداع.")

def save_receipt_photo(message, amount):
    if not message.photo:
        bot.reply_to(message, "❌ يرجى إرسال صورة حصراً.")
        return
    photo_id = message.photo[-1].file_id
    uid = message.from_user.id

    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO orders (user_id, type, item_name, target_id, amount, status) VALUES (?, 'deposit', 'طلب إيداع رصيد', 'تحويل يدوي', ?, 'pending')", (uid, amount))
        dep_id = c.lastrowid
        conn.commit()

    bot.reply_to(message, f"✅ تم تسليم الإيصال بنجاح (طلب رقم #{dep_id}). سيتم تدقيقه وإضافة الرصيد لمحفظتك فوراً.")

    adm_m = types.InlineKeyboardMarkup(row_width=2)
    adm_m.add(
        types.InlineKeyboardButton("✅ قبول وإضافة الرصيد", callback_data=f"adm_dep_ok_{dep_id}"),
        types.InlineKeyboardButton("❌ رفض الإيصال", callback_data=f"adm_dep_no_{dep_id}")
    )
    bot.send_photo(
        ADMIN_ID,
        photo_id,
        caption=f"💳 <b>طلب إيداع رصيد #{dep_id}</b>\n👤 من العميل: <code>{uid}</code>\n💵 المبلغ: <b>${amount}</b>",
        reply_markup=adm_m
    )

# ----------------- لوحة تحكم الأدمن والـ API الفوري -----------------

@bot.callback_query_handler(func=lambda call: call.data.startswith(("adm_ok_", "adm_no_", "adm_dep_ok_", "adm_dep_no_")))
def manage_order_actions(call):
    bot.answer_callback_query(call.id)
    if call.from_user.id != ADMIN_ID:
        return

    action_data = call.data
    oid = int(action_data.split("_")[-1])

    with get_db() as conn:
        c = conn.cursor()
        order = c.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
        if not order or order['status'] not in ['pending', 'processing']:
            bot.send_message(call.message.chat.id, "تم اتخاذ إجراء مسبق على هذا الطلب!")
            return

        if "adm_dep_ok" in action_data:
            c.execute("UPDATE orders SET status = 'completed' WHERE id = ?", (oid,))
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (order['amount'], order['user_id']))
            conn.commit()
            bot.send_message(order['user_id'], f"🎉 <b>تم تأكيد إيداعك بنجاح!</b>\nأصبح برصيدك الآن <b>+${order['amount']}</b> إضافية.")
            bot.edit_message_caption(f"✅ تم قبول الإيداع #{oid} وشحن ${order['amount']} للعميل.", call.message.chat.id, call.message.message_id)

        elif "adm_dep_no" in action_data:
            c.execute("UPDATE orders SET status = 'failed' WHERE id = ?", (oid,))
            conn.commit()
            bot.send_message(order['user_id'], f"❌ نعتذر، تم رفض إشعار الإيداع #{oid}. تواصل مع الدعم للمساعدة.")
            bot.edit_message_caption(f"❌ تم رفض الإيداع #{oid}.", call.message.chat.id, call.message.message_id)

        elif "adm_ok" in action_data:
            c.execute("UPDATE orders SET status = 'completed' WHERE id = ?", (oid,))
            conn.commit()
            bot.send_message(order['user_id'], f"✅ <b>تم تنفيذ طلب الشحن #{oid} بنجاح!</b>\nشكراً لثقتكم بنا.")
            bot.edit_message_text(f"✅ تم تأكيد إتمام الشحن للطلب #{oid}.", call.message.chat.id, call.message.message_id)

        elif "adm_no" in action_data:
            c.execute("UPDATE orders SET status = 'failed' WHERE id = ?", (oid,))
            c.execute("UPDATE users SET balance = balance
