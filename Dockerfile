FROM python:3.11-slim

# Instalacja zależności systemowych i Chromium
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    wget \
    gnupg \
    unzip \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Ustawienie zmiennych środowiskowych, aby Selenium wiedziało gdzie jest Chromium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]