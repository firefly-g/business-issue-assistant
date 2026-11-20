"""保留已有连接密文及运行方式，将原配置转为列表的第一项。"""

import sqlalchemy as sa

from alembic import op

revision = "926a0d21805e"
down_revision = "17d95ea021a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """迁移只复制连接密文，启动时无需访问供应商或加密密钥。"""
    op.create_table(
        "model_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
    )
    with op.batch_alter_table("model_settings") as batch:
        batch.add_column(sa.Column("profile_id", sa.String(36), nullable=True))
        batch.create_foreign_key(
            "fk_model_settings_profile", "model_profiles", ["profile_id"], ["id"]
        )
    op.execute(
        "INSERT INTO model_profiles (id, address, model, encrypted_key) "
        "SELECT 'legacy', address, model, encrypted_key FROM model_settings "
        "WHERE address <> '' AND model <> '' AND encrypted_key <> ''"
    )
    op.execute(
        "UPDATE model_settings SET profile_id = 'legacy' WHERE EXISTS (SELECT 1 FROM model_profiles)"
    )


def downgrade() -> None:
    """回退会移除备用配置，保留最后启用的连接及当前运行方式。"""
    with op.batch_alter_table("model_settings") as batch:
        batch.drop_constraint("fk_model_settings_profile", type_="foreignkey")
        batch.drop_column("profile_id")
    op.drop_table("model_profiles")
