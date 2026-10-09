FROM python:3.12-slim

# Không tạo .pyc, log ra ngay lập tức

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Cài thư viện trước để Docker cache lớp này khi sửa code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Chạy bằng user thường, không dùng root
RUN adduser --create-home appuser && chown -R appuser /code
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
