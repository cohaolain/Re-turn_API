def calculate_checksum(code):
    total = 0
    # Loop through the reversed code (from right to left)
    for i, digit in enumerate(reversed(code)):
        if i % 2 == 0:   # If the index of the current digit is even, multiply it by 3 and add it to the total
            total += int(digit) * 3
        else:             # Otherwise, just add it to the total as is
            total += int(digit)
    # Return the remainder of the total when divided by 10, or subtract from 10 if not zero
    return (10 - (total % 10)) % 10


def verify_checksum(code):
    """Validate a barcode based on its checksum."""
    # UPC-E
    if len(code) == 6:
        return int(code[-1]) == calculate_checksum(code[:-1])
    # EAN-8
    if len(code) == 8:
        return int(code[-1]) == calculate_checksum(code[:-1])
    # UPC-A
    elif len(code) == 12:
        return int(code[-1]) == calculate_checksum(code[:-1])
    # EAN-13
    elif len(code) == 13:
        return int(code[-1]) == calculate_checksum(code[:-1])
    else:
        # Return false if the barcode is not valid (wrong number of digits)
        return False
