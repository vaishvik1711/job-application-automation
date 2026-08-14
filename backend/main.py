#!/usr/bin/env python3
"""
Main CLI entry point for Job Automation System.
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import load_settings
from database.database import init_db, close_db, get_session
from database.repositories import RepositoryFactory
from agents.profile_agent import ProfileAgent, CandidateProfile
from agents.discovery_agent import DiscoveryAgent, DiscoveryResult, create_discovery_agent
from agents.matching_agent import MatchingAgent, MatchResult
from resume import (
    parse_resume,
    ResumeAgent,
    ResumeValidator,
    ResumeGenerationResult,
    ValidationResult,
    create_resume_agent,
    create_resume_validator,
)
from orchestration.orchestrator import Orchestrator, PipelineConfig, PipelineMode, PipelineStats
from utils.logger import setup_logging, get_logger


app = typer.Typer(
    name="job-automation",
    help="AI Job Application Automation System",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def setup_environment():
    """Setup logging and environment."""
    setup_logging()


console = Console()
logger = get_logger(__name__)


def run_async(coro):
    """Run an async coroutine, handling existing event loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already in an event loop, create a new task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        asyncio.run(coro)


@app.command()
def setup(
    resume: Optional[str] = typer.Option(None, "--resume", help="Path to master resume"),
    experience: Optional[str] = typer.Option(None, "--experience", help="Path to additional experience notes"),
    interactive: bool = typer.Option(False, "--interactive", help="Run interactive setup"),
):
    """Initialize the system with your profile and resume."""
    setup_environment()
    console.print(Panel.fit("🎯 Job Automation Setup", style="bold blue"))

    run_async(_run_setup(resume, experience, interactive))


async def _run_setup(resume_path: Optional[str], experience_path: Optional[str], interactive: bool):
    """Run the setup process."""
    # Initialize database
    await init_db()
    console.print("✓ Database initialized")

    # Get resume path
    if not resume_path:
        if interactive:
            resume_path = Prompt.ask("Path to master resume (DOCX/PDF/TXT)")
        else:
            console.print("[red]Error: Resume path required[/red]")
            raise typer.Exit(1)

    resume_path = Path(resume_path).expanduser()
    if not resume_path.exists():
        console.print(f"[red]Error: Resume not found at {resume_path}[/red]")
        raise typer.Exit(1)

    # Get experience path
    if experience_path is None and interactive:
        experience_path = Prompt.ask("Path to additional experience notes (optional)", default="")
        experience_path = Path(experience_path).expanduser() if experience_path else None
    elif experience_path == "":
        experience_path = None

    # Parse and analyze resume
    console.print("\n[bold]Analyzing resume...[/bold]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing resume...", total=None)

        agent = ProfileAgent()
        profile = await agent.analyze_resume(str(resume_path), str(experience_path) if experience_path else None)

        progress.update(task, description="Saving profile...")
        await _save_profile_to_db(profile)

    console.print("\n✓ [green]Profile created successfully![/green]")

    # Show summary
    _display_profile_summary(profile)

    # Generate job filters
    console.print("\n[bold]Generating job search filters...[/bold]")
    filters = await agent.generate_job_filters(profile)
    _save_job_filters(filters)
    console.print("✓ Job filters saved to config/job_filters.yaml")

    # Save profile to data directory
    agent.save_profile(profile, "data/user_documents/candidate_profile.json")
    console.print("✓ Profile saved to data/user_documents/candidate_profile.json")

    console.print("\n[bold green]Setup complete![/bold green]")
    console.print("Next steps:")
    console.print("  1. Review config/job_filters.yaml and adjust if needed")
    console.print("  2. Run [cyan]python main.py profile[/cyan] to view your profile")
    console.print("  3. Run [cyan]python main.py search[/cyan] to find jobs")
    console.print("  4. Run [cyan]python main.py --dry-run[/cyan] for a test run")

    await close_db()


