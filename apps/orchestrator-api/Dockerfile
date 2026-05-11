FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY docker/entrypoint.sh /entrypoint.sh
# С Windows checkout иногда попадают CRLF — ломает shebang в Linux.
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

COPY pyproject.toml /app/pyproject.toml
COPY src /app/src
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir .

ENV PYTHONPATH=/app/src

ENTRYPOINT ["/entrypoint.sh"]

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "orchestrator_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

