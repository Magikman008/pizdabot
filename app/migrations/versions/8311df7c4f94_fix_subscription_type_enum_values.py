"""fix_subscription_type_enum_values

Revision ID: 8311df7c4f94
Revises: 37568f83ea79
Create Date: 2025-11-25 21:10:20.977541

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8311df7c4f94'
down_revision: Union[str, Sequence[str], None] = '37568f83ea79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Изменяем enum на правильные значения
    op.execute(
        "ALTER TABLE transactions MODIFY COLUMN type "
        "ENUM('yookassa', 'telegram_stars') NOT NULL"
    )

def downgrade():
    op.execute(
        "ALTER TABLE transactions MODIFY COLUMN type "
        "ENUM('telegram_stars') NOT NULL"
    )
