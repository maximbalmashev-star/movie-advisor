import sys
import io
import os
import re
import random
import requests
from datetime import datetime

os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

import streamlit as st
from dotenv import load_dotenv
from gigachat import GigaChat
from supabase import create_client, Client

load_dotenv()


# ─────────────────────────────────────────────────────────────
# Универсальное чтение секретов: st.secrets → os.getenv
# ─────────────────────────────────────────────────────────────
def get_secret(key: str, default: str = ""):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


# ─────────────────────────────────────────────────────────────
# Подключение к Supabase
# ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")
    if not url or not key:
        st.error(
            "❌ SUPABASE_URL или SUPABASE_KEY не заданы. "
            "Проверьте .env (локально) или Secrets (в Streamlit Cloud)."
        )
        st.stop()
    return create_client(url, key)


supabase = get_supabase()


CATEGORIES = {
    "Шедевр 🌟": "masterpiece",
    "Понравилось 😊": "liked",
    "Не понравилось 😕": "disliked",
    "Не смотрел ⏸️": "not_watched",
    "Планирую 👀": "planned",
    "Не планирую ❌": "not_planned",
}

MOVIES = [
    "Интерстеллар", "Начало", "Дюна", "Дюна: Часть вторая", "Матрица",
    "Бойцовский клуб", "Криминальное чтиво", "Форрест Гамп",
    "Побег из Шоушенка", "Зелёная миля", "Тёмный рыцарь",
    "Тёмный рыцарь: Возрождение легенды", "Престиж", "Оппенгеймер",
    "Барби", "Джокер", "Паразиты", "Олдбой", "Убить Билла",
    "Крёстный отец", "Крёстный отец 2", "Список Шиндлера",
    "Властелин колец: Братство Кольца", "Властелин колец: Две крепости",
    "Властелин колец: Возвращение короля", "Хоббит: Нежданное путешествие",
    "Гарри Поттер и философский камень", "Гарри Поттер и Тайная комната",
    "Гарри Поттер и узник Азкабана", "Гарри Поттер и Кубок огня",
    "Мстители", "Мстители: Война бесконечности", "Мстители: Финал",
    "Железный человек", "Тор: Рагнарёк", "Человек-паук: Через вселенные",
    "Дедпул", "Логан", "Безумный Макс: Дорога ярости", "Гравитация",
    "Марсианин", "Прибытие", "Бегущий по лезвию 2049",
    "Терминатор 2: Судный день", "Чужой", "Чужие", "Нечто", "Сияние",
    "Молчание ягнят", "Семь", "Остров проклятых", "Отступники",
    "Ирландец", "Славные парни", "Лицо со шрамом",
    "Карты, деньги, два ствола", "Большой куш", "Рок-н-рольщик",
    "Шерлок Холмс", "Игра в имитацию", "Теория всего",
    "Вселенная Стивена Хокинга", "Социальная сеть", "1+1", "Ла-Ла Ленд",
    "Отель Гранд Будапешт", "Остров собак", "Аватар",
    "Аватар: Путь воды", "Титаник", "Волк с Уолл-стрит",
    "Омерзительная восьмёрка", "Джанго освобождённый",
    "Бесславные ублюдки", "Убить пересмешника",
    "12 разгневанных мужчин", "Пролетая над гнездом кукушки",
    "Достать ножи", "Исчезнувшая", "Девушка с татуировкой дракона",
    "Воспоминания об убийстве", "Служебный роман", "Ирония судьбы",
    "Москва слезам не верит", "Левиафан", "Нелюбовь", "Сталкер",
    "Солярис", "Андрей Рублёв", "Иван Васильевич меняет профессию",
    "Джентльмены удачи", "Кавказская пленница", "Белое солнце пустыни",
    "Брат", "Брат 2", "Остров", "Возвращение", "Кукушка",
    "Стиляги", "Географ глобус пропил", "Дурак", "Аритмия",
    "Холоп", "Последний богатырь", "Движение вверх", "Экипаж",
    "Иди и смотри", "Судьба человека", "Летят журавли",
    "Дом летающих кинжалов", "Герой", "Крадущийся тигр, затаившийся дракон",
    "Мемуары гейши", "Трудности перевода", "Вечное сияние чистого разума",
    "Игра", "Таксист", "Бешеные псы",
    "От заката до рассвета", "Отчаянный",
    "Форсаж", "Форсаж 5", "Миссия невыполнима",
    "Миссия невыполнима: Последняя расплата", "007: Координаты Скайфолл",
    "Казино Рояль", "Агент 007: Спектр", "Бэтмен",
    "Бэтмен: Начало", "Отряд самоубийц", "Хищник", "Чужой против Хищника",
    "Прометей", "Чужой: Завет",
    "Валли", "Вверх", "Головоломка", "Тайна Коко", "Душа",
    "Рататуй", "Суперсемейка", "История игрушек", "Корпорация монстров",
    "Как приручить дракона", "Шрек", "Мадагаскар", "Ледниковый период",
    "Король Лев", "Аладдин", "Красавица и чудовище", "Мулан",
    "Моана", "Холодное сердце", "Рапунцель",
    "Величайший шоумен", "Мулен Руж",
    "Богемская рапсодия", "Рокетмен", "Элвис", "8 миля",
    "Одержимость", "Королевство полной луны", "Фантастический мистер Фокс",
    "Она", "Лобстер", "Убийство священного оленя",
    "Седьмая печать", "Персона", "Шёпоты и крики",
    "8½", "Сладкая жизнь", "Дорога", "Ночи Кабирии",
    "Красная пустыня", "Забриски-пойнт", "Профессия: репортёр",
    "Апокалипсис сегодня", "Взвод", "Цельнометаллическая оболочка",
    "Спасти рядового Райана", "Дюнкерк", "1917", "Ярость",
    "Пианист", "Жизнь прекрасна", "Мальчик в полосатой пижаме",
    "Черный лебедь", "Боец", "Рестлер", "Бёрдмэн",
    "Великий Гэтсби",
]

