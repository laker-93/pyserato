from pathlib import Path

from mutagen.mp3 import MP3

SERATO_MARKERS_V2 = 'GEOB:Serato Markers2'
SERATO_OVERVIEW = 'GEOB:Serato Overview'
SERATO_MARKERS_V1 = 'GEOB:Serato Markers_'
SERATO_ANALYSIS = 'GEOB:Serato Analysis'


def clear_all_tags(track_path: Path, audio_encoding="mp3"):
    assert audio_encoding == "mp3", "only mp3 supported"
    track = MP3(track_path)
    for tag in [
        SERATO_MARKERS_V2,
        SERATO_OVERVIEW,
        SERATO_MARKERS_V1,
        SERATO_ANALYSIS
    ]:
        try:
            track.pop(tag)
        except Exception:
            pass
    track.save()
