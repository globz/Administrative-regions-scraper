#!/usr/bin/env python3
"""
Clean up addresses in the output CSV
- Keep only content after the 3rd comma
- Remove everything after "/" including the slash
"""

import csv
import sys

def clean_address(address):
    """
    Clean the address string:
    1. Keep only content after 3rd comma
    2. Remove everything after "/" including the slash
    3. Replace "Quebec" with "Québec"
    4. Handle special cases for provinces and cities
    
    Example:
    "G0R 1M0, Frampton, La Nouvelle-Beauce, Chaudière - Appalaches, Quebec / Québec"
    -> "Chaudière - Appalaches, Québec"
    """
    if not address or address == 'NOT FOUND':
        return address
    
    # Split by comma
    parts = [p.strip() for p in address.split(',')]
    
    # Special case: Ontario addresses - check pattern before general processing
    # Pattern: "POSTAL, City, County/Region, Ontario" -> return "County/Region, Ontario"
    if len(parts) == 4 and parts[-1] == 'Ontario':
        # Return last two parts (County, Ontario)
        return f"{parts[2]}, Ontario"
    
    # If there are fewer than 4 parts (3 commas), return as is
    if len(parts) < 4:
        return address.strip()
    
    # Join everything after the 3rd comma (index 3 onwards)
    cleaned = ', '.join(parts[3:])
    
    # Special case handling for provinces with French/English names
    # Extract what's after the "/" if it exists (French version)
    if '/' in cleaned:
        parts_slash = cleaned.split('/')
        
        # For Nova Scotia / Nouvelle-Écosse -> use Nouvelle-Écosse
        if 'Nouvelle-Écosse' in cleaned:
            return 'Nouvelle-Écosse'
        
        # For Newfoundland & Labrador / Terre-Neuve-et-Labrador -> use Terre-Neuve-et-Labrador
        if 'Terre-Neuve-et-Labrador' in cleaned:
            return 'Terre-Neuve-et-Labrador'
        
        # For Prince Edward Island / Île-du-Prince-Édouard -> use Île-du-Prince-Édouard
        if 'Île-du-Prince-Édouard' in cleaned:
            return 'Île-du-Prince-Édouard'
        
        # For New Brunswick / Nouveau-Brunswick -> use Nouveau-Brunswick
        if 'Nouveau-Brunswick' in cleaned:
            return 'Nouveau-Brunswick'
        
        # For Quebec / Québec (at the end) -> take everything before the slash
        cleaned = parts_slash[0].strip()
    
    # Special case: Ottawa, Ontario - keep both city and province
    if 'Ottawa' in address and 'Ontario' in cleaned:
        return 'Ottawa, Ontario'
    
    # Special case: Montréal addresses - should return "Montréal, Québec"
    if 'Montréal' in address or 'Montreal' in address:
        return 'Montréal, Québec'
    
    # Special case: Québec city - should return "Québec, Québec"
    # Check if the original address has "Québec, Québec" pattern
    if address.count('Québec') >= 2 or (address.count('Quebec') >= 2):
        return 'Québec, Québec'
    
    # Replace "Quebec" with "Québec" (with proper accent)
    cleaned = cleaned.replace('Quebec', 'Québec')
    
    return cleaned.strip()


def process_csv(input_file, output_file):
    """Process the CSV file and clean addresses"""
    
    results = []
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                postal_code = row['postal_code']
                address = row['address']
                
                # Clean the address
                cleaned_address = clean_address(address)
                
                results.append({
                    'postal_code': postal_code,
                    'address': cleaned_address
                })
        
        # Write cleaned results
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['postal_code', 'address'])
            writer.writeheader()
            writer.writerows(results)
        
        print(f"Cleaned {len(results)} addresses")
        print(f"Output written to: {output_file}")
        
        # Show some examples
        print("\nExample transformations:")
        for i, row in enumerate(results[:5]):
            print(f"  {row['postal_code']}: {row['address']}")
        
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 clean_addresses.py <input_csv> [output_csv]")
        print("\nExample: python3 clean_addresses.py output.csv cleaned_output.csv")
        print("\nThis script will:")
        print("  1. Keep only content after the 3rd comma")
        print("  2. Remove everything after '/' including the slash")
        print("  3. Replace 'Quebec' with 'Québec'")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'cleaned_' + input_file
    
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}\n")
    
    process_csv(input_file, output_file)


if __name__ == '__main__':
    main()
