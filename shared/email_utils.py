import os
import sendgrid
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64
import logging

class EmailClient:
    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY')
        self.sender = os.getenv('EMAIL_SENDER')
        self.client = sendgrid.SendGridAPIClient(self.api_key)
        
    def send_report(self, subject, content, recipient_list, attachments=None):
        if isinstance(recipient_list, str):
            recipient_list = recipient_list.split(',')
            
        message = Mail(
            from_email=self.sender,
            to_emails=recipient_list,
            subject=subject,
            plain_text_content=content
        )
        
        if attachments:
            for filename, file_path in attachments.items():
                with open(file_path, 'rb') as f:
                    data = base64.b64encode(f.read()).decode()
                    attachment = Attachment(
                        FileContent(data),
                        FileName(filename),
                        FileType('text/csv'),
                        Disposition('attachment')
                    )
                    message.add_attachment(attachment)
                    
        try:
            response = self.client.send(message)
            logging.info(f"Email sent with status code: {response.status_code}")
            return True
        except Exception as e:
            logging.error(f"Failed to send email: {e}")
            return False