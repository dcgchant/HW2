FROM python:3.14.8-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --only-binary=:all: -r requirements.txt \
    && python -m pip check

COPY prepare_model.py ./
RUN python prepare_model.py \
    && cp /usr/share/common-licenses/Apache-2.0 models/LICENSE

COPY app.py classifier.py ./
COPY static/ ./static/

USER 10001:10001
# Exercise the same loader, image preprocessing, and CPU inference as the app.
RUN python -c "from io import BytesIO; from PIL import Image; from classifier import Classifier; model = Classifier(); sample = BytesIO(); Image.new('RGB', (224, 224), 'green').save(sample, format='PNG'); result = model.classify(sample.getvalue()); assert model.session.get_providers() == ['CPUExecutionProvider']; assert len(result['predictions']) == 3; print('CPU model load and inference passed')"

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/health', timeout=3).close()"]

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
