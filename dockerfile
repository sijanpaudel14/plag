# Use the full Python image to avoid missing shared libraries
FROM python:3.9

# 1. Install dependencies for Chrome and Xvfb

# --- BETTER VERSION ---

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    libnss3 \
    libgbm1 \
    libasound2 \
    fonts-liberation \
    libu2f-udev \
    libvulkan1 \
    xdg-utils \
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
# We use --server-args to ensure the virtual screen is large enough
CMD ["xvfb-run", "-a", "--server-args='-screen 0 1920x1080x24'", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