SERIES = [
    "Мир Дикого Запада", "Игра престолов", "Дом Дракона",
    "Во все тяжкие", "Лучше звоните Солу", "Очень странные дела",
    "Черное зеркало", "Корона", "Мандалорец", "Ведьмак", "Пацаны",
    "Рик и Морти", "Симпсоны", "Южный парк", "Друзья",
    "Как я встретил вашу маму", "Теория Большого взрыва", "Офис",
    "Парки и зоны отдыха", "Шерлок", "Доктор Кто", "Пространство",
    "Светлячок", "Звёздный путь: Дискавери", "Остаться в живых",
    "Грань", "Секретные материалы", "Твин Пикс",
    "Настоящий детектив", "Мейр из Исттауна", "Острые козырьки",
    "Прослушка", "Клан Сопрано", "Дэдвуд", "Рим", "Викинги",
    "Последнее королевство", "Тюдоры", "Аббатство Даунтон",
    "Рассказ служанки", "Великая", "Молодой Папа",
    "Благие знамения", "Американские боги", "Песочный человек",
    "Ванда/Вижн", "Локи", "Сокол и Зимний солдат", "Странные вещи",
    "Академия Амбрелла", "Бумажный дом", "Элита", "Тьма", "1899",
    "Барри", "Наследники", "Белая ворона", "Ход королевы",
    "Форс-мажоры", "Миллиарды", "Карточный домик", "Родина",
    "Родина: Москва", "Шпион", "Тихий Дон", "Мастер и Маргарита",
    "Метод", "Топи", "Пищеблок", "Химера",
    "Кухня", "Отель Элеон", "Интерны", "Универ", "Реальные пацаны",
    "Физрук", "Слово пацана", "Фишер", "Территория",
    "Вампиры средней полосы", "Кибердеревня",
    "Первый отдел", "Хрустальный",
    "Шерлок в России", "Кровавая барыня", "Екатерина",
    "София", "Годунов", "Грозный", "Демон революции",
    "Ленинград 46", "Оттепель", "Восьмидесятые", "Семнадцать мгновений весны",
    "Место встречи изменить нельзя", "Ликвидация", "Исаев",
    "Адъютант его превосходительства", "Следствие ведут знатоки",
    "Противостояние", "ТАСС уполномочен заявить",
    "Бригада", "Бандитский Петербург", "Улицы разбитых фонарей",
    "Ментовские войны", "Литейный", "Невский",
    "Глухарь", "Пятницкий", "Карпов", "Побег",
    "Папины дочки", "Воронины", "Даёшь молодёжь!",
    "Наша Russia", "Однажды в России", "Comedy Баттл",
]

ANIME = [
    "Атака титанов", "Тетрадь смерти", "Стальной алхимик: Братство",
    "Наруто", "Ван-Пис", "Блич", "Токийский гуль",
    "Клинок, рассекающий демонов", "Магическая битва",
    "Моя геройская академия", "Евангелион", "Ковбой Бибоп",
    "Код Гиас", "Врата Штейна", "Меланхолия Харухи Судзумии",
    "Кланнад", "Ванпанчмен", "Сейлор Мун", "Ранма 1/2",
    "Инуяся", "Берсерк", "Хеллсинг", "Дневник будущего",
    "Эльфийская песнь", "Гуррен-Лаганн", "Психопаспорт",
    "Монстр", "Дорохедоро", "Вайолет Эвергарден",
    "Форма голоса", "Сад слов", "5 сантиметров в секунду",
    "Унесённые призраками", "Ходячий замок", "Мой сосед Тоторо",
    "Принцесса Мононоке", "Твоё имя", "Паприка", "Акира",
    "Призрак в доспехах", "Волчица и пряности",
    "Реинкарнация безработного", "О моём перерождении в слизь",
    "Маг-целитель: Новый старт", "Восхождение героя щита",
    "Поднятие уровня в одиночку", "Мастера меча онлайн",
    "Логин Horizon", "Overlord", "Re:Zero", "Konosuba",
    "Джо-Джо", "Хантер х Хантер", "Фейри Тейл",
    "Семь смертных грехов", "Сказания Зестирии",
    "Клеймор", "Триган", "Гантц", "Блэк Лагун",
    "Драконий жемчуг", "Покемон", "Дигимон", "Ю-Ги-О!",
    "Сейлор Мун Кристалл", "Карточки Сакуры", "Тсукимо",
    "Созданный в Бездне", "Обещанный Неверленд",
    "Клинок Бессмертного", "Бродяга Кэнсин",
    "Самурай Чамплу", "Скиталец Кэнсин", "Бэттерфлай",
    "Мобильный воин Гандам", "Макрос", "Евангелион 2.0",
    "Полный металл паника", "Код: Брейкер",
    "Хвост Феи", "Соул Итер", "Доктор Стоун",
    "Магическая битва 0", "Дзюдзюцу Кайсен",
]


