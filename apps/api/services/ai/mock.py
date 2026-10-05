"""
ReportForge AI - Mock AI Provider
Deterministic provider for testing and offline development.
"""

from typing import Optional, Type, TypeVar, Any, Dict
from pydantic import BaseModel
from apps.api.services.ai.base import AIProvider

T = TypeVar("T", bound=BaseModel)


class MockAIProvider(AIProvider):
    """Mock provider returning deterministic text and models."""

    def is_configured(self) -> bool:
        return True

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        **kwargs
    ) -> str:
        return f"[MOCK GENERATION] Content generated for: {prompt[:60]}..."

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs
    ) -> T:
        schema_name = getattr(response_schema, "__name__", "")

        # Specific mock handling for Stage 7 SectionGenerationOutput
        if schema_name == "SectionGenerationOutput":
            import re
            sec_id_m = re.search(r"section_id:\s*([^\n\r]+)", prompt)
            sec_id = sec_id_m.group(1).strip() if sec_id_m else "sec_1"

            title_m = re.search(r"title:\s*([^\n\r]+)", prompt)
            title = title_m.group(1).strip() if title_m else "Section Content"

            # Check for project title and description in prompt
            project_context = "Academic Project Research Study"
            if "attendance" in prompt.lower():
                project_context = "Automated Student Attendance Management System using edge camera facial recognition and RFID."
            elif "agriculture" in prompt.lower() or "irrigation" in prompt.lower():
                project_context = "Smart Agriculture Soil Moisture and Automated Drip Irrigation System using wireless sensor nodes."

            # Check for mapped evidence
            evidence_ids = []
            ev_m = re.search(r'"filename":\s*"([^"]+)"', prompt)
            if ev_m:
                evidence_ids.append(ev_m.group(1))

            data = {
                "section_id": sec_id,
                "section_title": title,
                "section_order": 1,
                "content_blocks": [
                    {
                        "block_type": "heading",
                        "text": title,
                        "level": 1,
                        "source_evidence_ids": []
                    },
                    {
                        "block_type": "paragraph",
                        "text": f"This section presents the comprehensive details of the {title.lower()} for {project_context}. The methodology and architecture follow institutional standards and verified requirements.",
                        "source_evidence_ids": evidence_ids
                    }
                ],
                "missing_information": [],
                "grounding_status": "grounded",
                "grounding_notes": [f"Grounded using verified facts from {project_context}"],
                "warnings": [],
                "research_marker_preserved": "research_required: True" in prompt or "research_required: true" in prompt,
                "visual_requirements": [],
                "word_count": 45
            }
            return response_schema.model_validate(data)

        fields = response_schema.model_fields
        dummy_data: Dict[str, Any] = {}
        for name, field in fields.items():
            if field.annotation == str:
                dummy_data[name] = f"Mock {name}"
            elif field.annotation == int:
                dummy_data[name] = 1
            elif field.annotation == float:
                dummy_data[name] = 1.0
            elif field.annotation == bool:
                dummy_data[name] = True
            elif field.annotation == list or getattr(field.annotation, "__origin__", None) == list:
                dummy_data[name] = []
            elif field.annotation == dict or getattr(field.annotation, "__origin__", None) == dict:
                dummy_data[name] = {}
        return response_schema.model_validate(dummy_data)
