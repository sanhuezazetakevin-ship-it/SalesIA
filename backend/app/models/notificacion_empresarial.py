from datetime import datetime
from sqlalchemy import Integer,String,Text,Boolean,DateTime,UniqueConstraint,ForeignKeyConstraint,Index,func
from sqlalchemy.orm import Mapped,mapped_column
from app.database.base import Base

class NotificacionEmpresarial(Base):
    __tablename__='notificaciones_empresariales'
    __table_args__=(
        ForeignKeyConstraint(['empresa_id'],['empresas.id'],name='fk_notificaciones_empresa'),
        UniqueConstraint('empresa_id','clave',name='uq_notificacion_empresa_clave'),
        Index('ix_notificaciones_empresa_estado_fecha','empresa_id','leida','created_at'),
    )
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    empresa_id:Mapped[int]=mapped_column(Integer,nullable=False)
    clave:Mapped[str]=mapped_column(String(160),nullable=False)
    codigo:Mapped[str]=mapped_column(String(50),nullable=False)
    titulo:Mapped[str]=mapped_column(String(180),nullable=False)
    descripcion:Mapped[str]=mapped_column(Text,nullable=False)
    nivel:Mapped[str]=mapped_column(String(24),nullable=False)
    leida:Mapped[bool]=mapped_column(Boolean,nullable=False,server_default='false')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,server_default=func.now())
    leida_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
