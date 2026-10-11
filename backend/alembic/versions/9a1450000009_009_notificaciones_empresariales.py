"""009 notificaciones empresariales; multiempresa e idempotencia
Revision ID: 9a1450000009
Revises: 746fcabdf249
"""
from alembic import op
import sqlalchemy as sa
revision='9a1450000009'
down_revision='746fcabdf249'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('notificaciones_empresariales',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('empresa_id',sa.Integer(),nullable=False),
        sa.Column('clave',sa.String(160),nullable=False),
        sa.Column('codigo',sa.String(50),nullable=False),
        sa.Column('titulo',sa.String(180),nullable=False),
        sa.Column('descripcion',sa.Text(),nullable=False),
        sa.Column('nivel',sa.String(24),nullable=False),
        sa.Column('leida',sa.Boolean(),nullable=False,server_default=sa.text('false')),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.text('now()')),
        sa.Column('leida_at',sa.DateTime(timezone=True),nullable=True),
        sa.ForeignKeyConstraint(['empresa_id'],['empresas.id'],name='fk_notificaciones_empresa'),
        sa.UniqueConstraint('empresa_id','clave',name='uq_notificacion_empresa_clave'))
    op.create_index('ix_notificaciones_empresa_estado_fecha','notificaciones_empresariales',['empresa_id','leida','created_at'])

def downgrade():
    op.drop_index('ix_notificaciones_empresa_estado_fecha',table_name='notificaciones_empresariales')
    op.drop_table('notificaciones_empresariales')
