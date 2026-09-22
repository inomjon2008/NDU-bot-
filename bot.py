import os
import sqlite3
import logging
from datetime import datetime

from dotenv import load_dotenv

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


# =========================================================
# SOZLAMALAR
# =========================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [
    7267416938,
    1058849364,
]

DB_NAME = "rektor_bot.db"


if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN .env faylda topilmadi!"
    )


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
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


def now():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # USERS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            course TEXT NOT NULL,
            faculty TEXT NOT NULL,
            group_name TEXT NOT NULL,
            phone TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # APPEALS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appeals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            appeal_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Yangi',
            admin_reply TEXT,
            media_type TEXT,
            media_file_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # USERS jadvali ustunlarini tekshirish
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "phone" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN phone TEXT"
        )

    if "created_at" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN created_at TEXT"
        )

    if "updated_at" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN updated_at TEXT"
        )

    # APPEALS jadvali ustunlarini tekshirish
    cursor.execute("PRAGMA table_info(appeals)")
    appeal_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "appeal_text" not in appeal_columns:
        cursor.execute(
            "ALTER TABLE appeals ADD COLUMN appeal_text TEXT"
        )

    if "status" not in appeal_columns:
        cursor.execute(
            "ALTER TABLE appeals ADD COLUMN status TEXT DEFAULT 'Yangi'"
        )

    if "admin_reply" not in appeal_columns:
        cursor.execute(
            "ALTER TABLE appeals ADD COLUMN admin_reply TEXT"
        )

    if "media_type" not in appeal_columns:
        cursor.execute(
            "ALTER TABLE appeals ADD COLUMN media_type TEXT"
        )

    if "media_file_id" not in appeal_columns:
        cursor.execute(
            "ALTER TABLE appeals ADD COLUMN media_file_id TEXT"
        )

    if "created_at" not in appeal_columns:
        cursor.execute(
            "ALTER TABLE appeals ADD COLUMN created_at TEXT"
        )

    if "updated_at" not in appeal_columns:
        cursor.execute(
            "ALTER TABLE appeals ADD COLUMN updated_at TEXT"
        )

    conn.commit()
    conn.close()


# =========================================================
# YORDAMCHI FUNKSIYALAR
# =========================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def get_user(telegram_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    user = cursor.fetchone()

    conn.close()

    return user


