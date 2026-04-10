import random
import asyncio
from datetime import datetime
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, Text, KeyboardButtonColor
import db
import texts

TOKEN = "vk1.a.WV3aK4FNc65zn74TChUFNzYZJB61uXuI5n_ZRvEQz_FiRe08oxtnGjbpfo_D1efNZdg4Y8M_zAaM9ZBUrCd9lxy06cRLXfeNt7FnhVKCl5JRlkMrDfO3P4cq53ofnEUcqkGdf42vMcwWhqLjm3xSYzyxsNlm9pIaw6qcNnW9Dw5amSKclBua-wM45je-7t4o2h0PcME0Bkk09xVMw_NKPQ"

DENS_CONFIG = [{"key":"leader","name":"Палатка предводителя","structure":"underground","preset":92},{"key":"healer","name":"Целительская","structure":"underground","preset":77},{"key":"storage","name":"Хранилище","structure":"underground","preset":93},{"key":"apprentices","name":"Палатка оруженосцев","structure":"underground","preset":88},{"key":"nursery","name":"Детская","structure":"underground","preset":76},{"key":"elders","name":"Палатка старейшин","structure":"branches","preset":75}]

db.init_db(DENS_CONFIG)
bot = Bot(token=TOKEN)
BOOT_MESSAGE = "Племя Ветра. Выбери раздел."

WAITING_BEDDING_OWNER = {}
WAITING_BEDDING_DELETE = {}
WAITING_RENAME_OWNER = {}
WAITING_SHAKE = {}

WEAR_DAYS = {1, 4, 5, 6}


async def wear_scheduler():
    last_worn = None
    while True:
        now = datetime.now()
        today_key = (now.year, now.month, now.day)
        if now.weekday() in WEAR_DAYS and now.hour == 0 and now.minute == 0 and last_worn != today_key:
            last_worn = today_key
            decay = random.randint(1, 10)
            cur = db.get_walls_condition()
            db.set_walls_condition(max(0, cur - decay))
            for den in db.get_all_dens():
                db.set_den_condition(den["key"], max(0, den["condition"] - decay))
            db.wear_all_beddings(decay)
        await asyncio.sleep(30)


def bedding_label(b):
    if b["is_nest"]:
        return f"Гнездо #{b['id']}"
    return f"Подстилка {b['owner']}"


