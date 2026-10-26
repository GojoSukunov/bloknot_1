# Bloknot — менеджер дел, задач и заметок

Django REST API (`backend/`) + Streamlit-интерфейс (`frontend/`), PostgreSQL, nginx с HTTPS. Всё запускается одной командой `docker compose`.

## Архитектура и что видно из интернета

```
Интернет ──443──▶ nginx ──▶ frontend (Streamlit) ──внутренняя сеть──▶ backend (gunicorn/Django API) ──▶ PostgreSQL
                    ├──▶ /<ADMIN_URL>/ и /static/ ─▶ backend (админка Django)
                    └──▶ /media/ (фото профилей, только чтение)
```

Наружу опубликован **только nginx (80/443)**. API (`/api/`), база и gunicorn недоступны из интернета: ходит к API только фронт по внутренней сети. Поэтому CORS в проекте выключен за ненадобностью.

## Развёртывание на сервере (Ubuntu 22.04/24.04)

1. **Сервер.** Создайте пользователя без root, вход по SSH-ключам, отключите вход по паролю и root (`/etc/ssh/sshd_config`: `PasswordAuthentication no`, `PermitRootLogin no`). Файрвол: `ufw default deny incoming && ufw allow 22,80,443/tcp && ufw enable`. Поставьте `fail2ban` и `unattended-upgrades`.
2. **Docker.** Установите Docker Engine + compose plugin по официальной инструкции.
3. **Код.** Скопируйте проект в `/opt/bloknot`.
4. **Настройки.** `cp .env.example .env && chmod 600 .env`, заполните все поля (команды генерации секретов — в комментариях файла). `ADMIN_URL` — непредсказуемый путь, например `panel-k3x9q2`.
5. **Сертификат TLS** (DNS домена уже должен смотреть на сервер; порт 80 свободен):
   ```bash
   sudo apt install certbot
   sudo certbot certonly --standalone -d ВАШ_ДОМЕН \
     --pre-hook "docker compose -f /opt/bloknot/docker-compose.yml stop nginx" \
     --post-hook "docker compose -f /opt/bloknot/docker-compose.yml start nginx"
   ```
   Хуки сохраняются, автопродление выполняет systemd-таймер certbot.
6. **Запуск:** `docker compose up -d --build`. При старте бэкенд сам применяет миграции.
7. **Первый администратор:** `docker compose exec backend python manage.py createsuperuser`, затем вход на `https://ДОМЕН/<ADMIN_URL>/`.
8. **Проверка:** `docker compose ps` (все сервисы healthy), открыть сайт, зарегистрироваться, создать дело. Проверьте сайт на ssllabs.com и securityheaders.com.

### Бэкапы (обязательно)
Cron: `0 3 * * * /opt/bloknot/deploy/backup.sh >> /var/log/bloknot-backup.log 2>&1`. Скрипт делает дамп БД и архив медиа в `backups/` и хранит 14 дней. **Копируйте `backups/` на другой сервер или в облако** (rclone/rsync/S3) и раз в квартал проверяйте восстановление:
```bash
docker compose exec -T db pg_restore -U bloknot -d bloknot --clean --if-exists < backups/db-ДАТА.dump
```

### Обновление
```bash
git pull   # или заменить файлы
docker compose up -d --build
docker compose logs -f backend
```

## Что исправлено по сравнению с исходным проектом

**Критичные уязвимости**
- Любой пользователь мог читать профили и хеши паролей всех пользователей, назначить себе `is_superuser`, создавать/удалять пользователей. Теперь есть только `/api/me/` с явным списком полей; пароль меняется отдельным эндпоинтом с валидацией и хешированием.
- Можно было создавать задачи и заметки в чужих делах и читать чужие дела через вложенные данные задачи. Теперь владелец проверяется в сериализаторах на создание **и** обновление; `owner` только для чтения.
- Анонимный POST на создание дела давал 500. Теперь по умолчанию всё требует авторизации (`DEFAULT_PERMISSION_CLASSES`).
- `DEBUG=True`, `ALLOWED_HOSTS=['*']`, `CORS_ALLOW_ALL_ORIGINS=True` + credentials. Теперь все значения из окружения, небезопасные настройки в проде блокируют запуск приложения.

