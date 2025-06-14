from flask import render_template, request, jsonify, session, redirect, url_for, make_response
from app import app, db
from models import FilterRequest
from brightdata_service import BrightDataService
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)
bright_data = BrightDataService()

@app.route('/')
def index():
    """Main page with filtering form"""
    return render_template('index.html')

@app.route('/filter', methods=['POST'])
def filter_profiles():
    """Start the filtering process"""
    try:
        base_company = request.form.get('base_company', '').strip()
        extra_company = request.form.get('extra_company', '').strip()
        linkedin_url = request.form.get('linkedin_url', '').strip()
        job_title = request.form.get('job_title', '').strip()
        
        if not base_company:
            return jsonify({'error': 'Base company name is required'}), 400
        
        # Check if we have cached results from previous requests
        cached_request = FilterRequest.find_cached_request(
            base_company, extra_company or None, linkedin_url or None, job_title or None
        )
        
        if cached_request:
            logger.info(f"Returning cached results from request ID: {cached_request.id}")
            cached_results = cached_request.get_results()
            
            # Create new filter request record for this cached result
            filter_request = FilterRequest(
                base_company=base_company,
                extra_company=extra_company or None,
                linkedin_url=linkedin_url or None,
                job_title=job_title or None,
                status='completed',
                completed_at=datetime.utcnow(),
                result_count=len(cached_results)
            )
            filter_request.set_results(cached_results)
            db.session.add(filter_request)
            db.session.commit()
            
            # Store results in session
            session[f'results_{filter_request.id}'] = cached_results
            
            return jsonify({
                'success': True,
                'request_id': filter_request.id,
                'cached': True,
                'result_count': len(cached_results)
            })
        
        # Create filter request record for new request
        filter_request = FilterRequest(
            base_company=base_company,
            extra_company=extra_company or None,
            linkedin_url=linkedin_url or None,
            job_title=job_title or None,
            status='filtering'
        )
        db.session.add(filter_request)
        db.session.commit()
        
        # Start filtering process
        snapshot_id = bright_data.filter_dataset(base_company)
        
        if snapshot_id:
            filter_request.snapshot_id = snapshot_id
            filter_request.status = 'building'
            db.session.commit()
            
            return jsonify({
                'success': True,
                'request_id': filter_request.id,
                'snapshot_id': snapshot_id,
                'cached': False
            })
        else:
            filter_request.status = 'failed'
            db.session.commit()
            return jsonify({'error': 'Failed to create dataset filter'}), 500
            
    except Exception as e:
        logger.error(f"Error in filter_profiles: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your request'}), 500

@app.route('/check_status/<int:request_id>')
def check_status(request_id):
    """Check the status of a filter request"""
    try:
        filter_request = FilterRequest.query.get_or_404(request_id)
        
        if filter_request.status == 'building' and filter_request.snapshot_id:
            # Check if snapshot is ready
            is_ready, data_or_message = bright_data.check_snapshot_status(filter_request.snapshot_id)
            
            if is_ready:
                # Download and process data
                filtered_data = bright_data.download_snapshot(filter_request.snapshot_id)
                
                if filtered_data is not None:
                    try:
                        # Apply additional filters
                        matched_profiles = bright_data.apply_additional_filter(
                            filtered_data,
                            filter_request.extra_company or "",
                            filter_request.linkedin_url or "",
                            filter_request.job_title or ""
                        )
                        
                        # Ensure matched_profiles is a list
                        if matched_profiles is None:
                            matched_profiles = []
                        
                        # Store results in session
                        session[f'results_{request_id}'] = matched_profiles
                        
                        # Cache the results for 30 days by storing in database
                        filter_request.set_results(matched_profiles)
                        filter_request.status = 'completed'
                        filter_request.completed_at = datetime.utcnow()
                        db.session.commit()
                        
                        logger.info(f"Cached results for request {request_id}: {len(matched_profiles)} profiles")
                        
                        return jsonify({
                            'status': 'completed',
                            'result_count': len(matched_profiles)
                        })
                    except Exception as filter_error:
                        logger.error(f"Error in additional filtering: {str(filter_error)}")
                        # Return unfiltered data as fallback
                        session[f'results_{request_id}'] = filtered_data
                        filter_request.set_results(filtered_data)
                        filter_request.status = 'completed'
                        filter_request.completed_at = datetime.utcnow()
                        db.session.commit()
                        
                        return jsonify({
                            'status': 'completed',
                            'result_count': len(filtered_data)
                        })
                else:
                    return jsonify({'status': 'building'})
            else:
                return jsonify({'status': 'building'})
        
        return jsonify({'status': filter_request.status})
        
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}")
        return jsonify({'error': 'Error checking status'}), 500

@app.route('/results/<int:request_id>')
def results(request_id):
    """Display results page"""
    try:
        filter_request = FilterRequest.query.get_or_404(request_id)
        
        if filter_request.status != 'completed':
            return redirect(url_for('index'))
        
        # Get results from session first, fallback to database
        results_data = session.get(f'results_{request_id}')
        if not results_data:
            results_data = filter_request.get_results()
        
        return render_template('results.html', 
                             filter_request=filter_request,
                             profiles=results_data,
                             total_count=len(results_data))
                             
    except Exception as e:
        logger.error(f"Error displaying results: {str(e)}")
        return redirect(url_for('index'))

@app.route('/download/<int:request_id>')
def download_results(request_id):
    """Download results as JSON file"""
    try:
        filter_request = FilterRequest.query.get_or_404(request_id)
        
        if filter_request.status != 'completed':
            return jsonify({'error': 'Results not ready'}), 400
        
        # Get results from session first, fallback to database
        results_data = session.get(f'results_{request_id}')
        if not results_data:
            results_data = filter_request.get_results()
        
        # Create response
        response = make_response(json.dumps(results_data, indent=2))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename=matched_profiles_{request_id}.json'
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading results: {str(e)}")
        return jsonify({'error': 'Error downloading results'}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('index.html'), 500
