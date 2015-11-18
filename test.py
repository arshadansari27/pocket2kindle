from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time


def readystate_complete(d):
    return d.execute_script("return document.readyState") == "complete"


driver = webdriver.Firefox()
driver.get("https://getpocket.com/a")
username_elem = driver.find_element_by_id('feed_id')
username_elem.send_keys('arshadansari27@gmail.com')
password_elem = driver.find_element_by_id('login_password')
password_elem.send_keys('Ethunt137')
password_elem.send_keys(Keys.RETURN)
articles = {}
lists = driver.find_elements(By.XPATH, '//ul[@id="queue"]/li')
time.sleep(10)
for l in lists:
    _id = l.get_attribute('id')
    articles[_id] = l
