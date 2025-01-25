# shared/shopify_utils.py

import os
import logging
import requests
import time

class ShopifyAPI:
    def __init__(self):
        self.shop_url = os.getenv('SHOP_URL')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        
        if not all([self.shop_url, self.access_token]):
            raise ValueError("Missing Shopify configuration")
            
        self.graphql_url = f"https://{self.shop_url}/admin/api/2025-01/graphql.json"
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }

    def run_query_with_retries(self, query, variables, max_retries=3, delay=1):
        """
        Executes a GraphQL query with retry logic
        """
        attempt = 0
        while attempt < max_retries:
            try:
                response = requests.post(
                    self.graphql_url,
                    json={'query': query, 'variables': variables},
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    logging.error(f"Error: Received status code {response.status_code}")
                    logging.error(f"Response: {response.text}")
                    attempt += 1
                    time.sleep(delay)
                    continue
                    
                data = response.json()
                
                if 'errors' in data:
                    logging.error(f"GraphQL Errors: {data['errors']}")
                    attempt += 1
                    time.sleep(delay)
                    continue
                    
                return data['data']
                
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed: {e}")
                attempt += 1
                time.sleep(delay)
                
        raise Exception(f"Failed to execute query after {max_retries} attempts")

    def fetch_orders(self, start_date, end_date):
        """
        Fetches all orders within the specified date range
        """
        orders = []
        has_next_page = True
        cursor = None
        
        query = """
        query($first: Int!, $query: String!, $after: String) {
            orders(first: $first, query: $query, after: $after, reverse: false) {
                edges {
                    cursor
                    node {
                        id
                        name
                        createdAt
                        cancelledAt
                        
                        lineItems(first: 100) {
                            edges {
                                node {
                                    id
                                    name
                                    quantity
                                    variant {
                                        id
                                        barcode
                                    }
                                }
                            }
                        }
                        
                        refunds {
                            id
                            createdAt
                            refundLineItems(first: 100) {
                                edges {
                                    node {
                                        quantity
                                        lineItem {
                                            id
                                            name
                                            variant {
                                                id
                                                barcode
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                }
            }
        }
        """

        variables = {
            "first": 250,
            "query": f'created_at:>="{start_date}" AND created_at:<="{end_date}"',
            "after": cursor
        }

        while has_next_page:
            try:
                data = self.run_query_with_retries(query, variables)
                fetched_orders = data['orders']['edges']
                
                for edge in fetched_orders:
                    orders.append(edge['node'])

                has_next_page = data['orders']['pageInfo']['hasNextPage']
                logging.info(f"Fetched {len(fetched_orders)} orders. Has next page: {has_next_page}")

                if has_next_page:
                    cursor = fetched_orders[-1]['cursor']
                    variables['after'] = cursor
                else:
                    break

            except Exception as e:
                logging.error(f"Failed to fetch orders: {e}")
                break

        logging.info(f"Total orders fetched: {len(orders)}")
        return orders