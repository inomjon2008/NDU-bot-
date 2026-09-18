import os
import sqlite3
import html
import logging
from datetime import datetime

from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# SOZLAMALAR
# =========================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

DB_NAME = "rektor_bot.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            course TEXT NOT NULL,
            faculty TEXT NOT NULL,
            group_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS appeals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            category TEXT DEFAULT 'Rektorga murojaat',
            message TEXT NOT NULL,
            status TEXT DEFAULT 'new',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appeal_id INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def get_user(telegram_id):
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()

    conn.close()
    return user


def save_user(telegram_id, full_name, course, faculty, group_name):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    existing = conn.execute(
        "SELECT id FROM users WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()

    if existing:
        conn.execute("""
            UPDATE users
            SET full_name = ?,
                course = ?,
                faculty = ?,
                group_name = ?,
                updated_at = ?
            WHERE telegram_id = ?
        """, (
            full_name,
            course,
            faculty,
            group_name,
            now,
            telegram_id,
        ))
    else:
        conn.execute("""
            INSERT INTO users
            (
                telegram_id,
                full_name,
                course,
                faculty,
                group_name,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            telegram_id,
            full_name,
            course,
            faculty,
            group_name,
            now,
            now,
        ))

    conn.commit()
    conn.close()


def create_appeal(telegram_id, message):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur = conn.execute("""
        INSERT INTO appeals
        (
            telegram_id,
            category,
            message,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        telegram_id,
        "Rektorga murojaat",
        message,
        "new",
        now,
        now,
    ))

    appeal_id = cur.lastrowid

    conn.commit()
    conn.close()

    return appeal_id


def get_appeal(appeal_id):
    conn = get_db()

    appeal = conn.execute(
        "SELECT * FROM appeals WHERE id = ?",
        (appeal_id,)
    ).fetchone()

    conn.close()

    return appeal


def get_new_appeals():
    conn = get_db()

    appeals = conn.execute("""
        SELECT *
        FROM appeals
        WHERE status = 'new'
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return appeals


def get_all_appeals():
    conn = get_db()

    appeals = conn.execute("""
        SELECT *
        FROM appeals
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return appeals


def update_status(appeal_id, status):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
        UPDATE appeals
        SET status = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        status,
        now,
        appeal_id,
    ))

    conn.commit()
    conn.close()


def save_reply(appeal_id, admin_id, message):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
        INSERT INTO replies
        (
            appeal_id,
            admin_id,
            message,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        appeal_id,
        admin_id,
        message,
        now,
    ))

    conn.commit()
    conn.close()


# =========================================================
# KEYBOARDS
# =========================================================

def start_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🚀 Boshlash",
                callback_data="register_start"
            )
        ]
    ])


def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📝 Rektorga murojaat",
                callback_data="appeal_start"
            )
        ]
    ])


def confirm_registration():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Tasdiqlash",
                callback_data="register_confirm"
            ),
            InlineKeyboardButton(
                "✏️ Qayta kiritish",
                callback_data="register_rewrite"
            ),
        ]
    ])


def appeal_confirm():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📨 Yuborish",
                callback_data="appeal_confirm"
            ),
            InlineKeyboardButton(
                "✏️ Qayta yozish",
                callback_data="appeal_rewrite"
            ),
        ]
    ])


def admin_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🆕 Yangi murojaatlar",
                callback_data="admin_new"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 Barcha murojaatlar",
                callback_data="admin_all"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Statistika",
                callback_data="admin_stats"
            )
        ],
    ])


def appeal_actions(appeal_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💬 Javob berish",
                callback_data=f"reply_{appeal_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 Jarayonda",
                callback_data=f"status_process_{appeal_id}"
            ),
            InlineKeyboardButton(
                "✅ Yakunlandi",
                callback_data=f"status_done_{appeal_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "❌ Rad etildi",
                callback_data=f"status_rejected_{appeal_id}"
            )
        ],
    ])


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = get_user(update.effective_user.id)

    if not user:
        await update.message.reply_text(
            "👋 Assalomu alaykum!\n\n"
            "🎓 Rektor bilan muloqot botiga xush kelibsiz.\n\n"
            "Murojaat yuborish uchun avval qisqa ro‘yxatdan o‘ting.",
            reply_markup=start_keyboard()
        )
    else:
        await update.message.reply_text(
            "👋 Xush kelibsiz!\n\n"
            "Rektorga murojaat yuborishingiz mumkin.",
            reply_markup=main_menu()
        )


