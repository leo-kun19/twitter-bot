# main_bot_pro.py
# Versi Profesional dengan Konfigurasi Terpisah dan Logging

import time
import random
import psutil
import os
import traceback
import json
import logging
from datetime import datetime, timezone, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- MODUL 1: SETUP LOGGING & KONFIGURASI ---

def setup_logging():
    """Mengkonfigurasi logging untuk mencatat ke file dan konsol."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("bot.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def load_config(filename="config.json"):
    """Memuat konfigurasi dari file JSON."""
    logging.info(f"Memuat konfigurasi dari {filename}...")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"FATAL: File konfigurasi '{filename}' tidak ditemukan.")
        exit()
    except json.JSONDecodeError:
        logging.error(f"FATAL: File '{filename}' bukan format JSON yang valid.")
        exit()

# --- Fungsi Utilitas ---
def cleanup_existing_processes():
    logging.info("Memeriksa dan membersihkan proses Chrome yang ada...")
    cleaned_count = 0
    for proc in psutil.process_iter(['pid', 'name']):
        if 'chrome' in proc.info['name'].lower(): 
            try:
                p = psutil.Process(proc.info['pid'])
                p.kill() 
                logging.info(f"Mematikan paksa proses Chrome (PID: {proc.info['pid']})")
                cleaned_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    if cleaned_count > 0:
        logging.info(f"Selesai. {cleaned_count} proses dibersihkan. Menunggu sebentar...")
        time.sleep(3) 
    else:
        logging.info("Tidak ada proses Chrome yang berjalan.")

def get_credentials():
    """Memuat kredensial dari Environment Variables untuk keamanan hosting."""
    logging.info("Memuat kredensial dari environment variables...")
    creds = {
        "username": os.environ.get('TWITTER_USERNAME'),
        "password": os.environ.get('TWITTER_PASSWORD'),
        "email": os.environ.get('TWITTER_EMAIL') 
    }
    if not creds['username'] or not creds['password']:
        logging.error("FATAL: Environment variables 'TWITTER_USERNAME' dan 'TWITTER_PASSWORD' tidak diatur.")
        logging.error("Harap atur variabel ini di platform hosting Anda.")
        exit()
    return creds
def load_replied_tweets(filepath='replied_tweets.txt'):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def save_replied_tweet(filepath, tweet_id):
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(tweet_id + '\n')

def get_tweet_id_from_url(url):
    try:
        return url.split('/status/')[1].split('?')[0]
    except IndexError:
        return None

def spin(text):
    while '{' in text:
        start_index = text.rfind('{')
        end_index = text.find('}', start_index)
        if end_index == -1: break
        options = text[start_index+1:end_index].split('|')
        text = text[:start_index] + random.choice(options) + text[end_index+1:]
    return text

def take_screenshot(driver, error_type="general_error"):
    """Mengambil screenshot dengan nama file yang unik."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"debug_{error_type}_{timestamp}.png"
    try:
        driver.save_screenshot(filename)
        logging.debug(f"Screenshot error disimpan: {filename}")
    except Exception as e:
        logging.error(f"Gagal menyimpan screenshot: {e}")

# --- MODUL 2: FUNGSI INTI OTOMATISASI ---

def setup_driver(config):
    """Menginisialisasi undetected-chromedriver dengan konfigurasi."""
    options = uc.ChromeOptions()
    profile_path = os.path.join(os.getenv('TEMP'), 'my_uc_chrome_profile')
    options.add_argument(f'--user-data-dir={profile_path}')
    options.add_argument("--start-maximized")
    
    if config['settings'].get('run_headless', False):
        logging.info("Menjalankan dalam mode Headless.")
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')

    logging.info(f"Menggunakan direktori profil: {profile_path}")
    driver = uc.Chrome(options=options, use_subprocess=True)
    logging.info("Undetected-Chromedriver berhasil diinisialisasi.")
    return driver

def login_to_x(driver, creds):
    """Fungsi login yang dirombak untuk menangani verifikasi secara otomatis."""
    username = creds['username']
    password = creds['password']
    email_for_verification = creds.get('email')

    try:
        driver.get("https://x.com/home")
        time.sleep(3)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-testid='SideNav_NewTweet_Button']")))
        logging.info("Sesi login sebelumnya ditemukan. Melewati proses login.")
        return True
    except TimeoutException:
        logging.info("Sesi login tidak ditemukan atau kedaluwarsa. Memulai proses login penuh.")

    driver.get("https://x.com/i/flow/login")
    try:
        username_input = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']")))
        username_input.send_keys(username)
        username_input.send_keys(Keys.RETURN)
        logging.info("Username dimasukkan.")
        
        time.sleep(random.uniform(2, 4))
        
        try:
            password_input = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='password']")))
            logging.info("Kolom password ditemukan, melanjutkan...")
        except TimeoutException:
            logging.warning("Kolom password tidak ditemukan. Memulai proses verifikasi otomatis.")
            if not email_for_verification:
                logging.error("Halaman verifikasi terdeteksi, tetapi tidak ada 'email' di credentials.txt.")
                return False
            
            verification_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[data-testid='ocfEnterTextTextInput']")))
            logging.info("Memasukkan email untuk verifikasi...")
            verification_input.send_keys(email_for_verification)
            verification_input.send_keys(Keys.RETURN)
            logging.info("Email verifikasi dimasukkan dan ENTER ditekan.")
            
            password_input = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='password']")))
            logging.info("Verifikasi otomatis berhasil! Kolom password sekarang terlihat.")

        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        logging.info("Password dimasukkan.")

        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-testid='SideNav_NewTweet_Button']")))
        logging.info("Login berhasil dikonfirmasi, timeline telah dimuat.")
        return True

    except Exception as e:
        logging.error(f"Gagal pada proses login: {e}")
        take_screenshot(driver, "login_error")
        return False

