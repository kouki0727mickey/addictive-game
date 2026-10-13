# GPU サーバー向け（NVIDIA Container Toolkit が必要）
#   docker build -t imgcls .
#   docker run --gpus all --shm-size=8g -v "$PWD/data:/app/data" -v "$PWD/outputs:/app/outputs" imgcls python scripts/verify_env.py
# CPU 版にする場合: docker build --build-arg TORCH_VARIANT=cpu -t imgcls .
FROM python:3.12-slim
ARG TORCH_VARIANT=cu126
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/${TORCH_VARIANT}
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "scripts/verify_env.py"]
