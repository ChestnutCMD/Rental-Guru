FROM python:3.10

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY /RentalGuru .

ENTRYPOINT ["bash", "entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "RentalGuru.asgi:application"]
EXPOSE 8000