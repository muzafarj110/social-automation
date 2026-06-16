"""Agency multi-client scoping helpers."""

from __future__ import annotations

from app.models.user import User


def active_client_id(user: User) -> int | None:
    """The client workspace the agency is currently in (None = default)."""
    return user.active_client_id


def client_scope(column, client_id: int | None):
    """A SQL condition scoping a `client_id` column to the active client.

    None means the default/personal workspace, so we match rows where the
    column IS NULL — never leak another client's rows into the default view.
    """
    return column.is_(None) if client_id is None else (column == client_id)
