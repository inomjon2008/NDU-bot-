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
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# YORDAMCHI FUNKSIYALAR
# =========================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def esc(text):
    return html.escape(str(text))


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def is_admin(user_id):
    return user_id in ADMIN_IDS


# =========================================================
# DATABASE
# =========================================================

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
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    ).fetchone()

    conn.close()
    return user


def save_user(
    telegram_id,
    full_name,
    course,
    faculty,
    group_name
):
    conn = get_db()

    current_time = now()

    existing = conn.execute(
        """
        SELECT id
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    ).fetchone()

    if existing:
        conn.execute(
            """
            UPDATE users
            SET
                full_name = ?,
                course = ?,
                faculty = ?,
                group_name = ?,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                full_name,
                course,
                faculty,
                group_name,
                current_time,
                telegram_id,
            )
        )
    else:
        conn.execute(
            """
            INSERT INTO users (
                telegram_id,
                full_name,
                course,
                faculty,
                group_name,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                full_name,
                course,
                faculty,
                group_name,
                current_time,
                current_time,
            )
        )

    conn.commit()
    conn.close()


def create_appeal(telegram_id, message):
    conn = get_db()

    current_time = now()

    cur = conn.execute(
        """
        INSERT INTO appeals (
            telegram_id,
            category,
            message,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_id,
            "Rektorga murojaat",
            message,
            "new",
            current_time,
            current_time,
        )
    )

    appeal_id = cur.lastrowid

    conn.commit()
    conn.close()

    return appeal_id


def get_appeal(appeal_id):
    conn = get_db()

    appeal = conn.execute(
        """
        SELECT *
        FROM appeals
        WHERE id = ?
        """,
        (appeal_id,)
    ).fetchone()

    conn.close()

    return appeal


def get_new_appeals():
    conn = get_db()

    appeals = conn.execute(
        """
        SELECT *
        FROM appeals
        WHERE status = 'new'
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return appeals


def get_all_appeals():
    conn = get_db()

    appeals = conn.execute(
        """
        SELECT *
        FROM appeals
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return appeals


def update_status(appeal_id, status):
    conn = get_db()

    conn.execute(
        """
        UPDATE appeals
        SET
            status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            status,
            now(),
            appeal_id,
        )
    )

    conn.commit()
    conn.close()


def save_reply(appeal_id, admin_id, message):
    conn = get_db()

    conn.execute(
        """
        INSERT INTO replies (
            appeal_id,
            admin_id,
            message,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            appeal_id,
            admin_id,
            message,
            now(),
        )
    )

    conn.commit()
    conn.close()


# =========================================================
# KEYBOARDS
# =========================================================

def start_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🚀 Ro‘yxatdan o‘tish",
                callback_data="register_start"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ Bot haqida",
                callback_data="about_bot"
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
        ],
        [
            InlineKeyboardButton(
                "👤 Mening ma’lumotlarim",
                callback_data="my_profile"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ Bot haqida",
                callback_data="about_bot"
            )
        ]
    ])


def confirm_registration():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Tasdiqlash",
                callback_data="register_confirm"
            )
        ],
        [
            InlineKeyboardButton(
                "✏️ Qayta kiritish",
                callback_data="register_rewrite"
            )
        ]
    ])


def appeal_confirm():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📨 Yuborish",
                callback_data="appeal_confirm"
            )
        ],
        [
            InlineKeyboardButton(
                "✏️ Qayta yozish",
                callback_data="appeal_rewrite"
            )
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
        ]
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
            )
        ],
        [
            InlineKeyboardButton(
                "❌ Rad etildi",
                callback_data=f"status_rejected_{appeal_id}"
            )
        ]
    ])


def back_to_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⬅️ Asosiy menyu",
                callback_data="back_main"
            )
        ]
    ])


# =========================================================
# /START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    user = get_user(update.effective_user.id)

    if not user:

        text = (
            "🎓 <b>UNIVERSITET REKTORIGA MUROJAAT BOTI</b>\n\n"
            "Assalomu alaykum! 👋\n\n"
            "Ushbu bot orqali talabalar "
            "<b>rektoratga o‘z murojaatlarini</b> "
            "qulay va tezkor tarzda yuborishlari mumkin.\n\n"
            "📌 Murojaat yuborishdan oldin "
            "qisqa ro‘yxatdan o‘tishingiz kerak.\n\n"
            "🔐 Sizning ma’lumotlaringiz murojaatni "
            "to‘g‘ri ko‘rib chiqish uchun foydalaniladi."
        )

        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=start_keyboard()
        )

    else:

        text = (
            "🎓 <b>Xush kelibsiz!</b>\n\n"
            f"👤 <b>{esc(user['full_name'])}</b>\n\n"
            "Rektoratga murojaat yuborish uchun "
            "quyidagi tugmadan foydalaning."
        )

        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu()
        )


