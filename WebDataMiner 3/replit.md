# Web3leads - Professional Profile Intelligence

## Overview
A sophisticated Flask web application branded as "Web3leads" for filtering and analyzing professional profile data with advanced intelligence tools. The system processes LinkedIn profiles from CSV data sources, focusing on precise professional profile filtering with intelligent executive role inference and category-based job title search.

**Current State**: Production-ready with Web3leads branding, CSV data integration, enhanced filtering algorithms, and category-based job title filtering.

## Key Technologies
- Flask web framework with SQLAlchemy ORM
- PostgreSQL database for caching and persistence
- Pandas for CSV data processing
- Advanced profile matching algorithms
- Bootstrap dark theme UI

## Recent Changes

### December 14, 2025
- **Brand Update**: Rebranded application to "Web3leads - Professional Profile Intelligence"
- **Enhanced Job Title Filtering**: Replaced real-time filtering with category-based search system
- **Search Categories**: Added 12 job title categories (Executive, Engineering, Marketing, Sales, etc.)
- **Custom Title Support**: Users can select categories or enter custom job titles with dedicated search button
- **Improved UX**: Category dropdown with descriptions and manual search initiation
- **Duplicate Removal**: Maintained deduplication system (166 → 82 unique profiles)
- **CSV Integration**: Continued instant processing of 2,559 profiles from local CSV file

### December 12, 2025
- **Executive Inclusion Fix**: Implemented special handling for profiles with company matches but incomplete title data
- **Raagulan Pathy Issue Resolved**: Enhanced position field fallback for CEO/Founder searches
- **Exact LinkedIn URL Matching**: Distinguished between company identifiers like "kastofficial" vs "kast"
- **Cache Management**: Added ability to clear cached results for fresh data processing

## Project Architecture

### Core Components
- `app.py`: Flask application initialization with database configuration
- `csv_data_service.py`: CSV data processing and filtering engine
- `routes.py`: Web endpoints for filtering, status checking, and results display
- `models.py`: Database models for filter requests and caching
- `templates/`: HTML templates with Bootstrap dark theme
- `static/`: CSS and JavaScript assets

### Data Processing Flow  
1. **Input**: User submits company name and LinkedIn URL filters via simplified interface
2. **CSV Processing**: CSVDataService loads and filters 2,559 profiles from attached CSV
3. **Advanced Filtering**: Applies company matching, LinkedIn URL validation, and duplicate removal
4. **Category Search**: Users select job title categories or enter custom titles for targeted filtering
5. **Ranking System**: Results ranked by relevance scores based on title matching algorithms
6. **Executive Inference**: Special handling for CEO/Founder searches with incomplete data
7. **Caching**: Results stored in PostgreSQL for 30-day cache validity
8. **Display**: Filtered results with dynamic job title search and download options

### Filtering Logic
- **Company Matching**: Exact company name and LinkedIn URL correlation  
- **Duplicate Removal**: Name and company-based deduplication for unique results
- **Job Title Categories**: 12 predefined categories with expanded keyword matching
  - Executive, Engineering, Marketing, Sales, Finance, Operations, HR, Product, Design, Data, Consulting, Management
- **Custom Title Search**: Manual title entry with category expansion algorithms
- **Relevance Ranking**: Scoring system for exact matches, partial matches, and keyword relevance
- **Executive Role Inference**: Includes profiles with perfect company matches but missing titles
- **Position Field Fallback**: Checks position field when other title fields are empty

## Database Schema
- `filter_request`: Stores filtering parameters and cached results
- Supports JSON result storage with 30-day cache validation
- PostgreSQL with connection pooling and pre-ping health checks

## User Preferences
- Professional, technical communication style
- Focus on data integrity and authentic results
- Immediate feedback on filtering accuracy
- Comprehensive documentation of architectural changes

## Deployment Notes
- Runs on Gunicorn with auto-reload for development
- Configured for 0.0.0.0:5000 binding
- Session management for large result sets
- Error handling with graceful fallbacks

## API Endpoints
- `POST /filter`: Submit filtering request (immediate CSV processing)
- `GET /check_status/<id>`: Check request completion status
- `GET /results/<id>`: Display filtered profile results
- `GET /download/<id>`: Download results as JSON

## Data Source
- **File**: `attached_assets/output_with_titles_and_links_1749932632525.csv`
- **Records**: 2,559 LinkedIn profiles
- **Fields**: name, current_company, experience, position, title, LinkedIn URLs, locations
- **Processing**: Real-time filtering with pandas DataFrame operations

## Performance Metrics
- **Abound Director Search**: 20 matches from 2,559 profiles
- **CEO Search**: 177 matches with executive role inference
- **Processing Time**: Immediate (no API delays)
- **Cache Hit Rate**: 30-day validity for repeated queries

## Technical Decisions
- **CSV over API**: Eliminates external dependencies and provides consistent data access
- **Immediate Processing**: Simplified workflow removes async complexity
- **Enhanced Matching**: Maintains sophisticated filtering logic for accurate results
- **Executive Handling**: Special case logic for leadership profiles with incomplete data