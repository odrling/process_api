FROM python:3-slim

RUN pip install poetry
RUN apt-get update && \
    apt-get install -y curl unzip && \
    curl https://www.pragmadev.com/downloads/Process/PROCESSV2-0-1.zip -o /PROCESS.zip && \
    unzip /PROCESS.zip && \
    rm /PROCESS.zip && \
    sh -c 'printf "\nq\n\n\n\n\n" | /PROCESS*/install-process.sh'

RUN apt-get install -y xorg xvfb

COPY pyproject.toml poetry.lock /api/
WORKDIR /api

RUN poetry install

COPY server.py entrypoint.sh /api/
ENTRYPOINT /api/entrypoint.sh
