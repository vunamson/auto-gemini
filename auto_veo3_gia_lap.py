import os
import time
import random
import glob
import shutil
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from gpm_driver import create_gpm_driver

import gspread
from oauth2client.service_account import ServiceAccountCredentials


# ============================
# CONFIG
# ============================
IMAGE_INPUT_DIR = r"C:\SunnyzGroup\Code\tik_tok\output_image"
OUTPUT_VIDEO_DIR = r"C:\SunnyzGroup\Code\auto-gemini\output_video_veo3"
CREDENTIAL_PATH = r"C:\SunnyzGroup\Code\auto-gemini\credentials.json"
SHEET_KEY = "17-RY-2rVg-bEbPONs_h5fNT7630c0oalMSV6HiT3vlM"
GOOGLE_LABS_VIDEO_URL = "https://labs.google/fx/vi/tools/flow/project/a089489b-74bd-4d52-b774-7828554ff7c5"   # Bạn có thể thay đúng url model video

os.makedirs(IMAGE_INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_VIDEO_DIR, exist_ok=True)


# ============================
# GOOGLE SHEET
# ============================
def connect_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIAL_PATH, scope)
    return gspread.authorize(creds)


def get_prompts(client):
    sheet = client.open_by_key(SHEET_KEY).worksheet("PROMPT VEO3 KHÔNG NGƯỜI")
    rows = sheet.get_all_values()[1:]

    prompts_A = [r[0] for r in rows if r[0].strip()]
    prompts_B = [r[1] for r in rows if len(r) > 1 and r[1].strip()]

    return prompts_A, prompts_B


# ============================
# SELENIUM DRIVER
# ============================

def create_driver():
    options = uc.ChromeOptions()
    prefs = {"download.default_directory": OUTPUT_VIDEO_DIR, "safebrowsing.enabled": True}
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(115,130)}.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    print(f"🧩 Using user-agent: {user_agent}")
    return uc.Chrome(options=options, headless=False)


# def safe_open(driver, url):
#     driver.execute_script(f'window.open("{url}", "_blank");')
#     driver.switch_to.window(driver.window_handles[-1])
#     print("✅ Đã mở Google Labs trong tab mới")
#     time.sleep(3)


# ============================
# GOOGLE LABS WORKFLOW
# ============================


# def upload_image(driver, image_path):
#     print(f"📤 Uploading image: {image_path}")

#     wait = WebDriverWait(driver, 20)

#     # -----------------------------
#     # 1) CLICK BUTTON ADD (“+”)
#     # -----------------------------
#     add_btn = wait.until(EC.element_to_be_clickable(
#         (By.CSS_SELECTOR, "button.sc-c177465c-1.hVamcH.sc-d02e9a37-1.hvUQuN")
#     ))
#     add_btn.click()
#     print("👉 Clicked ADD button")
#     time.sleep(2)

#     # -----------------------------
#     # 2) CLICK UPLOAD BUTTON (“Tải lên”)
#     # -----------------------------
#     upload_btn = wait.until(EC.element_to_be_clickable(
#         (By.CSS_SELECTOR, "button.sc-fbea20b2-0.dNBWVW")
#     ))
#     upload_btn.click()
#     print("👉 Clicked UPLOAD button")
#     time.sleep(1)

#     # -----------------------------
#     # 3) SEND FILE INTO INPUT[type=file]
#     # -----------------------------
#     file_input = wait.until(EC.presence_of_element_located(
#         (By.CSS_SELECTOR, "input[type='file']")
#     ))
#     file_input.send_keys(image_path)
#     print("📁 Image sent to file input")
#     time.sleep(3)

#     # -----------------------------
#     # 4) CLICK BUTTON “Cắt và lưu”
#     # -----------------------------
#     confirm_btn = wait.until(EC.element_to_be_clickable(
#         (By.CSS_SELECTOR, "button.sc-c177465c-1.gdArnN.sc-5983bb27-7.csgOts")
#     ))
#     confirm_btn.click()
#     print("✔️ Clicked CẮT VÀ LƯU")

#     time.sleep(3)


def upload_image(driver, image_path):
    print(f"📤 Uploading image: {image_path}")

    wait = WebDriverWait(driver, 20)

    # 1) CLICK dấu + mở khung upload (không phải mở file dialog)
    add_btn = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "button.sc-c177465c-1.hVamcH.sc-d02e9a37-1.hvUQuN")
    ))
    add_btn.click()
    print("👉 Clicked ADD button")
    time.sleep(1)

    # ❌ KHÔNG CLICK nút “Tải lên” – nó mở popup Windows
    # upload_btn.click()

    # 2) Gửi file trực tiếp vào input hidden
    file_input = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "input[type='file']")
    ))

    # Hiện input ra để send_file không lỗi
    driver.execute_script("""
        arguments[0].style.display='block';
        arguments[0].style.opacity='1';
        arguments[0].style.visibility='visible';
    """, file_input)

    file_input.send_keys(image_path)
    print("📁 File sent directly into hidden input")

    time.sleep(2)

    # 3) Click “Cắt và lưu”
    confirm_btn = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "button.sc-c177465c-1.gdArnN.sc-5983bb27-7.csgOts")
    ))
    confirm_btn.click()

    print("✔️ DONE upload")
    time.sleep(2)


