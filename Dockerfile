FROM python:3.11.9   # better than 3.10/3.13 for Pyrofork

WORKDIR /app

COPY requirements.txt /app/
RUN pip3 install -r requirements.txt

COPY . /app

CMD python3 bot.py & gunicorn app:app --bind 0.0.0.0:8000
