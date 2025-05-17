import sqlalchemy
from datetime import datetime
from .db_session import SqlAlchemyBase

class News(SqlAlchemyBase):
    __tablename__ = 'news'
    __table_args__ = (
        sqlalchemy.UniqueConstraint('api_id', name='uq_news_api_id'),
    )
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    content = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    source = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    tags = sqlalchemy.Column(sqlalchemy.String)
    published_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.now)
    api_id = sqlalchemy.Column(sqlalchemy.String, unique=True)
