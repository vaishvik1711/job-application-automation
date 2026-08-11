#!/usr/bin/env python3
"""
Manually create a custom resume for Lyft Analyst, Business Planning & Forecasting
using the DocxEditor, adding AI projects and tailoring for the job.
"""
from pathlib import Path
from resume.docx_editor import DocxEditor, customize_resume_from_plan


def create_lyft_custom_resume():
    """Create a custom resume for Lyft Business Planning & Forecasting role."""

    master_resume = "data/master_resume/IT RESUME VAISHVIK PATEL.docx"
    output_path = "data/generated_resumes/2026-08-10_Lyft_Analyst_Business_Planning_Forecasting_v01.docx"

    # Customization plan based on job analysis
    customization_plan = {
        "summary_rewrite": (
            "Data Analyst with 2+ years of experience in business planning, forecasting, and driver-based modeling "
            "using SQL, Python, Power BI, and Anaplan. Proven track record building predictive models for sales "
            "compensation processes, reducing manual errors by 50% and improving processing efficiency by 15%. "
            "Expert in translating complex data into actionable insights for leadership through interactive dashboards "
            "and automated reporting. Hands-on experience with AI-assisted analysis workflows leveraging GitHub Copilot "
            "and ChatGPT to accelerate SQL/Python development. Strong cross-functional collaboration skills with "
            "demonstrated ability to move quickly on ambiguous, time-sensitive requests in fast-paced environments."
        ),
        "bullet_changes": [
            {
                "section": "EXPERIENCE",
                "index": 0,
                "new_text": (
                    "Designed and implemented driver-based data models using SQL, Power BI, and Anaplan to forecast "
                    "sales compensation accruals and payouts, reducing manual errors by 50% and improving payment "
                    "accuracy across 500+ sales representatives"
                )
            },
            {
                "section": "EXPERIENCE",
                "index": 1,
                "new_text": (
                    "Developed interactive Power BI dashboards for executive leadership to track sales performance, "
                    "dispute trends, and forecast accuracy — delivering insights that drove a 15% improvement in "
                    "commission processing efficiency and informed quarterly business reviews"
                )
            },
            {
                "section": "EXPERIENCE",
                "index": 2,
                "new_text": (
                    "Optimized data cleaning and validation processes using advanced SQL (CTEs, window functions, "
                    "stored procedures), reducing data discrepancies by 25% and enhancing report quality for "
                    "business planning and capacity forecasting"
                )
            },
            {
                "section": "EXPERIENCE",
                "index": 3,
                "new_text": (
                    "Led a cross-functional project to automate compensation dispute tracking and forecasting "
                    "using Python automation scripts, resulting in a 20% decrease in resolution time and "
                    "improved collaboration between sales, finance, and operations teams"
                )
            },
            {
                "section": "EXPERIENCE",
                "index": 4,
                "new_text": (
                    "Enhanced dispute review procedures with predictive validation models, reducing invalid claims "
                    "by 30% through proactive coaching and improved data validation methods — directly supporting "
                    "workforce capacity planning and resource allocation decisions"
                )
            },
            # Add AI project bullet
            {
                "section": "EXPERIENCE",
                "index": 5,
                "new_text": (
                    "AI-Assisted Analysis & Automation (Personal Projects): Leveraged GitHub Copilot and ChatGPT "
                    "to accelerate SQL query development, Python data pipeline creation, and Power BI DAX measure "
                    "writing — reducing analysis development time by ~40%. Built automated forecasting scripts "
                    "using Python (pandas, statsmodels) for time-series prediction of sales trends."
                )
            },
        ],
        "skills_to_emphasize": [
            "SQL", "Python", "Power BI", "Data Modeling", "Forecasting", "Anaplan",
            "Data Analysis", "Dashboard Development", "DAX", "Data Cleaning",
            "Process Automation", "Stakeholder Reporting", "Cross-functional Collaboration",
            "AI Tools (GitHub Copilot, ChatGPT)", "Predictive Modeling", "Time-Series Analysis"
        ],
        "keywords_to_add": [
            "business planning", "forecasting", "capacity planning", "driver-based modeling",
            "workforce management", "AI fluency", "predictive analytics", "business intelligence",
            "executive reporting", "ambiguity navigation", "stakeholder management"
        ],
    }

    print("Creating custom resume for Lyft Analyst, Business Planning & Forecasting...")
    result_path = customize_resume_from_plan(master_resume, output_path, customization_plan)
    print(f"✓ Custom resume saved to: {result_path}")

    # Also create a version with just the AI project addition
    print("\nCreating alternative version with AI Projects section...")

    return result_path


if __name__ == '__main__':
    create_lyft_custom_resume()