import time
import logging
from datetime import datetime, timedelta
from models import FilterRequest
from brightdata_service import BrightDataService
from app import db, app

logger = logging.getLogger(__name__)

def process_pending_requests():
    """Background processor to check and complete pending API requests"""
    with app.app_context():
        service = BrightDataService()
        
        # Get pending requests older than 30 seconds
        cutoff_time = datetime.utcnow() - timedelta(seconds=30)
        pending_requests = FilterRequest.query.filter(
            FilterRequest.status == 'building',
            FilterRequest.created_at <= cutoff_time
        ).all()
        
        logger.info(f"Processing {len(pending_requests)} pending requests")
        
        for request in pending_requests:
            try:
                # Check snapshot status
                is_ready, status_msg = service.check_snapshot_status(request.snapshot_id)
                
                if is_ready:
                    # Download and process data
                    profiles = service.download_snapshot(request.snapshot_id)
                    
                    if profiles:
                        # Apply additional filters
                        filtered_profiles = service.apply_additional_filter(
                            profiles,
                            extra_company=request.extra_company or "",
                            linkedin_url=request.linkedin_url or "",
                            job_title=request.job_title or ""
                        )
                        
                        # Update request with results
                        request.status = 'completed'
                        request.completed_at = datetime.utcnow()
                        request.result_count = len(filtered_profiles)
                        request.set_results(filtered_profiles)
                        
                        logger.info(f"Request {request.id} completed with {len(filtered_profiles)} results")
                    else:
                        # No data returned
                        request.status = 'failed'
                        request.completed_at = datetime.utcnow()
                        logger.warning(f"Request {request.id} failed - no data returned")
                        
                    db.session.commit()
                    
                elif "error" in status_msg.lower():
                    # Error occurred
                    request.status = 'failed'
                    request.completed_at = datetime.utcnow()
                    db.session.commit()
                    logger.error(f"Request {request.id} failed: {status_msg}")
                    
                # If still building, leave as is
                    
            except Exception as e:
                logger.error(f"Error processing request {request.id}: {str(e)}")
                request.status = 'failed'
                request.completed_at = datetime.utcnow()
                db.session.commit()

if __name__ == "__main__":
    # Run background processor
    while True:
        try:
            process_pending_requests()
        except Exception as e:
            logger.error(f"Background processor error: {str(e)}")
        
        time.sleep(30)  # Check every 30 seconds