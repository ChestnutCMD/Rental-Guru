FROM python:3.10

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY /RentalGuru .

ENTRYPOINT ["bash", "entrypoint.sh"]
RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "myproject.asgi:application", "--workers", "4", "--bind", "0.0.0.0:8000"]
EXPOSE 8000