def _build_mixed_titles():
    items = (
        [(t, "movie") for t in MOVIES]
        + [(t, "series") for t in SERIES]
        + [(t, "anime") for t in ANIME]
    )
    rng = random.Random(20251012)
    rng.shuffle(items)
    return items


TITLES = _build_mixed_titles()


def media_label(media_type):
    return {"movie": "фильм", "series": "сериал", "anime": "аниме"}.get(media_type, media_type)


# ─────────────────────────────────────────────────────────────
# Работа с Supabase
# ─────────────────────────────────────────────────────────────
def save_rating(title, media_type, category):
    try:
        supabase.table("ratings").upsert({
            "title": title,
            "media_type": media_type,
            "category": category,
            "rated_at": datetime.now().isoformat(),
        }, on_conflict="title,media_type").execute()
    except Exception as e:
        st.error(f"Ошибка сохранения оценки: {e}")


def delete_rating(title, media_type):
    try:
        supabase.table("ratings").delete().eq("title", title).eq("media_type", media_type).execute()
    except Exception as e:
        st.error(f"Ошибка удаления: {e}")


def get_all_ratings():
    """Возвращает список кортежей (title, media_type, category, rated_at)."""
    try:
        resp = supabase.table("ratings").select("title,media_type,category,rated_at").order(
            "rated_at", desc=True
        ).execute()
        return [(r["title"], r["media_type"], r["category"], r["rated_at"]) for r in resp.data]
    except Exception:
        return []


def get_rated_titles():
    """Возвращает множество (title, media_type) — для быстрой проверки."""
    try:
        resp = supabase.table("ratings").select("title,media_type").execute()
        return {(r["title"], r["media_type"]) for r in resp.data}
    except Exception:
        return set()


def reset_all_ratings():
    try:
        # Сначала получаем все id
        resp = supabase.table("ratings").select("id").execute()
        ids = [r["id"] for r in resp.data]
        if ids:
            supabase.table("ratings").delete().in_("id", ids).execute()
    except Exception as e:
        st.error(f"Ошибка сброса: {e}")


def is_cached(title, media_type):
    """True если запись уже есть в media_cache (даже без описания)."""
    try:
        resp = supabase.table("media_cache").select("id").eq("title", title).eq(
            "media_type", media_type
        ).execute()
        return len(resp.data) > 0
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────
# Верификация: Кинопоиск (основной) + Wikipedia (fallback)
# ─────────────────────────────────────────────────────────────
KINOPOISK_API = "https://kinopoiskapiunofficial.tech/api/v2.1/films/search-by-keyword"
KINOPOISK_DETAILS = "https://kinopoiskapiunofficial.tech/api/v2.2/films/{film_id}"

WIKI_API = "https://ru.wikipedia.org/w/api.php"
USER_AGENT = "MovieAdvisor/1.0 (educational project, contact: none)"

DISAMBIG_MARKERS = [
    "может означать",
    "страница значений",
    "неоднозначност",
    "многозначный термин",
]

POSITIVE_MARKERS = [
    "фильм", "сериал", "телесериал", "аниме", "мультфильм",
    "режиссёр", "режиссер", "кинокартин", "картин",
    "премьер", "прокат", "кинопремьер",
]

STOP_WORDS = {
    "и", "в", "на", "из", "с", "по", "к", "о", "а", "но", "или",
    "фильм", "сериал", "аниме", "телесериал", "мультфильм",
    "the", "a", "an", "of",
}


def extract_year(text: str):
    if not text:
        return None
    m = re.search(r'\b(19\d{2}|20[0-2]\d)\b', text[:500])
    if m:
        return m.group(1)
    return None


def is_disambiguation(extract: str) -> bool:
    if not extract:
        return False
    lower = extract[:600].lower()
    for m in DISAMBIG_MARKERS:
        if m in lower:
            return True
    return False


