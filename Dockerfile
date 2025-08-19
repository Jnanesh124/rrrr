# Use Python 3.11 (stable for Pyrofork)
FROM python:3.11.9

WORKDIR /app

COPY requirements.txt /app/

RUN pip3 install -r requirements.txt

COPY . /app

# Start both bot.py (polling) and a dummy Flask app for health checks
CMD python3 bot.py & gunicorn app:app --bind 0.0.0.0:8000
