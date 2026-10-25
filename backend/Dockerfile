FROM python:3.12-slim
WORKDIR /service
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home windmarket && mkdir /data && chown windmarket:windmarket /data
COPY app ./app
COPY start.sh ./start.sh
USER windmarket
EXPOSE 8000
CMD ["sh", "/service/start.sh"]
