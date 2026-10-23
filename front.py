import base64
import json
import os
from datetime import date, datetime

import requests
import streamlit as st

API_URL = os.getenv("BLOKNOT_API_URL", "http://127.0.0.1:8000").rstrip("/")

STATUSES = ["active", "completed", "cancelled"]
STATUS_LABELS = {"active": "Активное", "completed": "Завершено", "cancelled": "Отменено"}
LEVELS = ["easy", "medium", "high", "critical"]
LEVEL_LABELS = {"easy": "Лёгкий", "medium": "Средний", "high": "Высокий", "critical": "Критический"}
LEVEL_ICONS = {"easy": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
PAGES = ["Главное меню", "Мои дела", "Задачи", "Заметки", "Профиль"]

st.set_page_config(page_title="Bloknot — менеджер дел", page_icon="🗂️", layout="wide")


# ----------------------------------------------------------------------------
# API-клиент
# ----------------------------------------------------------------------------
class ApiError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def _format_errors(data):
    """DRF отдаёт ошибки как {"field": ["msg"]} или {"detail": "msg"} — делаем читаемую строку."""
    if isinstance(data, dict):
        parts = []
        for key, val in data.items():
            if isinstance(val, (list, tuple)):
                val = "; ".join(str(v) for v in val)
            parts.append(str(val) if key in ("detail", "non_field_errors") else f"{key}: {val}")
        return " | ".join(parts)
    if isinstance(data, list):
        return "; ".join(str(x) for x in data)
    return str(data)


def _jwt_user_id(token):
    """user_id лежит в payload access-токена (подпись проверяет сервер)."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return int(json.loads(base64.urlsafe_b64decode(payload))["user_id"])  # в payload может быть строкой
    except Exception:
        return None


def _refresh_access():
    refresh = st.session_state.get("refresh")
    if not refresh:
        return False
    try:
        r = requests.post(f"{API_URL}/token/refresh/", json={"refresh": refresh}, timeout=10)
    except requests.RequestException:
        return False
    # В urls.py проекта /token/refresh/ не зарегистрирован — если 404, просто просим войти заново.
    if r.status_code != 200:
        return False
    data = r.json()
    st.session_state.access = data["access"]
    if data.get("refresh"):
        st.session_state.refresh = data["refresh"]
    return True


def api(method, path, *, json_body=None, data=None, files=None, params=None, auth=True):
    """Единая точка запросов. Возвращает распарсенный JSON (или None для 204/205)."""
    for attempt in (1, 2):
        headers = {}
        if auth and st.session_state.get("access"):
            headers["Authorization"] = f"Bearer {st.session_state.access}"
        try:
            resp = requests.request(
                method, f"{API_URL}{path}", json=json_body, data=data, files=files,
                params=params, headers=headers, timeout=15,
            )
        except requests.ConnectionError:
            raise ApiError(f"Не удаётся подключиться к API ({API_URL}). Запущен ли бэкенд?")
        except requests.RequestException as exc:
            raise ApiError(f"Ошибка сети: {exc}")

        if resp.status_code == 401 and auth and attempt == 1 and _refresh_access():
            continue
        if resp.status_code == 401 and auth:
            force_logout("Сессия истекла, войдите заново.")
        break

    if resp.status_code in (204, 205):
        return None
    try:
        body = resp.json()
    except ValueError:
        body = None
    if not resp.ok:
        if resp.status_code == 403:
            raise ApiError("Нет прав на это действие (403).", 403)
        if resp.status_code == 404:
            raise ApiError("Не найдено (404).", 404)
        if resp.status_code >= 500:
            raise ApiError(f"Ошибка сервера ({resp.status_code}).", resp.status_code)
        raise ApiError(_format_errors(body) if body else f"Ошибка {resp.status_code}", resp.status_code)
    return body


# ----------------------------------------------------------------------------
# Состояние / утилиты
# ----------------------------------------------------------------------------
def init_state():
    for key, value in {
        "access": None, "refresh": None, "user_id": None, "username": None,
        "page": "Главное меню", "flash": None, "selected_deal": None,
    }.items():
        st.session_state.setdefault(key, value)


def notify(text, kind="success"):
    st.session_state.flash = (kind, text)


def show_flash():
    flash = st.session_state.pop("flash", None)
    if flash:
        getattr(st, flash[0])(flash[1])


def force_logout(message=None):
    for key in ("access", "refresh", "user_id", "username", "selected_deal"):
        st.session_state[key] = None
    st.session_state.page = "Главное меню"
    if message:
        notify(message, "warning")
    st.rerun()


def do_logout():
    refresh = st.session_state.get("refresh")
    if refresh:
        try:  # best-effort: на сервере blacklist может быть не подключён
            api("POST", "/logout/", json_body={"refresh": refresh})
        except ApiError:
            pass
    force_logout()


def fmt_date(value):
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d.%m.%Y")
    except ValueError:
        return value


def fmt_money(value):
    return f"{int(value or 0):,}".replace(",", " ") + " сом"


def guard(fn):
    """Выполнить действие; ошибки API показать пользователю, не роняя приложение."""
    try:
        return True, fn()
    except ApiError as exc:
        st.error(str(exc))
        return False, None


# ----------------------------------------------------------------------------
# Загрузка данных пользователя
# ----------------------------------------------------------------------------
def load_deals():
    """Дела текущего пользователя с деталями и заметками (note_detail)."""
    listing = api("GET", "/deals/") or []
    if isinstance(listing, dict):  # на случай пагинации
        listing = listing.get("results", [])
    deals = []
    for item in listing:
        try:
            deals.append(api("GET", f"/deal/{item['id']}/"))
        except ApiError:
            continue
    deals.sort(key=lambda d: d.get("updated_at") or "", reverse=True)
    return deals


def load_tasks(deals_by_id):
    """/Tasks/ отдаёт задачи всех пользователей — оставляем только свои."""
    raw = api("GET", "/Tasks/") or []
    if isinstance(raw, dict):
        raw = raw.get("results", [])
    uid = st.session_state.user_id
    mine = [t for t in raw if t.get("owner") == uid]
    for t in mine:
        t["deal_title"] = (deals_by_id.get(t["deal"]) or t.get("deal_detail") or {}).get("title_deal", "—")
    return mine


def task_sort_key(t):
    return (t["status"], t.get("deadline") or "9999-12-31", t.get("created_at") or "")


def all_notes(deals):
    notes = []
    for d in deals:
        for n in d.get("note_detail", []):
            notes.append({**n, "deal_title": d["title_deal"]})
    notes.sort(key=lambda n: (n.get("date_note") or "", n["id"]), reverse=True)
    return notes


# ----------------------------------------------------------------------------
# Экран входа / регистрации
# ----------------------------------------------------------------------------
def auth_screen():
    st.title("🗂️ Bloknot")
    st.caption("Простой менеджер дел, задач и заметок.")
    tab_login, tab_register = st.tabs(["Войти", "Регистрация"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Логин")
            password = st.text_input("Пароль", type="password")
            if st.form_submit_button("Войти", use_container_width=True):
                if not username.strip() or not password:
                    st.error("Введите логин и пароль.")
                else:
                    ok, data = guard(lambda: api(
                        "POST", "/login/", json_body={"username": username.strip(), "password": password}, auth=False))
                    if ok:
                        st.session_state.access = data["access"]
                        st.session_state.refresh = data["refresh"]
                        st.session_state.username = data["user"]["username"]
                        st.session_state.user_id = _jwt_user_id(data["access"])
                        st.rerun()

    with tab_register:
        with st.form("register_form"):
            c1, c2 = st.columns(2)
            r_username = c1.text_input("Логин *")
            r_email = c2.text_input("Email *")
            r_first = c1.text_input("Имя")
            r_last = c2.text_input("Фамилия")
            r_phone = c1.text_input("Телефон", value="+996")
            r_age = c2.number_input("Возраст", min_value=10, max_value=100, value=18, step=1)
            r_pass = c1.text_input("Пароль *", type="password")
            r_pass2 = c2.text_input("Повторите пароль *", type="password")
            if st.form_submit_button("Создать аккаунт", use_container_width=True):
                errors = []
                if not r_username.strip():
                    errors.append("Введите логин.")
                if not r_email.strip():
                    errors.append("Введите email.")
                if len(r_pass) < 6:
                    errors.append("Пароль должен содержать минимум 6 символов.")
                if r_pass != r_pass2:
                    errors.append("Пароли не совпадают.")
                for e in errors:
                    st.error(e)
                if not errors:
                    payload = {
                        "username": r_username.strip(), "email": r_email.strip(), "password": r_pass,
                        "first_name": r_first.strip(), "last_name": r_last.strip(),
                        "age": int(r_age), "phone_number": r_phone.strip() or "+996",
                    }
                    ok, _ = guard(lambda: api("POST", "/register/", json_body=payload, auth=False))
                    if ok:
                        # сразу логинимся
                        ok2, data = guard(lambda: api(
                            "POST", "/login/", json_body={"username": payload["username"], "password": r_pass}, auth=False))
                        if ok2:
                            st.session_state.access = data["access"]
                            st.session_state.refresh = data["refresh"]
                            st.session_state.username = data["user"]["username"]
                            st.session_state.user_id = _jwt_user_id(data["access"])
                            notify("Аккаунт создан!")
                            st.rerun()


# ----------------------------------------------------------------------------
# Страницы
# ----------------------------------------------------------------------------
def deal_card(deal, key_prefix):
    with st.container(border=True):
        a, b, c = st.columns([5, 2, 1])
        with a:
            st.write(f"**{deal['title_deal']}**")
            desc = deal.get("description") or ""
            st.caption(desc[:140] if desc else "Без описания")
        with b:
            st.write(f"Статус: **{STATUS_LABELS.get(deal['status'], deal['status'])}**")
            st.caption(f"💰 {fmt_money(deal.get('cash'))}")
        with c:
            if st.button("Открыть", key=f"{key_prefix}_{deal['id']}"):
                st.session_state.selected_deal = deal["id"]
                st.session_state.page = "Мои дела"
                st.rerun()


def page_home(deals, tasks):
    st.title(f"Добро пожаловать, {st.session_state.username} 👋")
    st.caption("Управляй делами, задачами и заметками в одном месте.")

    cols = st.columns(5)
    cols[0].metric("Активные дела", sum(d["status"] == "active" for d in deals))
    cols[1].metric("Завершённые дела", sum(d["status"] == "completed" for d in deals))
    cols[2].metric("Открытые задачи", sum(not t["status"] for t in tasks))
    cols[3].metric("Выполненные задачи", sum(t["status"] for t in tasks))
    cols[4].metric("Сумма", fmt_money(sum(d.get("cash", 0) for d in deals)))

    st.subheader("🔎 Найти дело")
    q = st.text_input("Поиск по названию или описанию", placeholder="Например: «сайт клиенту»")
    if q:
        ql = q.lower()
        found = [d for d in deals if ql in d["title_deal"].lower() or ql in (d.get("description") or "").lower()]
        if not found:
            st.warning("Ничего не найдено.")
        else:
            st.caption(f"Найдено дел: {len(found)}")
            for d in found:
                deal_card(d, "search_open")
        st.divider()

    st.subheader("Последние дела")
    if not deals:
        st.info("Пока нет дел. Создай первое в разделе «Мои дела».")
    for d in deals[:5]:
        deal_card(d, "dash_open")

    st.subheader("Ближайшие задачи")
    upcoming = sorted((t for t in tasks if not t["status"]), key=task_sort_key)[:5]
    if not upcoming:
        st.info("Открытых задач нет.")
    for t in upcoming:
        dl = fmt_date(t.get("deadline")) or "без срока"
        st.write(f"- {LEVEL_ICONS[t['level']]} **{t['title_task']}** · {t['deal_title']} · {dl} · {LEVEL_LABELS[t['level']]}")


def page_deals(deals):
    st.title("📁 Мои дела")

    with st.expander("➕ Создать новое дело"):
        with st.form("create_deal", clear_on_submit=True):
            title = st.text_input("Название", max_chars=100)
            description = st.text_area("Описание")
            cash = st.number_input("Сумма, сом", min_value=0, step=100)
            if st.form_submit_button("Создать дело", use_container_width=True):
                if not title.strip():
                    st.error("Название обязательно.")
                else:
                    def create():
                        # POST /deals/ принимает только title_deal; остальное — PATCH на детальный эндпоинт
                        new = api("POST", "/deals/", json_body={"title_deal": title.strip()})
                        extra = {"cash": int(cash)}
                        if description.strip():  # API не принимает пустое описание
                            extra["description"] = description.strip()
                        api("PATCH", f"/deal/{new['id']}/", json_body=extra)
                        return new
                    ok, new = guard(create)
                    if ok:
                        st.session_state.selected_deal = new["id"]
                        notify("Дело создано!")
                        st.rerun()

    c1, c2 = st.columns([1, 2])
    status_filter = c1.selectbox("Статус", ["all"] + STATUSES,
                                 format_func=lambda x: "Все статусы" if x == "all" else STATUS_LABELS[x])
    search = c2.text_input("Поиск по названию", key="deals_search")

    shown = [d for d in deals
             if (status_filter == "all" or d["status"] == status_filter)
             and (not search or search.lower() in d["title_deal"].lower())]
    if not shown:
        st.info("Дела не найдены.")
        return

    ids = [d["id"] for d in shown]
    by_id = {d["id"]: d for d in shown}
    current = st.session_state.selected_deal if st.session_state.selected_deal in ids else ids[0]
    selected = st.selectbox(
        "Выберите дело", ids, index=ids.index(current),
        format_func=lambda i: f"{by_id[i]['title_deal']} · {STATUS_LABELS[by_id[i]['status']]} · {fmt_money(by_id[i]['cash'])}")
    st.session_state.selected_deal = selected
    deal = by_id[selected]

    with st.container(border=True):
        st.subheader(deal["title_deal"])
        st.caption(f"Создано: {fmt_date(deal['created_at'])} · Обновлено: {fmt_date(deal['updated_at'])}")
        st.write(deal.get("description") or "Без описания")
        st.metric("Сумма", fmt_money(deal["cash"]))

        with st.form(f"edit_deal_{deal['id']}"):
            e_title = st.text_input("Название", value=deal["title_deal"], max_chars=100)
            e_desc = st.text_area("Описание", value=deal.get("description") or "")
            e_status = st.selectbox("Статус", STATUSES, index=STATUSES.index(deal["status"]),
                                    format_func=STATUS_LABELS.get)
            e_cash = st.number_input("Сумма, сом", min_value=0, value=int(deal["cash"]), step=100)
            if st.form_submit_button("💾 Сохранить изменения", use_container_width=True):
                if not e_title.strip():
                    st.error("Название не может быть пустым.")
                elif not e_desc.strip():
                    st.error("Описание не может быть пустым.")
                else:
                    ok, _ = guard(lambda: api("PATCH", f"/deal/{deal['id']}/", json_body={
                        "title_deal": e_title.strip(), "description": e_desc.strip(),
                        "status": e_status, "cash": int(e_cash)}))
                    if ok:
                        notify("Изменения сохранены!")
                        st.rerun()

        with st.popover("🗑️ Удалить дело"):
            st.warning("Будут удалены также все задачи и заметки этого дела.")
            if st.button("Да, удалить", key=f"del_deal_{deal['id']}", type="primary"):
                ok, _ = guard(lambda: api("DELETE", f"/deal/{deal['id']}/"))
                if ok:
                    st.session_state.selected_deal = None
                    notify("Дело удалено.", "warning")
                    st.rerun()

    st.subheader("📝 Заметки этого дела")
    with st.form(f"note_form_{deal['id']}", clear_on_submit=True):
        n_title = st.text_input("Заголовок заметки", max_chars=100)
        n_desc = st.text_area("Текст заметки")
        if st.form_submit_button("Добавить заметку", use_container_width=True):
            if not n_title.strip():
                st.error("Заголовок заметки обязателен.")
            else:
                ok, _ = guard(lambda: api("POST", "/Note/", json_body={
                    "deal": deal["id"], "title_note": n_title.strip(), "description": n_desc.strip()}))
                if ok:
                    notify("Заметка добавлена!")
                    st.rerun()

    notes = sorted(deal.get("note_detail", []), key=lambda n: (n["date_note"], n["id"]), reverse=True)
    if not notes:
        st.caption("В этом деле пока нет заметок.")
    for n in notes:
        note_card(n, f"note_{n['id']}")

    deal_tasks = st.session_state.get("_tasks_cache", [])
    deal_tasks = [t for t in deal_tasks if t["deal"] == deal["id"]]
    if deal_tasks:
        st.subheader("✅ Задачи этого дела")
        for t in sorted(deal_tasks, key=task_sort_key):
            mark = "✔️" if t["status"] else "⬜"
            dl = f" · 📅 {fmt_date(t['deadline'])}" if t.get("deadline") else ""
            st.write(f"{mark} {LEVEL_ICONS[t['level']]} **{t['title_task']}**{dl}")


def note_card(n, key, show_deal=False):
    with st.container(border=True):
        a, b = st.columns([6, 1])
        with a:
            st.write(f"**{n['title_note']}**")
            caption = fmt_date(n.get("date_note"))
            if show_deal:
                caption = f"📁 {n['deal_title']} · {caption}"
            st.caption(caption)
            st.write(n.get("description") or "")
        with b:
            if st.button("Удалить", key=f"del_{key}"):
                ok, _ = guard(lambda: api("DELETE", f"/Note/{n['id']}/"))
                if ok:
                    notify("Заметка удалена.", "warning")
                    st.rerun()


def page_tasks(deals, tasks):
    st.title("✅ Задачи")
    if not deals:
        st.warning("Сначала создай хотя бы одно дело в разделе «Мои дела».")
        return

    with st.expander("➕ Создать задачу"):
        with st.form("create_task", clear_on_submit=True):
            t_title = st.text_input("Название задачи", max_chars=100)
            t_desc = st.text_area("Описание")
            c1, c2 = st.columns(2)
            t_deal = c1.selectbox("Дело", [d["id"] for d in deals],
                                  format_func=lambda i: next(d["title_deal"] for d in deals if d["id"] == i))
            t_level = c2.selectbox("Приоритет", LEVELS, format_func=LEVEL_LABELS.get)
            has_deadline = c1.checkbox("Установить дедлайн")
            t_deadline = c2.date_input("Дедлайн", value=date.today())
            if st.form_submit_button("Создать задачу", use_container_width=True):
                if not t_title.strip():
                    st.error("Название обязательно.")
                elif not t_desc.strip():
                    st.error("Описание обязательно (API не принимает пустое).")
                else:
                    payload = {"deal": t_deal, "title_task": t_title.strip(), "description": t_desc.strip(),
                               "level": t_level, "owner": st.session_state.user_id}
                    if has_deadline:
                        payload["deadline"] = t_deadline.isoformat()
                    ok, _ = guard(lambda: api("POST", "/Tasks/", json_body=payload))
                    if ok:
                        notify("Задача создана!")
                        st.rerun()

    c1, c2, c3 = st.columns(3)
    show = c1.selectbox("Показать", ["Все", "Открытые", "Выполненные"])
    deal_filter = c2.selectbox("Дело", [0] + [d["id"] for d in deals],
                               format_func=lambda i: "Все дела" if i == 0 else next(
                                   d["title_deal"] for d in deals if d["id"] == i))
    level_filter = c3.selectbox("Приоритет", ["all"] + LEVELS,
                                format_func=lambda x: "Любой" if x == "all" else LEVEL_LABELS[x])

    visible = [t for t in tasks
               if (show == "Все" or (show == "Открытые") == (not t["status"]))
               and (deal_filter == 0 or t["deal"] == deal_filter)
               and (level_filter == "all" or t["level"] == level_filter)]
    if not visible:
        st.info("Задач не найдено.")
    today = date.today().isoformat()
    for t in sorted(visible, key=task_sort_key):
        with st.container(border=True):
            c1, c2, c3 = st.columns([0.6, 5, 1])
            with c1:
                done = st.checkbox("Выполнено", value=t["status"], key=f"done_{t['id']}", label_visibility="collapsed")
                if done != t["status"]:
                    ok, _ = guard(lambda: api("PATCH", f"/Tasks/{t['id']}/", json_body={"status": done}))
                    if ok:
                        st.rerun()
            with c2:
                title = f"~~{t['title_task']}~~" if t["status"] else t["title_task"]
                st.write(f"**{title}**")
                st.caption(f"📁 {t['deal_title']} · {LEVEL_ICONS[t['level']]} {LEVEL_LABELS[t['level']]}")
                st.write(t.get("description") or "Без описания")
                if t.get("deadline"):
                    overdue = (not t["status"]) and t["deadline"] < today
                    st.caption(f"📅 Дедлайн: {fmt_date(t['deadline'])}" + (" — ⚠️ просрочено" if overdue else ""))
            with c3:
                if st.button("🗑️", key=f"del_task_{t['id']}", help="Удалить задачу"):
                    ok, _ = guard(lambda: api("DELETE", f"/Tasks/{t['id']}/"))
                    if ok:
                        st.rerun()


def page_notes(deals):
    st.title("📝 Все заметки")
    notes = all_notes(deals)
    q = st.text_input("Поиск по заметкам")
    if q:
        notes = [n for n in notes if q.lower() in n["title_note"].lower() or q.lower() in (n.get("description") or "").lower()]
    if not notes:
        st.info("Заметок нет.")
    for n in notes:
        note_card(n, f"all_note_{n['id']}", show_deal=True)


def page_profile():
    st.title("👤 Профиль")
    ok, profile = guard(lambda: api("GET", f"/User/{st.session_state.user_id}/"))
    if not ok:
        return

    left, right = st.columns([1, 3])
    with left:
        if profile.get("profile_image"):
            img = profile["profile_image"]
            st.image(img if img.startswith("http") else f"{API_URL}{img}", use_container_width=True)
        else:
            st.markdown("<div style='font-size:5rem;text-align:center'>👤</div>", unsafe_allow_html=True)
    with right:
        st.write(f"**{profile['username']}**")
        st.caption(f"На сайте с {fmt_date(profile.get('date_joined'))}")

    with st.form("profile_form"):
        c1, c2 = st.columns(2)
        p_username = c1.text_input("Логин", value=profile["username"])
        p_email = c2.text_input("Email", value=profile.get("email") or "")
        p_first = c1.text_input("Имя", value=profile.get("first_name") or "")
        p_last = c2.text_input("Фамилия", value=profile.get("last_name") or "")
        p_phone = c1.text_input("Телефон", value=str(profile.get("phone_number") or ""))
        p_age = c2.number_input("Возраст", min_value=10, max_value=100, value=int(profile.get("age") or 10))
        p_image = st.file_uploader("Фото профиля", type=["png", "jpg", "jpeg"])
        if st.form_submit_button("Сохранить профиль", use_container_width=True):
            if not p_username.strip():
                st.error("Логин не может быть пустым.")
            else:
                form = {"username": p_username.strip(), "email": p_email.strip(), "first_name": p_first.strip(),
                        "last_name": p_last.strip(), "phone_number": p_phone.strip(), "age": int(p_age)}
                files = {"profile_image": (p_image.name, p_image.getvalue(), p_image.type)} if p_image else None
                ok, _ = guard(lambda: api("PATCH", f"/User/{profile['id']}/", data=form, files=files))
                if ok:
                    st.session_state.username = form["username"]
                    notify("Профиль обновлён!")
                    st.rerun()

    st.info("Смена пароля через API сейчас небезопасна (UserProfileSerializer сохраняет пароль без хеширования), "
            "поэтому в интерфейс она не вынесена.")


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
init_state()

if not st.session_state.access:
    show_flash()
    auth_screen()
    st.stop()

if st.session_state.user_id is None:
    st.session_state.user_id = _jwt_user_id(st.session_state.access)

with st.sidebar:
    st.title("🗂️ Bloknot")
    st.caption(f"Пользователь: **{st.session_state.username}**")
    st.divider()
    for p in PAGES:
        if st.button(p, use_container_width=True, type="primary" if st.session_state.page == p else "secondary"):
            st.session_state.page = p
            st.rerun()
    st.divider()
    if st.button("🚪 Выйти", use_container_width=True):
        do_logout()

show_flash()

try:
    page = st.session_state.page
    if page == "Профиль":
        page_profile()
    else:
        deals_ = load_deals()
        tasks_ = load_tasks({d["id"]: d for d in deals_})
        st.session_state["_tasks_cache"] = tasks_
        if page == "Главное меню":
            page_home(deals_, tasks_)
        elif page == "Мои дела":
            page_deals(deals_)
        elif page == "Задачи":
            page_tasks(deals_, tasks_)
        elif page == "Заметки":
            page_notes(deals_)
except ApiError as exc:
    st.error(str(exc))