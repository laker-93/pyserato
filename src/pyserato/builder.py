import os
from pathlib import Path
from typing import Iterator, Optional

from pyserato.encoders.base_encoder import BaseEncoder
from pyserato.model.crate import Crate
from pyserato.model.track import Track
from pyserato.util import serato_encode, serato_decode

DEFAULT_SERATO_FOLDER = Path(os.path.expanduser("~/Music/_Serato_"))


class Builder:

    def __init__(self, encoder: Optional[BaseEncoder] = None):
        self._encoder = encoder

    @staticmethod
    def _resolve_path(root: Crate) -> Iterator[tuple[Crate, str]]:
        """
        DFS through the crate tree returning a generator of paths with the current crate as the root.
        :return:
        """
        path = ""
        crates = [(root, path)]
        while crates:
            crate, path = crates.pop()
            path += f"{crate.name}%%"
            children = crate.children
            if children:
                for child in children:
                    crates.append((child, path))
            yield crate, path.rstrip("%%") + ".crate"

    @staticmethod
    def _parse_crate_names(filepath: Path) -> Iterator[str]:
        for name in str(filepath.name).split("%%"):
            yield name.replace(".crate", "")

    def _build_crate_filepath(self, crate: Crate, serato_folder: Path) -> Iterator[tuple[Crate, Path]]:
        subcrate_folder = serato_folder / "SubCrates"
        subcrate_folder.mkdir(exist_ok=True)
        for crate, paths in self._resolve_path(crate):
            yield crate, subcrate_folder / paths

    def parse_crates_from_root_path(self, subcrate_path: Path) -> dict[str, Crate]:
        crate_name_to_crate: dict[str, Crate] = {}
        for f in subcrate_path.iterdir():
            if not f.name.endswith("crate"):
                continue
            crate = self._build_crates_from_filepath(f)
            if crate.name in crate_name_to_crate:
                crate += crate_name_to_crate[crate.name]
                crate_name_to_crate[crate.name] = crate
            else:
                crate_name_to_crate[crate.name] = crate
        return crate_name_to_crate

    def _build_crates_from_filepath(self, filepath: Path) -> Crate:
        """
        Builds the crate tree from an existing file path.
        :param filepath:
        :return:
        """
        crate_names = list(self._parse_crate_names(filepath))
        child_crate = None
        crate = None
        for crate_name in reversed(crate_names):
            if child_crate is None:
                crate = Crate(crate_name)
                for file_path in self._parse_crate_tracks(filepath):
                    track = Track.from_path(file_path)
                    crate.add_track(track)
                child_crate = crate
            else:
                crate = Crate(crate_name, children=[child_crate])
                child_crate = crate
        assert crate, f"no crates parsed from {filepath}"
        return crate

    @staticmethod
    def _parse_crate_tracks(filepath: Path) -> Iterator[Path]:
        crate_content = filepath.read_bytes()
        while crate_content:
            otrk_idx = crate_content.find("otrk".encode("utf-8"))
            if otrk_idx < 0:
                break
            assert "otrk".encode("utf-8") == crate_content[otrk_idx: otrk_idx + len("otrk")]
            ptrk_idx = crate_content.find("ptrk".encode("utf-8"))
            # Below would be the lgnth of the otrk data if needed for further parsing.
            # otrk_section = crate_content[otrk_idx + len("otrk"): ptrk_idx]
            # len_data = int.from_bytes(otrk_section, "big") - 8
            ptrk_section = crate_content[ptrk_idx:]
            track_name_length = int.from_bytes(ptrk_section[4:8], "big")
            track_name_encoded = ptrk_section[8: 8 + track_name_length]
            file_path = serato_decode(track_name_encoded)
            if not file_path.startswith("/"):
                file_path = "/" + file_path

            yield Path(file_path)
            crate_content = crate_content[ptrk_idx + 8 + track_name_length:]

    def _construct(self, crate: Crate) -> bytes:
        """
        Constructs the crate in bytes ready to save to disk.
        Also writes any cues and meta info as tags to the track.
        """
        header = "vrsn".encode("latin1")
        # byteorder is redundant here for a size of 1 but is a required arg in Python 3.10-
        header += (0).to_bytes(1, byteorder="big")
        header += (0).to_bytes(1, byteorder="big")
        header += serato_encode("81.0")
        header += serato_encode("/Serato ScratchLive Crate")

        # sorting = "osrt".encode('latin1')
        # default_sorting_type = "track"
        # default_sorting_rev = (1 << 8)
        # sorting += (len(default_sorting_type) * 2 + 17).to_bytes(4, 'big')
        # sorting += "tvcn".encode('latin1')
        # sorting += (len(default_sorting_type) * 2).to_bytes(4, 'big')
        # sorting += default_sorting_type.encode('utf-16')
        # sorting += "brev".encode('latin1')
        # sorting += (default_sorting_rev).to_bytes(5, 'big')
        DEFAULT_COLUMNS = ["track", "artist", "album", "length"]
        column_section = bytes()
        for column in DEFAULT_COLUMNS:
            column_section += "ovct".encode()
            column_section += (len(column) * 2 + 18).to_bytes(4, "big")
            column_section += "tvcn".encode()
            column_section += (len(column) * 2).to_bytes(4, "big")
            column_section += serato_encode(column)
            column_section += "tvcw".encode()
            column_section += (2).to_bytes(4, "big")
            column_section += "0".encode()
            column_section += "0".encode()

        playlist_section = bytes()
        if crate.tracks:
            for track in crate.tracks:
                if self._encoder:
                    self._encoder.write(track)
                absolute_track_path = Path(track.path).resolve()

                otrk_size = (len(str(absolute_track_path)) * 2 + 8).to_bytes(4, "big")
                ptrk_size = (len(str(absolute_track_path)) * 2).to_bytes(4, "big")
                playlist_section += "otrk".encode("latin1")
                playlist_section += otrk_size
                playlist_section += "ptrk".encode("latin1")
                playlist_section += ptrk_size
                playlist_section += serato_encode(str(absolute_track_path))

        contents = header + column_section + playlist_section
        return contents

    def save(
        self,
        root: Crate,
        save_path: Path = DEFAULT_SERATO_FOLDER,
        overwrite: bool = False,
    ):
        for crate, filepath in self._build_crate_filepath(root, save_path):
            if filepath.exists() and overwrite is False:
                continue
            buffer = self._construct(crate)
            filepath.write_bytes(buffer)
