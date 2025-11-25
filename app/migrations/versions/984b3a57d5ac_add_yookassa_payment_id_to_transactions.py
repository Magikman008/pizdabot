"""add_yookassa_payment_id_to_transactions

Revision ID: 984b3a57d5ac
Revises: 321b13fd8e25
Create Date: 2025-11-25 20:35:12.818528

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '984b3a57d5ac'
down_revision: Union[str, Sequence[str], None] = '321b13fd8e25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Добавляем колонку yookassa_payment_id
    op.add_column(
        'transactions',
        sa.Column('yookassa_payment_id', sa.String(255), nullable=True)
    )


def downgrade():
    # Удаляем колонку при откате
    op.drop_column('transactions', 'yookassa_payment_id')