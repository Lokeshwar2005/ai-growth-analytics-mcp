FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && \
    pip install uv

COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

COPY . .

# The container does not contain credentials. Provide Meta credentials at runtime.
RUN useradd --create-home --shell /usr/sbin/nologin growthmcp && \
    chown -R growthmcp:growthmcp /app

USER growthmcp

EXPOSE 8080

CMD ["python", "-m", "growthmcp", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8080"]
