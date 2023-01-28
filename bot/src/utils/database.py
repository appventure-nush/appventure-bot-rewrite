import logging
from datetime import date
from typing import Any, Collection, Literal, Mapping, Optional, Tuple, Union

from peewee import (
    JOIN,
    BigIntegerField,
    Cast,
    CharField,
    Model,
    PeeweeException,
    PostgresqlDatabase,
    fn,
)
from playhouse.hybrid import hybrid_property

db = PostgresqlDatabase(
    database="postgres", host="db", port=5432, user="postgres", password="postgres"
)  # TODO: modify this when deploying
logger = logging.getLogger(__name__)


class BaseModel(Model):
    class Meta:
        database = db


class Member(BaseModel):
    email = CharField(23, primary_key=True)
    name = CharField(100)
    discord_id = BigIntegerField(null=True, unique=True)

    @hybrid_property
    def year(self):  # type: ignore
        join_year = int(self.email[1:3])
        join_level = int(self.email[3])
        return (date.today().year - join_year) % 100 + join_level

    @year.expression
    def year(cls):
        # translation of the above to postgres for queries
        # note: sql is 1-indexed
        join_year = Cast(fn.SUBSTR(cls.email, 2, 2), "INT")
        join_level = Cast(fn.SUBSTR(cls.email, 4, 1), "INT")
        curr_year = Cast(fn.DATE_PART("year", fn.NOW()), "INT")
        year = fn.MOD(curr_year - join_year, 100) + join_level
        return year


class Github(BaseModel):
    discord_id = BigIntegerField(primary_key=True)
    github = CharField(100)


class Project(BaseModel):
    name = CharField(100, primary_key=True)
    discord_role_id = BigIntegerField()
    discord_text_channel_id = BigIntegerField()
    discord_voice_channel_id = BigIntegerField()
    webhook_id = BigIntegerField(null=True)
    github_repo = CharField(100, null=True)
    github_webhook_id = BigIntegerField(null=True)


class Database:
    __slots__ = ()

    def __init__(self) -> None:
        db.connect()

    def create_members(
        self, emails: Collection[str], names: Collection[str], update_existing: bool
    ) -> Union[Literal[False], Tuple[Literal[True], int, int]]:
        with db.atomic() as transaction:  # wrap in transaction
            try:
                curr_records = Member.select().count()
                Member.insert_many(
                    rows=zip(emails, names), fields=[Member.email, Member.name]
                ).on_conflict_ignore().execute()  # insert new records
                num_new = Member.select().count() - curr_records
                if update_existing:
                    Member.insert_many(rows=zip(emails, names), fields=[Member.email, Member.name]).on_conflict(
                        conflict_target=[Member.email], preserve=[Member.name]
                    ).execute()  # update existing records
                num_existing_updated = update_existing * (len(emails) - num_new)
                return (True, num_new, num_existing_updated)
            except PeeweeException:
                transaction.rollback()
                logging.warn("Database writing failed:", exc_info=True)
                return False

    def get_member_by_email(self, email: str) -> Optional[Member]:
        return Member.get_or_none(Member.email == email)

    def get_member_by_name(self, name: str) -> Collection[Member]:
        return Member.select().where(Member.name.contains(name))

    def get_member_by_discord_id(self, discord_id: int) -> Optional[Member]:
        return Member.get_or_none(Member.discord_id == discord_id)

    def get_members(self) -> Collection[Any]:
        return (
            Member.select(Member.year, Member.email, Member.name, Member.discord_id, Github.github)
            .join(Github, JOIN.LEFT_OUTER, on=(Member.discord_id == Github.discord_id))
            .order_by(Member.year, Member.name)
            .objects()
        )

    def set_discord(self, email: str, discord_id: int) -> None:
        with db.atomic():
            Member.update(discord_id=discord_id).where(Member.email == email).execute()

    def set_github(self, discord_id: int, github: str) -> None:
        with db.atomic():
            Github.insert(discord_id=discord_id, github=github).on_conflict(
                conflict_target=[Github.discord_id], preserve=[Github.github]
            ).execute()

    def get_graduated(self) -> Collection[Member]:
        target_year = 7
        if date.today().month >= 11:  # (november)
            # consider those graduating soon
            target_year = 6

        target_year = 4
        return Member.select().where(Member.year >= target_year)

    def get_non_graduated(self, *, strict: bool = False, with_github: bool = False) -> Collection[Any]:
        # note a slight overlap in "graduated" and "non_graduated" between Nov/Dec, unless strict is enabled
        target_year = 7
        if strict and date.today().month >= 11:  # (november)
            # don't get those graduating soon
            target_year = 6

        if with_github:
            return (
                Member.select(Member.year, Member.email, Member.name, Member.discord_id, Github.github)
                .where(Member.year < target_year)
                .join(Github, JOIN.LEFT_OUTER, on=(Member.discord_id == Github.discord_id))
                .order_by(Member.year, Member.name)
                .objects()
            )

        return Member.select().where(Member.year < target_year).objects()

    def get_github(self, discord_id: int) -> Optional[Github]:
        return Github.get_or_none(Github.discord_id == discord_id)

    def get_project(self, name: str) -> Optional[Project]:
        return Project.get_or_none(Project.name == name)

    def get_projects(self) -> Collection[Project]:
        return Project.select()

    def insert_project(self, project: Project) -> None:
        with db.atomic():
            project.save(force_insert=True)

    def delete_project(self, project: Project) -> None:
        with db.atomic():
            project.delete_instance()


database = Database()

__all__ = ["database", "Project", "Member", "Github"]