# =========================================================
# ABOUT
# =========================================================

async def about_bot(update, context):

    query = update.callback_query
    await query.answer()

    text = (
        "ℹ️ <b>BOT HAQIDA</b>\n\n"
        "🎓 Ushbu bot universitet talabalari "
        "va rektorat o‘rtasidagi murojaatlar "
        "almashinuvini qulaylashtirish uchun yaratilgan.\n\n"
        "📨 Siz murojaat yuborishingiz mumkin.\n"
        "💬 Rektorat javobini Telegram orqali olasiz.\n"
        "🔄 Murojaat holatini kuzatishingiz mumkin.\n\n"
        "<i>Har bir murojaat mas’ul xodimlar tomonidan "
        "ko‘rib chiqiladi.</i>"
    )

    await query.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu()
    )


# =========================================================
# REGISTRATION
# =========================================================

def parse_registration(text):

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

        if key in [
            "f.i.sh",
            "f.i.sh.",
            "fish",
            "ism familiya"
        ]:
            data["full_name"] = value

        elif key in [
            "kurs",
            "course"
        ]:
            data["course"] = value

        elif key in [
            "fakultet",
            "faculty"
        ]:
            data["faculty"] = value

        elif key in [
            "guruh",
            "group"
        ]:
            data["group_name"] = value

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

    context.user_data.clear()
    context.user_data["state"] = "registration"

    text = (
        "📝 <b>RO‘YXATDAN O‘TISH</b>\n\n"
        "Sizdan faqat <b>4 ta ma’lumot</b> kerak.\n\n"
        "Hammasini <b>bitta xabarda</b> yuboring:\n\n"
        "<code>"
        "F.I.Sh: Aliyev Ali Valiyevich\n"
        "Kurs: 2\n"
        "Fakultet: Axborot texnologiyalari\n"
        "Guruh: KX-24-01"
        "</code>\n\n"
        "💡 Guruhni oddiy yozishingiz mumkin:\n"
        "<b>KX-24-01</b>, <b>24-01</b>, <b>101</b>, <b>12-A</b>"
    )

    await query.message.edit_text(
        text,
        parse_mode=ParseMode.HTML
    )


async def process_registration(update, context):

    text = update.message.text.strip()

    data = parse_registration(text)

    if not data:

        await update.message.reply_text(
            "⚠️ <b>Ma’lumotlar to‘liq aniqlanmadi.</b>\n\n"
            "Iltimos, 4 ta ma’lumotni bitta xabarda "
            "quyidagi ko‘rinishda yuboring:\n\n"
            "<code>"
            "F.I.Sh: Aliyev Ali Valiyevich\n"
            "Kurs: 2\n"
            "Fakultet: Axborot texnologiyalari\n"
            "Guruh: KX-24-01"
            "</code>",
            parse_mode=ParseMode.HTML
        )

        return

    context.user_data["registration_data"] = data
    context.user_data["state"] = "registration_confirm"

    text = (
        "🔎 <b>MA’LUMOTLARNI TEKSHIRING</b>\n\n"
        "👤 <b>F.I.Sh</b>\n"
        f"{esc(data['full_name'])}\n\n"
        "🎓 <b>Kurs</b>\n"
        f"{esc(data['course'])}\n\n"
        "🏛 <b>Fakultet</b>\n"
        f"{esc(data['faculty'])}\n\n"
        "👥 <b>Guruh</b>\n"
        f"{esc(data['group_name'])}\n\n"
        "━━━━━━━━━━━━━━\n"
        "Ma’lumotlaringiz to‘g‘rimi?"
    )

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=confirm_registration()
    )


