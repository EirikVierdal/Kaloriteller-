"""Added popularity column to Product

Revision ID: 170ae71beac9
Revises: d791548a9218
Create Date: 2025-02-26 23:21:11.876127

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '170ae71beac9'
down_revision = 'd791548a9218'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.add_column(sa.Column('popularity', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.drop_column('popularity')

    # ### end Alembic commands ###
