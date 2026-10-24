"""Job application service managing lifecycle, form resolution, state machine, and audit events."""

import contextlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models.applications import Application, ApplicationEvent
from packages.core.models.jobs import Job
from packages.core.models.preferences import AnswerBank, AnswerEdit
from packages.core.models.profile import Profile
from packages.core.services.answer_resolver import (
    AnswerResolutionService,
    FieldDefinition,
    ResolvedPlan,
)
from packages.core.services.form_schema import FormSchemaService

VALID_STATUSES = {
    "draft",
    "preparing",
    "ready_for_review",
    "approved",
    "submitting",
    "submitted",
    "needs_user_action",
    "failed",
    "withdrawn",
    "interview",
    "offer",
    "rejected",
    "ghosted",
}


class ApplicationsService:
    """Core service for managing job application lifecycle, tracker, and review queue."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.form_service = FormSchemaService(db)
        self.resolver_service = AnswerResolutionService(db)

    async def create_or_get_application(
        self,
        user_id: str,
        job_id: uuid.UUID,
        channel: str = "extension",
        campaign_id: uuid.UUID | None = None,
    ) -> tuple[Application, ResolvedPlan]:
        """Create new application or return existing with resolved form plan."""
        # Check if already applied
        stmt = select(Application).where(
            Application.user_id == user_id, Application.job_id == job_id
        )
        res = await self.db.execute(stmt)
        existing = res.scalars().first()
        if existing:
            # Load stored plan from notes if available
            stored_plan: ResolvedPlan | None = None
            if existing.notes:
                try:
                    data = json.loads(existing.notes)
                    if "fields" in data:
                        stored_plan = ResolvedPlan(**data)
                except Exception:
                    pass
            if not stored_plan:
                job_res = await self.db.execute(select(Job).where(Job.id == job_id))
                job = job_res.scalars().first()
                if job:
                    form_schema = await self.form_service.get_or_extract_schema(job)
                    fields = [FieldDefinition(**f) for f in form_schema.schema_json]
                    p_res = await self.db.execute(select(Profile).where(Profile.user_id == user_id))
                    profile = p_res.scalars().first() or Profile(user_id=user_id)
                    stored_plan = await self.resolver_service.resolve_fields(
                        user_id=user_id, profile=profile, job=job, fields=fields
                    )
                else:
                    stored_plan = ResolvedPlan(fields=[], can_auto_submit=False, unresolved_count=0)
            return existing, stored_plan

        # Fetch job and profile
        job_res = await self.db.execute(select(Job).where(Job.id == job_id))
        job = job_res.scalars().first()
        if not job:
            raise HTTPException(status_code=404, detail="Job posting not found")

        p_res = await self.db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = p_res.scalars().first() or Profile(user_id=user_id)

        # Extract form schema & resolve fields
        form_schema = await self.form_service.get_or_extract_schema(job)
        fields = [FieldDefinition(**f) for f in form_schema.schema_json]
        plan = await self.resolver_service.resolve_fields(
            user_id=user_id, profile=profile, job=job, fields=fields
        )

        initial_status = "ready_for_review" if plan.unresolved_count > 0 else "approved"

        app_obj = Application(
            id=uuid.uuid4(),
            user_id=user_id,
            job_id=job_id,
            campaign_id=campaign_id,
            status=initial_status,
            channel=channel,
            application_url=getattr(job, "application_url", getattr(job, "apply_url", "")),
            notes=json.dumps(plan.model_dump()),
        )
        self.db.add(app_obj)

        event = ApplicationEvent(
            id=uuid.uuid4(),
            application_id=app_obj.id,
            type="created",
            payload={
                "channel": channel,
                "unresolved_count": plan.unresolved_count,
                "can_auto_submit": plan.can_auto_submit,
            },
            actor="user",
            created_at=datetime.now(UTC),
        )
        self.db.add(event)
        await self.db.flush()

        return app_obj, plan

    async def list_applications(
        self,
        user_id: str,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List user applications with job details and pagination."""
        query = (
            select(Application, Job)
            .join(Job, Application.job_id == Job.id)
            .where(Application.user_id == user_id)
        )

        if status:
            query = query.where(Application.status == status)

        if search:
            search_pat = f"%{search}%"
            query = query.where(
                or_(
                    Job.title.ilike(search_pat),
                    Job.company_name.ilike(search_pat),
                )
            )

        # Count total
        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        # Paginate
        query = query.order_by(desc(Application.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        results = (await self.db.execute(query)).all()

        items = []
        for app_obj, job_obj in results:
            company_title = getattr(job_obj, "company_name", None)
            if not company_title and getattr(job_obj, "company", None):
                company_title = job_obj.company.name
            loc = job_obj.locations[0] if getattr(job_obj, "locations", None) else getattr(job_obj, "location_city", "India")
            items.append(
                {
                    "id": str(app_obj.id),
                    "job_id": str(job_obj.id),
                    "job_title": job_obj.title,
                    "company_name": company_title or "Company",
                    "location": loc,
                    "salary_min_lpa": getattr(job_obj, "salary_min_lpa", None),
                    "salary_max_lpa": getattr(job_obj, "salary_max_lpa", None),
                    "status": app_obj.status,
                    "channel": app_obj.channel,
                    "application_url": app_obj.application_url,
                    "submitted_at": app_obj.submitted_at.isoformat() if app_obj.submitted_at else None,
                    "created_at": app_obj.created_at.isoformat(),
                }
            )

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_application_detail(
        self, user_id: str, application_id: uuid.UUID
    ) -> dict[str, Any]:
        """Fetch complete application details including timeline events and resolved form."""
        stmt = (
            select(Application, Job)
            .join(Job, Application.job_id == Job.id)
            .where(Application.id == application_id, Application.user_id == user_id)
        )
        res = await self.db.execute(stmt)
        record = res.first()
        if not record:
            raise HTTPException(status_code=404, detail="Application not found")

        app_obj, job_obj = record

        # Fetch events
        ev_stmt = (
            select(ApplicationEvent)
            .where(ApplicationEvent.application_id == application_id)
            .order_by(desc(ApplicationEvent.created_at))
        )
        ev_res = await self.db.execute(ev_stmt)
        events = ev_res.scalars().all()

        plan_dict = {}
        if app_obj.notes:
            with contextlib.suppress(Exception):
                plan_dict = json.loads(app_obj.notes)

        return {
            "id": str(app_obj.id),
            "status": app_obj.status,
            "channel": app_obj.channel,
            "application_url": app_obj.application_url,
            "submitted_at": app_obj.submitted_at.isoformat() if app_obj.submitted_at else None,
            "created_at": app_obj.created_at.isoformat(),
            "failure_reason": app_obj.failure_reason,
            "job": {
                "id": str(job_obj.id),
                "title": job_obj.title,
                "company_name": getattr(job_obj, "company_name", getattr(getattr(job_obj, "company", None), "name", "Company")),
                "location_city": job_obj.locations[0] if getattr(job_obj, "locations", None) else getattr(job_obj, "location_city", "India"),
                "is_remote": getattr(job_obj, "remote_mode", "onsite") in ("remote", "hybrid") or getattr(job_obj, "is_remote", False),
                "ats_type": getattr(job_obj, "ats_type", "generic"),
                "description": getattr(job_obj, "description_text", getattr(job_obj, "description", "")),
                "salary_min_lpa": getattr(job_obj, "salary_min_lpa", None),
                "salary_max_lpa": getattr(job_obj, "salary_max_lpa", None),
            },
            "plan": plan_dict,
            "events": [
                {
                    "id": str(e.id),
                    "type": e.type,
                    "payload": e.payload,
                    "actor": e.actor,
                    "created_at": e.created_at.isoformat(),
                }
                for e in events
            ],
        }

    async def update_status(
        self,
        user_id: str,
        application_id: uuid.UUID,
        new_status: str,
        actor: str = "user",
        notes: str | None = None,
        failure_reason: str | None = None,
    ) -> Application:
        """Update application status with audit event."""
        if new_status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")

        stmt = select(Application).where(
            Application.id == application_id, Application.user_id == user_id
        )
        res = await self.db.execute(stmt)
        app_obj = res.scalars().first()
        if not app_obj:
            raise HTTPException(status_code=404, detail="Application not found")

        old_status = app_obj.status
        app_obj.status = new_status
        if failure_reason:
            app_obj.failure_reason = failure_reason
        if new_status == "submitted" and not app_obj.submitted_at:
            app_obj.submitted_at = datetime.now(UTC)

        event = ApplicationEvent(
            id=uuid.uuid4(),
            application_id=app_obj.id,
            type="status_changed",
            payload={"from": old_status, "to": new_status, "notes": notes},
            actor=actor,
            created_at=datetime.now(UTC),
        )
        self.db.add(event)
        await self.db.flush()
        return app_obj

    async def edit_answer(
        self,
        user_id: str,
        application_id: uuid.UUID,
        field_id: str,
        new_value: Any,
        save_to_answer_bank: bool = False,
    ) -> dict[str, Any]:
        """Update a specific field's answer, optionally persisting to AnswerBank and AnswerEdit."""
        stmt = select(Application).where(
            Application.id == application_id, Application.user_id == user_id
        )
        res = await self.db.execute(stmt)
        app_obj = res.scalars().first()
        if not app_obj:
            raise HTTPException(status_code=404, detail="Application not found")

        plan_dict: dict[str, Any] = {}
        if app_obj.notes:
            with contextlib.suppress(Exception):
                plan_dict = json.loads(app_obj.notes)

        fields = plan_dict.get("fields", [])
        target_field = None
        for f in fields:
            if f.get("field_id") == field_id:
                old_val = f.get("value")
                f["value"] = new_value
                f["source"] = "user"
                f["confidence"] = 1.0
                f["needs_review"] = False
                target_field = f

                # Record personalization edit
                edit = AnswerEdit(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    application_id=application_id,
                    question_text=f.get("label", ""),
                    original_answer=str(old_val or ""),
                    edited_answer=str(new_value),
                    used_for_personalization=True,
                )
                self.db.add(edit)
                break

        if not target_field:
            raise HTTPException(status_code=404, detail=f"Field {field_id} not found in application plan")

        # Save to AnswerBank if requested
        if save_to_answer_bank:
            q_key = target_field.get("canonical_key") or target_field.get("field_id")
            q_label = target_field.get("label", "")
            ans_entry = AnswerBank(
                id=uuid.uuid4(),
                user_id=user_id,
                question_key=q_key,
                question_text=q_label,
                answer_text=str(new_value),
                source="user_edit",
                times_used=1,
                last_used_at=datetime.now(UTC),
            )
            self.db.add(ans_entry)

        # Recalculate unresolved count
        unresolved = sum(1 for f in fields if f.get("needs_review", False))
        plan_dict["unresolved_count"] = unresolved
        plan_dict["can_auto_submit"] = unresolved == 0
        app_obj.notes = json.dumps(plan_dict)

        if unresolved == 0 and app_obj.status == "needs_user_action":
            app_obj.status = "ready_for_review"

        await self.db.flush()
        return plan_dict
