# Document Processor

A Python-based system for processing bank statements using AWS Textract. This system can extract and format transaction data from different bank statement formats into a standardized JSON output.

## Features

- Automated document processing using AWS Textract
- Support for multiple bank statement formats
- AWS SSO authentication support
- Job tracking and status monitoring
- Standardized JSON output format
- Flexible header mapping for different statement layouts

## Prerequisites

- Python 3.6+
- AWS SSO configured with appropriate permissions for:
  - S3
  - Textract
- Virtual environment (recommended)

## Setup

1. Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate # Linux/Mac
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure AWS SSO:
   - Ensure you have AWS CLI v2 installed
   - Configure SSO with: `aws configure sso`
   - Follow the prompts to set up your SSO connection

4. Create a `.env` file with the following variables:

```
AWS_REGION=your-aws-region
CLI_PROFILE_NAME=your-sso-profile-name
INPUT_BUCKET_NAME=your-s3-bucket-name
```

## Usage

1. Activate your virtual environment:

```bash
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate # Linux/Mac
```

2. Start a processing job:

```bash
python main.py <document_name>
```

Example:

```bash
python main.py statement.pdf
```

3. Extract tables when job is complete:

```bash
python extract_tables_simple.py <job_id> <output_file>
```

Example:

```bash
python extract_tables_simple.py abc123... output.json
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

## Components

- `main.py` - Main entry point for starting Textract jobs
- `extract_tables_simple.py` - Table extraction and formatting
- `job_tracker.py` - Job history tracking
- `config.py` - Configuration settings

## AWS Permissions Required

Your AWS SSO role should have the following permissions:

- `s3:GetObject` and `s3:HeadObject` for accessing documents
- `textract:StartDocumentAnalysis` for starting jobs
- `textract:GetDocumentAnalysis` for retrieving results

## Troubleshooting

1. If you get credential errors:
   - Ensure your SSO session is active (`aws sso login`)
   - Check your `.env` file has the correct profile name
   - Verify your AWS region matches your S3 bucket region

2. If document processing fails:
   - Verify the document exists in your S3 bucket
   - Check the document format (PDF, PNG, or JPEG)
   - Ensure your SSO role has sufficient permissions