def post_reply(driver, tweet_url, reply_text):
    """Fungsi balas yang dirombak dengan metode CTRL+ENTER."""
    logging.info(f"Mencoba membalas tweet: {tweet_url}")
    driver.get(tweet_url)
    
    try:
        reply_area_selector = "div[data-testid='tweetTextarea_0']"
        reply_area = WebDriverWait(driver, 25).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, reply_area_selector))
        )
        logging.info("Area balas utama ditemukan.")
        
        reply_area.click()
        time.sleep(random.uniform(0.5, 1.5))
        
        logging.info(f"Mengetik pesan: \"{reply_text}\"")
        for char in reply_text:
            reply_area.send_keys(char)
            time.sleep(random.uniform(0.04, 0.12))

        logging.info("Mengirim balasan dengan shortcut CTRL+ENTER...")
        reply_area.send_keys(Keys.CONTROL, Keys.ENTER)
        
        time.sleep(random.uniform(5, 7))
        
        logging.info(f"Berhasil mengirim balasan untuk: {tweet_url}")
        return True

    except Exception as e:
        logging.error(f"Gagal membalas tweet {tweet_url}")
        logging.error(traceback.format_exc())
        take_screenshot(driver, "reply_error")
        return False

# --- MODUL 3: LOGIKA UTAMA BOT ---
def search_for_tweets(driver, query):
    """Mencari tweet berdasarkan query dan mendarat di tab Populer."""
    logging.info(f"Mencari dengan query: '{query}'")
    encoded_query = query.replace('#', '%23').replace(' ', '%20')
    search_url = f"https://x.com/search?q={encoded_query}&src=typed_query"
    driver.get(search_url)
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']")))
        logging.info(f"Halaman hasil pencarian untuk '{query}' berhasil dimuat (Tab Populer).")
        return True
    except TimeoutException:
        logging.warning(f"Tidak ada hasil ditemukan atau halaman gagal dimuat untuk '{query}'.")
        return False

def scrape_and_filter_tweets(driver, config):
    """
    Menggulir halaman dan mengumpulkan URL valid dengan logika filter "Niat + Layanan".
    """
    logging.info("Mulai scraping & filtering...")
    valid_tweet_urls = set()
    processed_urls = set()
    
    for _ in range(10): # Lakukan scroll maksimal 10 kali
        time.sleep(random.uniform(2, 3.5))
        
        tweets = driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
        if not tweets:
            break
            
        new_tweets_found_on_scroll = False
        for tweet in tweets:
            try:
                links = tweet.find_elements(By.CSS_SELECTOR, "a[href*='/status/']")
                tweet_url = ""
                for link in links:
                    href = link.get_attribute('href')
                    if '/status/' in href and '/photo/' not in href and '/video/' not in href:
                        tweet_url = href.split('/analytics')[0]
                        break
                
                if not tweet_url or tweet_url in processed_urls:
                    continue
                
                processed_urls.add(tweet_url)
                new_tweets_found_on_scroll = True

                timestamp_element = tweet.find_element(By.TAG_NAME, "time")
                datetime_str = timestamp_element.get_attribute("datetime")
                tweet_dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                tweet_age = datetime.now(timezone.utc) - tweet_dt
                
                if tweet_age.days > config['settings']['max_tweet_age_days']:
                    continue

                tweet_text = tweet.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']").text.lower()
                username = tweet.find_element(By.CSS_SELECTOR, "div[data-testid='User-Name']").text.lower()
                
                # --- LOGIKA FILTER DUA LAPIS ---
                has_intent = any(keyword in tweet_text for keyword in config['intent_keywords'])
                has_service = any(keyword in tweet_text for keyword in config['service_keywords'])
                is_promo = any(keyword in tweet_text for keyword in config['promo_keywords_to_avoid'])
                is_joki_username = any(keyword in username for keyword in config['username_keywords_to_avoid'])

                if is_joki_username or is_promo:
                    continue
                
                if has_intent and has_service:
                    logging.info(f"Lolos filter: {tweet_url}")
                    valid_tweet_urls.add(tweet_url)

            except Exception:
                continue
        
        if not new_tweets_found_on_scroll:
            logging.info("Tidak ada tweet baru ditemukan pada scroll ini, berhenti.")
            break
            
        driver.execute_script("window.scrollBy(0, 1500);")
    
    logging.info(f"Selesai scraping. Ditemukan {len(valid_tweet_urls)} tweet yang valid.")
    return list(valid_tweet_urls)