def enter_prompt(driver, prompt):
    print(f"✍️ Using prompt: {prompt}")
    textarea = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "textarea"))
    )
    textarea.clear()
    textarea.send_keys(prompt)
    # textarea.send_keys(Keys.ENTER)
    time.sleep(5)


def click_generate_button(driver):
    print("🎬 Generate video…")

    wait = WebDriverWait(driver, 20)

    gen_btn = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "button.sc-c177465c-1.gdArnN.sc-408537d4-2.gdXWm")
    ))

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", gen_btn)
    time.sleep(0.5)

    gen_btn.click()
    print("✔️ Clicked GENERATE button")
    time.sleep(2)


def download_video(driver ,image_path):
    wait = WebDriverWait(driver, 30)
    image_name = os.path.splitext(os.path.basename(image_path))[0]
    print("🔍 Đang tìm danh sách video đã generate...")

    # 1) Lấy danh sách video-block
    video_blocks = wait.until(EC.presence_of_all_elements_located(
        (By.CSS_SELECTOR, "div.sc-d90fd836-2.dLxTam.sc-9dc491e6-1")
    ))
    print(f"👉 Tìm thấy {len(video_blocks)} video")

    video_blocks = video_blocks[:4]   # chỉ lấy 4 video đầu

    for idx, block in enumerate(video_blocks, start=1):
        print(f"\n==============================")
        print(f"⬇️ ĐANG TẢI VIDEO {idx}")
        print("==============================")

        # -----------------------------------------
        # BƯỚC 1 — scroll đến đúng video
        # -----------------------------------------
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", block)
        time.sleep(0.6)

        # -----------------------------------------
        # BƯỚC 2 — click vào video-block để đóng overlay gLcdmv
        # -----------------------------------------
        try:
            # click vào chính video-block
            block.click()
            print("👉 Click vào video-block để đóng overlay")
            time.sleep(0.5)
        except:
            pass  # không sao
        before_files = set(os.listdir(OUTPUT_VIDEO_DIR))

        # -----------------------------------------
        # BƯỚC 3 — tìm nút download trong block  (KHÔNG tìm toàn trang)
        # -----------------------------------------
        dl_btn = WebDriverWait(block, 20).until(
            lambda b: b.find_element(By.XPATH, ".//button[.//span[contains(text(),'Tải xuống')]]")
        )

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", dl_btn)
        time.sleep(0.4)

        driver.execute_script("arguments[0].click();", dl_btn)
        print("👉 Click DOWNLOAD (force JS click)")

        # -----------------------------------------
        # BƯỚC 4 — chọn “Kích thước gốc (720p)”
        # -----------------------------------------
        size720_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(text(), 'Kích thước gốc')]")
        ))
        size720_btn.click()
        print("🎥 Đã chọn 720p")

        # -----------------------------------------
        # BƯỚC 5 — đợi tải
        # -----------------------------------------
        time.sleep(5)
        after_files = set(os.listdir(OUTPUT_VIDEO_DIR))

        new_files = list(after_files - before_files)
        if not new_files:
            print("❌ Không tìm thấy file vừa tải!")
            continue

        downloaded_file = new_files[0]
        old_path = os.path.join(OUTPUT_VIDEO_DIR, downloaded_file)
        new_name = f"{image_name}_{idx}.mp4"
        new_path = os.path.join(OUTPUT_VIDEO_DIR, new_name)

        os.rename(old_path, new_path)
        print(f"✅ Saved video as: {new_name}")

    print("\n🎉 Hoàn tất tải xong 2 video!")


# ============================
# MAIN PROCESS
# ============================
def main():
    client = connect_sheet()
    prompts_A, prompts_B = get_prompts(client)

    driver = create_driver()
    # safe_open(driver, GOOGLE_LABS_VIDEO_URL)
    driver.get(GOOGLE_LABS_VIDEO_URL)

    input("⏳ Đăng nhập Google xong nhấn Enter để chạy tiếp...")

    image_list = glob.glob(os.path.join(IMAGE_INPUT_DIR, "*.*"))

    for idx, image_path in enumerate(image_list, start=1):
        print(f"\n============================")
        print(f"📌 PROCESSING IMAGE {idx}/{len(image_list)}")
        print("============================\n")

        prompt = random.choice(prompts_A)

        # --- RUN WORKFLOW ---
        upload_image(driver, image_path)
        time.sleep(15)
        enter_prompt(driver, prompt)
        time.sleep(20)
        click_generate_button(driver)
        time.sleep(180)
        download_video(driver, image_path)

        print(f"✅ DONE: {os.path.basename(image_path)}\n")
        time.sleep(5)

    driver.quit()
    print("🎉 Completed all videos!")


# ============================
# RUN
# ============================
if __name__ == "__main__":
    main()