def _clean_title(t: str) -> str:
    t = re.sub(r'[«»"\u2018\u2019\u201c\u201d\']', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r'[«»"\'(),.\-—–:/;]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def verify_title_kinopoisk(title: str, media_type: str):
    api_key = get_secret("KINOPOISK_API_KEY")
    if not api_key:
        return None, None

    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    params = {"keyword": title, "page": 1}

    try:
        r = requests.get(KINOPOISK_API, headers=headers, params=params, timeout=5)
        if r.status_code != 200:
            return None, None

        data = r.json()
        films = data.get("films", [])
        if not films:
            return None, None

        title_norm = _norm(title)
        chosen = None
        for film in films:
            name_ru = _norm(film.get("nameRu") or "")
            name_en = _norm(film.get("nameEn") or "")
            if name_ru == title_norm or name_en == title_norm:
                chosen = film
                break
        if chosen is None:
            chosen = films[0]

        description = chosen.get("description") or None
        year = chosen.get("year")

        if not description:
            film_id = chosen.get("filmId")
            if film_id:
                try:
                    details_url = KINOPOISK_DETAILS.format(film_id=film_id)
                    r2 = requests.get(details_url, headers=headers, timeout=5)
                    if r2.status_code == 200:
                        details = r2.json()
                        description = details.get("description") or None
                        year = year or details.get("year")
                except Exception:
                    pass

        if not description:
            if year:
                return f"Год выпуска: {year}.", str(year)
            return None, None

        return description, str(year) if year else None

    except Exception:
        return None, None


def _titles_match(requested: str, article_title: str, extract: str = "") -> bool:
    req = _norm(requested)
    art = _norm(article_title)
    if not req:
        return False
    if req == art or req in art or art in req:
        return True
    req_words = set(req.split()) - STOP_WORDS
    if not req_words:
        return True
    pool = set(art.split())
    if extract:
        pool |= set(_norm(extract[:400]).split())
    matches = req_words & pool
    return len(matches) >= len(req_words) * 0.7


def _search_wiki(query: str, limit: int = 5):
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(
            WIKI_API,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "utf8": 1,
                "srlimit": limit,
            },
            headers=headers,
            timeout=5,
        )
        if r.status_code != 200:
            return []
        return [item["title"] for item in r.json().get("query", {}).get("search", [])]
    except Exception:
        return []


def _get_wiki_extract(page_title: str):
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(
            WIKI_API,
            params={
                "action": "query",
                "prop": "extracts",
                "exintro": 1,
                "explaintext": 1,
                "titles": page_title,
                "format": "json",
                "utf8": 1,
            },
            headers=headers,
            timeout=5,
        )
        if r.status_code != 200:
            return None
        pages = r.json().get("query", {}).get("pages", {})
        for _, page_data in pages.items():
            extract = page_data.get("extract", "")
            if extract:
                return extract
    except Exception:
        return None
    return None


def _try_direct_title(title: str, media_type: str):
    headers = {"User-Agent": USER_AGENT}
    if media_type == "anime":
        variants = [title, f"{title} (аниме)", f"{title} (аниме-сериал)"]
    elif media_type == "series":
        variants = [title, f"{title} (телесериал)", f"{title} (сериал)"]
    else:
        variants = [title, f"{title} (фильм)"]

    for variant in variants:
        try:
            r = requests.get(WIKI_API, params={
                "action": "query",
                "titles": variant,
                "redirects": 1,
                "prop": "extracts",
                "exintro": 1,
                "explaintext": 1,
                "format": "json",
                "utf8": 1,
            }, headers=headers, timeout=5)
            if r.status_code != 200:
                continue
            data = r.json()
            pages = data.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                if pid == "-1":
                    continue
                extract = page.get("extract", "")
                if not extract:
                    continue
                if is_disambiguation(extract):
                    continue
                lower = extract[:400].lower()
                if not any(m in lower for m in POSITIVE_MARKERS):
                    continue
                if media_type == "anime" and "аниме" not in lower and "аниме-сериал" not in lower:
                    continue
                has_book = any(m in lower for m in ["роман ", "книга ", "повесть "])
                has_game = any(m in lower for m in ["видеоигр", "компьютерн"])
                has_film = any(m in lower for m in ["фильм", "сериал", "телесериал", "аниме", "мультфильм"])
                if (has_book or has_game) and not has_film:
                    continue
                return extract
        except Exception:
            continue
    return None


def verify_title_wikipedia(title: str, media_type: str):
    clean = _clean_title(title)
    extract = _try_direct_title(clean, media_type)
    if extract:
        sentences = extract.split(". ")
        text = ". ".join(sentences[:3]).strip()
        if not text.endswith("."):
            text += "."
        year = extract_year(extract)
        return text, year

    if media_type == "movie":
        queries = [f"{clean} фильм", clean]
    elif media_type == "series":
        queries = [f"{clean} сериал", f"{clean} телесериал", clean]
    else:
        queries = [f"{clean} аниме", clean]

    seen_pages = set()
    for query in queries:
        results = _search_wiki(query, limit=5)
        for page_title in results:
            if page_title in seen_pages:
                continue
            seen_pages.add(page_title)

            lower_title = page_title.lower()
            if any(x in lower_title for x in [
                "неоднозначност", "список", "категория",
                "(значения)", "все страницы"
            ]):
                continue

            extract = _get_wiki_extract(page_title)
            if not extract:
                continue
            if is_disambiguation(extract):
                continue
            if not _titles_match(clean, page_title, extract):
                continue

            lower = extract[:400].lower()
            if not any(m in lower for m in POSITIVE_MARKERS):
                continue
            if media_type == "anime" and "аниме" not in lower and "аниме-сериал" not in lower:
                continue

            has_book = any(m in lower for m in ["роман ", "книга ", "повесть ", "сборник "])
            has_game = any(m in lower for m in ["видеоигр", "компьютерн", "игра для"])
            has_film = any(m in lower for m in ["фильм", "сериал", "телесериал", "аниме", "мультфильм", "режиссёр", "режиссер"])
            if (has_book or has_game) and not has_film:
                continue

            sentences = extract.split(". ")
            text = ". ".join(sentences[:3]).strip()
            if not text.endswith("."):
                text += "."
            year = extract_year(extract)
            return text, year

    return None, None


