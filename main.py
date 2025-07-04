import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ContentType
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor 
from datetime import datetime
API_TOKEN = '7427301583:AAHrkHshIQWntJkH74Che4oknQEg1iGXzC8'  # <-- Bu yerga o'zingizning bot tokeningizni yozing

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('malika_admin.db')
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price INTEGER,
            model TEXT,
            made_in TEXT,
            image TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            full_name TEXT,
            username TEXT,
            first_join TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# --- STATES ---
class ProductAdd(StatesGroup):
    name = State()
    price = State()
    model = State()
    made_in = State()
    image = State()

class SearchProduct(StatesGroup):
    query = State()

# --- START BOSILGANDA ISHLIDI! ---
from datetime import datetime  # yuqoriga qo‘shing

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username
    joined_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()

    # Agar user allaqachon bo‘lsa, yangi qo‘shmaydi
    cursor.execute("INSERT OR IGNORE INTO users (telegram_id, full_name, username, first_join) VALUES (?, ?, ?, ?)",
                   (user_id, full_name, username, joined_time))
    conn.commit()
    conn.close()

    await message.answer("🔐Admin Panel:\n/add – Mahsulot qo‘shish\n/products – Mahsulotlar ro‘yxati\n/search – Qidiruv")


# --- ADD MAHSULOT QO'SHISH ---
@dp.message_handler(commands=['add'])
async def add_product(message: types.Message):
    await message.answer("📦 Mahsulot nomini kiriting:")
    await ProductAdd.name.set()

@dp.message_handler(state=ProductAdd.name)
async def add_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("💰 Narxini kiriting:")
    await ProductAdd.price.set()

@dp.message_handler(state=ProductAdd.price)
async def add_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("🔢 Model nomini kiriting:")
    await ProductAdd.model.set()

@dp.message_handler(state=ProductAdd.model)
async def add_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("🌍 Qayerda ishlab chiqarilganini kiriting:")
    await ProductAdd.made_in.set()

@dp.message_handler(state=ProductAdd.made_in)
async def add_madein(message: types.Message, state: FSMContext):
    await state.update_data(made_in=message.text)
    await message.answer("🖼 Rasm yuboring:")
    await ProductAdd.image.set()

@dp.message_handler(content_types=ContentType.PHOTO, state=ProductAdd.image)
async def add_image(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id

    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, price, model, made_in, image) VALUES (?, ?, ?, ?, ?)",
                   (data['name'], data['price'], data['model'], data['made_in'], photo_id))
    conn.commit()
    conn.close()

    await message.answer("✅ Mahsulot qo‘shildi!")
    await state.finish()

# --- SHOW PRODUCTS MAHSULOT KO'RISH ---
@dp.message_handler(commands=['products'])
async def show_products(message: types.Message):
    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM products")
    products = cursor.fetchall()
    conn.close()

    if not products:
        await message.answer("❌ Mahsulot yo‘q.")
        return

    kb = InlineKeyboardMarkup()
    for pid, name in products:
        kb.add(InlineKeyboardButton(text=name, callback_data=f"view_{pid}"))
    await message.answer("🗂 Mahsulotlar ro‘yxati:", reply_markup=kb)

# --- VIEW PRODUCT ---
@dp.callback_query_handler(lambda c: c.data.startswith("view_"))
async def view_product(call: types.CallbackQuery):
    pid = int(call.data.split("_")[1])
    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, model, made_in, image FROM products WHERE id=?", (pid,))
    product = cursor.fetchone()
    conn.close()

    if product:
        name, price, model, made_in, image = product
        await bot.send_photo(call.from_user.id, image,
            caption=f"📦 {name}\n💰 Narx: {price} so‘m\n🔢 Model: {model}\n🌍 Ishlab chiqarilgan: {made_in}")
    else:
        await call.message.answer("❌ Mahsulot topilmadi.")

# --- SEARCH COMMAND ---
@dp.message_handler(commands=['search'])
async def search_start(message: types.Message):
    await message.answer("🔍 Qidiruv uchun model yoki nomni kiriting:")
    await SearchProduct.query.set()

@dp.message_handler(state=SearchProduct.query)
async def search_product(message: types.Message, state: FSMContext):
    query = message.text
    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM products WHERE name LIKE ? OR model LIKE ?", (f'%{query}%', f'%{query}%'))
    results = cursor.fetchall()
    conn.close()

    if results:
        kb = InlineKeyboardMarkup()
        for pid, name in results:
            kb.add(InlineKeyboardButton(text=name, callback_data=f"view_{pid}"))
        await message.answer("🔎 Natijalar:", reply_markup=kb)
    else:
        await message.answer("❌ Hech narsa topilmadi.")
    await state.finish()

# --- RUN ---
if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