async def _save_profile_to_db(profile: CandidateProfile):
    """Save candidate profile to database."""
    async with get_session() as session:
        repos = RepositoryFactory(session)

        # Map Pydantic profile to SQLAlchemy model fields
        db_data = {
            "name": profile.name,
            "email": profile.email,
            "phone": profile.phone,
            "address": profile.address,
            "city": profile.city,
            "province": profile.province,
            "postal_code": profile.postal_code,
            "country": profile.country,
            "work_authorization": profile.work_authorization,
            "linkedin_url": profile.linkedin_url,
            "portfolio_url": profile.portfolio_url,
            "github_url": profile.github_url,
            "notice_period_weeks": profile.notice_period_weeks,
            "salary_expectation_min": profile.salary_expectation_min,
            "salary_expectation_max": profile.salary_expectation_max,
            "salary_currency": profile.salary_currency,
            "education": [e.model_dump() for e in profile.education],
            "certifications": [c.model_dump() for c in profile.certifications],
            "employment_history": [e.model_dump() for e in profile.employment_history],
            "skills": [s.name for s in profile.skills],
            "technical_skills": [s.name for s in profile.technical_skills],
            "business_skills": [s.name for s in profile.business_skills],
            "tools": [s.name for s in profile.tools],
            "programming_languages": [s.name for s in profile.programming_languages],
            "industries": profile.industries,
            "job_titles": profile.job_titles,
            "preferred_job_titles": profile.preferred_job_titles,
            "title_keywords": profile.title_keywords,
            "preferred_locations": profile.preferred_locations,
            "remote_preferences": profile.remote_preferences,
            "employment_preferences": profile.employment_preferences,
            "excluded_titles": profile.excluded_titles,
            "excluded_industries": profile.excluded_industries,
            "excluded_requirements": profile.excluded_requirements,
        }

        # Check if profile exists
        existing = await repos.candidates.get_profile()
        if existing:
            # Update existing
            await repos.candidates.update_profile(existing, **db_data)
        else:
            # Create new
            await repos.candidates.create_profile(**db_data)

        # Add experience notes
        for exp in profile.additional_experience:
            await repos.candidates.add_experience_note(
                profile_id=1,  # Will be updated after create
                original_text=exp.original_text,
                category=exp.category,
                verified=exp.verified,
                source=exp.source,
            )


def _save_job_filters(filters):
    """Save job filters to YAML."""
    import yaml
    with open("config/job_filters.yaml", "w") as f:
        yaml.dump(filters.model_dump(), f, default_flow_style=False, sort_keys=False)


def _display_profile_summary(profile: CandidateProfile):
    """Display profile summary."""
    table = Table(title="Candidate Profile Summary")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Name", profile.name)
    table.add_row("Email", profile.email)
    table.add_row("Phone", profile.phone or "Not set")
    table.add_row("Location", f"{profile.city}, {profile.province}" if profile.city else "Not set")
    table.add_row("Work Authorization", profile.work_authorization or "Not set")
    table.add_row("LinkedIn", profile.linkedin_url or "Not set")
    table.add_row("GitHub", profile.github_url or "Not set")
    table.add_row("Total Experience", f"{sum(1 for _ in profile.employment_history)} positions")
    table.add_row("Education", f"{len(profile.education)} entries")
    table.add_row("Certifications", f"{len(profile.certifications)} entries")
    table.add_row("Technical Skills", f"{len(profile.technical_skills)} skills")
    table.add_row("Tools", f"{len(profile.tools)} tools")
    table.add_row("Industries", f"{len(profile.industries)} industries")
    table.add_row("Preferred Titles", f"{len(profile.preferred_job_titles)} titles")
    table.add_row("Additional Experience", f"{len(profile.additional_experience)} notes")

    console.print(table)


@app.command()
def profile():
    """View current candidate profile."""
    setup_environment()

    run_async(_show_profile())


async def _show_profile():
    await init_db()
    async with get_session() as session:
        repos = RepositoryFactory(session)
        profile = await repos.candidates.get_profile()
        if profile:
            _display_db_profile(profile)
        else:
            console.print("[yellow]No profile found. Run 'python main.py setup' first.[/yellow]")
    await close_db()


def _display_db_profile(profile: CandidateProfile):
    """Display profile from database."""
    table = Table(title="Candidate Profile (from Database)")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Name", profile.name)
    table.add_row("Email", profile.email)
    table.add_row("Phone", profile.phone or "Not set")
    table.add_row("Work Authorization", profile.work_authorization or "Not set")
    table.add_row("Notice Period", f"{profile.notice_period_weeks} weeks")
    table.add_row("Salary Expectation", f"{profile.salary_expectation_min}-{profile.salary_expectation_max} {profile.salary_currency}" if profile.salary_expectation_min else "Not set")

    console.print(table)

    # Skills
    if profile.technical_skills:
        skills_table = Table(title="Technical Skills")
        skills_table.add_column("Skill", style="cyan")
        skills_table.add_column("Proficiency", style="yellow")
        skills_table.add_column("Source", style="dim")
        for skill in profile.technical_skills:
            skills_table.add_row(skill.name, skill.proficiency.value, skill.source)
        console.print(skills_table)


