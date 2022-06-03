import asyncio
import logging
import operator
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text, CommandStart
from aiogram_dialog import DialogRegistry, StartMode
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, Window, Dialog
from aiogram_dialog.widgets.kbd import Select, Button, Row, Column, SwitchTo
from aiogram_dialog.widgets.managed import ManagedWidgetAdapter
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.input import TextInput

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


API_TOKEN = "TOKEN HERE"


class SettingsDialogSG(StatesGroup):
    main = State()
    users = State()
    delete = State()
    add = State()


class ConfirmSG(StatesGroup):
    main = State()


async def get_confirmation_data(dialog_manager: DialogManager, **kwargs):
    start_data = dialog_manager.current_context().start_data
    return {
        "text": start_data.get("text", "Are you sure?"),
        "process": start_data.get("process", "No"),
        "telegram_id": start_data.get("telegram_id", "0"),
        "description": start_data.get("description", "Нет описания"),
        "items": start_data.get("items", [(1, "Yes"), (2, "No")])
    }


async def get_users(**kwargs):
    users = [
        ("1123123", "user 1"),
        ("2123123", "user 2"),
        ("3123331", "user 3"),
    ]
    return {
        "users": users
    }


btn_settings = KeyboardButton("🛠 Настройки")
main_keyboard = ReplyKeyboardMarkup(
    resize_keyboard=True,
    one_time_keyboard=True
)
main_keyboard.add(btn_settings)


async def bot_start(message: Message):
    await message.answer(f"Привет {message.from_user.full_name}!", reply_markup=main_keyboard)
    logging.info("Пользователь {username} начал сеанс".format(username=message.from_user.username))


async def settings_dialog_start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(SettingsDialogSG.main, mode=StartMode.RESET_STACK)


async def cancel(call: CallbackQuery, button: Button, manager: DialogManager):
    await call.message.edit_text('Операция отменена')
    await manager.done()
    await call.message.answer(text="Выберите диалог", reply_markup=main_keyboard)


async def go_to_main(call: CallbackQuery, button: Button, manager: DialogManager):
    await manager.dialog().switch_to(SettingsDialogSG.main)


async def delete_user(call: CallbackQuery, button: ManagedWidgetAdapter[Select], manager: DialogManager, selected_user: str):
    await manager.start(
        ConfirmSG.main, data={"text": f"Удалить {selected_user} ?",
                              "telegram_id": f"{selected_user}",
                              "process": "delete"},
    )


async def save_user(call: CallbackQuery, button: Button, manager: DialogManager, data: str):
    telegram_id = data.split(' ')[0]
    description = data.split(' ')[1]
    await manager.start(
        ConfirmSG.main, data={"text": f"Сохранить {telegram_id} ?",
                              "telegram_id": f"{telegram_id}",
                              "description": f"{description}",
                              "process": "add"},
    )


async def confirm_operation(call: CallbackQuery, select, manager: DialogManager, data):
    context = manager.current_context()
    process = context.start_data.get('process')
    telegram_id = context.start_data.get('telegram_id')
    description = context.start_data.get('description')
    if process == 'delete':
        if data == '1':
            print(f"Процесс удаления пользователя {telegram_id}")
            await call.message.answer(f'Пользователь {telegram_id} удален')
        else:
            print(f"Процесс удаления отменён")
            await call.message.answer(f'Удаление отменено')
    elif process == 'add':
        if data == '1':
            print(f"Процесс добавления пользователя {telegram_id} : {description}")
            await call.message.answer(f'Пользователь {telegram_id} добавлен')
        else:
            print(f"Процесс добавления отменён")
            await call.message.answer(f'Добавление отменено')
    else:
        print(f"Ошибка. Передан несуществующий процесс")
    await manager.done({
        **manager.current_context().start_data,
        "result": data,
    })
    await manager.done()
    await call.message.answer(text="Выберите диалог", reply_markup=main_keyboard)


confirm_dialog = Dialog(
    Window(
        Format("{text}"),
        Select(
            text=Format("{item[1]}"),
            id="s_confirm",
            items="items",
            item_id_getter=operator.itemgetter(0),
            on_click=confirm_operation,
        ),
        state=ConfirmSG.main,
        getter=get_confirmation_data,
    ),
)


settings_dialog = Dialog(
    Window(
        Const("Настройки"),
        Button(Const("Все пользователи"), id="get_users", on_click=SwitchTo(Const(""), id="_", state=SettingsDialogSG.users)),
        Button(Const("Добавить пользователя"), id="add_user", on_click=SwitchTo(Const(""), id="_", state=SettingsDialogSG.add)),
        Button(Const("Удалить пользователя"), id="del_user", on_click=SwitchTo(Const(""), id="_", state=SettingsDialogSG.delete)),
        Button(Const("Отмена"), id="cancel", on_click=cancel),
        state=SettingsDialogSG.main,
    ),
    Window(
        Const("Зарегистрированные пользователи:"),
        Column(
            Select(
                Format("{item[0]} : {item[1]}"),
                id="s_users",
                item_id_getter=operator.itemgetter(0),
                items="users",
            ),
        ),
        Row(
            Button(Const("Назад"), id="back", on_click=go_to_main),
            Button(Const("Отмена"), id="cancel", on_click=cancel),
        ),
        state=SettingsDialogSG.users,
        getter=get_users,
    ),
    Window(
        Const("Введите пользовательские данные в формате: <telegram_id> <description>"),
        TextInput(id="user_data", on_success=save_user),
        Row(
            Button(Const("Назад"), id="back", on_click=go_to_main),
            Button(Const("Отмена"), id="cancel", on_click=cancel),
            ),
        state=SettingsDialogSG.add,
    ),
    Window(
        Const("Выберите пользователя для удаления:"),
        Column(
            Select(
                Format("{item[0]} : {item[1]}"),
                id="s_users",
                item_id_getter=operator.itemgetter(0),
                items="users",
                on_click=delete_user,
            ),
        ),
        Row(
            Button(Const("Назад"), id="back", on_click=go_to_main),
            Button(Const("Отмена"), id="cancel", on_click=cancel),
        ),
        state=SettingsDialogSG.delete,
        getter=get_users,
    ),
)


async def main():
    logging.basicConfig(level=logging.INFO)
    storage = MemoryStorage()
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(bot, storage=storage)
    registry = DialogRegistry(dp)
    dp.register_message_handler(bot_start, CommandStart(), state='*')
    dp.register_message_handler(settings_dialog_start, Text(equals="🛠 Настройки"))
    registry.register(confirm_dialog)
    registry.register(settings_dialog)
    await dp.start_polling()


if __name__ == '__main__':
    asyncio.run(main())
