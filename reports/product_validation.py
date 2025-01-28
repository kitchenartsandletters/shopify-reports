import sys
import os
import logging
import csv
from datetime import datetime
from typing import Dict, List

from shared.shopify_utils import ShopifyAPI
from shared.validation import ProductValidator, ValidationConfig, ValidationIssue
from shared.email_utils import EmailClient
from configs import report_configs

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def fetch_all_products(limit=20000):
    """Fetches products using GraphQL pagination up to specified limit"""
    api = ShopifyAPI()
    query = """
    query($first: Int!, $after: String) {
        products(
            first: $first, 
            after: $after, 
            query: "status:active AND published_status:published AND -title:OP:*"
        ) {
            edges {
                node {
                    id
                    title
                    status
                    descriptionHtml
                    productCategory {
                        productTaxonomyNode {
                            name
                        }
                    }
                    images(first: 10) {
                        edges {
                            node {
                                id
                                altText
                            }
                        }
                    }
                    tags
                    priceRangeV2 {
                        minVariantPrice {
                            amount
                        }
                    }
                    collections(first: 10) {
                        edges {
                            node {
                                id
                                title
                            }
                        }
                    }
                    metafields(first: 20) {
                        edges {
                            node {
                                namespace
                                key
                                value
                            }
                        }
                    }
                    variants(first: 20) {
                        edges {
                            node {
                                id
                                sku
                                barcode
                                price
                                inventoryItem {
                                    id
                                    inventoryLevels(first: 1) {
                                        edges {
                                            node {
                                                location {
                                                    id
                                                    name
                                                    isFulfillmentService
                                                    fulfillsOnlineOrders
                                                    shipsInventory
                                                    isActive
                                                }
                                            }
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
                endCursor
            }
        }
    }
    """
    
    all_products = []
    page_size = min(250, limit)  # Maximum allowed by Shopify
    has_next_page = True
    cursor = None
    
    while has_next_page and len(all_products) < limit:
        variables = {
            "first": page_size,
            "after": cursor
        }
        
        try:
            data = api.run_query(query, variables)
            products_data = data['products']
            
            # Extract products from edges
            products = [edge['node'] for edge in products_data['edges']]
            remaining = limit - len(all_products)
            products = products[:remaining]  # Only take what we need
            all_products.extend(products)
            
            # Update pagination info
            if len(all_products) >= limit:
                break
                
            page_info = products_data['pageInfo']
            has_next_page = page_info['hasNextPage']
            cursor = page_info['endCursor']
            
            logging.info(f"Fetched {len(products)} products. Total so far: {len(all_products)}")
            
        except Exception as e:
            logging.error(f"Error fetching products: {e}")
            raise
            
    return all_products

def generate_validation_report() -> Dict:
    """
    Fetches all products and generates validation report
    Returns dict of validation results and counts
    """
    logging.info("Starting product validation report generation")
    
    try:
        # Initialize validator
        config = ValidationConfig(
            min_images=1,
            min_description_length=100,
            min_price=0.01
        )
        validator = ProductValidator(config)
        
        # Fetch and validate products
        products = fetch_all_products(limit=20000)
        total_products = len(products)
        logging.info(f"Fetched {total_products} total products")
        
        # Track validation results
        issues_found = {}
        published_count = 0
        
        # Validate each product
        for product in products:
            if product.get('status') == 'ACTIVE':
                published_count += 1
                issues = validator.validate_product(product)
                if issues:
                    issues_found[product['id']] = {
                        'title': product['title'],
                        'issues': issues
                    }
        
        logging.info(f"Validated {published_count} published products")
        logging.info(f"Found issues in {len(issues_found)} products")
        
        return {
            'issues': issues_found,
            'total_products': published_count,
            'issues_count': len(issues_found)
        }
        
    except Exception as e:
        logging.error(f"Error generating validation report: {e}")
        raise

def generate_csv_report(issues_found: Dict) -> str:
    """Generate CSV report of validation issues"""
    # Create output directory if it doesn't exist
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    filename = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(output_dir, filename)
    
    # Prepare CSV data
    fieldnames = ['Product Title', 'Product ID', 'Issue Type', 'Issue Description', 'Details']
    rows = []
    
    for product_id, data in issues_found.items():
        title = data['title']
        for issue in data['issues']:
            rows.append({
                'Product Title': title,
                'Product ID': product_id,
                'Issue Type': issue.severity,
                'Issue Description': issue.message,
                'Details': str(issue.details) if issue.details else ''
            })
    
    # Write to CSV
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    return filepath

def format_email_content(total_products: int, issues_count: int, filename: str) -> str:
    """Format email content with summary and CSV attachment info"""
    return f"""Product Validation Report Summary
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Total Products Checked: {total_products}
Products with Issues: {issues_count}

Details are attached in: {filename}"""

def main():
    try:
        # Generate report
        validation_results = generate_validation_report()
        
        if validation_results['issues']:
            # Generate CSV
            csv_path = generate_csv_report(validation_results['issues'])
            filename = os.path.basename(csv_path)
            
            # Format email content
            email_content = format_email_content(
                total_products=validation_results['total_products'],
                issues_count=validation_results['issues_count'],
                filename=filename
            )
            
            # Send email with attachment
            email_client = EmailClient()
            email_client.send_report(
                subject=f"Daily Product Validation Report - {datetime.now().strftime('%Y-%m-%d')}",
                content=email_content,
                recipient_list=report_configs.INVENTORY_REPORT_RECIPIENTS,
                attachments={filename: csv_path}
            )
            
            # Exit with status code 1 if issues found
            sys.exit(1)
        else:
            logging.info("No validation issues found")
            sys.exit(0)
            
    except Exception as e:
        logging.error(f"Error running validation report: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()