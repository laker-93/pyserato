from pathlib import Path
from typing import Union

from pyserato.encoders.io.container import Container, probe_container
from pyserato.encoders.io.flac_tag_io import FlacTagIO
from pyserato.encoders.io.mp3_tag_io import Mp3TagIO
from pyserato.encoders.io.tag_io import TagIO, UnsupportedContainerError

__all__ = [
    "Container",
    "FlacTagIO",
    "Mp3TagIO",
    "TagIO",
    "UnsupportedContainerError",
    "probe_container",
    "tag_io_for",
]


def tag_io_for(path: Union[Path, str]) -> TagIO:
    """The reader and writer for whatever this file turns out to be.

    Raises UnsupportedContainerError for a container with no implementation yet,
    which is the point of deciding here rather than in each encoder: there is one
    place that decides, and it names the container it refused.
    """
    container = probe_container(path)
    if container == "MP3":
        return Mp3TagIO(path)
    if container == "FLAC":
        return FlacTagIO(path)
    raise UnsupportedContainerError(container, path)
