import os
import logging
import telebot
from config import TELEGRAM_TOKEN
from flask import Flask, request
from keyboards import (
    get_main_keyboard, get_help_inline_keyboard, get_settings_keyboard, 
    get_yes_no_keyboard, get_stores_keyboard, get_store_actions_keyboard
)
from utils import format_bytes
from stores import get_all_stores, get_store_by_id, get_store_info

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Create our bot instance
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Словарь для хранения состояний пользователей
user_states = {}

# Command handlers
@bot.message_handler(commands=['start'])
def start_command(message):
    """Send a message when the command /start is issued."""
    user_first_name = message.from_user.first_name
    logger.info(f"User {message.from_user.id} started the bot")
    
    welcome_message = (
        f"👋 Привет, {user_first_name}!\n\n"
        f"Добро пожаловать в бот сети магазинов. С моей помощью вы можете:\n"
        f"• Найти ближайший магазин\n"
        f"• Узнать адрес и часы работы\n"
        f"• Связаться с магазином через Telegram\n\n"
        f"Используйте кнопки ниже для навигации."
    )
    
    # Отправляем приветственное сообщение с основной клавиатурой
    bot.send_message(message.chat.id, welcome_message, reply_markup=get_main_keyboard())

@bot.message_handler(commands=['help'])
def help_command(message):
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 *Меню помощи*\n\n"
        "Вот команды, которые я понимаю:\n\n"
        "*/start* - Запустить бота и получить приветственное сообщение\n"
        "*/help* - Показать это сообщение помощи\n"
        "*/stores* - Показать список магазинов\n"
        "*/about* - Информация о боте\n\n"
        "Для получения дополнительной информации, выберите тему ниже:"
    )
    
    # Отправляем сообщение помощи с inline клавиатурой тем помощи
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown", reply_markup=get_help_inline_keyboard())

@bot.message_handler(commands=['about'])
def about_command(message):
    """Send information about the bot."""
    about_text = (
        "*О боте*\n\n"
        "Этот бот создан для сети магазинов, чтобы помочь клиентам:\n"
        "• Найти ближайший магазин\n"
        "• Узнать адрес и часы работы\n"
        "• Связаться с магазином через Telegram\n\n"
        "Версия: 1.0.0\n"
        "Разработано с использованием pyTelegramBotAPI"
    )
    
    bot.send_message(message.chat.id, about_text, parse_mode="Markdown")

@bot.message_handler(commands=['stores'])
def stores_command(message):
    """Show list of stores."""
    show_stores_list(message)

def show_stores_list(message):
    """Show list of all stores with keyboard."""
    stores_text = (
        "*Наши магазины*\n\n"
        "Выберите магазин из списка ниже, чтобы узнать подробную информацию:"
    )
    
    bot.send_message(
        message.chat.id, 
        stores_text, 
        parse_mode="Markdown", 
        reply_markup=get_stores_keyboard()
    )
    
    # Устанавливаем состояние пользователя для обработки выбора магазина
    user_states[message.from_user.id] = 'selecting_store'

def show_store_details(message, store_name):
    """Show details about a specific store."""
    # Найти магазин по имени
    stores = get_all_stores()
    store = None
    
    for s in stores:
        if s['name'] == store_name:
            store = s
            break
    
    if not store:
        bot.send_message(
            message.chat.id, 
            f"Извините, не могу найти информацию о магазине '{store_name}'.", 
            reply_markup=get_stores_keyboard()
        )
        return
    
    # Получаем информацию о магазине
    store_info_text = get_store_info(store['id'])
    
    # Отправляем информацию с клавиатурой действий
    bot.send_message(
        message.chat.id, 
        store_info_text, 
        parse_mode="Markdown", 
        reply_markup=get_store_actions_keyboard(store['id'], store['telegram'])
    )

# Обработчик для callback-запросов от inline-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Handle callback queries from inline keyboards."""
    user_id = call.from_user.id
    logger.info(f"Received callback from {user_id}: {call.data}")
    
    # Обработка кнопок помощи
    if call.data == 'help_stores':
        text = ("*Как найти магазин*\n\n"
                "Вы можете найти ближайший магазин несколькими способами:\n\n"
                "1. Нажмите кнопку '🏪 Магазины' в главном меню\n"
                "2. Используйте команду /stores\n"
                "3. Выберите магазин из списка, чтобы увидеть его адрес и другую информацию")
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'help_contact':
        text = ("*Как связаться с магазином*\n\n"
                "Чтобы связаться с конкретным магазином:\n\n"
                "1. Выберите магазин из списка\n"
                "2. В информации о магазине нажмите кнопку 'Написать в Telegram'\n"
                "3. Вы будете перенаправлены в чат Telegram с этим магазином\n\n"
                "Также вы можете позвонить по телефону магазина, указанному в информации")
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'help_text':
        text = ("*Текстовые команды*\n\n"
                "Бот понимает следующие текстовые команды:\n"
                "• /start - начать работу с ботом\n"
                "• /help - получить помощь\n"
                "• /stores - список магазинов\n"
                "• /about - информация о боте\n\n"
                "Также вы можете использовать кнопки на клавиатуре для быстрого доступа.")
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == 'back_to_main':
        help_command(call.message)
        
    # Обработка действий с магазинами
    elif call.data == 'back_to_stores':
        show_stores_list(call.message)
        
    elif call.data.startswith('map_'):
        # Извлекаем ID магазина
        try:
            store_id = int(call.data.split('_')[1])
            store = get_store_by_id(store_id)
            
            if store:
                bot.send_message(
                    call.message.chat.id, 
                    f"Карта магазина '{store['name']}'\n\nАдрес: {store['address']}\n\n"
                    f"К сожалению, прямо сейчас у меня нет встроенной карты, "
                    f"но вы можете найти этот адрес в любом картографическом сервисе."
                )
            else:
                bot.send_message(call.message.chat.id, "Информация о магазине не найдена.")
        except (ValueError, IndexError):
            bot.send_message(call.message.chat.id, "Произошла ошибка при обработке запроса.")
    
    # Уведомляем Telegram, что обработали callback
    bot.answer_callback_query(call.id)

