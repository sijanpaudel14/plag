from fastapi import FastAPI
from pydantic import BaseModel
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import json
import base64

app = FastAPI()

class PlagiarismRequest(BaseModel):
    text: str

def process_copychecker_network(text: str):
    options = uc.ChromeOptions()
    
    # Critical flags for Docker/Linux environments
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument("--window-size=1920,1080")
    
    # Note: We keep headless=False and use Xvfb (virtual screen) in Docker
    # because headless=True is easily detected by anti-bot systems.
    
    try:
        # Initialize driver (Chrome is installed via Dockerfile)
        driver = uc.Chrome(options=options, headless=False, use_subprocess=False)
        
        # Enable performance logging
        driver.execute_cdp_cmd('Network.enable', {})
        
        print("🚀 Loading CopyChecker...")
        driver.get("https://copychecker.com/")

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
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(., 'Check Plagiarism')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.5)
        submit_btn.click()

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
                        response = params.get("response", {})
                        url = response.get("url", "")
                        if "plagiarism-checker-api" in url:
                            target_request_id = params.get("requestId")
                            print(f"👀 Detected target ID: {target_request_id}")

                    if method == "Network.loadingFinished":
                        request_id = params.get("requestId")
                        if request_id == target_request_id:
                            print(f"✅ Download finished: {request_id}")
                            try:
                                body_response = driver.execute_cdp_cmd(
                                    'Network.getResponseBody',
                                    {'requestId': request_id}
                                )
                                body_content = body_response['body']
                                if body_response.get('base64Encoded', False):
                                    body_content = base64.b64decode(body_content).decode('utf-8')
                                return json.loads(body_content)
                            except Exception as e:
                                print(f"⚠️ Error retrieving body: {e}")
                                continue
                except Exception:
                    continue
            time.sleep(0.5)
        return {"error": "Network timeout - API response not found"}

    except Exception as e:
        return {"error": str(e)}
    finally:
        try:
            driver.quit()
        except:
            pass

@app.post("/check-plagiarism-network")
def check_plagiarism_net(request: PlagiarismRequest):
    return process_copychecker_network(request.text)
