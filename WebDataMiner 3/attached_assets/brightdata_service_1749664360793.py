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
        self.api_key = os.environ.get("BRIGHT_DATA_API_KEY", "08dd9ea6-dc91-40df-9b2d-c6aa3b5f224c")
        self.dataset_id = "gd_l1viktl72bvl7bjuj0"
    
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
        Apply additional filters to handle both original LinkedIn format and Bright Data format:
        - Company name and LinkedIn URL must both match in experience (AND logic)
        - Job title matches in current title or experience titles (partial match)
        """
        if not profiles:
            return []
            
        matched = []

        input_company = extra_company.strip().lower() if extra_company else ""
        normalized_linkedin = self.normalize_linkedin_url(linkedin_url) if linkedin_url else ""
        input_title = job_title.strip().lower() if job_title else ""

        logger.info(f"Applying filters - Company: '{input_company}', LinkedIn: '{normalized_linkedin}', Title: '{input_title}'")

        # If no additional filters are provided, return all profiles
        if not input_company and not normalized_linkedin and not input_title:
            return profiles

        for profile in profiles:
            experiences = profile.get("experience", [])
            if experiences is None:
                experiences = []
            
            # Handle both data formats for current title
            current_title = ""
            if "current_company_title" in profile:  # Original format
                current_title = str(profile.get("current_company_title", "")).strip().lower()
            else:  # Bright Data format
                current_company = profile.get("current_company") or {}
                current_title = str(current_company.get("title", "")).strip().lower()

            # Debug logging for each profile
            profile_name = profile.get("name", "Unknown")
            logger.debug(f"Checking profile: {profile_name}")
            logger.debug(f"Current title: '{current_title}'")
            logger.debug(f"Experience count: {len(experiences)}")

            # Log experience data for debugging - handle both formats
            for i, exp in enumerate(experiences):
                if isinstance(exp, dict):
                    exp_company = str(exp.get("company", "")).strip().lower()
                    exp_linkedin = self.normalize_linkedin_url(str(exp.get("url", "")))
                    logger.debug(f"Experience {i}: company='{exp_company}', linkedin='{exp_linkedin}'")

            # Check for matching experience AND current company - handle both data formats
            has_matching_experience = False
            matched_job_title = ""
            
            # First check current company (both formats)
            if input_company:
                current_company_name = ""
                if "current_company_name" in profile:  # Original format
                    current_company_name = str(profile.get("current_company_name", "")).strip().lower()
                else:  # Bright Data format
                    current_company = profile.get("current_company") or {}
                    current_company_name = str(current_company.get("name", "")).strip().lower()
                
                if current_company_name == input_company:
                    has_matching_experience = True
                    logger.debug(f"Current company match found: {current_company_name}")
                    # Get the current title as matched job title
                    if current_title:
                        matched_job_title = current_title
            
            # If no current company match, check experience history
            if not has_matching_experience:
                if input_company and normalized_linkedin:
                    # Both company and LinkedIn URL must match in the same experience
                    for exp in experiences:
                        if isinstance(exp, dict):
                            exp_company = str(exp.get("company", "")).strip().lower()
                            exp_linkedin = self.normalize_linkedin_url(str(exp.get("url", "")))
                            
                            company_matches = exp_company == input_company
                            linkedin_matches = normalized_linkedin in exp_linkedin
                            
                            logger.debug(f"Company match: {company_matches} ('{exp_company}' == '{input_company}')")
                            logger.debug(f"LinkedIn match: {linkedin_matches} ('{normalized_linkedin}' in '{exp_linkedin}')")
                            
                            if company_matches and linkedin_matches:
                                has_matching_experience = True
                                # Get the experience title as matched job title
                                matched_job_title = str(exp.get("title", "")).strip()
                                logger.debug(f"Experience match found!")
                                break
                elif input_company:
                    # Only company filter provided
                    for exp in experiences:
                        if isinstance(exp, dict):
                            exp_company = str(exp.get("company", "")).strip().lower()
                            if exp_company == input_company:
                                has_matching_experience = True
                                matched_job_title = str(exp.get("title", "")).strip()
                                logger.debug(f"Company-only match found: {exp_company}")
                                break
                elif normalized_linkedin:
                    # Only LinkedIn filter provided
                    for exp in experiences:
                        if isinstance(exp, dict):
                            exp_linkedin = self.normalize_linkedin_url(str(exp.get("url", "")))
                            if normalized_linkedin in exp_linkedin:
                                has_matching_experience = True
                                matched_job_title = str(exp.get("title", "")).strip()
                                logger.debug(f"LinkedIn-only match found: {exp_linkedin}")
                                break
                else:
                    # No experience filters provided
                    has_matching_experience = True

            # Check title match - handle both current title and experience titles (including positions)
            title_match = True
            matched_title_detail = ""
            
            if input_title:
                title_match = False
                
                # Check current company title first
                if current_title and input_title in current_title:
                    title_match = True
                    matched_title_detail = current_title
                    logger.debug(f"Title match found in current title: {current_title}")
                
                # Also check profile.position field (original format)
                if not title_match and profile.get("position"):
                    position_title = str(profile.get("position", "")).strip().lower()
                    if input_title in position_title:
                        title_match = True
                        matched_title_detail = position_title
                        logger.debug(f"Title match found in position field: {position_title}")
                
                # If no current title match, check experience titles
                if not title_match:
                    for exp in experiences:
                        if isinstance(exp, dict):
                            # Check direct title field
                            exp_title = str(exp.get("title", "")).strip().lower()
                            if exp_title and input_title in exp_title:
                                title_match = True
                                matched_title_detail = exp_title
                                logger.debug(f"Title match found in experience: {exp_title}")
                                break
                            
                            # Check positions array (original LinkedIn format)
                            positions = exp.get("positions", [])
                            if positions:
                                for pos in positions:
                                    if isinstance(pos, dict):
                                        pos_title = str(pos.get("title", "")).strip().lower()
                                        if pos_title and input_title in pos_title:
                                            title_match = True
                                            matched_title_detail = pos_title
                                            logger.debug(f"Title match found in position: {pos_title}")
                                            break
                                if title_match:
                                    break
                
                logger.debug(f"Title match: {title_match} ('{input_title}' searched in current and experience titles)")
                
                # Update matched_job_title if we found a title match and didn't have one from experience
                if title_match and not matched_job_title and matched_title_detail:
                    matched_job_title = matched_title_detail

            # Profile matches if experience criteria AND title criteria are met
            if has_matching_experience and title_match:
                # Add the matched job title to the profile for display
                profile_copy = profile.copy()
                if matched_job_title:
                    profile_copy['matched_job_title'] = matched_job_title
                elif current_title:
                    profile_copy['matched_job_title'] = current_title
                else:
                    profile_copy['matched_job_title'] = profile.get('position', '')
                
                matched.append(profile_copy)
                logger.info(f"✓ Profile matched: {profile_name}")
            else:
                logger.debug(f"✗ Profile not matched: {profile_name} (exp:{has_matching_experience}, title:{title_match})")

        logger.info(f"Applied additional filters: {len(matched)} profiles matched out of {len(profiles)}")
        return matched
