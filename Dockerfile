FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV IMG_UPSCLR_ESRGAN_DIR=/opt/img-upsclr/realesrgan

WORKDIR /app

COPY requirements-web.txt /app/requirements-web.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements-web.txt

COPY esrgan_backend.py /app/esrgan_backend.py
COPY scripts/install_esrgan_backend.py /app/scripts/install_esrgan_backend.py
COPY upscaler_core.py /app/upscaler_core.py
COPY web_api.py /app/web_api.py
COPY web_frontend /app/web_frontend
RUN python /app/scripts/install_esrgan_backend.py --target-dir "${IMG_UPSCLR_ESRGAN_DIR}"

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "web_api:app", "--host", "0.0.0.0", "--port", "8000"]
