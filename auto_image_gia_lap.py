import os
import time
import random
import re
from pathlib import Path
from io import BytesIO
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==== CONFIG ====
IMAGE_INPUT_DIR = r"C:\SunnyzGroup\Code\auto-gemini\image_goc"
OUTPUT_DIR = r"C:\SunnyzGroup\Code\auto-gemini\output"
CREDENTIAL_PATH = r"C:\SunnyzGroup\Code\auto-gemini\credentials.json"
SHEET_KEY = "17-RY-2rVg-bEbPONs_h5fNT7630c0oalMSV6HiT3vlM"


# ==== GOOGLE SHEET ====
def connect_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIAL_PATH, scope)
    client = gspread.authorize(creds)
    return client


def get_sheet_data(client):
    sheet = client.open_by_key(SHEET_KEY).worksheet("Sheet1")
    data = sheet.get_all_values()[1:]
    prompts_A = [row[0] for row in data if row[0].strip()]
    prompts_B = [row[1] for row in data if len(row) > 1 and row[1].strip()]
    return prompts_A, prompts_B


# ==== SELENIUM SETUP ====
def create_driver():
    options = uc.ChromeOptions()
    prefs = {
        "download.default_directory": OUTPUT_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100,130)}.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    print(f"🧩 Using user-agent: {user_agent}")
    driver = uc.Chrome(options=options, headless=False)
    return driver


def login_to_gemini(driver):
    driver.get("https://gemini.google.com/app")
    print("🔐 Đang mở trang Gemini...")
    time.sleep(15)
    print("➡️ Hãy đăng nhập thủ công vào tài khoản Google (1 lần duy nhất).")
    WebDriverWait(driver, 300).until(lambda d: "gemini.google.com/app" in d.current_url)
    print("✅ Đăng nhập thành công vào Gemini!")


# ==== HÀM HỖ TRỢ ====
def scroll_to_bottom(driver):
    """Cuộn xuống cuối khung hội thoại trong Gemini"""
    try:
        # Tìm vùng cuộn chính (Gemini thường dùng div có role='main' hoặc class chứa 'scroll')
        scroll_areas = driver.find_elements(By.CSS_SELECTOR, "div[role='main'], div[class*='scroll'], div[class*='conversation']")
        if scroll_areas:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_areas[-1])
        else:
            # fallback: cuộn toàn trang nếu không tìm thấy container riêng
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
    except Exception as e:
        print(f"⚠️ Không thể cuộn trang: {e}")


# ==== GỬI PROMPT ====
def send_prompt(driver, prompt, image_path=None):
    try:
        scroll_to_bottom(driver)

        input_box = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ql-editor[contenteditable='true']"))
        )

        # Upload ảnh (nếu có)
        if image_path and os.path.exists(image_path):
            try:
                print(f"📤 Upload ảnh: {os.path.basename(image_path)}")
                add_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Mở trình đơn tải tệp lên']"))
                )
                driver.execute_script("arguments[0].click();", add_button)
                time.sleep(1.5)

                upload_menu_btn = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test-id='local-images-files-uploader-button']"))
                )
                driver.execute_script("arguments[0].click();", upload_menu_btn)
                time.sleep(1.5)

                file_input = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                )
                file_input.send_keys(image_path)
                print(f"✅ Ảnh đã gửi: {os.path.basename(image_path)}")
                time.sleep(4)

            except Exception as e:
                print(f"⚠️ Lỗi upload ảnh: {e}")

        # Nhập prompt
        input_box.click()
        input_box.send_keys(prompt)
        print(f"📝 Prompt: {prompt[:80]}...")

        # Gửi prompt
        try:
            send_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Gửi tin nhắn']"))
            )
            driver.execute_script("arguments[0].click();", send_button)
            print("📨 Đã gửi prompt.")
        except Exception:
            print("⚠️ Nút gửi không tương tác được — dùng Enter thay thế.")
            input_box.send_keys(u'\ue007')

        # Chờ ảnh sinh xong
        # WebDriverWait(driver, 150).until(
        #     EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-test-id='download-generated-image-button']"))
        # )
        # print("✅ Đã sinh ảnh thành công.")
        time.sleep(3)

    except Exception as e:
        print(f"⚠️ Lỗi khi gửi prompt: {e}")


