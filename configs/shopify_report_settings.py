# Shopify Report Configuration Settings

# Shopify API Configuration
SHOPIFY_CONFIG = {
    'api_version': '2024-01',
    'report_timezone': 'UTC'
}

# Sales Report Settings
SALES_REPORT_CONFIG = {
    'include_collections': True,
    'minimum_quantity_threshold': 0,
    'export_formats': ['csv', 'xlsx']
}

# Email Notification Settings
EMAIL_CONFIG = {
    'send_email': True,
    'recipients': [gil@kitchenartsandletters.com],  # Add email addresses
    'subject_template': 'Shopify Sales Report - {date}'
}

# Logging Configuration
LOGGING_CONFIG = {
    'log_level': 'INFO',
    'log_directory': 'logs',
    'max_log_age_days': 30
}