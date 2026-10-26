FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN useradd --system --uid 10001 --create-home --shell /usr/sbin/nologin app
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# Статика собирается на этапе сборки образа (значения ниже — только для этой команды)
RUN SECRET_KEY=build-only-$(head -c 40 /dev/urandom | od -An -tx1 | tr -d ' \n') \
    ALLOWED_HOSTS=build ADMIN_URL=build ALLOW_SQLITE=1 DATABASE_URL=sqlite:////tmp/build.sqlite3 \
    python manage.py collectstatic --noinput \
 && mkdir -p /app/media && chown -R app:app /app/media /app/staticfiles \
 && chmod +x /app/entrypoint.sh

USER app
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "mysite.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", \
     "--timeout", "30", "--graceful-timeout", "30", "--max-requests", "1000", "--max-requests-jitter", "100", \
     "--worker-tmp-dir", "/dev/shm", "--access-logfile", "-", "--error-logfile", "-"]
