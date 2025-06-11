# Bank Statement Processor

A Python-based system for processing bank statements using AWS Textract. This system can extract and format transaction data from different bank statement formats into a standardized JSON output.

## Features

- Automated document processing using AWS Textract
- Support for multiple bank statement formats
- Job tracking and status monitoring
- Standardized JSON output format
- Flexible header mapping for different statement layouts

## Components

- `main.py` - Main entry point for starting Textract jobs
- `check_job.py` - Tool for monitoring job status
- `extract_tables_simple.py` - Table extraction and formatting
- `job_tracker.py` - Job history tracking
- `config.py` - Configuration settings

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure AWS credentials and settings in `config.py`

3. Ensure your AWS account has necessary permissions for:
   - S3
   - Textract
   - SNS
   - SQS

## Usage

1. Start a processing job:
```bash
python main.py <document_name>
```

2. Check job status:
```bash
python check_job.py <job_id>
```

3. Extract tables when job is complete:
```bash
python extract_tables_simple.py <job_id> <output_file>
```

## Output Format

The system produces a JSON file with two main sections:

1. Summary - Contains account information and statement metadata
2. Transactions - List of transactions with standardized fields:
   - Date
   - Reference
   - Description
   - Value Date
   - Deposit
   - Withdrawal
   - Balance

## Requirements

- Python 3.6+
- boto3
- AWS Account with appropriate permissions
- Configured AWS credentials 