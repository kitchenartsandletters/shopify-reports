import os
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
        issues = []
        collections = product.get('collections', {}).get('edges', [])
        
        if not collections:
            issues.append(ValidationIssue(
                severity='error',
                message='Product not assigned to any collection'
            ))
                
        return issues
        
    def validate_tags(self, product: Dict) -> List[ValidationIssue]:
        """Validate product has more than one tag"""
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
                
        return issues
        
    def validate_metafields(self, product: Dict) -> List[ValidationIssue]:
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
        
    def validate_publication(self, product: Dict) -> bool:
        """
        Checks if product is published to online store.
        Returns True if published, False if not.
        """
        return product.get('status') == 'ACTIVE'
        
    def validate_variant_settings(self, product: Dict) -> List[ValidationIssue]:
        """Validate various variant settings"""
        issues = []
        variants = product.get('variants', {}).get('edges', [])
        
        for variant in variants:
            node = variant['node']
            variant_id = node.get('id')
            
            # Check SKU
            if not node.get('sku'):
                issues.append(ValidationIssue(
                    severity='error',
                    message='Variant missing SKU',
                    details={'variant_id': variant_id}
                ))
            
            # Check inventory and fulfillment settings
            inventory_item = node.get('inventoryItem', {})
            inventory_levels = inventory_item.get('inventoryLevels', {}).get('edges', [])
            
            if inventory_levels:
                location = inventory_levels[0]['node']['location']
                
                # Check if it's manual fulfillment (not a fulfillment service and handles online orders)
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

def format_validation_report(products_with_issues: Dict[str, List[ValidationIssue]]) -> str:
    """Format validation results into readable report"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not products_with_issues:
        return f"Product Data Validation Report\nGenerated: {now}\n\nAll products passed validation checks."
        
    error_count = sum(1 for issues in products_with_issues.values() 
                     for issue in issues if issue.severity == 'error')
    warning_count = sum(1 for issues in products_with_issues.values() 
                       for issue in issues if issue.severity == 'warning')
    
    lines = [
        f"Product Data Validation Report",
        f"Generated: {now}",
        f"\nSummary:",
        f"• Products with issues: {len(products_with_issues)}",
        f"• Critical errors: {error_count}",
        f"• Warnings: {warning_count}\n",
        "\nDetailed Issues:"
    ]
    
    for product_id, issues in products_with_issues.items():
        errors = [i for i in issues if i.severity == 'error']
        warnings = [i for i in issues if i.severity == 'warning']
        
        lines.extend([
            f"\n{product_id}:",
            "Critical Issues:" if errors else None,
            *[f"❌ {issue.message}" for issue in errors],
            "Warnings:" if warnings else None,
            *[f"⚠️ {issue.message}" for issue in warnings]
        ])
        
    return "\n".join(line for line in lines if line is not None)