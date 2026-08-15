FROM python:3.13-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY . .

# 清理旧数据库，让启动时重建
RUN rm -f person_job_match.db

EXPOSE 8000

CMD ["python", "main.py"]
