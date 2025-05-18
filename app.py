from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
import requests
import logging
from typing import Dict, List

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class Config:
    BOT_TOKEN = "7876032803:AAEvI5NvECzAhJH34Jb4hG3Iee8WmwJLrkw"
    KINOPOISK_API_KEY = "d85e3525-959b-47bd-9df9-b45e2387404e"
    MAX_RESULTS = 7
    REQUEST_TIMEOUT = 15


SEARCH, DETAILS = range(2)


def format_film_info(film: Dict) -> str:
    title = film.get("nameRu", "Без названия")
    original_title = film.get("nameEn", "")
    year = film.get("year", "не указан")
    rating_kp = film.get("ratingKinopoisk", "нет")
    rating_imdb = film.get("ratingImdb", "нет")

    countries = [c["country"] for c in film.get("countries", [])]
    genres = [g["genre"] for g in film.get("genres", [])]

    return (
        f"🎬 <b>{title}</b>\n"
        f"🏷 <i>{original_title}</i>\n"
        f"📅 Год: <b>{year}</b>\n"
        f"🌍 Страны: <b>{', '.join(countries) if countries else 'не указаны'}</b>\n"
        f"🎭 Жанры: <b>{', '.join(genres) if genres else 'не указаны'}</b>\n"
        f"⭐ Кинопоиск: <b>{rating_kp}</b>\n"
        f"⭐ Рейтинг: <b>{rating_imdb}</b>\n"
    )


def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск фильмов", callback_data="start_search")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_film_details_keyboard(film_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📌 Кинопоиск", url=f"https://www.kinopoisk.ru/film/{film_id}/")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def get_actors(film_id: int) -> str:
    try:
        url = f"https://kinopoiskapiunofficial.tech/api/v1/staff?filmId={film_id}"
        headers = {
            "X-API-KEY": Config.KINOPOISK_API_KEY,
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=Config.REQUEST_TIMEOUT)
        response.raise_for_status()

        staff = response.json()
        actors = [person for person in staff if person.get("professionKey") == "ACTOR"]
        actors = sorted(actors, key=lambda x: x.get("order", 0))[:10]

        if not actors:
            return "Информация об актерах отсутствует."

        actors_list = []
        for actor in actors:
            name = actor.get("nameRu", actor.get("nameEn", "Неизвестный актер"))
            role = actor.get("description", "")
            actors_list.append(f"• <b>{name}</b> - {role if role else 'роль не указана'}")

        return "👨‍👩‍👧‍👦 <b>Актерский состав:</b>\n\n" + "\n".join(actors_list)

    except Exception as e:
        logger.error(f"Ошибка при получении актеров: {str(e)}")
        return "Не удалось загрузить информацию об актерах."


