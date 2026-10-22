FROM python:3.14.9-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/IMS-Toucan

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        espeak-ng \
        ffmpeg \
        libportaudio2 \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-inference.txt /opt/IMS-Toucan/requirements-inference.txt

RUN pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements-inference.txt

COPY . /opt/IMS-Toucan

EXPOSE 8765
CMD ["python", "cherokee_tts_api.py"]