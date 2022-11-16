from datetime import date
from typing import Collection, Optional

from peewee import BigIntegerField, CharField, Model, SqliteDatabase, fn, Cast, SQL
from playhouse.hybrid import hybrid_property

db = SqliteDatabase("../secrets/data.db")  # TODO: modify this when deploying


class Members(Model):
    email = CharField(23, primary_key=True, column_name="id")
    name = CharField(100)
    discord_id = BigIntegerField(null=True, column_name="discordID")
    github = CharField(100, null=True)

    class Meta:
        database = db

    @hybrid_property
    def year(self):
        join_year = int(self.email[1:3])
        join_level = int(self.email[3])
        return (date.today().year - join_year) % 100 + join_level

    @year.expression
    def year(cls):
        # translation of the above to raw sql for queries
        # note: sql is 1-indexed
        join_year = Cast(fn.SUBSTR(cls.email, 2, 2), "INT")
        join_level = Cast(fn.SUBSTR(cls.email, 4, 1), "INT")
        curr_year = Cast(fn.STRFTIME("%Y", 'now'), "INT")
        year = fn.MOD(curr_year - join_year, 100) + join_level
        return year


class Database:
    __slots__ = ()

    def __init__(self) -> None:
        db.connect()

    def create_member(self, email: str, name: str) -> None:
        with db.atomic():  # wrap in transaction
            Members.create(id=email, name=name)

    def get_member_by_email(self, email: str) -> Optional[Members]:
        return Members.get_or_none(Members.email == email)

    def get_member_by_name(self, name: str) -> Collection[Members]:
        return Members.select().where(Members.name.contains(name))

    def get_member_by_discord_id(self, discord_id: int) -> Collection[Members]:
        return Members.select().where(Members.discord_id == discord_id)

    def get_members(self) -> Collection[Members]:
        return Members.select()

    def set_discord(self, email: str, discord_id: int) -> None:
        with db.atomic():
            Members.update(discordID=discord_id).where(Members.email == email)

    def set_github(self, email: str, github: str) -> None:
        with db.atomic():
            Members.update(github=github).where(Members.email == email)

    def get_graduated(self) -> Collection[Members]:
        target_year = 7
        if date.today().month >= 11:  # (november)
            # consider those graduating soon
            target_year = 6

        target_year = 4
        return Members.select().where(Members.year >= target_year)

    def get_non_graduated(self, *, strict: bool = False) -> Collection[Members]:
        # note a slight overlap in "graduated" and "non_graduated" between Nov/Dec, unless strict is enabled
        target_year = 7
        if strict and date.today().month >= 11:  # (november)
            # don't get those graduating soon
            target_year = 6

        return Members.select().where(Members.year < target_year)


database = Database()

__all__ = ["database"]
