import boto3
import json
import sys
from config import AWS_REGION, CLI_PROFILE_NAME

def get_table_results(job_id):
    """
    Get table results from a completed Textract job
    Args:
        job_id (str): The job ID to get results for
    Returns:
        list: List of extracted tables
    """
    session = boto3.Session(profile_name=CLI_PROFILE_NAME, region_name=AWS_REGION)
    textract = session.client('textract')
    
    tables = []
    pagination_token = None
    
    while True:
        # Get the next page of results
        if pagination_token:
            response = textract.get_document_analysis(
                JobId=job_id,
                MaxResults=1000,
                NextToken=pagination_token
            )
        else:
            response = textract.get_document_analysis(
                JobId=job_id,
                MaxResults=1000
            )
            
        # Process blocks
        blocks = response['Blocks']
        tables.extend(extract_tables_from_blocks(blocks))
        
        # Check if there are more pages
        if 'NextToken' in response:
            pagination_token = response['NextToken']
        else:
            break
            
    return tables

def extract_tables_from_blocks(blocks):
    """
    Extract tables from Textract blocks
    Args:
        blocks (list): List of Textract blocks
    Returns:
        list: List of extracted tables
    """
    tables = []
    table = None
    
    for block in blocks:
        if block['BlockType'] == 'TABLE':
            if table:
                tables.append(table)
            table = {
                'Rows': [],
                'Page': block['Page']
            }
        elif block['BlockType'] == 'CELL' and table:
            # Get cell text
            text = ''
            if 'Relationships' in block:
                for relationship in block['Relationships']:
                    if relationship['Type'] == 'CHILD':
                        for child_id in relationship['Ids']:
                            child_block = next((b for b in blocks if b['Id'] == child_id), None)
                            if child_block and child_block['BlockType'] == 'WORD':
                                text += child_block['Text'] + ' '
            
            # Add cell to table
            row_index = block['RowIndex'] - 1
            col_index = block['ColumnIndex'] - 1
            
            # Ensure row exists
            while len(table['Rows']) <= row_index:
                table['Rows'].append([])
                
            # Ensure column exists
            while len(table['Rows'][row_index]) <= col_index:
                table['Rows'][row_index].append('')
                
            # Add cell text
            table['Rows'][row_index][col_index] = text.strip()
            
    # Add last table if exists
    if table:
        tables.append(table)
        
    return tables

def format_bank_statement_data(tables):
    """
    Format bank statement data from extracted tables
    Args:
        tables (list): List of extracted tables
    Returns:
        dict: Dictionary containing summary and transactions
    """
    # Initialize result structure
    result = {
        "summary": {},
        "transactions": []
    }
    
    # Define possible header mappings (add more variations as needed)
    header_mappings = {
        "Date": ["Date", "Transaction Date", "Value Date", "Tran Date", "Create Date"],
        "Reference": ["Reference", "Reference No", "Ref No", "Transaction ID", "Trans ID", "Trans Ref"],
        "Description": ["Description", "Narration", "Transaction Description", "Details", "Particulars", "Description/Payee/Memo"],
        "Value Date": ["Value Date", "Val Date", "Settlement Date", "Create Date"],
        "Deposit": ["Deposit", "Credit", "Credit Amount", "Amount (CR)", "Deposits"],
        "Withdrawal": ["Withdrawal", "Debit", "Debit Amount", "Amount (DR)", "Withdrawals"],
        "Balance": ["Balance", "Running Balance", "Closing Balance", "Current Balance"]
    }
    
    def find_matching_header(headers, possible_names):
        """Find the actual header name used in this statement"""
        for header in headers:
            header = header.strip()
            if any(possible.lower() in header.lower() for possible in possible_names):
                return header
        return None
    
    def map_headers(actual_headers):
        """Map actual headers to our standard format"""
        header_map = {}
        print("\nDebug - Found headers:", actual_headers)  # Debug print
        for standard_header, possible_names in header_mappings.items():
            matched_header = find_matching_header(actual_headers, possible_names)
            if matched_header:
                header_map[standard_header] = matched_header
                print(f"Mapped '{matched_header}' to '{standard_header}'")  # Debug print
        return header_map
    
    for table in tables:
        # Skip empty tables
        if not table['Rows']:
            continue
            
        first_row = table['Rows'][0]
        headers = [cell.strip() for cell in first_row]
        
        print("\nDebug - Processing table with headers:", headers)  # Debug print
        
        # Check if this is a summary/account info table
        # Look for typical summary indicators
        if (any(indicator in cell.lower() for cell in first_row for indicator in 
                ['account', 'currency', 'balance:', 'period', 'statement', 'branch'])):
            print("Found summary table")  # Debug print
            # Extract summary information
            for row in table['Rows']:
                if len(row) >= 2:
                    key = row[0].strip().rstrip(':')  # Remove trailing colon if present
                    value = row[1].strip()
                    if key and value:
                        result["summary"][key] = value
            continue
        
        # Try to identify if this is a transaction table
        header_map = map_headers(headers)
        print(f"Found {len(header_map)} matching headers")  # Debug print
        
        # If we found at least 4 of our expected headers, treat it as a transaction table
        if len(header_map) >= 4:
            print("Processing as transaction table")  # Debug print
            # Get the index for each mapped column
            header_indices = {std_header: headers.index(actual_header) 
                            for std_header, actual_header in header_map.items()}
            
            # Process transactions
            for row in table['Rows'][1:]:  # Skip header row
                if len(row) != len(headers):
                    continue
                    
                transaction = {}
                # Add mapped fields in our standard order
                for std_header in header_mappings.keys():
                    if std_header in header_indices:
                        idx = header_indices[std_header]
                        value = row[idx].strip() if idx < len(row) else ""
                        transaction[std_header] = value
                    else:
                        # If header wasn't found, add empty string to maintain consistent format
                        transaction[std_header] = ""
                        
                if any(transaction.values()):  # Only add if at least one field has data
                    result["transactions"].append(transaction)
    
    return result

def save_results(data, output_file):
    """
    Save formatted results to a JSON file
    Args:
        data (dict): Dictionary containing summary and transactions
        output_file (str): Path to output file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {output_file}")
    print(f"Summary items: {len(data['summary'])}")
    print(f"Transactions: {len(data['transactions'])}")
    
    # Print found headers from first transaction if available
    if data['transactions']:
        print("\nFields found in transactions:")
        for key, value in data['transactions'][0].items():
            if value:  # Only show fields that have data
                print(f"- {key}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python extract_tables_simple.py <job_id> <output_file>")
        sys.exit(1)
        
    job_id = sys.argv[1]
    output_file = sys.argv[2]
    
    print(f"Extracting tables from job {job_id}...")
    tables = get_table_results(job_id)
    print(f"Found {len(tables)} tables")
    
    print("Formatting bank statement data...")
    data = format_bank_statement_data(tables)
    
    save_results(data, output_file)

if __name__ == "__main__":
    main() 