import logging
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

BASE_RESUME_PATH = os.path.join("C:\\Users\\Vinay Bharadwaj\\Desktop\\Job-Recommender-System\\job_recommender\\media\\resumes")
DEFAULT_RESUME_PATH = os.path.join(BASE_RESUME_PATH, 'default_resume.pdf')
os.makedirs(BASE_RESUME_PATH, exist_ok=True)



def validate_file_path(file_path):
    if not os.path.exists(file_path):
        print(f"Error: Resume file not found: {file_path}")
        return False
    return True



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


import re

def extract_min_experience(experience_range_str):
    """
    Extracts the minimum required experience from a given experience range string like "0-1 years", "1 - 2 years" or "3 years".
    If the experience is a range or has a '+', returns the lower bound. Otherwise, returns the exact experience in years.
    """
    if isinstance(experience_range_str, str):
        # Match a pattern like "0-1 years", "1 - 2 years" or "3 years"
        match = re.match(r"(\d+)\s*-\s*(\d+)\s*years?", experience_range_str)
        if match:
            # If it's a range, return the lower bound
            return int(match.group(1))
        # Match for a single experience or "1+ years"
        match = re.match(r"(\d+)\+?\s*years?", experience_range_str)
        if match:
            return int(match.group(1))
    return 0  # Return 0 if no valid experience found


def compare_resume_with_job(resume_details, job_details):
    """
    Compare resume details with job requirements and calculate compatibility scores.
    """
    try:
        # Education comparison with "Any Graduate/Any Postgraduate" logic
        job_education = job_details["education"].lower()
        if "any graduate" in job_education or "any postgraduate" in job_education:
            education_match = 1.0  # 100%
        else:
            education_match = fuzz.partial_ratio(
                resume_details["education"].lower(), job_details["education"].lower()
            ) / 100.0 if resume_details["education"] != "Not Specified" else 0.0

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

        # Overall compatibility
        overall_score = round((education_match * 0.3) + (skills_score * 0.4) + (experience_match * 0.3), 2)

        # Compatibility matrix
        criteria = [
            {"Criteria": "Education",
             "Resume_Details": resume_details["education"],
             "Job_Description_Requirements": job_details["education"],
             "Match": "Yes" if education_match == 1.0 else "No",
             "Comments": "Matches" if education_match == 1.0 else "Mismatch"
            },
            {"Criteria": "Experience (Years)",
             "Resume_Details": resume_details["experience_years"] if resume_details["experience_years"] > 0 else "0 years",
             "Job_Description_Requirements": job_experience if job_experience > 0 else "0 years",
             "Match": "Yes" if experience_match == 1.0 else "No",
             "Comments": "Matches" if experience_match == 1.0 else "Experience mismatch"
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

        return criteria, {
            "education_compatibility": education_match * 100,  # Convert to percentage
            "skills_compatibility": skills_score * 100,  # Convert to percentage
            "experience_compatibility": experience_match * 100,  # Convert to percentage
            "overall_compatibility": overall_score * 100,  # Convert to percentage
            "recommendation": recommendation_text
        }

    except Exception as e:
        logger.error(f"Error comparing resume with job: {e}")
        return [], {"education_compatibility": 0, "skills_compatibility": 0, "experience_compatibility": 0, "overall_compatibility": 0, "recommendation": ""}


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
            job_skills = set(map(lambda s: s.lower(), job_skills))

        # Identify missing skills (those required by the job but not matched in the resume)
        missing_skills = job_skills & unmatched_skills

        # If there are missing skills, suggest upskill
        if missing_skills:
            recommendations.append(f"Upskill in: {', '.join(missing_skills)}.")

        # Check for mismatches in education and experience
        for criteria in compatibility_matrix:
            if criteria["Criteria"].lower() == "experience (years)" and "Experience mismatch" in criteria.get("Comments", ""):
                recommendations.append("Consider gaining more relevant experience.")
            elif criteria["Criteria"].lower() == "education" and criteria["Match"] == "No":
                if "any graduate" in job_details["education"].lower():
                    recommendations.append("Your education meets the general requirements.")
                else:
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
                # Skip excluded users
                if profile.user.username.lower() in EXCLUDED_USERS:
                    logger.debug(f"Skipping excluded user: {profile.user.username}")
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
                    "Candidate": profile.user.username,
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
                logger.debug(f"Resume Details for {profile.user.username}: {resume_details}")
                logger.debug(f"Compatibility Matrix: {compatibility_matrix}")
                logger.debug(f"Scores for {profile.user.username} and Job {job.id}: {scores}")

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

        # Check if the logged-in user is excluded
        if employee.username.lower() in EXCLUDED_USERS:
            raise ValueError("This user is not eligible for compatibility report generation.")

        # Fetch the logged-in employee's profile
        try:
            employee_profile = employee.userprofile
        except UserProfile.DoesNotExist:
            raise ValueError("Employee profile not found.")

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
                "Job": company_name,  # Use original company name here
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



import matplotlib.pyplot as plt
import math

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