def check_if_already_replied(driver, tweet_url, my_username):
    """Membuka URL tweet di tab baru dan memeriksa balasan."""
    logging.info(f"Memeriksa apakah '{my_username}' sudah membalas: {tweet_url}")
    original_window = driver.current_window_handle
    try:
        driver.switch_to.new_window('tab')
        driver.get(tweet_url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']")))
        time.sleep(2) 
        
        all_usernames = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='User-Name'] a[role='link']")
        for user in all_usernames:
            if f"@{my_username.lower()}" in user.text.lower():
                logging.warning(f"Ditemukan balasan sebelumnya dari '{my_username}'. Melewati.")
                driver.close()
                driver.switch_to.window(original_window)
                return True
                
        logging.info("Tidak ada balasan sebelumnya yang ditemukan.")
        driver.close()
        driver.switch_to.window(original_window)
        return False
    except Exception as e:
        logging.error(f"Error saat memeriksa balasan: {e}")
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(original_window)
        return False

def main():
    """Fungsi utama untuk menjalankan siklus bot."""
    setup_logging()
    cleanup_existing_processes()
    config = load_config()

    creds = get_credentials()
    my_bot_username = creds['username']

    driver = None  
    try:
        driver = setup_driver(config)
        
        if not login_to_x(driver, creds):
            return
        
        replied_tweets = load_replied_tweets()
        all_queries = [f'"{term}"' for term in config['search_terms']] # Gabungkan dengan hashtag nanti di filter
        
        while True: 
            logging.info("MEMULAI SIKLUS PENUH")
            random.shuffle(all_queries)

            for query in all_queries:
                try:
                    if not search_for_tweets(driver, query):
                        time.sleep(random.uniform(config['sleep_timers']['between_queries_min'], config['sleep_timers']['between_queries_max']))
                        continue
                    
                    target_urls = scrape_and_filter_tweets(driver, config)
                    
                    if not target_urls:
                        logging.info("Tidak ada tweet baru yang valid ditemukan untuk query ini.")
                        continue
                    
                    for url in target_urls:
                        tweet_id = get_tweet_id_from_url(url)
                        if not tweet_id or tweet_id in replied_tweets:
                            continue

                        if check_if_already_replied(driver, url, my_bot_username):
                            save_replied_tweet('replied_tweets.txt', tweet_id)
                            replied_tweets.add(tweet_id)
                            continue

                        logging.info(f"Memproses target baru yang valid: {url}")
                        
                        base_reply = spin(config['reply_template']['base'])
                        detail_reply = spin(random.choice(config['reply_template']['details']))
                        chosen_cta = random.choice(config['reply_template']['cta_options'])
                        final_reply = f"{base_reply} {detail_reply} {chosen_cta}"
                        
                        save_replied_tweet('replied_tweets.txt', tweet_id)
                        replied_tweets.add(tweet_id)
                        logging.info(f"Tweet ID {tweet_id} telah dicatat untuk menghindari duplikasi.")

                        if post_reply(driver, url, final_reply):
                            sleep_duration = random.uniform(config['sleep_timers']['after_reply_min'], config['sleep_timers']['after_reply_max'])
                            logging.info(f"Balasan berhasil. Tidur selama {sleep_duration:.2f} detik...")
                            time.sleep(sleep_duration)
                        else:
                            logging.warning("Balasan gagal, melanjutkan ke target berikutnya.")

                except Exception as e:
                    logging.error(f"Terjadi error saat memproses query '{query}': {e}")
                    logging.error(traceback.format_exc())
                    continue
            
            cycle_sleep_min = config['sleep_timers']['after_full_cycle_min']
            cycle_sleep_max = config['sleep_timers']['after_full_cycle_max']
            cycle_sleep = random.uniform(cycle_sleep_min, cycle_sleep_max)
            logging.info(f"Siklus penuh selesai. Tidur selama {cycle_sleep:.2f} detik...")
            time.sleep(cycle_sleep)

    except KeyboardInterrupt:
        logging.info("Bot dihentikan oleh pengguna.")
    except Exception as e:
        logging.error(f"Terjadi error fatal yang menghentikan bot: {e}")
        if driver:
            take_screenshot(driver, "fatal_error")
        logging.error(traceback.format_exc())
    finally:
        if driver:
            logging.info("Menutup browser Chrome...")
            driver.quit()

if __name__ == "__main__":
    main()