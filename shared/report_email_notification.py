import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

def send_report_email(report_file):
    """
    Send an email with the generated report as an attachment.
    
    Args:
        report_file (str): Path to the report CSV file
    """
    # Load environment variables
    load_dotenv()

    # Email configuration from environment variables
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')
    recipient_email = os.getenv('RECIPIENT_EMAIL')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))

    # Validate email settings
    if not all([sender_email, sender_password, recipient_email]):
        print("Email configuration incomplete. Skipping email notification.")
        return

    try:
        # Create message
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = f"Daily Shopify Sales Report - {os.path.basename(report_file)}"

        # Email body
        body = "Please find attached the daily Shopify sales report."
        message.attach(MIMEText(body, 'plain'))

        # Attach report file
        with open(report_file, 'rb') as file:
            part = MIMEApplication(file.read(), Name=os.path.basename(report_file))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(report_file)}"'
            message.attach(part)

        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)

        print("Report email sent successfully")

    except Exception as e:
        print(f"Failed to send email: {e}")