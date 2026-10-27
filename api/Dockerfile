FROM python:3.12-slim
WORKDIR /app
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# shared logging + redaction code
COPY common/logsetup.py .
COPY api/ .
# don't run as root inside the container. Same uid in api and worker so both can
# write to the shared log volume.
RUN useradd --uid 1000 --create-home appuser \
    && mkdir -p /var/log/app && chown appuser /var/log/app
USER appuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