# ==== LƯU ẢNH ====
def save_generated_images(driver, output_folder, prefix):
    os.makedirs(output_folder, exist_ok=True)
    print("⏳ Đang tải ảnh mới nhất...")

    try:

        time.sleep(5)

        # ===== 2️⃣ Chờ đến khi KHÔNG CÒN thẻ "Vui lòng chờ trong giây lát..." hoặc spinner =====
        print("🕐 Đang chờ Gemini xử lý xong...")

        try:
            WebDriverWait(driver, 180).until_not(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div.presented-response-container.thinking"
                ))
            )
            WebDriverWait(driver, 180).until_not(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "span.bot-name-ugc-label"
                ))
            )
            print("✅ Gemini đã hoàn tất sinh ảnh.")
        except TimeoutException:
            print("⚠️ Hết thời gian chờ — vẫn còn thẻ loading, tiếp tục lưu ảnh để tránh kẹt.")

        time.sleep(15)
        # Chờ ít nhất 1 nút tải xuất hiện
        download_buttons = WebDriverWait(driver, 60).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "button[data-test-id='download-generated-image-button']")
            )
        )

        # Lấy NÚT CUỐI CÙNG — ảnh mới nhất Gemini vừa tạo
        latest_btn = download_buttons[-1]
        scroll_to_bottom(driver)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", latest_btn)
        time.sleep(1.5)
        driver.execute_script("arguments[0].click();", latest_btn)
        print("⬇️  Đã click nút tải ảnh mới nhất.")

        # Chờ file mới tải về trong OUTPUT_DIR
        latest_file = None
        for _ in range(120):
            time.sleep(1)
            files = list(Path(OUTPUT_DIR).glob("*.png")) + list(Path(OUTPUT_DIR).glob("*.jpg"))
            if files:
                latest = max(files, key=lambda f: f.stat().st_mtime)
                if latest.exists() and latest.stat().st_size > 10_000:
                    latest_file = latest
                    break

        if not latest_file:
            print(f"⚠️ Không tìm thấy ảnh mới cho {prefix}")
            return

        target_path = os.path.join(output_folder, f"{prefix}.png")
        os.rename(latest_file, target_path)
        print(f"💾 Đã lưu ảnh mới nhất: {target_path}")

    except TimeoutException:
        print("⚠️ Không tìm thấy nút tải ảnh (có thể chưa sinh ảnh).")
    except Exception as e:
        print(f"⚠️ Lỗi khi tải ảnh: {e}")



# ==== MAIN ====
def main():
    client = connect_sheet()
    prompts_A, prompts_B = get_sheet_data(client)
    driver = create_driver()
    login_to_gemini(driver)
    time.sleep(10)
    image_files = [f for f in os.listdir(IMAGE_INPUT_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    print(f"📸 Tổng {len(image_files)} ảnh cần xử lý")

    for img_file in image_files:
        img_name = os.path.splitext(img_file)[0]
        img_path = os.path.join(IMAGE_INPUT_DIR, img_file)
        img_output_dir = os.path.join(OUTPUT_DIR, img_name)
        os.makedirs(img_output_dir, exist_ok=True)

        print(f"\n=== 🔹 Đang xử lý ảnh: {img_name} ===")
        prompt_A = random.choice(prompts_A)
        send_prompt(driver, prompt_A, image_path=img_path)
        time.sleep(5)
        scroll_to_bottom(driver)
        save_generated_images(driver, img_output_dir, f"{img_name}_1")
        random_prompts_B = random.sample(prompts_B, min(2, len(prompts_B)))

        for idx, prompt_B in enumerate(random_prompts_B, start=2):
            send_prompt(driver, prompt_B)
            time.sleep(5)
            scroll_to_bottom(driver)
            save_generated_images(driver, img_output_dir, f"{img_name}_{idx}")

    print("🎉 Hoàn tất toàn bộ ảnh!")
    driver.quit()


if __name__ == "__main__":
    main()