async def registration_confirm(update, context):

    query = update.callback_query
    await query.answer()

    data = context.user_data.get("registration_data")

    if not data:

        await query.message.edit_text(
            "⚠️ Ma’lumotlar topilmadi.\n\n"
            "Iltimos, ro‘yxatdan o‘tishni qaytadan boshlang.",
            reply_markup=start_keyboard()
        )

        return

    save_user(
        update.effective_user.id,
        data["full_name"],
        data["course"],
        data["faculty"],
        data["group_name"]
    )

    context.user_data.clear()

    text = (
        "✅ <b>RO‘YXATDAN O‘TISH YAKUNLANDI!</b>\n\n"
        "Ma’lumotlaringiz muvaffaqiyatli saqlandi.\n\n"
        "Endi siz rektoratga murojaat yuborishingiz mumkin. 📨"
    )

    await query.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu()
    )


async def registration_rewrite(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data.clear()
    context.user_data["state"] = "registration"

    await query.message.edit_text(
        "✏️ <b>MA’LUMOTLARNI QAYTA KIRITING</b>\n\n"
        "<code>"
        "F.I.Sh: Aliyev Ali Valiyevich\n"
        "Kurs: 2\n"
        "Fakultet: Axborot texnologiyalari\n"
        "Guruh: KX-24-01"
        "</code>",
        parse_mode=ParseMode.HTML
    )


# =========================================================
# PROFILE
# =========================================================

async def my_profile(update, context):

    query = update.callback_query
    await query.answer()

    user = get_user(update.effective_user.id)

    if not user:

        await query.message.edit_text(
            "⚠️ Siz hali ro‘yxatdan o‘tmagansiz.",
            reply_markup=start_keyboard()
        )

        return

    text = (
        "👤 <b>MENING MA’LUMOTLARIM</b>\n\n"
        "━━━━━━━━━━━━━━\n"
        f"👤 <b>F.I.Sh:</b>\n{esc(user['full_name'])}\n\n"
        f"🎓 <b>Kurs:</b> {esc(user['course'])}\n"
        f"🏛 <b>Fakultet:</b> {esc(user['faculty'])}\n"
        f"👥 <b>Guruh:</b> {esc(user['group_name'])}\n"
        "━━━━━━━━━━━━━━"
    )

    await query.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu()
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
            "⚠️ Avval ro‘yxatdan o‘ting.",
            reply_markup=start_keyboard()
        )

        return

    context.user_data.clear()
    context.user_data["state"] = "appeal"

    text = (
        "📝 <b>REKTORGA MUROJAAT</b>\n\n"
        "Murojaatingizni imkon qadar "
        "<b>aniq va tushunarli</b> qilib yozing.\n\n"
        "Masalan:\n"
        "<i>“Kontrakt to‘lovi bo‘yicha savolim bor. "
        "To‘lovni bo‘lib amalga oshirish imkoniyati haqida "
        "ma’lumot bermoqchiman.”</i>\n\n"
        "📌 Murojaatni bitta xabarda yuboring."
    )

    await query.message.edit_text(
        text,
        parse_mode=ParseMode.HTML
    )


async def process_appeal(update, context):

    text = update.message.text.strip()

    if len(text) < 5:

        await update.message.reply_text(
            "⚠️ <b>Murojaat juda qisqa.</b>\n\n"
            "Iltimos, muammo yoki savolingizni "
            "batafsilroq yozing.",
            parse_mode=ParseMode.HTML
        )

        return

    context.user_data["appeal_text"] = text
    context.user_data["state"] = "appeal_confirm"

    preview = (
        "🔎 <b>MUROJAATNI TEKSHIRISH</b>\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{esc(text)}\n"
        "━━━━━━━━━━━━━━\n\n"
        "Murojaat yuborilsinmi?"
    )

    await update.message.reply_text(
        preview,
        parse_mode=ParseMode.HTML,
        reply_markup=appeal_confirm()
    )


