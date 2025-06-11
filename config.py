import json

# AWS Configuration
AWS_REGION = 'eu-central-1'
CLI_PROFILE_NAME = 'ayem'

# S3 Bucket Configuration
INPUT_BUCKET_NAME = 'input-textract-bucket-ayemdanm'

# IAM Role Configuration
ROLE_ARN = 'arn:aws:iam::288518841645:role/aws-reserved/sso.amazonaws.com/eu-central-1/AWSReservedSSO_AdministratorAccess_96dd29b7bba829e2'

# Table Configuration
TABLE_CONFIG = {
    # Bank statement configuration
    "bank_statement": {
        "summary_table": {
            "required_headers": ["Account Name", "Account No", "Begin Balance"],
            "optional_headers": ["Begin Balance Date", "End Balance", "End Balance Date"]
        },
        "transaction_table": {
            "required_headers": ["Create Date", "Effective Date", "Description/Payee/Memo", "Balance"],
            "optional_headers": ["Check No", "Debit Amount", "Credit Amount", "Reference"]
        }
    }
    # Add more document types here as needed
} 