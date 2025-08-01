import requests
import time
import re
import random
import string
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# --- PENTING: JALUR CHROME DRIVER MANUAL ---
# GANTI JALUR DI BAWAH INI DENGAN LOKASI FILE chromedriver.exe ANDA
# Contoh: r"C:\Users\dani\Downloads\chromedriver.exe"
# r"" digunakan untuk memastikan Python membaca path sebagai raw string
CHROME_DRIVER_PATH = r"C:\path\to\your\chromedriver.exe" 

# --- Konfigurasi API Mail.tm ---
MAILTM_API_BASE_URL = "https://api.mail.tm"

# --- Konfigurasi Situs Target ---
URL_SIGNUP_PAGE = "https://waypoint.roninchain.com/register?clientId=767d97f1-8c63-44c3-86ed-c0c97e270e89&redirect=https%3A%2F%2Fwww.partyicons.com&origin=https%3A%2F%2Fwww.partyicons.com&state=158387ec-3706-41c9-9642-ff9bc3f21ad8&continue=%2Fclient%2F767d97f1-8c63-44c3-86ed-c0c97e270e89%2Fauthorize%3Fredirect%3Dhttps%253A%252F%252Fwww.partyicons.com%26scope%3Demail%2Bopenid%2Bprofile%2Bwallet%26origin%3Dhttps%253A%252F%252Fwww.partyicons.com%26state%3D158387ec-3706-41c9-9642-ff9bc3f21ad8&method=password"

# --- Fungsi untuk membuat password acak yang kuat ---
def generate_random_password(length=12):
    """Menghasilkan password acak yang kuat."""
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for i in range(length))
    return password

# --- Fungsi untuk membuat passphrase acak ---
def generate_passphrase():
    """Menghasilkan passphrase acak dengan 12 kata umum."""
    # Anda bisa mengganti daftar kata ini sesuai kebutuhan
    words = ["apple", "banana", "cat", "dog", "elephant", "flower", "grape", "house", "icecream", "jacket", "key", "lemon"]
    random.shuffle(words)
    passphrase = " ".join(words[:12])
    return passphrase

# --- Fungsi untuk menyimpan hasil pendaftaran ke file ---
def save_to_file(filename, content):
    """Menyimpan konten ke file yang diberikan."""
    try:
        # Menggunakan mode 'a' untuk menambahkan data baru tanpa menghapus data sebelumnya
        with open(filename, "a") as f:
            f.write(content + "\n")
        print(f"Data akun berhasil disimpan ke {filename}")
    except IOError as e:
        print(f"Gagal menyimpan ke file: {e}")

# --- Fungsi untuk membuat akun email baru dari Mail.tm ---
def create_mailtm_account():
    """Membuat akun email sementara dan mengembalikan alamat email, ID akun, serta password."""
    print("Membuat akun email sementara...")
    headers = {"Content-Type": "application/json"}
    
    try:
        domains_response = requests.get(f"{MAILTM_API_BASE_URL}/domains")
        domains_response.raise_for_status()
        domain = domains_response.json()["hydra:member"][0]["domain"]
    except requests.exceptions.RequestException as e:
        print(f"Gagal mendapatkan domain dari Mail.tm: {e}")
        return None, None, None

    username = "user" + str(int(time.time()))
    mailtm_password = generate_random_password(16)
    email_address = f"{username}@{domain}"
    
    data = {
        "address": email_address,
        "password": mailtm_password
    }

    try:
        response = requests.post(f"{MAILTM_API_BASE_URL}/accounts", headers=headers, json=data)
        response.raise_for_status()
        account_id = response.json()["id"]
        print(f"Akun email baru berhasil dibuat: {email_address}")
        return email_address, account_id, mailtm_password
    except requests.exceptions.RequestException as e:
        print(f"Gagal membuat akun Mail.tm: {e}")
        return None, None, None

# --- Fungsi untuk mendapatkan token login dari Mail.tm ---
def get_mailtm_token(email, password):
    """Mendapatkan token otorisasi untuk mengakses inbox."""
    headers = {"Content-Type": "application/json"}
    data = {
        "address": email,
        "password": password
    }
    try:
        response = requests.post(f"{MAILTM_API_BASE_URL}/token", headers=headers, json=data)
        response.raise_for_status()
        token = response.json()["token"]
        return token
    except requests.exceptions.RequestException as e:
        print(f"Gagal mendapatkan token Mail.tm: {e}")
        return None

