#!/usr/bin/env python3
"""
Postal Code Address Scraper for Canadian Postal Codes
Queries https://can.postcodequery.com/ and extracts address information
"""

import csv
import sys
import time
import html
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional


def clean_postal_code(postal_code: str) -> str:
    """Clean and format postal code (strip whitespace, convert to uppercase)"""
    return postal_code.strip().upper()


def query_postal_code(postal_code: str, session: requests.Session, max_retries: int = 3, verbose: bool = False) -> Optional[str]:
    """
    Query the website for a postal code and extract the address information
    
    Args:
        postal_code: The postal code to query (e.g., 'J2C 2B6')
        session: requests Session object for connection reuse
        max_retries: Maximum number of retry attempts on failure
        
    Returns:
        The address string if found, None otherwise
    """
    # Clean postal code - just strip and uppercase, let requests handle encoding
    clean_code = postal_code.strip().upper()
    url = "https://can.postcodequery.com/"
    
    # Use simple headers that work (like in verify_fix.py)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://can.postcodequery.com/'
    }
    
    # Form data with the postal code
    form_data = {
        'q': clean_code
    }
    
    for attempt in range(max_retries):
        try:
            response = session.post(url, data=form_data, headers=headers, timeout=15)
            
            # Handle rate limiting (HTTP 429)
            if response.status_code == 429:
                wait_time = (2 ** attempt) * 2  # Exponential backoff: 2, 4, 8 seconds
                print(f"Rate limited. Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                continue
            
            response.raise_for_status()
            
            # Parse HTML with lxml parser for better handling
            soup = BeautifulSoup(response.content, 'lxml')
            
            # The address is in a table with class "bx"
            # Looking for: <table class="bx">...<tbody><tr><td align="left"><a>ADDRESS HERE</a>
            
            postal_code_no_plus = clean_code  # Already has spaces, no need to replace
            
            if verbose:
                print(f"  [DEBUG] Looking for postal code: {postal_code_no_plus}")
                print(f"  [DEBUG] Response status: {response.status_code}")
                print(f"  [DEBUG] Response length: {len(response.content)} bytes")
                # Save response to file for debugging
                import os
                os.makedirs('debug_responses', exist_ok=True)
                debug_file = f"debug_responses/debug_{postal_code.replace(' ', '_')}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"  [DEBUG] Response saved to: {debug_file}")
            
            # Check if response seems valid (should be at least 5KB for a real result)
            if len(response.content) < 5000:
                if verbose:
                    print(f"  [DEBUG] ⚠ Response seems too small ({len(response.content)} bytes) - may be an error page")
                # Still try to parse it, but this is suspicious
            
            if verbose:
                # Check if response contains the table
                if 'class="bx"' in response.text:
                    print(f"  [DEBUG] ✓ Response contains table with class='bx'")
                else:
                    print(f"  [DEBUG] ✗ Response does NOT contain table with class='bx'")
                if postal_code_no_plus in response.text:
                    print(f"  [DEBUG] ✓ Response contains postal code '{postal_code_no_plus}'")
                else:
                    print(f"  [DEBUG] ✗ Response does NOT contain postal code '{postal_code_no_plus}'")
            
            # Method 1: Find all <tr> tags directly in the document (more reliable)
            all_rows = soup.find_all('tr')
            if verbose:
                print(f"  [DEBUG] Found {len(all_rows)} total rows in document")
            
            for row in all_rows:
                # Look for td with align="left"
                cells = row.find_all('td', {'align': 'left'})
                if cells:
                    # Check if there's a link in this cell
                    link = cells[0].find('a')
                    if link:
                        link_text = link.get_text(strip=True)
                        # Check if this contains our postal code and looks like an address
                        if postal_code_no_plus in link_text and ',' in link_text:
                            address = html.unescape(link_text)
                            if verbose:
                                print(f"  [DEBUG] Found via Method 1 (table rows): {address[:80]}...")
                            return address
            
            # Method 2: Look for any link that contains the postal code and has commas (address format)
            all_links = soup.find_all('a', href=True)
            if verbose:
                print(f"  [DEBUG] Found {len(all_links)} total links")
            
            for link in all_links:
                link_text = link.get_text(strip=True)
                # Address format: "G0R 3Z0, City, Region, Province, Quebec / Québec"
                if postal_code_no_plus in link_text and ',' in link_text:
                    address = html.unescape(link_text)
                    if verbose:
                        print(f"  [DEBUG] Found via Method 2 (all links): {address[:80]}...")
                    return address
            
            # Method 3: Look directly in all table cells
            all_tds = soup.find_all('td', {'align': 'left'})
            if verbose:
                print(f"  [DEBUG] Found {len(all_tds)} cells with align=left")
            
            for td in all_tds:
                td_text = td.get_text(strip=True)
                if postal_code_no_plus in td_text and ',' in td_text:
                    address = html.unescape(td_text)
                    if verbose:
                        print(f"  [DEBUG] Found via Method 3 (td cells): {address[:80]}...")
                    return address
            
            # Method 4: Search all table cells for matching text
            all_tds = soup.find_all('td')
            for td in all_tds:
                td_text = td.get_text(strip=True)
                if postal_code_no_plus in td_text and ',' in td_text and len(td_text) > 20:
                    address = html.unescape(td_text)
                    if verbose:
                        print(f"  [DEBUG] Found via Method 4 (all td cells): {address[:80]}...")
                    return address
            
            if verbose:
                print(f"  [DEBUG] No address found after trying all methods")
            
            print(f"Warning: Could not find address for {postal_code}")
            return None
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt)  # Exponential backoff: 1, 2, 4 seconds
                print(f"Timeout for {postal_code}. Retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"Error: Timeout querying {postal_code} after {max_retries} attempts")
                return None
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt)  # Exponential backoff
                print(f"Network error for {postal_code}. Retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"Error querying {postal_code} after {max_retries} attempts: {e}")
                return None
                
        except Exception as e:
            print(f"Unexpected error for {postal_code}: {e}")
            return None
    
    return None


def process_csv(input_file: str, output_file: str, delay: float = 1.0, verbose: bool = False):
    """
    Process CSV file with postal codes and create output with addresses
    
    Args:
        input_file: Path to input CSV file with postal codes
        output_file: Path to output CSV file
        delay: Delay between requests in seconds (to be respectful to the server)
    """
    results: List[Dict[str, str]] = []
    
    # Read input CSV
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Check if there's a postal_code column
            if reader.fieldnames is None:
                print("Error: CSV file appears to be empty")
                return
            
            # Find the postal code column (case insensitive)
            postal_code_col = None
            for col in reader.fieldnames:
                if col.lower() in ['postal_code', 'postalcode', 'postal code', 'zip', 'postcode']:
                    postal_code_col = col
                    break
            
            if postal_code_col is None:
                print(f"Error: Could not find postal code column. Available columns: {reader.fieldnames}")
                print("Please ensure your CSV has a column named 'postal_code' or similar")
                return
            
            postal_codes = [row[postal_code_col] for row in reader if row[postal_code_col].strip()]
            
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found")
        return
    except Exception as e:
        print(f"Error reading input file: {e}")
        return
    
    print(f"Found {len(postal_codes)} postal codes to process")
    
    # Create a session for connection reuse
    session = requests.Session()
    
    # Visit the homepage first to establish session cookies
    try:
        print("Establishing session with website...")
        home_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        session.get('https://can.postcodequery.com/', headers=home_headers, timeout=10)
        time.sleep(2)  # Wait after initial visit
        print("Session established.\n")
    except Exception as e:
        print(f"Warning: Could not establish session: {e}\n")
    
    # Query each postal code
    # Open output file and write header
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['postal_code', 'address'])
            writer.writeheader()
            
            for i, postal_code in enumerate(postal_codes, 1):
                print(f"Processing {i}/{len(postal_codes)}: {postal_code}")
                
                address = query_postal_code(postal_code, session, verbose=verbose)
                
                result = {
                    'postal_code': postal_code,
                    'address': address if address else 'NOT FOUND'
                }
                
                # Write result immediately
                writer.writerow(result)
                f.flush()  # Ensure it's written to disk
                
                results.append(result)
                
                # Be respectful to the server
                if i < len(postal_codes):
                    time.sleep(delay)
        
        print(f"\nResults written to {output_file}")
        print(f"Successfully processed: {sum(1 for r in results if r['address'] != 'NOT FOUND')}/{len(results)}")
        
    except Exception as e:
        print(f"Error writing output file: {e}")
        # Still print summary of what we got
        if results:
            print(f"Processed {len(results)} postal codes before error")


