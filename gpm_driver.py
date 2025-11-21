from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def create_gpm_driver():
    chrome_options = Options()

    # ⚡ CHÚ Ý: Chỉ cần dòng này để kết nối GPM
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    # ❗ BẮT BUỘC: Tắt Selenium Manager để CHỈ dùng debug mode
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    # ⚡ Trick quan trọng: KHÔNG CHO SELENIUM TỰ TÌM chromedriver
    service = Service(executable_path="")   # ép Selenium bỏ qua chromedriver

    driver = webdriver.Chrome(service=service, options=chrome_options)

    print("🔥 Selenium đã kết nối GPM Browser qua port 9222!")
    return driver