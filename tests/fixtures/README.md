# Fixtures

Both files are shared with the TypeScript twin, tserato, byte for byte
(`tserato/tests/fixtures/`). That is deliberate: in subbox the client writes
Serato tags with tserato and the server reads them with pyserato, so the two
libraries agreeing on these exact bytes is the property that matters, and
testing both against one pair of files is how it gets checked.

## `analysed.mp3`

A real Serato-analysed track: four cues (three CUE, one LOOP) and all six of the
GEOB frames Serato writes, with `Serato BeatGrid` present but carrying zero
markers -- analysed, never gridded.

## `analysed.flac`

The same track, and the same Serato payloads, in a FLAC. Built from
`analysed.mp3` with ffmpeg and metaflac -- by neither library, so these tests
are not reading back their own output.

```sh
# audio, losslessly, with none of the MP3's tags
ffmpeg -i analysed.mp3 -map_metadata -1 -c:a flac analysed.flac

# the MP3's own Serato bytes, in the envelope Serato uses for FLAC
python3 - <<'EOF'
import base64
from mutagen.mp3 import MP3

tags = MP3('analysed.mp3')
for desc, field in [('Serato Markers2', 'serato_markers_v2'),
                    ('Serato BeatGrid', 'serato_beatgrid')]:
    payload = next(f.data for k, f in tags.items()
                   if k.startswith('GEOB:') and f.desc == desc)
    raw = b'application/octet-stream\x00\x00' + desc.encode() + b'\x00' + payload
    # unpadded, and wrapped at 72 characters, which is how Serato writes it
    b64 = base64.b64encode(raw).decode().rstrip('=')
    open(f'{field}.txt', 'w').write(
        '\n'.join(b64[i:i + 72] for i in range(0, len(b64), 72)))
EOF

metaflac \
  --set-tag='TITLE=Zenith Lantern' \
  --set-tag='ARTIST=Basalt Bloom' \
  --set-tag='ARTIST=Second Artist' \
  --set-tag='COMMENT=see https://example.test/?a=1&b=2' \
  --set-tag-from-file=serato_markers_v2=serato_markers_v2.txt \
  --set-tag-from-file=serato_beatgrid=serato_beatgrid.txt \
  --add-seekpoint=1s \
  analysed.flac

# plus an APPLICATION block, added with mutagen, that nothing here parses
```

The repeated `ARTIST`, the `=` inside `COMMENT`, the seektable, the application
block and the padding are all there deliberately: they are what a careless tag
writer destroys on the way past, and the write tests assert every one of them
survives.

Serato has never seen this FLAC. What it demonstrates is that the retrieval and
envelope handling are right for bytes in the documented place -- the bytes
themselves come from a file Serato did write.
