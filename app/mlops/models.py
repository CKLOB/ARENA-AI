from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Enum, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base
from app.shared.enums import ModelStatus


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("version_tag", name="uq_model_versions_version_tag"),
        Index(
            "uq_model_versions_champion",
            "status",
            unique=True,
            postgresql_where="status = 'CHAMPION'",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    version_tag: Mapped[str] = mapped_column(String(50), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    performance_metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[ModelStatus] = mapped_column(
        Enum(ModelStatus, native_enum=False, name="ck_model_versions_status"),
        nullable=False,
        default=ModelStatus.CHALLENGER,
        server_default=ModelStatus.CHALLENGER.value,
    )