async def appeal_send(update, context):

    query = update.callback_query
    await query.answer()

    text = context.user_data.get("appeal_text")

    if not text:

        await query.message.edit_text(
            "⚠️ Murojaat topilmadi.\n\n"
            "Iltimos, qaytadan urinib ko‘ring.",
            reply_markup=main_menu()
        )

        return

    user = get_user(update.effective_user.id)

    if not user:

        await query.message.edit_text(
            "⚠️ Foydalanuvchi ma’lumotlari topilmadi.",
            reply_markup=start_keyboard()
        )

        return

    appeal_id = create_appeal(
        update.effective_user.id,
        text
    )

    admin_text = (
        "🚨 <b>YANGI REKTORGA MUROJAAT</b>\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Murojaat:</b> #{appeal_id}\n"
        f"👤 <b>Talaba:</b> {esc(user['full_name'])}\n"
        f"🎓 <b>Kurs:</b> {esc(user['course'])}\n"
        f"🏛 <b>Fakultet:</b> {esc(user['faculty'])}\n"
        f"👥 <b>Guruh:</b> {esc(user['group_name'])}\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "📝 <b>Murojaat matni:</b>\n\n"
        f"{esc(text)}\n\n"
        f"🕐 <b>Vaqt:</b> {now()}"
    )

    sent = 0

    for admin_id in ADMIN_IDS:

        try:

            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode=ParseMode.HTML,
                reply_markup=appeal_actions(appeal_id)
            )

            sent += 1

        except Exception as e:

            logger.error(
                f"Admin {admin_id} ga yuborishda xato: {e}"
            )

    context.user_data.clear()

    if sent == 0:

        await query.message.edit_text(
            "⚠️ <b>Texnik xatolik yuz berdi.</b>\n\n"
            "Murojaatingiz saqlandi, lekin "
            "mas’ullarga yuborishda muammo yuz berdi.\n\n"
            "Iltimos, keyinroq tekshiring.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu()
        )

        return

    text = (
        "✅ <b>MUROJAATINGIZ QABUL QILINDI!</b>\n\n"
        "Murojaatingiz rektorat mas’ullariga "
        "muvaffaqiyatli yuborildi.\n\n"
        f"🆔 <b>Murojaat raqami:</b> #{appeal_id}\n\n"
        "📩 Javob yoki murojaat holatidagi "
        "o‘zgarishlar Telegram orqali yuboriladi."
    )

    await query.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu()
    )


async def appeal_rewrite(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["state"] = "appeal"

    await query.message.edit_text(
        "✏️ <b>MUROJAATNI QAYTA YOZING</b>\n\n"
        "Murojaatingizni bitta xabarda yuboring.",
        parse_mode=ParseMode.HTML
    )


# =========================================================
# ADMIN PANEL
# =========================================================

async def admin_command(update, context):

    if not is_admin(update.effective_user.id):

        await update.message.reply_text(
            "⛔ <b>Kirish taqiqlangan.</b>\n\n"
            "Sizda admin huquqi mavjud emas.",
            parse_mode=ParseMode.HTML
        )

        return

    await update.message.reply_text(
        "🔐 <b>ADMINISTRATOR PANELI</b>\n\n"
        "Kerakli bo‘limni tanlang:",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_menu()
    )


# =========================================================
# NEW APPEALS
# =========================================================

async def show_new_appeals(update, context):

    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        return

    appeals = get_new_appeals()

    if not appeals:

        await query.message.edit_text(
            "📭 <b>Yangi murojaatlar yo‘q.</b>\n\n"
            "Hozircha ko‘rib chiqilmagan murojaatlar mavjud emas.",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_menu()
        )

        return

    await query.message.edit_text(
        f"🆕 <b>YANGI MUROJAATLAR</b>\n\n"
        f"Jami: <b>{len(appeals)}</b> ta",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_menu()
    )

    for appeal in appeals:

        user = get_user(appeal["telegram_id"])

        if user:

            student_info = (
                f"👤 <b>Talaba:</b> {esc(user['full_name'])}\n"
                f"🎓 <b>Kurs:</b> {esc(user['course'])}\n"
                f"🏛 <b>Fakultet:</b> {esc(user['faculty'])}\n"
                f"👥 <b>Guruh:</b> {esc(user['group_name'])}\n\n"
            )

        else:
            student_info = ""

        text = (
            "🆕 <b>MUROJAAT</b>\n\n"
            f"🆔 <b>#{appeal['id']}</b>\n"
            f"{student_info}"
            "━━━━━━━━━━━━━━━━\n"
            f"📝 {esc(appeal['message'])}\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🕐 {appeal['created_at']}"
        )

        await query.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=appeal_actions(appeal["id"])
        )


# =========================================================
# ALL APPEALS
# =========================================================

