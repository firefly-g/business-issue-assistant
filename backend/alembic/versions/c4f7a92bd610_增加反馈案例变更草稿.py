"""新增反馈草稿与不可变整理依据，不回填或改写已有案例和反馈。"""

import sqlalchemy as sa

from alembic import op

revision = "c4f7a92bd610"
down_revision = "926a0d21805e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """仅创建新表，唯一反馈约束在多实例重复生成时保护业务幂等。"""
    op.create_table(
        "feedback_drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("question_id", sa.String(36), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("feedback_id", sa.String(36), sa.ForeignKey("feedback.id"), nullable=False),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("analysis_runs.id"), nullable=False),
        sa.Column("business", sa.String(80), nullable=False),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("question_source_id", sa.String(36), sa.ForeignKey("sources.id")),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("target_case_id", sa.String(36), sa.ForeignKey("cases.id")),
        sa.Column("target_version", sa.Integer()),
        sa.Column("base_snapshot", sa.JSON()),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("generated_content", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("history", sa.JSON(), nullable=False),
        sa.Column("rule_version", sa.String(80), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("published_case_id", sa.String(36), sa.ForeignKey("cases.id")),
        sa.Column("published_case_version", sa.Integer()),
        sa.Column("published_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.UniqueConstraint("feedback_id", name="uq_feedback_drafts_feedback"),
    )


def downgrade() -> None:
    """回退移除草稿及整理审计；已经发布的案例和历史版本继续保留。"""
    op.drop_table("feedback_drafts")
