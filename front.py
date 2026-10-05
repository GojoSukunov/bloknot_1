import os
import sys
from datetime import date
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DJANGO_DIR = BASE_DIR / "mysite"
if str(DJANGO_DIR) not in sys.path:
    sys.path.insert(0, str(DJANGO_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
import django

django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from mysite.blaknot_app.models import User, Deal, Tasks, Note


st.set_page_config(
    page_title="Bloknot — менеджер дел",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Helpers
# -----------------------------

def init_state():
    defaults = {
        "user_id": None,
        "page": "Главное меню",
        "flash": None,
        "selected_deal": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def current_user():
    uid = st.session_state.get("user_id")
    if not uid:
        return None
    try:
        return User.objects.get(pk=uid)
    except User.DoesNotExist:
        st.session_state.user_id = None
        return None


def notify(text, kind="success"):
    st.session_state.flash = (kind, text)


def show_flash():
    flash = st.session_state.pop("flash", None)
    if not flash:
        return
    kind, text = flash
    getattr(st, kind)(text)


def login_user(username, password):
    user = authenticate(username=username.strip(), password=password)
    if user is None:
        return False
    st.session_state.user_id = user.pk
    st.session_state.page = "Главное меню"
    return True


def logout():
    st.session_state.user_id = None
    st.session_state.selected_deal = None
    st.session_state.page = "Главное меню"
    st.rerun()


def safe_date(value):
    return value.isoformat() if value else ""


init_state()
user = current_user()

# -----------------------------
# CSS
# -----------------------------
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.2rem; max-width: 1400px; }
    [data-testid="stSidebar"] { min-width: 250px; max-width: 300px; }
    .hero {
        padding: 1.2rem 1.4rem;
        border: 1px solid rgba(128,128,128,.2);
        border-radius: 18px;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, rgba(80,120,255,.10), rgba(150,80,255,.08));
    }
    .metric-card {
        padding: 1rem;
        border: 1px solid rgba(128,128,128,.2);
        border-radius: 16px;
        min-height: 105px;
    }
    .muted { opacity: .7; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Auth screens
# -----------------------------
if not user:
    st.markdown(
        '<div class="hero"><h1>🗂️ Bloknot</h1><p>Простой менеджер дел, задач и заметок.</p></div>',
        unsafe_allow_html=True,
    )
    tab_login, tab_register = st.tabs(["Войти", "Регистрация"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Логин")
            password = st.text_input("Пароль", type="password")
            submitted = st.form_submit_button("Войти", use_container_width=True)
            if submitted:
                if login_user(username, password):
                    st.rerun()
                else:
                    st.error("Неверный логин или пароль.")

    with tab_register:
        with st.form("register_form"):
            r_username = st.text_input("Логин", key="r_username")
            r_email = st.text_input("Email", key="r_email")
            r_phone = st.text_input("Телефон", value="+996", key="r_phone")
            r_age = st.number_input("Возраст", min_value=10, max_value=100, value=18, step=1)
            r_password = st.text_input("Пароль", type="password", key="r_password")
            r_password2 = st.text_input("Повторите пароль", type="password", key="r_password2")
            submitted = st.form_submit_button("Создать аккаунт", use_container_width=True)

            if submitted:
                errors = []
                if not r_username.strip():
                    errors.append("Введите логин.")
                if User.objects.filter(username=r_username.strip()).exists():
                    errors.append("Такой логин уже существует.")
                if r_email and User.objects.filter(email=r_email.strip()).exists():
                    errors.append("Такой email уже используется.")
                if len(r_password) < 6:
                    errors.append("Пароль должен содержать минимум 6 символов.")
                if r_password != r_password2:
                    errors.append("Пароли не совпадают.")

                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        new_user = User.objects.create(
                            username=r_username.strip(),
                            email=r_email.strip(),
                            phone_number=r_phone.strip() or "+996",
                            age=int(r_age),
                            password=make_password(r_password),
                        )
                        st.session_state.user_id = new_user.pk
                        st.session_state.page = "Главное меню"
                        st.success("Аккаунт создан!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Не удалось создать пользователя: {exc}")
    st.stop()

# -----------------------------
# Sidebar navigation
# -----------------------------
with st.sidebar:
    st.title("🗂️ Bloknot")
    st.caption(f"Пользователь: **{user.username}**")
    st.divider()

    pages = ["Главное меню", "Мои дела", "Задачи", "Заметки", "Профиль"]
    for page in pages:
        if st.button(page, use_container_width=True, type="primary" if st.session_state.page == page else "secondary"):
            st.session_state.page = page
            st.rerun()

    st.divider()
    if st.button("🚪 Выйти", use_container_width=True):
        logout()

show_flash()

# -----------------------------
# Главное меню (бывший Дашборд)
# -----------------------------
if st.session_state.page == "Главное меню":
    deals = Deal.objects.filter(owner=user)
    tasks = Tasks.objects.filter(owner=user)
    notes = Note.objects.filter(deal__owner=user)

    active_deals = deals.filter(status="active").count()
    completed_deals = deals.filter(status="completed").count()
    open_tasks = tasks.filter(status=False).count()
    completed_tasks = tasks.filter(status=True).count()
    total_cash = sum(d.cash for d in deals)

    st.markdown(
        f'<div class="hero"><h1>Добро пожаловать, {user.username} 👋</h1>'
        f'<p class="muted">Управляй делами, задачами и заметками в одном месте.</p></div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (c1, "Активные дела", active_deals),
        (c2, "Завершённые дела", completed_deals),
        (c3, "Открытые задачи", open_tasks),
        (c4, "Выполненные задачи", completed_tasks),
        (c5, "Сумма", f"{total_cash:,}".replace(",", " ") + " сом"),
    ]
    for col, label, value in metrics:
        with col:
            st.markdown(
                f'<div class="metric-card"><div class="muted">{label}</div><h2>{value}</h2></div>',
                unsafe_allow_html=True,
            )

    # --- поиск дел по названию/описанию — теперь здесь, в Главном меню ---
    st.subheader("🔎 Найти дело")
    search = st.text_input(
        "Поиск по названию или описанию",
        key="dashboard_deal_search",
        placeholder="Например: «сайт клиенту» или часть описания",
    )

    if search:
        found = deals.filter(
            Q(title_deal__icontains=search) | Q(description__icontains=search)
        ).order_by("-updated_at")

        if not found:
            st.warning("Ничего не найдено.")
        else:
            st.caption(f"Найдено дел: {found.count()}")
            for deal in found:
                with st.container(border=True):
                    a, b, c = st.columns([5, 2, 1])
                    with a:
                        st.write(f"**{deal.title_deal}**")
                        st.caption(deal.description[:140] if deal.description else "Без описания")
                    with b:
                        st.write(f"Статус: **{deal.get_status_display()}**")
                        st.caption(f"💰 {deal.cash} сом")
                    with c:
                        if st.button("Открыть", key=f"search_open_{deal.pk}"):
                            st.session_state.selected_deal = deal.pk
                            st.session_state.page = "Мои дела"
                            st.rerun()
        st.divider()

    st.subheader("Последние дела")
    recent = deals.order_by("-updated_at")[:5]
    if not recent:
        st.info("Пока нет дел. Создай первое в разделе «Мои дела».")
    else:
        for deal in recent:
            with st.container(border=True):
                a, b, c = st.columns([5, 2, 1])
                with a:
                    st.write(f"**{deal.title_deal}**")
                    st.caption(deal.description[:140] if deal.description else "Без описания")
                with b:
                    st.write(f"Статус: **{deal.get_status_display()}**")
                    st.caption(f"💰 {deal.cash} сом")
                with c:
                    if st.button("Открыть", key=f"dash_open_{deal.pk}"):
                        st.session_state.selected_deal = deal.pk
                        st.session_state.page = "Мои дела"
                        st.rerun()

    st.subheader("Ближайшие задачи")
    upcoming = tasks.filter(status=False).order_by("deadline", "-created_at")[:5]
    if not upcoming:
        st.info("Открытых задач нет.")
    else:
        for task in upcoming:
            deadline_text = task.deadline.strftime("%d.%m.%Y") if task.deadline else "без срока"
            st.write(f"- **{task.title_task}** · {task.deal.title_deal} · {deadline_text} · {task.get_level_display()}")

# -----------------------------
# Deals
# -----------------------------
elif st.session_state.page == "Мои дела":
    st.title("📁 Мои дела")

    with st.expander("➕ Создать новое дело", expanded=False):
        with st.form("create_deal"):
            title = st.text_input("Название", max_chars=100)
            description = st.text_area("Описание")
            cash = st.number_input("Сумма, сом", min_value=0, step=100)
            submitted = st.form_submit_button("Создать дело", use_container_width=True)
            if submitted:
                if not title.strip():
                    st.error("Название обязательно.")
                else:
                    Deal.objects.create(
                        owner=user,
                        title_deal=title.strip(),
                        description=description.strip(),
                        cash=int(cash),
                    )
                    notify("Дело создано!")
                    st.rerun()

    status_filter = st.selectbox("Статус", ["Все", "active", "completed", "cancelled"], format_func=lambda x: {
        "Все": "Все статусы", "active": "Активные", "completed": "Завершённые", "cancelled": "Отменённые"
    }[x])

    qs = Deal.objects.filter(owner=user)
    if status_filter != "Все":
        qs = qs.filter(status=status_filter)
    qs = qs.order_by("-updated_at")

    deals = list(qs)
    if not deals:
        st.info("Дела не найдены. Найти конкретное дело по названию можно в «Главном меню».")
    else:
        deal_ids = [d.pk for d in deals]
        labels = {d.pk: f"{d.title_deal} · {d.get_status_display()} · {d.cash} сом" for d in deals}
        current_id = st.session_state.selected_deal if st.session_state.selected_deal in deal_ids else deal_ids[0]
        selected_id = st.selectbox("Выберите дело", deal_ids, index=deal_ids.index(current_id), format_func=lambda x: labels[x])
        st.session_state.selected_deal = selected_id
        deal = Deal.objects.get(pk=selected_id, owner=user)

        with st.container(border=True):
            st.subheader(deal.title_deal)
            st.caption(f"Создано: {deal.created_at:%d.%m.%Y} · Обновлено: {deal.updated_at:%d.%m.%Y %H:%M}")
            st.write(deal.description or "Без описания")
            st.metric("Сумма", f"{deal.cash:,}".replace(",", " ") + " сом")

            with st.form(f"edit_deal_{deal.pk}"):
                e_title = st.text_input("Название", value=deal.title_deal)
                e_desc = st.text_area("Описание", value=deal.description)
                e_status = st.selectbox(
                    "Статус",
                    ["active", "completed", "cancelled"],
                    index=["active", "completed", "cancelled"].index(deal.status),
                    format_func=lambda x: {"active": "Активное", "completed": "Завершено", "cancelled": "Отменено"}[x],
                )
                e_cash = st.number_input("Сумма, сом", min_value=0, value=int(deal.cash), step=100)
                save = st.form_submit_button("💾 Сохранить изменения", use_container_width=True)
                if save:
                    deal.title_deal = e_title.strip()
                    deal.description = e_desc.strip()
                    deal.status = e_status
                    deal.cash = int(e_cash)
                    deal.save()
                    notify("Изменения сохранены!")
                    st.rerun()

            if st.button("🗑️ Удалить дело", key=f"delete_deal_{deal.pk}", type="secondary"):
                deal.delete()
                st.session_state.selected_deal = None
                notify("Дело удалено.", "warning")
                st.rerun()

        st.subheader("📝 Заметки этого дела")
        with st.form(f"note_form_{deal.pk}"):
            n_title = st.text_input("Заголовок заметки")
            n_desc = st.text_area("Текст заметки")
            add_note = st.form_submit_button("Добавить заметку", use_container_width=True)
            if add_note:
                if not n_title.strip():
                    st.error("Заголовок заметки обязателен.")
                else:
                    Note.objects.create(deal=deal, title_note=n_title.strip(), description=n_desc.strip())
                    notify("Заметка добавлена!")
                    st.rerun()

        notes = Note.objects.filter(deal=deal).order_by("-date_note")
        for note in notes:
            with st.container(border=True):
                a, b = st.columns([6, 1])
                with a:
                    st.write(f"**{note.title_note}**")
                    st.caption(f"{note.date_note:%d.%m.%Y}")
                    st.write(note.description or "")
                with b:
                    if st.button("Удалить", key=f"del_note_{note.pk}"):
                        note.delete()
                        st.rerun()

# -----------------------------
# Tasks
# -----------------------------
elif st.session_state.page == "Задачи":
    st.title("✅ Задачи")

    deals = list(Deal.objects.filter(owner=user).order_by("title_deal"))
    if not deals:
        st.warning("Сначала создай хотя бы одно дело в разделе «Мои дела».")
    else:
        with st.expander("➕ Создать задачу", expanded=False):
            with st.form("create_task"):
                t_title = st.text_input("Название задачи", max_chars=100)
                t_desc = st.text_area("Описание")
                t_deal = st.selectbox("Дело", deals, format_func=lambda d: d.title_deal)
                t_level = st.selectbox("Приоритет", ["easy", "medium", "high", "critical"], format_func=lambda x: {
                    "easy": "Лёгкий", "medium": "Средний", "high": "Высокий", "critical": "Критический"
                }[x])
                has_deadline = st.checkbox("Установить дедлайн")
                t_deadline = st.date_input("Дедлайн", value=date.today()) if has_deadline else None
                create = st.form_submit_button("Создать задачу", use_container_width=True)
                if create:
                    if not t_title.strip():
                        st.error("Название обязательно.")
                    else:
                        Tasks.objects.create(
                            owner=user,
                            deal=t_deal,
                            title_task=t_title.strip(),
                            description=t_desc.strip(),
                            level=t_level,
                            deadline=t_deadline,
                        )
                        notify("Задача создана!")
                        st.rerun()

        filter_done = st.selectbox("Показать", ["Все", "Открытые", "Выполненные"])
        task_qs = Tasks.objects.filter(owner=user).select_related("deal").order_by("status", "deadline", "-created_at")
        if filter_done == "Открытые":
            task_qs = task_qs.filter(status=False)
        elif filter_done == "Выполненные":
            task_qs = task_qs.filter(status=True)

        for task in task_qs:
            with st.container(border=True):
                c1, c2, c3 = st.columns([0.6, 5, 1.4])
                with c1:
                    done = st.checkbox("", value=task.status, key=f"done_{task.pk}")
                    if done != task.status:
                        task.status = done
                        task.save(update_fields=["status"])
                        st.rerun()
                with c2:
                    st.write(f"**{task.title_task}**")
                    st.caption(f"📁 {task.deal.title_deal} · Приоритет: {task.get_level_display()}")
                    st.write(task.description or "Без описания")
                    if task.deadline:
                        st.caption(f"📅 Дедлайн: {task.deadline:%d.%m.%Y}")
                with c3:
                    if st.button("🗑️", key=f"del_task_{task.pk}", help="Удалить задачу"):
                        task.delete()
                        st.rerun()

# -----------------------------
# Notes
# -----------------------------
elif st.session_state.page == "Заметки":
    st.title("📝 Все заметки")
    notes = Note.objects.filter(deal__owner=user).select_related("deal").order_by("-date_note")
    if not notes:
        st.info("Пока нет заметок.")
    else:
        for note in notes:
            with st.container(border=True):
                st.write(f"**{note.title_note}**")
                st.caption(f"📁 {note.deal.title_deal} · {note.date_note:%d.%m.%Y}")
                st.write(note.description or "")
                if st.button("Удалить", key=f"all_del_note_{note.pk}"):
                    note.delete()
                    st.rerun()

# -----------------------------
# Profile
# -----------------------------
elif st.session_state.page == "Профиль":
    st.title("👤 Профиль")
    with st.form("profile_form"):
        p_username = st.text_input("Логин", value=user.username)
        p_email = st.text_input("Email", value=user.email or "")
        p_phone = st.text_input("Телефон", value=str(user.phone_number or ""))
        p_age = st.number_input("Возраст", min_value=10, max_value=100, value=int(user.age), step=1)
        save_profile = st.form_submit_button("Сохранить профиль", use_container_width=True)
        if save_profile:
            if not p_username.strip():
                st.error("Логин не может быть пустым.")
            elif User.objects.exclude(pk=user.pk).filter(username=p_username.strip()).exists():
                st.error("Такой логин уже занят.")
            else:
                user.username = p_username.strip()
                user.email = p_email.strip()
                user.phone_number = p_phone.strip()
                user.age = int(p_age)
                user.save()
                notify("Профиль обновлён!")
                st.rerun()

    st.subheader("🔐 Смена пароля")
    with st.form("password_form"):
        old_password = st.text_input("Текущий пароль", type="password")
        new_password = st.text_input("Новый пароль", type="password")
        new_password2 = st.text_input("Повторите новый пароль", type="password")
        change_password = st.form_submit_button("Изменить пароль", use_container_width=True)
        if change_password:
            if not user.check_password(old_password):
                st.error("Текущий пароль введён неверно.")
            elif len(new_password) < 6:
                st.error("Новый пароль должен содержать минимум 6 символов.")
            elif new_password != new_password2:
                st.error("Новые пароли не совпадают.")
            else:
                user.set_password(new_password)
                user.save(update_fields=["password"])
                notify("Пароль изменён!")
                st.rerun()