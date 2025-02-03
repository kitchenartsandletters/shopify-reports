from typing import Dict, List, Set
from dataclasses import dataclass
from .validation import ValidationIssue, TagValidator  # Use relative import with dot notation

@dataclass
class CSVField:
    """Represents a field in the import CSV"""
    column_name: str
    value: str = ""
    required: bool = True

class ValidationMapper:
    """Maps validation issues to CSV fields"""
    
    def __init__(self):
        # Define standard columns that should always be included
        self.standard_columns = {
            'Handle',
            'Title'
        }
        
        # Map validation issues to CSV columns
        self.validation_map = {
            'missing_description': ['Body (HTML)'],
            'missing_price': ['Variant Price'],
            'missing_tags': ['Tags'],
            'missing_sku': ['Variant SKU'],
            'missing_barcode': ['Variant Barcode'],
            'fulfillment_service': ['Variant Fulfillment Service'],
            'taxable_status': ['Variant Taxable'],
            'missing_metafield_author': ['Author (product.metafields.custom.author)'],
            'missing_metafield_language': ['Language (product.metafields.custom.language)'],
            'missing_metafield_binding': ['Binding (product.metafields.custom.binding)'],
            'missing_metafield_pub_date': ['Publication Date (product.metafields.custom.pub_date)']
        }

    def map_validation_issues(self, product: Dict, issues: List[ValidationIssue]) -> Dict[str, CSVField]:
        """
        Maps validation issues to CSV fields
        Returns dictionary of column names and their values/settings
        """
        csv_fields = {}
        
        # Add standard columns
        csv_fields['Handle'] = CSVField('Handle', product.get('handle', ''))
        csv_fields['Title'] = CSVField('Title', product.get('title', ''))
        
        for issue in issues:
            # Access ValidationIssue attributes directly
            severity = issue.severity
            message = issue.message
            details = issue.details or {}
            
            # Process each type of validation issue
            if 'description' in message.lower():
                csv_fields['Body (HTML)'] = CSVField('Body (HTML)')
                
            elif 'price' in message.lower():
                csv_fields['Variant Price'] = CSVField('Variant Price')
                
            elif 'tags' in message.lower():
                csv_fields['Tags'] = CSVField('Tags')
                
            elif 'SKU' in message:
                csv_fields['Variant SKU'] = CSVField('Variant SKU')
                
            elif 'barcode' in message.lower():
                csv_fields['Variant Barcode'] = CSVField('Variant Barcode')
                
            elif 'fulfillment' in message.lower():
                csv_fields['Variant Fulfillment Service'] = CSVField(
                    'Variant Fulfillment Service',
                    'manual'  # Set default value
                )
                
            elif 'taxable' in message.lower():
                csv_fields['Variant Taxable'] = CSVField(
                    'Variant Taxable',
                    'true'  # Set default value
                )
                
            # Handle metafield issues
            elif 'metafield' in message.lower():
                field = details.get('field', '')
                if 'author' in field:
                    csv_fields['Author (product.metafields.custom.author)'] = CSVField(
                        'Author (product.metafields.custom.author)'
                    )
                elif 'language' in field:
                    csv_fields['Language (product.metafields.custom.language)'] = CSVField(
                        'Language (product.metafields.custom.language)'
                    )
                elif 'binding' in field:
                    csv_fields['Binding (product.metafields.custom.binding)'] = CSVField(
                        'Binding (product.metafields.custom.binding)'
                    )
                elif 'pub_date' in field:
                    csv_fields['Publication Date (product.metafields.custom.pub_date)'] = CSVField(
                        'Publication Date (product.metafields.custom.pub_date)'
                    )

        return csv_fields

    def map_image_issues(self, product: Dict, images: List[Dict]) -> List[Dict[str, CSVField]]:
        """Maps image validation issues to CSV fields"""
        image_rows = []
        
        for idx, image in enumerate(images, 1):
            node = image.get('node', {})
            row_fields = {
                'Handle': CSVField('Handle', product.get('handle', '')),
                'Title': CSVField('Title', product.get('title', '')),
                'Image Position': CSVField('Image Position', str(idx)),
                'Image Src': CSVField('Image Src', node.get('originalSrc', '')),
            }
            
            # Set alt text based on position
            if idx == 1:
                alt_text = f"Book Cover: {product.get('title', '')}"
            else:
                alt_text = "presentation image"
                
            row_fields['Image Alt Text'] = CSVField('Image Alt Text', alt_text)
            image_rows.append(row_fields)
            
        return image_rows

    def map_product_data(self, product: Dict) -> Dict[str, CSVField]:
    """Maps core product data to CSV fields, including custom metafields"""
    validator = TagValidator()
    variant = product.get('variants', {}).get('edges', [])[0].get('node', {}) if product.get('variants', {}).get('edges') else {}
    
    # Process tags for special formats
    tags = list(product.get('tags', []))  # Convert to list for modification
    transformed_tags = []
    metafields = {}
    languages = []  # List to collect multiple languages
    
    # Clean up SKU and Barcode values
    sku = variant.get('sku', '').strip() if variant.get('sku') else ''
    barcode = variant.get('barcode', '').strip() if variant.get('barcode') else ''
    
    # Validate and clean ISBN if necessary
    if barcode.startswith(('978', '979')) and len(barcode) != 13:
        barcode = ''  # Clear invalid ISBN
    
    # Process each tag
    for tag in tags:
        # Check for date tag
        date_tag, pub_date = validator.parse_date_tag(tag)
        if date_tag:
            transformed_tags.append(date_tag)  # Add standardized date tag
            metafields['Publication Date (product.metafields.custom.pub_date)'] = pub_date
            continue
        
        # Check for binding tag
        binding = validator.is_binding_tag(tag)
        if binding:
            metafields['Binding (product.metafields.custom.binding)'] = binding
            transformed_tags.append(tag)
            continue
        
        # Check for language tag
        language = validator.get_language_name(tag)
        if language:
            languages.append(language)  # Add to languages list
            transformed_tags.append(tag)
            continue
            
        transformed_tags.append(tag)
    
    # Add languages as array if any found
    if languages:
        language_list = [f'"{lang}"' for lang in languages]
        metafields['Language (product.metafields.custom.language)'] = f"[{', '.join(language_list)}]"
    
    # If SKU exists, use it for author field (using cleaned SKU)
    if sku:
        metafields['Author (product.metafields.custom.author)'] = sku
    
    # Combine product data with metafields
    csv_fields = {
        'Handle': CSVField('Handle', product.get('handle', '')),
        'Title': CSVField('Title', product.get('title', '')),
        'Body (HTML)': CSVField('Body (HTML)', product.get('descriptionHtml', '')),
        'Tags': CSVField('Tags', ', '.join(transformed_tags)),
        'Variant SKU': CSVField('Variant SKU', sku),
        'Variant Barcode': CSVField('Variant Barcode', barcode),
        'Variant Price': CSVField('Variant Price', str(variant.get('price', ''))),
        'Variant Fulfillment Service': CSVField('Variant Fulfillment Service', 'manual')
    }
    
    # Add metafields to CSV fields
    for key, value in metafields.items():
        csv_fields[key] = CSVField(key, str(value))
    
    return csv_fields

    def get_required_columns(self, fields: Dict[str, CSVField]) -> List[str]:
        """Gets list of all required columns based on validation issues"""
        columns = set(self.standard_columns)
        columns.update(field.column_name for field in fields.values())
        return sorted(list(columns))
    
    def get_column_order(self, fields: Dict[str, CSVField] = None) -> List[str]:
        """
        Returns a standardized order of columns for CSV export
        
        If fields is provided, it will incorporate those column names.
        Otherwise, uses predefined columns.
        """
        # Base standard columns
        base_columns = [
            'Handle',
            'Title',
            'Body (HTML)',
            'Tags',
            'Variant SKU',
            'Variant Barcode', 
            'Variant Price',
            'Variant Fulfillment Service',
            'Image Position',
            'Image Src',
            'Image Alt Text',
            # Metafield columns
            'Author (product.metafields.custom.author)',
            'Language (product.metafields.custom.language)',
            'Binding (product.metafields.custom.binding)',
            'Publication Date (product.metafields.custom.pub_date)'
        ]
        
        # If fields are provided, add any new column names
        if fields:
            additional_columns = set(fields.keys()) - set(base_columns)
            base_columns.extend(sorted(list(additional_columns)))
        
        return base_columns

    # Add this as an alias for compatibility
    @property
    def column_order(self) -> List[str]:
        """
        Property alias for get_column_order to maintain backwards compatibility
        """
        return self.get_column_order()