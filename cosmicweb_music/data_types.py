from __future__ import annotations

from datetime import datetime
from typing import NamedTuple, Any, List, Dict, TypedDict, Tuple


class Ellipsoid(NamedTuple):
    center: List[float]
    shape: List[List[float]]
    traceback_radius: float
    radius_definition: str


class Resolution(TypedDict):
    low: int
    high: int


class Configuration(TypedDict):
    outputType: str
    resolution: Resolution
    outputOptions: List[Tuple[str, str]]
    startRedshift: int
    outputFilename: str
    separateFolders: bool
    tracebackRadius: int | float | str


class ICSections(TypedDict):
    setup: str
    random: str
    cosmology: str
    poisson: str


class DownloadConfig(NamedTuple):
    simulation_name: str
    project_name: str
    halo_names: List[str]
    halo_ids: List[int]
    halo_urls: List[str]
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
