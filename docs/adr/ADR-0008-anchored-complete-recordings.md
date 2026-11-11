# ADR 0008: Anchored complete recordings and optional streaming

Status: accepted from the user's November 11, 2026 complete-block request.

A complete recording can be local or an explicitly enabled direct HTTPS video
source. It is cataloged independently of segmentation or restoration. Register a
source bracket and either its broadcast start or a known airing's source offset
and timestamp. The resulting absolute broadcast bracket is fixed and does not
float to another day, channel or start time during recombination. Known imported
airings can provide the timestamp. Contradictory anchors, overlaps and out-of-range
brackets are rejected transactionally.

The composer gives an eligible complete block its original slot and emits one
uninterrupted source reference. Tuning inside it joins the corresponding source
offset. Complete-block footage is counted separately from known program/ad spans;
we do not claim a mixed recording is 90 minutes of program or commercial inventory.
Published programming remains immutable, so newly added blocks affect new viewing
contexts and unpublished airtime, not an existing published gap.

Remote sources are references, not downloaded archives. Their stored identity is
explicitly marked `remote-url:` and is not represented as a media-byte checksum.
A browser follows a current-segment redirect and retrieves/seeks the video itself;
the server does not continuously stream/decode unwatched channels. Availability
starts unknown and changes on actual player success/failure. Direct MP4 range
playback is tested; supported formats and remote availability depend on the player
and source. Streaming is per-source opt-in and has no effect on ordinary local
libraries. Archive item landing pages are not direct video files.

Downloaded or restored copies may be approved as local presentations if they
preserve source duration/timeline. Their file hash and approval are recorded;
the original source reference and broadcast anchor remain intact. Approval is a
human assertion of matching content, not an automatic semantic comparison. The
existing companion may produce optional spans/cuts from a local original. No new
restoration model or remote downloader is required by this slice.

Complete-block ingestion/editor/presentation approval are server-only. The TV/PC
viewer frontends only tune and display them like other broadcasts.
