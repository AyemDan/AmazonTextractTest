import json
from datetime import datetime
import os

class JobTracker:
    def __init__(self, tracker_file="textract_jobs.json"):
        self.tracker_file = tracker_file
        self.jobs = self._load_jobs()

    def _load_jobs(self):
        """Load existing jobs from tracker file"""
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []

    def add_job(self, job_id, file_name, document_type="bank_statement"):
        """Add a new job to the tracker"""
        job_info = {
            "job_id": job_id,
            "file_name": file_name,
            "document_type": document_type,
            "start_time": datetime.now().isoformat(),
            "output_file": f"{document_type}_data.json"
        }
        
        self.jobs.append(job_info)
        self._save_jobs()
        return job_info

    def get_job(self, job_id):
        """Get information about a specific job"""
        for job in self.jobs:
            if job["job_id"] == job_id:
                return job
        return None

    def get_jobs_for_file(self, file_name):
        """Get all jobs associated with a specific file"""
        return [job for job in self.jobs if job["file_name"] == file_name]

    def update_job_status(self, job_id, status, output_file=None):
        """Update the status of a job"""
        for job in self.jobs:
            if job["job_id"] == job_id:
                job["status"] = status
                job["last_updated"] = datetime.now().isoformat()
                if output_file:
                    job["output_file"] = output_file
                self._save_jobs()
                return True
        return False

    def _save_jobs(self):
        """Save jobs to tracker file"""
        with open(self.tracker_file, 'w') as f:
            json.dump(self.jobs, f, indent=2)

    def get_recent_jobs(self, limit=10):
        """Get the most recent jobs"""
        return sorted(
            self.jobs,
            key=lambda x: x.get("start_time", ""),
            reverse=True
        )[:limit] 