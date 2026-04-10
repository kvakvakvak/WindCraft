import random
import asyncio
import datetime
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, Text, KeyboardButtonColor
import db
import texts


TOKEN = "vk1.a.WV3aK4FNc65zn74TChUFNzYZJB61uXuI5n_ZRvEQz_FiRe08oxtnGjbpfo_D1efNZdg4Y8M_zAaM9ZBUrCd9lxy06cRLXfeNt7FnhVKCl5JRlkMrDfO3P4cq53ofnEUcqkGdf42vMcwWhqLjm3xSYzyxsNlm9pIaw6qcNnW9Dw5amSKclBua-wM45je-7t4o2h0PcME0Bkk09xVMw_NKPQ"


DENS_CONFIG = [
    {"key": "leader", "name": "Палатка предводителя", "structure": "underground", "preset": 92},
    {"key": "healer", "name": "Целительская", "structure": "underground", "preset": 77},
    {"key": "storage", "name": "Хранилище", "structure": "underground", "preset": 93},
    {"key": "apprentices", "name": "Палатка оруженосцев", "structure": "underground", "preset": 88},
    {"key": "nursery", "name": "Детская", "structure": "underground", "preset": 76},
    {"key": "elders", "name": "Палатка старейшин", "structure": "branches", "preset": 75},
]

DECAY_DAYS = {1, 4, 5, 6}  # вт=1, пт=4, сб=5, вс=6 (понедельник=0)


async def wear_scheduler():
    while True:
        now = datetime.datetime.now()
        weekday = now.weekday()

        if weekday in DECAY_DAYS:
            # подстилки и гнёзда: минус 2–5
            bed_decay = random.randint(2, 5)
            db.lower_all_beddings(bed_decay)

            # стены: минус 2–4
            wall_decay = random.randint(2, 4)
            db.lower_walls(wall_decay)

            # палатки: минус 2–4
            dens_decay = random.randint(2, 4)
            db.lower_all_dens(dens_decay)

        # ждать до следующего дня (24 часа)
        await asyncio.sleep(24 * 60 * 60)


db.init_db(DENS_CONFIG)
bot = Bot(token=TOKEN)
BOOT_MESSAGE = "Выберите раздел."

