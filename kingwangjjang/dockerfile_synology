# Mongodb는 나중에....... AWS 할 때... 20231222
FROM python:3
ENV PYTHONUNBUFFERED 1
WORKDIR /web
COPY . .
RUN pip install -r requirements.txt

CMD [ "python", "manage.py", "runserver" ]