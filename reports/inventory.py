import sys
from datetime import datetime
from shared import shopify_utils, email_utils, validation
from configs import report_configs

def fetch_active_products():
    """Fetches all published products using GraphQL"""
    query = """
    query($first: Int!, $after: String) {
        products(first: $first, after: $after, query: "status:active") {
            edges {
                node {
                    id
                    title
                    descriptionHtml
                    images(first: 10) {
                        edges {
                            node {
                                id
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
                                key
                                value
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
    return shopify_utils.paginated_query(query)

def validate_product(product):
    """Validates a single product for required data"""
    issues = []
    
    # Check images
    if not product['images']['edges']:
        issues.append(f"No images found")
        
    # Check description
    if not product.get('descriptionHtml'):
        issues.append(f"Missing description")
        
    # Check price
    price_range = product.get('priceRangeV2', {})
    min_price = price_range.get('minVariantPrice', {}).get('amount')
    if not min_price or float(min_price) <= 0:
        issues.append(f"Invalid or missing price")
        
    # Check tags
    if not product.get('tags'):
        issues.append(f"No tags assigned")
        
    # Check collections
    if not product['collections']['edges']:
        issues.append(f"Not assigned to any collection")
        
    # Check required metafields
    required_metafields = report_configs.REQUIRED_METAFIELDS
    found_metafields = {edge['node']['key'] for edge in product['metafields']['edges']}
    missing_metafields = required_metafields - found_metafields
    if missing_metafields:
        issues.append(f"Missing metafields: {', '.join(missing_metafields)}")
        
    return issues

def generate_report():
    """Generates inventory validation report"""
    products = fetch_active_products()
    issues_found = {}
    
    for product in products:
        issues = validate_product(product)
        if issues:
            issues_found[product['id']] = {
                'title': product['title'],
                'issues': issues
            }
    
    return issues_found

def main():
    try:
        issues = generate_report()
        
        if issues:
            email_content = validation.format_validation_report(
                title="Daily Product Data Validation Report",
                issues=issues,
                date=datetime.now()
            )
            
            email_utils.send_report(
                subject="Daily Product Validation Report",
                content=email_content,
                recipient_list=report_configs.INVENTORY_REPORT_RECIPIENTS
            )
            
        sys.exit(0 if not issues else 1)
        
    except Exception as e:
        print(f"Error generating report: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()