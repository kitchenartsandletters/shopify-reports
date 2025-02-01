import time
import logging
import random
from functools import wraps

import shopify

class ShopifyRateLimiter:
    """
    Custom rate limiter for Shopify API calls
    """
    def __init__(self, max_calls=2, per_seconds=1, max_retries=5):
        """
        Initialize rate limiter
        
        Args:
            max_calls (int): Maximum number of calls allowed
            per_seconds (int): Time window for calls
            max_retries (int): Maximum number of retry attempts
        """
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self.max_retries = max_retries
        self.calls = []
    
    def __call__(self, func):
        """
        Decorator to apply rate limiting to a function
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Implement rate limiting
            for attempt in range(self.max_retries):
                # Remove old calls outside the time window
                current_time = time.time()
                self.calls = [call for call in self.calls if current_time - call < self.per_seconds]
                
                # Check if we can make the call
                if len(self.calls) < self.max_calls:
                    # Record this call
                    self.calls.append(current_time)
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        # Log the error
                        logging.warning(f"API call attempt {attempt + 1} failed: {e}")
                        
                        # If it's a rate limit error, wait and retry
                        if 'Exceeded' in str(e) or '429' in str(e):
                            # Exponential backoff with jitter
                            wait_time = (2 ** attempt) + random.random()
                            logging.warning(f"Rate limit hit. Waiting {wait_time:.2f} seconds")
                            time.sleep(wait_time)
                            continue
                        
                        # For other errors, re-raise
                        raise
                
                # If too many calls, wait
                wait_time = self.per_seconds + random.random()
                logging.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
            
            # If all retries fail
            raise Exception("Max retries exceeded for API call")
        
        return wrapper

def get_product_details(product_id):
    """
    Retrieve detailed information for a specific product with rate limiting
    
    Args:
        product_id (int or None): Shopify product ID
    
    Returns:
        dict: Product details including collection and online store availability
    """
    # Skip invalid product IDs
    if product_id is None:
        logging.warning(f"Skipping product details: None product ID")
        return {
            'collection': 'Uncategorized',
            'online_store': 'No',
            'current_quantity': 0
        }

    @ShopifyRateLimiter(max_calls=2, per_seconds=1, max_retries=3)
    def _fetch_product_details():
        """
        Inner function to fetch product details with rate limiting
        """
        try:
            # Fetch product
            product = shopify.Product.find(product_id)
            
            # Verify product exists and has variants
            if not hasattr(product, 'variants') or not product.variants:
                logging.warning(f"Product {product_id} has no variants")
                return {
                    'collection': 'Uncategorized',
                    'online_store': 'No',
                    'current_quantity': 0
                }
            
            # Determine collection with error handling
            try:
                collections = product.collections()
                collection = collections[0].title if collections else 'Uncategorized'
            except Exception:
                logging.warning(f"Could not fetch collections for product {product_id}")
                collection = 'Uncategorized'
            
            # Check online store availability and inventory
            online_store_available = 'No'
            current_quantity = 0
            
            for variant in product.variants:
                # Check if variant has inventory tracking
                if hasattr(variant, 'inventory_quantity') and variant.inventory_quantity is not None:
                    current_quantity += variant.inventory_quantity
                    
                    # Mark as available if any variant has positive inventory
                    if variant.inventory_quantity > 0:
                        online_store_available = 'Yes'
            
            return {
                'collection': collection,
                'online_store': online_store_available,
                'current_quantity': current_quantity
            }
        
        except Exception as e:
            logging.warning(f"Could not fetch details for product {product_id}: {e}")
            return {
                'collection': 'Uncategorized',
                'online_store': 'No',
                'current_quantity': 0
            }

    return _fetch_product_details()