# Message handlers
@bot.message_handler(content_types=['text'])
def handle_text_message(message):
    """Handle text messages."""
    user_message = message.text
    user_id = message.from_user.id
    
    logger.info(f"Received text message from {user_id}: {user_message}")
    
    # Проверяем состояние пользователя
    user_state = user_states.get(user_id)
    
    # Обрабатываем кнопки основной клавиатуры
    if user_message == '🏪 Магазины':
        show_stores_list(message)
        
    elif user_message == '🔍 Помощь':
        help_command(message)
        
    elif user_message == 'ℹ️ О боте':
        about_command(message)
        
    elif user_message == '📝 Обратная связь':
        feedback_text = "Пожалуйста, напишите ваш отзыв или предложение:"
        sent = bot.send_message(message.chat.id, feedback_text)
        bot.register_next_step_handler(sent, process_feedback)
        
    elif user_message == '🔙 Назад':
        back_text = "Вы вернулись в главное меню"
        bot.send_message(message.chat.id, back_text, reply_markup=get_main_keyboard())
        # Сбрасываем состояние пользователя
        if user_id in user_states:
            del user_states[user_id]
            
    # Если пользователь в режиме выбора магазина
    elif user_state == 'selecting_store':
        # Проверяем, выбрал ли пользователь магазин из списка
        stores = get_all_stores()
        store_names = [store['name'] for store in stores]
        
        if user_message in store_names:
            show_store_details(message, user_message)
        else:
            # Если сообщение не соответствует ни одному магазину
            bot.send_message(
                message.chat.id, 
                "Пожалуйста, выберите магазин из списка или вернитесь в главное меню.",
                reply_markup=get_stores_keyboard()
            )
    else:
        # Обрабатываем любые другие сообщения
        response = f"Я не совсем понимаю, что вы имеете в виду. Пожалуйста, используйте кнопки меню для навигации."
        bot.send_message(message.chat.id, response, reply_markup=get_main_keyboard())

# Обработчик обратной связи
def process_feedback(message):
    """Process feedback message."""
    feedback = message.text
    user_id = message.from_user.id
    
    logger.info(f"Received feedback from {user_id}: {feedback}")
    
    # Здесь можно сохранить отзыв в базу данных или отправить администратору
    
    thank_you = "Спасибо за ваш отзыв! Мы обязательно рассмотрим его."
    bot.send_message(message.chat.id, thank_you, reply_markup=get_main_keyboard())

# Flask web app for webhook (production) mode
app = Flask(__name__)

@app.route('/')
def index():
    bot_info = bot.get_me()
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Telegram Bot - {bot_info.first_name}</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            body {{
                padding: 20px;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
            }}
            .feature-list {{
                margin-top: 20px;
            }}
            .feature-item {{
                margin-bottom: 10px;
            }}
        </style>
    </head>
    <body data-bs-theme="dark">
        <div class="container">
            <div class="py-5 text-center">
                <h1>Бот для сети магазинов - {bot_info.first_name}</h1>
                <p class="lead">Этот бот поможет клиентам найти информацию о магазинах и связаться с ними.</p>
                <a href="https://t.me/{bot_info.username}" class="btn btn-primary" target="_blank">
                    Открыть бота в Telegram
                </a>
            </div>
            
            <div class="row feature-list">
                <div class="col-md-6">
                    <div class="card mb-4">
                        <div class="card-header">
                            <h3>Возможности бота</h3>
                        </div>
                        <div class="card-body">
                            <ul class="list-group list-group-flush">
                                <li class="list-group-item">Просмотр списка магазинов</li>
                                <li class="list-group-item">Информация о каждом магазине</li>
                                <li class="list-group-item">Связь с магазинами через Telegram</li>
                                <li class="list-group-item">Обратная связь</li>
                            </ul>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="card mb-4">
                        <div class="card-header">
                            <h3>Команды</h3>
                        </div>
                        <div class="card-body">
                            <ul class="list-group list-group-flush">
                                <li class="list-group-item">/start - Запуск бота</li>
                                <li class="list-group-item">/help - Помощь по использованию</li>
                                <li class="list-group-item">/stores - Список магазинов</li>
                                <li class="list-group-item">/about - О боте</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="text-center py-3 mt-3">
                <p>Статус бота: <span class="badge bg-success">Онлайн</span></p>
                <p class="text-muted">© 2025 Сеть магазинов</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'OK'

# Configure webhook for production
def setup_webhook(url):
    bot.remove_webhook()
    bot.set_webhook(url=url + '/webhook')
    logger.info(f"Webhook set to {url}/webhook")

# Entry point
if __name__ == "__main__":
    # Use polling for development (Replit)
    # Check if we're running in the Flask server or standalone
    if os.environ.get('FLASK_RUN', '0') == '1':
        # We're running within the Flask/Gunicorn server, don't start polling
        logger.info("Running in Flask mode")
        webhook_url = os.environ.get('WEBHOOK_URL')
        if webhook_url:
            setup_webhook(webhook_url)
    else:
        # We're running standalone, start polling
        logger.info("Starting bot in polling mode...")
        bot.remove_webhook()
        bot.infinity_polling()