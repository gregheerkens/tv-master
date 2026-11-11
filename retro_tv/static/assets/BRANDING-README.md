# TV MASTER / Heritage Brand Rebuild v2

**Corrected to follow the original user-supplied TV-1985 manual cover.** The v1 artwork departed from that cover by using a generic compressed italic wordmark and unrelated CRT emblem. **Do not use the v1 wordmarks as production branding.**

## Source and accuracy

`reference/manual-cover-original.png` is the authoritative source. The primary wordmark SVGs in `assets/svg/` use black letter contours **traced directly from the supplied cover**, with dimensional cream/orange/red outlines recreated in SVG. They are faithful approximations subject to the original reference raster's resolution, not an exact recovered font.

`reference/family-original-framed.png` and `assets/png/family-illustration-original-crop.png` are source-photo crops, **not vector art or true isolated transparencies**. The splash screens use those original illustrations; no new family has been invented. The guide remains visually separate (1990s dark blue/pixel/embossed) and should never inherit paper texture or photo decoration.

## Production assets

- `assets/svg/logo-primary-stripes.svg` / PNG: primary brand lockup with four horizontal bands.
- `assets/svg/logo-original-letterform.svg` / PNG: branding without stripes.
- `assets/svg/logo-monochrome-ink.svg`, `logo-monochrome-cream.svg`: single-color master silhouettes.
- `assets/svg/logo-primary-on-paper.svg`: cream lockup.
- `assets/svg/header-admin.svg`: admin header variant.
- `assets/svg/model-badge.svg`: exact model wording.
- `assets/svg/brand-stripes.svg`, `brand-stripes-corner.svg`: decorative accents.
- `assets/svg/app-monogram-paper.svg`: app icon using TV *from the original wordmark*, not a novel emblem.
- `assets/icons/`: PNG sizes and favicon.
- `assets/png/splash-manual-1920x1080.png`, `splash-manual-dark-1920x1080.png`: source-illustration splashes.

### File format notes

- The core logo letterforms are actual vector contours, not SVG wrappers around raster artwork.
- Decorative tagline and model wording are live SVG `<text>` where applicable, so use appropriate locally available sans-serif typefaces; the principal wordmark needs **no font installation**.
- PNG exports are transparent except named paper/background/splash assets and the source reference crops.

### Important

This brand pack is derived from an image containing an intentionally aged original-style paper manual. Individual transparent logos are suitable for digital UI; the weathering, page patina, and halftone image should be used sparingly in admin/about contexts only. The TV guide is not a manual page.