def verify_title(title: str, media_type: str):
    desc, year = verify_title_kinopoisk(title, media_type)
    if desc:
        return desc, year
    return verify_title_wikipedia(title, media_type)


@st.cache_data(ttl=3600, show_spinner=False)
def get_description(title: str, media_type: str):
    # 1. Проверяем кэш в Supabase
    try:
        resp = supabase.table("media_cache").select("description,year").eq(
            "title", title
        ).eq("media_type", media_type).execute()
        if resp.data:
            row = resp.data[0]
            return row.get("description"), row.get("year")
    except Exception:
        pass

    # 2. Верификация через Кинопоиск / Wikipedia
    desc, year = verify_title(title, media_type)

    # 3. Сохраняем в Supabase (включая NULL — чтобы не пробовать снова)
    try:
        supabase.table("media_cache").upsert({
            "title": title,
            "media_type": media_type,
            "description": desc,
            "year": year,
            "cached_at": datetime.now().isoformat(),
        }, on_conflict="title,media_type").execute()
    except Exception:
        pass

    return desc, year


def clear_cache():
    try:
        resp = supabase.table("media_cache").select("id").execute()
        ids = [r["id"] for r in resp.data]
        if ids:
            supabase.table("media_cache").delete().in_("id", ids).execute()
        get_description.clear()
    except Exception as e:
        st.error(f"Ошибка очистки кэша: {e}")


