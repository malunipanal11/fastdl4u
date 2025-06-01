from aiogram import Router, types
from aiogram.types import FSInputFile
from io import BytesIO
from utils import user_categories, upload_to_gofile

router = Router()


@router.message(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer("👋 Welcome! Use /add <category> and then send me files.")


@router.message(commands=["add"])
async def cmd_add(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❗ Usage: /add <category>")
        return

    category = args[1]
    user_categories[message.from_user.id] = category
    await message.reply(f"📁 Now send files to add in category: {category}")


@router.message()
async def handle_files(message: types.Message):
    user_id = message.from_user.id
    category = user_categories.get(user_id)

    if not category:
        await message.reply("❗ Use /add <category> before sending files.")
        return

    file_info = None
    filename = None
    file_bytes = BytesIO()

    if message.document:
        file_info = message.document
        filename = file_info.file_name
    elif message.photo:
        file_info = message.photo[-1]
        filename = f"photo_{file_info.file_id}.jpg"
    else:
        await message.reply("❗ Unsupported file type.")
        return

    try:
        tg_file = await message.bot.get_file(file_info.file_id)
        file = await message.bot.download_file(tg_file.file_path)
        file_bytes.write(file.read())

        result = upload_to_gofile(file_bytes, filename, category)

        if result["success"]:
            await message.reply(f"✅ Uploaded: {result['data']['url']}")
        else:
            await message.reply(f"❌ Upload failed: {result['message']}")
    except Exception as e:
        await message.reply("❌ Error during file processing.")
