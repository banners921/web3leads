import os
import requests
import time
import logging
import json
import re
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class BrightDataService:
    """Service class for interacting with Bright Data API"""
    
    def __init__(self):
        self.api_key = "cb12e00f-5913-4206-a407-12b79e4532fd"
        self.dataset_id = "gd_l1viktl72bvl7bjuj0"
        
        # Job categories for expanded title matching
        self.job_categories = {
            "executive": ["Founder", "Co-founder", "Co Founder", "Owner", "President", "Partner", "CEO", "Chief Executive Officer", "Cofounder"],
            "technology": ["CTO", "Co-CTO", "VP of Engineering", "VP Engineering", "VP-Engineering", "Tech Lead",
                          "Head of Technology", "Chief Technology Officer", "VP Technology", "VP-Technology",
                          "VP of Technology", "Software Engineer", "Senior Software Engineer", "Engineering Lead"],
            "marketing": ["CMO", "Head of Marketing", "VP Marketing", "VP-Marketing", "VP of Marketing",
                         "Growth Hacker", "Marketing Manager", "Chief Marketing Officer", "Marketing Director"],
            "product": ["CPO", "Product Manager", "Head of Product", "Chief Product Officer", "VP Product",
                       "VP-Product", "VP of Product", "Product Lead", "Product Director"],
            "finance": ["CFO", "VP Finance", "VP-Finance", "VP of Finance", "Finance Director",
                       "Chief Financial Officer", "Finance Manager", "Financial Controller"],
            "operations": ["COO", "Head of Operations", "Operations Manager", "Chief Operations Officer",
                          "VP Operations", "VP-Operations", "VP of Operations", "Operations Director"],
            "business_development": ["Business Development", "BD", "Head of BD", "Head of Business Development",
                                   "VP of Business Development", "VP BD", "VP Business Development",
                                   "Business Development Director", "Business Development Manager"],
            "design": ["Creative Director", "Head of Design", "UX Lead", "Design Manager", "Chief Design Officer",
                      "VP Design", "VP of Design", "VP-Design", "UX Director"],
            "hr": ["CHRO", "Head of HR", "People Operations", "Chief HR Officer", "VP HR", "VP of HR",
                  "VP-HR", "HR Director", "People Lead"],
            "data": ["CDO", "Head of Data", "Data Scientist", "Data Analyst", "Chief Data Officer",
                    "VP Data", "VP of Data", "VP-Data", "Data Engineer"]
        }
    
    def filter_dataset(self, company_name: str) -> Optional[str]:
        """
        Create a filtered dataset snapshot for the given company
        Returns snapshot_id if successful, None otherwise
        """
        try:
            url = "https://api.brightdata.com/datasets/filter"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "dataset_id": self.dataset_id,
                "filter": {
                    "operator": "and",
                    "filters": [
                        {
                            "name": "current_company_name",
                            "value": company_name,
                            "operator": "="
                        }
                    ]
                }
            }

            logger.info(f"Creating dataset filter for company: {company_name}")
            response = requests.post(url, headers=headers, json=payload)

            if response.ok:
                snapshot_id = response.json().get("snapshot_id")
                logger.info(f"Filter request successful. Snapshot ID: {snapshot_id}")
                return snapshot_id
            else:
                logger.error(f"Filter request failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating dataset filter: {str(e)}")
            return None
    
    def normalize_linkedin_url(self, url):
        """Remove https://www. and trailing slashes from LinkedIn URL."""
        if not url:
            return ""
        url = str(url).strip().lower()
        # Remove protocol and www
        url = re.sub(r'^https?://(www\.)?', '', url)
        # Remove trailing slash
        url = url.rstrip('/')
        return url
    
    def get_expanded_job_titles(self, input_title: str) -> List[str]:
        """
        Get all job titles in the same category as the input title.
        Returns list of titles to match against, including the original input.
        """
        if not input_title:
            return []
        
        input_title_clean = input_title.strip()
        expanded_titles = [input_title_clean.lower()]  # Always include original
        
        # Find which category the input title belongs to
        for category, titles in self.job_categories.items():
            for title in titles:
                if input_title_clean.lower() in title.lower() or title.lower() in input_title_clean.lower():
                    # Found a match, add all titles from this category
                    for category_title in titles:
                        category_title_lower = category_title.lower()
                        if category_title_lower not in expanded_titles:
                            expanded_titles.append(category_title_lower)
                    logger.info(f"Input title '{input_title}' matched category '{category}' with {len(titles)} expanded titles")
                    return expanded_titles
        
        logger.info(f"Input title '{input_title}' did not match any category, using exact match only")
        return expanded_titles
    
    def title_matches_any(self, display_title: str, expanded_titles: List[str]) -> bool:
        """
        Check if display_title contains any of the expanded job titles.
        """
        if not display_title or not expanded_titles:
            return False
        
        display_title_lower = display_title.lower()
        
        for title in expanded_titles:
            if title in display_title_lower:
                return True
        
        return False
    
    def check_snapshot_status(self, snapshot_id: str) -> Tuple[bool, str]:
        """
        Check if a snapshot is ready for download
        Returns (is_ready, status_message)
        """
        try:
            url = f"https://api.brightdata.com/datasets/snapshots/{snapshot_id}/download"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = requests.get(url, headers=headers)
            
            if response.ok and "Snapshot is building" not in response.text:
                return True, "Snapshot is ready for download"
            else:
                return False, "Snapshot is still building"
                
        except Exception as e:
            logger.error(f"Error checking snapshot status: {str(e)}")
            return False, "Error checking status"
    
    def download_snapshot(self, snapshot_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Download snapshot data
        Returns list of profile data if successful, None otherwise
        """
        try:
            url = f"https://api.brightdata.com/datasets/snapshots/{snapshot_id}/download"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = requests.get(url, headers=headers)
            
            if response.ok and "Snapshot is building" not in response.text:
                logger.info("Snapshot ready. Processing data...")
                try:
                    # If data has multiple JSON objects, split and parse manually
                    raw_objects = response.text.strip().split("\n")
                    data = [json.loads(obj) for obj in raw_objects if obj.strip()]

                    filtered_data = []
                    for d in data:
                        filtered_profile = {
                            "url": d.get("url"),
                            "name": d.get("name"),
                            "city": d.get("city"),
                            "position": d.get("position"),
                            "avatar": d.get("avatar"),
                            "experience": d.get("experience", []),
                            "current_company": {
                                "name": d.get("current_company_name"),
                                "title": d.get("current_company_title")
                            }
                        }
                        filtered_data.append(filtered_profile)

                    # Log sample data structure for debugging
                    if filtered_data:
                        sample = filtered_data[0]
                        logger.info(f"Sample profile structure: {json.dumps(sample, indent=2)}")
                        
                        # Log experience structure specifically
                        if sample.get("experience"):
                            sample_exp = sample["experience"][0] if isinstance(sample["experience"], list) else sample["experience"]
                            logger.info(f"Sample experience structure: {json.dumps(sample_exp, indent=2)}")
                    
                    logger.info(f"Processed {len(filtered_data)} profiles")
                    return filtered_data

                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)}")
                    return []
            else:
                logger.info("Snapshot still building")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading snapshot: {str(e)}")
            return []
    
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
            
            # Get current company info
            current_company_name = ""
            current_title = ""
            current_company_linkedin = ""
            
            if "current_company_name" in profile:  # Original format
                current_company_name = str(profile.get("current_company_name", "")).strip().lower()
                current_title = str(profile.get("current_company_title", "")).strip()
            else:  # Bright Data format
                current_company = profile.get("current_company") or {}
                current_company_name = str(current_company.get("name", "")).strip().lower()
                current_title = str(current_company.get("title", "")).strip()
                current_company_linkedin = self.normalize_linkedin_url(str(current_company.get("url", "")))

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
                        exp_linkedin = self.normalize_linkedin_url(str(exp.get("url", "")))
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
                if display_title:
                    profile["matched_job_title"] = display_title
                    if executive_role_inference:
                        profile["executive_inference"] = True
                matched.append(profile)
                logger.debug(f"Profile {profile_name} included in results with title: {display_title}")
            else:
                logger.debug(f"Profile {profile_name} filtered out - Company: {has_company_match}, Title: {job_title_match}, Final Title: {final_title_match}")

        logger.info(f"Filtered {len(profiles)} profiles -> {len(matched)} matches")
        return matched