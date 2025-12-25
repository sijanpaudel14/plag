from fastapi import FastAPI
from pydantic import BaseModel
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import os
import json
import base64

app = FastAPI()

class PlagiarismRequest(BaseModel):
    text: str


def get_chrome_version():
    """Detects the installed Google Chrome version."""
    try:
        cmd = os.popen("google-chrome --version").read().strip()
        # Output is like: "Google Chrome 131.0.6778.204"
        version = cmd.split()[-1].split('.')[0]
        return int(version)
    except:
        return 131  # Default fallback

def process_copychecker_network(text: str):
    options = uc.ChromeOptions()
    options.binary_location = "/usr/bin/google-chrome"
    
    # Docker/Linux specific arguments
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-setuid-sandbox")
    
    # Critical for avoiding "session not created" in some environments
    options.add_argument("--remote-debugging-port=9222") 

    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    
    chrome_ver = get_chrome_version()
    print(f"ℹ️ Detected Chrome Version: {chrome_ver}")

    driver = None
    try:
        driver = uc.Chrome(
            options=options, 
            headless=False, 
            use_subprocess=True,
            version_main=chrome_ver 
        )
        
        print("🚀 Loading CopyChecker...")
        driver.get("https://copychecker.com/")

        # ... (Rest of your interaction logic remains the same) ...
        # (Be sure to keep the indentation correct!)
        
        # --- Interaction Logic ---
        textarea = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "message")))

        ActionChains(driver).move_to_element(textarea).click().perform()
        time.sleep(2)

        driver.execute_script("arguments[0].value = arguments[1];", textarea, text)
        textarea.click()
        textarea.send_keys(" ")
        textarea.send_keys(Keys.BACKSPACE)
        time.sleep(1)

        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Check Plagiarism')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.5)
        submit_btn.click()
        # -------------------------

        # 2. MONITOR NETWORK
        print("⏳ Waiting for API response...")
        timeout = 30
        start_wait = time.time()
        target_request_id = None

        while time.time() - start_wait < timeout:
            logs = driver.get_log("performance")
            for entry in logs:
                try:
                    message = json.loads(entry["message"])["message"]
                    method = message.get("method")
                    params = message.get("params")

                    if method == "Network.responseReceived":
                        if "plagiarism-checker-api" in params.get("response", {}).get("url", ""):
                            target_request_id = params.get("requestId")

                    if method == "Network.loadingFinished" and params.get("requestId") == target_request_id:
                        body_response = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': target_request_id})
                        body_content = body_response['body']
                        if body_response.get('base64Encoded', False):
                            body_content = base64.b64decode(body_content).decode('utf-8')
                        return json.loads(body_content)
                except:
                    continue
            time.sleep(0.5)

        return {"error": "Timeout - API call not found"}

    except Exception as e:
        return {"error": f"Chrome Crash: {str(e)}"}
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

@app.post("/check-plagiarism-network")
def check_plagiarism_net(request: PlagiarismRequest):
    return process_copychecker_network(request.text)
