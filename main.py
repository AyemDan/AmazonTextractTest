import boto3
import json
import sys
import time
import os

from job_tracker import JobTracker

# Load environment variables

AWS_REGION = os.getenv('AWS_REGION')
CLI_PROFILE_NAME = os.getenv('CLI_PROFILE_NAME')
INPUT_BUCKET_NAME = os.getenv('INPUT_BUCKET_NAME')
ROLE_ARN = os.getenv('ROLE_ARN')

class ProcessType:
    DETECTION = 1
    ANALYSIS = 2


class DocumentProcessor:
    def __init__(self, bucket, document, region):
        self.jobId = ''
        self.bucket = bucket
        self.document = document
        self.region_name = region if region else AWS_REGION

        # Create a session using AWS profile
        session = boto3.Session(profile_name=CLI_PROFILE_NAME, region_name=self.region_name)

        # Initialize AWS clients
        self.textract = session.client('textract')
        self.s3 = session.client('s3')

        # Initialize job tracker
        self.tracker = JobTracker()

    def ProcessDocument(self, type):
        """Process a document using Textract with direct polling"""
        self.processType = type
        validType = False

        print(f"Using bucket: {self.bucket}")
        print(f"Document name: {self.document}")

        # Verify the document exists in S3
        try:
            self.s3.head_object(Bucket=self.bucket, Key=self.document)
            print(f"Document exists in S3: {self.document}")
        except Exception as e:
            print(f"Error checking document in S3: {e}")
            return

        try:
            # Start appropriate processing type
            if self.processType == ProcessType.DETECTION:
                response = self.textract.start_document_text_detection(
                    DocumentLocation={
                        'S3Object': {
                            'Bucket': self.bucket,
                            'Name': self.document
                        }
                    }
                )
                print('Processing type: Detection')
                validType = True

            elif self.processType == ProcessType.ANALYSIS:
                response = self.textract.start_document_analysis(
                    DocumentLocation={
                        'S3Object': {
                            'Bucket': self.bucket,
                            'Name': self.document
                        }
                    },
                    FeatureTypes=["TABLES", "FORMS"]
                )
                print('Processing type: Analysis')
                validType = True

            if not validType:
                print("Invalid processing type. Choose Detection or Analysis.")
                return

            self.jobId = response['JobId']
            print('Started Job Id: ' + self.jobId)

            # Track the job
            self.tracker.add_job(self.jobId, self.document)

            # Poll for job completion
            print("Waiting for job completion...")
            while True:
                response = self.textract.get_document_analysis(JobId=self.jobId)
                status = response['JobStatus']
                print(f"Status: {status}")
                
                self.tracker.update_job_status(self.jobId, status)
                
                if status in ['SUCCEEDED', 'FAILED']:
                    if status == 'SUCCEEDED':
                        self.GetResults(self.jobId)
                    break
                    
                time.sleep(5)

            print('Done!')

        except Exception as e:
            print(f"Error in document processing: {e}")
            self.tracker.update_job_status(self.jobId, "FAILED")

    def GetResults(self, jobId):
        """Get the results of the text detection/analysis"""
        maxResults = 1000
        paginationToken = None
        finished = False

        while not finished:
            if paginationToken:
                response = self.textract.get_document_analysis(JobId=jobId, MaxResults=maxResults, NextToken=paginationToken)
            else:
                response = self.textract.get_document_analysis(JobId=jobId, MaxResults=maxResults)

            # Process the response here (you can customize this part)
            print(f"Processing page {len(response.get('Blocks', []))} blocks")

            if 'NextToken' in response:
                paginationToken = response['NextToken']
            else:
                finished = True

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <document_name>")
        print("Example: python main.py document.pdf")
        sys.exit(1)

    document = sys.argv[1]

    # Initialize processor with configuration
    processor = DocumentProcessor(
        bucket=INPUT_BUCKET_NAME,
        document=document,
        region=AWS_REGION
    )

    # Process document with Analysis type
    processor.ProcessDocument(ProcessType.ANALYSIS)

if __name__ == "__main__":
    main()