async def get_similar_films(film_id: int) -> str:
    try:
        url = f"https://kinopoiskapiunofficial.tech/api/v2.2/films/{film_id}/similars"
        headers = {
            "X-API-KEY": Config.KINOPOISK_API_KEY,
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=Config.REQUEST_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        similar_films = data.get("items", [])[:5]

        if not similar_films:
            return "Похожие фильмы не найдены."

        films_list = []
        for film in similar_films:
            title = film.get("nameRu", film.get("nameEn", "Без названия"))
            year = film.get("year", "")
            films_list.append(f"• <b>{title}</b> ({year})")

        return "📺 <b>Похожие фильмы:</b>\n\n" + "\n".join(films_list)

    except Exception as e:
        logger.error(f"Ошибка при получении похожих фильмов: {str(e)}")
        return "Не удалось загрузить похожие фильмы."


async def get_where_to_watch(film_id: int) -> str:
    try:
        url = f"https://kinopoiskapiunofficial.tech/api/v2.2/films/{film_id}/distributions"
        headers = {
            "X-API-KEY": Config.KINOPOISK_API_KEY,
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=Config.REQUEST_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        distributions = data.get("items", [])

        if not distributions:
            return (
                "🍿 <b>Где посмотреть?</b>\n\n"
                "Информация о доступных платформах отсутствует.\n\n"
                "Попробуйте поискать на:\n"
                "• Кинопоиск: https://www.kinopoisk.ru/film/{film_id}/\n"
                "• IVI: https://www.ivi.ru/search/\n"
                "• Netflix: https://www.netflix.com/search"
            )

        platforms = []
        for dist in distributions:
            if dist.get("type") == "SUBSCRIPTION":
                platform = dist.get("platform", {}).get("name", "Неизвестная платформа")
                platforms.append(f"• {platform}")

        if not platforms:
            platforms = ["• Информация о подписках отсутствует"]

        return (
                "🍿 <b>Где посмотреть?</b>\n\n"
                "Доступен на платформах:\n" + "\n".join(platforms) + "\n\n" +
                "Также попробуйте:\n"
                "• Кинопоиск: https://www.kinopoisk.ru/film/{film_id}/\n"
                "• IVI: https://www.ivi.ru/search/\n"
                "• Netflix: https://www.netflix.com/search"
        )

    except Exception as e:
        logger.error(f"Ошибка при получении информации о платформах: {str(e)}")
        return (
            "🍿 <b>Где посмотреть?</b>\n\n"
            "Не удалось загрузить информацию о платформах.\n\n"
            "Попробуйте поискать на:\n"
            "• Кинопоиск: https://www.kinopoisk.ru/film/{film_id}/\n"
            "• IVI: https://www.ivi.ru/search/\n"
            "• Netflix: https://www.netflix.com/search"
        )


async def start_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    welcome_text = (
        f"🎥 <b>Привет, {user.first_name}!</b> 👋\n\n"
        "Я - умный кино-бот, который поможет тебе найти информацию о фильмах и сериалах."
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=create_main_menu_keyboard(),
        parse_mode="HTML"
    )


async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "<b>Как искать:</b>\n"
        "1. Нажмите кнопку '🔍 Поиск фильмов'\n"
        "2. Введите название фильма или сериала\n"
        "3. Выберите из списка результат\n"
        "4. Просматривайте подробную информацию\n\n"
        "В любой момент вы можете вернуться в главное меню."
    )

    if update.message:
        await update.message.reply_text(
            help_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
            ])
        )
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            help_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
            ])
        )


async def help_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    help_text = (
        "<b>Как искать:</b>\n"
        "1. Нажмите кнопку '🔍 Поиск фильмов'\n"
        "2. Введите название фильма или сериала\n"
        "3. Выберите из списка результат\n"
        "4. Просматривайте подробную информацию\n\n"
        "В любой момент вы можете вернуться в главное меню."
    )

    await query.edit_message_text(
        help_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
        ])
    )


async def start_search(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🔍 <b>Введите название фильма или сериала:</b>\n\n"
        "Можно уточнить год выпуска для более точного поиска.\n"
        "<i>Пример: Криминальное чтиво 1994</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
        ])
    )

    return SEARCH


