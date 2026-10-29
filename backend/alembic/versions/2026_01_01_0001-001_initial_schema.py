"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'])

    # 2. accounts table
    op.create_table(
        'accounts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('account_type', sa.String(length=30), nullable=False),
        sa.Column('institution', sa.String(length=100), nullable=False),
        sa.Column('account_number_mask', sa.String(length=20), nullable=True),
        sa.Column('balance_paise', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_accounts_id', 'accounts', ['id'])
    op.create_index('ix_accounts_user_id', 'accounts', ['user_id'])

    # 3. categories table
    op.create_table(
        'categories',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('slug', sa.String(length=80), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=False, server_default='tag'),
        sa.Column('color', sa.String(length=20), nullable=False, server_default='#64748b'),
        sa.Column('is_income', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_categories_id', 'categories', ['id'])
    op.create_index('ix_categories_slug', 'categories', ['slug'])
    op.create_index('ix_categories_user_id', 'categories', ['user_id'])

    # 4. transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('account_id', sa.Uuid(), nullable=False),
        sa.Column('category_id', sa.Uuid(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('amount_paise', sa.BigInteger(), nullable=False),
        sa.Column('transaction_type', sa.String(length=10), nullable=False),
        sa.Column('narration', sa.String(length=500), nullable=False),
        sa.Column('raw_narration', sa.String(length=1000), nullable=True),
        sa.Column('merchant_name', sa.String(length=150), nullable=True),
        sa.Column('payment_mode', sa.String(length=30), nullable=False, server_default='UPI'),
        sa.Column('reference_id', sa.String(length=100), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('fingerprint', sa.String(length=64), nullable=False),
        sa.Column('categorization_method', sa.String(length=20), nullable=False, server_default='MANUAL'),
        sa.Column('categorization_confidence', sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'])
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'])
    op.create_index('ix_transactions_account_id', 'transactions', ['account_id'])
    op.create_index('ix_transactions_category_id', 'transactions', ['category_id'])
    op.create_index('ix_transactions_date', 'transactions', ['date'])
    op.create_index('ix_transactions_fingerprint', 'transactions', ['fingerprint'])
    op.create_index('ix_transactions_merchant_name', 'transactions', ['merchant_name'])
    op.create_index('ix_transactions_reference_id', 'transactions', ['reference_id'])
    op.create_index('idx_transactions_user_date', 'transactions', ['user_id', 'date'])
    op.create_index('idx_transactions_user_fingerprint', 'transactions', ['user_id', 'fingerprint'])
    op.create_index('idx_transactions_user_cat_date', 'transactions', ['user_id', 'category_id', 'date'])

    # 5. budgets table
    op.create_table(
        'budgets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('category_id', sa.Uuid(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('amount_paise', sa.BigInteger(), nullable=False),
        sa.Column('alert_threshold', sa.Numeric(precision=4, scale=2), nullable=False, server_default='0.80'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'category_id', 'month', 'year', name='uq_user_category_month_year')
    )
    op.create_index('ix_budgets_id', 'budgets', ['id'])
    op.create_index('ix_budgets_user_id', 'budgets', ['user_id'])
    op.create_index('idx_budgets_user_period', 'budgets', ['user_id', 'year', 'month'])

    # 6. goals table
    op.create_table(
        'goals',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('target_amount_paise', sa.BigInteger(), nullable=False),
        sa.Column('current_amount_paise', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('target_date', sa.Date(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='SAVINGS'),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='MEDIUM'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_goals_id', 'goals', ['id'])
    op.create_index('ix_goals_user_id', 'goals', ['user_id'])
    op.create_index('idx_goals_user_status', 'goals', ['user_id', 'status'])

    # 7. recurring_transactions table
    op.create_table(
        'recurring_transactions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('category_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('merchant_name', sa.String(length=150), nullable=False),
        sa.Column('expected_amount_paise', sa.BigInteger(), nullable=False),
        sa.Column('frequency', sa.String(length=20), nullable=False, server_default='MONTHLY'),
        sa.Column('last_detected_date', sa.Date(), nullable=True),
        sa.Column('next_expected_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_recurring_transactions_id', 'recurring_transactions', ['id'])
    op.create_index('ix_recurring_transactions_user_id', 'recurring_transactions', ['user_id'])
    op.create_index('ix_recurring_transactions_next_date', 'recurring_transactions', ['next_expected_date'])

    # 8. financial_insights table
    op.create_table(
        'financial_insights',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('insight_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='INFO'),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_financial_insights_id', 'financial_insights', ['id'])
    op.create_index('ix_financial_insights_user_id', 'financial_insights', ['user_id'])

    # 9. forecasts table
    op.create_table(
        'forecasts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('account_id', sa.Uuid(), nullable=True),
        sa.Column('forecast_date', sa.Date(), nullable=False),
        sa.Column('horizon_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('predicted_balance_paise', sa.BigInteger(), nullable=False),
        sa.Column('lower_bound_80_paise', sa.BigInteger(), nullable=False),
        sa.Column('upper_bound_80_paise', sa.BigInteger(), nullable=False),
        sa.Column('lower_bound_95_paise', sa.BigInteger(), nullable=False),
        sa.Column('upper_bound_95_paise', sa.BigInteger(), nullable=False),
        sa.Column('projected_net_change_paise', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('shortfall_flag', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('model_version', sa.String(length=50), nullable=False, server_default='holt_winters_v1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_forecasts_id', 'forecasts', ['id'])
    op.create_index('ix_forecasts_user_id', 'forecasts', ['user_id'])
    op.create_index('ix_forecasts_forecast_date', 'forecasts', ['forecast_date'])

    # 10. chat_conversations table
    op.create_table(
        'chat_conversations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_conversations_id', 'chat_conversations', ['id'])
    op.create_index('ix_chat_conversations_user_id', 'chat_conversations', ['user_id'])

    # 11. chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('conversation_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('provider_used', sa.String(length=50), nullable=False, server_default='mock'),
        sa.Column('citations_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_messages_id', 'chat_messages', ['id'])
    op.create_index('ix_chat_messages_conversation_id', 'chat_messages', ['conversation_id'])

    # 12. user_notifications table
    op.create_table(
        'user_notifications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(length=30), nullable=False, server_default='ALERT'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('action_url', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_notifications_id', 'user_notifications', ['id'])
    op.create_index('ix_user_notifications_user_id', 'user_notifications', ['user_id'])

    # 13. import_jobs table
    op.create_table(
        'import_jobs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('bank_format', sa.String(length=50), nullable=False, server_default='GENERIC'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PENDING'),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('imported_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duplicate_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_import_jobs_id', 'import_jobs', ['id'])
    op.create_index('ix_import_jobs_user_id', 'import_jobs', ['user_id'])

    # 14. model_evaluations table
    op.create_table(
        'model_evaluations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('model_name', sa.String(length=80), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('evaluation_type', sa.String(length=50), nullable=False, server_default='TEST_SPLIT'),
        sa.Column('metrics_json', sa.Text(), nullable=False),
        sa.Column('sample_size', sa.Integer(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_model_evaluations_id', 'model_evaluations', ['id'])
    op.create_index('ix_model_evaluations_model_name', 'model_evaluations', ['model_name'])

def downgrade() -> None:
    op.drop_table('model_evaluations')
    op.drop_table('import_jobs')
    op.drop_table('user_notifications')
    op.drop_table('chat_messages')
    op.drop_table('chat_conversations')
    op.drop_table('forecasts')
    op.drop_table('financial_insights')
    op.drop_table('recurring_transactions')
    op.drop_table('goals')
    op.drop_table('budgets')
    op.drop_table('transactions')
    op.drop_table('categories')
    op.drop_table('accounts')
    op.drop_table('users')