**Защита**
- Подбор паролей: `django-axes` (5 неудач → блокировка логин+IP на 15 минут) и лимиты запросов (логин 10/мин, регистрация 5/час, смена пароля 5/час, общие лимиты).
- Регистрация проверяет пароль (минимум 10 символов, частые пароли, схожесть с логином) и уникальность email без учёта регистра.
- JWT: access 15 минут, refresh 7 дней с ротацией и чёрным списком; добавлен `/api/auth/refresh/` (раньше отсутствовал, и сессия обрывалась); logout принимает только токен самого пользователя; смена пароля отзывает все токены.
- Фото профиля: до 2 МБ, только JPEG/PNG/WEBP (проверка содержимого), имя файла — случайный UUID, nginx отдаёт с `nosniff` и `sandbox`-CSP.
- Админка по секретному пути, под защитой axes и лимита запросов, с корректным `UserAdmin` (раньше пароли в админке сохранялись без хеширования).
- Убраны ненужные поверхности атаки: allauth (`/accounts/`), Swagger (`/docs/`), индекс API, браузерный интерфейс DRF.
- HTTPS, HSTS, secure-cookies, `nosniff`, запрет встраивания во фрейм, Referrer-Policy; контейнеры от непривилегированных пользователей, `cap_drop`, `no-new-privileges`, backend с read-only файловой системой.
- Пользовательский текст во фронте больше не интерпретируется как Markdown/HTML.

**Надёжность**
- PostgreSQL вместо SQLite, healthchecks, автоперезапуск, ротация логов, gunicorn с перезапуском воркеров, `/healthz/`.
- Фронт делал по запросу на каждое дело при каждом клике (N+1). Теперь один запрос с пагинацией; запросы GET повторяются при временных сбоях.
- Повреждённый `requirements.txt` (UTF-16, без simplejwt) заменён на корректный с закреплёнными версиями; зависимости фронта отдельно.
- Пагинация и стабильная сортировка, индексы, ограничение длины текстов, 24 автотеста (изоляция данных, права, лимиты, загрузка файлов, токены), CI с `pip-audit` и `check --deploy`.

## API (все пути с префиксом `/api/`, только внутри сети)

| Метод | Путь | Описание |
|---|---|---|
| POST | `auth/register/` | регистрация |
| POST | `auth/login/` | вход → `access`, `refresh`, `user` |
| POST | `auth/refresh/` | обновление токенов |
| POST | `auth/logout/` | отзыв refresh-токена |
| POST | `auth/password/` | смена пароля |
| GET/PATCH | `me/` | свой профиль |
| GET/POST | `deals/`, `deals/<id>/` | дела (с заметками; поиск `?search=`, фильтр `?status=`) |
| CRUD | `tasks/` | задачи (фильтры `deal`, `status`, `level`) |
| CRUD | `notes/` | заметки (фильтр `deal`) |

## Локальная разработка
```bash
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export DEBUG=1            # SQLite, консольная почта, localhost
python manage.py migrate && python manage.py createcachetable
python manage.py runserver
# во втором терминале
cd frontend && pip install -r requirements.txt && streamlit run front.py
python manage.py test     # тесты (из backend/, без настройки окружения)
```

## Важно знать
- **Миграция существующих данных.** Поле `email` стало уникальным: если в старой базе есть пустые или повторяющиеся email, исправьте их до `migrate`. Для нового клиента с пустой базой это не нужно. Пути API изменились (`/Tasks/` → `/api/tasks/` и т.д.).
- **Не включено в проект (рекомендуется для «максимальной» защиты):** двухфакторная аутентификация админки (`django-otp`) — до её подключения ограничьте админку по IP в `deploy/nginx/default.conf.template` (блок `allow/deny`); восстановление пароля по email (нужен SMTP); внешний мониторинг доступности и Sentry (`SENTRY_DSN` + `pip install sentry-sdk`); WAF/CDN (например, Cloudflare) перед сайтом.
- **Streamlit** не сохраняет вход при обновлении страницы (токены живут в памяти сессии) и не даёт ссылок на отдельные страницы. Для клиентского продукта в перспективе стоит заменить его на SPA (React/Vue) — API для этого уже готов; при подключении браузерного клиента нужно настроить CORS и вернуть публикацию `/api/` через nginx с лимитами.
- **Тест Docker-сборки и nginx-конфига** в среде разработки не выполнялся (там нет Docker-демона). Бэкенд проверен под gunicorn в production-режиме; `docker compose config` валиден. Первый запуск на сервере проверьте по шагу 8.
