FROM python:3.9-slim

# 1. Install dependencies for Chrome and Xvfb
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libnss3 \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Google Chrome Stable
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

# 3. Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy application code
COPY . .

# 5. Run command: Use xvfb-run to simulate a display
CMD ["xvfb-run", "-a", "--server-args='-screen 0 1280x800x24'", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
