FROM python:3.11-slim

WORKDIR /app

COPY analytics-lambda/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY analytics-lambda/ .

RUN chmod +x entrypoint.sh

ENV PYTHONPATH=/app

ENTRYPOINT ["./entrypoint.sh"]
CMD ["python", "local_worker.py"]
