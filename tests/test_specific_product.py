import os
from shared.validation import ProductValidator, ValidationConfig
from shared.shopify_utils import ShopifyAPI
from configs.report_configs import PRODUCT_VALIDATION

def fetch_specific_product(product_id):
    api = ShopifyAPI()
    query = """
    query($id: ID!) {
        product(id: $id) {
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
                    }
                }
            }
        }
    }
    """
    
    variables = {
        "id": f"gid://shopify/Product/{product_id}"
    }
    
    data = api.run_query(query, variables)
    return data['product']

def test_specific_product(product_id):
    config = ValidationConfig(
        min_images=PRODUCT_VALIDATION['min_images'],
        min_description_length=PRODUCT_VALIDATION['min_description_length'],
        min_price=PRODUCT_VALIDATION['min_price']
    )
    
    validator = ProductValidator(config)
    
    try:
        product = fetch_specific_product(product_id)
        print(f"\nTesting product: {product['title']} (ID: {product_id})")
        
        issues = validator.validate_product(product)
        if issues:
            print("\nValidation Issues Found:")
            for issue in issues:
                print(f"[{issue.severity}] {issue.message}")
                if issue.details:
                    print(f"    Details: {issue.details}")
        else:
            print("No validation issues found.")
            
    except Exception as e:
        print(f"Error testing product: {e}")

if __name__ == "__main__":
    test_specific_product("7111610990725")