WAITING_BEDDING_OWNER = {}
WAITING_BEDDING_DELETE = {}
WAITING_RENAME_OWNER = {}
WAITING_SHAKE = {}


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
        .add(Text("Вытряхнуть"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Уничтожить"), color=KeyboardButtonColor.NEGATIVE)
        .row()
        .add(Text("Проверить все"), color=KeyboardButtonColor.PRIMARY)
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
        .add(Text(f"Скрафтить: {den_name}"), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("Назад"), color=KeyboardButtonColor.SECONDARY)
        .get_json()
    )


@bot.on.private_message()
async def universal_handler(message: Message):
    uid = message.from_id
    text = (message.text or "").strip()

    if not text:
        return

    lowered = text.lower()

    if lowered in {"меню крафта", "меню"}:
        await message.answer(BOOT_MESSAGE, keyboard=main_keyboard())
        return

    if text == "Подстилки":
        await message.answer("Раздел подстилок.", keyboard=bedding_keyboard())
        return

    if text == "Стены":
        await message.answer("Раздел стен.", keyboard=walls_keyboard())
        return

    if text == "Палатки":
        await message.answer("Палатки Племени Ветра. Выберите палатку.", keyboard=dens_keyboard())
        return

    if text == "Назад":
        WAITING_BEDDING_OWNER.pop(uid, None)
        WAITING_BEDDING_DELETE.pop(uid, None)
        WAITING_RENAME_OWNER.pop(uid, None)
        WAITING_SHAKE.pop(uid, None)
        await message.answer("Главное меню.", keyboard=main_keyboard())
        return

    if text == "Скрафтить подстилку":
        WAITING_BEDDING_OWNER[uid] = True
        await message.answer("Подстилка готова. Кому она принадлежит? (Имя персонажа в именительном падеже).")
        return

    if text == "Скрафтить гнездо":
        nest_id = db.add_nest()
        await message.answer(f"Гнездо #{nest_id} сплетено. Состояние: 100%.", keyboard=bedding_keyboard())
        return

    if text == "Вытряхнуть":
        beddings = db.get_all_beddings()
        if not beddings:
            await message.answer("Нет ни одной подстилки или гнезда.", keyboard=bedding_keyboard())
            return
        lines = ["Какую подстилку вытряхнуть? Напишите номер из списка.\n"]
        for i, b in enumerate(beddings, 1):
            desc = texts.nest_desc(b["condition"]) if b["is_nest"] else texts.bedding_desc_tribe(b["condition"])
            lines.append(f"{i}. {bedding_label(b)} — {desc}")
        WAITING_SHAKE[uid] = [b["id"] for b in beddings]
        await message.answer("\n".join(lines))
        return

    if text == "Уничтожить":
        beddings = db.get_all_beddings()
        if not beddings:
            await message.answer("Нет ни одной подстилки или гнезда.", keyboard=bedding_keyboard())
            return
        lines = ["Выбери, что уничтожить. Напишите номер из списка.\n"]
        for i, b in enumerate(beddings, 1):
            desc = texts.nest_desc(b["condition"]) if b["is_nest"] else texts.bedding_desc_tribe(b["condition"])
            lines.append(f"{i}. {bedding_label(b)} — {desc}")
        WAITING_BEDDING_DELETE[uid] = [b["id"] for b in beddings]
        await message.answer("\n".join(lines))
        return

    if text == "Проверить все":
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
        return

    if text == "Блохи":
        beddings = db.get_all_beddings()
        bad = [
            b for b in beddings
            if (not b["is_nest"] and b["condition"] <= 40)
            or (b["is_nest"] and b["condition"] <= 20)
        ]
        if not bad:
            await message.answer("Всё в порядке.", keyboard=bedding_keyboard())
            return
        lines = ["Требуют замены:\n"] + [f"{bedding_label(b)}" for b in bad]
        await message.answer("\n".join(lines), keyboard=bedding_keyboard())
        return

    if lowered == "изменить владельца":
        beddings = [b for b in db.get_all_beddings() if not b["is_nest"]]
        if not beddings:
            await message.answer("Нет подстилок с владельцем.", keyboard=bedding_keyboard())
            return
        lines = ["Выбери подстилку. Напиши её номер из списка.\n"]
        for i, b in enumerate(beddings, 1):
            lines.append(f"{i}. Подстилка. Владелец — {b['owner']}")
        WAITING_RENAME_OWNER[uid] = {"step": "pick", "ids": [b["id"] for b in beddings]}
        await message.answer("\n".join(lines))
        return

    if text == "Скрафтить стены":
        db.set_walls_condition(25)
        await message.answer("Стены возведены с нуля. Состояние: 25%.", keyboard=walls_keyboard())
        return

    if text == "Укрепить стены":
        cur = db.get_walls_condition()
        bonus = random.randint(8, 15)
        new_val = db.set_walls_condition(cur + bonus)
        await message.answer(f"Стены укреплены на {bonus}%. Текущее состояние: {new_val}%.", keyboard=walls_keyboard())
        return

    if text == "Оценить стены":
        cond = db.get_walls_condition()
        await message.answer(f"Лагерные стены: {texts.walls_desc(cond)}", keyboard=walls_keyboard())
        return

    if lowered == "снести стены":
        db.set_walls_condition(0)
        await message.answer("Стены снесены. Состояние: 0%.", keyboard=walls_keyboard())
        return

    if uid in WAITING_BEDDING_OWNER:
        WAITING_BEDDING_OWNER.pop(uid, None)
        db.add_bedding(text)
        await message.answer(f"Владелец подстилки — {text}. Состояние: 100%.", keyboard=bedding_keyboard())
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
                            msg += " При разборе нашлось немного пригодного мха (х1 мох)."
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
                    await message.answer(f"Напишите новое имя владельца подстилки {b['owner']}.")
                    return
            WAITING_RENAME_OWNER.pop(uid, None)
            await message.answer("Неверный номер. Действие отменено.", keyboard=bedding_keyboard())
            return

        if state["step"] == "name":
            new_name = text
            old_name = db.rename_bedding(state["target_id"], new_name)
            WAITING_RENAME_OWNER.pop(uid, None)
            if old_name is not None:
                await message.answer(f"Подстилка {old_name} -> Подстилка {new_name}", keyboard=bedding_keyboard())
            else:
                await message.answer("Не удалось изменить владельца.", keyboard=bedding_keyboard())
            return

    if lowered.startswith("понизить значение подстилок на "):
        try:
            amount = int(lowered.replace("понизить значение подстилок на ", "").strip())
            if amount < 0:
                await message.answer("Число должно быть положительным.", keyboard=bedding_keyboard())
                return

            beddings = db.get_all_beddings()
            if not beddings:
                await message.answer("Подстилок и гнёзд нет.", keyboard=bedding_keyboard())
                return

            db.lower_all_beddings(amount)
            await message.answer(
                f"Значение всех подстилок и гнёзд понижено на {amount}%.",
                keyboard=bedding_keyboard()
            )
            return
        except ValueError:
            await message.answer("После команды нужно указать число.", keyboard=bedding_keyboard())
            return

    if lowered.startswith("понизить значение стен на "):
        try:
            amount = int(lowered.replace("понизить значение стен на ", "").strip())
            if amount < 0:
                await message.answer("Число должно быть положительным.", keyboard=walls_keyboard())
                return

            new_value = db.lower_walls(amount)
            await message.answer(
                f"Значение стен понижено на {amount}%. Теперь состояние стен: {new_value}%.",
                keyboard=walls_keyboard()
            )
            return
        except ValueError:
            await message.answer("После команды нужно указать число.", keyboard=walls_keyboard())
            return

    if lowered.startswith("понизить значение палаток на "):
        try:
            amount = int(lowered.replace("понизить значение палаток на ", "").strip())
            if amount < 0:
                await message.answer("Число должно быть положительным.", keyboard=dens_keyboard())
                return

            dens_list = db.get_all_dens()
            if not dens_list:
                await message.answer("Палаток нет.", keyboard=dens_keyboard())
                return

            db.lower_all_dens(amount)
            await message.answer(
                f"Значение всех палаток понижено на {amount}%.",
                keyboard=dens_keyboard()
            )
            return
        except ValueError:
            await message.answer("После команды нужно указать число.", keyboard=dens_keyboard())
            return

    if lowered in {"показать все значения", "показать все проценты"}:
        lines = ["Все текущие значения:\n"]

        walls = db.get_walls_condition()
        lines.append(f"Стены — {walls}%")
        lines.append("")

        lines.append("Палатки:")
        dens_list = db.get_all_dens()
        if dens_list:
            for den in dens_list:
                lines.append(f"- {den['name']} — {den['condition']}%")
        else:
            lines.append("- Палаток нет")
        lines.append("")

        lines.append("Подстилки и гнёзда:")
        beddings = db.get_all_beddings()
        if beddings:
            for b in beddings:
                if b["is_nest"]:
                    lines.append(f"- Гнездо #{b['id']} — {b['condition']}%")
                else:
                    lines.append(f"- Подстилка {b['owner']} — {b['condition']}%")
        else:
            lines.append("- Подстилок и гнёзд нет")

        await message.answer("\n".join(lines), keyboard=main_keyboard())
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

        if text == f"Скрафтить: {den['name']}":
            db.set_den_condition(den["key"], 100)
            await message.answer(f"{den['name']} возведена заново. Состояние: 100%.", keyboard=dens_keyboard())
            return

        if lowered == f"снести: {den['name'].lower()}":
            db.set_den_condition(den["key"], 0)
            await message.answer(f"{den['name']} снесена. Состояние: 0%.", keyboard=dens_keyboard())
            return

    await message.answer("Неизвестная команда. Используй кнопки меню.", keyboard=main_keyboard())


if __name__ == "__main__":
    bot.loop_wrapper.add_task(wear_scheduler())
    bot.run_forever()
