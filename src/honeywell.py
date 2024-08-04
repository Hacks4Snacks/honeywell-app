import requests
from base64 import b64encode
import time
import schedule
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, parse_qs
from alert_email import send_sms_via_email
from azure_keyvault import get_secret_from_key_vault
import json
import logging

# Configure logging to output to the console (STDOUT)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

class HoneywellTemperatureChecker:
    def __init__(self, config_file="config.json"):
        self.config = self.load_config(config_file)
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.client_id = None
        self.client_secret = None
        self.initialize_tokens()

    def load_config(self, config_file):
        with open(config_file, "r") as file:
            return json.load(file)

    def get_authorization_code(self, client_id, username, password):
        """
        Retrieves the authorization code for the Honeywell API.
        This method is highly dependent on the structure of the Honeywell login page and may break if the page structure changes.
        Args:
            client_id (str): The client ID for the Honeywell API.
            username (str): The username for Honeywell account.
            password (str): The password for Honeywell account.
        Returns:
            str: The authorization code.
        Raises:
            Exception: If the authorization code is not found in the redirect URL.
        """
        logging.debug("Getting authorization code")
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        auth_url = f"https://api.honeywellhome.com/oauth2/authorize?response_type=code&client_id={client_id}&redirect_uri={self.config['honeywell']['redirect_uri']}"
        driver.get(auth_url)
        
        time.sleep(2)  # Wait for page load
        driver.find_element(By.NAME, 'username').send_keys(username)
        driver.find_element(By.NAME, 'password').send_keys(password + Keys.RETURN)
        
        time.sleep(5)  # Wait for the allow button to appear
        driver.find_element(By.CLASS_NAME, 'allowButton').click()

        time.sleep(5)  # Wait for device selection page
        devices = driver.find_elements(By.CLASS_NAME, 'flexbox-wrapper-item')
        for device in devices:
            checkbox = device.find_element(By.TAG_NAME, 'input')
            if not checkbox.is_selected():
                device.click()
                time.sleep(1)  # Ensure the checkbox is toggled

        # Click on the "Allow" button to proceed
        driver.find_element(By.CLASS_NAME, 'connect').click()
        
        time.sleep(5)  # Wait for redirection to get the authorization code
        redirect_url = driver.current_url
        driver.quit()
        
        query_params = parse_qs(urlparse(redirect_url).query)
        code = query_params.get('code', [None])[0]
        if not code:
            logging.error("Authorization code not found in redirect URL")
            raise Exception("Authorization code not found in redirect URL")
        return code

    def get_tokens(self, authorization_code, client_id, client_secret):
        auth_header = b64encode(f"{client_id}:{client_secret}".encode()).decode()
        token_response = requests.post(
            self.config['honeywell']['token_url'],
            headers={'Authorization': f'Basic {auth_header}', 'Content-Type': 'application/x-www-form-urlencoded'},
            data={'grant_type': 'authorization_code', 'code': authorization_code, 'redirect_uri': self.config['honeywell']['redirect_uri']}
        )
        tokens = token_response.json()
        return tokens['access_token'], tokens['refresh_token'], float(tokens['expires_in'])

    def refresh_access_token(self, refresh_token, client_id, client_secret):
        auth_header = b64encode(f"{client_id}:{client_secret}".encode()).decode()
        response = requests.post(
            self.config['honeywell']['token_url'],
            headers={'Authorization': f'Basic {auth_header}', 'Content-Type': 'application/x-www-form-urlencoded'},
            data={'grant_type': 'refresh_token', 'refresh_token': refresh_token}
        )
        new_tokens = response.json()
        return new_tokens['access_token'], new_tokens['refresh_token'], float(new_tokens['expires_in'])

    def initialize_tokens(self):
        logging.info("Initializing tokens")
        keyvault_url = self.config['keyvault_url']
        uami_client_id = self.config.get('uami_client_id')
        self.client_id = get_secret_from_key_vault(keyvault_url, self.config['honeywell']['api_key_secret'], uami_client_id)
        self.client_secret = get_secret_from_key_vault(keyvault_url, self.config['honeywell']['client_secret_secret'], uami_client_id)
        username = get_secret_from_key_vault(keyvault_url, self.config['honeywell']['username_secret'], uami_client_id)
        password = get_secret_from_key_vault(keyvault_url, self.config['honeywell']['password_secret'], uami_client_id)

        authorization_code = self.get_authorization_code(self.client_id, username, password)
        self.access_token, self.refresh_token, expires_in = self.get_tokens(authorization_code, self.client_id, self.client_secret)
        self.token_expiry = time.time() + expires_in

    def get_locations(self):
        if time.time() > self.token_expiry:
            self.access_token, self.refresh_token, expires_in = self.refresh_access_token(self.refresh_token, self.client_id, self.client_secret)
            self.token_expiry = time.time() + expires_in
        
        headers = {'Authorization': f'Bearer {self.access_token}', 'Content-Type': 'application/json'}
        url = f'https://api.honeywellhome.com/v2/locations?apikey={self.client_id}'
        response = requests.get(url, headers=headers)
        
        device_temps = []
        
        if response.status_code == 200:
            data = response.json()
            parsed_data = self.parse_location_data(data)
            for device in parsed_data:
                device_name = device['userDefinedDeviceName']
                temp = device['indoorTemperature']
                device_temps.append((device_name, temp))
        else:
            logging.error(f"Failed to get locations: {response.status_code} - {response.text}")
        
        return device_temps

    def parse_location_data(self, data):
        parsed_data = []
        for location in data:
            for device in location['devices']:
                device_info = {
                    'deviceID': device['deviceID'],
                    'userDefinedDeviceName': device['userDefinedDeviceName'],
                    'indoorTemperature': device['indoorTemperature'],
                    'mode': device['changeableValues']['mode']
                }
                parsed_data.append(device_info)
        return parsed_data

    def check_temperature(self, indoor_temperature, device_name):
        if indoor_temperature > self.config['honeywell']['temperature_threshold']:
            subject = f"Alert! High Temp in {device_name}"
            message = f"The temp in {device_name} is {indoor_temperature}°F."
            send_sms_via_email(self.config, subject, message)
            logging.info(f"Sent alert: {subject}")
        else:
            logging.info(f"Temperature in {device_name} is {indoor_temperature}°F, which is below the threshold of {self.config['honeywell']['temperature_threshold']}°F.")

    def run(self):
        logging.info("Honeywell Temperature Checker running")
        device_temps = self.get_locations()
        
        for device_name, indoor_temperature in device_temps:
            self.check_temperature(indoor_temperature, device_name)

if __name__ == "__main__":
    logging.info("Starting Honeywell Temperature Checker")
    try:
        checker = HoneywellTemperatureChecker()
        # Run the check immediately
        checker.run()
        # Schedule the check to run every hour
        schedule.every().hour.do(checker.run)
        while True:
            schedule.run_pending()
            time.sleep(1)
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        raise