async def show_all_appeals(update, context):

    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        return

    appeals = get_all_appeals()

    if not appeals:

        await query.message.edit_text(
            "📭 <b>Murojaatlar mavjud emas.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_menu()
        )

        return

    status_map = {
        "new": "🆕 Yangi",
        "process": "🔄 Jarayonda",
        "done": "✅ Yakunlandi",
        "rejected": "❌ Rad etildi",
    }

    await query.message.edit_text(
        f"📋 <b>BARCHA MUROJAATLAR</b>\n\n"
        f"Jami: <b>{len(appeals)}</b> ta",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_menu()
    )

    for appeal in appeals:

        user = get_user(appeal["telegram_id"])

        student = ""

        if user:

            student = (
                f"👤 <b>{esc(user['full_name'])}</b>\n"
                f"🎓 {esc(user['course'])} | "
                f"👥 {esc(user['group_name'])}\n"
                f"🏛 {esc(user['faculty'])}\n\n"
            )

        text = (
            f"📌 <b>#{appeal['id']}</b>\n"
            f"📊 <b>Status:</b> "
            f"{status_map.get(appeal['status'], appeal['status'])}\n\n"
            f"{student}"
            f"📝 {esc(appeal['message'])}\n\n"
            f"🕐 {appeal['created_at']}"
        )

        await query.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=appeal_actions(appeal["id"])
        )


# =========================================================
# STATISTICS
# =========================================================

async def show_stats(update, context):

    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        return

    conn = get_db()

    users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

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

    conn.close()

    text = (
        "📊 <b>BOT STATISTIKASI</b>\n\n"
        "━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Talabalar:</b> {users}\n"
        f"📨 <b>Jami murojaatlar:</b> {total}\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"🆕 <b>Yangi:</b> {new}\n"
        f"🔄 <b>Jarayonda:</b> {process}\n"
        f"✅ <b>Yakunlangan:</b> {done}\n"
        f"❌ <b>Rad etilgan:</b> {rejected}"
    )

    await query.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=admin_menu()
    )


# =========================================================
# ADMIN REPLY
# =========================================================

async def start_reply(update, context):

    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        return

    try:
        appeal_id = int(query.data.split("_")[1])
    except (ValueError, IndexError):

        await query.message.reply_text(
            "⚠️ Murojaat raqami noto‘g‘ri."
        )

        return

    appeal = get_appeal(appeal_id)

    if not appeal:

        await query.message.reply_text(
            "❌ Murojaat topilmadi."
        )

        return

    context.user_data["state"] = "admin_reply"
    context.user_data["reply_appeal_id"] = appeal_id

    await query.message.reply_text(
        f"💬 <b>#{appeal_id}</b> Murojaatga javob\n\n"
        "Javobingizni bitta xabarda yozing.\n\n"
        "✍️ <i>Masalan: Murojaatingiz ko‘rib chiqildi...</i>",
        parse_mode=ParseMode.HTML
    )


async def process_admin_reply(update, context):

    appeal_id = context.user_data.get("reply_appeal_id")

    text = update.message.text.strip()

    if not appeal_id:
        return

    if not text:
        await update.message.reply_text(
            "⚠️ Javob matni bo‘sh bo‘lishi mumkin emas."
        )
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
                "💬 <b>REKTORATDAN JAVOB</b>\n\n"
                "━━━━━━━━━━━━━━━━\n"
                f"🆔 <b>Murojaat:</b> #{appeal_id}\n"
                "━━━━━━━━━━━━━━━━\n\n"
                f"{esc(text)}\n\n"
                "Hurmat bilan,\n"
                "<b>Universitet rektorati</b>"
            ),
            parse_mode=ParseMode.HTML
        )

    except Exception as e:

        logger.error(
            f"Talabaga javob yuborishda xato: {e}"
        )

        await update.message.reply_text(
            "⚠️ Javob saqlandi, ammo talabaga "
            "yuborishda texnik xatolik yuz berdi."
        )

        context.user_data.clear()

        return

    context.user_data.clear()

    await update.message.reply_text(
        f"✅ <b>#{appeal_id}</b> murojaatga javob yuborildi.",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_menu()
    )


# =========================================================
# STATUS
# =========================================================

