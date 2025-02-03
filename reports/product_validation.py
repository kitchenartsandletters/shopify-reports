import sys
import os
import logging
import csv
from datetime import datetime
from typing import Dict, List

from shared.shopify_utils import ShopifyAPI
from shared.validation import ProductValidator, ValidationConfig, ValidationIssue
from shared.email_utils import EmailClient
from shared import csv_generator
from configs import report_configs
from configs.exclusions import load_exclusions

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def fetch_all_products():
    """Fetches all products using GraphQL pagination"""
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
                    handle
                    status
                    descriptionHtml
                    images(first: 10) {
                        edges {
                            node {
                                id
                                altText
                                originalSrc
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
                                inventoryQuantity
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
                                taxable
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
    page_size = 250
    has_next_page = True
    cursor = None
    total_fetched = 0
    
    while has_next_page:
        variables = {
            "first": page_size,
            "after": cursor
        }
        
        try:
            data = api.run_query(query, variables)
            products_data = data['products']
            
            # Extract products from edges
            products = [edge['node'] for edge in products_data['edges']]
            all_products.extend(products)
            total_fetched = len(all_products)
            
            # Update pagination info
            page_info = products_data['pageInfo']
            has_next_page = page_info['hasNextPage']
            cursor = page_info['endCursor']
            
            # Log progress every 1000 products
            if total_fetched % 1000 == 0:
                logging.info(f"Fetched {total_fetched} products...")
            
        except Exception as e:
            logging.error(f"Error fetching products: {e}")
            raise
            
    # Log final count only once
    logging.info(f"Total products fetched: {total_fetched}")
    return all_products

def log_exclusions(product: Dict, reason: str):
    """Log excluded products"""
    logging.info(f"Excluded product: {product.get('title')} - Reason: {reason}")

def generate_validation_report() -> Dict:
    """
    Fetches all products and generates validation report
    Returns dict of validation results and counts
    """
    logging.info("Starting product validation report generation")
    
    try:
        # Initialize validator and exclusions
        config = ValidationConfig(
            min_images=1,
            min_description_length=100,
            min_price=0.01
        )
        validator = ProductValidator(config)
        exclusions = load_exclusions()
        
        # Fetch and validate products
        products = fetch_all_products()
        total_products = len(products)
        logging.info(f"Fetched {total_products} total products")
        
        # Track validation results and exclusions
        issues_found = {}
        published_count = 0
        excluded_count = 0
        
        # Validate each product
        for product in products:
            # Check exclusions first
            should_exclude, reason = exclusions.should_exclude(product)
            if should_exclude:
                excluded_count += 1
                log_exclusions(product, reason)
                continue
                
            published_count += 1
            issues = validator.validate_product(product)
            if issues:
                issues_found[product['id']] = {
                    'product': product,
                    'issues': issues
                }
        
        logging.info(f"Validated {published_count} published products")
        logging.info(f"Excluded {excluded_count} products")
        logging.info(f"Found issues in {len(issues_found)} products")
        
        return {
            'issues': issues_found,
            'total_products': published_count,
            'issues_count': len(issues_found),
            'excluded_count': excluded_count
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
    fieldnames = ['Product ID', 'Product Title', 'Issue Type', 'Issue Description', 'Details']
    rows = []
    
    for product_id, data in issues_found.items():
        product = data['product']
        title = product['title']
        for issue in data['issues']:
            rows.append({
                'Product ID': product_id,
                'Product Title': title,
                'Issue Type': issue.severity,
                'Issue Description': issue.message,
                'Details': str(issue.details) if issue.details else ''
            })
    
    # Write to CSV
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
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
            # Generate CSV report
            csv_path = generate_csv_report(validation_results['issues'])
            csv_filename = os.path.basename(csv_path)
            
            # Generate import CSV
            import_path = csv_generator.generate_import_csv(validation_results['issues'])
            import_filename = os.path.basename(import_path)
            
            # Format email content
            email_content = format_email_content(
                total_products=validation_results['total_products'],
                issues_count=validation_results['issues_count'],
                filename=f"{csv_filename}, {import_filename}"
            )
            
            # Send email with both attachments
            email_client = EmailClient()
            email_client.send_report(
                subject=f"Daily Product Validation Report - {datetime.now().strftime('%Y-%m-%d')}",
                content=email_content,
                recipient_list=report_configs.INVENTORY_REPORT_RECIPIENTS,
                attachments={
                    csv_filename: csv_path,
                    import_filename: import_path
                }
            )
            
            # Exit with status code 0 even if issues found
            logging.info("Report generated and sent successfully")
            sys.exit(0)
        else:
            logging.info("No validation issues found")
            sys.exit(0)
            
    except Exception as e:
        logging.error(f"Error running validation report: {e}")
        sys.exit(1)  # Only exit with 1 for actual errors

if __name__ == "__main__":
    main()