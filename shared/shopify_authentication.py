import os
import shopify
from dotenv import load_dotenv

def authenticate_shopify():
    """
    Authenticate with Shopify using environment variables.
    
    Returns:
        shopify.Session: Authenticated Shopify session
    """
    # Load environment variables
    load_dotenv()

    # Retrieve Shopify credentials from environment
    shop_url = os.getenv('SHOPIFY_SHOP_URL')
    api_version = os.getenv('SHOPIFY_API_VERSION', '2024-01')
    access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')

    if not all([shop_url, access_token]):
        raise ValueError("Missing Shopify authentication credentials")

    # Configure Shopify session
    session = shopify.Session(shop_url, api_version, access_token)
    
    return session