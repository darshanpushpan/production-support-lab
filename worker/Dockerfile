FROM python:3.12-slim
WORKDIR /app
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# shared logging + redaction code
COPY common/logsetup.py .
COPY worker/ .
# don't run as root inside the container. Same uid in api and worker so both can
# write to the shared log volume.
RUN useradd --uid 1000 --create-home appuser \
    && mkdir -p /var/log/app && chown appuser /var/log/app
USER appuser
CMD ["python", "worker.py"]
