from fastapi import FastAPI
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os
import base64

app = FastAPI()

class PlagiarismRequest(BaseModel):
    text: str

@app.get("/")
def root():
    return {"status": "Selenium API is running"}

def process_copychecker_network(text: str):
    options = webdriver.ChromeOptions()
    options.binary_location = "/usr/bin/google-chrome"
    
    # --- DOCKER STABILITY FLAGS ---
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument("--window-size=1920,1080")
    
    # --- STEALTH / BYPASS FLAGS ---
    # "headless=new" is the modern way to run headless that looks like a real head
    # ... existing flags ...
    options.add_argument("--headless=new")
    
    # MEMORY SAVING FLAGS
    options.add_argument("--disable-dev-shm-usage") # Essential
    options.add_argument("--no-zygote")             # Disables the use of the zygote process
    options.add_argument("--single-process")        # Runs Chrome in a single process (Less reliable but saves RAM)
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    
    # Block heavy content
    prefs = {
        "profile.managed_default_content_settings.images": 2,  # Block images
        "profile.default_content_setting_values.notifications": 2, 
        "profile.managed_default_content_settings.stylesheets": 2, # Block CSS (Might break detection)
        "profile.managed_default_content_settings.cookies": 2,
        "profile.managed_default_content_settings.javascript": 1, 
        "profile.managed_default_content_settings.plugins": 2, 
        "profile.managed_default_content_settings.popups": 2, 
        "profile.managed_default_content_settings.geolocation": 2, 
        "profile.managed_default_content_settings.media_stream": 2, 
    }
    # CORRECT WAY TO ENABLE PERFORMANCE LOGGING IN SELENIUM
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    
    # Sometimes 'perfLoggingPrefs' is needed to actually capture network events
    options.add_experimental_option("perfLoggingPrefs", {
        "enableNetwork": True,
        "enablePage": False,
    })
    try:
        print("🚀 Starting Selenium (Headless=New)...")
        
        # Use webdriver_manager to get the correct driver automatically
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Execute CDP command to remove the 'navigator.webdriver' property
        # This is the #1 way Cloudflare detects bots
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })

        print("🚀 Loading CopyChecker...")
        driver.get("https://copychecker.com/")
        
        # ... (Rest of logic is the same) ...
        # NOTE: Since we are headless, we don't need to physically see the browser
        # But we do need to wait for elements.

        textarea = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "message")))
            
        # We might not need ActionChains click in headless, but let's keep it safe
        # Sometimes headless elements need to be scrolled into view to be interactable
        driver.execute_script("arguments[0].scrollIntoView(true);", textarea)
        time.sleep(1)
        
        driver.execute_script("arguments[0].value = arguments[1];", textarea, text)
        
        # Simulate typing just in case they check for key events
        textarea.send_keys(" ")
        textarea.send_keys(Keys.BACKSPACE)
        time.sleep(1)

        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Check Plagiarism')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(1) # Give it a moment
        driver.execute_script("arguments[0].click();", submit_btn)

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

        return {"error": "Timeout - API call not found (Likely blocked or slow)"}

    except Exception as e:
        return {"error": f"Selenium Error: {str(e)}"}
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

@app.post("/check-plagiarism-network")
def check_plagiarism_net(request: PlagiarismRequest):
    return process_copychecker_network(request.text)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
