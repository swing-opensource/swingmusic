import datetime
from shlex import join
from typing import Any
from flask_jwt_extended import current_user
from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Integer,
    String,
    and_,
    delete,
    insert,
    select,
    update,
    join,
)

from sqlalchemy.orm import Mapped, mapped_column

from app.db.utils import (
    albums_to_dataclasses,
    artists_to_dataclasses,
    favorites_to_dataclass,
    playlist_to_dataclass,
    playlists_to_dataclasses,
    plugin_to_dataclasses,
    similar_artist_to_dataclass,
    similar_artists_to_dataclass,
    tracklog_to_dataclass,
    tracklog_to_dataclasses,
    tracks_to_dataclasses,
    user_to_dataclass,
    user_to_dataclasses,
)

from app.db import Base, DbManager
from app.utils.auth import get_current_userid, hash_password


class UserTable(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    image: Mapped[str] = mapped_column(String(), nullable=True)
    password: Mapped[str] = mapped_column(String())
    username: Mapped[str] = mapped_column(String(), index=True)
    roles: Mapped[list[str]] = mapped_column(JSON(), default_factory=lambda: ["user"])
    extra: Mapped[dict[str, Any]] = mapped_column(
        JSON(), nullable=True, default_factory=dict
    )

    @classmethod
    def get_all(cls):
        result = cls.execute(select(cls))
        return user_to_dataclasses(result.fetchall())

    @classmethod
    def insert_default_user(cls):
        user = {
            "username": "admin",
            "password": hash_password("admin"),
            "roles": ["admin"],
        }

        return cls.insert_one(user)

    @classmethod
    def insert_guest_user(cls):
        user = {
            "username": "guest",
            "password": hash_password("guest"),
            "roles": ["guest"],
        }

        return cls.insert_one(user)

    @classmethod
    def get_by_id(cls, id: int):
        with DbManager() as conn:
            result = conn.execute(select(cls).where(cls.id == id))
            res = result.fetchone()

            if res:
                return user_to_dataclass(res)

    @classmethod
    def get_by_username(cls, username: str):
        with DbManager() as conn:
            result = conn.execute(select(cls).where(cls.username == username))
            res = result.fetchone()

            if res:
                return user_to_dataclass(res)

    @classmethod
    def update_one(cls, user: dict[str, Any]):
        with DbManager(commit=True) as conn:
            conn.execute(update(cls).where(cls.id == user["id"]).values(user))

    @classmethod
    def remove_by_username(cls, username: str):
        return cls.execute(delete(cls).where(cls.username == username), commit=True)


class PluginTable(Base):
    __tablename__ = "plugin"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(), unique=True)
    active: Mapped[bool] = mapped_column(Boolean())
    settings: Mapped[dict[str, Any]] = mapped_column(JSON())
    extra: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=True)

    @classmethod
    def get_all(cls):
        return plugin_to_dataclasses(cls.all())


class SimilarArtistTable(Base):
    __tablename__ = "notlastfm_similar_artists"

    id: Mapped[int] = mapped_column(Integer(), primary_key=True)
    artisthash: Mapped[str] = mapped_column(String(), index=True)
    similar_artists: Mapped[dict[str, str]] = mapped_column(JSON())

    @classmethod
    def get_all(cls):
        with DbManager() as conn:
            result = conn.execute(select(cls))
            return similar_artists_to_dataclass(result.fetchall())

    @classmethod
    def exists(cls, artisthash: str):
        """
        Check whether an artisthash exists in the database.
        """

        with DbManager() as conn:
            result = conn.execute(
                select(cls.artisthash).where(cls.artisthash == artisthash)
            )
            return result.fetchone() is not None

    @classmethod
    def get_by_hash(cls, artisthash: str):
        """
        Get a single artist by hash.
        """

        with DbManager() as conn:
            result = conn.execute(select(cls).where(cls.artisthash == artisthash))
            result = result.fetchone()

            if result:
                return similar_artist_to_dataclass(result)


class FavoritesTable(Base):
    __tablename__ = "favorite"

    id: Mapped[int] = mapped_column(primary_key=True)
    hash: Mapped[str] = mapped_column(String())
    type: Mapped[str] = mapped_column(String(), index=True)
    timestamp: Mapped[int] = mapped_column(Integer(), index=True)
    userid: Mapped[int] = mapped_column(
        Integer(), ForeignKey("user.id", ondelete="cascade"), default=1, index=True
    )
    extra: Mapped[dict[str, Any]] = mapped_column(
        JSON(), nullable=True, default_factory=dict
    )

    @classmethod
    def get_all(cls):
        with DbManager() as conn:
            result = conn.execute(select(cls))
            return favorites_to_dataclass(result.fetchall())

    @classmethod
    def insert_item(cls, item: dict[str, Any]):
        item["timestamp"] = int(datetime.datetime.now().timestamp())
        item["userid"] = get_current_userid()

        with DbManager(commit=True) as conn:
            conn.execute(insert(cls).values(item))

    @classmethod
    def remove_item(cls, item: dict[str, Any]):
        with DbManager(commit=True) as conn:
            conn.execute(
                delete(cls).where(
                    (cls.hash == item["hash"]) & (cls.type == item["type"])
                )
            )

    @classmethod
    def check_exists(cls, hash: str, type: str):
        result = cls.execute(select(cls).where((cls.hash == hash) & (cls.type == type)))
        return result.fetchone() is not None

    @classmethod
    def get_all_of_type(cls, table: Any, field: Any, type: str, start: int, limit: int):
        result = cls.execute(
            select(table)
            .select_from(join(table, cls, field == cls.hash))
            .where(and_(cls.type == type, cls.userid == get_current_userid()))
            .offset(start)
            # INFO: If start is 0, fetch all so we can get the total count
            .limit(limit if start != 0 else None)
        )

        res = result.fetchall()

        if start == 0:
            return res[:limit], len(res)

        return res, -1

    @classmethod
    def get_fav_tracks(cls, start: int, limit: int):
        from .libdata import TrackTable

        result, total = cls.get_all_of_type(
            TrackTable, TrackTable.trackhash, "track", start, limit
        )
        return tracks_to_dataclasses(result), total

    @classmethod
    def get_fav_albums(cls, start: int, limit: int):
        from .libdata import AlbumTable

        result, total = cls.get_all_of_type(
            AlbumTable, AlbumTable.albumhash, "album", start, limit
        )
        return albums_to_dataclasses(result), total

    @classmethod
    def get_fav_artists(cls, start: int, limit: int):
        from .libdata import ArtistTable

        result, total = cls.get_all_of_type(
            ArtistTable, ArtistTable.artisthash, "artist", start, limit
        )
        return artists_to_dataclasses(result), total


