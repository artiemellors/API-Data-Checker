FROM python:3.11-slim

WORKDIR /app

# System deps for Playwright
RUN apt-get update && apt-get install -y \
    curl wget gnupg \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Install Playwright Chromium
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

EXPOSE 8000
CMD ["uvicorn", "api_checker.main:app", "--host", "0.0.0.0", "--port", "8000"]
