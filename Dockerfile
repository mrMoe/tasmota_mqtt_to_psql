FROM python:3.10

ENV PYTHONFAULTHANDLER=1
ENV PYTHONHASHSEED=random
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_NO_CACHE_DIR=1

RUN pip install "poetry"

WORKDIR /app
COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction --no-ansi --no-root

COPY . /app

CMD [ "poetry", "run", "python", "tasmota_mqtt_to_psql/tasmota_mqtt_to_psql.py" ]
