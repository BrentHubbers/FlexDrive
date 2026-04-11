import logging
from typing import Iterable

from sqlmodel import Session, func, select

from app.models.user import Comment


logger = logging.getLogger(__name__)


class CommentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_many(self, comments: Iterable[Comment]) -> list[Comment]:
        created_comments: list[Comment] = []
        try:
            for comment in comments:
                self.db.add(comment)
                created_comments.append(comment)
            self.db.commit()
            for comment in created_comments:
                self.db.refresh(comment)
            return created_comments
        except Exception as exc:
            logger.error(f"An error occurred while saving comments: {exc}")
            self.db.rollback()
            raise

    def count(self) -> int:
        statement = select(func.count()).select_from(Comment)
        return int(self.db.exec(statement).one())