def test_kinopoisk_api():
    api_key = get_secret("KINOPOISK_API_KEY")
    if not api_key:
        return False, "❌ KINOPOISK_API_KEY не задан"
    try:
        r = requests.get(
            KINOPOISK_API,
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            params={"keyword": "Интерстеллар", "page": 1},
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            count = len(data.get("films", []))
            return True, f"✅ Кинопоиск работает. Найдено результатов: {count}"
        else:
            return False, f"❌ HTTP {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return False, f"❌ Ошибка сети: {e}"


def test_wikipedia_api():
    try:
        r = requests.get(
            WIKI_API,
            params={
                "action": "query",
                "list": "search",
                "srsearch": "Интерстеллар фильм",
                "format": "json",
                "srlimit": 3,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=5,
        )
        if r.status_code == 200:
            found = r.json().get("query", {}).get("search", [])
            return True, f"✅ Wikipedia работает. Найдено результатов: {len(found)}"
        else:
            return False, f"❌ HTTP {r.status_code}"
    except Exception as e:
        return False, f"❌ Ошибка сети: {e}"


def test_supabase():
    try:
        resp = supabase.table("ratings").select("id").limit(1).execute()
        return True, f"✅ Supabase работает. Записей в ratings: {len(resp.data)} (видна первая)"
    except Exception as e:
        return False, f"❌ Ошибка Supabase: {e}"


# ─────────────────────────────────────────────────────────────
# Парсинг ответа GigaChat
# ─────────────────────────────────────────────────────────────
TITLE_PATTERNS = [
    r'^\s*\*{0,2}\s*(?:\d+\.\s*)?\*{0,2}\s*(.+?)\s*\((\d{4})[^)]*\)\s*\*{0,2}',
    r'^\s*\*{0,2}\s*(?:\d+\.\s*)?\*{0,2}\s*(.+?)\s*\((фильм|сериал|аниме)[^)]*\)\s*\*{0,2}',
    r'^\s*\*{0,2}\s*(?:\d+\.\s*)?\*{0,2}\s*(.+?)\*{0,2}\s*[—\-–]\s*[А-Яа-я]',
]


def normalize_str(s: str) -> str:
    s = re.sub(r'\([^)]*\)', '', s)
    s = re.sub(r'[^\w\s]', '', s)
    return s.lower().strip()


def is_title_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 200:
        return False
    bad_starts = ["почему", "обоснование", "жанр:", "пояснение",
                  "итак", "вот", "например", "кстати", "наконец"]
    if any(stripped.lower().startswith(b) for b in bad_starts):
        return False
    for pat in TITLE_PATTERNS:
        if re.match(pat, stripped):
            if re.search(r'\(\s*\d{4}', stripped) or \
               re.search(r'\((фильм|сериал|аниме)', stripped, re.IGNORECASE):
                return True
    return False


def extract_title_from_block(block: str):
    first_line = block.split('\n')[0].strip()
    for pat in TITLE_PATTERNS:
        m = re.match(pat, first_line)
        if m:
            raw = m.group(1).strip()
            raw = re.sub(r'^\d+\.\s*', '', raw)
            raw = raw.strip('*').strip()
            title_clean = re.sub(r'\s*\([^)]*\)\s*$', '', raw).strip()
            lower = first_line.lower()
            if "аниме" in lower:
                media_type = "anime"
            elif "сериал" in lower or "series" in lower:
                media_type = "series"
            else:
                media_type = "movie"
            if not title_clean or len(title_clean) < 2:
                continue
            return title_clean, media_type
    return None, None


def split_into_blocks(text: str):
    lines = text.split('\n')
    blocks = []
    current = None
    for line in lines:
        if is_title_line(line):
            if current is not None:
                blocks.append('\n'.join(current).strip())
            current = [line]
        elif current is not None:
            current.append(line)
    if current is not None:
        blocks.append('\n'.join(current).strip())
    return blocks


# ─────────────────────────────────────────────────────────────
# GigaChat
# ─────────────────────────────────────────────────────────────
def get_gigachat_recommendations(user_ratings_text: str, rated_titles: set,
                                 extra_prompt: str = "") -> str:
    credentials = get_secret("GIGACHAT_CREDENTIALS")
    if not credentials:
        return "❌ Ключ GIGACHAT_CREDENTIALS не найден"

    rated_list = "\n".join(f"- {t[0]} ({media_label(t[1])})" for t in rated_titles)

    if extra_prompt.strip():
        extra_section = f"""
ОСОБЫЕ ПОЖЕЛАНИЯ ПОЛЬЗОВАТЕЛЯ (обязательно учти!):
{extra_prompt.strip()}
"""
    else:
        extra_section = ""

    prompt = f"""Ты — персональный киносоветчик. Порекомендуй ровно 15 РЕАЛЬНО СУЩЕСТВУЮЩИХ фильмов, сериалов или аниме.

Оценки пользователя:
{user_ratings_text}
{extra_section}
ЗАПРЕЩЕНО упоминать эти тайтлы (пользователь их уже видел):
{rated_list}

ЖЁСТКИЕ ТРЕБОВАНИЯ:
1. Только РЕАЛЬНЫЕ фильмы/сериалы/аниме. Используй русские названия, под которыми они известны в Кинопоиске. НЕ ВЫДУМЫВАЙ названия!
2. НЕ рекомендуй книги, романы, комиксы, видеоигры, спектакли, мюзиклы, отдельные серии сериалов.
3. Дай РОВНО 15 рекомендаций.
4. Минимум 6 из них — малоизвестные, авторские, нишевые работы.
5. Формат строго:
**Название (год, фильм)** — жанр
*Почему:* твоё обоснование в 2–3 предложениях.

Для сериала — **(год, сериал)**, для аниме — **(год, аниме)**.
6. Каждая рекомендация с новой строки. Без вступлений и заключений.

ПРИМЕРЫ ПРАВИЛЬНОГО ОТВЕТА:
**Прибытие (2016, фильм)** — фантастика, драма
*Почему:* Ты оценил 🌟 Интерстеллар, поэтому этот фильм подойдёт.

**Тьма (2017, сериал)** — фантастика, триллер
*Почему:* Подходит под твой вкус к закрученным сюжетам о времени.

**Врата Штейна (2011, аниме)** — фантастика, триллер
*Почему:* Подходит под твой интерес к путешествиям во времени.
"""

    import traceback

    try:
        with GigaChat(
            credentials=credentials,
            model="GigaChat-2-Pro",
            verify_ssl_certs=False,
        ) as client:
            response = client.chat(prompt)
            return response.choices[0].message.content
    except Exception as e:
        return f"❌ Ошибка: {e}\n\n{traceback.format_exc()}"


def generate_recommendations(user_ratings_text: str, rated_titles: set,
                             extra_prompt: str = "", min_count: int = 5,
                             max_count: int = 10):
    rated_norm = {normalize_str(t[0]) for t in rated_titles}

    raw = get_gigachat_recommendations(user_ratings_text, rated_titles, extra_prompt)
    log = []

    if raw.startswith("❌"):
        return [], raw, ["Ошибка от GigaChat"]

    if extra_prompt.strip():
        log.append(f"Доп. пожелание: {extra_prompt.strip()}")

    blocks = split_into_blocks(raw)
    log.append(f"GigaChat дал {len(blocks)} блоков")

    verified = []
    seen_titles = set()

    for block in blocks:
        title, media_type = extract_title_from_block(block)
        if title is None:
            continue

        key = normalize_str(title)
        if key in rated_norm:
            log.append(f"  ✗ уже оценён: {title}")
            continue
        if key in seen_titles:
            continue
        seen_titles.add(key)

        desc, year = get_description(title, media_type)
        if not desc:
            log.append(f"  ✗ не найден: {title} ({media_type})")
            continue

        verified.append((block, title, media_type, desc, year))
        log.append(f"  ✓ {title} ({media_type}, {year or '?'})")

    result = verified[:max_count]
    log.append(f"Итого верифицировано: {len(verified)}, показываем {len(result)}")
    return result, raw, log


# ─────────────────────────────────────────────────────────────
# Предзагрузка
# ─────────────────────────────────────────────────────────────
def preload_descriptions(batch):
    uncached = [(t, mt) for (t, mt) in batch if not is_cached(t, mt)]
    if not uncached:
        return

    progress = st.progress(0, text=f"⏳ Загружаю описания: 0 / {len(uncached)}")
    for i, (title, media_type) in enumerate(uncached):
        progress.progress(
            (i + 1) / len(uncached),
            text=f"⏳ Загружаю описания: {i+1} / {len(uncached)} — {title}",
        )
        get_description(title, media_type)
    progress.empty()


# ─────────────────────────────────────────────────────────────
# Рендер
# ─────────────────────────────────────────────────────────────
def _render_buttons_only(title, media_type, key_prefix):
    cols = st.columns(6)
    for i, (label, value) in enumerate(CATEGORIES.items()):
        if cols[i].button(
            label,
            key=f"{key_prefix}|{title}|{media_type}|{value}",
            use_container_width=True,
        ):
            save_rating(title, media_type, value)
            st.rerun()


def render_rating_buttons(title, media_type, key_prefix):
    desc, year = get_description(title, media_type)
    meta = media_label(media_type)
    if year:
        meta += f", {year}"
    st.markdown(f"**{title}** _({meta})_")

    if desc:
        st.caption(desc)
    else:
        st.caption("_Описание не найдено._")

    _render_buttons_only(title, media_type, key_prefix)


def render_recommendation(block, title, media_type, desc, year, key_prefix):
    st.markdown(block)
    if desc:
        st.caption(f"📖 {desc}")
    _render_buttons_only(title, media_type, key_prefix)


# ─────────────────────────────────────────────────────────────
# Вспомогательные функции для рекомендаций
# ─────────────────────────────────────────────────────────────
def _do_generate_recommendations(extra_prompt: str = ""):
    ratings = get_all_ratings()
    if len(ratings) < 5:
        st.warning("Оцени хотя бы 5 тайтлов.")
        return

    with st.spinner("GigaChat думает + Кинопоиск и Википедия проверяют (30–90 секунд)..."):
        lines = []
        for title, media_type, category, _ in ratings:
            label = next((k for k, v in CATEGORIES.items() if v == category), category)
            lines.append(f"- {title} ({media_label(media_type)}): {label}")
        user_ratings_text = "\n".join(lines)

        rated_set = get_rated_titles()
        verified, raw, log = generate_recommendations(
            user_ratings_text, rated_set, extra_prompt=extra_prompt,
            min_count=5, max_count=10,
        )
        st.session_state["ai_blocks"] = verified
        st.session_state["ai_raw"] = raw
        st.session_state["ai_log"] = log


# ─────────────────────────────────────────────────────────────
# Интерфейс
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Что посмотреть", page_icon="🎬", layout="wide")

st.title("🎬 Что посмотреть")
st.caption("Персональный советчик: оцени тайтлы и получи рекомендации от GigaChat.")

if not get_secret("KINOPOISK_API_KEY"):
    st.warning(
        "⚠️ Ключ `KINOPOISK_API_KEY` не найден. "
        "Верификация пойдёт только через Википедию."
    )

tab_rate, tab_plan, tab_my, tab_ai, tab_settings = st.tabs(
    ["📝 Оценка", "👀 Планирую", "📚 Мои оценки", "💡 Рекомендации", "⚙️ Настройки"]
)

# ─── Вкладка «Оценка» ────────────────────────────────────────
with tab_rate:
    st.subheader("Пакетная оценка")
    st.caption(
        "Выбери размер и нажми «Загрузить пакет». Фильмы не подгружаются автоматически."
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        media_filter = st.selectbox(
            "Что оцениваем?",
            options=["Всё подряд", "Только фильмы", "Только сериалы", "Только аниме"],
        )
    with col2:
        batch_size = st.radio(
            "Размер пакета",
            options=[10, 50, 100],
            index=0,
            horizontal=True,
        )

    type_map = {
        "Всё подряд": {"movie", "series", "anime"},
        "Только фильмы": {"movie"},
        "Только сериалы": {"series"},
        "Только аниме": {"anime"},
    }

    if "rate_batch" not in st.session_state:
        st.session_state["rate_batch"] = []

    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("📥 Загрузить пакет", type="primary", use_container_width=True):
            rated = get_rated_titles()
            allowed = type_map[media_filter]
            available = [t for t in TITLES if t not in rated and t[1] in allowed]
            st.session_state["rate_batch"] = available[:batch_size]
            st.rerun()
    with btn2:
        if st.button("⏭️ Следующий пакет", use_container_width=True):
            rated = get_rated_titles()
            current = set(st.session_state["rate_batch"])
            allowed = type_map[media_filter]
            available = [
                t for t in TITLES
                if t not in rated and t not in current and t[1] in allowed
            ]
            st.session_state["rate_batch"] = available[:batch_size]
            st.rerun()

    rated_now = get_rated_titles()
    batch = [t for t in st.session_state["rate_batch"] if t not in rated_now]

    if not batch:
        if st.session_state["rate_batch"]:
            st.success("🎉 Все тайтлы в этом пакете оценены. Жми «Следующий пакет».")
        else:
            st.info("Нажми «📥 Загрузить пакет», чтобы начать оценку.")
    else:
        st.write(f"В пакете **{len(batch)}** тайтлов.")
        preload_descriptions(batch)
        for title, media_type in batch:
            render_rating_buttons(title, media_type, "batch")
            st.markdown("---")

# ─── Вкладка «Планирую посмотреть» ───────────────────────────
with tab_plan:
    st.subheader("👀 Планирую посмотреть")
    st.caption("Все тайтлы, которые ты отметил как «Планирую 👀».")

    ratings = get_all_ratings()
    planned = [r for r in ratings if r[2] == "planned"]

    if not planned:
        st.info(
            "Пока пусто. Отмечай тайтлы как «Планирую 👀» во вкладке «Оценка» "
            "или в блоке рекомендаций."
        )
    else:
        st.metric("В планах", len(planned))

        type_filter = st.radio(
            "Тип",
            options=["Все", "Фильмы", "Сериалы", "Аниме"],
            horizontal=True,
            key="plan_filter",
        )
        type_map_plan = {
            "Все": {"movie", "series", "anime"},
            "Фильмы": {"movie"},
            "Сериалы": {"series"},
            "Аниме": {"anime"},
        }
        allowed = type_map_plan[type_filter]
        filtered = [r for r in planned if r[1] in allowed]

        if filtered:
            preload_descriptions([(r[0], r[1]) for r in filtered])

        st.markdown("---")
        for title, media_type, _, rated_at in filtered:
            render_rating_buttons(title, media_type, "plan_re")
            if st.button(
                "❌ Убрать из планов",
                key=f"plan_remove|{title}|{media_type}",
            ):
                delete_rating(title, media_type)
                st.rerun()
            st.markdown("---")

# ─── Вкладка «Мои оценки» ────────────────────────────────────
with tab_my:
    st.subheader("📚 Мои оценки")
    ratings = get_all_ratings()

    if not ratings:
        st.info("Пока нет ни одной оценки. Начни с вкладки «Оценка».")
    else:
        st.metric("Всего оценено", len(ratings))

        for label, value in CATEGORIES.items():
            items = [r for r in ratings if r[2] == value]
            if items:
                with st.expander(f"{label} — {len(items)}", expanded=False):
                    for title, media_type, _, _ in items:
                        st.write(f"- {title} _({media_label(media_type)})_")

# ─── Вкладка «Рекомендации GigaChat» ─────────────────────────
with tab_ai:
    st.subheader("💡 Персональные рекомендации")
    st.write(
        "GigaChat предложит варианты, а Кинопоиск и Википедия проверят, "
        "что они реально существуют. Показываю от 5 до 10 подтверждённых тайтлов."
    )

    extra_prompt = st.text_area(
        "🎯 Дополнительные пожелания (необязательно)",
        placeholder=(
            "Например: «только аниме, желательно без исекая», "
            "«сериалы про маньяков и расследования», "
            "«что-то лёгкое и смешное на вечер», "
            "«фантастика с философским подтекстом»"
        ),
        height=80,
        key="extra_prompt",
        help="Здесь можно указать жанр, тип, настроение, что угодно — GigaChat учтёт это в запросе."
    )

    ratings = get_all_ratings()

    if len(ratings) < 5:
        st.warning("Оцени хотя бы 5 тайтлов, чтобы рекомендации были осмысленными.")
    else:
        if "ai_blocks" not in st.session_state:
            if st.button("🎯 Получить рекомендации", type="primary"):
                _do_generate_recommendations(extra_prompt=extra_prompt)
                st.rerun()
        else:
            rated_now = get_rated_titles()
            rated_norm = {normalize_str(t[0]) for t in rated_now}

            fresh_blocks = [
                b for b in st.session_state["ai_blocks"]
                if normalize_str(b[1]) not in rated_norm
            ]

            if not fresh_blocks:
                st.success(
                    "✅ Все рекомендованные тайтлы оценены. "
                    "Нажми кнопку, чтобы получить новую порцию."
                )
                if st.button("🔄 Получить ещё рекомендации", type="primary"):
                    _do_generate_recommendations(extra_prompt=extra_prompt)
                    st.rerun()
            else:
                st.caption(f"Рекомендаций в списке: {len(fresh_blocks)} (макс. 10)")

                preload_descriptions([(t, mt) for (_, t, mt, _, _) in fresh_blocks])

                for block, title, media_type, desc, year in fresh_blocks:
                    render_recommendation(block, title, media_type, desc, year, "rec")
                    st.markdown("---")

                if st.button("🔄 Получить ещё рекомендации", use_container_width=True):
                    _do_generate_recommendations(extra_prompt=extra_prompt)
                    st.rerun()

            with st.expander("🔍 Сырой ответ GigaChat + лог верификации"):
                st.text(st.session_state.get("ai_raw", "—"))
                st.markdown("**Лог:**")
                for line in st.session_state.get("ai_log", []):
                    st.text(line)

# ─── Вкладка «Настройки» ─────────────────────────────────────
with tab_settings:
    st.subheader("⚙️ Настройки")

    st.markdown("### Диагностика источников")
    st.caption("Проверить доступность Supabase, Кинопоиска и Википедии.")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🗄️ Проверить Supabase"):
            ok, msg = test_supabase()
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    with col2:
        if st.button("🔍 Проверить Кинопоиск"):
            ok, msg = test_kinopoisk_api()
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    with col3:
        if st.button("🔍 Проверить Wikipedia"):
            ok, msg = test_wikipedia_api()
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.markdown("---")
    st.markdown("### Оценки")
    st.write("Сброс всех оценок. Действие необратимо.")
    if st.button("🗑️ Сбросить все оценки"):
        reset_all_ratings()
        st.session_state.pop("ai_blocks", None)
        st.session_state.pop("ai_raw", None)
        st.session_state.pop("ai_log", None)
        st.session_state.pop("rate_batch", None)
        st.success("Все оценки удалены.")
        st.rerun()

    st.markdown("---")
    st.markdown("### Кэш описаний")
    st.write("Очистить кэш описаний.")
    if st.button("🧹 Очистить кэш описаний"):
        clear_cache()
        st.success("Кэш описаний очищен.")
        st.rerun()
