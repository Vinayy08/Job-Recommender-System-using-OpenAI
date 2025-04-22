import logging
import math
import os , re
from django.conf import settings
import pandas as pd
import matplotlib.pyplot as plt
from .models import Job, UserProfile
from fuzzywuzzy import fuzz  # For education matching
from .helpers import preprocess_text, extract_text_from_file

# Directories for caching and reports
CACHE_DIR = os.path.join(settings.BASE_DIR, 'main', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

REPORTS_DIR = os.path.join(settings.STATICFILES_DIRS[0], 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logging.getLogger('matplotlib').setLevel(logging.ERROR)

EXCLUDED_USERS = ["vinaybharadwaj", "admin"]


# Use Django's MEDIA_ROOT which is already defined in your settings.py
BASE_RESUME_PATH = os.path.join(settings.MEDIA_ROOT, "resumes")
DEFAULT_RESUME_PATH = os.path.join(BASE_RESUME_PATH, 'default_resume.pdf')
os.makedirs(BASE_RESUME_PATH, exist_ok=True)



def validate_file_path(file_path):
    if not os.path.exists(file_path):
        print(f"Error: Resume file not found: {file_path}")
        return False
    return True


def compare_resume_with_job(resume_details, job_details):
    """
    Compare resume details with job requirements and calculate compatibility scores.
    """
    try:
        # Normalize education for comparison purposes
        resume_educations = normalize_education(resume_details["education"])
        job_educations = normalize_education(job_details["education"])
        
        # Education comparison using normalized education (keep this as is)
        education_match = compare_education(
            resume_details["education"], 
            job_details["education"]
        )

        # Rest of the function remains the same
        # Extract minimum required experience from the job details (handle experience ranges)
        job_experience = extract_min_experience(job_details["experience"])

        # If employee's experience is greater than or equal to the required experience, give full match
        if resume_details["experience_years"] >= job_experience:
            experience_match = 1.0  # 100%
        elif resume_details["experience_years"] > 0 and resume_details["experience_years"] < job_experience:
            experience_match = (resume_details["experience_years"] / job_experience) * 1.0  # Between 0 and 1
        else:
            experience_match = 0.0  # 0%

        # Skill comparison
        skills_required = set(job_details["skills"])
        skills_provided = set(resume_details["skills"])
        matched_skills = skills_required & skills_provided
        skills_score = (len(matched_skills) / len(skills_required)) if skills_required else 0.0  # Between 0 and 1

        # Identify missing skills
        missing_skills = skills_required - skills_provided

        # Overall compatibility - ensure this continues to work
        overall_score = calculate_overall_score(education_match, skills_score, experience_match)
        
        # Join normalized educations for internal reference
        resume_std_education = "; ".join(resume_educations) if resume_educations else "Not Specified"
        job_std_education = "; ".join(job_educations) if job_educations else "Not Specified"
        
        # Format education for display
        resume_formatted_education = format_education(resume_details["education"])
        job_formatted_education = format_education(job_details["education"])
        
        # Use formatted education for display in the compatibility matrix
        criteria = [
            {"Criteria": "Education",
             "Resume_Details": resume_formatted_education if resume_formatted_education else resume_std_education,
             "Job_Description_Requirements": job_formatted_education if job_formatted_education else job_std_education,
             "Match": "Yes" if education_match >= 0.8 else "No",
             "Comments": "Matches" if education_match >= 0.8 else "Mismatch"
            },
            {"Criteria": "Experience (Years)",
             "Resume_Details": resume_details["experience_years"] if resume_details["experience_years"] > 0 else "0 years",
             "Job_Description_Requirements": job_experience if job_experience > 0 else "0 years",
             "Match": "Yes" if experience_match >= 0.8 else "No",
             "Comments": "Matches" if experience_match >= 0.8 else "Experience mismatch"
            }
        ]

        # Add all skills to the compatibility matrix (including those that are missing)
        for skill in skills_required:
            resume_skill = skill if skill in skills_provided else "Not Specified"
            match_status = "Yes" if skill in skills_provided else "No"
            comments = "Matches" if skill in skills_provided else "Missing"

            # Add skill to the compatibility matrix even if missing
            criteria.append({
                "Criteria": skill,
                "Resume_Details": resume_skill,
                "Job_Description_Requirements": skill,
                "Match": match_status,
                "Comments": comments
            })

        # Upskill recommendation for missing skills
        if missing_skills:
            upskill_recommendation = ", ".join(missing_skills)
            recommendation_text = f"Upskill in: {upskill_recommendation}. Pursue certifications or additional education to match job requirements."
        else:
            recommendation_text = "All required skills are present. No upskill needed."

        logger.debug(f"Compatibility Matrix: {criteria}")
        logger.debug(f"Overall Compatibility Score: {overall_score}")

        # Round all percentage scores to 2 decimal places
        scores = {
            "education_compatibility": round(education_match * 100, 2),  # Round to 2 decimal places
            "skills_compatibility": round(skills_score * 100, 2),  # Round to 2 decimal places
            "experience_compatibility": round(experience_match * 100, 2),  # Round to 2 decimal places
            "overall_compatibility": round(overall_score * 100, 2),  # Already rounded but ensure consistency
            "recommendation": recommendation_text
        }

        # Log final output before returning
        logger.debug(f"Returning from compare_resume_with_job: {criteria}, {scores}")
        return criteria, scores

    except Exception as e:
        logger.error(f"Error comparing resume with job: {e}")
        # Log what is being returned on error
        logger.debug("Returning default values due to error.")
        return [], {
            "education_compatibility": 0, 
            "skills_compatibility": 0, 
            "experience_compatibility": 0, 
            "overall_compatibility": 0, 
            "recommendation": "An error occurred. Unable to calculate compatibility."
        }


def format_education(education_data):
    """Convert education data to a formatted string"""
    if not education_data:
        return ""
    
    # Handle exact string representation like "[{'degree': 'Bachelor of Science in Computer Science'}]"
    if isinstance(education_data, str) and education_data.startswith('[') and education_data.endswith(']'):
        try:
            # Replace single quotes with double quotes for valid JSON
            import json
            json_str = education_data.replace("'", '"')
            edu_list = json.loads(json_str)
            
            formatted_text = ""
            for edu in edu_list:
                if isinstance(edu, dict):
                    degree = edu.get('degree', '')
                    institution = edu.get('institution', '')
                    year = edu.get('year', '')
                    
                    if degree:
                        formatted_text += f"{degree}"
                        if institution and institution.lower() != 'not specified':
                            formatted_text += f" from {institution}"
                        if year:
                            formatted_text += f" ({year})"
                        formatted_text += "\n"
                elif isinstance(edu, str):
                    formatted_text += f"{edu}\n"
            
            return formatted_text.strip()
        except json.JSONDecodeError:
            try:
                # Fall back to ast.literal_eval for Python list syntax
                import ast
                edu_list = ast.literal_eval(education_data)
                
                formatted_text = ""
                for edu in edu_list:
                    if isinstance(edu, dict):
                        degree = edu.get('degree', '')
                        institution = edu.get('institution', '')
                        year = edu.get('year', '')
                        
                        if degree:
                            formatted_text += f"{degree}"
                            if institution and institution.lower() != 'not specified':
                                formatted_text += f" from {institution}"
                            if year:
                                formatted_text += f" ({year})"
                            formatted_text += "\n"
                    elif isinstance(edu, str):
                        formatted_text += f"{edu}\n"
                
                return formatted_text.strip()
            except (ValueError, SyntaxError):
                pass
    
    # If it's already a list of dictionaries
    if isinstance(education_data, list):
        formatted_text = ""
        for edu in education_data:
            if isinstance(edu, dict):
                degree = edu.get('degree', '')
                institution = edu.get('institution', '')
                year = edu.get('year', '')
                
                if degree:
                    formatted_text += f"{degree}"
                    if institution and institution.lower() != 'not specified':
                        formatted_text += f" from {institution}"
                    if year:
                        formatted_text += f" ({year})"
                    formatted_text += "\n"
            elif isinstance(edu, str):
                formatted_text += f"{edu}\n"
        
        return formatted_text.strip()
    
    # Return as is if nothing matched
    return str(education_data)

def format_links(links_data):
    """Convert links data to a formatted string with proper labeling"""
    # Return empty string for empty data
    if not links_data or links_data == "[]" or links_data == "{}":
        return ""
    
    # Handle the case when links_data is a Python list of objects with platform and url
    if isinstance(links_data, list):
        # If it's an empty list, return empty string
        if len(links_data) == 0:
            return ""
            
        formatted_text = ""
        for link_item in links_data:
            if isinstance(link_item, dict) and 'platform' in link_item and 'url' in link_item:
                # Only add non-empty URLs
                if link_item['url'] and link_item['url'].strip():
                    formatted_text += f"{link_item['platform']}: {link_item['url']}\n"
            elif isinstance(link_item, str) and link_item.strip():
                # Extract domain name to use as label for URLs
                try:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(link_item)
                    domain = parsed_url.netloc.replace('www.', '')
                    platform = domain.split('.')[0].capitalize()
                    formatted_text += f"{platform}: {link_item}\n"
                except Exception:
                    formatted_text += f"{link_item}\n"
        
        # If after processing all links, we have no content, return empty string
        if not formatted_text.strip():
            return ""
        return formatted_text.strip()
    
    # Handle the case when links_data is a string that looks like a Python list/dict
    if isinstance(links_data, str):
        # If it's an empty JSON array/object string, return empty
        if links_data.strip() in ('[]', '{}', ''):
            return ""
            
        # First check if it's just a simple string with URLs
        import re
        urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*', links_data)
        if urls:
            return format_links(urls)  # Process the extracted URLs
            
        if links_data.startswith('[') or links_data.startswith('{'):
            try:
                # Try to parse as JSON
                import json
                json_str = links_data.replace("'", '"')
                parsed_data = json.loads(json_str)
                
                # If it's an empty structure after parsing, return empty string
                if not parsed_data or (isinstance(parsed_data, list) and len(parsed_data) == 0):
                    return ""
                
                if isinstance(parsed_data, list):
                    return format_links(parsed_data)  # Recursively process the list
                elif isinstance(parsed_data, dict):
                    formatted_text = ""
                    for platform, url in parsed_data.items():
                        # Only add non-empty URLs
                        if url and str(url).strip():
                            formatted_text += f"{platform}: {url}\n"
                    
                    # If after processing, we have no content, return empty
                    if not formatted_text.strip():
                        return ""
                    return formatted_text.strip()
            except json.JSONDecodeError:
                try:
                    # Fall back to ast.literal_eval for Python syntax
                    import ast
                    parsed_data = ast.literal_eval(links_data)
                    
                    # If it's empty after parsing, return empty string
                    if not parsed_data or (isinstance(parsed_data, list) and len(parsed_data) == 0):
                        return ""
                        
                    return format_links(parsed_data)  # Recursively process the parsed data
                except (ValueError, SyntaxError):
                    pass
    
    # Return as is if nothing matched but make sure it's not just whitespace
    result = str(links_data).strip()
    return result if result else ""

def format_experience_projects(experience_data):
    """Convert complex experience data to a clean, plain-text string with line breaks and spacing"""

    if not experience_data:
        return ""

    # Handle string representation of experience data
    if isinstance(experience_data, str) and (experience_data.startswith('[') or experience_data.startswith('{')):
        try:
            import json
            json_str = experience_data.replace("'", '"')
            exp_list = json.loads(json_str)
            return format_experience_projects(exp_list)
        except json.JSONDecodeError:
            try:
                import ast
                exp_list = ast.literal_eval(experience_data)
                return format_experience_projects(exp_list)
            except (ValueError, SyntaxError):
                return experience_data

    # If it's already a list of dictionaries
    if isinstance(experience_data, list):
        formatted_entries = []

        for exp in experience_data:
            if isinstance(exp, dict):
                lines = []
                company = exp.get('company',
                        exp.get('employer',
                        exp.get('organization',
                        exp.get('workplace',
                        exp.get('firm',
                        exp.get('business', ''))))))
                project = exp.get('project',
                        exp.get('title',
                        exp.get('project_title',
                        exp.get('project_name',
                        exp.get('assignment',
                        exp.get('task', ''))))))
                role = exp.get('role',
                    exp.get('title',
                    exp.get('position',
                    exp.get('job_title',
                    exp.get('designation', '')))))
                duration = exp.get('duration',
                            exp.get('period',
                            exp.get('timeframe',
                            exp.get('time_period',
                            exp.get('dates',
                            exp.get('timeline', ''))))))
                description = exp.get('description',
                            exp.get('responsibilities',
                            exp.get('details',
                            exp.get('summary',
                            exp.get('work',
                            exp.get('achievements',
                            exp.get('tasks', '')))))))
                location = exp.get('location',
                        exp.get('place',
                        exp.get('city',
                        exp.get('region',
                        exp.get('country', '')))))
                technologies = exp.get('skills',
                        exp.get('technologies',
                        exp.get('tech_stack',
                        exp.get('tools',
                        exp.get('languages', [])))))

                if company:
                    lines.append(f"Company: {company}")
                elif project:
                    lines.append(f"Project: {project}")

                if role:
                    lines.append(f"Role: {role}")
                if duration:
                    lines.append(f"Duration: {duration}")
                if location:
                    lines.append(f"Location: {location}")
                if description:
                    lines.append(f"Description: {description}")

                if technologies:
                    # join list of skills or leave string as-is
                    technologies_str = ", ".join(technologies) if isinstance(technologies, (list, tuple)) else technologies
                    lines.append(f"technologies: {technologies_str}")

                formatted_entries.append("\n".join(lines))


            elif isinstance(exp, str):
                formatted_entries.append(exp)

        return '\n\n'.join(formatted_entries).strip()

    # Return as-is if nothing matched
    return str(experience_data)


def calculate_overall_score(education_match, skills_score, experience_match):
    """
    Calculate the overall compatibility score based on education, skills, and experience weights.
    """
    try:
        # Define weightages for each component
        WEIGHT_EDUCATION = 0.3
        WEIGHT_SKILLS = 0.4
        WEIGHT_EXPERIENCE = 0.3

        # Calculate weighted score
        overall_score = (
            (education_match * WEIGHT_EDUCATION) +
            (skills_score * WEIGHT_SKILLS) +
            (experience_match * WEIGHT_EXPERIENCE)
        )
        return round(overall_score, 2)
    except Exception as e:
        print(f"Error calculating overall score: {e}")
        return 0


def create_education_lookup_table():
    """
    Create a comprehensive education lookup table mapping abbreviations to their full forms
    and alternative expressions, with special focus on Indian education qualifications.
    """
    # Dictionary where keys are variations of education qualifications 
    # and values are their standardized forms
    education_lookup = {
        # Engineering Degrees
        "be": "Bachelor of Engineering",
        "b.e.": "Bachelor of Engineering",
        "b.e": "Bachelor of Engineering",
        "bachelor of engineering": "Bachelor of Engineering",
        "btech": "Bachelor of Technology",
        "b.tech": "Bachelor of Technology",
        "b.tech.": "Bachelor of Technology",
        "bachelor of technology": "Bachelor of Technology",
        "me": "Master of Engineering",
        "m.e.": "Master of Engineering",
        "m.e": "Master of Engineering",
        "master of engineering": "Master of Engineering",
        "mtech": "Master of Technology",
        "m.tech": "Master of Technology",
        "m.tech.": "Master of Technology",
        "master of technology": "Master of Technology",
        
        # Computer Science Degrees
        "bca": "Bachelor of Computer Applications",
        "b.c.a.": "Bachelor of Computer Applications",
        "b.c.a": "Bachelor of Computer Applications",
        "bachelor of computer applications": "Bachelor of Computer Applications",
        "mca": "Master of Computer Applications",
        "m.c.a.": "Master of Computer Applications",
        "m.c.a": "Master of Computer Applications",
        "master of computer applications": "Master of Computer Applications",
        
        # Business/Management Degrees
        "bba": "Bachelor of Business Administration",
        "b.b.a.": "Bachelor of Business Administration",
        "b.b.a": "Bachelor of Business Administration",
        "bachelor of business administration": "Bachelor of Business Administration",
        "mba": "Master of Business Administration",
        "m.b.a.": "Master of Business Administration",
        "m.b.a": "Master of Business Administration",
        "master of business administration": "Master of Business Administration",
        
        # Science Degrees
        "bsc": "Bachelor of Science",
        "b.sc.": "Bachelor of Science",
        "b.sc": "Bachelor of Science",
        "bachelor of science": "Bachelor of Science",
        "msc": "Master of Science",
        "m.sc.": "Master of Science",
        "m.sc": "Master of Science",
        "master of science": "Master of Science",
        
        # Commerce Degrees
        "bcom": "Bachelor of Commerce",
        "b.com.": "Bachelor of Commerce",
        "b.com": "Bachelor of Commerce",
        "bachelor of commerce": "Bachelor of Commerce",
        "mcom": "Master of Commerce",
        "m.com.": "Master of Commerce",
        "m.com": "Master of Commerce",
        "master of commerce": "Master of Commerce",
        
        # Arts Degrees
        "ba": "Bachelor of Arts",
        "b.a.": "Bachelor of Arts",
        "b.a": "Bachelor of Arts",
        "bachelor of arts": "Bachelor of Arts",
        "ma": "Master of Arts",
        "m.a.": "Master of Arts",
        "m.a": "Master of Arts",
        "master of arts": "Master of Arts",
        
        # Medical Degrees
        "mbbs": "Bachelor of Medicine and Bachelor of Surgery",
        "m.b.b.s.": "Bachelor of Medicine and Bachelor of Surgery",
        "m.b.b.s": "Bachelor of Medicine and Bachelor of Surgery",
        "bachelor of medicine and bachelor of surgery": "Bachelor of Medicine and Bachelor of Surgery",
        "md": "Doctor of Medicine",
        "m.d.": "Doctor of Medicine",
        "m.d": "Doctor of Medicine",
        "doctor of medicine": "Doctor of Medicine",
        
        # Pharmacy Degrees
        "b.pharm": "Bachelor of Pharmacy",
        "b.pharm.": "Bachelor of Pharmacy",
        "bachelor of pharmacy": "Bachelor of Pharmacy",
        "m.pharm": "Master of Pharmacy",
        "m.pharm.": "Master of Pharmacy",
        "master of pharmacy": "Master of Pharmacy",
        
        # Education Degrees
        "b.ed": "Bachelor of Education",
        "b.ed.": "Bachelor of Education",
        "bachelor of education": "Bachelor of Education",
        "m.ed": "Master of Education",
        "m.ed.": "Master of Education",
        "master of education": "Master of Education",
        
        # Doctoral Degrees
        "phd": "Doctor of Philosophy",
        "ph.d.": "Doctor of Philosophy",
        "ph.d": "Doctor of Philosophy",
        "doctor of philosophy": "Doctor of Philosophy",
        
        # General Education Levels
        "bachelors": "Bachelor's Degree",
        "bachelor's": "Bachelor's Degree",
        "bachelor degree": "Bachelor's Degree",
        "bachelor's degree": "Bachelor's Degree",
        "masters": "Master's Degree",
        "master's": "Master's Degree",
        "master degree": "Master's Degree",
        "master's degree": "Master's Degree",
        "doctorate": "Doctoral Degree",
        "doctoral": "Doctoral Degree",
        "doctoral degree": "Doctoral Degree",
        
        # Indian Specific Education
        "12th": "Higher Secondary",
        "hsc": "Higher Secondary Certificate",
        "higher secondary": "Higher Secondary Certificate",
        "10th": "Secondary School",
        "ssc": "Secondary School Certificate",
        "secondary school": "Secondary School Certificate",
        "diploma": "Diploma",
        
        # Additional Indian Specific Qualifications
        "ca": "Chartered Accountant",
        "chartered accountant": "Chartered Accountant",
        "cs": "Company Secretary",
        "company secretary": "Company Secretary",
        "icwa": "Cost and Management Accountant",
        "cma": "Cost and Management Accountant",
        "cost and management accountant": "Cost and Management Accountant"
    }
    
    return education_lookup


def normalize_education(education_text, lookup_table=None):
    """
    Normalize education text that may contain multiple qualifications using the lookup table.
    Returns a list of all normalized education qualifications found, preserving specialization.
    
    Args:
        education_text (str): The education qualification from resume or job description
        lookup_table (dict, optional): Education lookup table. If None, creates a new one.
        
    Returns:
        list: List of standardized education forms found with specializations
    """
    # Import re module at the function level to ensure it's available
    import re
    
    if not education_text:
        return []
        
    if lookup_table is None:
        lookup_table = create_education_lookup_table()
    
    # Initialize result list to store all normalized educations
    normalized_educations = []
    
    # Handle slashes as alternatives first
    alternatives = [education_text]
    if "/" in education_text:
        # Create separate entries for slash-separated alternatives
        parts = education_text.split(",")
        new_parts = []
        
        for part in parts:
            if "/" in part:
                # Split by slash and create separate entries
                slash_parts = part.strip().split("/")
                new_parts.extend(slash_parts)
            else:
                new_parts.append(part)
        
        alternatives = [", ".join(new_parts)]
    
    for alt_text in alternatives:
        # Split text by common separators like semicolons and commas
        education_parts = [part.strip() for part in alt_text.split(';')]
        # Further split by commas if needed
        expanded_parts = []
        for part in education_parts:
            if ',' in part:
                expanded_parts.extend([p.strip() for p in part.split(',')])
            else:
                expanded_parts.append(part)
        
        # Process each education part
        for part in expanded_parts:
            if not part:  # Skip empty parts
                continue
                
            # Clean the part but preserve case for specialization
            original_text = part.strip()
            clean_text = original_text.lower()
            
            # Extract degree and specialization
            degree_found = False
            specialization = ""
            normalized_degree = ""
            
            # Try direct match first
            if clean_text in lookup_table:
                normalized_degree = lookup_table[clean_text]
                degree_found = True
            else:
                # Look for degree patterns like "B.Tech", "BTech", "Bachelor of Technology"
                abbr_pattern = r'\b([A-Za-z](?:\.[A-Za-z])+(?:\.)?|\b[A-Za-z]{1,5}\b)'
                
                # Find all possible abbreviations in the text
                abbreviations = re.findall(abbr_pattern, clean_text)
                
                # Try to match each abbreviation with our lookup table
                for abbr in abbreviations:
                    abbr_clean = abbr.lower().replace('.', '')
                    for key, value in lookup_table.items():
                        key_clean = key.lower().replace('.', '')
                        if abbr_clean == key_clean:
                            normalized_degree = value
                            degree_found = True
                            break
                    if degree_found:
                        break
                
                # If not found by abbreviation, try to find if any key is contained within the education text
                if not degree_found:
                    for abbr, full_form in lookup_table.items():
                        # Look for standalone abbreviations with word boundaries
                        if (f" {abbr} " in f" {clean_text} " or 
                            clean_text.startswith(f"{abbr} ") or 
                            clean_text.endswith(f" {abbr}") or 
                            clean_text == abbr):
                            normalized_degree = full_form
                            degree_found = True
                            break
                
                # If still not found, check if the full form is contained in the education text
                if not degree_found:
                    for abbr, full_form in lookup_table.items():
                        if full_form.lower() in clean_text:
                            normalized_degree = full_form
                            degree_found = True
                            break
            
            # Extract specialization using common patterns
            if degree_found:
                # Specialization often follows "in", "of", "with focus on", etc.
                spec_patterns = [
                    r'in\s+([^;,]+)', 
                    r'of\s+([^;,]+)',
                    r'with\s+focus\s+on\s+([^;,]+)',
                    r'with\s+specialization\s+in\s+([^;,]+)',
                    r'specializing\s+in\s+([^;,]+)'
                ]
                
                for pattern in spec_patterns:
                    match = re.search(pattern, clean_text)
                    if match:
                        specialization = match.group(1).strip()
                        break
                
                # Combine degree with specialization if found
                if specialization:
                    normalized_educations.append(f"{normalized_degree} in {specialization}")
                else:
                    normalized_educations.append(normalized_degree)
            # If no match found, add the original
            else:
                normalized_educations.append(original_text)
    
    # Remove duplicates while preserving order
    unique_educations = []
    for edu in normalized_educations:
        if edu not in unique_educations:
            unique_educations.append(edu)
            
    return unique_educations

def compare_education(resume_education, job_education):
    """
    Compare resume education with job requirements using the lookup table.
    This version handles multiple education qualifications and specializations.
    
    Args:
        resume_education (str): Education from resume
        job_education (str): Required education from job description
        
    Returns:
        float: Match score between 0.0 and 1.0
    """
    # Import modules at the function level to ensure they're available
    import re
    try:
        from fuzzywuzzy import fuzz
    except ImportError:
        # Define a simple fallback if fuzzywuzzy is not available
        class SimpleFuzz:
            @staticmethod
            def partial_ratio(str1, str2):
                # Very basic similarity - just check if one is in the other
                if str1 in str2 or str2 in str1:
                    return 80  # Fairly high match
                return 50  # Medium match as fallback
                
            @staticmethod
            def token_sort_ratio(str1, str2):
                # Very basic token comparison
                tokens1 = set(str1.lower().split())
                tokens2 = set(str2.lower().split())
                if tokens1.intersection(tokens2):
                    return 70  # Some tokens match
                return 30  # Low match
        
        fuzz = SimpleFuzz()
    if not resume_education or resume_education == "Not Specified":
        return 0.0
        
    if not job_education:
        return 1.0  # If no education specified in job, consider it a match
    
    # Use lookup table for normalization
    lookup_table = create_education_lookup_table()
    
    # Get all normalized education qualifications
    resume_educations = normalize_education(resume_education, lookup_table)
    job_educations = normalize_education(job_education, lookup_table)
    
    # For debug purposes
    # print(f"Resume Educations: Original='{resume_education}', Normalized={resume_educations}")
    # print(f"Job Educations: Original='{job_education}', Normalized={job_educations}")
    
    if not resume_educations:
        return 0.0
    
    # Handle "Any Graduate/Any Postgraduate" logic
    job_ed_lower = job_education.lower()
    if "any graduate" in job_ed_lower or "any postgraduate" in job_ed_lower:
        resume_ed_lower = resume_education.lower()
        
        if "any graduate" in job_ed_lower:
            # Check if resume has a bachelor's degree
            bachelor_keywords = ["bachelor", "b.", "b ", "undergraduate", "be", "btech", "bca", "bsc", "bcom", "ba"]
            if any(keyword in resume_ed_lower for keyword in bachelor_keywords):
                return 1.0
                
        if "any postgraduate" in job_ed_lower:
            # Check if resume has a master's degree or higher
            postgrad_keywords = ["master", "m.", "m ", "postgraduate", "phd", "doctorate", "me", "mtech", "mca", "msc", "mcom", "ma", "mba"]
            if any(keyword in resume_ed_lower for keyword in postgrad_keywords):
                return 1.0
    
    # Special case: "x or y" in job requirements
    for job_edu in job_educations:
        if " or " in job_edu.lower():
            job_options = job_edu.lower().split(" or ")
            job_options = [option.strip() for option in job_options]
            
            # If resume education matches any of the options, it's a match
            for resume_edu in resume_educations:
                if any(option in resume_edu.lower() for option in job_options):
                    return 1.0
    
    # Calculate education levels for comparison
    def get_education_level(edu_text):
        edu_lower = edu_text.lower()
        if any(term in edu_lower for term in ["phd", "doctorate", "doctor of"]):
            return 3  # Doctoral
        elif any(term in edu_lower for term in ["master", "post graduate", "postgraduate", "post-graduate", "m.", "ms ", " ms", "mtech", "mca", "mba"]):
            return 2  # Master's
        elif any(term in edu_lower for term in ["bachelor", "graduate", "b.", "bs ", " bs", "btech", "be ", " be", "bca"]):
            return 1  # Bachelor's
        else:
            return 0  # Other
    
    # Get maximum education level from resume
    resume_max_level = max([get_education_level(edu) for edu in resume_educations]) if resume_educations else 0
    
    # Check for specialization matches
    specialization_match_score = 0.0
    
    for job_edu in job_educations:
        job_level = get_education_level(job_edu)
        job_spec = None
        
        # Extract specialization from job education
        if " in " in job_edu:
            job_spec = job_edu.split(" in ", 1)[1].lower()
        
        # Direct match check
        for resume_edu in resume_educations:
            # Perfect match (including specialization)
            if resume_edu.lower() == job_edu.lower():
                return 1.0
            
            # Check for specialization match
            resume_spec = None
            if " in " in resume_edu:
                resume_spec = resume_edu.split(" in ", 1)[1].lower()
            
            # If both have specializations, compare them
            if job_spec and resume_spec:
                # Import fuzzywuzzy for better specialization comparison
                from fuzzywuzzy import fuzz
                spec_score = fuzz.token_sort_ratio(resume_spec, job_spec) / 100.0
                
                # If specialization is highly similar, consider it a strong match
                if spec_score > 0.7:
                    # Higher score for exact degree and similar specialization
                    if resume_edu.split(" in ")[0].lower() == job_edu.split(" in ")[0].lower():
                        specialization_match_score = max(specialization_match_score, 0.9)
                    else:
                        specialization_match_score = max(specialization_match_score, 0.7)
        
        # If resume education level is higher than or equal to job requirement, consider it a match
        if resume_max_level >= job_level and resume_max_level > 0 and job_level > 0:
            # Partial match for having appropriate education level
            specialization_match_score = max(specialization_match_score, 0.8)
    
    # Return specialization match if it's significant
    if specialization_match_score > 0.0:
        return specialization_match_score
    
    # Create a single string from all resume educations for fuzzy matching
    resume_edu_text = " ".join(resume_educations)
    job_edu_text = " ".join(job_educations)
    
    match_score = fuzz.partial_ratio(resume_edu_text.lower(), job_edu_text.lower()) / 100.0
    
    # If high fuzzy match (>80%), consider it a strong match
    if match_score > 0.8:
        return 1.0
        
    return match_score

# Example usage:
if __name__ == "__main__":
    # Import fuzzywuzzy if needed
    try:
        from fuzzywuzzy import fuzz
    except ImportError:
        print("fuzzywuzzy module not available, install with: pip install fuzzywuzzy python-Levenshtein")
    
    # Example
    jd_education = "B.Tech/B.E., MTech in Computers"
    employee_education = "Bachelor of Science in Computer Science; Master of Science in Software Engineering"
    
    # Get all normalized educations
    lookup_table = create_education_lookup_table()
    
    normalized_jd = normalize_education(jd_education, lookup_table)
    print(f"JD Original: {jd_education}")
    print(f"JD Normalized: {normalized_jd}")
    
    normalized_resume = normalize_education(employee_education, lookup_table)
    print(f"Resume Original: {employee_education}")
    print(f"Resume Normalized: {normalized_resume}")
    
    # Compare with job requirement
    score = compare_education(employee_education, jd_education)
    print(f"Match score: {score:.2f}")

def extract_min_experience(experience_text):
    """
    Extract minimum required experience from the job details.
    This function should be implemented to handle experience ranges like "2-5 years".
    """
    # This is a placeholder. You should implement this according to your needs.
    # For example, if experience_text is "2-5 years", it should return 2
    import re
    
    if not experience_text:
        return 0
        
    # Handle ranges like "2-5 years" or "2 to 5 years"
    range_pattern = r'(\d+)(?:\s*-|\s+to\s+)(\d+)'
    range_match = re.search(range_pattern, experience_text.lower())
    if range_match:
        return float(range_match.group(1))
    
    # Handle simple patterns like "2 years"
    years_pattern = r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?)'
    years_match = re.search(years_pattern, experience_text.lower())
    if years_match:
        return float(years_match.group(1))
    
    # Handle patterns like "minimum 2 years" or "at least 2 years"
    min_pattern = r'(?:minimum|min|at least)\s*(\d+(?:\.\d+)?)'
    min_match = re.search(min_pattern, experience_text.lower())
    if min_match:
        return float(min_match.group(1))
    
    return 0


def generate_recommendations(compatibility_matrix, job_details):
    """
    Generate recommendations based on compatibility matrix and job details.
    """
    try:
        recommendations = []

        # Extract skills from compatibility matrix where Match == "No"
        unmatched_skills = set(
            criteria["Criteria"].lower().strip()
            for criteria in compatibility_matrix
            if criteria["Match"] == "No" and criteria["Criteria"].lower() not in ["education", "experience (years)"]
        )

        # Clean and normalize job skills
        job_skills = job_details.get("skills", [])
        if isinstance(job_skills, str):
            job_skills = {skill.strip().lower() for skill in job_skills.split(",")}
        else:
            job_skills = set(map(lambda s: s.lower().strip(), job_skills))

        # Identify missing skills (those required by the job but not matched in the resume)
        missing_skills = job_skills & unmatched_skills

        # If there are missing skills, suggest upskill
        if missing_skills:
            recommendations.append(f"Upskill in: {', '.join(sorted(missing_skills))}.")

        # Check for mismatches in education and experience
        for criteria in compatibility_matrix:
            if criteria["Criteria"].lower() == "experience (years)" and "Experience mismatch" in criteria.get("Comments", ""):
                recommendations.append("Consider gaining more relevant experience.")
            elif criteria["Criteria"].lower() == "education" and criteria["Match"] == "No":
                recommendations.append("Pursue certifications or additional education to match job requirements.")

        # Default recommendation if no specific mismatches are found
        return recommendations or ["No specific recommendations available."]

    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return ["Unable to generate recommendations."]


def generate_detailed_compatibility_report(employer=None, job_id=None):
    """
    Generate a compatibility report for jobs and employees.

    Args:
        employer (str): Employer name to filter jobs (optional).
        job_id (int): Specific job ID to filter (optional).

    Returns:
        list: Detailed compatibility report for jobs and employees.
    """
    try:
        # Query jobs
        jobs_query = Job.objects.filter(employer=employer) if employer else Job.objects.all()
        if job_id:
            jobs_query = jobs_query.filter(id=job_id)

        logger.debug(f"Jobs Query: {jobs_query}")

        # List of excluded users
        EXCLUDED_USERS = ["vinaybharadwaj", "admin"]

        # Query user profiles
        user_profiles = UserProfile.objects.filter(role='employee', resume__isnull=False)
        detailed_report = []

        for job in jobs_query:
            # Extract job details
            job_details = {
                "education": job.education or "Not Specified",
                "skills": [skill.strip() for skill in (job.skills or "").split(",") if skill.strip()] or ["Not Specified"],
                "experience": job.experience or "0"
            }

            for profile in user_profiles:
                # Skip excluded users based on full_name
                if profile.full_name.lower() in EXCLUDED_USERS:
                    logger.debug(f"Skipping excluded user: {profile.full_name}")
                    continue

                # Extract profile details
                resume_details = {
                    "education": profile.education or "Not Specified",
                    "skills": [skill.strip() for skill in (profile.skills or "").split(",") if skill.strip()] or ["Not Specified"],
                    "experience_years": profile.experience_years or 0
                }

                # Compare resume with job requirements
                compatibility_matrix, scores = compare_resume_with_job(resume_details, job_details)

                # Append results to the report
                detailed_report.append({
                    "Candidate": profile.full_name,
                    "Job": f"{job.company_name} - {job.role}",
                    "job_id": job.id,  # Include job_id for dynamic URL generation
                    "Criteria": compatibility_matrix,
                    "Education Compatibility": scores.get("education_compatibility", 0),
                    "Skills Compatibility": scores.get("skills_compatibility", 0),
                    "Experience Compatibility": scores.get("experience_compatibility", 0),
                    "Overall Compatibility": scores.get("overall_compatibility", 0),
                })

                # Debugging logs
                logger.debug(f"Job Details: {job_details}")
                logger.debug(f"Resume Details for {profile.full_name}: {resume_details}")
                logger.debug(f"Compatibility Matrix: {compatibility_matrix}")
                logger.debug(f"Scores for {profile.full_name} and Job {job.id}: {scores}")

        logger.info("Detailed Report Generated")
        return detailed_report

    except Exception as e:
        logger.error(f"Error generating compatibility report: {e}")
        return []


def display_compatibility_report(report):
    """
    Display the compatibility report in a formatted console output.

    Args:
        report (list): List of compatibility report entries.
    """
    for entry in report:
        print(f"Candidate: {entry['Candidate']}")
        print(f"Job: {entry['Job']}\n")
        
        for row in entry["Criteria"]:
            print(
                f"Criteria: {row['Criteria']}\n"
                f"Resume Details: {row['Resume Details']}\n"
                f"Job Description Requirements: {row['Job Description Requirements']}\n"
                f"Match: {row['Match']}\n"
                f"Comments: {row['Comments']}\n"
            )
        print(f"Overall Compatibility: {entry['Overall Compatibility']}%\n{'-' * 50}\n")


def generate_employee_compatibility_report(employee):
    """
    Generate a compatibility report for the logged-in employee with all posted jobs.
    """
    try:
        if not employee:
            raise ValueError("No employee provided for compatibility report generation.")

        # List of excluded users
        EXCLUDED_USERS = ["vinaybharadwaj", "admin"]

        # Fetch the logged-in employee's profile
        try:
            employee_profile = employee.userprofile
        except UserProfile.DoesNotExist:
            raise ValueError("Employee profile not found.")

        # Check if the logged-in user is excluded
        if employee_profile.full_name.lower() in EXCLUDED_USERS:
            raise ValueError("This user is not eligible for compatibility report generation.")

        if not employee_profile.resume:
            raise ValueError("Employee does not have a resume uploaded.")

        # Extract resume details
        resume_details = {
            "education": employee_profile.education or "Not Specified",
            "skills": [skill.strip() for skill in (employee_profile.skills or "").split(",")] or ["Not Specified"],
            "experience_years": employee_profile.experience_years or 0,
        }

        # Fetch all available jobs
        jobs_query = Job.objects.all()

        # Prepare detailed report
        detailed_report = []

        for job in jobs_query:
            company_name = job.company_name.strip()

            # Extract job details
            job_details = {
                "education": job.education or "Not Specified",
                "skills": [skill.strip() for skill in (job.skills or "").split(",")] or ["Not Specified"],
                "experience": job.experience or "0",
            }

            # Compare employee resume with job requirements
            compatibility_matrix, scores = compare_resume_with_job(resume_details, job_details)

            # Generate recommendations for this job
            recommendations = generate_recommendations(compatibility_matrix, job_details)

            # Append compatibility results to the report
            detailed_report.append({
                "Job": company_name,
                "Criteria": compatibility_matrix,
                "Education Compatibility": scores["education_compatibility"],
                "Skills Compatibility": scores["skills_compatibility"],
                "Experience Compatibility": scores["experience_compatibility"],
                "Overall Compatibility": scores["overall_compatibility"],
                "Recommendations": recommendations,
            })

            # Debugging
            logger.debug(f"Job Details: {job_details}")
            logger.debug(f"Compatibility Matrix for Job {company_name}: {compatibility_matrix}")
            logger.debug(f"Recommendations for {company_name}: {recommendations}")

        logger.info("Employee Compatibility Report Generated")
        return detailed_report

    except Exception as e:
        logger.error(f"Error generating employee compatibility report: {e}")
        raise



def generate_clustered_bar_chart(similarity_df, file_path):
    """
    Generate multiple clustered bar charts by splitting the data into smaller subplots.

    Args:
        similarity_df (pd.DataFrame): DataFrame containing compatibility scores with employees as columns.
        file_path (str): Path to save the generated chart.
    """
    try:
        if similarity_df.empty:
            logger.warning("Cannot generate clustered bar chart for an empty DataFrame.")
            return

        # Exclude non-employees (e.g., 'vinaybharadwaj')
        if "vinaybharadwaj" in similarity_df.index:
            similarity_df = similarity_df.drop(index="vinaybharadwaj")

        # Increase the number of companies per subplot to 20
        max_companies_per_subplot = 20
        num_subplots = math.ceil(len(similarity_df.columns) / max_companies_per_subplot)

        # Set up the subplots
        fig, axes = plt.subplots(
            nrows=num_subplots, 
            figsize=(18, 10 * num_subplots), 
            sharey=True
        )
        if num_subplots == 1:  # If only one subplot, treat axes as a single axis
            axes = [axes]

        # Generate each subplot
        for i, ax in enumerate(axes):
            start = i * max_companies_per_subplot
            end = (i + 1) * max_companies_per_subplot
            subset_df = similarity_df.iloc[:, start:end]

            # Plot the data
            subset_df.plot(kind='bar', ax=ax, width=0.8)

            # Add titles and labels
            ax.set_title(f"Compatibility Scores (Companies {start + 1} to {min(end, len(similarity_df.columns))})", fontsize=16, weight="bold")
            ax.set_xlabel("Employees", fontsize=16)
            ax.set_ylabel("Compatibility Score", fontsize=16)

            # Update legend font size
            ax.legend(
                title="Companies",
                loc="upper left",
                bbox_to_anchor=(1, 1),
                fontsize=14,            # Increase legend font size
                title_fontsize=16       # Increase title font size
            )
            ax.tick_params(axis='x', labelrotation=45, labelsize=12)

        # Adjust layout
        plt.tight_layout()
        plt.savefig(file_path, bbox_inches="tight", dpi=300)
        plt.close()
        logger.info(f"Clustered bar chart saved at {file_path}")

    except Exception as e:
        logger.error(f"Error generating clustered bar chart: {e}")


def recommend_top_jobs(similarity_df, jobs_query, top_n=10):
    """
    Recommend top N jobs for each employee based on compatibility scores.
    """
    recommendations = {}
    for employee in similarity_df.index:
        sorted_scores = similarity_df.loc[employee].sort_values(ascending=False)
        top_jobs = sorted_scores.head(top_n).index
        
        # Fetch the corresponding jobs based on the top job names
        recommendations[employee] = jobs_query.filter(company_name__in=top_jobs)
    return recommendations


def generate_employee_clustered_chart(compatibility_scores, output_path):
    """
    Generate a clustered bar chart for employee compatibility scores.
    
    Args:
        compatibility_scores (pd.Series): Compatibility scores for the employee.
        output_path (str): Path to save the generated chart.
    """
    if compatibility_scores.empty:
        logger.warning("Cannot generate bar chart for an empty compatibility score.")
        return

    # Set the maximum number of companies per chart
    max_companies_per_chart = 30
    num_subplots = math.ceil(len(compatibility_scores) / max_companies_per_chart)

    # Set up the subplots
    fig, axes = plt.subplots(
        nrows=num_subplots, 
        figsize=(18, 10 * num_subplots), 
        sharey=True
    )
    
    if num_subplots == 1:  # If only one subplot, treat axes as a single axis
        axes = [axes]

    # Create a dynamic color palette based on the number of companies
    num_colors = len(compatibility_scores)
    colors = plt.cm.tab20.colors * (num_colors // 20 + 1)  # Repeat colors if more than 20 companies
    colors = colors[:num_colors]  # Ensure that we only use as many colors as needed

    # Generate each subplot
    for i, ax in enumerate(axes):
        start = i * max_companies_per_chart
        end = (i + 1) * max_companies_per_chart
        subset_scores = compatibility_scores.iloc[start:end]
        companies = compatibility_scores.index[start:end]  # Get the companies for the legend

        # Create the bar chart for the subset
        bars = subset_scores.plot(kind='bar', ax=ax, color=colors[start:end], width=0.8)

        # Set custom legend to display company names
        ax.legend(bars.patches, companies, title="Companies", loc="upper left", bbox_to_anchor=(1, 1), fontsize=14, title_fontsize=16)

        # Add titles and labels
        ax.set_title(f"Compatibility Scores (Companies {start + 1} to {min(end, len(compatibility_scores))})", fontsize=16, weight="bold")
        ax.set_xlabel("Jobs", fontsize=16)
        ax.set_ylabel("Compatibility Score", fontsize=16)

        # Remove x-axis labels (company names)
        ax.set_xticklabels([])

        # Rotate x-axis labels for readability (they will be empty)
        ax.tick_params(axis='x', labelrotation=45, labelsize=12)

    # Improve layout and save the chart
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    plt.close()
    logger.info(f"Clustered bar chart saved at {output_path}")

