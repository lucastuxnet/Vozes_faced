FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

# Pasta de áudios como volume persistente
RUN mkdir -p static/audio static/img

EXPOSE 5000

ENV SECRET_KEY="troque-esta-chave-em-producao"
ENV FLASK_ENV="production"

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "app:app"]