@app.command()
def search(
    dry_run_search: bool = typer.Option(False, "--dry-run-search", help="Run in dry-run mode"),
    limit: int = typer.Option(50, "--limit", help="Maximum jobs to find per source"),
):
    """Search for jobs using configured filters."""
    setup_environment()
    console.print(Panel.fit("🔍 Job Search", style="bold blue"))

    run_async(_run_search(dry_run_search, limit))


async def _run_search(dry_run: bool, limit: int):
    await init_db()

    agent = await create_discovery_agent()
    result = await agent.discover_jobs(limit_per_source=limit, dry_run=dry_run)
    await agent.close()

    # Display results
    table = Table(title="Discovery Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")

    table.add_row("Jobs Found", str(result.jobs_found))
    table.add_row("New Jobs Saved", str(result.jobs_new))
    table.add_row("Duplicates Removed", str(result.jobs_duplicate))
    table.add_row("Sources Used", ", ".join(result.sources_used))
    if result.errors:
        table.add_row("Errors", str(len(result.errors)))

    console.print(table)

    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  - {error}")

    if dry_run:
        console.print("\n[yellow]Dry run mode - no jobs saved to database[/yellow]")

    await close_db()


@app.command()
def analyze(
    job_id: Optional[int] = typer.Option(None, "--job-id-analyze", help="Specific job ID to analyze"),
    all_analyze: bool = typer.Option(False, "--all-analyze", help="Analyze all unmatched jobs"),
    limit: int = typer.Option(50, "--limit", help="Maximum jobs to analyze"),
    force_rematch: bool = typer.Option(False, "--force-rematch", help="Re-analyze already matched jobs"),
):
    """Analyze and score jobs against profile."""
    setup_environment()
    console.print(Panel.fit("📊 Job Analysis", style="bold blue"))

    run_async(_run_analyze(job_id, all_analyze, limit, force_rematch))


async def _run_analyze(job_id: Optional[int], all_jobs: bool, limit: int, force_rematch: bool = False):
    await init_db()

    agent = MatchingAgent()

    job_ids = [job_id] if job_id else None
    if not job_id and not all_jobs:
        console.print("[yellow]Specify --job-id-analyze or --all-analyze[/yellow]")
        await close_db()
        return

    result = await agent.match_jobs(job_ids=job_ids, limit=limit, force_rematch=force_rematch)

    # Display results
    table = Table(title="Matching Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")

    table.add_row("Jobs Processed", str(result.jobs_processed))
    table.add_row("Jobs Matched", str(result.jobs_matched))
    table.add_row("Qualified (APPLY)", str(result.jobs_qualified))
    table.add_row("Needs Review (REVIEW)", str(result.jobs_matched - result.jobs_qualified - result.jobs_rejected))
    table.add_row("Rejected (REJECT)", str(result.jobs_rejected))
    table.add_row("Failed", str(result.jobs_failed))

    console.print(table)

    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  - {error}")

    await close_db()


@app.command()
def resumes(
    job_id: Optional[int] = typer.Option(None, "--job-id", help="Specific job ID"),
    all_resumes: bool = typer.Option(False, "--all", help="Generate for all qualified jobs"),
    validate: bool = typer.Option(True, "--validate/--no-validate", help="Validate generated resumes"),
    master_resume: Optional[str] = typer.Option(None, "--master-resume", help="Path to master resume (default: data/master_resume/test_resume.docx)"),
):
    """Generate customized resumes for qualified jobs."""
    setup_environment()
    console.print(Panel.fit("📝 Resume Generation & Validation", style="bold blue"))

    run_async(_run_resumes(job_id, all_resumes, validate, master_resume))


async def _run_resumes(
    job_id: Optional[int],
    all_resumes: bool,
    validate: bool,
    master_resume: Optional[str],
):
    await init_db()

    if not master_resume:
        master_resume = "data/master_resume/test_resume.docx"

    master_path = Path(master_resume).expanduser()
    if not master_path.exists():
        console.print(f"[red]Error: Master resume not found at {master_path}[/red]")
        await close_db()
        return

    resume_agent = await create_resume_agent()
    validator = await create_resume_validator()

    results: List[ResumeGenerationResult] = []

    if job_id:
        # Generate for specific job
        console.print(f"Generating resume for job {job_id}...")
        result = await resume_agent.generate_resume(job_id, str(master_path))
        results.append(result)
        _display_resume_result(result)

        if validate and result.success:
            console.print("\nValidating resume...")
            val_result = await validator.validate_resume(result.resume_id, str(master_path))
            _display_validation_result(val_result)
    elif all_resumes:
        # Generate for all qualified jobs
        console.print("Generating resumes for all qualified jobs...")
        results = await resume_agent.generate_resumes_for_all_qualified(str(master_path))

        for result in results:
            _display_resume_result(result)

        if validate:
            console.print("\nValidating generated resumes...")
            for result in results:
                if result.success:
                    val_result = await validator.validate_resume(result.resume_id, str(master_path))
                    _display_validation_result(val_result)
    else:
        console.print("[yellow]Please specify --job-id or --all[/yellow]")

    await close_db()


