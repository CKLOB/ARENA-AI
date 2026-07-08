from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mlops.models import ModelVersion
from app.shared.enums import ModelStatus


class ModelVersionRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, model_version: ModelVersion) -> ModelVersion:
        self.db.add(model_version)
        self.db.flush()
        return model_version

    def get_by_version_tag(self, version_tag: str) -> ModelVersion | None:
        stmt = select(ModelVersion).where(ModelVersion.version_tag == version_tag)
        return self.db.scalar(stmt)

    def get_champion(self) -> ModelVersion | None:
        stmt = select(ModelVersion).where(ModelVersion.status == ModelStatus.CHAMPION.value)
        return self.db.scalar(stmt)
