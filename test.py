import os
import random
import time
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from PIL import Image

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai


# ==== CONFIG ====
API_KEY = "AIzaSyAbtgUtm4r2LGxH7kvdTGDKHaSwn1ZvQMQ"  # <-- Dán key API Gemini của bạn
IMAGE_INPUT_DIR = r"C:\SunnyzGroup\Code\auto-gemini\image goc"
OUTPUT_DIR = r"C:\SunnyzGroup\Code\auto-gemini\output"
MAX_WORKERS = 3  # số ảnh chạy song song
SHEET_KEY = "17-RY-2rVg-bEbPONs_h5fNT7630c0oalMSV6HiT3vlM"
CREDENTIAL_PATH = r"C:\SunnyzGroup\Code\auto-gemini\credentials.json"

# ==== GOOGLE SHEET ====
def connect_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIAL_PATH, scope)
    client = gspread.authorize(creds)
    return client


def get_sheet_data(client):
    sheet = client.open_by_key(SHEET_KEY).worksheet("Sheet1")
    data = sheet.get_all_values()[1:]
    prompts_A = [row[0] for row in data if row[0].strip()]
    prompts_B = [row[1] for row in data if len(row) > 1 and row[1].strip()]
    return prompts_A, prompts_B


def log_to_sheet(client, img_name, prompt, file_path):
    try:
        sheet = client.open_by_key(SHEET_KEY).worksheet("Gemini_Log")
    except gspread.exceptions.WorksheetNotFound:
        sheet = client.open_by_key(SHEET_KEY).add_worksheet(title="Gemini_Log", rows="1000", cols="4")
        sheet.append_row(["Time", "Image Name", "Prompt", "Output Path"])
    sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), img_name, prompt, file_path])


# ==== GEMINI API ====
def configure_gemini():
    genai.configure(api_key=API_KEY)
    models = [m.name for m in genai.list_models()]
    if "models/imagen-4.0-generate" in models:
        print("✅ Model ảnh sẵn sàng: imagen-4.0-generate")
        return genai.GenerativeModel("imagen-4.0-generate")
    else:
        print("⚠️ Không tìm thấy model tạo ảnh (imagen-4.0-generate). Có thể bạn chưa bật Billing hoặc project chưa hỗ trợ hình ảnh.")
        raise SystemExit("🛑 Dừng chương trình: Cần bật billing hoặc chọn project khác trong Google Cloud.")


def save_generated_image(response, save_path):
    try:
        image_data = response.images[0].data
        image = Image.open(BytesIO(image_data))
        image.save(save_path)
        print(f"✅ Ảnh đã lưu: {save_path}")
    except Exception as e:
        print(f"❌ Không thể lưu ảnh: {e}")


def generate_with_gemini(model, prompt, image_path=None):
    try:
        if image_path and os.path.exists(image_path):
            uploaded_file = genai.upload_file(image_path)
            response = model.generate_content([uploaded_file, prompt])
        else:
            response = model.generate_content(prompt)
        return response
    except Exception as e:
        if "PERMISSION_DENIED" in str(e) or "billing" in str(e).lower():
            raise SystemExit("🛑 Lỗi: API chưa bật billing. Hãy bật thanh toán tại https://console.cloud.google.com/billing")
        raise


# ==== XỬ LÝ 1 ẢNH ====
def process_image(img_file, prompts_A, prompts_B, model, sheet_client):
    img_name = os.path.splitext(img_file)[0]
    img_path = os.path.join(IMAGE_INPUT_DIR, img_file)
    img_output_dir = os.path.join(OUTPUT_DIR, img_name)
    os.makedirs(img_output_dir, exist_ok=True)

    print(f"\n=== 🔹 Đang xử lý ảnh: {img_name} ===")
    prompt_A = random.choice(prompts_A)

    # Lệnh 1: prompt + ảnh
    print(f"👉 Lệnh 1: {prompt_A}")
    try:
        response = generate_with_gemini(model, prompt_A, image_path=img_path)
        file_path = os.path.join(img_output_dir, f"{img_name}_1.png")
        save_generated_image(response, file_path)
        log_to_sheet(sheet_client, img_name, prompt_A, file_path)
    except Exception as e:
        print(f"❌ Lỗi ở lệnh 1 ({img_name}): {e}")

    # Lệnh 2,3,4... từ cột B (chỉ text)
    for i, prompt_B in enumerate(prompts_B, start=2):
        print(f"👉 Lệnh {i}: {prompt_B}")
        try:
            response = generate_with_gemini(model, prompt_B)
            file_path = os.path.join(img_output_dir, f"{img_name}_{i}.png")
            save_generated_image(response, file_path)
            log_to_sheet(sheet_client, img_name, prompt_B, file_path)
        except Exception as e:
            print(f"❌ Lỗi ở lệnh {i} ({img_name}): {e}")
        time.sleep(2)


# ==== MAIN ====
def main():
    print("🔗 Kết nối Google Sheet...")
    sheet_client = connect_sheet()
    prompts_A, prompts_B = get_sheet_data(sheet_client)
    model = configure_gemini()

    image_files = [f for f in os.listdir(IMAGE_INPUT_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    print(f"📸 Tổng số ảnh cần xử lý: {len(image_files)}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for img_file in image_files:
            executor.submit(process_image, img_file, prompts_A, prompts_B, model, sheet_client)

    print("\n🎉 Hoàn tất quá trình tạo ảnh!")


if __name__ == "__main__":
    main()
