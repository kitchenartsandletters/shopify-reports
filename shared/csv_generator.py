import csv
import os
from datetime import datetime
from typing import Dict, List
from .csv_mapper import ValidationMapper

def generate_import_csv(products_with_issues: Dict, output_dir: str = 'output') -> str:
    """
    Generates Shopify product import CSV based on validation issues
    Returns path to generated CSV file
    """
    mapper = ValidationMapper()
    rows = []
    
    # Process each product's issues
    for product_id, data in products_with_issues.items():
        product = data.get('product', {})
        images = product.get('images', {}).get('edges', [])
        
        # Get image-specific rows
        image_rows = mapper.map_image_issues(product, images)
        for image_row in image_rows:
            # Merge with product data
            row_data = mapper.map_product_data(product)
            row_data.update(image_row)
            rows.append(row_data)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    filename = f"product_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(output_dir, filename)
    
    # Write CSV file
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=mapper.column_order)
        writer.writeheader()
        
        for row in rows:
            row_dict = {}
            for col in mapper.column_order:
                field = row.get(col)
                row_dict[col] = field.value if field else ''
            writer.writerow(row_dict)
    
    return filepath