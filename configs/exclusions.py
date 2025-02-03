from typing import List, Dict, Optional
import re

class ExclusionList:
    def __init__(self):
        # Core exclusion lists
        self.exact_titles = set([
            "Kitchen Arts & Letters Gift Card",
            # Add more exact titles here
        ])
        
        # Define patterns with type
        self.partial_patterns = [
            {'pattern': "Class:", 'type': 'starts_with'},  # Only match at start
            {'pattern': "Gift Card", 'type': 'contains'},  # Match anywhere
            {'pattern': "Limited Edition", 'type': 'contains'},
            {'pattern': "Clean Out", 'type': 'contains'},
            {'pattern': "OP:", 'type': 'starts_with'},
            {'pattern': "Talk & Taste", 'type': 'starts_with'},
            {'pattern': "Le Journal du Patissier", 'type': 'starts_with'},
            {'pattern': "Cookbook Club", 'type': 'contains'},
            # Add more partial matches here
        ]
        
        self.barcodes = set([
            # Add more barcodes here
        ])
        
        self.urls = set([
            # Add more URLs here
        ])
        
        # Compile partial title patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile partial title patterns for efficient matching"""
        self.title_patterns = []
        for pattern_info in self.partial_patterns:
            pattern = pattern_info['pattern']
            match_type = pattern_info['type']
            
            if match_type == 'starts_with':
                regex = f"^{re.escape(pattern)}"
            elif match_type == 'contains':
                regex = f".*{re.escape(pattern)}.*"
            else:
                continue  # Skip invalid pattern types
                
            self.title_patterns.append(re.compile(regex, re.IGNORECASE))
    
    def should_exclude(self, product: Dict) -> tuple[bool, Optional[str]]:
        """
        Check if a product should be excluded
        Returns (should_exclude: bool, reason: Optional[str])
        """

        # Defensive check for None or empty product
        if not product:
            return False, None  # Or log a warning if needed

        # Check exact title match
        title = product.get('title', '')
        if not title:  # Additional check in case title is None
            return False, None

        if title in self.exact_titles:
            return True, f"Exact title match: {title}"
            
        # Check partial title matches
        for pattern in self.title_patterns:
            if pattern.search(title):
                return True, f"Partial title match: {pattern.pattern}"
        
        # Check barcode/ISBN
        variants = product.get('variants', {}).get('edges', [])
        for variant in variants:
            variant_node = variant.get('node', {})
            if not variant_node:  # Defensive check for None variant
                continue
            
            barcode = variant_node.get('barcode')
            if barcode and barcode in self.barcodes:
                return True, f"Barcode match: {barcode}"
        
        # Check URL
        handle = product.get('handle', '')
        if handle:
            url = f"https://kitchenartsandletters.com/products/{handle}"
            if url in self.urls:
                return True, f"URL match: {url}"
        
        return False, None

def load_exclusions() -> ExclusionList:
    """Factory function to create and return ExclusionList instance"""
    return ExclusionList()