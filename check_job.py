import boto3
import sys
import time
from config import AWS_REGION, CLI_PROFILE_NAME

def check_job_status(job_id):
    """
    Check the status of a Textract job
    Args:
        job_id (str): The job ID to check
    Returns:
        str: The job status
    """
    session = boto3.Session(profile_name=CLI_PROFILE_NAME, region_name=AWS_REGION)
    textract = session.client('textract')
    
    try:
        response = textract.get_document_analysis(JobId=job_id)
        status = response['JobStatus']
        print(f"Job {job_id} status: {status}")
        
        if status == 'SUCCEEDED':
            print(f"Pages processed: {response['DocumentMetadata']['Pages']}")
        elif status == 'FAILED':
            print(f"Error message: {response.get('StatusMessage', 'No error message available')}")
            
        return status
        
    except textract.exceptions.InvalidJobIdException:
        print(f"Error: Job {job_id} not found")
        return 'NOT_FOUND'
    except Exception as e:
        print(f"Error checking job status: {e}")
        return 'ERROR'

def wait_for_job_completion(job_id, check_interval=5):
    """
    Wait for a Textract job to complete
    Args:
        job_id (str): The job ID to monitor
        check_interval (int): How often to check the status in seconds
    Returns:
        str: Final job status
    """
    print(f"Waiting for job {job_id} to complete...")
    dots = 0
    
    while True:
        status = check_job_status(job_id)
        
        if status in ['SUCCEEDED', 'FAILED', 'NOT_FOUND', 'ERROR']:
            return status
            
        # Print progress dots
        if dots < 40:
            print('.', end='', flush=True)
            dots += 1
        else:
            print()
            dots = 0
            
        time.sleep(check_interval)

def main():
    if len(sys.argv) != 2:
        print("Usage: python check_job.py <job_id>")
        sys.exit(1)
        
    job_id = sys.argv[1]
    wait_for_job_completion(job_id)

if __name__ == "__main__":
    main() 