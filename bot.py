import logging
import os
import json
import csv
import re
import zipfile
import io
from io import StringIO
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()  # загружает переменные из .env

# Импорты из telegram
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from telegram.request import HTTPXRequest

# Если используете какие-то дополнительные модули, добавьте их ниже
# ... остальные импорты (telegram и т.д.)  # загружает переменные из файла .env
# ========== Настройка логирования ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# ========== Константы ==========
# Константы файлов
INGREDIENTS_FILE = "ingredients.json"
RECIPES_FILE = "recipes.json"
SETTINGS_FILE = "settings.json"
SALES_FILE = "sales.json"
PLANS_FILE = "plans.json"
CUSTOMERS_FILE = "customers.json"
ORDERS_FILE = "orders.json"

def load_data(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
# Глобальные переменные
ingredients = {}
recipes = {}
settings = {}
sales = []
plans = []
customers = {}
orders = []
# Состояния для диалога импорта рецепта
WAITING_RECIPE_TEXT, WAITING_INGREDIENT_PRICE, WAITING_RECIPE_NAME, WAITING_RECIPE_TYPE = range(4)
# ========== Глобальные переменные ==========
ingredients = {}
recipes = {}
settings = {}  # для хранения почасовой ставки и др.
plans = []  # глобальный список планов
sales = []  # глобальный список продаж
customers = {}
orders = []
# ========== Функции для работы с файлами ==========
def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except:
            settings = {}
    else:
        settings = {}
    if 'hourly_rate' not in settings:
        settings['hourly_rate'] = 0.0
        save_settings()

def save_settings():
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def load_sales():
    global sales
    if os.path.exists(SALES_FILE):
        try:
            with open(SALES_FILE, 'r', encoding='utf-8') as f:
                sales = json.load(f)
        except:
            sales = []
    else:
        sales = []

def save_sales():
    with open(SALES_FILE, 'w', encoding='utf-8') as f:
        json.dump(sales, f, ensure_ascii=False, indent=2)

def load_plans():
    global plans
    if os.path.exists(PLANS_FILE):
        try:
            with open(PLANS_FILE, 'r', encoding='utf-8') as f:
                plans = json.load(f)
        except:
            plans = []
    else:
        plans = []

def save_plans():
    with open(PLANS_FILE, 'w', encoding='utf-8') as f:
        json.dump(plans, f, ensure_ascii=False, indent=2)

def load_customers():
    global customers
    if os.path.exists(CUSTOMERS_FILE):
        try:
            with open(CUSTOMERS_FILE, 'r', encoding='utf-8') as f:
                customers = json.load(f)
        except:
            customers = {}
    else:
        customers = {}

def save_customers():
    with open(CUSTOMERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(customers, f, ensure_ascii=False, indent=2)

def load_orders():
    global orders
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                orders = json.load(f)
        except:
            orders = []
    else:
        orders = []

def save_orders():
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)
# ========== Меню с кнопками ==========


def get_main_keyboard():
    keyboard = [
        [KeyboardButton("➕ Добавить ингредиент")],
        [KeyboardButton("📋 Список ингредиентов")],
        [KeyboardButton("🍰 Добавить рецепт")],
        [KeyboardButton("💰 Рассчитать себестоимость")],
        [KeyboardButton("📖 Мои рецепты")],
        [KeyboardButton("⚖️ Пересчитать рецепт")],
        [KeyboardButton("📦 Остатки")],
        [KeyboardButton("🛒 Список покупок")],   # <-- новая кнопка
        [KeyboardButton("📊 Аналитика")],
        [KeyboardButton("📅 Заказы")],
        [KeyboardButton("❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, first_time=False):
    """Показывает главное меню с reply-кнопками"""
    if update.message:
        if first_time:
            user = update.effective_user
            name = user.first_name or "друг"
            greeting = f"👋 Привет, {name}! Я помогу управлять кондитерским производством.\nЧто будем делать?"
            await update.message.reply_text(greeting, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    elif update.callback_query:
        # Если вызов из Inline-кнопки (старые), то отправляем новое сообщение с клавиатурой
        await update.callback_query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "➕ Добавить ингредиент":
        await update.message.reply_text(
            "Чтобы добавить ингредиент, отправьте команду:\n"
            "/add_ingredient название цена единица\n"
            "Или с ценой за упаковку: /add_ingredient название цена_упаковки вес_упаковки единица\n\n"
            "Допустимые единицы: кг, г, шт, л, мл"
        )
        return
    elif text == "📋 Список ингредиентов":
        await show_ingredients(update, context)
        return
    elif text == "🍰 Добавить рецепт":
        await update.message.reply_text(
            "Чтобы добавить рецепт, отправьте:\n"
            "/add_recipe Название: порции; ингредиенты (старый формат)\n"
            "или /add_recipe2 название тип базовое_количество: ингредиенты (для масштабирования)\n\n"
            "Примеры:\n"
            "/add_recipe Омлет: 2; яйца 3, молоко 0.1\n"
            "/add_recipe2 торт вес 1: мука 0.5, сахар 0.2, яйца 3"
        )
        return
    elif text == "💰 Рассчитать себестоимость":
        await update.message.reply_text(
            "Введите название десерта для расчёта:\n"
            "/calculate название\n"
            "Например: /calculate омлет"
        )
        return
    elif text == "📖 Мои рецепты":
        await list_recipes(update, context)
        return
    elif text == "⚖️ Пересчитать рецепт":
        await update.message.reply_text(
            "Чтобы пересчитать рецепт на нужный вес/количество:\n"
            "/scale название новое_количество [единица]\n\n"
            "Примеры:\n"
            "/scale торт 2.5 кг\n"
            "/scale печенье 30 шт"
        )
        return
    elif text == "📦 Остатки":
        await show_stock(update, context)
        return
    elif text == "🛒 Список покупок":
        await shopping_list(update, context)
        return
    elif text == "📊 Аналитика":
        await stats(update, context)  # вызовет stats без аргументов → период "месяц"
        return
    elif text == "📅 Заказы":
        await list_orders(update, context)
        return
    elif text == "❓ Помощь":
        await help_command(update, context)
        return
    else:
        # Если текст не кнопка, просто выходим, чтобы сработал echo
        return
async def show_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ingredients:
        await update.message.reply_text("Список ингредиентов пуст")
        return
    msg = "📦 Текущие остатки:\n"
    for name in sorted(ingredients.keys()):
        data = ingredients[name]
        stock = data.get('stock', 0.0)
        unit = data['unit']
        line = f"• {name}: {stock:.2f} {unit}\n"
        if len(msg) + len(line) > 4000:
            await update.message.reply_text(msg)
            msg = "📦 Продолжение остатков:\n"
        msg += line
    await update.message.reply_text(msg)
async def use_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Списать ингредиенты на приготовление: /use рецепт [количество]"""
    if len(context.args) < 1:
        await update.message.reply_text("Формат: /use название_рецепта [количество]\nПример: /use тест_омлет 2")
        return
    args = context.args
    if len(args) == 1:
        name = args[0].lower()
        qty = 1
    else:
        *name_parts, qty_str = args
        name = ' '.join(name_parts).lower()
        try:
            qty = float(qty_str.replace(',', '.'))
        except ValueError:
            await update.message.reply_text("Ошибка! Количество должно быть числом")
            return

    if name not in recipes:
        await update.message.reply_text(f"Рецепт '{name}' не найден")
        return

    data = recipes[name]
    # Получаем ингредиенты
    if isinstance(data, dict) and "ingredients" in data:
        ing_dict = data["ingredients"]
    else:
        ing_dict = data

    # Масштабируем на нужное количество
    needed = {}
    for ing_name, ing_qty in ing_dict.items():
        needed[ing_name] = ing_qty * qty

    # Проверяем наличие остатков
    missing = []
    for ing_name, need_qty in needed.items():
        if ing_name not in ingredients:
            missing.append(ing_name)
        else:
            stock = ingredients[ing_name].get('stock', 0.0)
            if stock < need_qty:
                missing.append(f"{ing_name} (нужно {need_qty:.2f}, есть {stock:.2f})")

    if missing:
        await update.message.reply_text(f"❌ Недостаточно ингредиентов:\n" + "\n".join(missing))
        return

    # Списание
    for ing_name, need_qty in needed.items():
        ingredients[ing_name]['stock'] -= need_qty
    save_data(ingredients, INGREDIENTS_FILE)

    # Расчёт себестоимости
    total_ing = 0.0
    for ing_name, need_qty in needed.items():
        total_ing += ingredients[ing_name]['price'] * need_qty

    # Дополнительные расходы
    packaging = data.get('packaging', 0.0) if isinstance(data, dict) else 0.0
    work_hours = data.get('work_hours', 0.0) if isinstance(data, dict) else 0.0
    hourly_rate = settings.get('hourly_rate', 0.0)
    work_cost = work_hours * hourly_rate * qty if work_hours and hourly_rate else 0.0
    markup = data.get('markup') if isinstance(data, dict) else None

    total_cost = total_ing + packaging * qty + work_cost
    if markup is not None:
        price_sale = total_cost * (1 + markup / 100)
        profit = price_sale - total_cost
    else:
        price_sale = None
        profit = None

    # Запись о продаже
    sale_record = {
        "date": datetime.now().isoformat(),
        "recipe": name,
        "quantity": qty,
        "cost": total_ing,                # себестоимость ингредиентов
        "cost_with_extras": total_cost,    # полная себестоимость
        "price": price_sale,               # цена продажи
        "profit": profit
    }
    sales.append(sale_record)
    save_sales()

    # Ответ пользователю
    msg = f"✅ Приготовлено {qty} шт '{name}'. Ингредиенты списаны.\n"
    msg += f"💰 Себестоимость ингредиентов: {total_ing:.2f} руб\n"
    if packaging or work_cost:
        msg += f"🧾 Полная себестоимость: {total_cost:.2f} руб\n"
    if price_sale:
        msg += f"💵 Цена продажи: {price_sale:.2f} руб\n"
        msg += f"💸 Прибыль: {profit:.2f} руб"
    await update.message.reply_text(msg)
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика продаж: /stats [день|неделя|месяц|год]"""
    try:
        period = context.args[0].lower() if context.args else "месяц"
        now = datetime.now()
        if period == "день":
            start = now - timedelta(days=1)
        elif period == "неделя":
            start = now - timedelta(weeks=1)
        elif period == "месяц":
            start = now - timedelta(days=30)
        elif period == "год":
            start = now - timedelta(days=365)
        else:
            await update.message.reply_text("Период может быть: день, неделя, месяц, год")
            return

        total_revenue = 0.0
        total_cost = 0.0
        total_profit = 0.0
        count = 0

        for sale in sales:
            sale_date = datetime.fromisoformat(sale['date'])
            if sale_date >= start:
                total_revenue += sale.get('price', 0.0) or 0.0
                total_cost += sale.get('cost_with_extras', sale['cost'])
                total_profit += sale.get('profit', 0.0) or 0.0
                count += 1

        if count == 0:
            await update.message.reply_text(f"Нет продаж за {period}.")
            return

        msg = f"📊 *Статистика за {period}:*\n"
        msg += f"• Продано десертов: {count}\n"
        msg += f"• Выручка: {total_revenue:.2f} руб\n"
        msg += f"• Себестоимость: {total_cost:.2f} руб\n"
        msg += f"• Прибыль: {total_profit:.2f} руб\n"
        if total_cost > 0:
            msg += f"• Рентабельность: {(total_profit/total_cost*100):.1f}%"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка в stats: {e}")
async def low_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    threshold = 1.0
    if context.args:
        try:
            threshold = float(context.args[0].replace(',', '.'))
        except:
            pass
    if not ingredients:
        await update.message.reply_text("Список ингредиентов пуст")
        return
    low = []
    for name, data in ingredients.items():
        stock = data.get('stock', 0.0)
        if stock < threshold:
            low.append(f"• {name}: {stock:.2f} {data['unit']}")
    if low:
        msg = f"⚠️ *Ингредиенты с остатком менее {threshold}:*\n" + "\n".join(low)
    else:
        msg = f"✅ Все остатки выше {threshold}."
    await update.message.reply_text(msg)
async def popular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Топ-5 рецептов по продажам"""
    try:
        recipe_count = {}
        for sale in sales:
            recipe = sale['recipe']
            recipe_count[recipe] = recipe_count.get(recipe, 0) + sale.get('quantity', 1)

        if not recipe_count:
            await update.message.reply_text("Пока нет продаж.")
            return

        sorted_recipes = sorted(recipe_count.items(), key=lambda x: x[1], reverse=True)[:5]
        msg = "🏆 *Топ-5 рецептов:*\n"
        for i, (recipe, cnt) in enumerate(sorted_recipes, 1):
            msg += f"{i}. {recipe}: {cnt} шт\n"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка в popular: {e}")

async def list_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Функция заказов пока не реализована.")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context, first_time=True)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context, first_time=False)
async def set_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить категорию для рецепта: /set_category рецепт категория"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Формат: /set_category рецепт категория\n"
            "Пример: /set_category меренговый_рулет_белый рулеты"
        )
        return
    # Название рецепта может состоять из нескольких слов, поэтому все аргументы кроме последнего — это название
    *name_parts, category = context.args
    name = ' '.join(name_parts).lower()
    if name not in recipes:
        await update.message.reply_text(f"Рецепт '{name}' не найден")
        return
    if isinstance(recipes[name], dict):
        recipes[name]['category'] = category.lower()
    else:
        # Если рецепт в старом формате (не словарь), преобразуем
        recipes[name] = {"ingredients": recipes[name], "category": category.lower()}
    save_data(recipes, RECIPES_FILE)
    await update.message.reply_text(f"✅ Категория '{category}' установлена для рецепта '{name}'")
# ---------- Ингредиенты ----------
async def add_ingredient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "Ошибка! Нужно: /add_ingredient название цена единица\n"
                "Или: /add_ingredient название цена_упаковки вес_упаковки единица_веса\n"
                "Примеры:\n"
                "/add_ingredient мука 50 кг\n"
                "/add_ingredient масло 209.99 180 г"
            )
            return

        if len(args) >= 4:
            # Новый формат: цена, количество, единица
            *name_parts, price_str, qty_str, unit = args
            name = ' '.join(name_parts).lower()
            price_pack = float(price_str.replace(',', '.'))
            qty_pack = float(qty_str.replace(',', '.'))
            unit = unit.lower()

            allowed_units = ['кг', 'г', 'л', 'мл', 'шт']
            if unit not in allowed_units:
                await update.message.reply_text(f"Единица должна быть одной из: {', '.join(allowed_units)}")
                return

            # Пересчёт в базовую единицу (кг, л, шт)
            if unit in ['г', 'кг']:
                if unit == 'г':
                    qty_kg = qty_pack / 1000.0
                else:  # кг
                    qty_kg = qty_pack
                price_per_kg = price_pack / qty_kg
                price_per_kg = round(price_per_kg, 2)
                ingredients[name] = {"price": price_per_kg, "unit": "кг"}
                save_data(ingredients, INGREDIENTS_FILE)
                await update.message.reply_text(
                    f"✅ Ингредиент '{name}' добавлен: {price_per_kg} руб/кг "
                    f"(рассчитано из {price_pack} руб за {qty_pack} {unit})"
                )
            elif unit in ['мл', 'л']:
                if unit == 'мл':
                    qty_l = qty_pack / 1000.0
                else:
                    qty_l = qty_pack
                price_per_l = price_pack / qty_l
                price_per_l = round(price_per_l, 2)
                ingredients[name] = {"price": price_per_l, "unit": "л"}
                save_data(ingredients, INGREDIENTS_FILE)
                await update.message.reply_text(
                    f"✅ Ингредиент '{name}' добавлен: {price_per_l} руб/л "
                    f"(рассчитано из {price_pack} руб за {qty_pack} {unit})"
                )
            elif unit == 'шт':
                price_per_pcs = price_pack / qty_pack
                price_per_pcs = round(price_per_pcs, 2)
                ingredients[name] = {"price": price_per_pcs, "unit": "шт"}
                save_data(ingredients, INGREDIENTS_FILE)
                await update.message.reply_text(
                    f"✅ Ингредиент '{name}' добавлен: {price_per_pcs} руб/шт "
                    f"(рассчитано из {price_pack} руб за {qty_pack} шт)"
                )
        else:
            # Старый формат: цена и единица
            *name_parts, price_str, unit = args
            name = ' '.join(name_parts).lower()
            price = float(price_str.replace(',', '.'))
            unit = unit.lower()
            allowed_units = ['кг', 'г', 'шт', 'л', 'мл']
            if unit not in allowed_units:
                await update.message.reply_text(f"Ошибка! Единица должна быть одной из: {', '.join(allowed_units)}")
                return
            ingredients[name] = {"price": price, "unit": unit}
            save_data(ingredients, INGREDIENTS_FILE)
            await update.message.reply_text(f"✅ Ингредиент '{name}' добавлен: {price} руб/{unit}")
    except ValueError:
        await update.message.reply_text("Ошибка! Цена и количество должны быть числами (например, 50 или 45.5)")
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {e}")

async def show_ingredients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        reply_func = update.callback_query.edit_message_text
    else:
        reply_func = update.message.reply_text
    if not ingredients:
        await reply_func("Список ингредиентов пуст")
        return
    message = "📋 *Список ингредиентов (по алфавиту):*\n"
    for name in sorted(ingredients.keys()):
        data = ingredients[name]
        message += f"• {name}: {data['price']} руб/{data['unit']}\n"
    await reply_func(message)

async def remove_ingredient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите название ингредиента: /remove_ingredient мука")
        return
    name = ' '.join(context.args).lower()
    if name in ingredients:
        del ingredients[name]
        save_data(ingredients, INGREDIENTS_FILE)
        await update.message.reply_text(f"✅ Ингредиент '{name}' удалён")
    else:
        await update.message.reply_text(f"Ингредиент '{name}' не найден")

async def update_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Формат: /update_price название новая_цена\nПример: /update_price мука 55")
        return
    *name_parts, price_str = context.args
    name = ' '.join(name_parts).lower()
    try:
        new_price = float(price_str.replace(',', '.'))
        if name in ingredients:
            ingredients[name]["price"] = new_price
            save_data(ingredients, INGREDIENTS_FILE)
            await update.message.reply_text(f"✅ Цена '{name}' обновлена: {new_price} руб/{ingredients[name]['unit']}")
        else:
            await update.message.reply_text(f"Ингредиент '{name}' не найден")
    except ValueError:
        await update.message.reply_text("Ошибка! Цена должна быть числом")

# ---------- Рецепты ----------
async def add_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):  # старый формат
    try:
        text = update.message.text.replace('/add_recipe', '', 1).strip()
        if ':' not in text:
            await update.message.reply_text(
                "Ошибка! Нужно: /add_recipe Название: порции; ингредиент количество, ...\n"
                "Пример: /add_recipe Омлет: 2; яйца 3, молоко 0.1"
            )
            return
        name_part, rest = text.split(':', 1)
        name = name_part.strip().lower()
        if ';' in rest:
            portions_part, ingredients_part = rest.split(';', 1)
            try:
                portions = float(portions_part.strip())
            except ValueError:
                await update.message.reply_text("Ошибка! Количество порций должно быть числом")
                return
        else:
            portions = 1
            ingredients_part = rest
        recipe_ingredients = {}
        for item in ingredients_part.split(','):
            item = item.strip()
            if not item:
                continue
            parts = item.rsplit(' ', 1)
            if len(parts) != 2:
                await update.message.reply_text(f"Ошибка в элементе: '{item}'. Должно быть 'название количество'")
                return
            ing_name = parts[0].strip().lower()
            try:
                qty = float(parts[1].replace(',', '.'))
            except ValueError:
                await update.message.reply_text(f"Ошибка: количество должно быть числом в '{item}'")
                return
            recipe_ingredients[ing_name] = qty
        recipes[name] = {"ingredients": recipe_ingredients, "portions": portions}
        save_data(recipes, RECIPES_FILE)
        await update.message.reply_text(f"✅ Рецепт '{name}' добавлен! ({portions} порций)")
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {e}")

async def add_recipe_scaled(update: Update, context: ContextTypes.DEFAULT_TYPE):  # масштабируемый формат
    try:
        text = update.message.text.replace('/add_recipe2', '', 1).strip()
        if ':' not in text:
            await update.message.reply_text(
                "Ошибка! Нужно: /add_recipe2 название тип базовое_количество: ингредиенты\n"
                "Пример: /add_recipe2 торт вес 1: мука 0.5, сахар 0.2"
            )
            return
        left, right = text.split(':', 1)
        parts = left.strip().split()
        if len(parts) < 3:
            await update.message.reply_text("Укажите название, тип (вес/штук) и базовое количество")
            return
        name = parts[0].lower()
        type_str = parts[1].lower()
        try:
            base_qty = float(parts[2].replace(',', '.'))
        except ValueError:
            await update.message.reply_text("Ошибка! Базовое количество должно быть числом")
            return
        if type_str == 'вес':
            recipe_type = 'weight'
            base_unit = 'кг'
        elif type_str == 'штук':
            recipe_type = 'pcs'
            base_unit = 'шт'
        else:
            await update.message.reply_text("Ошибка! Тип должен быть 'вес' или 'штук'")
            return
        ingredients_list = right.strip().split(',')
        recipe_ingredients = {}
        for item in ingredients_list:
            item = item.strip()
            if not item:
                continue
            parts = item.rsplit(' ', 1)
            if len(parts) != 2:
                await update.message.reply_text(f"Ошибка в элементе: '{item}'. Должно быть 'название количество'")
                return
            ing_name = parts[0].strip().lower()
            try:
                qty = float(parts[1].replace(',', '.'))
            except ValueError:
                await update.message.reply_text(f"Ошибка: количество должно быть числом в '{item}'")
                return
            recipe_ingredients[ing_name] = qty
        recipes[name] = {"type": recipe_type, "base_qty": base_qty, "ingredients": recipe_ingredients}
        save_data(recipes, RECIPES_FILE)
        await update.message.reply_text(f"✅ Рецепт '{name}' добавлен! (тип: {type_str}, база {base_qty} {base_unit})")
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {e}")

async def list_recipes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список рецептов. Если указана категория, показать только из неё."""
    try:
        category = None
        if context.args:
            category = ' '.join(context.args).lower()
        
        if update.callback_query:
            await update.callback_query.answer()
            reply_func = update.callback_query.edit_message_text
        else:
            reply_func = update.message.reply_text

        if not recipes:
            await reply_func("Список рецептов пуст")
            return

        filtered_recipes = {}
        for name, data in recipes.items():
            if category:
                cat = data.get('category') if isinstance(data, dict) else None
                if cat and cat == category:
                    filtered_recipes[name] = data
            else:
                filtered_recipes[name] = data

        if not filtered_recipes:
            await reply_func(f"Нет рецептов в категории '{category}'." if category else "Список рецептов пуст")
            return

        message = f"📖 Список рецептов{f' в категории {category}' if category else ''}:\n"
        for name, data in filtered_recipes.items():
            if isinstance(data, dict) and "type" in data:
                rtype = "весовой" if data["type"] == "weight" else "штучный"
                base = data["base_qty"]
                unit = "кг" if data["type"] == "weight" else "шт"
                ing_list = [f"{ing} {qty} {ingredients.get(ing, {}).get('unit', 'ед')}" for ing, qty in data["ingredients"].items()]
                message += f"• {name} ({rtype}, база {base} {unit}): {', '.join(ing_list)}\n"
            else:
                if isinstance(data, dict) and "ingredients" in data:
                    ing_dict = data["ingredients"]
                    portions = data.get("portions", 1)
                else:
                    ing_dict = data
                    portions = 1
                ing_list = [f"{ing} {qty} {ingredients.get(ing, {}).get('unit', 'ед')}" for ing, qty in ing_dict.items()]
                message += f"• {name} ({portions} порц.): {', '.join(ing_list)}\n"
        await reply_func(message)
    except Exception as e:
        error_msg = f"❌ Ошибка в команде /recipes: {e}"
        await update.message.reply_text(error_msg)
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика продаж: /stats [день|неделя|месяц|год]"""
    period = context.args[0].lower() if context.args else "месяц"
    now = datetime.now()
    if period == "день":
        start = now - timedelta(days=1)
    elif period == "неделя":
        start = now - timedelta(weeks=1)
    elif period == "месяц":
        start = now - timedelta(days=30)
    elif period == "год":
        start = now - timedelta(days=365)
    else:
        await update.message.reply_text("Период может быть: день, неделя, месяц, год")
        return

    total_revenue = 0.0
    total_cost = 0.0
    total_profit = 0.0
    count = 0

    for sale in sales:
        sale_date = datetime.fromisoformat(sale['date'])
        if sale_date >= start:
            total_revenue += sale.get('price', 0.0) or 0.0
            total_cost += sale.get('cost_with_extras', sale['cost'])
            total_profit += sale.get('profit', 0.0) or 0.0
            count += 1

    if count == 0:
        await update.message.reply_text(f"Нет продаж за {period}.")
        return

    msg = f"📊 *Статистика за {period}:*\n"
    msg += f"• Продано десертов: {count}\n"
    msg += f"• Выручка: {total_revenue:.2f} руб\n"
    msg += f"• Себестоимость: {total_cost:.2f} руб\n"
    msg += f"• Прибыль: {total_profit:.2f} руб\n"
    if total_cost > 0:
        msg += f"• Рентабельность: {(total_profit/total_cost*100):.1f}%"
    await update.message.reply_text(msg)
async def popular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Топ-5 рецептов по продажам"""
    recipe_count = {}
    for sale in sales:
        recipe = sale['recipe']
        recipe_count[recipe] = recipe_count.get(recipe, 0) + sale.get('quantity', 1)

    if not recipe_count:
        await update.message.reply_text("Пока нет продаж.")
        return

    sorted_recipes = sorted(recipe_count.items(), key=lambda x: x[1], reverse=True)[:5]
    msg = "🏆 *Топ-5 рецептов:*\n"
    for i, (recipe, cnt) in enumerate(sorted_recipes, 1):
        msg += f"{i}. {recipe}: {cnt} шт\n"
    await update.message.reply_text(msg)
async def remove_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите название рецепта: /remove_recipe омлет")
        return
    name = ' '.join(context.args).strip().lower()
    if name in recipes:
        del recipes[name]
        save_data(recipes, RECIPES_FILE)
        await update.message.reply_text(f"✅ Рецепт '{name}' удалён")
    else:
        await update.message.reply_text(f"Рецепт '{name}' не найден")

async def delete_all_recipes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global recipes
    recipes = {}
    save_data(recipes, RECIPES_FILE)
    await update.message.reply_text("Все рецепты удалены.")

# ---------- Расчёты ----------
async def calculate_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите название десерта: /calculate тирамису")
        return
    name = ' '.join(context.args).strip().lower()
    if name not in recipes:
        await update.message.reply_text(f"Рецепт '{name}' не найден")
        return
    data = recipes[name]
    if isinstance(data, dict) and "type" in data:
        recipe = data["ingredients"]
        portions = 1
    else:
        recipe = data["ingredients"] if isinstance(data, dict) and "ingredients" in data else data
        portions = data.get("portions", 1) if isinstance(data, dict) else 1
    total = 0.0
    missing = []
    for ing_name, qty in recipe.items():
        if ing_name in ingredients:
            total += ingredients[ing_name]["price"] * qty
        else:
            missing.append(ing_name)
    if missing:
        await update.message.reply_text(f"❌ Не хватает ингредиентов: {', '.join(missing)}.\nДобавьте их через /add_ingredient")
    else:
        base = f"💰 Себестоимость '{name}': {total:.2f} руб"
        if portions != 1:
            base += f"\n🍽 На {portions} порций: {(total/portions):.2f} руб/порция"
        await update.message.reply_text(base)

async def scale_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Формат: /scale название новое_количество [единица]\nПример: /scale красный_бархат 1.5 кг")
        return
    name = context.args[0].lower()
    if name not in recipes:
        await update.message.reply_text(f"Рецепт '{name}' не найден")
        return
    data = recipes[name]
    if not isinstance(data, dict) or "type" not in data:
        await update.message.reply_text("Этот рецепт нельзя масштабировать, добавьте через /add_recipe2")
        return
    try:
        if len(context.args) >= 3:
            new_qty = float(context.args[1].replace(',', '.'))
            unit = context.args[2].lower()
        else:
            match = re.match(r'^([\d.,]+)\s*([а-яa-z]+)?$', context.args[1].lower())
            if match:
                new_qty = float(match.group(1).replace(',', '.'))
                unit = match.group(2) or ''
            else:
                new_qty = float(context.args[1].replace(',', '.'))
                unit = ''
    except ValueError:
        await update.message.reply_text("Ошибка! Количество должно быть числом")
        return

    if data["type"] == "weight":
        expected_unit = "кг"
        if unit and unit not in ["кг", "килограмм", "kg"]:
            await update.message.reply_text("Для весового рецепта единица должна быть 'кг'")
            return
    else:
        expected_unit = "шт"
        if unit and unit not in ["шт", "штук", "pcs"]:
            await update.message.reply_text("Для штучного рецепта единица должна быть 'шт'")
            return

    scale_factor = new_qty / data["base_qty"]
    scaled = {ing: qty * scale_factor for ing, qty in data["ingredients"].items()}

    # --- Начало новых расчётов ---
    # Себестоимость ингредиентов
    total_ing = 0.0
    missing = []
    ing_lines = []
    for ing_name, qty in scaled.items():
        if ing_name in ingredients:
            cost = ingredients[ing_name]["price"] * qty
            total_ing += cost
            unit_i = ingredients[ing_name]["unit"]
            ing_lines.append(f"• {ing_name}: {qty:.2f} {unit_i} = {cost:.2f} руб")
        else:
            missing.append(ing_name)

    if missing:
        await update.message.reply_text(f"❌ Не хватает ингредиентов: {', '.join(missing)}")
        return

    # Дополнительные расходы (упаковка, работа)
    packaging = data.get('packaging', 0.0)
    work_hours = data.get('work_hours', 0.0)
    hourly_rate = settings.get('hourly_rate', 0.0)
    markup = data.get('markup')

    # Различаем тип рецепта: для штучных умножаем на количество, для весовых оставляем как есть
    if data["type"] == "weight":
        total_packaging = packaging  # упаковка на весь торт
        total_work = work_hours * hourly_rate if work_hours and hourly_rate else 0.0  # работа на весь торт
    else:
        total_packaging = packaging * scale_factor
        total_work = work_hours * hourly_rate * scale_factor if work_hours and hourly_rate else 0.0

    total_cost = total_ing + total_packaging + total_work

    # Формируем сообщение
    msg = f"📐 *Рецепт '{name}'* на {new_qty:.2f} {expected_unit}:\n\n"
    msg += "*Ингредиенты:*\n" + "\n".join(ing_lines)
    msg += f"\n\n💰 *Себестоимость ингредиентов:* {total_ing:.2f} руб"

    if packaging:
        msg += f"\n📦 *Упаковка:* {total_packaging:.2f} руб"
    else:
        msg += f"\n📦 *Упаковка:* не указана (0 руб)"

    if work_hours:
        if hourly_rate:
            if data["type"] == "weight":
                msg += f"\n⏱ *Работа:* {work_hours:.2f} ч × {hourly_rate:.2f} руб/ч = {total_work:.2f} руб"
            else:
                msg += f"\n⏱ *Работа:* {work_hours * scale_factor:.2f} ч × {hourly_rate:.2f} руб/ч = {total_work:.2f} руб"
        else:
            if data["type"] == "weight":
                msg += f"\n⏱ *Работа:* {work_hours:.2f} ч (ставка не задана)"
            else:
                msg += f"\n⏱ *Работа:* {work_hours * scale_factor:.2f} ч (ставка не задана)"
    else:
        msg += f"\n⏱ *Работа:* не указана (0 руб)"

    msg += f"\n🧾 *Полная себестоимость:* {total_cost:.2f} руб"

    if markup is not None:
        price = total_cost * (1 + markup / 100)
        profit = price - total_cost
        margin = (profit / total_cost) * 100 if total_cost > 0 else 0
        msg += f"\n📈 *Наценка:* {markup}%"
        msg += f"\n💵 *Цена продажи:* {price:.2f} руб"
        msg += f"\n💸 *Прибыль:* {profit:.2f} руб"
        msg += f"\n📊 *Рентабельность:* {margin:.1f}%"
    else:
        msg += f"\n❓ *Наценка не задана.* Установите через /set_markup"

    await update.message.reply_text(msg)

# ---------- Экспорт ----------
async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ingredients:
        await update.message.reply_text("Список ингредиентов пуст, нечего экспортировать")
        return
    try:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Название", "Цена (руб)", "Единица"])
        for name, data in ingredients.items():
            writer.writerow([name, data['price'], data['unit']])
        output.seek(0)
        document = output.getvalue().encode('utf-8')
        await update.message.reply_document(
            document=document,
            filename="ingredients.csv",
            caption="📊 Экспорт ингредиентов"
        )
        output.close()
    except Exception as e:
        await update.message.reply_text(f"Ошибка при экспорте: {e}")

# ---------- Помощь ----------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        reply_func = update.callback_query.edit_message_text
    else:
        reply_func = update.message.reply_text
    help_text = (
        "📖 Доступные команды:\n"
        "/start - показать меню\n"
        "/menu - показать меню\n"
        "/add_ingredient название цена единица - добавить ингредиент (или цена_упаковки вес единица)\n"
        "/ingredients - список ингредиентов\n"
        "/add_recipe Название: порции; ингредиенты - добавить рецепт (старый формат)\n"
        "/add_recipe2 название тип базовое_количество: ингредиенты - добавить рецепт для масштабирования\n"
        "/recipes - список рецептов\n"
        "/calculate название - рассчитать себестоимость\n"
        "/scale название новое_количество [единица] - пересчитать рецепт\n"
        "/update_price название новая_цена - изменить цену ингредиента\n"
        "/remove_ingredient название - удалить ингредиент\n"
        "/remove_recipe название - удалить рецепт\n"
        "/export - выгрузить ингредиенты в CSV\n"
        "/delete_recipes - удалить все рецепты\n"
        "/set_description название описание - добавить описание к рецепту\n"
        "/show_recipe название - показать рецепт с описанием и расчётами\n"
        "/set_hourly_rate ставка - установить почасовую ставку работы\n"
        "/set_packaging название цена - установить стоимость упаковки для рецепта\n"
        "/set_work_hours название часы - установить время работы на рецепт\n"
        "/set_markup название процент - установить наценку для рецепта\n"
        "/price_list - список всех рецептов с ценами продажи\n\n"
        "Единицы измерения: кг, г, шт, л, мл"
    )
    await reply_func(help_text)

# ---------- Описание рецепта ----------
async def set_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "Ошибка! Нужно: /set_description название описание\n"
                "Пример: /set_description меренговый_рулет_белый Взбить белки..."
            )
            return
        recipe_name = context.args[0].lower()
        if recipe_name not in recipes:
            await update.message.reply_text(f"Рецепт '{recipe_name}' не найден")
            return
        description = ' '.join(context.args[1:])
        if isinstance(recipes[recipe_name], dict):
            recipes[recipe_name]['description'] = description
        else:
            recipes[recipe_name] = {"ingredients": recipes[recipe_name], "description": description}
        save_data(recipes, RECIPES_FILE)
        await update.message.reply_text(f"✅ Описание для рецепта '{recipe_name}' сохранено!")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")
import re  # убедитесь, что этот импорт есть в начале файла

import re

async def parse_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Парсит текстовый рецепт и предлагает команду для добавления"""
    if context.args:
        # Если есть аргументы, объединяем их в текст
        text = ' '.join(context.args)
        await process_recipe_text(update, context, text)
    else:
        # Если аргументов нет, просим прислать текст отдельно
        await update.message.reply_text(
            "Отправьте текст рецепта (каждый ингредиент с новой строки или через запятую):\n"
            "Например:\n"
            "мука 200 г\n"
            "сахар 150 г\n"
            "яйцо 2 шт"
        )
        context.user_data['awaiting_recipe'] = True
# Словари для временного хранения данных диалога
# Ключ: user_id
temp_recipe_data = {}

async def import_recipe_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога – отправляем приветствие и ждём текст рецепта"""
    user_id = update.effective_user.id
    temp_recipe_data[user_id] = {
        'ingredients': [],      # список кортежей (название, кол-во, ед)
        'new_ingredients': [],  # список названий новых ингредиентов
        'new_prices': {}        # словарь: название -> цена за базовую единицу
    }
    await update.message.reply_text(
        "🍰 Отправьте мне текст рецепта.\n"
        "Каждый ингредиент должен быть на отдельной строке или через запятую.\n"
        "Формат: название количество единица\n"
        "Пример:\n"
        "мука 200 г\n"
        "сахар 150 г\n"
        "яйцо 2 шт"
    )
    return WAITING_RECIPE_TEXT

async def receive_recipe_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем текст рецепта, парсим ингредиенты"""
    user_id = update.effective_user.id
    text = update.message.text

    # Заменяем запятые на переносы и разбиваем на строки
    text = text.replace(',', '\n')
    lines = text.split('\n')
    units_map = {'г': 'кг', 'мл': 'л', 'кг': 'кг', 'л': 'л', 'шт': 'шт'}
    conversion = {'г': 0.001, 'мл': 0.001, 'кг': 1, 'л': 1, 'шт': 1}

    pattern = re.compile(r'^\s*([а-яА-ЯёЁa-zA-Z\s]+?)\s+(\d+[.,]?\d*)\s*(г|кг|мл|л|шт)\s*$', re.UNICODE)

    found = []
    new_ingredients = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            ing_name_raw = match.group(1).strip().lower()
            qty_str = match.group(2).replace(',', '.')
            unit = match.group(3).lower()
            try:
                qty = float(qty_str)
            except ValueError:
                continue
            base_unit = units_map[unit]
            qty_base = qty * conversion[unit]

            # Ищем существующий ингредиент (простое сравнение)
            existing_ing = None
            for ing in ingredients:
                if ing_name_raw in ing or ing in ing_name_raw:
                    existing_ing = ing
                    break

            if existing_ing:
                ing_name = existing_ing
            else:
                ing_name = ing_name_raw
                new_ingredients.append(ing_name)

            found.append((ing_name, qty_base, base_unit))

    if not found:
        await update.message.reply_text(
            "❌ Не удалось распознать ни одного ингредиента. Попробуйте ещё раз."
        )
        return WAITING_RECIPE_TEXT

    # Сохраняем распознанные ингредиенты
    temp_recipe_data[user_id]['ingredients'] = found
    temp_recipe_data[user_id]['new_ingredients'] = new_ingredients

    # Если есть новые ингредиенты, начинаем запрашивать цены
    if new_ingredients:
        # Берём первый новый ингредиент
        next_ing = new_ingredients[0]
        unit = None
        # Находим единицу для этого ингредиента из списка
        for ing, qty, base_unit in found:
            if ing == next_ing:
                unit = base_unit
                break
        if not unit:
            unit = 'кг'  # запасной вариант
        await update.message.reply_text(
            f"🆕 Найден новый ингредиент: *{next_ing}*.\n"
            f"Введите цену за 1 {unit} (например, 150):"
        )
        return WAITING_INGREDIENT_PRICE
    else:
        # Если все ингредиенты известны, переходим к запросу названия рецепта
        await update.message.reply_text("Введите название рецепта (например, «Красный бархат»):")
        return WAITING_RECIPE_NAME

async def receive_ingredient_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем цену для очередного нового ингредиента"""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    try:
        price = float(text.replace(',', '.'))
    except ValueError:
        await update.message.reply_text("❌ Ошибка! Введите число (например, 150).")
        return WAITING_INGREDIENT_PRICE

    # Определяем, для какого ингредиента мы ждём цену
    new_ings = temp_recipe_data[user_id]['new_ingredients']
    if not new_ings:
        # такого не должно быть, но на всякий случай
        await update.message.reply_text("Введите название рецепта:")
        return WAITING_RECIPE_NAME

    current_ing = new_ings[0]
    temp_recipe_data[user_id]['new_prices'][current_ing] = price

    # Удаляем обработанный ингредиент из списка новых
    new_ings.pop(0)

    if new_ings:
        # Есть ещё новые ингредиенты
        next_ing = new_ings[0]
        # Находим его единицу
        unit = None
        for ing, qty, base_unit in temp_recipe_data[user_id]['ingredients']:
            if ing == next_ing:
                unit = base_unit
                break
        if not unit:
            unit = 'кг'
        await update.message.reply_text(
            f"🆕 Следующий новый ингредиент: *{next_ing}*.\n"
            f"Введите цену за 1 {unit}:"
        )
        return WAITING_INGREDIENT_PRICE
    else:
        # Все цены введены, переходим к названию рецепта
        await update.message.reply_text("Введите название рецепта (например, «Красный бархат»):")
        return WAITING_RECIPE_NAME

async def receive_recipe_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем название рецепта, запрашиваем тип"""
    user_id = update.effective_user.id
    recipe_name = update.message.text.strip().lower()
    temp_recipe_data[user_id]['recipe_name'] = recipe_name

    await update.message.reply_text(
        "Введите тип рецепта и базовое количество.\n"
        "Примеры:\n"
        "- для весового: вес 1 кг\n"
        "- для штучного: штук 1 шт\n"
        "Вы можете указать другое базовое количество, например: вес 0.5 кг"
    )
    return WAITING_RECIPE_TYPE

async def receive_recipe_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем тип рецепта и базовое количество, сохраняем всё в базу"""
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    # Парсим тип и количество
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Неверный формат. Введите, например: вес 1 кг или штук 1 шт"
        )
        return WAITING_RECIPE_TYPE

    type_str = parts[0]
    try:
        base_qty = float(parts[1].replace(',', '.'))
    except ValueError:
        await update.message.reply_text("❌ Ошибка! Количество должно быть числом.")
        return WAITING_RECIPE_TYPE

    if type_str in ['вес', 'weight']:
        recipe_type = 'weight'
        if len(parts) >= 3 and parts[2] in ['кг', 'килограмм', 'kg']:
            base_unit = 'кг'
        else:
            base_unit = 'кг'  # по умолчанию
    elif type_str in ['штук', 'pcs', 'шт']:
        recipe_type = 'pcs'
        if len(parts) >= 3 and parts[2] in ['шт', 'штук', 'pcs']:
            base_unit = 'шт'
        else:
            base_unit = 'шт'
    else:
        await update.message.reply_text("❌ Тип должен быть «вес» или «штук».")
        return WAITING_RECIPE_TYPE

    # Добавляем новые ингредиенты в базу с указанными ценами
    new_prices = temp_recipe_data[user_id]['new_prices']
    for ing_name, price in new_prices.items():
        # Определяем единицу для этого ингредиента (из ранее распознанного списка)
        unit = 'кг'  # по умолчанию
        for ing, qty, base_unit in temp_recipe_data[user_id]['ingredients']:
            if ing == ing_name:
                unit = base_unit
                break
        ingredients[ing_name] = {"price": price, "unit": unit, "stock": 0.0}
        save_data(ingredients, INGREDIENTS_FILE)

    # Формируем словарь ингредиентов для рецепта
    recipe_ingredients = {}
    for ing, qty, unit in temp_recipe_data[user_id]['ingredients']:
        recipe_ingredients[ing] = qty

    # Сохраняем рецепт
    recipe_data = {
        "type": recipe_type,
        "base_qty": base_qty,
        "ingredients": recipe_ingredients
    }
    recipe_name = temp_recipe_data[user_id]['recipe_name']
    recipes[recipe_name] = recipe_data
    save_data(recipes, RECIPES_FILE)

    # Очищаем временные данные
    del temp_recipe_data[user_id]

    await update.message.reply_text(
        f"✅ Рецепт «{recipe_name}» успешно добавлен!\n"
        f"Новые ингредиенты также добавлены в базу."
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена диалога"""
    user_id = update.effective_user.id
    if user_id in temp_recipe_data:
        del temp_recipe_data[user_id]
    await update.message.reply_text("❌ Диалог отменён.")
    return ConversationHandler.END
async def process_recipe_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Основная логика парсинга"""
    # Заменяем запятые на переносы строк и разбиваем
    text = text.replace(',', '\n')
    lines = text.split('\n')
    found = []
    units_map = {'г': 'кг', 'мл': 'л', 'кг': 'кг', 'л': 'л', 'шт': 'шт'}
    conversion = {'г': 0.001, 'мл': 0.001, 'кг': 1, 'л': 1, 'шт': 1}

    # Регулярное выражение: название (может состоять из нескольких слов), затем число, затем единица
    pattern = re.compile(r'^\s*([а-яА-ЯёЁa-zA-Z\s]+?)\s+(\d+[.,]?\d*)\s*(г|кг|мл|л|шт)\s*$', re.UNICODE)

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            ing_name_raw = match.group(1).strip().lower()
            qty_str = match.group(2).replace(',', '.')
            unit = match.group(3).lower()
            try:
                qty = float(qty_str)
            except ValueError:
                continue
            base_unit = units_map[unit]
            qty_base = qty * conversion[unit]

            # Ищем существующий ингредиент (простое сравнение)
            found_ing = None
            for existing in ingredients:
                if ing_name_raw in existing or existing in ing_name_raw:
                    found_ing = existing
                    break
            if not found_ing:
                found_ing = ing_name_raw  # используем как есть

            found.append((found_ing, qty_base, base_unit))
        else:
            # Если строка не распознана, игнорируем
            pass

    if not found:
        await update.message.reply_text(
            "❌ Не удалось распознать ингредиенты.\n"
            "Убедитесь, что каждый ингредиент указан в формате:\n"
            "название количество единица\n"
            "Например: мука 200 г\n"
            "Допустимые единицы: г, кг, мл, л, шт"
        )
        return

    # Формируем команду /add_recipe2
    ing_parts = []
    for ing, qty, unit in found:
        # Красивое форматирование числа (убираем лишние нули)
        qty_str = f"{qty:.3f}".rstrip('0').rstrip('.') if '.' in f"{qty:.3f}" else f"{qty:.3f}"
        ing_parts.append(f"{ing} {qty_str}")

    cmd = f"/add_recipe2 новый_рецепт штук 1: " + ", ".join(ing_parts)

    msg = "✅ *Распознанные ингредиенты:*\n"
    for (ing, qty, unit) in found:
        msg += f"• {ing}: {qty:.3f} {unit}\n"
    msg += f"\n📝 *Команда для добавления*\n(проверьте и скорректируйте название рецепта):\n`{cmd}`"

    await update.message.reply_text(msg)
async def plan_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("Формат: /plan рецепт количество дата\nПример: /plan тест_омлет 2 2025-03-20")
        return
    *name_parts, qty_str, date_str = context.args
    name = ' '.join(name_parts).lower()
    try:
        qty = float(qty_str.replace(',', '.'))
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text("Ошибка! Количество должно быть числом, дата в формате ГГГГ-ММ-ДД")
        return
    if name not in recipes:
        await update.message.reply_text(f"Рецепт '{name}' не найден")
        return
    plan = {
        "date": date.isoformat(),
        "recipe": name,
        "quantity": qty
    }
    plans.append(plan)
    save_plans()
    await update.message.reply_text(f"✅ Запланировано {qty} шт '{name}' на {date_str}")
async def plan_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запланировать приготовление: /plan рецепт количество ГГГГ-ММ-ДД"""
    if len(context.args) < 3:
        await update.message.reply_text(
            "Формат: /plan рецепт количество дата\n"
            "Пример: /plan меренговый_рулет_белый 5 2025-03-15"
        )
        return
    # Собираем название рецепта (может быть из нескольких слов)
    *name_parts, qty_str, date_str = context.args
    name = ' '.join(name_parts).lower()
    try:
        qty = float(qty_str.replace(',', '.'))
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text("Ошибка! Количество должно быть числом, дата в формате ГГГГ-ММ-ДД")
        return
    if name not in recipes:
        await update.message.reply_text(f"Рецепт '{name}' не найден")
        return
    plan = {
        "date": date.isoformat(),
        "recipe": name,
        "quantity": qty
    }
    plans.append(plan)
    save_plans()
    await update.message.reply_text(f"✅ Запланировано {qty} шт '{name}' на {date_str}")
async def shopping_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сформировать список закупок на дату (или все планы)"""
    target_date = None
    if context.args:
        try:
            target_date = datetime.strptime(context.args[0], "%Y-%m-%d").date()
        except:
            await update.message.reply_text("Неверный формат даты. Используйте ГГГГ-ММ-ДД")
            return

    # Собираем все потребности из планов
    needs = {}
    for plan in plans:
        plan_date = datetime.fromisoformat(plan['date']).date()
        if target_date and plan_date != target_date:
            continue
        recipe_name = plan['recipe']
        qty = plan['quantity']
        if recipe_name not in recipes:
            continue  # пропускаем, если рецепт вдруг удалён
        data = recipes[recipe_name]
        if isinstance(data, dict) and "ingredients" in data:
            ing_dict = data["ingredients"]
        else:
            ing_dict = data
        # Масштабируем на нужное количество
        # Для штучных рецептов: ингредиенты даны на 1 шт, умножаем на qty
        # Для весовых: ингредиенты даны на 1 кг, умножаем на qty
        scale = qty
        for ing_name, ing_qty in ing_dict.items():
            need = ing_qty * scale
            needs[ing_name] = needs.get(ing_name, 0.0) + need

    if not needs:
        await update.message.reply_text("Нет планов на указанную дату." if target_date else "Нет планов.")
        return

    # Вычитаем остатки
    to_buy = {}
    for ing_name, need in needs.items():
        stock = ingredients.get(ing_name, {}).get('stock', 0.0)
        deficit = need - stock
        if deficit > 0:
            to_buy[ing_name] = deficit

    if not to_buy:
        await update.message.reply_text("✅ Все необходимые ингредиенты уже есть на складе.")
        return

    msg = "🛒 *Список закупок:*\n"
    for ing_name, deficit in to_buy.items():
        unit = ingredients.get(ing_name, {}).get('unit', '')
        msg += f"• {ing_name}: {deficit:.2f} {unit}\n"
    await update.message.reply_text(msg)
async def process_recipe_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Основная логика парсинга"""
    # Простейший парсер: ищем строки вида "ингредиент число единица"
    lines = text.strip().split('\n')
    found = []
    units_map = {'г': 'кг', 'мл': 'л', 'кг': 'кг', 'л': 'л', 'шт': 'шт'}
    conversion = {'г': 0.001, 'мл': 0.001, 'кг': 1, 'л': 1, 'шт': 1}

    # Регулярное выражение: слово(а) + пробел + число (с точкой/запятой) + пробел + единица
    pattern = re.compile(r'^\s*([а-яА-ЯёЁa-zA-Z\s]+?)\s+(\d+[.,]?\d*)\s*(г|кг|мл|л|шт)\s*$', re.UNICODE)

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            ing_name_raw = match.group(1).strip().lower()
            qty_str = match.group(2).replace(',', '.')
            unit = match.group(3).lower()
            try:
                qty = float(qty_str)
            except ValueError:
                continue
            # Переводим в базовую единицу
            base_unit = units_map[unit]
            qty_base = qty * conversion[unit]

            # Ищем похожий ингредиент в базе (простое сравнение по нижнему регистру)
            found_ing = None
            for existing in ingredients:
                if ing_name_raw in existing or existing in ing_name_raw:
                    found_ing = existing
                    break
            if not found_ing:
                # Если не нашли, предлагаем создать новый
                found_ing = ing_name_raw
                # Добавим в список для дальнейшего использования (но пока не сохраняем)
                # Можно было бы предложить создать ингредиент отдельно, но упростим: оставляем как есть
                pass

            found.append((found_ing, qty_base, base_unit))
        else:
            # Если строка не распознана, просто игнорируем (можно уведомить)
            pass

    if not found:
        await update.message.reply_text("Не удалось распознать ингредиенты. Проверьте формат:\nназвание количество единица\nНапример: мука 200 г")
        return

    # Формируем команду /add_recipe2
    ing_parts = []
    for ing, qty, unit in found:
        ing_parts.append(f"{ing} {qty:.3f}".rstrip('0').rstrip('.') if '.' in f"{qty:.3f}" else f"{qty:.3f}")
    cmd = f"/add_recipe2 новый_рецепт штук 1: " + ", ".join(ing_parts)

    # Отправляем результат пользователю
    msg = "✅ Распознанные ингредиенты:\n"
    for (ing, qty, unit) in found:
        msg += f"• {ing}: {qty:.3f} {unit}\n"
    msg += f"\nКоманда для добавления (проверьте и скорректируйте название рецепта):\n`{cmd}`"
    await update.message.reply_text(msg)
# ---------- Продвинутый показ рецепта ----------
async def show_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите название рецепта: /show_recipe красный_бархат")
        return
    name = ' '.join(context.args).strip().lower()
    if name not in recipes:
        await update.message.reply_text(f"Рецепт '{name}' не найден")
        return
    data = recipes[name]
    # Получаем ингредиенты
    if isinstance(data, dict) and "ingredients" in data:
        ing_dict = data["ingredients"]
        base_info = ""
        if "type" in data:
            base_info = f"Тип: {data['type']}, база: {data['base_qty']} {'кг' if data['type']=='weight' else 'шт'}\n"
    else:
        ing_dict = data
        base_info = "Старый формат рецепта (без масштабирования)\n"
    # Рассчитываем себестоимость ингредиентов
    total_ing = 0.0
    missing = []
    for ing_name, qty in ing_dict.items():
        if ing_name in ingredients:
            total_ing += ingredients[ing_name]["price"] * qty
        else:
            missing.append(ing_name)
    # Формируем основное сообщение (без описания)
    msg = f"🍰 {name}\n"
    msg += base_info
    msg += "\nИнгредиенты:\n"
    for ing_name, qty in ing_dict.items():
        unit = ingredients.get(ing_name, {}).get('unit', '')
        msg += f"• {ing_name}: {qty} {unit}\n"
    if missing:
        msg += f"\n⚠️ Отсутствуют в базе: {', '.join(missing)}\n"
        await update.message.reply_text(msg)
        return
    # Дополнительные расходы
    packaging = data.get('packaging') if isinstance(data, dict) else None
    work_hours = data.get('work_hours') if isinstance(data, dict) else None
    markup = data.get('markup') if isinstance(data, dict) else None
    hourly_rate = settings.get('hourly_rate', 0.0)
    work_cost = work_hours * hourly_rate if work_hours is not None and hourly_rate > 0 else None
    total_cost = total_ing
    if packaging is not None:
        total_cost += packaging
    if work_cost is not None:
        total_cost += work_cost
    msg += f"\n💰 Себестоимость ингредиентов: {total_ing:.2f} руб"
    if packaging is not None:
        msg += f"\n📦 Упаковка: {packaging:.2f} руб"
    else:
        msg += f"\n📦 Упаковка: не указана (0 руб)"
    if work_hours is not None:
        if hourly_rate > 0:
            msg += f"\n⏱ Работа: {work_hours:.2f} ч × {hourly_rate:.2f} руб/ч = {work_cost:.2f} руб"
        else:
            msg += f"\n⏱ Работа: {work_hours:.2f} ч (ставка не задана)"
    else:
        msg += f"\n⏱ Работа: не указана (0 руб)"
    msg += f"\n🧾 Полная себестоимость: {total_cost:.2f} руб"
    if markup is not None:
        price = total_cost * (1 + markup/100)
        profit = price - total_cost
        margin = (profit / total_cost) * 100 if total_cost > 0 else 0
        msg += f"\n📈 Наценка: {markup}%"
        msg += f"\n💵 Цена продажи: {price:.2f} руб"
        msg += f"\n💸 Прибыль: {profit:.2f} руб"
        msg += f"\n📊 Рентабельность: {margin:.1f}%"
    else:
        msg += f"\n❓ Наценка не задана. Установите через /set_markup"

    # Функция для отправки длинных сообщений частями
    async def send_long_message(text):
        if len(text) <= 4096:
            await update.message.reply_text(text)
        else:
            parts = [text[i:i+4096] for i in range(0, len(text), 4096)]
            for part in parts:
                await update.message.reply_text(part)

    # Отправляем основное сообщение
    await send_long_message(msg)

    # Если есть описание, отправляем его отдельно
    if isinstance(data, dict) and "description" in data:
        desc_msg = f"🍳 Приготовление:\n{data['description']}"
        await send_long_message(desc_msg)

# ---------- Установка почасовой ставки ----------
async def set_hourly_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите ставку: /set_hourly_rate 350")
        return
    try:
        rate = float(context.args[0].replace(',', '.'))
        settings['hourly_rate'] = rate
        save_settings()
        await update.message.reply_text(f"✅ Почасовая ставка установлена: {rate} руб/час")
    except ValueError:
        await update.message.reply_text("Ошибка! Ставка должна быть числом")

# ---------- Установка стоимости упаковки ----------
async def set_packaging(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Формат: /set_packaging название цена")
        return
    *name_parts, price_str = context.args
    name = ' '.join(name_parts).lower()
    if name not in recipes:
        await update.message.reply_text(f"Рецепт '{name}' не найден")
        return
    try:
        price = float(price_str.replace(',', '.'))
        if isinstance(recipes[name], dict):
            recipes[name]['packaging'] = price
        else:
            recipes[name] = {"ingredients": recipes[name], "packaging": price}
        save_data(recipes, RECIPES_FILE)
        await update.message.reply_text(f"✅ Для рецепта '{name}' установлена упаковка: {price} руб")
    except ValueError:
        await update.message.reply_text("Ошибка! Цена должна быть числом")

# ---------- Установка времени работы ----------
async def set_work_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Формат: /set_work_hours название часы")
        return
    *name_parts, hours_str = context.args
    name = ' '.join(name_parts).lower()
    if name not in recipes:
        await update.message.reply_text(f"Рецепт '{name}' не найден")
        return
    try:
        hours = float(hours_str.replace(',', '.'))
        if isinstance(recipes[name], dict):
            recipes[name]['work_hours'] = hours
        else:
            recipes[name] = {"ingredients": recipes[name], "work_hours": hours}
        save_data(recipes, RECIPES_FILE)
        await update.message.reply_text(f"✅ Для рецепта '{name}' установлено время работы: {hours} ч")
    except ValueError:
        await update.message.reply_text("Ошибка! Часы должны быть числом")

# ---------- Установка наценки ----------
async def set_markup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Формат: /set_markup название процент")
        return
    *name_parts, markup_str = context.args
    name = ' '.join(name_parts).lower()
    if name not in recipes:
        await update.message.reply_text(f"Рецепт '{name}' не найден")
        return
    try:
        markup = float(markup_str.replace(',', '.'))
        if isinstance(recipes[name], dict):
            recipes[name]['markup'] = markup
        else:
            recipes[name] = {"ingredients": recipes[name], "markup": markup}
        save_data(recipes, RECIPES_FILE)
        await update.message.reply_text(f"✅ Для рецепта '{name}' установлена наценка: {markup}%")
    except ValueError:
        await update.message.reply_text("Ошибка! Процент должен быть числом")
async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Формат: /add_stock название количество\nПример: /add_stock мука 10")
        return
    *name_parts, qty_str = context.args
    name = ' '.join(name_parts).lower()
    if name not in ingredients:
        await update.message.reply_text(f"Ингредиент '{name}' не найден")
        return
    try:
        qty = float(qty_str.replace(',', '.'))
        if 'stock' not in ingredients[name]:
            ingredients[name]['stock'] = 0.0
        ingredients[name]['stock'] += qty
        save_data(ingredients, INGREDIENTS_FILE)
        await update.message.reply_text(f"✅ Добавлено {qty} {ingredients[name]['unit']} к '{name}'. Текущий остаток: {ingredients[name]['stock']} {ingredients[name]['unit']}")
    except ValueError:
        await update.message.reply_text("Ошибка! Количество должно быть числом")
# ---------- Список рецептов с ценами ----------
async def price_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not recipes:
        await update.message.reply_text("Список рецептов пуст")
        return
    msg = "📋 *Список рецептов с ценами:*\n\n"
    hourly_rate = settings.get('hourly_rate', 0.0)
    for name, data in recipes.items():
        # Себестоимость ингредиентов
        if isinstance(data, dict) and "ingredients" in data:
            ing_dict = data["ingredients"]
        else:
            ing_dict = data
        total_ing = 0.0
        missing = False
        for ing_name, qty in ing_dict.items():
            if ing_name in ingredients:
                total_ing += ingredients[ing_name]["price"] * qty
            else:
                missing = True
                break
        if missing:
            continue  # Пропускаем рецепты с отсутствующими ингредиентами
        packaging = data.get('packaging') if isinstance(data, dict) else None
        work_hours = data.get('work_hours') if isinstance(data, dict) else None
        markup = data.get('markup') if isinstance(data, dict) else None
        total_cost = total_ing
        if packaging:
            total_cost += packaging
        if work_hours and hourly_rate > 0:
            total_cost += work_hours * hourly_rate
        price = total_cost * (1 + markup/100) if markup else None
        msg += f"• *{name}*"
        if price:
            msg += f": {price:.2f} руб (себ. {total_cost:.2f} руб)"
        else:
            msg += f": себест. {total_cost:.2f} руб (наценка не задана)"
        msg += "\n"
    await update.message.reply_text(msg)

# ---------- Эхо ----------
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    buttons = [   # <-- эта строка должна иметь отступ (4 пробела)
        "➕ Добавить ингредиент",
        "📋 Список ингредиентов",
        "🍰 Добавить рецепт",
        "💰 Рассчитать себестоимость",
        "📖 Мои рецепты",
        "⚖️ Пересчитать рецепт",
        "📦 Остатки",
        "🛒 Список покупок",
        "📊 Аналитика",
        "📅 Заказы",
        "❓ Помощь"
    ]
    if text in buttons:
        return
    await update.message.reply_text(f"Ты написал: {text}")
# ---------- Обработчик кнопок ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'add_ing':
        await query.edit_message_text(
            "Чтобы добавить ингредиент, отправьте команду:\n"
            "/add_ingredient название цена единица\n"
            "Или с ценой за упаковку: /add_ingredient название цена_упаковки вес_упаковки единица\n\n"
            "Допустимые единицы: кг, г, шт, л, мл"
        )
    elif data == 'list_ing':
        await show_ingredients(update, context)
    elif data == 'add_rcp':
        await query.edit_message_text(
            "Чтобы добавить рецепт, отправьте:\n"
            "/add_recipe Название: порции; ингредиенты (старый формат)\n"
            "или /add_recipe2 название тип базовое_количество: ингредиенты (для масштабирования)\n\n"
            "Примеры:\n"
            "/add_recipe Омлет: 2; яйца 3, молоко 0.1\n"
            "/add_recipe2 торт вес 1: мука 0.5, сахар 0.2, яйца 3"
        )
    elif data == 'calc':
        await query.edit_message_text(
            "Введите название десерта для расчёта:\n"
            "/calculate название\n"
            "Например: /calculate омлет"
        )
    elif data == 'list_rcp':
        await list_recipes(update, context)
    elif data == 'scale':
        await query.edit_message_text(
            "Чтобы пересчитать рецепт на нужный вес/количество:\n"
            "/scale название новое_количество [единица]\n\n"
            "Примеры:\n"
            "/scale торт 2.5 кг\n"
            "/scale печенье 30 шт"
        )
    elif data == 'help':
        await help_command(update, context)
async def export_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import zipfile, io
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        def add_json(data, filename):
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            zip_file.writestr(filename, json_str.encode('utf-8'))
        add_json(ingredients, "ingredients.json")
        add_json(recipes, "recipes.json")
        add_json(settings, "settings.json")
        add_json(sales, "sales.json")
        add_json(customers, "customers.json")
        add_json(orders, "orders.json")
        add_json(plans, "plans.json")
    zip_buffer.seek(0)
    await update.message.reply_document(
        document=zip_buffer,
        filename="backup.zip",
        caption="📦 Полный бэкап данных"
    )
async def list_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все категории, которые есть в рецептах"""
    cats = set()
    for data in recipes.values():
        if isinstance(data, dict) and 'category' in data:
            cats.add(data['category'])
    if not cats:
        await update.message.reply_text("Нет категорий.")
        return
    msg = "📂 *Категории:*\n" + "\n".join(f"• {c}" for c in sorted(cats))
    await update.message.reply_text(msg)
# ========== Главная функция ==========
def main():
    TOKEN = os.environ.get("BOT_TOKEN")

    # Настройка HTTP-клиента с таймаутами (без прокси)

    request = HTTPXRequest(
        connection_pool_size=20,
        connect_timeout=60,
        read_timeout=60,
        write_timeout=60,
        pool_timeout=60
    )
    application = Application.builder().token(TOKEN).request(request).build()
    # Загружаем данные
    global ingredients, recipes, settings
    ingredients.clear()
    ingredients.update(load_data(INGREDIENTS_FILE))
    recipes.clear()
    recipes.update(load_data(RECIPES_FILE))
    load_settings()
    load_sales()
    load_plans()
    load_customers()
    load_orders()
    # Диалог импорта рецепта
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('import_recipe', import_recipe_start)],
        states={
            WAITING_RECIPE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_recipe_text)],
            WAITING_INGREDIENT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ingredient_price)],
            WAITING_RECIPE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_recipe_name)],
            WAITING_RECIPE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_recipe_type)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(conv_handler)
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("add_ingredient", add_ingredient))
    application.add_handler(CommandHandler("ingredients", show_ingredients))
    application.add_handler(CommandHandler("add_recipe", add_recipe))
    application.add_handler(CommandHandler("add_recipe2", add_recipe_scaled))
    application.add_handler(CommandHandler("recipes", list_recipes))
    application.add_handler(CommandHandler("calculate", calculate_cost))
    application.add_handler(CommandHandler("scale", scale_recipe))
    application.add_handler(CommandHandler("remove_ingredient", remove_ingredient))
    application.add_handler(CommandHandler("remove_recipe", remove_recipe))
    application.add_handler(CommandHandler("update_price", update_price))
    application.add_handler(CommandHandler("export", export_data))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("delete_recipes", delete_all_recipes))
    application.add_handler(CommandHandler("set_description", set_description))
    application.add_handler(CommandHandler("show_recipe", show_recipe))
    application.add_handler(CommandHandler("set_hourly_rate", set_hourly_rate))
    application.add_handler(CommandHandler("set_packaging", set_packaging))
    application.add_handler(CommandHandler("set_work_hours", set_work_hours))
    application.add_handler(CommandHandler("set_markup", set_markup))
    application.add_handler(CommandHandler("price_list", price_list))
    application.add_handler(CommandHandler("parse", parse_recipe))
    application.add_handler(CommandHandler("set_category", set_category))
    application.add_handler(CommandHandler("categories", list_categories))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("popular", popular))
    application.add_handler(CommandHandler("add_stock", add_stock))
    application.add_handler(CommandHandler("stock", show_stock))
    application.add_handler(CommandHandler("low_stock", low_stock))
    # Обработчик list_recipes уже есть, но он должен быть зарегистрирован как обычно (он будет принимать аргументы)
    # Единый обработчик для всех текстовых сообщений, кроме команд
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.add_handler(CommandHandler("plan", plan_recipe))
    application.add_handler(CommandHandler("shopping_list", shopping_list))
    application.add_handler(CommandHandler("export_full", export_full))
    application.add_handler(CommandHandler("use", use_recipe))
    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()