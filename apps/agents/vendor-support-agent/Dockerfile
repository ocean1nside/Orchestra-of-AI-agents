FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir .

COPY src /app/src
COPY prompts /app/prompts

ENV PYTHONPATH=/app/src

EXPOSE 8010

CMD ["python", "-m", "uvicorn", "vendor_support_agent.main:app", "--host", "0.0.0.0", "--port", "8010"]

