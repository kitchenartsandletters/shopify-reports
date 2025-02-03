import os

# Report recipient configurations
INVENTORY_REPORT_RECIPIENTS = [
    "gil@kitchenartsandletters.com"
]

# Validation thresholds
PRODUCT_VALIDATION = {
    'min_images': 1,
    'min_description_length': 100,
    'min_price': 0.01,
    'required_collections': {'All Books'},
    'required_metafields': {
        'isbn': 'ISBN number',
        'author': 'Author name',
        'publisher': 'Publisher name',
        'publication_date': 'Publication date'
    }
}

# Report schedules (UTC times)
SCHEDULE_CONFIG = {
    "inventory": "0 14 * * 1",  # Monday at 10am ET (14:00 UTC)
    "sales": "0 15 * * 1"      # Weekly on Monday at 3pm
}