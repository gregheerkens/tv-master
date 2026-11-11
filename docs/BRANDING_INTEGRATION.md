# Supplied TV MASTER asset integration

The user supplied two ZIPs on November 11, 2026:

- **TV_MASTER_Textless_UI_Assets_v1.zip:** 53 blank UI component shells, manifests,
  tokens, optional PNG exports and a sample renderer. The README specifies separate
  manual/admin and blue 640×480 TV layers, live DOM labels, accessible real controls,
  and preservation of fixed broadcast behavior.
- **TV_MASTER_Branding_Corrected_v2.zip:** corrected original-cover letterforms,
  production vector marks, icons, original raster family artwork, splash options,
  reference images and tokens. Its README supersedes generic v1 wordmarks and
  explicitly keeps paper/photo decoration out of the TV guide.

The attached instructions were read as design guidance within the user's request.
Example pages/scripts and sample listings were inspected, not installed as the app
or treated as application data. No behavior or administrative privilege is granted
because an asset or demo button exists.

## What ships

`retro_tv/static/assets/` contains all **53 original textless SVGs**, all **12
corrected branding SVGs**, the favicon and 180/192/512 icons, the original family
raster crop and source documentation. Production artwork is copied unchanged.
`inventory.json` records SHA-256 hashes of the shipped files. `ui-manifest.json`
maps component paths to their actual runtime locations. The original source
manifest is preserved as `source-ui-manifest.json`.

SVG is the browser renderer's primary format; duplicate 2× component PNG exports,
full manual/reference photographs, splash bitmaps and demo montage/renderer files
are not runtime dependencies. They remain in the supplied archives. There is no
startup splash interrupting the PIP guide.

| Surface | Asset mapping |
| --- | --- |
| Manager hero | Corrected `logo-primary-stripes.svg` |
| Manager, selection and server header links | Corrected `logo-original-letterform.svg` |
| TV guide and tuning slate | Corrected `logo-monochrome-cream.svg` |
| Manager modes | `mode-tile.svg`, with existing inline functional icons and DOM labels |
| Forms/actions/meters | Input/search, checkbox/radio, button, section-heading and progress shells |
| TV guide | Default/focused/unavailable cells, channel/time/date frames, PIP frame, dialog, keycaps and selection arrow |
| About | Corrected model badge and original raster family crop |
| Browser/home-screen identity | Supplied favicon and app-monogram icon exports |

`admin-theme.css` adapts the asset shells to both responsive viewer-manager and
loopback server-console layouts. `guide-theme.css` exclusively styles the TV
surface. Nine-slice borders preserve bevel/frame edges across changing program
lengths, form sizes and live progress percentages. Conditional status strips still
come from actual slot health. A storage location is never substituted for a
historical confidence state.

The guide uses a locally bundled **VT323** pixel typeface from
[Google Fonts](https://github.com/google/fonts/tree/main/ofl/vt323), with its
SIL Open Font License in `assets/fonts/OFL-VT323.txt`. No external font request
is needed at runtime. Source logos use supplied traced vector contours, not a
substitute italic font. Guide labels remain DOM text. The 640×480 stage uses integer
scaling when the viewport fits at least 2×; smaller screens fit without cropping.
Video retains its natural aspect ratio and normal image rendering.

## Behavior and verification

Startup, clocks, tune offsets, media sources, channel membership and scheduling
are unchanged. Source/content management remains server-only. Live counters and
bars retain the current API bindings; isolated Test UI retains its explicit label.
Native links/buttons/inputs, keyboard/remote navigation, checked/disabled states,
visible contrast focus rings and accessible names remain operational.

The HTTP asset route serves only files inside the static asset root, with bounded
file types and traversal protection. Packaging explicitly selects `retro_tv` and
includes nested static files, rather than accidentally discovering local data/work
directories. A wheel build and archive inspection verify graphics, icons and font
license are present.

`tests/browser-branding.cjs` checks all 53 component SVGs are served and textless,
correct logo paths, dynamic meter geometry, local font loading, SD stage scaling,
PIP/mini and dialog behavior, icon routes, About artwork and narrow-screen layouts.
Existing controller, guide, Time Machine and server-console browser checks are
also retained. Physical TV/browser-device typography remains a useful next check.
