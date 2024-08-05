FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY /RentalGuru .

RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["sh", "entrypoint.sh"]

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "RentalGuru.asgi:application"]
EXPOSE 8000