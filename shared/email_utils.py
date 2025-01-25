# shared/email_utils.py

import os
import base64
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

def send_report_email(
    subject,
    content,
    attachments,
    start_date=None,
    end_date=None,
):
    """
    Generic function to send report emails via SendGrid
    
    Args:
        subject (str): Email subject line
        content (str): Email body content
        attachments (list): List of dicts with keys 'path' and 'filename'
        start_date (str, optional): Report start date
        end_date (str, optional): Report end date
    """
    api_key = os.getenv('SENDGRID_API_KEY')
    sender_email = os.getenv('EMAIL_SENDER')
    recipient_emails = os.getenv('EMAIL_RECIPIENTS').split(',')

    if not all([api_key, sender_email, recipient_emails]):
        logging.error("Missing email configuration.")
        return False

    # Add date range to subject if provided
    if start_date and end_date:
        subject = f"{subject} ({start_date} to {end_date})"

    message = Mail(
        from_email=sender_email,
        to_emails=recipient_emails,
        subject=subject,
        plain_text_content=content
    )

    # Attach files
    for attachment_info in attachments:
        try:
            with open(attachment_info['path'], 'rb') as f:
                data = f.read()
                encoded_file = base64.b64encode(data).decode()
                
                attachment = Attachment(
                    FileContent(encoded_file),
                    FileName(attachment_info['filename']),
                    FileType('text/csv'),
                    Disposition('attachment')
                )
                message.add_attachment(attachment)
        except Exception as e:
            logging.error(f"Error attaching file {attachment_info['filename']}: {e}")
            return False

    # Send email
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logging.info(f"Email sent! Status: {response.status_code}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False