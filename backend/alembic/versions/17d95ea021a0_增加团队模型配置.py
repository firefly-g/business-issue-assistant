"""增加团队模型配置，旧库仍直接沿用环境变量，无需回填。"""

import sqlalchemy as sa

from alembic import op

revision = "17d95ea021a0"
down_revision = "88ea6388b127"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """独立创建配置表，不触碰案例和账号历史数据。"""
    op.create_table(
        "model_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_model_settings_singleton"),
    )


def downgrade() -> None:
    """移除网页配置，运行方式恢复从环境变量读取。"""
    op.drop_table("model_settings")
