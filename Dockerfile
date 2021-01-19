FROM python:3.8

ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python", "agent_ensurer.py"]
