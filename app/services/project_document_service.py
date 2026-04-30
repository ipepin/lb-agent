from __future__ import annotations

from pathlib import Path
import shutil
from typing import Sequence

from app.config import AppConfig
from app.db import crud
from app.db.models import ProjectDocumentModel
from app.schemas.entities import ProjectDocument
from app.utils.file_utils import ensure_directory, sanitize_filename


class ProjectDocumentService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.base_dir = self.config.data_dir / "project_documents"
        ensure_directory(self.base_dir)

    def list_documents(self, project_id: int | None = None) -> Sequence[ProjectDocumentModel]:
        return crud.list_project_documents(self.config, project_id=project_id)

    def get_document(self, document_id: int) -> ProjectDocumentModel | None:
        return crud.get_project_document(self.config, document_id)

    def save_document(
        self,
        *,
        project_id: int,
        filename: str,
        content: bytes,
        title: str = "",
        document_type: str = "general",
        source_email_id: str | None = None,
        worker_id: int | None = None,
        work_date: str | None = None,
    ) -> int:
        project_dir = self.base_dir / str(project_id)
        ensure_directory(project_dir)
        safe_name = sanitize_filename(filename)
        target_path = project_dir / safe_name
        target_path.write_bytes(content)

        document = ProjectDocument(
            project_id=project_id,
            title=(title or safe_name).strip(),
            file_path=str(target_path),
            document_type=document_type,
            source_email_id=source_email_id,
            worker_id=worker_id,
            work_date=work_date,
        )
        return crud.create_project_document(self.config, document)

    def import_email_attachments(self, *, project_id: int, email_id: str) -> list[int]:
        email = crud.get_email(self.config, email_id)
        if email is None:
            return []

        created_ids: list[int] = []
        for attachment_path in email.attachments:
            path = Path(attachment_path)
            if not path.exists():
                continue
            created_ids.append(
                self.save_document(
                    project_id=project_id,
                    filename=path.name,
                    content=path.read_bytes(),
                    title=path.name,
                    document_type=self._infer_document_type(path.name),
                    source_email_id=email_id,
                )
            )
        return created_ids

    def delete_documents_for_project(self, project_id: int) -> int:
        documents = list(self.list_documents(project_id))
        for document in documents:
            path = Path(document.file_path)
            if path.exists():
                path.unlink()

        project_dir = self.base_dir / str(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)

        return crud.delete_project_documents_by_project(self.config, project_id)

    def _infer_document_type(self, filename: str) -> str:
        lower_name = filename.lower()
        if lower_name.endswith((".jpg", ".jpeg", ".png", ".webp", ".heic")):
            return "photo"
        if lower_name.endswith(".pdf"):
            return "invoice"
        return "general"
