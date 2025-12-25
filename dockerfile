FROM python:3.9

# 1. Install dependencies for Chrome, Xvfb, and Key management
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
    dbus \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*


# 2. Install Google Chrome Stable (Modern Method)
# We manually download the key, dearmor it, and place it in the trusted keyrings folder
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

# 3. Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy application code
COPY . .

# Grant execution permission to the start script
RUN chmod +x start.sh

# 5. Run command: Use the start script
CMD ["./start.sh"]