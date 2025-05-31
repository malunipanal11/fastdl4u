from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from gofile import upload_to_gofile, get_files_by_type
from aiogram.filters.command import Command

router = Router()
user_states = {}  # Track upload modes


@router.message(Command("start"))
async def start_handler(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🖼 Images", callback_data="img"),
            InlineKeyboardButton(text="🎞 Videos", callback_data="vid"),
            InlineKeyboardButton(text="🎧 Audio", callback_data="aud")
        ],
        [
            InlineKeyboardButton(text="➕ Add File", callback_data="addfile"),
            InlineKeyboardButton(text="🔒 Add Secret", callback_data="addsecret"),
            InlineKeyboardButton(text="🔗 Add Link", callback_data="addlink")
        ]
    ])
    await message.answer("👋 Welcome! Use the menu or send a command.", reply_markup=keyboard)


@router.callback_query(F.data.in_({"img", "vid", "aud"}))
async def category_callback(call: CallbackQuery):
    cat_map = {"img": "images", "vid": "videos", "aud": "audios"}
    category = cat_map[call.data]

    files = get_files_by_type(category)
    if not files:
        await call.message.answer("🚫 No files found.")
    else:
        response = f"📂 *{category.title()}*:\n"
        for f in files:
            response += f"🔗 [{f['name']}]({f['url']})\n"
        await call.message.answer(response, parse_mode="Markdown")


@router.callback_query(F.data.in_({"addfile", "addsecret", "addlink"}))
async def add_callback(call: CallbackQuery):
    user_states[call.from_user.id] = call.data
    prompts = {
        "addfile": "📤 Please send a file to upload.",
        "addsecret": "🔒 Please send the secret you want to store.",
        "addlink": "🔗 Please send the link you want to store."
    }
    await call.message.answer(prompts[call.data])


@router.message(F.content_type.in_({ContentType.DOCUMENT, ContentType.PHOTO, ContentType.VIDEO, ContentType.AUDIO}))
async def handle_media(message: Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if state != "addfile":
        return

    file = message.document or message.video or message.audio or message.photo[-1]
    file_name = getattr(file, "file_name", "uploaded_file.jpg")

    file_data = await message.bot.get_file(file.file_id)
    file_path = file_data.file_path
    file_bytes = await message.bot.download_file(file_path)

    # Detect category
    if message.photo:
        category = "images"
    elif message.video:
        category = "videos"
    elif message.audio:
        category = "audios"
    else:
        category = "files"

    # Upload
    url, file_code = upload_to_gofile(file_bytes, file_name, category)
    await message.answer(f"✅ File uploaded!\n🔗 {url}\n🆔 Code: `{file_code}`", parse_mode="Markdown")

    user_states.pop(user_id, None)
