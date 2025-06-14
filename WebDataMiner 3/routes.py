from flask import render_template, request, jsonify, session, redirect, url_for, make_response
from app import app, db
from models import FilterRequest
from csv_data_service import CSVDataService
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

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
        
        # Process data directly using CSV service
        csv_service = CSVDataService()
        
        # Filter profiles immediately using CSV data (no job title filtering at this stage)
        filtered_profiles = csv_service.filter_profiles(
            company_name=base_company,
            linkedin_url=linkedin_url,
            job_title=""  # No job title filtering initially - will be done on results page
        )
        
        # Create filter request record with completed results
        filter_request = FilterRequest(
            base_company=base_company,
            extra_company=extra_company or None,
            linkedin_url=linkedin_url or None,
            job_title=job_title or None,
            status='completed',
            completed_at=datetime.utcnow(),
            result_count=len(filtered_profiles)
        )
        filter_request.set_results(filtered_profiles)
        db.session.add(filter_request)
        db.session.commit()
        
        # Store results in session
        session[f'results_{filter_request.id}'] = filtered_profiles
        
        return jsonify({
            'success': True,
            'request_id': filter_request.id,
            'cached': False,
            'result_count': len(filtered_profiles)
        })
            
    except Exception as e:
        logger.error(f"Error in filter_profiles: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your request'}), 500

@app.route('/check_status/<int:request_id>')
def check_status(request_id):
    """Check the status of a filter request"""
    try:
        filter_request = FilterRequest.query.get_or_404(request_id)
        
        # Since CSV processing is immediate, all requests should be completed
        return jsonify({
            'status': filter_request.status,
            'result_count': filter_request.result_count or 0
        })
        
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
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500