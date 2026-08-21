"""
Form filler for job application forms.
Maps candidate profile data to form fields intelligently.
"""
import asyncio
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path

from browser.automation import BrowserAutomation
from utils.logger import get_logger
from utils.helpers import clean_text

logger = get_logger(__name__)


@dataclass
class FieldMapping:
    """Mapping between profile field and form field."""
    profile_field: str
    form_selectors: List[str]
    transform: Optional[Callable[[Any], str]] = None
    required: bool = False
    field_type: str = "text"  # text, email, phone, select, file, textarea, radio, checkbox


def _work_auth_to_choice(value: Any) -> str:
    """Collapse free-text work authorization ('Canadian citizen', 'PR',
    'authorized to work') onto Yes/No for ATS selects. Returns the original
    text when unsure — an unmatched select lands in fields_failed and gets
    human review instead of a wrong guess."""
    text = str(value or "").lower()
    if "not" in text or text.startswith("no ") or "sponsorship" in text:
        return "No"
    if any(k in text for k in ("citizen", "permanent resident", " pr", "authorized",
                               "eligible", "entitled", "yes", "can work")):
        return "Yes"
    return str(value or "")


@dataclass
class FormFillResult:
    """Result of form filling."""
    success: bool
    fields_filled: int
    fields_failed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class FormFiller:
    """
    Intelligent form filler that maps candidate profile to job application forms.
    Uses multiple selector strategies and handles various form field types.
    """

    def __init__(self, automation: BrowserAutomation):
        self.automation = automation
        self.field_mappings = self._build_field_mappings()

    def _build_field_mappings(self) -> List[FieldMapping]:
        """Build comprehensive field mappings."""
        return [
            # Personal Information
            FieldMapping(
                profile_field="first_name",
                form_selectors=[
                    "input[name*='first']",
                    "input[id*='first']",
                    "input[placeholder*='first' i]",
                    "input[name='givenName']",
                    "input[name='fname']",
                ],
                required=True,
            ),
            FieldMapping(
                profile_field="last_name",
                form_selectors=[
                    "input[name*='last']",
                    "input[id*='last']",
                    "input[placeholder*='last' i]",
                    "input[name='familyName']",
                    "input[name='lname']",
                ],
                required=True,
            ),
            FieldMapping(
                profile_field="email",
                form_selectors=[
                    "input[type='email']",
                    "input[name*='email']",
                    "input[id*='email']",
                    "input[placeholder*='email' i]",
                    "input[name='emailAddress']",
                ],
                required=True,
                field_type="email",
            ),
            FieldMapping(
                profile_field="phone",
                form_selectors=[
                    "input[type='tel']",
                    "input[name*='phone']",
                    "input[id*='phone']",
                    "input[placeholder*='phone' i]",
                    "input[name*='mobile']",
                    "input[name*='telephone']",
                ],
                field_type="phone",
            ),
            FieldMapping(
                profile_field="address",
                form_selectors=[
                    "input[name*='address']",
                    "input[id*='address']",
                    "input[placeholder*='address' i]",
                    "input[name='streetAddress']",
                    "textarea[name*='address']",
                ],
                field_type="textarea",
            ),
            FieldMapping(
                profile_field="city",
                form_selectors=[
                    "input[name*='city']",
                    "input[id*='city']",
                    "input[placeholder*='city' i]",
                    "input[name='addressLocality']",
                ],
            ),
            FieldMapping(
                profile_field="province",
                form_selectors=[
                    "select[name*='province']",
                    "select[name*='state']",
                    "select[id*='province']",
                    "select[id*='state']",
                    "input[name*='province']",
                    "input[name*='state']",
                ],
                field_type="select",
            ),
            FieldMapping(
                profile_field="postal_code",
                form_selectors=[
                    "input[name*='postal']",
                    "input[name*='zip']",
                    "input[id*='postal']",
                    "input[id*='zip']",
                    "input[placeholder*='postal' i]",
                    "input[placeholder*='zip' i]",
                    "input[name='postalCode']",
                ],
            ),
            FieldMapping(
                profile_field="country",
                form_selectors=[
                    "select[name*='country']",
                    "select[id*='country']",
                ],
                field_type="select",
                transform=lambda x: "Canada" if x and "canada" in x.lower() else x,
            ),
            FieldMapping(
                profile_field="linkedin_url",
                form_selectors=[
                    "input[name*='linkedin']",
                    "input[id*='linkedin']",
                    "input[placeholder*='linkedin' i]",
                    "input[name='linkedinUrl']",
                ],
            ),
            FieldMapping(
                profile_field="portfolio_url",
                form_selectors=[
                    "input[name*='portfolio']",
                    "input[id*='portfolio']",
                    "input[placeholder*='portfolio' i]",
                    "input[name*='website']",
                    "input[name*='personal']",
                ],
            ),
            FieldMapping(
                profile_field="github_url",
                form_selectors=[
                    "input[name*='github']",
                    "input[id*='github']",
                    "input[placeholder*='github' i]",
                ],
            ),

            # Work Authorization
            FieldMapping(
                profile_field="work_authorization",
                form_selectors=[
                    "select[name*='work']",
                    "select[name*='visa']",
                    "select[name*='authorization']",
                    "select[id*='work']",
                    "select[id*='visa']",
                ],
                transform=_work_auth_to_choice,
                field_type="select",
            ),
            FieldMapping(
                profile_field="notice_period_weeks",
                form_selectors=[
                    "input[name*='notice']",
                    "input[id*='notice']",
                    "input[placeholder*='notice' i]",
                    "select[name*='notice']",
                ],
                transform=lambda x: str(x) if x else "",
            ),
            FieldMapping(
                profile_field="salary_expectation_min",
                form_selectors=[
                    "input[name*='salary']",
                    "input[name*='compensation']",
                    "input[name*='expected']",
                    "input[id*='salary']",
                    "input[placeholder*='salary' i]",
                ],
                transform=lambda x: str(x) if x else "",
            ),

            # Resume/CV Upload
            FieldMapping(
                profile_field="resume_file",
                form_selectors=[
                    "input[type='file'][accept*='pdf']",
                    "input[type='file'][accept*='doc']",
                    "input[name*='resume']",
                    "input[name*='cv']",
                    "input[id*='resume']",
                    "input[id*='cv']",
                    "input[accept*='.pdf']",
                    "input[accept*='.doc']",
                ],
                field_type="file",
                required=True,
            ),
            FieldMapping(
                profile_field="cover_letter_file",
                form_selectors=[
                    "input[type='file'][name*='cover']",
                    "input[type='file'][id*='cover']",
                    "input[name*='coverLetter']",
                ],
                field_type="file",
            ),

            # Education
            FieldMapping(
                profile_field="education_summary",
                form_selectors=[
                    "textarea[name*='education']",
                    "textarea[id*='education']",
                    "input[name*='degree']",
                    "input[name*='university']",
                ],
                field_type="textarea",
            ),

            # Experience
            FieldMapping(
                profile_field="experience_summary",
                form_selectors=[
                    "textarea[name*='experience']",
                    "textarea[id*='experience']",
                    "textarea[name*='work']",
                    "textarea[id*='work']",
                ],
                field_type="textarea",
            ),
            FieldMapping(
                profile_field="current_title",
                form_selectors=[
                    "input[name*='current']",
                    "input[name*='title']",
                    "input[id*='current']",
                    "input[id*='title']",
                    "input[placeholder*='current' i]",
                ],
            ),
            FieldMapping(
                profile_field="current_company",
                form_selectors=[
                    "input[name*='company']",
                    "input[name*='employer']",
                    "input[id*='company']",
                    "input[id*='employer']",
                ],
            ),
        ]

    def _get_profile_value(self, profile: Dict[str, Any], field: str) -> Any:
        """Extract value from profile dict using dot notation."""
        keys = field.split(".")
        value = profile
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
            if value is None:
                return None
        return value

    def _transform_value(self, value: Any, transform: Optional[Callable], field_type: str) -> str:
        """Transform value based on field type and custom transform."""
        if value is None:
            return ""

        if transform:
            value = transform(value)

        if field_type == "phone":
            # Normalize phone number
            phone = re.sub(r"\D", "", str(value))
            if len(phone) == 10:
                return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
            elif len(phone) == 11 and phone.startswith("1"):
                return f"+1 ({phone[1:4]}) {phone[4:7]}-{phone[7:]}"
            return str(value)

        if field_type == "select":
            return str(value)

        return clean_text(str(value))

    async def fill_form(self, profile: Dict[str, Any], resume_path: Optional[str] = None,
                       cover_letter_path: Optional[str] = None) -> FormFillResult:
        """Fill the application form with profile data."""
        result = FormFillResult(success=False, fields_filled=0)

        # Handle file uploads first
        if resume_path:
            await self._upload_file("resume_file", resume_path, result)

        if cover_letter_path:
            await self._upload_file("cover_letter_file", cover_letter_path, result)

        # Fill all mapped fields
        for mapping in self.field_mappings:
            if mapping.field_type == "file":
                continue  # Already handled

            value = self._get_profile_value(profile, mapping.profile_field)
            if value is None:
                if mapping.required:
                    result.fields_failed.append(mapping.profile_field)
                    result.errors.append(f"Required field missing: {mapping.profile_field}")
                continue

            transformed_value = self._transform_value(value, mapping.transform, mapping.field_type)
            if not transformed_value:
                continue

            success = await self._fill_field(mapping, transformed_value)
            if success:
                result.fields_filled += 1
            else:
                result.fields_failed.append(mapping.profile_field)

        # Handle popups after form filling
        await self.automation.handle_popups()

        result.success = result.fields_filled > 0 and len(result.fields_failed) == 0
        return result

    async def _fill_field(self, mapping: FieldMapping, value: str) -> bool:
        """Fill a single field using multiple selector strategies."""
        for selector in mapping.form_selectors:
            try:
                element = await self.automation.page.query_selector(selector)
                if element and await element.is_visible():
                    if mapping.field_type == "select":
                        success = await self.automation.select_option(selector, value)
                    elif mapping.field_type == "textarea":
                        success = await self.automation.fill_field(selector, value)
                    elif mapping.field_type in ("radio", "checkbox"):
                        success = await self.automation.click_element(selector)
                    else:
                        success = await self.automation.fill_field(selector, value)

                    if success:
                        logger.debug(f"Filled {mapping.profile_field} with selector {selector}")
                        await self.automation.wait_random(100, 300)
                        return True
            except Exception as e:
                logger.debug(f"Selector {selector} failed for {mapping.profile_field}: {e}")
                continue

        logger.warning(f"Could not fill field: {mapping.profile_field}")
        return False

    async def _upload_file(self, field_name: str, file_path: str, result: FormFillResult):
        """Upload a file to the form."""
        mapping = next((m for m in self.field_mappings if m.profile_field == field_name), None)
        if not mapping:
            return

        path = Path(file_path)
        if not path.exists():
            result.errors.append(f"File not found: {file_path}")
            return

        for selector in mapping.form_selectors:
            try:
                # Probe first — page.set_input_files waits out its full
                # default timeout (30s) per absent selector, which turns a
                # missing field into minutes of dead air.
                element = await self.automation.page.query_selector(selector)
                if not element:
                    continue
                success = await self.automation.upload_file(selector, str(path.absolute()))
                if success:
                    result.fields_filled += 1
                    logger.debug(f"Uploaded {field_name}: {file_path}")
                    await self.automation.wait_random(500, 1000)
                    return
            except Exception as e:
                logger.debug(f"Upload selector {selector} failed: {e}")
                continue

        result.fields_failed.append(field_name)
        result.errors.append(f"Could not upload {field_name}")

    async def detect_form_fields(self) -> List[Dict[str, Any]]:
        """Detect all form fields on the current page."""
        fields = await self.automation.evaluate("""
            () => {
                const fields = [];
                const inputs = document.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    if (input.type === 'hidden' || input.type === 'submit' || input.type === 'button') return;
                    fields.push({
                        tag: input.tagName.toLowerCase(),
                        type: input.type,
                        name: input.name,
                        id: input.id,
                        placeholder: input.placeholder,
                        ariaLabel: input.getAttribute('aria-label'),
                        required: input.required,
                        value: input.value,
                        options: Array.from(input.options || []).map(o => ({value: o.value, text: o.text}))
                    });
                });
                return fields;
            }
        """)
        return fields

    async def smart_fill(self, profile: Dict[str, Any], resume_path: Optional[str] = None) -> FormFillResult:
        """Smart fill using detected form fields."""
        # First detect all fields
        detected_fields = await self.detect_form_fields()

        # Build dynamic mappings based on detected fields
        dynamic_mappings = self._build_dynamic_mappings(detected_fields, profile)

        result = FormFillResult(success=False, fields_filled=0)

        # Upload resume if provided
        if resume_path:
            await self._upload_file("resume_file", resume_path, result)

        # Fill dynamic mappings
        for mapping in dynamic_mappings:
            value = self._get_profile_value(profile, mapping.profile_field)
            if value is None:
                continue

            transformed_value = self._transform_value(value, mapping.transform, mapping.field_type)
            if not transformed_value:
                continue

            success = await self._fill_field(mapping, transformed_value)
            if success:
                result.fields_filled += 1
            else:
                result.fields_failed.append(mapping.profile_field)

        await self.automation.handle_popups()
        result.success = result.fields_filled > 0
        return result

    def _build_dynamic_mappings(self, detected_fields: List[Dict], profile: Dict) -> List[FieldMapping]:
        """Build field mappings based on detected form fields."""
        mappings = []

        # Keywords for field matching
        field_keywords = {
            "first_name": ["first", "given", "fname", "christian"],
            "last_name": ["last", "family", "surname", "lname"],
            "email": ["email", "mail"],
            "phone": ["phone", "tel", "mobile", "cell", "telephone"],
            "address": ["address", "street", "line1", "line2"],
            "city": ["city", "town", "locality"],
            "province": ["province", "state", "region"],
            "postal_code": ["postal", "zip", "postcode"],
            "country": ["country", "nation"],
            "linkedin_url": ["linkedin", "linked_in"],
            "portfolio_url": ["portfolio", "website", "personal", "web"],
            "github_url": ["github", "git_hub"],
            "work_authorization": ["work", "visa", "authorization", "citizen", "eligible"],
            "notice_period_weeks": ["notice", "availability", "start"],
            "salary_expectation_min": ["salary", "compensation", "expected", "pay", "rate"],
            "current_title": ["current", "title", "position", "role"],
            "current_company": ["company", "employer", "organization"],
        }

        for field in detected_fields:
            field_text = " ".join(filter(None, [
                field.get("name", ""),
                field.get("id", ""),
                field.get("placeholder", ""),
                field.get("ariaLabel", ""),
            ])).lower()

            # Match field to profile field
            matched_profile_field = None
            for profile_field, keywords in field_keywords.items():
                if any(kw in field_text for kw in keywords):
                    matched_profile_field = profile_field
                    break

            if matched_profile_field:
                # Determine field type
                field_type = field.get("type", "text")
                if field["tag"] == "select":
                    field_type = "select"
                elif field["tag"] == "textarea":
                    field_type = "textarea"
                elif field_type in ("radio", "checkbox"):
                    pass

                # Build selectors
                selectors = []
                if field.get("id"):
                    selectors.append(f"#{field['id']}")
                if field.get("name"):
                    selectors.append(f"[name='{field['name']}']")

                mapping = FieldMapping(
                    profile_field=matched_profile_field,
                    form_selectors=selectors,
                    field_type=field_type,
                    required=field.get("required", False),
                )
                mappings.append(mapping)

        return mappings