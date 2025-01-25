# shared/validation.py

import logging

def validate_sales_data(sales_data, skipped_items):
    """
    Performs basic validation checks on sales data
    Returns a list of warnings if any issues are found
    """
    warnings = []
    
    # Basic volume checks
    total_quantity = sum(sales_data.values())
    if total_quantity == 0:
        warnings.append("WARNING: No sales recorded for this period")
    
    # ISBN format check
    invalid_isbns = [isbn for isbn in sales_data.keys() if not str(isbn).startswith('978')]
    if invalid_isbns:
        warnings.append(f"WARNING: Found {len(invalid_isbns)} invalid ISBNs in sales data")
    
    # Unusual quantities check
    large_quantities = [(isbn, qty) for isbn, qty in sales_data.items() if qty > 1000]
    if large_quantities:
        warnings.append(f"WARNING: Unusually large quantities found for {len(large_quantities)} ISBNs")
        for isbn, qty in large_quantities:
            warnings.append(f"         ISBN: {isbn}, Quantity: {qty}")
    
    # Check for negative quantities
    negative_quantities = [(isbn, qty) for isbn, qty in sales_data.items() if qty < 0]
    if negative_quantities:
        warnings.append(f"WARNING: Found {len(negative_quantities)} ISBNs with negative quantities")
    
    # Basic skipped items analysis
    if len(skipped_items) > 100:  # Arbitrary threshold
        warnings.append(f"WARNING: Large number of skipped items: {len(skipped_items)}")
    
    return warnings

def is_valid_isbn(barcode):
    """
    Checks if a barcode is a valid ISBN (starts with 978)
    """
    return barcode and str(barcode).startswith('978')