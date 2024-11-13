import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select

from .constants.links import LOGIN_URL, CART_URL, PACKAGES
from .constants.xpaths import *

options = Options()
# arguments for running headless
options.add_argument('--headless')
options.add_argument(
    'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
    AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36')

# arguments for page crash when running automation in docker
options.add_argument('--no-sandbox')
options.add_argument('--disable-setuid-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument("--start-maximized")
options.add_argument('--window-size=1680,1050')


class KitAutomation:
    def __init__(self, username, password) -> None:
        print('Initializing Chrome driver')
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        self.username = username
        self.password = password

    def login(self):
        print('Logging in to USPS')
        username = self.username
        password = self.password
        if not username and password:
            print('No username or password provided')
            raise Exception('No username or password provided')
        self.driver.get(LOGIN_URL)
        time.sleep(1)
        self._fill_form(LOGIN_USERNAME_INPUT, username)
        self._fill_form(LOGIN_PASSWORD_INPUT, password)
        self.driver.find_element("xpath", LOGIN_SUBMIT_BUTTON).click()
        time.sleep(1)

    def clear_cart(self):
        print('Clearing cart')
        self.driver.get(CART_URL)
        time.sleep(2)
        try:
            self.driver.find_element("xpath", CLEAR_CART_BUTTON).click()
        except Exception as e:
            print(e)

    def add_to_cart(self, item: str):
        print(f'Adding {item} to cart')
        self.driver.get(item)
        time.sleep(1)
        self.driver.find_element("xpath", SELECT_ITEM_BUTTON).click()
        self.driver.find_element("xpath", ADD_ITEM_TO_CART_BUTTON).click()

    def checkout(self):
        print('Checking out')
        self.driver.get(CART_URL)
        time.sleep(1)
        self.driver.find_element("xpath", GOTO_CHECKOUT_BUTTON).click()

    def select_shipping_method(self):
        print('Selecting shipping method')
        time.sleep(1)
        try:
            self.driver.find_element("xpath", SHIPPING_METHOD_RADIO).click()
            self.driver.find_element("xpath", CONFIRM_SHIPPING_BUTTON).click()
        except Exception as e:
            print(e)

    def confirm_order(self):
        print('Confirming order')
        time.sleep(1)
        self.driver.find_element("xpath", CONFIRM_ORDER_BUTTON).click()

    def _fill_form(self, match_string: str, value: str):
        input_field = self.driver.find_element("xpath", match_string)
        input_field.clear()
        input_field.send_keys(value)

    def set_shipping_address(self, address: dict):
        print('Setting shipping address')
        self.driver.find_element("xpath", NEW_ADDRESS_BUTTON).click()
        time.sleep(1)
        self._fill_form(SHIPMENT_NICKNAME_INPUT, address['nickname'])
        self._fill_form(SHIPMENT_FNAME_INPUT, address['firstName'])
        self._fill_form(SHIPMENT_LNAME_INPUT, address['lastName'])
        self._fill_form(SHIPMENT_ADD1_INPUT, address['street_address'])

        if address.get('address2') is not None and address['address2'] != '':
            self._fill_form(SHIPMENT_ADD2_INPUT, address['address2'])

        self._fill_form(SHIPMENT_CITY_INPUT, address['city'])
        Select(self.driver.find_element("xpath", SHIPMENT_STATE_SELECT)
               ).select_by_value(address['state'].upper())
        self._fill_form(SHIPMENT_ZIP_INPUT, address['postal_code'])
        Select(self.driver.find_element("xpath", SHIPMENT_COUNTRY_SELECT)
               ).select_by_value(address['country'].upper())
        self._fill_form(SHIPMENT_PHONE_INPUT, address['phone'])
        self._fill_form(SHIPMENT_EMAIL_INPUT, address['email'])
        self.driver.find_element("xpath", SHIP_TO_ADDRESS_BUTTON).click()

    def agree_terms_and_conditions(self):
        print('Agreeing terms and conditions')
        time.sleep(1)
        self.driver.find_element("xpath", AGREE_TERMS_BUTTON).click()

    def reset(self):
        print('Resetting')
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)

    def get_order_details(self):
        print('Getting order details')
        try:
            order_number = self.driver.find_element("xpath", ORDER_NUMBER).text
            email = self.driver.find_element(
                "xpath", ORDER_EMAIL).text.rstrip('.')
            shipping_adr = self.driver.find_element(
                "xpath", ORDER_ADDRESS).find_elements("tag name", value='p')
            name = shipping_adr[1].text
            address = [p.text for p in shipping_adr[3:]]
            return {'order_number': order_number, 'email': email, 'name': name, 'address': address}
        except Exception as e:
            print(e)
        return None

    def send_bundle_kits(self, address: dict, package_names: list):
        if len(package_names) == 0:
            return {'success': False, 'details': 'No packages to send', 'package_names': package_names}
        try:
            self.login()
            self.clear_cart()
            for name in package_names:
                self.add_to_cart(PACKAGES[name])
            self.checkout()
            self.set_shipping_address(address)
            self.select_shipping_method()
            self.confirm_order()
            self.agree_terms_and_conditions()
            details = self.get_order_details()
            return {'success': True, 'details': details, 'package_names': package_names}
        except Exception as e:
            return {'success': False, 'details': str(e), 'package_names': package_names}
