from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import TOKEN, BOT_PASS
from aiogram.utils import executor
import sqlite3
from DbQueries import DbQueries
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from MailBot import MailBot
import keyring


class Form(StatesGroup):
    sender_mail = State()
    sender_password = State()
    authorized = State()
    login_password = State()
    dest_mail = State()


# telegram bot connection
bot = Bot(token=TOKEN)
disp = Dispatcher(bot, storage=MemoryStorage())
this_bot_password = BOT_PASS
# database connection
db = sqlite3.connect('EthermailBot.db')
# database queries
queries = DbQueries(db)
queries.create_default_tables()
# mail bots container
mail_bots = {}


async def check_user_id_or_set(state: FSMContext):
    data = await state.get_data()
    if not data or 'user_id_db' not in data or not data['user_id_db']:
        user_id_db = queries.get_user(state.chat)
        await state.update_data(user_id_db=user_id_db)

    return data


def get_manage_mail_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text='Добавить/изменить почту', callback_data='man_add_mail')
        ],
        [
            InlineKeyboardButton(text='Удалить почту', callback_data='man_del_mail')
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    return keyboard


def get_exist_mails_keyboard(mails):
    buttons = []
    for el in mails:
        cur_mail = el[0]
        buttons.append([
            InlineKeyboardButton(text=cur_mail, callback_data=f'del_mail_{cur_mail}')
        ])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    return keyboard


@disp.message_handler(commands=['start'])
async def start_handler(msg: types.Message, state: FSMContext):
    queries.add_user(state.chat, msg.chat.first_name)
    user_id = queries.get_user(state.chat)
    await state.update_data(user_id_db=user_id)
    user_name = msg.chat.first_name if msg.chat.first_name else 'новый пользователь'
    await msg.reply(f'Добро пожаловать, {user_name}!')


@disp.message_handler(commands=['login'], state=None)
async def login_handler(msg: types.Message, state: FSMContext):
    await msg.reply('Пожалуйста, введите пароль')
    await Form.login_password.set()


@disp.message_handler(state=Form.login_password)
async def add_mail_command_mail(msg: types.Message, state: FSMContext):
    await state.update_data(login_password=msg.text)
    if msg.text == this_bot_password:
        await check_user_id_or_set(state)
        await msg.reply('Пароль верный, бот разблокирован')
        await Form.authorized.set()
    else:
        await msg.reply('Неверный пароль!')
        await state.reset_state()


@disp.message_handler(commands=['managesendermail'], state=Form.authorized)
async def manage_mail_command(msg: types.Message, state: FSMContext):
    await state.reset_state(with_data=False)
    await msg.reply('Выберите действие', reply_markup=get_manage_mail_keyboard())


@disp.callback_query_handler(lambda el: el.data.__contains__('man_'))
async def callback_manage_mail(callback_query: types.CallbackQuery):
    call_type = callback_query.data
    if call_type == 'man_add_mail':
        await Form.sender_mail.set()
        await bot.send_message(callback_query.from_user.id, text='Введите адрес почты, с которой будет производиться рассылка')
    elif call_type == 'man_del_mail':
        mails = queries.get_sending_mails(callback_query.from_user.id)
        await bot.send_message(callback_query.from_user.id, text='Выберите почту для удаления', reply_markup=get_exist_mails_keyboard(mails))


@disp.callback_query_handler(lambda el: el.data.__contains__('del_mail_'))
async def callback_manage_mail(callback_query: types.CallbackQuery):
    mail = callback_query.data.removeprefix('del_mail_')
    queries.delete_sending_mail(callback_query.from_user.id, mail)
    await Form.authorized.set()


@disp.message_handler(state=Form.sender_mail)
async def add_mail_command_mail(msg: types.Message, state: FSMContext):
    await state.update_data(mail=msg.text)
    await Form.sender_password.set()
    await msg.reply('Введите пароль для указанной почты')


@disp.message_handler(state=Form.sender_password)
async def add_mail_command_pass(msg: types.Message, state: FSMContext):
    await state.update_data(password=msg.text)
    data = await state.get_data()
    queries.add_sending_mail(data['user_id_db'], data['mail'])
    mail_id: int = queries.get_sending_mail_id(data['user_id_db'], data['mail'])
    keyring.set_password('EthermailBot', mail_id.__str__(), data['password'])
    await Form.authorized.set()


@disp.message_handler(commands=['startmessaging'], state=Form.authorized)
async def start_messaging_command(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    int_sending_mails = queries.get_sending_mails(data['user_id_db'])
    dest_mail = queries.get_dest_mail(data['user_id_db'])
    sending_mails = []
    for el in int_sending_mails:
        mail_id = el[0]
        password = keyring.get_password('EthermailBot', mail_id.__str__())
        sending_mails.append((mail_id, el[1], password))
    mail_bot = MailBot(dest_mail)
    await mail_bot.login_mails(sending_mails)
    mail_bots.update({
        state.chat: mail_bot,
    })
    await mail_bot.start_bot()


@disp.message_handler(commands=['stopmessaging'], state=Form.authorized)
async def stop_messaging_command(msg: types.Message, state: FSMContext):
    mail_bot = mail_bots[state.chat]
    await mail_bot.stop_bot()
    del mail_bots[state.chat]


@disp.message_handler(commands=['setdestmail'], state=Form.authorized)
async def set_dest_mail_command(msg: types.Message, state: FSMContext):
    await msg.reply('Введите адрес почты, на которую будет производиться рассылка')
    await Form.dest_mail.set()


@disp.message_handler(state=Form.dest_mail)
async def dest_mail_handler(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    queries.set_dest_mail(data['user_id_db'], msg.text)
    await Form.authorized.set()


@disp.message_handler(commands=['getinfo'], state=Form.authorized)
async def get_info_command(msg: types.Message, state: FSMContext):
    await msg.reply('Данная команда находится в разработке')


@disp.message_handler(state=Form.authorized)
async def unrec_command_handler(msg: types.Message, state: FSMContext):
    await msg.reply('Команда не распознана')


@disp.message_handler(state=None)
async def refresh_handler(msg: types.Message, state: FSMContext):
    data = await check_user_id_or_set(state)
    if 'login_password' in data and data['login_password'] == this_bot_password:
        await msg.reply(f'Данные были обновлены по причине перезапуска бота. Пожалуйста, повторите последнюю команду')
        await Form.authorized.set()
    else:
        await msg.reply(f'Пожалуйста, авторизуйтесь')
        await state.reset_state()


def start_server():
    executor.start_polling(disp)


if __name__ == '__main__':
    start_server()
