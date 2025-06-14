#!/usr/bin/env python3

import pandas as pd
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import ast
import os

logger = logging.getLogger(__name__)

class CSVDataService:
    """Service class for reading and filtering LinkedIn profile data from CSV file"""
    
    def __init__(self, csv_file_path: str = "attached_assets/output_with_titles_and_links_1749932632525.csv"):
        self.csv_file_path = csv_file_path
        self.data = None
        self._load_data()
    
    def _load_data(self):
        """Load and preprocess the CSV data"""
        try:
            if not os.path.exists(self.csv_file_path):
                logger.error(f"CSV file not found: {self.csv_file_path}")
                self.data = pd.DataFrame()
                return
            
            # Read CSV with proper handling of complex fields
            self.data = pd.read_csv(self.csv_file_path)
            logger.info(f"Loaded {len(self.data)} profiles from CSV")
            
            # Clean and preprocess data
            self.data = self.data.fillna('')
            
            # Parse JSON-like string fields
            for col in ['current_company', 'experience']:
                if col in self.data.columns:
                    self.data[col] = self.data[col].apply(self._safe_parse_json)
            
            logger.info(f"Preprocessed CSV data successfully")
            
        except Exception as e:
            logger.error(f"Error loading CSV data: {str(e)}")
            self.data = pd.DataFrame()
    
    def _safe_parse_json(self, value):
        """Safely parse JSON-like strings"""
        if not value or value == '':
            return {}
        
        try:
            # Handle string representations of Python dictionaries/lists
            if isinstance(value, str):
                # Try to evaluate as Python literal
                return ast.literal_eval(value)
            return value
        except (ValueError, SyntaxError):
            try:
                # Try JSON parsing as fallback
                return json.loads(value)
            except json.JSONDecodeError:
                logger.debug(f"Could not parse value: {value[:100]}...")
                return {}
    
    def normalize_linkedin_url(self, url):
        """Remove https://www. and trailing slashes from LinkedIn URL."""
        if not url:
            return ""
        
        # Remove protocol and www
        normalized = url.lower()
        normalized = normalized.replace("https://www.", "")
        normalized = normalized.replace("https://", "")
        normalized = normalized.replace("http://www.", "")
        normalized = normalized.replace("http://", "")
        normalized = normalized.replace("www.", "")
        
        # Remove trailing slash
        normalized = normalized.rstrip("/")
        
        return normalized
    
    def get_expanded_job_titles(self, input_title: str) -> List[str]:
        """
        Get all job titles in the same category as the input title.
        Returns list of titles to match against, including the original input.
        """
        if not input_title:
            return []
        
        input_lower = input_title.lower().strip()
        
        # Job title categories with expanded matches
        title_categories = {
            "executive": ["ceo", "founder", "co-founder", "co founder", "owner", "president", "partner", "chief executive officer", "cofounder"],
            "engineering": ["engineer", "developer", "programmer", "architect", "technical lead", "tech lead", "software engineer", "senior engineer", "principal engineer", "staff engineer"],
            "marketing": ["marketing", "marketer", "marketing manager", "marketing director", "marketing specialist", "brand manager", "digital marketing", "content marketing"],
            "sales": ["sales", "sales manager", "sales director", "sales representative", "account manager", "business development", "sales executive"],
            "finance": ["finance", "financial", "accountant", "accounting", "cfo", "chief financial officer", "financial analyst", "finance manager"],
            "operations": ["operations", "operations manager", "ops", "operational", "operations director", "operations specialist"],
            "hr": ["hr", "human resources", "people", "talent", "recruiter", "recruitment", "hr manager", "people manager"],
            "product": ["product", "product manager", "product director", "product owner", "product specialist", "product lead"],
            "design": ["design", "designer", "ux", "ui", "user experience", "user interface", "creative", "graphic designer", "product designer"],
            "data": ["data", "analyst", "data analyst", "data scientist", "analytics", "business analyst", "data engineer"],
            "consulting": ["consultant", "consulting", "advisor", "advisory", "strategist", "strategy"],
            "management": ["manager", "director", "head of", "vp", "vice president", "chief", "lead", "supervisor"]
        }
        
        # Find which category the input title belongs to
        for category, titles in title_categories.items():
            if any(title in input_lower for title in titles):
                logger.info(f"Input title '{input_title}' matched category '{category}' with {len(titles)} expanded titles")
                return titles
        
        # If no category match, return the original title
        return [input_lower]
    
    def title_matches_any(self, display_title: str, expanded_titles: List[str]) -> bool:
        """
        Check if display_title contains any of the expanded job titles.
        """
        if not display_title or not expanded_titles:
            return False
        
        display_lower = display_title.lower()
        return any(title in display_lower for title in expanded_titles)
    
    def filter_profiles(self, company_name: str = "", linkedin_url: str = "", job_title: str = "") -> List[Dict[str, Any]]:
        """
        Filter profiles based on company name, LinkedIn URL, and job title
        Returns list of matching profiles
        """
        if self.data is None or self.data.empty:
            logger.error("No data available for filtering")
            return []
        
        # Convert to list of dictionaries for processing
        profiles = self.data.to_dict('records')
        
        return self.apply_additional_filter(profiles, company_name, linkedin_url, job_title)
    
    def apply_additional_filter(self, profiles: List[Dict[str, Any]], 
                              extra_company: str = "", 
                              linkedin_url: str = "", 
                              job_title: str = "") -> List[Dict[str, Any]]:
        """
        Apply additional filters with the correct flow:
        1. Check experience for company name AND linkedin match
        2. If none, check current_company for company name AND linkedin match
        3. Check current_company_name for name matching
        4. For title display, use only title from current_company if matched there
        """
        if not profiles:
            return []
            
        matched = []

        input_company = extra_company.strip().lower() if extra_company else ""
        normalized_linkedin = self.normalize_linkedin_url(linkedin_url) if linkedin_url else ""
        input_title = job_title.strip().lower() if job_title else ""

        # Get expanded job titles based on category matching
        expanded_titles = self.get_expanded_job_titles(job_title) if job_title else []

        logger.info(f"Applying filters - Company: '{input_company}', LinkedIn: '{normalized_linkedin}', Title: '{input_title}'")
        if expanded_titles:
            logger.info(f"Expanded titles for matching: {expanded_titles}")

        # If no additional filters are provided, return all profiles
        if not input_company and not normalized_linkedin and not input_title:
            return profiles

        for profile in profiles:
            experiences = profile.get("experience", [])
            if experiences is None:
                experiences = []
            
            # Handle case where experience is a string that needs parsing
            if isinstance(experiences, str):
                experiences = self._safe_parse_json(experiences)
                if not isinstance(experiences, list):
                    experiences = []
            
            # Get current company info
            current_company_name = ""
            current_title = ""
            current_company_linkedin = ""
            
            if "current_company_name" in profile:  # Original format
                current_company_name = str(profile.get("current_company_name", "")).strip().lower()
                current_title = str(profile.get("title", "")).strip()
            
            # Also check current_company field (structured data)
            current_company = profile.get("current_company")
            if isinstance(current_company, str):
                current_company = self._safe_parse_json(current_company)
            
            if isinstance(current_company, dict):
                if not current_company_name:
                    current_company_name = str(current_company.get("name", "")).strip().lower()
                if not current_title:
                    current_title = str(current_company.get("title", "")).strip()
                
                # Check for LinkedIn URL in current company
                company_url = current_company.get("link") or current_company.get("url", "")
                if company_url:
                    current_company_linkedin = self.normalize_linkedin_url(str(company_url))

            profile_name = profile.get("name", "Unknown")
            logger.debug(f"Checking profile: {profile_name}")
            logger.debug(f"Current company: '{current_company_name}', title: '{current_title}'")
            logger.debug(f"Experience count: {len(experiences)}")

            # Step 1: Check experience for company name AND LinkedIn URL match
            experience_match = False
            experience_matched_title = ""
            
            if input_company and normalized_linkedin:
                for i, exp in enumerate(experiences):
                    if isinstance(exp, dict):
                        exp_company = str(exp.get("company", "")).strip().lower()
                        exp_url = exp.get("url") or exp.get("company_linkedin_url", "")
                        exp_linkedin = self.normalize_linkedin_url(str(exp_url))
                        exp_title = str(exp.get("title", "")).strip()
                        
                        logger.debug(f"Experience {i}: company='{exp_company}', linkedin='{exp_linkedin}', title='{exp_title}'")
                        
                        if input_company in exp_company and normalized_linkedin in exp_linkedin:
                            experience_match = True
                            experience_matched_title = exp_title
                            logger.debug(f"Experience match found: {exp_company} + {exp_linkedin}")
                            break
            
            # Step 2: If no experience match, check current_company for company name AND LinkedIn URL
            current_company_match = False
            current_company_matched_title = ""
            
            if not experience_match and input_company and normalized_linkedin:
                if (input_company in current_company_name and 
                    normalized_linkedin in current_company_linkedin):
                    current_company_match = True
                    current_company_matched_title = current_title
                    logger.debug(f"Current company match found: {current_company_name} + {current_company_linkedin}")
            
            # Step 3: Check current_company_name for name matching (if no previous matches)
            current_name_match = False
            current_name_matched_title = ""
            
            if not experience_match and not current_company_match and input_company:
                if input_company in current_company_name:
                    current_name_match = True
                    current_name_matched_title = current_title
                    logger.debug(f"Current company name match found: {current_company_name}")
            
            # Determine if profile has company/linkedin match
            has_company_match = experience_match or current_company_match or current_name_match
            
            # If no company filter provided, include all
            if not input_company and not normalized_linkedin:
                has_company_match = True
            
            # Job title filter using expanded categories
            job_title_match = True
            matched_job_title = ""
            
            if expanded_titles:
                job_title_match = False
                
                # Check current title first against all expanded titles
                if current_title and self.title_matches_any(current_title, expanded_titles):
                    job_title_match = True
                    matched_job_title = current_title  # Use full current title
                    logger.debug(f"Job title match in current title: {current_title}")
                
                # If not found in current title, check experience titles
                if not job_title_match:
                    for exp in experiences:
                        if isinstance(exp, dict):
                            exp_title = str(exp.get("title", "")).strip()
                            if exp_title and self.title_matches_any(exp_title, expanded_titles):
                                job_title_match = True
                                matched_job_title = exp_title  # Use full experience title
                                logger.debug(f"Job title match in experience: {exp_title}")
                                break
                
                # If still no match, check for position field for executive searches
                if not job_title_match and "position" in profile:
                    position = str(profile.get("position", "")).strip()
                    if position and self.title_matches_any(position, expanded_titles):
                        job_title_match = True
                        matched_job_title = position
                        logger.debug(f"Job title match in position field: {position}")
            
            # Step 4: For display title, prioritize current_company title if matched there
            display_title = ""
            if current_company_match or current_name_match:
                display_title = current_company_matched_title or current_name_matched_title
            elif experience_match:
                display_title = experience_matched_title
            elif matched_job_title:
                display_title = matched_job_title
            elif current_title:
                display_title = current_title
            
            # Step 5: Final filter - match expanded job titles with display_title
            final_title_match = True
            executive_role_inference = False
            
            if expanded_titles and display_title:
                final_title_match = self.title_matches_any(display_title, expanded_titles)
                logger.debug(f"Final title filter: expanded titles {expanded_titles} in '{display_title}' = {final_title_match}")
            elif expanded_titles and not display_title:
                # Special case: For executive searches (CEO, Founder, etc.), include profiles 
                # with perfect company matches even if they lack title data
                is_executive_search = any(title in ["ceo", "founder", "co-founder", "cofounder", "owner", "president"] 
                                        for title in expanded_titles)
                
                if is_executive_search and has_company_match and (experience_match or current_company_match):
                    final_title_match = True
                    executive_role_inference = True
                    display_title = "Executive Role (CEO/Founder)"
                    logger.debug(f"Executive role inference: including profile with company match but missing title data")
                else:
                    final_title_match = False
                    logger.debug(f"Final title filter: no display title available for expanded titles {expanded_titles}")
            
            # Include profile if it passes all filters including the final title match
            if has_company_match and job_title_match and final_title_match:
                # Create a clean profile dict with standardized fields
                clean_profile = {
                    "name": profile.get("name", "Unknown"),
                    "url": profile.get("url", ""),
                    "city": profile.get("city", ""),
                    "position": profile.get("position", ""),
                    "avatar": profile.get("avatar", ""),
                    "current_company_name": profile.get("current_company_name", ""),
                    "title": profile.get("title", ""),
                    "experience": experiences,
                    "current_company": current_company if isinstance(current_company, dict) else {},
                    "matched_job_title": display_title,
                    "company_linkedin_link": profile.get("company_linkedin_link", "")
                }
                
                if executive_role_inference:
                    clean_profile["executive_inference"] = True
                
                matched.append(clean_profile)
                logger.debug(f"Profile {profile_name} included in results with title: {display_title}")
            else:
                logger.debug(f"Profile {profile_name} filtered out - Company: {has_company_match}, Title: {job_title_match}, Final Title: {final_title_match}")

        # Remove duplicates based on name and current company
        seen = set()
        unique_profiles = []
        for profile in matched:
            key = (profile.get("name", "").lower().strip(), 
                   profile.get("current_company_name", "").lower().strip())
            if key not in seen:
                seen.add(key)
                unique_profiles.append(profile)

        logger.info(f"Filtered {len(profiles)} profiles -> {len(matched)} matches -> {len(unique_profiles)} unique profiles")
        return unique_profiles