def main_keyboard():
    return (
        Keyboard(one_time=False)
        .add(Text("Подстилки"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Стены"), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("Палатки"), color=KeyboardButtonColor.PRIMARY)
        .get_json()
    )


def bedding_keyboard():
    return (
        Keyboard(one_time=False)
        .add(Text("Скрафтить подстилку"), color=KeyboardButtonColor.POSITIVE)
        .add(Text("Скрафтить гнездо"), color=KeyboardButtonColor.POSITIVE)
        .row()
        .add(Text("Вытряхнуть подстилку"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Уничтожить подстилку"), color=KeyboardButtonColor.NEGATIVE)
        .row()
        .add(Text("Проверить все подстилки"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Блохи"), color=KeyboardButtonColor.NEGATIVE)
        .row()
        .add(Text("Назад"), color=KeyboardButtonColor.SECONDARY)
        .get_json()
    )


def walls_keyboard():
    return (
        Keyboard(one_time=False)
        .add(Text("Скрафтить стены"), color=KeyboardButtonColor.POSITIVE)
        .add(Text("Укрепить стены"), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("Снести стены"), color=KeyboardButtonColor.NEGATIVE)
        .add(Text("Оценить стены"), color=KeyboardButtonColor.SECONDARY)
        .row()
        .add(Text("Назад"), color=KeyboardButtonColor.SECONDARY)
        .get_json()
    )


def dens_keyboard():
    kb = Keyboard(one_time=False)
    dens = db.get_all_dens()
    for i, den in enumerate(dens):
        kb.add(Text(den["name"]), color=KeyboardButtonColor.PRIMARY)
        if (i + 1) % 2 == 0:
            kb.row()
    kb.row()
    kb.add(Text("Назад"), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def den_action_keyboard(den_name):
    return (
        Keyboard(one_time=True)
        .add(Text(f"Починить: {den_name}"), color=KeyboardButtonColor.POSITIVE)
        .add(Text(f"Снести: {den_name}"), color=KeyboardButtonColor.NEGATIVE)
        .row()
        .add(Text(f"Скрафтить: {den_name}"), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("Назад"), color=KeyboardButtonColor.SECONDARY)
        .get_json()
    )


@bot.on.message()
async def bootstrap_text_handler(message: Message):
    text = (message.text or "").strip().lower()
    if text in {"начало", "меню"}:
        await message.answer(BOOT_MESSAGE, keyboard=main_keyboard())


@bot.on.message(text=["Начало", "начало", "Меню", "меню"])
async def start_handler(message: Message):
    await message.answer(BOOT_MESSAGE, keyboard=main_keyboard())


@bot.on.message(text="Подстилки")
async def beddings_menu(message: Message):
    await message.answer("Раздел подстилок.", keyboard=bedding_keyboard())


@bot.on.message(text="Стены")
async def walls_menu(message: Message):
    await message.answer("Раздел стен.", keyboard=walls_keyboard())


@bot.on.message(text="Палатки")
async def dens_menu(message: Message):
    await message.answer("Палатки Племени Ветра. Выбери палатку.", keyboard=dens_keyboard())


@bot.on.message(text="Назад")
async def back_handler(message: Message):
    uid = message.from_id
    WAITING_BEDDING_OWNER.pop(uid, None)
    WAITING_BEDDING_DELETE.pop(uid, None)
    WAITING_RENAME_OWNER.pop(uid, None)
    WAITING_SHAKE.pop(uid, None)
    await message.answer("Главное меню.", keyboard=main_keyboard())


@bot.on.message(text="Скрафтить подстилку")
async def craft_bedding(message: Message):
    WAITING_BEDDING_OWNER[message.from_id] = True
    await message.answer("Подстилка готова. Кому она принадлежит? Напиши имя персонажа.")


@bot.on.message(text="Скрафтить гнездо")
async def craft_nest(message: Message):
    nest_id = db.add_nest()
    await message.answer(f"Гнездо #{nest_id} сплетено. Состояние: 100%.", keyboard=bedding_keyboard())


@bot.on.message(text="Вытряхнуть подстилку")
async def shake_menu(message: Message):
    beddings = db.get_all_beddings()
    if not beddings:
        await message.answer("Нет ни одной подстилки или гнезда.", keyboard=bedding_keyboard())
        return
    lines = ["Какую подстилку вытряхнуть? Напиши номер из списка.\n"]
    for i, b in enumerate(beddings, 1):
        desc = texts.nest_desc(b["condition"]) if b["is_nest"] else texts.bedding_desc_tribe(b["condition"])
        lines.append(f"{i}. {bedding_label(b)} — {desc}")
    WAITING_SHAKE[message.from_id] = [b["id"] for b in beddings]
    await message.answer("\n".join(lines))


@bot.on.message(text="Уничтожить подстилку")
async def destroy_menu(message: Message):
    beddings = db.get_all_beddings()
    if not beddings:
        await message.answer("Нет ни одной подстилки или гнезда.", keyboard=bedding_keyboard())
        return
    lines = ["Выбери, что уничтожить. Напиши номер из списка.\n"]
    for i, b in enumerate(beddings, 1):
        desc = texts.nest_desc(b["condition"]) if b["is_nest"] else texts.bedding_desc_tribe(b["condition"])
        lines.append(f"{i}. {bedding_label(b)} — {desc}")
    WAITING_BEDDING_DELETE[message.from_id] = [b["id"] for b in beddings]
    await message.answer("\n".join(lines))


@bot.on.message(text="Проверить все подстилки")
async def check_beddings(message: Message):
    beddings = db.get_all_beddings()
    if not beddings:
        await message.answer("Подстилок и гнёзд нет.", keyboard=bedding_keyboard())
        return
    lines = []
    for b in beddings:
        if b["is_nest"]:
            desc = texts.nest_desc(b["condition"])
            debuff = texts.nest_debuff(b["condition"])
        else:
            desc = texts.bedding_desc_tribe(b["condition"])
            debuff = texts.bedding_debuff_tribe(b["condition"])
        line = f"{bedding_label(b)}: {desc}"
        if debuff:
            line += f"\n{debuff}"
        lines.append(line)
    await message.answer("\n- - - -\n".join(lines), keyboard=bedding_keyboard())


@bot.on.message(text="Блохи")
async def flea_check(message: Message):
    beddings = db.get_all_beddings()
    bad = [
        b for b in beddings
        if (not b["is_nest"] and b["condition"] <= 40)
        or (b["is_nest"] and b["condition"] <= 20)
    ]
    if not bad:
        await message.answer("Всё в порядке.", keyboard=bedding_keyboard())
        return
    lines = ["Требуют замены:\n"] + [f"{bedding_label(b)} — состояние критическое" for b in bad]
    await message.answer("\n".join(lines), keyboard=bedding_keyboard())


@bot.on.message(text=["Изменить владельца", "изменить владельца"])
async def rename_start(message: Message):
    beddings = [b for b in db.get_all_beddings() if not b["is_nest"]]
    if not beddings:
        await message.answer("Нет подстилок с владельцем.", keyboard=bedding_keyboard())
        return
    lines = ["Выбери подстилку. Напиши её номер из списка.\n"]
    for i, b in enumerate(beddings, 1):
        lines.append(f"{i}. Подстилка {b['owner']}")
    WAITING_RENAME_OWNER[message.from_id] = {"step": "pick", "ids": [b["id"] for b in beddings]}
    await message.answer("\n".join(lines))


@bot.on.message(text="Скрафтить стены")
async def craft_walls(message: Message):
    db.set_walls_condition(25)
    await message.answer("Стены возведены с нуля. Состояние: 25%.", keyboard=walls_keyboard())


@bot.on.message(text="Укрепить стены")
async def repair_walls(message: Message):
    cur = db.get_walls_condition()
    bonus = random.randint(8, 15)
    new_val = db.set_walls_condition(cur + bonus)
    await message.answer(f"Стены укреплены на {bonus}%. Текущее состояние: {new_val}%.", keyboard=walls_keyboard())


@bot.on.message(text="Снести стены")
async def destroy_walls(message: Message):
    db.set_walls_condition(0)
    await message.answer("Стены снесены. Состояние: 0%.", keyboard=walls_keyboard())


@bot.on.message(text="Оценить стены")
async def assess_walls(message: Message):
    cond = db.get_walls_condition()
    await message.answer(f"Лагерные стены: {texts.walls_desc(cond)}", keyboard=walls_keyboard())


@bot.on.message()
async def universal_handler(message: Message):
    uid = message.from_id
    text = message.text.strip()

    if uid in WAITING_BEDDING_OWNER:
        del WAITING_BEDDING_OWNER[uid]
        db.add_bedding(text)
        await message.answer(f"Подстилка закреплена за {text}. Состояние: 100%.", keyboard=bedding_keyboard())
        return

    if uid in WAITING_SHAKE:
        id_list = WAITING_SHAKE.pop(uid)
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(id_list):
                amount = random.randint(2, 4)
                new_val = db.shake_bedding(id_list[idx], amount)
                if new_val is not None:
                    b = db.get_bedding_by_id(id_list[idx])
                    await message.answer(
                        f"{bedding_label(b)} вытряхнута. Состояние улучшилось на {amount}% — теперь {new_val}%.",
                        keyboard=bedding_keyboard()
                    )
                    return
        await message.answer("Неверный номер. Действие отменено.", keyboard=bedding_keyboard())
        return

    if uid in WAITING_BEDDING_DELETE:
        id_list = WAITING_BEDDING_DELETE.pop(uid)
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(id_list):
                result = db.delete_bedding(id_list[idx])
                if result:
                    if result["is_nest"]:
                        await message.answer("Гнездо уничтожено.", keyboard=bedding_keyboard())
                    else:
                        msg = "Подстилка уничтожена."
                        if result["condition"] <= 70 and random.random() < 0.5:
                            msg += " При разборе нашлось немного мха (+1 мох)."
                        await message.answer(msg, keyboard=bedding_keyboard())
                    return
        await message.answer("Неверный номер. Действие отменено.", keyboard=bedding_keyboard())
        return

    if uid in WAITING_RENAME_OWNER:
        state = WAITING_RENAME_OWNER[uid]
        if state["step"] == "pick":
            if text.isdigit():
                idx = int(text) - 1
                if 0 <= idx < len(state["ids"]):
                    state["step"] = "name"
                    state["target_id"] = state["ids"][idx]
                    b = db.get_bedding_by_id(state["target_id"])
                    await message.answer(f"Напиши новое имя владельца подстилки {b['owner']}.")
                    return
            del WAITING_RENAME_OWNER[uid]
            await message.answer("Неверный номер. Действие отменено.", keyboard=bedding_keyboard())
            return
        elif state["step"] == "name":
            new_name = text
            old_name = db.rename_bedding(state["target_id"], new_name)
            del WAITING_RENAME_OWNER[uid]
            if old_name is not None:
                await message.answer(f"Подстилка {old_name} -> Подстилка {new_name}", keyboard=bedding_keyboard())
            else:
                await message.answer("Не удалось изменить владельца.", keyboard=bedding_keyboard())
            return

    dens = db.get_all_dens()
    den_by_name = {d["name"]: d for d in dens}

    if text in den_by_name:
        den = den_by_name[text]
        desc = texts.den_desc(den["structure"], den["condition"])
        await message.answer(f"{den['name']}: {desc}.", keyboard=den_action_keyboard(den["name"]))
        return

    for den in dens:
        if text == f"Починить: {den['name']}":
            bonus = random.randint(7, 11)
            new_val = db.set_den_condition(den["key"], den["condition"] + bonus)
            await message.answer(f"{den['name']} отремонтирована. Состояние: {new_val}%.", keyboard=dens_keyboard())
            return
        if text == f"Снести: {den['name']}":
            db.set_den_condition(den["key"], 0)
            await message.answer(f"{den['name']} снесена. Состояние: 0%.", keyboard=dens_keyboard())
            return
        if text == f"Скрафтить: {den['name']}":
            db.set_den_condition(den["key"], 100)
            await message.answer(f"{den['name']} возведена заново. Состояние: 100%.", keyboard=dens_keyboard())
            return

    await message.answer("Неизвестная команда. Используй кнопки меню.", keyboard=main_keyboard())


if __name__ == "__main__":
    bot.loop_wrapper.add_task(wear_scheduler)
    bot.run_forever()