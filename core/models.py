# ORM models
# core/models.py
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey, func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(DateTime, default=func.now())
    last_login_at: Mapped[str] = mapped_column(DateTime, nullable=True)

class Class(Base):
    __tablename__ = "classes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(128), index=True)
    rn_format: Mapped[str] = mapped_column(String(256), nullable=True)
    naming_props_csv: Mapped[str] = mapped_column(String(256), nullable=True)
    label: Mapped[str] = mapped_column(String(256), nullable=True)
    category: Mapped[str] = mapped_column(String(128), nullable=True)
    descr: Mapped[str] = mapped_column(Text, nullable=True)
    mo_dn_prefix: Mapped[str] = mapped_column(String(128), nullable=True)

class Prop(Base):
    __tablename__ = "props"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(64), nullable=True)
    is_naming: Mapped[bool] = mapped_column(Boolean, default=False)
    is_config: Mapped[bool] = mapped_column(Boolean, default=False)
    is_regex_capable: Mapped[bool] = mapped_column(Boolean, default=True)
    descr: Mapped[str] = mapped_column(Text, nullable=True)

class Relation(Base):
    __tablename__ = "relations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    src_class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    rel_type: Mapped[str] = mapped_column(String(32))  # child/parent/rs/rt
    dst_class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    cardinality: Mapped[str] = mapped_column(String(32), nullable=True)
    descr: Mapped[str] = mapped_column(Text, nullable=True)

class Query(Base):
    __tablename__ = "queries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(256))
    body: Mapped[str] = mapped_column(Text)  # final moquery text
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    tags_csv: Mapped[str] = mapped_column(String(256), default="")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(DateTime, default=func.now())

class QueryRun(Base):
    __tablename__ = "query_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("queries.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ran_at: Mapped[str] = mapped_column(DateTime, default=func.now())
    target_device: Mapped[str] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32))  # success/fail
    error_text: Mapped[str] = mapped_column(Text, nullable=True)

class Example(Base):
    __tablename__ = "examples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    title: Mapped[str] = mapped_column(String(256))
    moquery_text: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(DateTime, default=func.now())
    likes: Mapped[int] = mapped_column(Integer, default=0)