# =========================================================
# REGISTRATION
# =========================================================

def parse_registration(text):
    """
    Qabul qilinadigan format:

    F.I.Sh: Aliyev Ali Valiyevich
    Kurs: 2
    Fakultet: Axborot texnologiyalari
    Guruh: 24-01
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    data = {}

    for line in lines:
        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        key = key.strip().lower()
        value = value.strip()

        if not value:
            continue

        if key in ["f.i.sh", "fish", "f.i.sh.", "ism familiya"]:
            data["full_name"] = value

        elif key in ["kurs", "course"]:
            data["course"] = value

        elif key in ["fakultet", "faculty"]:
            data["faculty"] = value

        elif key in ["guruh", "group"]:
            data["group_name"] = value

    # Agar foydalanuvchi oddiy 4 qator yuborsa ham qabul qilamiz
    if len(data) < 4 and len(lines) == 4:

        data = {
            "full_name": lines[0],
            "course": lines[1],
            "faculty": lines[2],
            "group_name": lines[3],
        }

    required = [
        "full_name",
        "course",
        "faculty",
        "group_name",
    ]

    if not all(key in data for key in required):
        return None

    return data


async def registration_start(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["state"] = "registration"

    await query.message.edit_text(
        "📝 <b>Ro‘yxatdan o‘tish</b>\n\n"
        "Quyidagi 4 ta ma’lumotni <b>bitta xabarda</b> yuboring:\n\n"
        "<code>"
        "F.I.Sh: Aliyev Ali Valiyevich\n"
        "Kurs: 2\n"
        "Fakultet: Axborot texnologiyalari\n"
        "Guruh: 24-01"
        "</code>\n\n"
        "💡 Guruhni oddiy yozishingiz mumkin: "
        "<b>24-01</b>, <b>101</b>, <b>12-A</b> va hokazo.",
        parse_mode=ParseMode.HTML
    )


async def process_registration(update, context):

    text = update.message.text.strip()

    data = parse_registration(text)

    if not data:
        await update.message.reply_text(
            "❌ Ma’lumotlar to‘liq kiritilmadi.\n\n"
            "Iltimos, bitta xabarda quyidagicha yuboring:\n\n"
            "<code>"
            "F.I.Sh: Aliyev Ali Valiyevich\n"
            "Kurs: 2\n"
            "Fakultet: Axborot texnologiyalari\n"
            "Guruh: 24-01"
            "</code>",
            parse_mode=ParseMode.HTML
        )
        return

    context.user_data["registration_data"] = data
    context.user_data["state"] = "registration_confirm"

    await update.message.reply_text(
        "🔎 <b>Ma’lumotlaringizni tekshiring:</b>\n\n"
        f"👤 <b>F.I.Sh:</b> {html.escape(data['full_name'])}\n"
        f"🎓 <b>Kurs:</b> {html.escape(data['course'])}\n"
        f"🏛 <b>Fakultet:</b> {html.escape(data['faculty'])}\n"
        f"👥 <b>Guruh:</b> {html.escape(data['group_name'])}\n\n"
        "Ma’lumotlar to‘g‘rimi?",
        parse_mode=ParseMode.HTML,
        reply_markup=confirm_registration()
    )


async def registration_confirm(update, context):

    query = update.callback_query
    await query.answer()

    data = context.user_data.get("registration_data")

    if not data:
        await query.message.edit_text(
            "❌ Ma’lumotlar topilmadi. Iltimos, qaytadan boshlang."
        )
        return

    save_user(
        update.effective_user.id,
        data["full_name"],
        data["course"],
        data["faculty"],
        data["group_name"],
    )

    context.user_data.clear()

    await query.message.edit_text(
        "✅ <b>Ro‘yxatdan o‘tish muvaffaqiyatli yakunlandi!</b>\n\n"
        "Endi rektorga murojaat yuborishingiz mumkin.",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu()
    )


async def registration_rewrite(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["state"] = "registration"

    await query.message.edit_text(
        "✏️ Ma’lumotlarni qaytadan yuboring:\n\n"
        "<code>"
        "F.I.Sh: Aliyev Ali Valiyevich\n"
        "Kurs: 2\n"
        "Fakultet: Axborot texnologiyalari\n"
        "Guruh: 24-01"
        "</code>",
        parse_mode=ParseMode.HTML
    )


# =========================================================
# APPEAL
# =========================================================

async def appeal_start(update, context):

    query = update.callback_query
    await query.answer()

    user = get_user(update.effective_user.id)

    if not user:
        await query.message.edit_text(
            "Avval ro‘yxatdan o‘ting.",
            reply_markup=start_keyboard()
        )
        return

    context.user_data["state"] = "appeal"

    await query.message.edit_text(
        "📝 <b>Rektorga murojaat</b>\n\n"
        "Murojaatingizni bitta xabarda yozing.\n\n"
        "Masalan:\n"
        "“Kontrakt bo‘yicha savolim bor...”",
        parse_mode=ParseMode.HTML
    )


async def process_appeal(update, context):

    text = update.message.text.strip()

    if not text:
        await update.message.reply_text(
            "❌ Murojaat matni bo‘sh bo‘lishi mumkin emas."
        )
        return

    context.user_data["appeal_text"] = text
    context.user_data["state"] = "appeal_confirm"

    await update.message.reply_text(
        "🔎 <b>Murojaatingiz:</b>\n\n"
        f"{html.escape(text)}\n\n"
        "Yuborilsinmi?",
        parse_mode=ParseMode.HTML,
        reply_markup=appeal_confirm()
    )


async def appeal_send(update, context):

    query = update.callback_query
    await query.answer()

    text = context.user_data.get("appeal_text")

    if not text:
        await query.message.edit_text(
            "❌ Murojaat topilmadi."
        )
        return

    appeal_id = create_appeal(
        update.effective_user.id,
        text
    )

    user = get_user(update.effective_user.id)

    # Adminlarga yuborish
    admin_text = (
        "🚨 <b>YANGI MUROJAAT</b>\n\n"
        f"🆔 <b>Murojaat:</b> #{appeal_id}\n"
        f"👤 <b>F.I.Sh:</b> {html.escape(user['full_name'])}\n"
        f"🎓 <b>Kurs:</b> {html.escape(user['course'])}\n"
        f"🏛 <b>Fakultet:</b> {html.escape(user['faculty'])}\n"
        f"👥 <b>Guruh:</b> {html.escape(user['group_name'])}\n\n"
        f"📝 <b>Murojaat:</b>\n"
        f"{html.escape(text)}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode=ParseMode.HTML,
                reply_markup=appeal_actions(appeal_id)
            )
        except Exception as e:
            logger.error(
                f"Admin {admin_id} ga yuborishda xato: {e}"
            )

    context.user_data.clear()

    await query.message.edit_text(
        "✅ <b>Murojaatingiz yuborildi!</b>\n\n"
        f"🆔 Murojaat raqami: <b>#{appeal_id}</b>\n\n"
        "Javob berilganda sizga Telegram orqali xabar keladi.",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu()
    )


async def appeal_rewrite(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["state"] = "appeal"

    await query.message.edit_text(
        "✏️ Murojaatingizni qaytadan yozing:"
    )


# =========================================================
# ADMIN
# =========================================================

async def admin_command(update, context):

    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text(
            "⛔ Sizda admin huquqi yo‘q."
        )
        return

    await update.message.reply_text(
        "🔐 <b>Admin panel</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_menu()
    )


async def show_new_appeals(update, context):

    query = update.callback_query
    await query.answer()

    if update.effective_user.id not in ADMIN_IDS:
        return

    appeals = get_new_appeals()

    if not appeals:
        await query.message.edit_text(
            "📭 Hozircha yangi murojaatlar yo‘q.",
            reply_markup=admin_menu()
        )
        return

    for appeal in appeals:

        user = get_user(appeal["telegram_id"])

        if user:
            info = (
                f"👤 <b>F.I.Sh:</b> "
                f"{html.escape(user['full_name'])}\n"
                f"🎓 <b>Kurs:</b> "
                f"{html.escape(user['course'])}\n"
                f"🏛 <b>Fakultet:</b> "
                f"{html.escape(user['faculty'])}\n"
                f"👥 <b>Guruh:</b> "
                f"{html.escape(user['group_name'])}\n\n"
            )
        else:
            info = ""

        text = (
            "🆕 <b>YANGI MUROJAAT</b>\n\n"
            f"🆔 #{appeal['id']}\n"
            f"{info}"
            f"📝 {html.escape(appeal['message'])}\n\n"
            f"🕐 {appeal['created_at']}"
        )

        await query.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=appeal_actions(appeal["id"])
        )

    await query.message.reply_text(
        "🔐 Admin panel",
        reply_markup=admin_menu()
    )


async def show_all_appeals(update, context):

    query = update.callback_query
    await query.answer()

    if update.effective_user.id not in ADMIN_IDS:
        return

    appeals = get_all_appeals()

    if not appeals:
        await query.message.edit_text(
            "📭 Murojaatlar mavjud emas.",
            reply_markup=admin_menu()
        )
        return

    for appeal in appeals:

        status_map = {
            "new": "🆕 Yangi",
            "process": "🔄 Jarayonda",
            "done": "✅ Yakunlandi",
            "rejected": "❌ Rad etildi",
        }

        await query.message.reply_text(
            f"🆔 <b>#{appeal['id']}</b>\n"
            f"📌 <b>Status:</b> "
            f"{status_map.get(appeal['status'], appeal['status'])}\n\n"
            f"📝 {html.escape(appeal['message'])}\n\n"
            f"🕐 {appeal['created_at']}",
            parse_mode=ParseMode.HTML,
            reply_markup=appeal_actions(appeal["id"])
        )

    await query.message.reply_text(
        "🔐 Admin panel",
        reply_markup=admin_menu()
    )


async def show_stats(update, context):

    query = update.callback_query
    await query.answer()

    if update.effective_user.id not in ADMIN_IDS:
        return

    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) FROM appeals"
    ).fetchone()[0]

    new = conn.execute(
        "SELECT COUNT(*) FROM appeals WHERE status='new'"
    ).fetchone()[0]

    process = conn.execute(
        "SELECT COUNT(*) FROM appeals WHERE status='process'"
    ).fetchone()[0]

    done = conn.execute(
        "SELECT COUNT(*) FROM appeals WHERE status='done'"
    ).fetchone()[0]

    rejected = conn.execute(
        "SELECT COUNT(*) FROM appeals WHERE status='rejected'"
    ).fetchone()[0]

    users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    conn.close()

    await query.message.edit_text(
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users}</b>\n"
        f"📨 Jami murojaatlar: <b>{total}</b>\n\n"
        f"🆕 Yangi: <b>{new}</b>\n"
        f"🔄 Jarayonda: <b>{process}</b>\n"
        f"✅ Yakunlangan: <b>{done}</b>\n"
        f"❌ Rad etilgan: <b>{rejected}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_menu()
    )


# =========================================================
# ADMIN REPLY
# =========================================================

async def start_reply(update, context):

    query = update.callback_query
    await query.answer()

    if update.effective_user.id not in ADMIN_IDS:
        return

    appeal_id = int(query.data.split("_")[1])

    appeal = get_appeal(appeal_id)

    if not appeal:
        await query.message.reply_text(
            "❌ Murojaat topilmadi."
        )
        return

    context.user_data["state"] = "admin_reply"
    context.user_data["reply_appeal_id"] = appeal_id

    await query.message.reply_text(
        f"💬 <b>#{appeal_id}</b> murojaatga javobingizni yozing:",
        parse_mode=ParseMode.HTML
    )


async def process_admin_reply(update, context):

    appeal_id = context.user_data.get("reply_appeal_id")
    text = update.message.text.strip()

    if not appeal_id:
        return

    appeal = get_appeal(appeal_id)

    if not appeal:
        await update.message.reply_text(
            "❌ Murojaat topilmadi."
        )
        context.user_data.clear()
        return

    save_reply(
        appeal_id,
        update.effective_user.id,
        text
    )

    try:
        await context.bot.send_message(
            chat_id=appeal["telegram_id"],
            text=(
                f"💬 <b>Rektorat javobi</b>\n\n"
                f"🆔 Murojaat: <b>#{appeal_id}</b>\n\n"
                f"{html.escape(text)}"
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Userga javob yuborishda xato: {e}")

    context.user_data.clear()

    await update.message.reply_text(
        f"✅ #{appeal_id} murojaatga javob yuborildi.",
        reply_markup=admin_menu()
    )


# =========================================================
# STATUS
# =========================================================

async def change_status(update, context):

    query = update.callback_query
    await query.answer()

    if update.effective_user.id not in ADMIN_IDS:
        return

    parts = query.data.split("_")

    status = parts[1]
    appeal_id = int(parts[2])

    update_status(appeal_id, status)

    appeal = get_appeal(appeal_id)

    status_text = {
        "process": "🔄 Murojaatingiz ko‘rib chiqilmoqda.",
        "done": "✅ Murojaatingiz yakunlandi.",
        "rejected": "❌ Murojaatingiz rad etildi.",
    }

    try:
        await context.bot.send_message(
            chat_id=appeal["telegram_id"],
            text=(
                f"📢 <b>#{appeal_id} murojaat holati</b>\n\n"
                f"{status_text.get(status, 'Holat yangilandi.')}"
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Status yuborishda xato: {e}")

    await query.message.reply_text(
        f"✅ #{appeal_id} holati yangilandi."
    )


# =========================================================
# CANCEL
# =========================================================

async def cancel(update, context):

    context.user_data.clear()

    user = get_user(update.effective_user.id)

    if user:
        await update.message.reply_text(
            "Bekor qilindi.",
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "Bekor qilindi.",
            reply_markup=start_keyboard()
        )


# =========================================================
# ID
# =========================================================

async def my_id(update, context):

    await update.message.reply_text(
        f"🆔 Sizning Telegram ID: <code>{update.effective_user.id}</code>",
        parse_mode=ParseMode.HTML
    )


# =========================================================
# CALLBACK ROUTER
# =========================================================

async def callback_router(update, context):

    query = update.callback_query
    data = query.data

    if data == "register_start":
        await registration_start(update, context)

    elif data == "register_confirm":
        await registration_confirm(update, context)

    elif data == "register_rewrite":
        await registration_rewrite(update, context)

    elif data == "appeal_start":
        await appeal_start(update, context)

    elif data == "appeal_confirm":
        await appeal_send(update, context)

    elif data == "appeal_rewrite":
        await appeal_rewrite(update, context)

    elif data == "admin_new":
        await show_new_appeals(update, context)

    elif data == "admin_all":
        await show_all_appeals(update, context)

    elif data == "admin_stats":
        await show_stats(update, context)

    elif data.startswith("reply_"):
        await start_reply(update, context)

    elif data.startswith("status_"):
        await change_status(update, context)


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(update, context):

    state = context.user_data.get("state")

    if state == "registration":
        await process_registration(update, context)

    elif state == "appeal":
        await process_appeal(update, context)

    elif state == "admin_reply":
        await process_admin_reply(update, context)

    else:
        user = get_user(update.effective_user.id)

        if user:
            await update.message.reply_text(
                "Kerakli bo‘limni tanlang:",
                reply_markup=main_menu()
            )
        else:
            await update.message.reply_text(
                "Avval ro‘yxatdan o‘ting.",
                reply_markup=start_keyboard()
            )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN topilmadi!")
        return

    if not ADMIN_IDS:
        print("⚠️ ADMIN_IDS topilmadi!")

    init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("admin", admin_command)
    )

    application.add_handler(
        CommandHandler("cancel", cancel)
    )

    application.add_handler(
        CommandHandler("id", my_id)
    )

    application.add_handler(
        CallbackQueryHandler(callback_router)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )

    print("🤖 Rektor bot ishga tushdi...")

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()