# coding: utf-8
import enum
from dataclasses import dataclass


@dataclass(frozen=True)
class MSG(enum.Enum):
    HORIZONTAL_LINE = "-" * 80
    LINKSEARCHER_CREATE_START = "LinkSearcher each fetcher registering -> start"
    LINKSEARCHER_CREATE_DONE = "LinkSearcher each fetcher registering -> done"
    LINKSEARCHER_REGISTERED = "LinkSearcher {} -> registered."
    LINKSEARCHER_FETCHER_FOUND = "{} -> Fetcher found: {}."
