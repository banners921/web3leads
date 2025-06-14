from datetime import datetime, timedelta
from app import db
import json
import logging

logger = logging.getLogger(__name__)

class FilterRequest(db.Model):
    """Model for storing filter requests and results with caching capabilities"""
    
    id = db.Column(db.Integer, primary_key=True)
    base_company = db.Column(db.String(255), nullable=False)
    extra_company = db.Column(db.String(255), nullable=True)
    linkedin_url = db.Column(db.String(500), nullable=True)
    job_title = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), nullable=False, default='pending')
    snapshot_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    result_count = db.Column(db.Integer, nullable=True, default=0)
    results_json = db.Column(db.Text, nullable=True)  # Store JSON results
    
    def __repr__(self):
        return f'<FilterRequest {self.id}: {self.base_company}>'
    
    def set_results(self, results):
        """Store results as JSON"""
        if results is not None:
            self.results_json = json.dumps(results)
            self.result_count = len(results) if isinstance(results, list) else 0
        else:
            self.results_json = None
            self.result_count = 0
    
    def get_results(self):
        """Retrieve results from JSON"""
        if self.results_json:
            try:
                return json.loads(self.results_json)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON for request {self.id}")
                return []
        return []
    
    def is_cache_valid(self, cache_days=30):
        """Check if cached results are still valid (default 30 days)"""
        if not self.completed_at:
            return False
        
        expiry_date = self.completed_at + timedelta(days=cache_days)
        return datetime.utcnow() < expiry_date
    
    @classmethod
    def find_cached_request(cls, base_company, extra_company=None, linkedin_url=None, job_title=None):
        """Find a valid cached request with the same parameters"""
        # Temporarily disable caching to ensure new filtering logic is applied
        # This can be re-enabled later once filtering is stable
        return None
        
        query = cls.query.filter(
            cls.base_company == base_company,
            cls.status == 'completed'
        )
        
        # Handle nullable fields properly
        if extra_company is None:
            query = query.filter(cls.extra_company.is_(None))
        else:
            query = query.filter(cls.extra_company == extra_company)
        
        if linkedin_url is None:
            query = query.filter(cls.linkedin_url.is_(None))
        else:
            query = query.filter(cls.linkedin_url == linkedin_url)
        
        if job_title is None:
            query = query.filter(cls.job_title.is_(None))
        else:
            query = query.filter(cls.job_title == job_title)
        
        # Find the most recent valid cached request
        cached_requests = query.order_by(cls.completed_at.desc()).all()
        
        for request in cached_requests:
            if request.is_cache_valid():
                return request
        
        return None