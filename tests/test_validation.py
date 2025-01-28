from shared.shopify_utils import ShopifyAPI
from shared.validation import ProductValidator, ValidationConfig
import json

def test_specific_product(product_id):
    """Test validation on a specific product"""
    api = ShopifyAPI()
    query = """
    query($id: ID!) {
        product(id: $id) {
            id
            title
            status
            variants(first: 20) {
                edges {
                    node {
                        id
                        sku
                        taxable
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
    """
    
    variables = {
        "id": f"gid://shopify/Product/{product_id}"
    }
    
    try:
        data = api.run_query(query, variables)
        product = data['product']
        
        print("\nRaw Product Data:")
        print(json.dumps(product, indent=2))
        
        print(f"\nTesting Product: {product['title']} (ID: {product_id})")
        
        config = ValidationConfig()
        validator = ProductValidator(config)
        
        issues = validator.validate_variant_settings(product)
        
        if issues:
            print("\nIssues found:")
            for issue in issues:
                print(f"[{issue.severity}] {issue.message}")
                if issue.details:
                    print(f"Details: {issue.details}")
        else:
            print("No issues found")
            
    except Exception as e:
        print(f"Error testing product: {e}")

if __name__ == "__main__":
    # Test gift card product
    test_specific_product("6589468967045")