def _display_resume_result(result: ResumeGenerationResult):
    """Display resume generation result."""
    if result.success:
        table = Table(title="Resume Generated", show_header=True)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Path", result.resume_path or "N/A")
        table.add_row("Version", str(result.version))
        table.add_row("Resume ID", str(result.resume_id))
        console.print(table)
    else:
        console.print(f"[red]Failed: {', '.join(result.errors)}[/red]")


def _display_validation_result(result: ValidationResult):
    """Display validation result."""
    table = Table(title="Validation Result", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Score", style="yellow")
    table.add_row("Overall", f"{result.validation_score:.1f}/100")
    table.add_row("Truthfulness", f"{result.truthfulness_score}/100")
    table.add_row("Format", f"{result.format_score}/100")
    table.add_row("Relevance", f"{result.relevance_score}/100")

    if result.issues:
        table.add_row("Issues", str(len(result.issues)))
        for issue in result.issues[:3]:
            console.print(f"  [yellow]• {issue.get('message', issue)}[/yellow]")

    console.print(table)


@app.command()
def apply(
    job_id: Optional[int] = typer.Option(None, "--job-id-apply", help="Specific job ID to apply"),
    auto_submit: bool = typer.Option(False, "--auto-submit", help="Auto-submit applications"),
    manual_mode: bool = typer.Option(False, "--manual-mode", help="Manual mode - stop before submit"),
):
    """Apply to jobs."""
    setup_environment()
    console.print(Panel.fit("📤 Job Application", style="bold blue"))

    run_async(_run_apply())


async def _run_apply():
    await init_db()
    console.print("[yellow]Application automation not yet implemented (Phases 5-7)[/yellow]")
    await close_db()


@app.command()
def run(
    dry_run_pipeline: bool = typer.Option(False, "--dry-run-pipeline", help="Run full pipeline without submitting"),
    manual_mode_pipeline: bool = typer.Option(False, "--manual-mode-pipeline", help="Manual mode - review before submit"),
    auto_mode_pipeline: bool = typer.Option(False, "--auto-mode-pipeline", help="Auto mode - submit automatically"),
):
    """Run the complete automation pipeline."""
    setup_environment()

    mode = "DRY RUN" if dry_run_pipeline else "MANUAL" if manual_mode_pipeline else "AUTO" if auto_mode_pipeline else "INTERACTIVE"
    console.print(Panel.fit(f"🚀 Pipeline Run - {mode} Mode", style="bold green"))

    run_async(_run_pipeline(dry_run_pipeline, manual_mode_pipeline, auto_mode_pipeline))


async def _run_pipeline(
    dry_run_pipeline: bool = typer.Option(False, "--dry-run-pipeline", help="Run full pipeline without submitting"),
    manual_mode_pipeline: bool = typer.Option(False, "--manual-mode-pipeline", help="Manual mode - review before submit"),
    auto_mode_pipeline: bool = typer.Option(False, "--auto-mode-pipeline", help="Auto mode - submit automatically"),
):
    """Run the complete automation pipeline using the Phase 8 orchestrator."""
    await init_db()

    # Determine pipeline mode
    if dry_run_pipeline:
        mode = "DRY RUN"
        pipeline_mode = PipelineMode.DRY_RUN
    elif manual_mode_pipeline:
        mode = "MANUAL"
        pipeline_mode = PipelineMode.MANUAL
    elif auto_mode_pipeline:
        mode = "AUTO"
        pipeline_mode = PipelineMode.AUTO
    else:
        mode = "INTERACTIVE"
        pipeline_mode = PipelineMode.INTERACTIVE

    console.print(Panel.fit(f"���🚀 Pipeline Run - {mode} Mode", style="bold green"))

    try:
        # Run the pipeline using the orchestrator
        async with Orchestrator(
            PipelineConfig(
                mode=pipeline_mode,
                dry_run_search=dry_run_pipeline,  # For search phase dry run
                # Other config values can be loaded from settings or use defaults
            )
        ) as orchestrator:
            stats = await orchestrator.run_pipeline()

            # Display results
            _display_pipeline_stats(stats)

    except Exception as e:
        console.print(f"[red]Pipeline failed: {e}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        await close_db()


def _display_pipeline_stats(stats: PipelineStats):
    """Display pipeline execution statistics."""
    console.print("\n[bold]Pipeline Execution Complete[/bold]")

    # Create stats table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim")
    table.add_column("Value")

    table.add_row("Jobs Found", str(stats.jobs_found))
    table.add_row("New Jobs", str(stats.jobs_new))
    table.add_row("Jobs Analyzed", str(stats.jobs_analyzed))
    table.add_row("Jobs Qualified", str(stats.jobs_qualified))
    table.add_row("Resumes Generated", str(stats.resumes_generated))
    table.add_row("Resumes Validated", str(stats.resumes_validated))
    table.add_row("Applications Submitted", str(stats.applications_submitted))
    table.add_row("Applications Failed", str(stats.applications_failed))
    table.add_row("Human Interventions", str(stats.human_interventions))

    if stats.start_time and stats.end_time:
        duration = (stats.end_time - stats.start_time).total_seconds()
        table.add_row("Total Duration", f"{duration:.1f}s")

    console.print(table)

    # Show errors if any
    if stats.errors:
        console.print("\n[red]Errors Encountered:[/red]")
        for error in stats.errors:
            console.print(f"  • {error}")


@app.command()
def status():
    """Show current status and statistics."""
    setup_environment()

    run_async(_show_status())


async def _show_status():
    await init_db()
    async with get_session() as session:
        repos = RepositoryFactory(session)

        # Get statistics
        stats = await repos.statistics.get_or_create_today()

        # Get job counts by status
        from database.models import Job, JobStatus, Application, ApplicationStatus
        from sqlalchemy import select, func

        job_counts = {}
        for status in JobStatus:
            result = await session.execute(select(func.count(Job.id)).where(Job.status == status))
            job_counts[status.value] = result.scalar() or 0

        app_counts = {}
        for status in ApplicationStatus:
            result = await session.execute(select(func.count(Application.id)).where(Application.status == status))
            app_counts[status.value] = result.scalar() or 0

        # Display
        console.print(Panel.fit("📊 Job Automation Status", style="bold blue"))

        table = Table(title="Jobs")
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="white", justify="right")
        for status, count in job_counts.items():
            if count > 0:
                table.add_row(status.replace("_", " ").title(), str(count))
        console.print(table)

        table2 = Table(title="Applications")
        table2.add_column("Status", style="cyan")
        table2.add_column("Count", style="white", justify="right")
        for status, count in app_counts.items():
            if count > 0:
                table2.add_row(status.replace("_", " ").title(), str(count))
        console.print(table2)

        # Daily stats
        stats_table = Table(title="Today's Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white", justify="right")
        stats_table.add_row("Jobs Found", str(stats.jobs_found))
        stats_table.add_row("Duplicates Removed", str(stats.duplicates_removed))
        stats_table.add_row("Jobs Qualified", str(stats.jobs_qualified))
        stats_table.add_row("Resumes Created", str(stats.resumes_created))
        stats_table.add_row("Resumes Validated", str(stats.resumes_validated))
        stats_table.add_row("Applications Submitted", str(stats.applications_submitted))
        stats_table.add_row("Failed", str(stats.applications_failed))
        stats_table.add_row("Human Intervention", str(stats.human_intervention_required))
        stats_table.add_row("Avg Match Score", f"{stats.average_match_score:.1f}%" if stats.average_match_score else "N/A")
        console.print(stats_table)

    await close_db()


@app.command()
def export(
    output: str = typer.Option("output/job_applications.xlsx", "--output", help="Output Excel file"),
):
    """Export application data to Excel."""
    setup_environment()
    console.print(Panel.fit("📈 Export to Excel", style="bold blue"))

    run_async(_run_export(output))


async def _run_export(output: str):
    await init_db()
    try:
        from excel import export_to_excel
        file_path = await export_to_excel(output)
        console.print(f"✓ [green]Excel exported to {file_path}[/green]")
    except Exception as e:
        console.print(f"[red]Export failed: {e}[/red]")
        import traceback
        traceback.print_exc()
    await close_db()


@app.command()
def config(
    show: bool = typer.Option(False, "--config-show", help="Show current configuration"),
    edit: bool = typer.Option(False, "--config-edit", help="Edit configuration"),
):
    """View or edit configuration."""
    setup_environment()

    if show:
        import yaml
        with open("config/settings.yaml", "r") as f:
            settings = yaml.safe_load(f)
        console.print(yaml.dump(settings, default_flow_style=False))
    elif edit:
        import subprocess
        subprocess.run(["code", "config/settings.yaml"])
    else:
        console.print("Use --config-show or --config-edit")


if __name__ == "__main__":
    app()