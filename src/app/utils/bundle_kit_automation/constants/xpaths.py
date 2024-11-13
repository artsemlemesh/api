# Xpaths for the login page
LOGIN_USERNAME_INPUT = "//input[@id='username']"
LOGIN_PASSWORD_INPUT = "//input[@id='password']"
LOGIN_SUBMIT_BUTTON = "//button[@id='btn-submit']"

# Xpaths for the cart page
VIEW_CART_LINK = "//div[@id='link-cart']//a[@href]"
CLEAR_CART_BUTTON = "//*[@id='clearCart']"
GOTO_CHECKOUT_BUTTON = "//div[@class='button-container']//input[@id='atg_store_checkout']"

# Xpaths for the item page
SELECT_ITEM_BUTTON = "//div[@class='button-container item-size stamp-box-size']\
                        //a[@class='btn-primary button--white active']//span[@class='price-btn-label']"
ADD_ITEM_TO_CART_BUTTON = "//div[contains(@class, 'check-out-process-btn')]//div[@class='button-container']\
                            //a[@class='button--primary button--green button--cart add-to-cart']"

# Xpaths for shipping page
SHIPPING_METHOD_RADIO = "//div[contains(@class, 'eps-shipping-options')]//input[@id='normal-shipping']"
CONFIRM_SHIPPING_BUTTON = "//div[contains(@class, 'adr-shipping-btn button-wrapper')]\
                            //a[@class='input-btn-primary confirm-order-btn']"
NEW_ADDRESS_BUTTON = "//div[contains(@class, 'create-shipping-address-tab-wrapper')]\
                        //a[contains(@class, 'create-shipping-address-tab')]"
SHIP_TO_ADDRESS_BUTTON = "//div[@class='button-container']//a[@class='btn-primary ship-to-this-address-btn']/span"
SHIPMENT_NICKNAME_INPUT = "//input[@id='atg_store_nickNameInput']"
SHIPMENT_FNAME_INPUT = "//input[@id='atg_store_firstNameInput']"
SHIPMENT_LNAME_INPUT = "//input[@id='atg_store_lastNameInput']"
SHIPMENT_ADD1_INPUT = "//input[@id='atg_store_streetAddressInput']"
SHIPMENT_ADD2_INPUT = "//input[@id='atg_store_streetAddressOptionalInput']"
SHIPMENT_CITY_INPUT = "//input[@id='atg_store_localityInput']"
SHIPMENT_STATE_SELECT = "//select[@id='atg_store_stateSelect']"
SHIPMENT_ZIP_INPUT = "//input[@id='atg_store_postalCodeInput']"
SHIPMENT_COUNTRY_SELECT = "//select[@id='atg_store_countryNameSelect']"
SHIPMENT_EMAIL_INPUT = "//input[@id='atg_store_emailInput']"
SHIPMENT_PHONE_INPUT = "//input[@id='atg_store_telephoneInput']"

CONFIRM_ORDER_BUTTON = "//input[@id='placeMyOrderBtn']"

# Xpaths for terms and conditions modal
AGREE_TERMS_BUTTON = "//div[@class='modal-body']//input[@id='agree']"

# Xpaths for getting order details
ORDER_NUMBER = "//div[contains(@class, 'confirmation-success')]//a[@href]"
ORDER_EMAIL = "//div[contains(@class, 'confirmation-success')]//span[@class='user-email']"
ORDER_ADDRESS = "//div[@class='shpping-adr']"
