import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from azure_keyvault import get_secret_from_key_vault

def send_sms_via_email(config, subject, body):
    """
    Sends an SMS via email using the provided configuration.
    Args:
        config (dict): A dictionary containing the configuration settings.
        subject (str): The subject of the email.
        body (str): The body of the email.
    Raises:
        KeyError: If any required configuration setting is missing.
    """
    keyvault_url = config['keyvault_url']
    
    smtp_user = get_secret_from_key_vault(keyvault_url, config['email']['smtp_user_secret'])
    smtp_password = get_secret_from_key_vault(keyvault_url, config['email']['smtp_password_secret'])
    phone_numbers = config['email']['phone_numbers']
    carrier_gateway = config['email']['carrier_gateway']
    smtp_server = config['email']['smtp_server']
    smtp_port = config['email']['smtp_port']
    
    for phone_number in phone_numbers:
        recipient_email = f"{phone_number}@{carrier_gateway}"
        
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient_email, msg.as_string())