async def change_status(update, context):

    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        return

    parts = query.data.split("_")

    if len(parts) != 3:
        return

    status = parts[1]

    try:
        appeal_id = int(parts[2])
    except ValueError:
        return

    appeal = get_appeal(appeal_id)

    if not appeal:

        await query.message.reply_text(
            "❌ Murojaat topilmadi."
        )

        return

    update_status(
        appeal_id,
        status
    )

    status_text = {

        "process":
            "🔄 <b>Murojaatingiz ko‘rib chiqilmoqda.</b>\n\n"
            "Mas’ul xodimlar murojaatingiz bilan ishlamoqda.",

        "done":
            "✅ <b>Murojaatingiz yakunlandi.</b>\n\n"
            "Murojaatingiz bo‘yicha ko‘rib chiqish jarayoni yakunlandi.",

        "rejected":
            "❌ <b>Murojaatingiz rad etildi.</b>\n\n"
            "Qo‘shimcha ma’lumot olish uchun "
            "universitet mas’ullariga murojaat qilishingiz mumkin.",
    }

    try:

        await context.bot.send_message(
            chat_id=appeal["telegram_id"],
            text=(
                "📢 <b>MUROJAAT HOLATI YANGILANDI</b>\n\n"
                f"🆔 <b>#{appeal_id}</b>\n\n"
                f"{status_text.get(status, 'Holat yangilandi.')}"
            ),
            parse_mode=ParseMode.HTML
        )

    except Exception as e:

        logger.error(
            f"Status yuborishda xato: {e}"
        )

    status_names = {
        "process": "🔄 Jarayonda",
        "done": "✅ Yakunlandi",
        "rejected": "❌ Rad etildi",
    }

    await query.message.reply_text(
        f"✅ <b>#{appeal_id}</b>\n\n"
        f"Yangi holat: "
        f"<b>{status_names.get(status, status)}</b>",
        parse_mode=ParseMode.HTML
    )


# =========================================================
# BACK MAIN
# =========================================================

async def back_main(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data.clear()

    user = get_user(update.effective_user.id)

    if user:

        await query.message.edit_text(
            "🎓 <b>ASOSIY MENYU</b>\n\n"
            "Kerakli bo‘limni tanlang:",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu()
        )

    else:

        await query.message.edit_text(
            "🎓 <b>UNIVERSITET REKTORIGA MUROJAAT BOTI</b>\n\n"
            "Botdan foydalanish uchun ro‘yxatdan o‘ting.",
            parse_mode=ParseMode.HTML,
            reply_markup=start_keyboard()
        )


# =========================================================
# CANCEL
# =========================================================

async def cancel(update, context):

    context.user_data.clear()

    user = get_user(update.effective_user.id)

    if user:

        await update.message.reply_text(
            "↩️ <b>Amal bekor qilindi.</b>\n\n"
            "Asosiy menyudan kerakli bo‘limni tanlang.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu()
        )

    else:

        await update.message.reply_text(
            "↩️ <b>Amal bekor qilindi.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=start_keyboard()
        )


# =========================================================
# ID
# =========================================================

async def my_id(update, context):

    await update.message.reply_text(
        "🆔 <b>Sizning Telegram ID:</b>\n\n"
        f"<code>{update.effective_user.id}</code>",
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

    elif data == "my_profile":
        await my_profile(update, context)

    elif data == "about_bot":
        await about_bot(update, context)

    elif data == "back_main":
        await back_main(update, context)

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

        await process_registration(
            update,
            context
        )

    elif state == "appeal":

        await process_appeal(
            update,
            context
        )

    elif state == "admin_reply":

        if not is_admin(update.effective_user.id):
            return

        await process_admin_reply(
            update,
            context
        )

    else:

        user = get_user(
            update.effective_user.id
        )

        if user:

            await update.message.reply_text(
                "🎓 <b>Asosiy menyu</b>\n\n"
                "Kerakli bo‘limni tanlang:",
                parse_mode=ParseMode.HTML,
                reply_markup=main_menu()
            )

        else:

            await update.message.reply_text(
                "⚠️ Avval ro‘yxatdan o‘ting.",
                reply_markup=start_keyboard()
            )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(update, context):

    logger.error(
        "Botda xatolik:",
        exc_info=context.error
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

    # Commands
    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )

    application.add_handler(
        CommandHandler(
            "cancel",
            cancel
        )
    )

    application.add_handler(
        CommandHandler(
            "id",
            my_id
        )
    )

    # Callback buttons
    application.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    # Text
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )

    # Error
    application.add_error_handler(
        error_handler
    )

    print(
        "🤖 Universitet Rektor Murojaat Boti ishga tushdi..."
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()