async def process_search(update: Update, context: CallbackContext) -> int:
    search_query = update.message.text
    context.user_data['search_query'] = search_query
    context.user_data['search_results'] = []

    await update.message.reply_text(f"🔍 Ищу фильмы по запросу: <b>{search_query}</b>...", parse_mode="HTML")

    try:
        url = f"https://kinopoiskapiunofficial.tech/api/v2.1/films/search-by-keyword?keyword={search_query}"
        headers = {
            "X-API-KEY": Config.KINOPOISK_API_KEY,
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=Config.REQUEST_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        films = data.get("films", [])

        if not films:
            await update.message.reply_text(
                "😕 По вашему запросу ничего не найдено.\n"
                "Попробуйте изменить название или уточнить год выпуска."
            )
            return ConversationHandler.END

        context.user_data['search_results'] = films[:Config.MAX_RESULTS]

        message_text = "🎬 <b>Результаты поиска:</b>\n\n"
        keyboard = []

        for idx, film in enumerate(context.user_data['search_results'], 1):
            title = film.get("nameRu", "Без названия")
            year = film.get("year", "")
            rating = film.get("rating", "нет оценки")

            message_text += (
                f"{idx}. <b>{title}</b> ({year}) ⭐ {rating}\n"
                f"<i>{film.get('description', '')[:100]}...</i>\n\n"
            )

            keyboard.append([InlineKeyboardButton(
                f"{idx}. {title} ({year})",
                callback_data=f"film_{film['filmId']}"
            )])

        await update.message.reply_text(
            message_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return DETAILS

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка API: {str(e)}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при поиске. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END


async def show_film_details(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    film_id = int(query.data.split("_")[1])
    film = next((f for f in context.user_data['search_results'] if f['filmId'] == film_id), None)

    if not film:
        await query.edit_message_text("Фильм не найден в результатах поиска.")
        return ConversationHandler.END

    message_text = format_film_info(film)

    description = film.get("description", "")
    if description:
        message_text += f"\n📝 <b>Описание:</b>\n<i>{description}</i>\n"

    poster_url = film.get("posterUrl")
    if poster_url:
        try:
            await query.message.reply_photo(
                photo=poster_url,
                caption=message_text,
                parse_mode="HTML",
                reply_markup=create_film_details_keyboard(film_id)
            )
            await query.delete_message()
            return DETAILS
        except Exception as e:
            logger.warning(f"Не удалось отправить постер: {str(e)}")

    await query.edit_message_text(
        message_text,
        parse_mode="HTML",
        reply_markup=create_film_details_keyboard(film_id)
    )

    return DETAILS


async def show_actors(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    film_id = int(query.data.split("_")[1])
    actors_info = await get_actors(film_id)

    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=f"film_{film_id}")]
    ]

    await query.edit_message_text(
        actors_info,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_similar(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    film_id = int(query.data.split("_")[1])
    similar_info = await get_similar_films(film_id)

    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=f"film_{film_id}")]
    ]

    await query.edit_message_text(
        similar_info,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_where_to_watch(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    film_id = int(query.data.split("_")[1])
    watch_info = await get_where_to_watch(film_id)

    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=f"film_{film_id}")]
    ]

    await query.edit_message_text(
        watch_info,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def back_to_results(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    search_query = context.user_data.get('search_query', '')
    films = context.user_data.get('search_results', [])

    if not films:
        await query.edit_message_text(
            "Результаты поиска больше не доступны. Пожалуйста, выполните новый поиск.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Новый поиск", callback_data="start_search")]
            ])
        )
        return ConversationHandler.END

    message_text = f"🎬 <b>Результаты поиска:</b> {search_query}\n\n"
    keyboard = []

    for idx, film in enumerate(films, 1):
        title = film.get("nameRu", "Без названия")
        year = film.get("year", "")
        rating = film.get("rating", "нет оценки")

        message_text += (
            f"{idx}. <b>{title}</b> ({year}) ⭐ {rating}\n"
            f"<i>{film.get('description', '')[:100]}...</i>\n\n"
        )

        keyboard.append([InlineKeyboardButton(
            f"{idx}. {title} ({year})",
            callback_data=f"film_{film['filmId']}"
        )])

    keyboard.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="start_search")])

    await query.edit_message_text(
        message_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return DETAILS


async def main_menu(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=create_main_menu_keyboard()
    )

    return ConversationHandler.END


def main() -> None:
    logger.info("Запуск кино-бота...")

    application = Application.builder().token(Config.BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CommandHandler("help", help_command),
            CommandHandler("search", start_search),
            CallbackQueryHandler(start_search, pattern="^start_search$"),
            CallbackQueryHandler(help_button, pattern="^help$"),
            CallbackQueryHandler(main_menu, pattern="^main_menu$")
        ],
        states={
            SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_search)],
            DETAILS: [
                CallbackQueryHandler(show_film_details, pattern="^film_"),
                CallbackQueryHandler(show_actors, pattern="^actors_"),
                CallbackQueryHandler(show_similar, pattern="^similar_"),
                CallbackQueryHandler(show_where_to_watch, pattern="^where_to_watch_"),
                CallbackQueryHandler(back_to_results, pattern="^back_to_results$"),
                CallbackQueryHandler(main_menu, pattern="^main_menu$"),
                CallbackQueryHandler(start_search, pattern="^start_search$")
            ]
        },
        fallbacks=[
            CommandHandler("start", start_command),
            CommandHandler("help", help_command),
            CallbackQueryHandler(main_menu, pattern="^main_menu$")
        ]
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(help_button, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))

    application.run_polling()
    logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)
        print("Произошла критическая ошибка. Подробности в логах.")
