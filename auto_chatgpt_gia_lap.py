import os
import re
import time
import random
import base64
import requests
import unicodedata
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc
import gspread
from oauth2client.service_account import ServiceAccountCredentials


# ==== CONFIG ====
IMAGE_INPUT_DIR = r"C:\SunnyzGroup\Code\auto-gemini\image_goc"
OUTPUT_DIR = r"C:\SunnyzGroup\Code\auto-gemini\output chatgpt"
CREDENTIAL_PATH = r"C:\SunnyzGroup\Code\auto-gemini\credentials.json"
SHEET_KEY = "17-RY-2rVg-bEbPONs_h5fNT7630c0oalMSV6HiT3vlM"

os.makedirs(IMAGE_INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==== GOOGLE SHEET ====
def connect_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIAL_PATH, scope)
    return gspread.authorize(creds)


def get_sheet_data(client):
    sheet = client.open_by_key(SHEET_KEY).worksheet("PROMPT YOUTOBE")
    data = sheet.get_all_values()[1:]
    prompts_A = [row[0] for row in data if row[0].strip()]
    prompts_B = [row[1] for row in data if len(row) > 1 and row[1].strip()]
    return prompts_A, prompts_B


# ==== HỖ TRỢ ====
def remove_vietnamese(text):
    """Bỏ dấu tiếng Việt"""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def safe_filename(name):
    """Chuyển tên file thành định dạng an toàn"""
    name = remove_vietnamese(name)
    name = re.sub(r'[\\/:"*?<>|#]+', "_", name)
    name = name.replace("(", "").replace(")", "").strip()
    if len(name) > 60:
        name = name[:60]
    return name


def scroll_to_bottom(driver):
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
    except Exception as e:
        print(f"⚠️ Không thể cuộn trang: {e}")


# ==== SELENIUM SETUP ====
def create_driver():
    options = uc.ChromeOptions()
    prefs = {"download.default_directory": OUTPUT_DIR, "safebrowsing.enabled": True}
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(115,130)}.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    print(f"🧩 Using user-agent: {user_agent}")
    return uc.Chrome(options=options, headless=False)


# ==== LOGIN ====
def login_to_chatgpt(driver):
    driver.get("https://chat.openai.com/")
    print("🔐 Mở trang ChatGPT...")
    print("➡️ Đăng nhập thủ công (chỉ lần đầu).")
    time.sleep(50)
    try:
        WebDriverWait(driver, 600).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[id='prompt-textarea'][contenteditable='true']"))
        )
        print("✅ Đăng nhập thành công vào ChatGPT!")
    except TimeoutException:
        print("❌ Hết thời gian chờ — Có thể bạn chưa đăng nhập hoặc selector sai.")
        driver.quit()
        exit()
    time.sleep(15)


# ==== GỬI PROMPT + ẢNH ====
def send_prompt(driver, prompt, image_path=None):
    try:
        scroll_to_bottom(driver)

        # Upload ảnh
        if image_path and os.path.exists(image_path):
            print(f"📤 Upload ảnh: {os.path.basename(image_path)}")
            upload_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file'][accept^='image']")
            if upload_inputs:
                upload_inputs[-1].send_keys(image_path)
                print("✅ Ảnh đã upload thành công.")
                time.sleep(30)
            else:
                print("⚠️ Không tìm thấy ô upload ảnh.")

        # Gửi prompt
        input_box = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[id='prompt-textarea'][contenteditable='true']"))
        )
        time.sleep(3)
        input_box.click()
        input_box.send_keys(prompt)
        print(f"📝 Prompt: {prompt[:100]}...")

        send_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='send-button']"))
        )
        driver.execute_script("arguments[0].click();", send_button)
        print("📨 Đã gửi prompt.")
        # Đợi GPT xử lý xong
        WebDriverWait(driver, 240).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label='Stop generating']"))
        )
        time.sleep(240)  # đủ để ảnh render xong
        print("✅ GPT đã phản hồi xong.")


    except Exception as e:
        print(f"⚠️ Lỗi khi gửi prompt: {e}")