def get_appeal(appeal_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM appeals
        WHERE id = ?
        """,
        (appeal_id,),
    )

    appeal = cursor.fetchone()

    conn.close()

    return appeal


# =========================================================
# KEYBOARDS
# =========================================================

def start_registration_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["📝 Ro‘yxatdan o‘tish"],
        ],
        resize_keyboard=True,
    )


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["📝 Murojaat yuborish"],
        ],
        resize_keyboard=True,
    )


def course_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["1-kurs", "2-kurs"],
            ["3-kurs", "4-kurs"],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def faculty_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["Aniq fanlar fakulteti"],
            ["Iqtisodiyot fakulteti"],
            ["Maktabgacha va boshlang‘ich ta’lim fakulteti"],
            ["San’at va sport fakulteti"],
            ["Tabiiy fanlar va tibbiyot fakulteti"],
            ["Tarix fakulteti"],
            ["Tillar fakulteti"],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def phone_keyboard():
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    "📱 Telefon raqamimni yuborish",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def media_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["✅ Ha, ilova qilaman"],
            ["❌ Yo‘q, ilova qilmayman"],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def cancel_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["❌ Bekor qilish"],
        ],
        resize_keyboard=True,
    )


def admin_appeal_keyboard(appeal_id: int):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💬 Javob berish",
                    callback_data=f"reply:{appeal_id}",
                )
            ]
        ]
    )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user
    user_id = user.id

    context.user_data.clear()

    # =====================================================
    # ADMIN
    # =====================================================

    if is_admin(user_id):

        await update.message.reply_text(
            "✅ NAVOIY DAVLAT UNIVERSITETI\n"
            "REKTORGA MUROJAAT BOTI\n\n"
            "Siz admin sifatida tizimga kirdingiz.\n\n"
            "📩 Yangi murojaatlar shu chatga keladi.\n"
            "💬 Murojaatga javob berish uchun "
            "«Javob berish» tugmasidan foydalaning."
        )

        return

    # =====================================================
    # FOYDALANUVCHI
    # =====================================================

    existing_user = get_user(user_id)

    if existing_user:

        await update.message.reply_text(
            "Assalomu alaykum! 👋\n\n"
            "Ushbu bot orqali Navoiy davlat universiteti "
            "rektoriga savol, murojaat, muammo, taklif va "
            "tashabbuslaringizni bevosita yuborishingiz mumkin.\n\n"
            "📌 Murojaat yuborish uchun quyidagi tugmani bosing.",
            reply_markup=main_menu_keyboard(),
        )

        return

    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "Ushbu bot orqali Navoiy davlat universiteti rektoriga "
        "*savol, murojaat, muammo, taklif va tashabbuslaringizni* "
        "bevosita yuborishingiz mumkin.\n\n"
        "📌 Murojaat yuborish uchun qisqa ro‘yxatdan o‘ting.\n\n"
        "Taqdim etilgan ma’lumotlardan murojaatingizni ko‘rib "
        "chiqish va zarur hollarda Siz bilan bog‘lanish "
        "maqsadida foydalaniladi.",
        parse_mode="Markdown",
        reply_markup=start_registration_keyboard(),
    )


# =========================================================
# REGISTRATION START
# =========================================================

async def start_registration(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    context.user_data.clear()

    context.user_data["registration"] = True
    context.user_data["registration_step"] = "full_name"

    await update.message.reply_text(
        "📝 *RO‘YXATDAN O‘TISH*\n\n"
        "Iltimos, F.I.Sh.ingizni to‘liq kiriting.\n\n"
        "Masalan:\n"
        "`Aliyev Ali Valiyevich`",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


# =========================================================
# REGISTRATION TEXT
# =========================================================

async def registration_text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = update.message.text.strip()

    if text == "❌ Bekor qilish":

        context.user_data.clear()

        await update.message.reply_text(
            "❌ Ro‘yxatdan o‘tish bekor qilindi.",
            reply_markup=start_registration_keyboard(),
        )

        return

    step = context.user_data.get(
        "registration_step"
    )

    # F.I.SH.
    if step == "full_name":

        if len(text) < 3:

            await update.message.reply_text(
                "❗️ Iltimos, F.I.Sh.ingizni to‘liq kiriting."
            )

            return

        context.user_data["full_name"] = text
        context.user_data["registration_step"] = "course"

        await update.message.reply_text(
            "🎓 *Iltimos, kursingizni tanlang:*",
            parse_mode="Markdown",
            reply_markup=course_keyboard(),
        )

        return

    # KURS
    if step == "course":

        courses = [
            "1-kurs",
            "2-kurs",
            "3-kurs",
            "4-kurs",
        ]

        if text not in courses:

            await update.message.reply_text(
                "❗️ Iltimos, kursingizni tugma orqali tanlang.",
                reply_markup=course_keyboard(),
            )

            return

        context.user_data["course"] = text
        context.user_data["registration_step"] = "faculty"

        await update.message.reply_text(
            "🏛 *Iltimos, fakultetingizni tanlang:*",
            parse_mode="Markdown",
            reply_markup=faculty_keyboard(),
        )

        return

    # FAKULTET
    if step == "faculty":

        faculties = [
            "Aniq fanlar fakulteti",
            "Iqtisodiyot fakulteti",
            "Maktabgacha va boshlang‘ich ta’lim fakulteti",
            "San’at va sport fakulteti",
            "Tabiiy fanlar va tibbiyot fakulteti",
            "Tarix fakulteti",
            "Tillar fakulteti",
        ]

        if text not in faculties:

            await update.message.reply_text(
                "❗️ Iltimos, fakultetingizni tugma orqali tanlang.",
                reply_markup=faculty_keyboard(),
            )

            return

        context.user_data["faculty"] = text
        context.user_data["registration_step"] = "group"

        await update.message.reply_text(
            "👥 *Iltimos, guruhingizni kiriting.*\n\n"
            "Masalan: `KX-24-01`",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )

        return

    # GURUH
    if step == "group":

        if len(text) < 2:

            await update.message.reply_text(
                "❗️ Iltimos, guruhingizni to‘g‘ri kiriting."
            )

            return

        context.user_data["group_name"] = text
        context.user_data["registration_step"] = "phone"

        await update.message.reply_text(
            "📱 *Telefon raqamingizni yuboring.*\n\n"
            "Quyidagi tugmani bosib, telefon raqamingizni "
            "yuborishingiz mumkin:",
            parse_mode="Markdown",
            reply_markup=phone_keyboard(),
        )

        return


# =========================================================
# CONTACT
# =========================================================

async def contact_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.user_data.get("registration"):
        return

    contact = update.message.contact

    if not contact:
        return

    if contact.user_id != update.effective_user.id:

        await update.message.reply_text(
            "❗️ Iltimos, o‘zingizning telefon raqamingizni yuboring."
        )

        return

    full_name = context.user_data.get("full_name")
    course = context.user_data.get("course")
    faculty = context.user_data.get("faculty")
    group_name = context.user_data.get("group_name")

    phone = contact.phone_number

    if not all(
        [
            full_name,
            course,
            faculty,
            group_name,
        ]
    ):

        context.user_data.clear()

        await update.message.reply_text(
            "❗️ Ma’lumotlarda xatolik yuz berdi.\n\n"
            "Iltimos, /start orqali qaytadan boshlang.",
            reply_markup=start_registration_keyboard(),
        )

        return

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO users (
            telegram_id,
            full_name,
            course,
            faculty,
            group_name,
            phone,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            update.effective_user.id,
            full_name,
            course,
            faculty,
            group_name,
            phone,
            now(),
            now(),
        ),
    )

    conn.commit()
    conn.close()

    context.user_data.clear()

    await update.message.reply_text(
        "✅ *RO‘YXATDAN O‘TISH MUVAFFAQIYATLI YAKUNLANDI!*\n\n"
        f"👤 F.I.Sh.: {full_name}\n"
        f"🎓 Kurs: {course}\n"
        f"🏛 Fakultet: {faculty}\n"
        f"👥 Guruh: {group_name}\n"
        f"📱 Telefon: {phone}\n\n"
        "Endi Siz rektorga murojaat yuborishingiz mumkin.",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


# =========================================================
# APPEAL START
# =========================================================

async def start_appeal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = get_user(update.effective_user.id)

    if not user:

        await update.message.reply_text(
            "❗️ Murojaat yuborishdan avval, "
            "iltimos, ro‘yxatdan o‘ting.",
            reply_markup=start_registration_keyboard(),
        )

        return

    context.user_data.clear()

    context.user_data["appeal"] = True
    context.user_data["appeal_step"] = "text"

    await update.message.reply_text(
        "📝 *MUROJAAT YUBORISH*\n\n"
        "Hurmatli foydalanuvchi!\n\n"
        "Murojaatingiz mazmunini imkon qadar "
        "*batafsil va aniq* bayon qiling.\n\n"
        "💡 Siz o‘z murojaatingizda:\n"
        "• muammo yoki masalani;\n"
        "• taklif va tashabbuslaringizni;\n"
        "• savol yoki boshqa murojaatlaringizni yozishingiz mumkin.\n\n"
        "📎 Zarur bo‘lsa, murojaatingizga tegishli "
        "*foto, video yoki hujjatlarni* ham ilova qilishingiz mumkin.\n\n"
        "✍️ Iltimos, murojaatingizni quyidagi xabarda yuboring.",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


# =========================================================
# APPEAL TEXT
# =========================================================

async def appeal_text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = update.message.text.strip()

    if text == "❌ Bekor qilish":

        context.user_data.clear()

        await update.message.reply_text(
            "❌ Murojaat yuborish bekor qilindi.",
            reply_markup=main_menu_keyboard(),
        )

        return

    if context.user_data.get("appeal_step") != "text":
        return

    if len(text) < 5:

        await update.message.reply_text(
            "❗️ Iltimos, murojaatingizni batafsilroq yozing."
        )

        return

    context.user_data["appeal_text"] = text
    context.user_data["appeal_step"] = "media"

    await update.message.reply_text(
        "📎 *Murojaatingizga foto, video yoki hujjat "
        "ilova qilasizmi?*",
        parse_mode="Markdown",
        reply_markup=media_keyboard(),
    )


# =========================================================
# MEDIA QUESTION
# =========================================================

async def media_question_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = update.message.text.strip()

    if text == "❌ Bekor qilish":

        context.user_data.clear()

        await update.message.reply_text(
            "❌ Murojaat yuborish bekor qilindi.",
            reply_markup=main_menu_keyboard(),
        )

        return

    if context.user_data.get("appeal_step") != "media":
        return

    # MEDIA YO‘Q
    if text == "❌ Yo‘q, ilova qilmayman":

        await create_and_send_appeal(
            update,
            context,
            media_type=None,
            media_file_id=None,
        )

        return

    # MEDIA BOR
    if text == "✅ Ha, ilova qilaman":

        context.user_data["appeal_step"] = "waiting_media"

        await update.message.reply_text(
            "📎 *Iltimos, endi foto, video yoki hujjatni yuboring.*\n\n"
            "Kerakli faylni shu yerga yuborishingiz mumkin.",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )

        return

    await update.message.reply_text(
        "❗️ Iltimos, quyidagi tugmalardan birini tanlang.",
        reply_markup=media_keyboard(),
    )


# =========================================================
# CREATE AND SEND APPEAL
# =========================================================

async def create_and_send_appeal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    media_type=None,
    media_file_id=None,
):

    user_id = update.effective_user.id

    user = get_user(user_id)

    if not user:

        context.user_data.clear()

        await update.message.reply_text(
            "❗️ Iltimos, avval ro‘yxatdan o‘ting.",
            reply_markup=start_registration_keyboard(),
        )

        return

    appeal_text = context.user_data.get(
        "appeal_text"
    )

    if not appeal_text:

        context.user_data.clear()

        await update.message.reply_text(
            "❗️ Murojaat topilmadi.\n\n"
            "Iltimos, qaytadan urinib ko‘ring.",
            reply_markup=main_menu_keyboard(),
        )

        return

    # =====================================================
    # DATABASE
    # =====================================================

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO appeals (
            telegram_id,
            appeal_text,
            status,
            admin_reply,
            media_type,
            media_file_id,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            appeal_text,
            "Yangi",
            None,
            media_type,
            media_file_id,
            now(),
            now(),
        ),
    )

    appeal_id = cursor.lastrowid

    conn.commit()
    conn.close()

    # =====================================================
    # ADMIN XABARI
    # =====================================================

    admin_text = (
        "🔔 YANGI MUROJAAT\n\n"
        f"🆔 Murojaat: #{appeal_id}\n\n"
        f"👤 F.I.Sh.: {user['full_name']}\n"
        f"📱 Telefon: {user['phone'] or 'Ko‘rsatilmagan'}\n"
        f"🎓 Kurs: {user['course']}\n"
        f"🏛 Fakultet: {user['faculty']}\n"
        f"👥 Guruh: {user['group_name']}\n\n"
        "📝 MUROJAAT:\n"
        f"{appeal_text}\n\n"
        "👇 Talabaga javob berish uchun "
        "«Javob berish» tugmasini bosing."
    )

    success_count = 0

    # =====================================================
    # IKKALA ADMIN
    # =====================================================

    for admin_id in ADMIN_IDS:

        try:

            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=admin_appeal_keyboard(
                    appeal_id
                ),
            )

            # FOTO
            if (
                media_type == "photo"
                and media_file_id
            ):

                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=media_file_id,
                    caption=(
                        f"📎 Murojaat #{appeal_id} "
                        "ilovasi"
                    ),
                )

            # VIDEO
            elif (
                media_type == "video"
                and media_file_id
            ):

                await context.bot.send_video(
                    chat_id=admin_id,
                    video=media_file_id,
                    caption=(
                        f"📎 Murojaat #{appeal_id} "
                        "ilovasi"
                    ),
                )

            # DOCUMENT
            elif (
                media_type == "document"
                and media_file_id
            ):

                await context.bot.send_document(
                    chat_id=admin_id,
                    document=media_file_id,
                    caption=(
                        f"📎 Murojaat #{appeal_id} "
                        "ilovasi"
                    ),
                )

            success_count += 1

        except Exception as e:

            logger.error(
                f"Admin {admin_id} ga yuborishda "
                f"xatolik: {e}"
            )

    # =====================================================
    # FOYDALANUVCHIGA TASDIQ
    # =====================================================

    context.user_data.clear()

    if success_count > 0:

        await update.message.reply_text(
            "☑️ *MUROJAATINGIZ QABUL QILINDI!*\n\n"
            "Hurmatli talaba, murojaatingiz muvaffaqiyatli "
            "qabul qilindi va *o‘rganib chiqish uchun tegishli "
            "mas’ullarga yo‘naltirildi.*\n\n"
            "🔎 Murojaatingiz belgilangan tartibda o‘rganib "
            "chiqiladi va natijasi bo‘yicha Sizga ushbu bot "
            "orqali ma’lumot beriladi.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

    else:

        await update.message.reply_text(
            "⚠️ Murojaatingiz saqlandi, ammo hozircha "
            "tegishli mas’ullarga yuborishda texnik muammo "
            "yuz berdi.\n\n"
            "Iltimos, birozdan so‘ng qayta urinib ko‘ring.",
            reply_markup=main_menu_keyboard(),
        )


# =========================================================
# PHOTO
# =========================================================

async def photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if context.user_data.get("appeal_step") != "waiting_media":
        return

    photo = update.message.photo[-1]

    await create_and_send_appeal(
        update,
        context,
        media_type="photo",
        media_file_id=photo.file_id,
    )


# =========================================================
# VIDEO
# =========================================================

async def video_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if context.user_data.get("appeal_step") != "waiting_media":
        return

    video = update.message.video

    await create_and_send_appeal(
        update,
        context,
        media_type="video",
        media_file_id=video.file_id,
    )


# =========================================================
# DOCUMENT
# =========================================================

async def document_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if context.user_data.get("appeal_step") != "waiting_media":
        return

    document = update.message.document

    await create_and_send_appeal(
        update,
        context,
        media_type="document",
        media_file_id=document.file_id,
    )


# =========================================================
# ADMIN CALLBACK
# =========================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):

        await query.answer(
            "❌ Sizda ruxsat yo‘q.",
            show_alert=True,
        )

        return

    await query.answer()

    data = query.data

    if data.startswith("reply:"):

        try:

            appeal_id = int(
                data.split(":")[1]
            )

        except (
            ValueError,
            IndexError,
        ):

            await query.message.reply_text(
                "❌ Murojaat ID noto‘g‘ri."
            )

            return

        appeal = get_appeal(appeal_id)

        if not appeal:

            await query.message.reply_text(
                "❌ Murojaat topilmadi."
            )

            return

        context.user_data["admin_reply"] = True
        context.user_data["reply_appeal_id"] = appeal_id

        await query.message.reply_text(
            f"💬 Murojaat #{appeal_id}\n\n"
            "Iltimos, talabaga yubormoqchi bo‘lgan "
            "javobingizni yozing.",
            reply_markup=ReplyKeyboardMarkup(
                [
                    ["❌ Bekor qilish"]
                ],
                resize_keyboard=True,
            ),
        )


# =========================================================
# ADMIN REPLY
# =========================================================

async def admin_reply_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_admin(
        update.effective_user.id
    ):
        return

    if not context.user_data.get("admin_reply"):
        return

    text = update.message.text.strip()

    if text == "❌ Bekor qilish":

        context.user_data.clear()

        await update.message.reply_text(
            "❌ Javob berish bekor qilindi."
        )

        return

    appeal_id = context.user_data.get(
        "reply_appeal_id"
    )

    if not appeal_id:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ Murojaat topilmadi."
        )

        return

    appeal = get_appeal(appeal_id)

    if not appeal:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ Murojaat topilmadi."
        )

        return

    student_id = appeal["telegram_id"]

    try:

        await context.bot.send_message(
            chat_id=student_id,
            text=(
                "💬 MUROJAATINGIZ BO‘YICHA JAVOB\n\n"
                f"{text}"
            ),
            reply_markup=main_menu_keyboard(),
        )

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE appeals
            SET admin_reply = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                text,
                "Javob berildi",
                now(),
                appeal_id,
            ),
        )

        conn.commit()
        conn.close()

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ Javob murojaat #{appeal_id} "
            "egasiga muvaffaqiyatli yuborildi."
        )

    except Exception as e:

        logger.error(
            f"Talabaga javob yuborishda xatolik: {e}"
        )

        await update.message.reply_text(
            "❌ Javob yuborilmadi.\n\n"
            "Foydalanuvchi botni /start orqali ishga "
            "tushirganini tekshiring."
        )


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = update.message.text.strip()
    user_id = update.effective_user.id

    # =====================================================
    # ADMIN JAVOBI
    # =====================================================

    if (
        is_admin(user_id)
        and context.user_data.get("admin_reply")
    ):

        await admin_reply_handler(
            update,
            context,
        )

        return

    # =====================================================
    # ADMIN
    # =====================================================

    if is_admin(user_id):
        return

    # =====================================================
    # REGISTRATION
    # =====================================================

    if context.user_data.get("registration"):

        await registration_text_handler(
            update,
            context,
        )

        return

    # =====================================================
    # APPEAL
    # =====================================================

    if context.user_data.get("appeal"):

        step = context.user_data.get(
            "appeal_step"
        )

        if step == "text":

            await appeal_text_handler(
                update,
                context,
            )

            return

        if step == "media":

            await media_question_handler(
                update,
                context,
            )

            return

        if step == "waiting_media":

            await update.message.reply_text(
                "📎 Iltimos, foto, video yoki hujjatni yuboring."
            )

            return

    # =====================================================
    # MENU
    # =====================================================

    if text == "📝 Ro‘yxatdan o‘tish":

        await start_registration(
            update,
            context,
        )

        return

    if text == "📝 Murojaat yuborish":

        await start_appeal(
            update,
            context,
        )

        return

    # =====================================================
    # DEFAULT
    # =====================================================

    user = get_user(user_id)

    if user:

        await update.message.reply_text(
            "Kerakli bo‘limni tanlang:",
            reply_markup=main_menu_keyboard(),
        )

    else:

        await update.message.reply_text(
            "Iltimos, avval ro‘yxatdan o‘ting.",
            reply_markup=start_registration_keyboard(),
        )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Botda xatolik:",
        exc_info=context.error,
    )


# =========================================================
# MAIN
# =========================================================

def main():

    init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # /start
    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # ADMIN INLINE BUTTON
    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    # CONTACT
    application.add_handler(
        MessageHandler(
            filters.CONTACT,
            contact_handler,
        )
    )

    # PHOTO
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_handler,
        )
    )

    # VIDEO
    application.add_handler(
        MessageHandler(
            filters.VIDEO,
            video_handler,
        )
    )

    # DOCUMENT
    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            document_handler,
        )
    )

    # TEXT
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router,
        )
    )

    # ERROR
    application.add_error_handler(
        error_handler
    )

    logger.info(
        "========================================"
    )
    logger.info(
        "NAVOIY DAVLAT UNIVERSITETI"
    )
    logger.info(
        "REKTORGA MUROJAAT BOTI ISHLAMOQDA"
    )
    logger.info(
        "========================================"
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":
    main()