def main():
    """Main function"""
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print("Usage: python3 postal_code_scraper.py <input_csv> [output_csv] [delay_seconds] [--verbose]")
        print("\nExample: python3 postal_code_scraper.py postal_codes.csv results.csv 2.0")
        print("Example: python3 postal_code_scraper.py postal_codes.csv results.csv 2.0 --verbose")
        print("\nInput CSV should have a column named 'postal_code' (or similar)")
        print("\nRecommended delay: 1.5-2.0 seconds to avoid rate limiting")
        print("\nOptions:")
        print("  --verbose, -v    Show debug information for each request")
        sys.exit(1)
    
    # Check for verbose flag
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    # Remove verbose flags from args
    args = [arg for arg in sys.argv if arg not in ['--verbose', '-v']]
    
    input_file = args[1]
    output_file = args[2] if len(args) > 2 else 'postal_code_results.csv'
    delay = float(args[3]) if len(args) > 3 else 1.5  # Increased default to 1.5 seconds
    
    # Warn if delay is too short
    if delay < 1.0:
        print(f"WARNING: Delay of {delay}s is quite aggressive and may trigger rate limiting.")
        print("Recommended minimum: 1.5 seconds")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted. Please use a longer delay.")
            sys.exit(1)
    
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Delay between requests: {delay} seconds")
    print(f"Verbose mode: {'ON' if verbose else 'OFF'}\n")
    
    process_csv(input_file, output_file, delay, verbose)


if __name__ == '__main__':
    main()
