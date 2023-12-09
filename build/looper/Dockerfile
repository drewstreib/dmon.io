FROM python:3-slim

WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

WORKDIR /app
#ENTRYPOINT ["tail", "-F", "/dev/null"]
ENTRYPOINT ["python3", "loop_checker.py"]
