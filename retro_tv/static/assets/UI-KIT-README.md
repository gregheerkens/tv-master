# TV MASTER — Textless UI Components v1.0

**Two intentionally distinct visual layers:**

1. `svg/admin/` and `png/admin/`: warm cream, rust, yellow and ink, derived from the TV MASTER instruction-manual identity. For browser-based manager and server console.
2. `svg/guide/` and `png/guide/`: dark royal-blue late-1990s cable-system bevels, for 640×480 set-top-box guide screens and overlays.

## Why this is more reusable than the original sprite sheets

All **53 graphical source assets contain zero rendered UI text**. Every button caption, title, timestamp, percentage, channel number, station name, and status label must be inserted by HTML/SVG/JS at runtime. Static arrows and non-text decorative symbols are included. SVGs are scalable independent files; PNG exports are transparent 2× rasters for clients that need bitmaps.

The previous generated sprite sheets mixed sample labels into the art; editing the copy in a renderer would have been impossible. These are freshly rebuilt **blank graphics** in the same two design languages, not exact pixel-for-pixel erasures of the mockups.

## Files

- `manifest.json`: list of assets with paths, sizes and intended usage.
- `svg/admin/*.svg`: 31 clean admin graphic shells.
- `svg/guide/*.svg`: 22 clean blue-guide graphic shells.
- `png/admin/*.png` and `png/guide/*.png`: matching 2× transparent raster versions.
- `demo/preview.html`, `demo/theme.css`, `demo/preview.js`: functional reference renderers with sample text inserted from HTML/JS.
- `demo/assets-index-admin.png` and `demo/assets-index-guide.png`: visual inventory sheets (their captions are outside the individual assets).

## Implementation example

```html
<button class="tm-admin-button" type="button">Import sources</button>
<div class="tm-guide-row">
  <div class="channel"><span>31</span><span>WUHF</span></div>
  <div>The X-Files</div><div>News</div><div>...</div>
</div>
```

```css
@import url('./demo/theme.css');
/* Your own code can use the underlying files too: */
.background-shell { background: url('./svg/guide/cell-default.svg') center/100% 100% no-repeat; }
```

`demo/theme.css` is a style reference, not a drop-in replacement for the existing `retro_tv/static` styles. Treat the 640×480 on-TV guide as a fixed-coordinate screen, and keep the responsive manager/server layouts independent. Bind dynamic text from the existing API/DOM. No artwork should be used as authoritative program data.

## Notes for Codex

- **No baked-in program listings or placeholders** in the assets. The demo's sample strings are **only** in HTML/JS and must be replaced with live data.
- Do not put remote/video-control buttons into fixed-broadcast Channel Surf or Time Machine playback merely because a blank button graphic exists. Respect the no-pause/no-skip constraints in `AGENTS.md` and ADRs.
- Do not blur/stretches at the guide's target 640×480; render CSS/overlay text at native scale, then integer-scale the composite when practical.
- These assets are illustrative artwork, not tested accessibility components. Make actual buttons/inputs native HTML or ARIA-accessible elements with visible focus and adequate text contrast.
- Important: never substitute source status labels for historical certainty; `LOCAL`/`REMOTE` concern media storage, not historical evidence.
