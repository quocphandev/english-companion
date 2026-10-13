FROM python:3.13-slim

# Không tạo .pyc, log ra ngay lập tức
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Cài thư viện trước để Docker cache lớp này khi sửa code.
# Dùng file lock: đúng phiên bản đã chạy test (Python 3.13).
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY . .

# Chạy bằng user thường, không dùng root
RUN useradd --create-home appuser && chown -R appuser /code
USER appuser

EXPOSE 8000
# Khi khởi động: áp migration rồi chạy app.
# - PORT do nền tảng host (Render) cấp; chạy local thì mặc định 8000.
# - 0.0.0.0 vì trong container phải nhận kết nối từ bên ngoài container.
# - --proxy-headers: lấy IP thật của người dùng từ proxy HTTPS của host (cho rate limit).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