class ScrobbleTable(Base):
    __tablename__ = "scrobble"

    id: Mapped[int] = mapped_column(primary_key=True)
    trackhash: Mapped[str] = mapped_column(String(), index=True)
    duration: Mapped[int] = mapped_column(Integer())
    timestamp: Mapped[int] = mapped_column(Integer())
    source: Mapped[str] = mapped_column(String())
    userid: Mapped[int] = mapped_column(
        Integer(), ForeignKey("user.id", ondelete="cascade"), index=True
    )
    extra: Mapped[dict[str, Any]] = mapped_column(
        JSON(), nullable=True, default_factory=dict
    )

    @classmethod
    def add(cls, item: dict[str, Any]):
        item["userid"] = get_current_userid()
        return cls.insert_one(item)

    @classmethod
    def get_all(cls, start: int, limit: int):
        result = cls.execute(
            select(cls)
            .where(cls.userid == get_current_userid())
            .order_by(cls.timestamp.desc())
            .offset(start)
            .limit(limit)
        )

        return tracklog_to_dataclasses(result.fetchall())


class PlaylistTable(Base):
    __tablename__ = "playlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(), index=True)
    last_updated: Mapped[int] = mapped_column(Integer())
    image: Mapped[str] = mapped_column(String(), nullable=True)
    userid: Mapped[int] = mapped_column(
        Integer(), ForeignKey("user.id", ondelete="cascade")
    )
    settings: Mapped[dict[str, Any]] = mapped_column(JSON())
    trackhashes: Mapped[list[str]] = mapped_column(JSON(), default_factory=list)
    extra: Mapped[dict[str, Any]] = mapped_column(
        JSON(), nullable=True, default_factory=dict
    )

    @classmethod
    def get_all(cls):
        result = cls.all()
        return playlists_to_dataclasses(result)

    @classmethod
    def add_one(cls, playlist: dict[str, Any]):
        playlist["userid"] = get_current_userid()
        result = cls.insert_one(playlist)
        return result.lastrowid

    @classmethod
    def check_exists_by_name(cls, name: str):
        result = cls.execute(
            select(cls).where((cls.name == name) & (cls.userid == get_current_userid()))
        )
        return result.fetchone() is not None

    @classmethod
    def append_to_playlist(cls, id: int, trackhashes: list[str]):
        print("type(trackhashes):", type(trackhashes))
        return cls.execute(
            update(cls)
            .where((cls.id == id) & (cls.userid == get_current_userid()))
            .values(trackhashes=cls.trackhashes + trackhashes),
            commit=True,
        )

    @classmethod
    def remove_from_playlist(cls, id: int, trackhashes: list[dict[str, Any]]):
        # CHECKPOINT: Properly remove tracks from a playlist
        # Without messing up the order in case of duplicates
        tracks = cls.execute(
            select(cls.trackhashes).where(
                (cls.id == id) & (cls.userid == get_current_userid())
            )
        )

        results = tracks.fetchone()
        if results:
            dbhashes: list[str] = results[0]

            for item in trackhashes:
                if dbhashes.index(item["trackhash"]) == item["index"]:
                    dbhashes.remove(item["trackhash"])

            return cls.execute(
                update(cls)
                .where((cls.id == id) & (cls.userid == get_current_userid()))
                .values(trackhashes=dbhashes),
                commit=True,
            )

    @classmethod
    def get_by_id(cls, id: int):
        result = cls.execute(
            select(cls).where((cls.id == id) & (cls.userid == get_current_userid()))
        )
        result = result.fetchone()
        if result:
            return playlist_to_dataclass(result)

    @classmethod
    def update_one(cls, id: int, playlist: dict[str, Any]):
        return cls.execute(
            update(cls)
            .where((cls.id == id) & (cls.userid == get_current_userid()))
            .values(playlist),
            commit=True,
        )

    @classmethod
    def update_settings(cls, id: int, settings: dict[str, Any]):
        return cls.execute(
            update(cls)
            .where((cls.id == id) & (cls.userid == get_current_userid()))
            .values(settings=settings),
            commit=True,
        )

    @classmethod
    def remove_image(cls, id: int):
        return cls.execute(
            update(cls)
            .where((cls.id == id) & (cls.userid == get_current_userid()))
            .values(image=None),
            commit=True,
        )