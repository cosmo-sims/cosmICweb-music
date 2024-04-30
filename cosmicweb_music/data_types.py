from __future__ import annotations

from datetime import datetime
from typing import NamedTuple, TypedDict


class Ellipsoid(NamedTuple):
    center: list[float]
    shape: list[list[float]]
    traceback_radius: float
    radius_definition: str


class Resolution(TypedDict):
    low: int
    high: int


class Configuration(TypedDict):
    outputType: str
    resolution: Resolution
    outputOptions: list[tuple[str, str]]
    startRedshift: int
    outputFilename: str
    seperateFolders: bool
    tracebackRadius: int | float | str


class ICSections(TypedDict):
    setup: str
    random: str
    cosmology: str
    poisson: str


class DownloadConfig(NamedTuple):
    simulation_name: str
    project_name: str
    halo_names: list[str]
    halo_ids: list[int]
    halo_urls: list[str]
    traceback_radius: float
    api_token: str
    MUSIC: ICSections
    settings: Configuration | None
    accessed_at: datetime


class Args(NamedTuple):
    url: str
    output_path: str
    common_directory: bool
    attempts: int
