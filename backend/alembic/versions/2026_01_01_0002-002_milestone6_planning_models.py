"""milestone 6 planning models and recommendations

Revision ID: 002
Revises: 001
Create Date: 2026-10-23 03:55:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Add monthly_contribution_paise to goals table
    op.add_column('goals', sa.Column('monthly_contribution_paise', sa.BigInteger(), nullable=False, server_default='0'))

    # 2. Create saved_scenarios table
    op.create_table(
        'saved_scenarios',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('params_json', sa.Text(), nullable=False),
        sa.Column('results_summary_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_scenarios_user_created', 'saved_scenarios', ['user_id', 'created_at'])

    # 3. Create recommendations table
    op.create_table(
        'recommendations',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recommendation_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('data_period', sa.String(length=100), nullable=False),
        sa.Column('estimated_impact_inr', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('impact_assumptions', sa.Text(), nullable=False),
        sa.Column('confidence', sa.String(length=20), nullable=False, server_default='HIGH'),
        sa.Column('suggested_action', sa.String(length=255), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=True),
        sa.Column('action_payload_json', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='new'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_recommendations_user_status', 'recommendations', ['user_id', 'status'])

def downgrade() -> None:
    op.drop_index('idx_recommendations_user_status', table_name='recommendations')
    op.drop_table('recommendations')
    op.drop_index('idx_scenarios_user_created', table_name='saved_scenarios')
    op.drop_table('saved_scenarios')
    op.drop_column('goals', 'monthly_contribution_paise')
