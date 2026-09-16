from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Group = Literal["people", "helps", "avoid", "goals"]


class RememberItem(BaseModel):
    group: Group
    text: str = Field(min_length=2, max_length=80)


class RememberStore(BaseModel):
    opt_in: bool = False
    items: list[RememberItem] = Field(default_factory=list)


REMEMBERS: dict[str, RememberStore] = {}


def get_remembers(token: str) -> RememberStore:
    return REMEMBERS.setdefault(token, RememberStore())


def set_opt_in(token: str, opt_in: bool) -> RememberStore:
    store = get_remembers(token)
    store.opt_in = opt_in
    if not opt_in:
        return store
    return store


def add_item(token: str, item: RememberItem) -> RememberStore:
    store = get_remembers(token)
    if not store.opt_in:
        raise PermissionError("remembers_opt_in_required")
    if len(store.items) >= 20:
        raise ValueError("remembers_full")
    store.items.append(item)
    return store


def clear_all(token: str) -> RememberStore:
    store = get_remembers(token)
    store.items.clear()
    return store


def context_for(token: str) -> list[str]:
    store = get_remembers(token)
    if not store.opt_in:
        return []
    return [f"{item.group}: {item.text}" for item in store.items[:20]]
