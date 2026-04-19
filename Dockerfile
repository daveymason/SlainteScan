FROM python:3.11-slim

ENV PYTHONUNBUFFERED=True \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["python", "-m", "src.mcp_server"]
