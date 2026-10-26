FROM python:3.12-slim
WORKDIR /app
COPY receiver.py .
RUN useradd --create-home appuser
USER appuser
CMD ["python", "receiver.py"]
