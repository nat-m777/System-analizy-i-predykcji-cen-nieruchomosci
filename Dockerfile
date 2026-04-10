# Używamy lekkiego obrazu z Pythonem
FROM python:3.10-slim

# Ustawiamy katalog roboczy wewnątrz kontenera
WORKDIR /app

# Kopiujemy plik z listą bibliotek
COPY requirements.txt .

# Instalujemy biblioteki (w tym streamlit, pandas, itp.)
RUN pip install --no-cache-dir -r requirements.txt

# Kopiujemy całą resztę Twojego kodu do kontenera
COPY . .

# Otwieramy port, na którym działa Streamlit
EXPOSE 8501

# Komenda startowa
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]