# ==== LƯU ẢNH GPT ====
def save_generated_images(driver, output_folder, file_prefix):
    """Lưu ảnh GPT sinh ra (fix lỗi trùng safe_name)"""
    scroll_to_bottom(driver)
    time.sleep(2)
    os.makedirs(output_folder, exist_ok=True)
    print("⏳ Đang tìm ảnh GPT sinh ra...")

    try:
        images = driver.find_elements(
            By.CSS_SELECTOR,
            "img[alt*='Generated image'], img[alt='Generated image'], "
            "img[src*='/backend-api/estuary/content'], "
            "img[alt='Image'], img[alt*='Generated'], img[alt*='Result']"
        )
        if not images:
            print("⚠️ Không có ảnh GPT nào được tạo.")
            return

        latest_img = images[-1]
        src = latest_img.get_attribute("src")

        # chỉ tạo safe name 1 lần
        file_name = f"{file_prefix}.png"
        img_path = os.path.join(output_folder, file_name)

        # Lưu ảnh
        if src.startswith("data:image"):
            img_data = base64.b64decode(src.split(",")[1])
            with open(img_path, "wb") as f:
                f.write(img_data)
            print(f"💾 Đã lưu ảnh GPT (base64): {img_path}")

        elif "backend-api/estuary/content" in src:
            # ✅ Dùng cookie của phiên ChatGPT
            cookies = driver.get_cookies()
            cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/130.0.0.0 Safari/537.36",
                "Cookie": cookie_header,
            }

            print("📥 Đang tải ảnh từ ChatGPT backend...")
            r = requests.get(src, headers=headers)
            if r.status_code == 200 and len(r.content) > 1024:
                with open(img_path, "wb") as f:
                    f.write(r.content)
                print(f"💾 Đã lưu ảnh GPT (auth): {img_path}")
            else:
                print(f"⚠️ Không thể tải ảnh. Mã lỗi {r.status_code}, dung lượng: {len(r.content)} bytes")

        else:
            # fallback HTTPS
            r = requests.get(src)
            if r.status_code == 200:
                with open(img_path, "wb") as f:
                    f.write(r.content)
                print(f"💾 Đã lưu ảnh GPT (https): {img_path}")
            else:
                print(f"⚠️ Lỗi tải ảnh: HTTP {r.status_code}")

    except Exception as e:
        print(f"⚠️ Lỗi lưu ảnh: {e}")



# ==== MAIN ====
def main():
    client = connect_sheet()
    prompts_A, prompts_B = get_sheet_data(client)
    driver = create_driver()
    login_to_chatgpt(driver)

    image_files = [f for f in os.listdir(IMAGE_INPUT_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    print(f"📸 Tổng {len(image_files)} ảnh cần xử lý")

    for img_file in image_files:
        img_name = os.path.splitext(img_file)[0]
        safe_name = safe_filename(img_name)
        img_path = os.path.join(IMAGE_INPUT_DIR, img_file)
        # img_output_dir = os.path.join(OUTPUT_DIR, safe_name)
        # os.makedirs(img_output_dir, exist_ok=True)
        print(f"\n=== 🔹 Đang xử lý ảnh: {img_name} ===")

        # Gửi prompt + ảnh
        prompt_A = random.choice(prompts_A)
        send_prompt(driver, prompt_A, image_path=img_path)
        save_generated_images(driver, OUTPUT_DIR, f"{safe_name}_1")

        # 🔄 F5 lại để tránh dính ảnh cũ
        print("🔄 Làm mới trang để reset session ảnh...")
        driver.refresh()
        time.sleep(20)

    print("🎉 Hoàn tất toàn bộ ảnh!")
    driver.quit()


if __name__ == "__main__":
    main()
