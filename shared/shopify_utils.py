import os
import requests
import time
import logging

class ShopifyAPI:
    def __init__(self):
        self.shop_url = os.getenv('SHOP_URL')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.graphql_url = f"https://{self.shop_url}/admin/api/2025-01/graphql.json"
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }

    def run_query(self, query, variables=None, max_retries=3, delay=1):
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.graphql_url,
                    json={'query': query, 'variables': variables},
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    logging.error(f"Status code {response.status_code}: {response.text}")
                    raise Exception(f"Query failed with status {response.status_code}")
                    
                data = response.json()
                if 'errors' in data:
                    raise Exception(f"GraphQL errors: {data['errors']}")
                    
                return data['data']
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay)
                
    def paginated_query(self, query, page_size=250):
        """Execute a paginated GraphQL query and return all results"""
        results = []
        has_next_page = True
        cursor = None
        
        while has_next_page:
            variables = {
                "first": page_size,
                "after": cursor
            }
            
            data = self.execute_query(query, variables)
            page_info = list(data.values())[0]['pageInfo']  # Works with any root field
            edges = list(data.values())[0]['edges']
            
            results.extend(edge['node'] for edge in edges)
            
            has_next_page = page_info['hasNextPage']
            if has_next_page:
                cursor = edges[-1]['cursor']
                
        return results