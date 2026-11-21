FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --gid 10001 superturiya && useradd --uid 10001 --gid 10001 --no-create-home superturiya && mkdir /data && chown 10001:10001 /data
COPY superturiya/ ./superturiya/
COPY benchmark/ ./benchmark/
COPY evidence/ ./evidence/
COPY web/ ./web/
USER 10001:10001
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=3)"
CMD ["python", "-m", "superturiya", "--host", "0.0.0.0", "--port", "8765", "--db", "/data/superturiya.db"]
