import os
import re
from typing import Dict, List, Set
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ValidationConfig:
    min_images: int = 1
    min_description_length: int = 100
    required_metafields: Set[str] = None
    required_collections: Set[str] = None
    required_tags: Set[str] = None
    min_price: float = 0.01

@dataclass
class ValidationIssue:
    severity: str  # 'error' or 'warning'
    message: str
    details: Dict = None

class ProductValidator:
    def __init__(self, config: ValidationConfig):
        self.config = config
        
    def validate_images(self, product: Dict) -> List[ValidationIssue]:
        """Validate product has required number of images"""
        issues = []
        images = product.get('images', {}).get('edges', [])
        
        if not images:
            issues.append(ValidationIssue(
                severity='error',
                message='No product images found'
            ))
        elif len(images) < self.config.min_images:
            issues.append(ValidationIssue(
                severity='warning',
                message=f'Found {len(images)} images, minimum {self.config.min_images} required'
            ))
            
        return issues
        
    def validate_description(self, product: Dict) -> List[ValidationIssue]:
        """Validate product description length"""
        issues = []
        description = product.get('descriptionHtml', '')
        
        if not description:
            issues.append(ValidationIssue(
                severity='error',
                message='Missing product description'
            ))
        elif len(description) < self.config.min_description_length:
            issues.append(ValidationIssue(
                severity='warning',
                message=f'Description length ({len(description)}) below minimum ({self.config.min_description_length})'
            ))
            
        return issues
        
    def validate_pricing(self, product: Dict) -> List[ValidationIssue]:
        """Validate product pricing"""
        issues = []
        price_range = product.get('priceRangeV2', {})
        min_price = price_range.get('minVariantPrice', {}).get('amount')
        
        if not min_price:
            issues.append(ValidationIssue(
                severity='error',
                message='No price information found'
            ))
        elif float(min_price) < self.config.min_price:
            issues.append(ValidationIssue(
                severity='error',
                message=f'Price ({min_price}) below minimum ({self.config.min_price})'
            ))
            
        return issues
        
    def validate_collections(self, product: Dict) -> List[ValidationIssue]:
        """Validate product collection assignments"""
        issues = []
        collections = product.get('collections', {}).get('edges', [])
        
        if not collections:
            issues.append(ValidationIssue(
                severity='error',
                message='Product not assigned to any collection'
            ))
                
        return issues
        
    def validate_tags(self, product: Dict) -> List[ValidationIssue]:
        """Validate product tags"""
        issues = []
        tags = product.get('tags', [])
        
        if not tags:
            issues.append(ValidationIssue(
                severity='error',
                message='Product has no tags assigned'
            ))
        elif len(tags) == 1:
            issues.append(ValidationIssue(
                severity='warning',
                message='Product has only one tag',
                details={'current_tag': tags[0]}
            ))
        elif len(tags) == 2:
            issues.append(ValidationIssue(
                severity='warning',
                message='Product has only two tags',
                details={'current_tags': tags}
            ))
                
        return issues
        
    def validate_metafields(self, product: Dict) -> List[ValidationIssue]:
        """Validate required metafields"""
        issues = []
        required_fields = {
            'custom.author': 'Author missing',
            'custom.language': 'Language missing',
            'custom.binding': 'Binding missing',
            'custom.pub_date': 'Publication date missing'
        }
        
        metafields = {
            f"{edge['node']['namespace']}.{edge['node']['key']}": edge['node']['value']
            for edge in product.get('metafields', {}).get('edges', [])
        }
        
        for field, error_msg in required_fields.items():
            if field not in metafields or not metafields[field]:
                issues.append(ValidationIssue(
                    severity='error',
                    message=error_msg,
                    details={'field': field}
                ))
        
        return issues
        
    def validate_barcode(self, product: Dict) -> List[ValidationIssue]:
        """Validate variant barcodes"""
        issues = []
        variants = product.get('variants', {}).get('edges', [])
        
        if not variants:
            issues.append(ValidationIssue(
                severity='error',
                message='Product has no variants'
            ))
            return issues
            
        for variant in variants:
            barcode = variant['node'].get('barcode')
            if not barcode:
                issues.append(ValidationIssue(
                    severity='error',
                    message='Variant missing barcode/ISBN',
                    details={'variant_id': variant['node'].get('id')}
                ))
                
        return issues
        
    def validate_sku(self, product: Dict) -> List[ValidationIssue]:
        """Validate variant SKUs"""
        issues = []
        variants = product.get('variants', {}).get('edges', [])
        
        if not variants:
            issues.append(ValidationIssue(
                severity='error',
                message='Product has no variants'
            ))
            return issues
            
        for variant in variants:
            sku = variant['node'].get('sku')
            if not sku:
                issues.append(ValidationIssue(
                    severity='error',
                    message='Variant missing SKU',
                    details={'variant_id': variant['node'].get('id')}
                ))
                
        return issues
        
    def validate_variant_settings(self, product: Dict) -> List[ValidationIssue]:
        """Validate variant settings (fulfillment, inventory, taxable)"""
        issues = []
        variants = product.get('variants', {}).get('edges', [])
        
        for variant in variants:
            node = variant['node']
            variant_id = node.get('id')
            
            # Check inventory and fulfillment settings
            inventory_item = node.get('inventoryItem', {})
            inventory_levels = inventory_item.get('inventoryLevels', {}).get('edges', [])
            
            if inventory_levels:
                location = inventory_levels[0]['node']['location']
                
                # Check if it's manual fulfillment
                if location.get('isFulfillmentService'):
                    issues.append(ValidationIssue(
                        severity='error',
                        message='Variant not set for manual fulfillment',
                        details={
                            'variant_id': variant_id,
                            'location': location.get('name')
                        }
                    ))
                
                if not location.get('fulfillsOnlineOrders'):
                    issues.append(ValidationIssue(
                        severity='error',
                        message='Location not set to fulfill online orders',
                        details={
                            'variant_id': variant_id,
                            'location': location.get('name')
                        }
                    ))
                
                if not location.get('shipsInventory'):
                    issues.append(ValidationIssue(
                        severity='error',
                        message='Location not set to ship inventory',
                        details={
                            'variant_id': variant_id,
                            'location': location.get('name')
                        }
                    ))
            
            # Check taxable status
            if not node.get('taxable'):
                issues.append(ValidationIssue(
                    severity='error',
                    message='Variant not set as taxable',
                    details={'variant_id': variant_id}
                ))
                
        return issues

    def validate_image_alt_text(self, product: Dict) -> List[ValidationIssue]:
        """Validate image alt text"""
        issues = []
        images = product.get('images', {}).get('edges', [])
        
        for idx, image in enumerate(images, 1):
            node = image['node']
            alt_text = node.get('altText', '')
            
            if not alt_text:
                if idx == 1:
                    expected = f"Book Cover: {product['title']}"
                    issues.append(ValidationIssue(
                        severity='error',
                        message=f'First image missing alt text',
                        details={
                            'image_id': node.get('id'),
                            'expected': expected
                        }
                    ))
                else:
                    issues.append(ValidationIssue(
                        severity='error',
                        message=f'Image {idx} missing alt text',
                        details={
                            'image_id': node.get('id'),
                            'expected': 'presentation image'
                        }
                    ))
            elif idx == 1 and alt_text != f"Book Cover: {product['title']}":
                issues.append(ValidationIssue(
                    severity='error',
                    message='First image has incorrect alt text',
                    details={
                        'image_id': node.get('id'),
                        'current': alt_text,
                        'expected': f"Book Cover: {product['title']}"
                    }
                ))
            elif idx > 1 and alt_text.lower() != "presentation image":
                issues.append(ValidationIssue(
                    severity='error',
                    message=f'Image {idx} has incorrect alt text',
                    details={
                        'image_id': node.get('id'),
                        'current': alt_text,
                        'expected': 'presentation image'
                    }
                ))
                
        return issues
        
    def validate_publication(self, product: Dict) -> bool:
        """
        Checks if product is published to online store.
        Returns True if published, False if not.
        """
        return product.get('status') == 'ACTIVE'
        
    def validate_product(self, product: Dict) -> List[ValidationIssue]:
        """Run all validation checks on a product"""
        # First check if product is published
        if not self.validate_publication(product):
            return []  # Skip validation for unpublished products
            
        issues = []
        validation_methods = [
            self.validate_images,
            self.validate_description,
            self.validate_pricing,
            self.validate_collections,
            self.validate_tags,
            self.validate_metafields,
            self.validate_barcode,
            self.validate_sku,
            self.validate_variant_settings,
            self.validate_image_alt_text
        ]
        
        for validate in validation_methods:
            issues.extend(validate(product))
            
        return issues

