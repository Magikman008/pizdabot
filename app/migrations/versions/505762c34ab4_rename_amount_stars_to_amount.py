"""rename_amount_stars_to_amount

Revision ID: 505762c34ab4
Revises: 8311df7c4f94
Create Date: 2025-11-25 21:30:21.013137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '505762c34ab4'
down_revision: Union[str, Sequence[str], None] = '8311df7c4f94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Переименовываем колонку
    op.alter_column(
        'transactions',
        'amount_stars',
        new_column_name='amount',
        existing_type=sa.Numeric(10, 2),
        existing_nullable=False
    )


def downgrade():
    # Откат
    op.alter_column(
        'transactions',
        'amount',
        new_column_name='amount_stars',
        existing_type=sa.Numeric(10, 2),
        existing_nullable=False
    )