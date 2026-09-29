FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip && \
    pip install uv

COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

COPY . .

CMD ["python", "-m", "growthmcp"]
