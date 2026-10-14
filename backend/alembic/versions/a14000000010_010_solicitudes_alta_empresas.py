"""010 solicitudes de incorporación de empresas
Revision ID: a14000000010
Revises: 9a1450000009
"""
from alembic import op
import sqlalchemy as sa
revision='a14000000010'
down_revision='9a1450000009'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('solicitudes_alta_empresas',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('razon_social',sa.String(200),nullable=False),
        sa.Column('ruc',sa.String(11),nullable=False),
        sa.Column('nombre_contacto',sa.String(120),nullable=False),
        sa.Column('email_contacto',sa.String(255),nullable=False),
        sa.Column('telefono',sa.String(25),nullable=True),
        sa.Column('estado',sa.String(20),nullable=False,server_default='PENDIENTE'),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.text('now()')),
        sa.UniqueConstraint('ruc',name='uq_solicitudes_alta_ruc'))
    op.create_index('ix_solicitudes_alta_estado','solicitudes_alta_empresas',['estado','created_at'])

def downgrade():
    op.drop_index('ix_solicitudes_alta_estado',table_name='solicitudes_alta_empresas')
    op.drop_table('solicitudes_alta_empresas')
