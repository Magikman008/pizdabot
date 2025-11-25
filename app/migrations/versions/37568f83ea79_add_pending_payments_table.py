"""add_pending_payments_table

Revision ID: 37568f83ea79
Revises: 984b3a57d5ac
Create Date: 2025-11-25 20:58:02.130509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37568f83ea79'
down_revision: Union[str, Sequence[str], None] = '984b3a57d5ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'pending_payments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('payment_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('payment_id'),
        mysql_charset='utf8mb4'
    )
    op.create_index('ix_pending_payments_payment_id', 'pending_payments', ['payment_id'])


def downgrade():
    op.drop_index('ix_pending_payments_payment_id', 'pending_payments')
    op.drop_table('pending_payments')
