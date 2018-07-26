#!/usr/bin/env python3

import config
import bs4
import re
import pandas as pd
import sys

from urllib.parse import urljoin, urlencode
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

BASE_URL = 'https://wwwsc.ekeystone.com'
ZIP_CODE = '99501'

def config_cookies(driver):
    cookie = { 'name': 'AccessoriesSearchResultsPageSize', 'value': '48' }
    driver.add_cookie(cookie)

def login(driver):

    if config.KEYSTONE_USER is None \
    or config.KEYSTONE_PASS is None:
        raise Exception('Set credentials!')

    driver.get('https://wwwsc.ekeystone.com/login')

    username = driver.find_element_by_id('webcontent_0_txtUserName')
    password = driver.find_element_by_id('webcontent_0_txtPassword')

    username.send_keys(config.KEYSTONE_USER)
    password.send_keys(config.KEYSTONE_PASS)

    submit = driver.find_element_by_id('webcontent_0_submit')
    submit.click()

    config_cookies(driver)
    return driver.get_cookies()

def wait_for_elem_id(driver, id_):

    event = EC.element_to_be_clickable((By.ID, id_))
    wait = WebDriverWait(driver, 10)
    elem = wait.until(event)
    return elem

def add_product(driver, pid):

    url  = urljoin(BASE_URL, '/Search/Detail') 
    url += '?pid={}'.format(pid)
    print(url)

    # Go to product page in ekeystone
    print('Loading product page...')
    driver.get(url) 

    # Wait to button to be present
    try:
        id_  = 'webcontent_0_row2_0_productDetail'
        id_ += 'BasicInfo_addToOrder_lbAddToOrder'
        elem = wait_for_elem_id(driver, id_)

    except TimeoutException as e:
        print(e)
        return
    
    # Clicking "Add to Cart" button
    print('Adding to cart', pid)
    elem.click()

    return url

    # Executing javascript
    # target  = 'webcontent_0$row2_0$productDetailBasicInfo$'
    # target += 'addToOrder$lbAddToOrder'
    # script = "__doPostBack({}, '')".format(target)
    # print(script)
    # driver.execute_script(script)

def clear_cart(driver):

    url = urljoin(BASE_URL, '/MyCart')
    driver.get(url)

def wait_for_progress(driver, timeout=600):

    id_ = 'webcontent_0_row2_0_upCheckoutProgress'
    event = EC.visibility_of_element_located((By.ID, id_))

    try:
        wait = WebDriverWait(driver, 30)
        wait.until(event)
    except TimeoutException:
        pass

    wait = WebDriverWait(driver, timeout)
    wait.until_not(event)

    driver.implicitly_wait(0.5)

def parse_shipping(soup):

    # Extract options for each product
    options = []
    pids = []

    for tb in soup.select('.checkoutShippingOptionsGrid > table'):
        opt = [ l.get_text() for l in tb.select('td label') ]
        options.append(opt)

    for a in soup.select('.checkoutPartGrid .checkoutPrimaryPartId a'):
        href  = a.get('href')
        match = re.search(r'pid\=(.+)', href)
        pid = match.group(1)
        pids.append(pid)

    return { p: opt for p, opt in zip(pids, options) }

def calculate_shipping(driver: webdriver.Chrome):

    url = urljoin(BASE_URL, '/Checkout')
    print('Loading checkout page')
    driver.get(url)

    try:
        # Test if page is really checkout page
        if driver.current_url != url:

            print('Redirected!', driver.current_url)
            id_ = 'webcontent_0_row2_0_lbCheckout'
            elem = wait_for_elem_id(driver, id_)
            elem.click()

        id_ = 'webcontent_0_row2_0_dropShipPostalCode'
        elem = wait_for_elem_id(driver, id_)
        elem.clear()
        elem.send_keys(ZIP_CODE)
        
        id_ = 'webcontent_0_row2_0_lbCalculateShipping'
        elem = wait_for_elem_id(driver, id_)

        # Avoid to click the calculate button
        script = "__doPostBack('webcontent_0$row2_0$lbCalculateShipping','')"
        driver.execute_script(script)

        # Wait page to calculate
        wait_for_progress(driver)

    except TimeoutException as e:
        print('TimeoutException!:', id_) 
        return

    # Scrape data here...
    html = driver.page_source
    soup = bs4.BeautifulSoup(html, 'html.parser')
    data = parse_shipping(soup)

    return data

def add_batch(driver, batch):

    for p in batch:
        add_product(driver, p)

def main():

    if len(sys.argv) != 2:
        print('Usage: ./eKeystone_cart.py [FILENAME]')
        return

    filename = sys.argv[1]
    df = pd.read_csv(filename)

    driver = webdriver.Chrome()
    # '--disable-dev-profile'

    # Login to eKeystone
    login(driver) 

    # Add product to cart
    # add_product(driver, 'MTH08612')

    pids = df.pid[:5]
    add_batch(driver, pids)

    data = calculate_shipping(driver)
    print(data)

    input()

if __name__ == '__main__':
    main()
