"""Legg til product_id i SelectedProduct

Revision ID: 63be3dd5cccd
Revises: 6f0313e8124b
Create Date: 2025-03-10 20:25:33.816408

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '63be3dd5cccd'
down_revision = '6f0313e8124b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('selected_products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('product_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, 'product', ['product_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('selected_products', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('product_id')

    # ### end Alembic commands ###
