"""New revision

Revision ID: 5d164bbb4813
Revises: 4f97b4438c18
Create Date: 2021-06-14 13:20:30.953423

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d164bbb4813'
down_revision = '4f97b4438c18'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute('''update "user" set commercial_name = '' where commercial_name is null;''')
    conn.execute('''update "user" set email_customer = '' where email_customer is null;''')
    conn.execute('''update "user" set email_technical = '' where email_technical is null;''')
    conn.execute('''update "user" set operator_api_key = '' where operator_api_key is null;''')
    conn.execute('''update "user" set operator_header_name = '' where operator_header_name is null;''')
    conn.execute('''update "user" set phone_number_customer = '' where phone_number_customer is null;''')
    conn.execute('''update "user" set phone_number_technical = '' where phone_number_technical is null;''')

    op.alter_column('user', 'commercial_name',
                    existing_type=sa.VARCHAR(),
                    server_default='',
                    nullable=False)
    op.alter_column('user', 'email',
                    existing_type=sa.VARCHAR(length=255),
                    nullable=False)
    op.alter_column('user', 'email_customer',
                    existing_type=sa.VARCHAR(),
                    server_default='',
                    nullable=False)
    op.alter_column('user', 'email_technical',
                    existing_type=sa.VARCHAR(),
                    server_default='',
                    nullable=False)
    op.alter_column('user', 'operator_api_key',
                    existing_type=sa.VARCHAR(),
                    server_default='',
                    nullable=False)
    op.alter_column('user', 'operator_header_name',
                    existing_type=sa.VARCHAR(),
                    server_default='',
                    nullable=False)
    op.alter_column('user', 'password',
                    existing_type=sa.VARCHAR(length=255),
                    nullable=False)
    op.alter_column('user', 'phone_number_customer',
                    existing_type=sa.VARCHAR(),
                    server_default='',
                    nullable=False)
    op.alter_column('user', 'phone_number_technical',
                    existing_type=sa.VARCHAR(),
                    server_default='',
                    nullable=False)


def downgrade():
    op.alter_column('user', 'phone_number_technical',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
    op.alter_column('user', 'phone_number_customer',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
    op.alter_column('user', 'password',
                    existing_type=sa.VARCHAR(length=255),
                    nullable=True)
    op.alter_column('user', 'operator_header_name',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
    op.alter_column('user', 'operator_api_key',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
    op.alter_column('user', 'email_technical',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
    op.alter_column('user', 'email_customer',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
    op.alter_column('user', 'email',
                    existing_type=sa.VARCHAR(length=255),
                    nullable=True)
    op.alter_column('user', 'commercial_name',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