@dataclass        
class TagValidator:
    """Helper class for tag validation and transformation"""
    
    BINDING_TAGS = {
        'P': 'Paperback',
        'C': 'Hardcover',
        'F': 'Flexibound',
        'S': 'Spiralbound'
    }
    
    LANGUAGE_TAGS = {
        'Ln_Ar': 'Arabic',
        'Ln_Aa': 'Catalan',
        'Ln_Ch': 'Chinese',
        'Ln_Da': 'Danish',
        'Ln_Du': 'Dutch',
        'Ln_En': 'English',
        'Ln_Fa': 'Faroese',
        'Ln_Fr': 'French',
        'Ln_Ge': 'German',
        'Ln_Kr': 'Korean',
        'Ln_It': 'Italian',
        'Ln_Ja': 'Japanese',
        'Ln_Po': 'Portuguese',
        'Ln_Sp': 'Spanish',
        'Ln_Sw': 'Swedish',
        'Ln_Ta': 'Tagalog',
        'Ln_Th': 'Thai'
    }
    
    @staticmethod
    def parse_date_tag(tag: str) -> tuple:
        """Parse date tag and return standardized format if valid"""
        # Various date patterns
        patterns = [
            r'^(\d{1,2})-(\d{1,2})-(\d{4})$',  # M-D-YYYY or MM-DD-YYYY
        ]
        
        for pattern in patterns:
            match = re.match(pattern, tag)
            if match:
                month, day, year = match.groups()
                try:
                    # Validate date
                    date_obj = datetime(int(year), int(month), int(day))
                    # Return both formatted strings
                    return (
                        f"{int(month):02d}-{int(day):02d}-{year}",  # MM-DD-YYYY
                        f"{year}-{int(month):02d}-{int(day):02d}"    # YYYY-MM-DD
                    )
                except ValueError:
                    pass
        return None, None
    
    @staticmethod
    def is_binding_tag(tag: str) -> str:
        """Check if tag is a binding code and return full name"""
        return TagValidator.BINDING_TAGS.get(tag)
    
    @staticmethod
    def get_language_name(tag: str) -> str:
        """Get full language name from language tag"""
        return TagValidator.LANGUAGE_TAGS.get(tag)