# --- FUNGSI BARU: untuk menghapus pesan ---
def delete_mailtm_message(token, message_id):
    """Menghapus pesan dari inbox Mail.tm."""
    print(f"Menghapus pesan dengan ID: {message_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.delete(f"{MAILTM_API_BASE_URL}/messages/{message_id}", headers=headers)
        response.raise_for_status()
        print("Pesan berhasil dihapus dari inbox.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Gagal menghapus pesan: {e}")
        return False

# --- Fungsi untuk memeriksa inbox, menyimpan, dan mencari kode verifikasi ---
def check_for_verification_code(token, max_retries=15, delay=5):
    """Memeriksa inbox secara berulang, menyimpan isi, dan mencari kode verifikasi 6 digit."""
    print("Menunggu email verifikasi...")
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(max_retries):
        try:
            response = requests.get(f"{MAILTM_API_BASE_URL}/messages", headers=headers)
            response.raise_for_status()
            messages = response.json()["hydra:member"]

            if messages:
                print("Email verifikasi ditemukan!")
                latest_email_id = messages[0]["id"]
                
                email_response = requests.get(f"{MAILTM_API_BASE_URL}/messages/{latest_email_id}", headers=headers)
                email_response.raise_for_status()
                email_content = email_response.json()["text"]

                # Menulis konten email ke file pesan.txt (akan menimpa file lama)
                with open("pesan.txt", "w") as f:
                    f.write(email_content)
                print("Konten email berhasil disimpan ke pesan.txt")
                
                match = re.search(r'\b(\d{6})\b', email_content)
                if match:
                    verification_code = match.group(1)
                    print(f"Kode verifikasi 6 digit ditemukan: {verification_code}")
                    delete_mailtm_message(token, latest_email_id)
                    return verification_code
                else:
                    print("Kode verifikasi tidak ditemukan dalam isi email.")
                    delete_mailtm_message(token, latest_email_id)
                    return None
        except requests.exceptions.RequestException as e:
            print(f"Gagal memeriksa email: {e}")
        
        print(f"Percobaan {i+1}/{max_retries}: Email belum diterima. Menunggu {delay} detik...")
        time.sleep(delay)

    print("Melebihi batas waktu tunggu untuk email verifikasi.")
    return None

# --- Fungsi untuk menangani halaman pembuatan passphrase ---
def handle_passphrase_setup(driver, wait, passphrase):
    """Mengisi dan mengirimkan formulir passphrase."""
    print("Menangani halaman pengaturan passphrase...")
    try:
        # Cek apakah elemen 'passphrase-input' ada di halaman
        passphrase_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input.passphrase-input")))
        passphrase_confirm_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.confirm-button")))
        
        passphrase_input.send_keys(passphrase)
        passphrase_confirm_button.click()
        
        print("Passphrase berhasil dimasukkan dan dikonfirmasi.")
    except TimeoutException:
        print("Waktu habis saat mencari input atau tombol passphrase.")
        raise
    except NoSuchElementException:
        print("Elemen input atau tombol passphrase tidak ditemukan.")
        raise

# --- Fungsi untuk menangani halaman otorisasi akhir ---
def handle_final_authorization(driver, wait):
    """Mengklik tombol 'Confirm' atau 'Authorize' di halaman akhir."""
    print("Menangani halaman otorisasi akhir...")
    try:
        authorize_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.authorize-btn")))
        authorize_button.click()
        print("Otorisasi akhir berhasil dikonfirmasi!")
    except TimeoutException:
        print("Waktu habis saat mencari tombol otorisasi.")
        raise
    except NoSuchElementException:
        print("Tombol otorisasi tidak ditemukan.")
        raise

# --- Fungsi utama untuk menjalankan bot ---
def run_signup_bot():
    """Mengotomatisasi proses pendaftaran dari awal hingga akhir."""
    chrome_options = Options()
    # Hapus baris ini jika Anda ingin melihat proses secara visual
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")

    # Memastikan file driver ada sebelum mencoba menggunakannya
    if not os.path.exists(CHROME_DRIVER_PATH):
        print("Kesalahan: chromedriver.exe tidak ditemukan di jalur yang diberikan.")
        print(f"Pastikan Anda mengunduh driver yang benar dan mengubah CHROME_DRIVER_PATH.")
        return
    
    try:
        # Gunakan Service untuk menunjuk ke jalur Chrome Driver yang diunduh secara manual
        service = Service(executable_path=CHROME_DRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except WebDriverException as e:
        print(f"Gagal menginisialisasi WebDriver: {e}")
        print("Pastikan Anda sudah mengunduh Chrome Driver yang sesuai dan jalurnya benar.")
        return
    
    try:
        # 1. Buat akun email sementara
        email_address, account_id, mailtm_password = create_mailtm_account()
        if not email_address:
            driver.quit()
            return
        
        print(f"Membuka halaman pendaftaran: {URL_SIGNUP_PAGE}")
        driver.get(URL_SIGNUP_PAGE)
        
        wait = WebDriverWait(driver, 30)
        
        print("Mengisi formulir pendaftaran...")
        email_input = wait.until(EC.visibility_of_element_located((By.NAME, "email")))
        password_input = wait.until(EC.visibility_of_element_located((By.NAME, "password")))
        
        signup_password = generate_random_password(12)
        
        email_input.send_keys(email_address)
        password_input.send_keys(signup_password)
        
        print("Mengklik tombol Continue...")
        submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        submit_button.click()

        print("Pendaftaran awal berhasil. Memeriksa email...")
        token = get_mailtm_token(email_address, mailtm_password)
        if not token:
            driver.quit()
            return

        verification_code = check_for_verification_code(token)
        
        if verification_code:
            print("Mengisi kode verifikasi pada halaman...")
            code_input = wait.until(EC.visibility_of_element_located((By.ID, "verification-code")))
            code_input.send_keys(verification_code)
            
            verify_button = wait.until(EC.element_to_be_clickable((By.ID, "verify-button")))
            verify_button.click()

            print("Kode verifikasi berhasil dimasukkan dan dikirim!")

            passphrase = generate_passphrase()
            handle_passphrase_setup(driver, wait, passphrase)
            
            handle_final_authorization(driver, wait)
            
            save_to_file("hasil.txt", f"Email: {email_address} | Password: {signup_password} | Passphrase: {passphrase}")

            print("Semua proses pendaftaran dan otorisasi berhasil diselesaikan!")
            
        else:
            print("Proses verifikasi gagal.")

    except (TimeoutException, NoSuchElementException) as e:
        print(f"Elemen tidak ditemukan atau waktu habis: {e}")
        print("Pastikan selector di dalam skrip sudah sesuai dengan halaman web.")
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
    finally:
        # Selalu pastikan untuk menutup driver
        if 'driver' in locals() and driver.service.is_connectable():
            driver.quit()

if __name__ == "__main__":
    run_signup_bot()
