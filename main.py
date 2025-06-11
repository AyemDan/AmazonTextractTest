import boto3
import json
import sys
import time
from config import AWS_REGION, CLI_PROFILE_NAME, INPUT_BUCKET_NAME, ROLE_ARN
from job_tracker import JobTracker


class ProcessType:
    DETECTION = 1
    ANALYSIS = 2


class DocumentProcessor:
    def __init__(self, role, bucket, document, region):
        self.jobId = ''
        self.roleArn = role
        self.bucket = bucket
        self.document = document
        self.region_name = region if region else AWS_REGION

        # Create a session using AWS profile
        session = boto3.Session(profile_name=CLI_PROFILE_NAME, region_name=self.region_name)
        
        # Initialize AWS clients
        self.textract = session.client('textract')
        self.sqs = session.client('sqs')
        self.sns = session.client('sns')
        self.s3 = session.client('s3')

        # Initialize other attributes
        self.sqsQueueUrl = ''
        self.snsTopicArn = ''
        self.processType = ''
        
        # Initialize job tracker
        self.tracker = JobTracker()

    def ProcessDocument(self, type):
        """Process a document using Textract with progress tracking"""
        jobFound = False
        self.processType = type
        validType = False

        print(f"Using bucket: {self.bucket}")
        print(f"Document name: {self.document}")
        print(f"Role ARN: {self.roleArn}")

        # Create SNS topic and SQS queue
        self.CreateTopicandQueue()
        print(f"Created SNS topic: {self.snsTopicArn}")
        print(f"Created SQS queue: {self.sqsQueueUrl}")

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
                    },
                    NotificationChannel={
                        'RoleArn': self.roleArn,
                        'SNSTopicArn': self.snsTopicArn
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
                    FeatureTypes=["TABLES", "FORMS"],
                    NotificationChannel={
                        'RoleArn': self.roleArn,
                        'SNSTopicArn': self.snsTopicArn
                    }
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

            # Wait for job completion
            dotLine = 0
            while not jobFound:
                sqsResponse = self.sqs.receive_message(
                    QueueUrl=self.sqsQueueUrl,
                    MessageAttributeNames=['ALL'],
                    MaxNumberOfMessages=10
                )

                if sqsResponse:
                    if 'Messages' not in sqsResponse:
                        if dotLine < 40:
                            print('.', end='')
                            dotLine = dotLine + 1
                        else:
                            print()
                            dotLine = 0
                        sys.stdout.flush()
                        time.sleep(5)
                        continue

                    for message in sqsResponse['Messages']:
                        notification = json.loads(message['Body'])
                        textMessage = json.loads(notification['Message'])
                        print(f"\nJob ID: {textMessage['JobId']}")
                        print(f"Status: {textMessage['Status']}")
                        
                        if str(textMessage['JobId']) == self.jobId:
                            print('Matching Job Found: ' + textMessage['JobId'])
                            jobFound = True
                            
                            # Update job status
                            self.tracker.update_job_status(self.jobId, textMessage['Status'])
                            
                            if textMessage['Status'] == 'SUCCEEDED':
                                self.GetResults(textMessage['JobId'])
                            
                            self.sqs.delete_message(
                                QueueUrl=self.sqsQueueUrl,
                                ReceiptHandle=message['ReceiptHandle']
                            )
                        else:
                            print(f"Job didn't match: {textMessage['JobId']} : {self.jobId}")
                        
                        # Delete processed message
                        self.sqs.delete_message(
                            QueueUrl=self.sqsQueueUrl,
                            ReceiptHandle=message['ReceiptHandle']
                        )

            print('Done!')
            
        except Exception as e:
            print(f"Error in document processing: {e}")
            self.tracker.update_job_status(self.jobId, "FAILED")
        finally:
            # Clean up resources
            self.DeleteTopicandQueue()

    def CreateTopicandQueue(self):
        """Create SNS topic and SQS queue for notifications"""
        millis = str(int(round(time.time() * 1000)))

        # Create SNS topic
        snsTopicName = "AmazonTextractTopic" + millis
        topicResponse = self.sns.create_topic(Name=snsTopicName)
        self.snsTopicArn = topicResponse['TopicArn']

        # Create SQS queue
        sqsQueueName = "AmazonTextractQueue" + millis
        self.sqs.create_queue(QueueName=sqsQueueName)
        self.sqsQueueUrl = self.sqs.get_queue_url(QueueName=sqsQueueName)['QueueUrl']

        # Get queue ARN
        attribs = self.sqs.get_queue_attributes(
            QueueUrl=self.sqsQueueUrl,
            AttributeNames=['QueueArn']
        )['Attributes']
        sqsQueueArn = attribs['QueueArn']

        # Subscribe SQS queue to SNS topic
        self.sns.subscribe(
            TopicArn=self.snsTopicArn,
            Protocol='sqs',
            Endpoint=sqsQueueArn
        )

        # Set up queue policy
        policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "MyPolicy",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "SQS:SendMessage",
                "Resource": sqsQueueArn,
                "Condition": {
                    "ArnEquals": {
                        "aws:SourceArn": self.snsTopicArn
                    }
                }
            }]
        }

        self.sqs.set_queue_attributes(
            QueueUrl=self.sqsQueueUrl,
            Attributes={
                'Policy': json.dumps(policy)
            }
        )

    def DeleteTopicandQueue(self):
        """Clean up SNS topic and SQS queue"""
        try:
            self.sqs.delete_queue(QueueUrl=self.sqsQueueUrl)
            self.sns.delete_topic(TopicArn=self.snsTopicArn)
        except Exception as e:
            print(f"Error cleaning up resources: {e}")

    def DisplayBlockInfo(self, block):
        """Display detailed information about a Textract block"""
        print(f"Block Id: {block['Id']}")
        print(f"Type: {block['BlockType']}")
        
        if 'EntityTypes' in block:
            print(f"EntityTypes: {block['EntityTypes']}")

        if 'Text' in block:
            print(f"Text: {block['Text']}")

        if block['BlockType'] != 'PAGE' and "Confidence" in block:
            print(f"Confidence: {block['Confidence']:.2f}%")

        print(f"Page: {block['Page']}")

        if block['BlockType'] == 'CELL':
            print('Cell Information')
            print(f"\tColumn: {block['ColumnIndex']}")
            print(f"\tRow: {block['RowIndex']}")
            print(f"\tColumn span: {block['ColumnSpan']}")
            print(f"\tRow span: {block['RowSpan']}")

            if 'Relationships' in block:
                print(f"\tRelationships: {block['Relationships']}")

        if 'Geometry' in block:
            print('Geometry')
            print(f"\tBounding Box: {block['Geometry']['BoundingBox']}")
            print(f"\tPolygon: {block['Geometry']['Polygon']}")

        if block['BlockType'] == 'SELECTION_ELEMENT':
            status = 'Selected' if block['SelectionStatus'] == 'SELECTED' else 'Not selected'
            print(f"Selection element detected: {status}")

        if block['BlockType'] == 'QUERY':
            print("Query info:")
            print(block['Query'])
        
        if block['BlockType'] == 'QUERY_RESULT':
            print("Query answer:")
            print(block['Text'])

    def GetResults(self, jobId):
        """Get and display results from Textract job"""
        maxResults = 1000
        paginationToken = None
        finished = False

        while not finished:
            # Get appropriate response based on process type
            if self.processType == ProcessType.ANALYSIS:
                response = self.textract.get_document_analysis(
                    JobId=jobId,
                    MaxResults=maxResults,
                    NextToken=paginationToken if paginationToken else None
                )
            else:  # ProcessType.DETECTION
                response = self.textract.get_document_text_detection(
                    JobId=jobId,
                    MaxResults=maxResults,
                    NextToken=paginationToken if paginationToken else None
                )

            # Process blocks
            blocks = response['Blocks']
            print('\nDetected Document Text')
            print(f"Pages: {response['DocumentMetadata']['Pages']}")

            # Display block information
            for block in blocks:
                self.DisplayBlockInfo(block)
                print('\n')

            # Handle pagination
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
        role=ROLE_ARN,
        bucket=INPUT_BUCKET_NAME,
        document=document,
        region=AWS_REGION
    )
    
    # Process document with Analysis type
    processor.ProcessDocument(ProcessType.ANALYSIS)

if __name__ == "__main__":
    main() 