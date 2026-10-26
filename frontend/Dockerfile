FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/app

RUN useradd --system --uid 10002 --create-home --shell /usr/sbin/nologin app
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=app:app . .
USER app
EXPOSE 8501
CMD ["streamlit", "run", "front.py"]
