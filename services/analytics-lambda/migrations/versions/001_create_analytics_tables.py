"""Create raw_metrics, processed_metrics, and aggregations tables.

Revision ID: 001
Revises: None
Create Date: 2026-03-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raw_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("metric_type", sa.String(30), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "metric_type", "recorded_at", name="uq_raw_user_type_time"),
    )
    op.create_index("idx_raw_metrics_user_type_time", "raw_metrics", ["user_id", "metric_type", "recorded_at"])

    op.create_table(
        "processed_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("metric_type", sa.String(30), nullable=False),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("avg_value", sa.Float, nullable=False),
        sa.Column("min_value", sa.Float, nullable=False),
        sa.Column("max_value", sa.Float, nullable=False),
        sa.Column("sample_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "metric_type", "period", "period_start", name="uq_proc_user_type_period"),
    )
    op.create_index("idx_processed_metrics_user_period", "processed_metrics", ["user_id", "period", "period_start"])

    op.create_table(
        "aggregations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("insight_type", sa.String(20), nullable=False),
        sa.Column("metric_type", sa.String(30), nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_aggregations_user_time", "aggregations", ["user_id", "generated_at"])


def downgrade() -> None:
    op.drop_table("aggregations")
    op.drop_table("processed_metrics")
    op.drop_table("raw_metrics")
