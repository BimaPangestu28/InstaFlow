from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import random
import os
import pickle
from dotenv import load_dotenv

load_dotenv()

class InstagramBot:
    def __init__(self, username=None, password=None):
        self.username = username or os.getenv('INSTAGRAM_USERNAME')
        self.password = password or os.getenv('INSTAGRAM_PASSWORD')
        
        self.chrome_options = Options()
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.cookies_path = f'cookies/{self.username}_cookies.pkl'
        
        self.driver = self.setup_driver()

    def setup_driver(self):
        driver = webdriver.Chrome(options=self.chrome_options)
        
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        return driver

    def save_cookies(self):
        try:
            pickle.dump(self.driver.get_cookies(), open(self.cookies_path, 'wb'))
            print("Cookies berhasil disimpan.")
        except Exception as e:
            print(f"Gagal menyimpan cookies: {e}")

    def load_cookies(self):
        try:
            if os.path.exists(self.cookies_path):
                cookies = pickle.load(open(self.cookies_path, 'rb'))
                
                self.driver.get('https://www.instagram.com/')
                
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as cookie_error:
                        print(f"Gagal menambahkan cookie: {cookie_error}")
                
                self.driver.refresh()
                print("Cookies berhasil dimuat.")
                return True
            else:
                print("File cookies tidak ditemukan.")
                return False
        except Exception as e:
            print(f"Gagal memuat cookies: {e}")
            return False

    def login(self):
        try:
            if self.load_cookies():
                time.sleep(3)
                try:
                    self.driver.find_element(By.XPATH, "//a[contains(@href, '/direct/inbox/')]")
                    print("Login dengan cookies berhasil!")
                    return True
                except:
                    pass
            
            self.driver.get('https://www.instagram.com/accounts/login/')
            
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, 'username'))
            )
            
            username_input.send_keys(self.username)
            
            password_input = self.driver.find_element(By.NAME, 'password')
            password_input.send_keys(self.password)
            
            password_input.send_keys(Keys.RETURN)
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/direct/inbox/')]"))
            )
            
            self.save_cookies()
            
            print("Login berhasil!")
            return True
        
        except Exception as e:
            print(f"Gagal login: {e}")
            return False

    def follow_user(self, username):
        try:
            self.driver.get(f'https://www.instagram.com/{username}/')
            
            follow_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Follow')]"))
            )
            
            follow_button.click()
            
            time.sleep(random.uniform(2, 5))
            
            print(f"Berhasil follow @{username}")
            return True
        
        except Exception as e:
            print(f"Gagal follow @{username}: {e}")
            return False

    def explore_hashtag(self, hashtag):
        try:
            self.driver.get(f'https://www.instagram.com/explore/search/keyword/?q=%23{hashtag}')
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//article"))
            )
            
            print(f"Berhasil membuka halaman hashtag #{hashtag}")
            return True
        
        except Exception as e:
            print(f"Gagal membuka hashtag #{hashtag}: {e}")
            return False

    def close(self):
        self.driver.quit()

def main():
    try:
        bot = InstagramBot()
        
        if bot.login():
            bot.follow_user('hibimbim')
            bot.explore_hashtag('techlover')
    
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
    
    finally:
        bot.close()

if __name__ == "__main__":
    main()