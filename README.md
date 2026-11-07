# Pixar's OpenUSD sample assets for PartCAD

Serves the sample assets Pixar offers on [openusd.org's Downloads
page](https://openusd.org/release/dl_downloads.html) as PartCAD parts, published as
`//pub/collection/openusd/pixar/assets`:

| Package | What it is | Parts |
| --- | --- | --- |
| `assets/kitchen-set` | [The Kitchen Set](https://openusd.org/release/dl_kitchen_set.html): a kitchen of 76 props | `Kitchen_set`, `Kitchen_set_instanced` (the whole kitchen) and each prop, by its name: `Bowl`, `Chair`, `TeaKettle`, ... |
| `assets/city-set` | [The City Set](https://openusd.org/release/dl_city_set.html): a city of point instances | `PointInstancedMedCity` |
| `assets/usdskel-examples` | [The UsdSkel examples](https://openusd.org/release/dl_usdskel_examples.html): a skinned character | `HumanFemale`, `HumanFemale_walk`, `HumanFemale_keepAlive` |

```shell
pc list parts //pub/collection/openusd/pixar/assets/kitchen-set
pc search parts -P '//pub/collection/openusd/pixar/assets...' -k kettle
pc inspect //pub/collection/openusd/pixar/assets/kitchen-set:Bowl
pc inspect "//pub/collection/openusd/pixar/assets/usdskel-examples:HumanFemale_walk;time=115"
```

**Accept Pixar's licence first.** Pixar offers these under its USD Asset End User License
Agreement, behind an "OK" button on each asset's page: a temporary, revocable licence for *your
personal, non-commercial testing* of USD, and no production, commercial or distributing use of the
assets or of anything derived from them. Read it on the
[Kitchen Set's page](https://openusd.org/release/dl_kitchen_set.html). Listing the parts asks nothing
of you; building one fetches the asset, which the plugin does only once you have said you accept the
agreement, as your own parameter of the plugin, in `~/.partcad/config.yaml`:

```yaml
parameters:
  "//pub/collection/openusd/pixar:pixar_repo":
    accept_license: true
```

Never in a package: the agreement is between Pixar and you.

**No geometry is vendored.** Every asset is fetched from openusd.org the first time a part of it is
built, and kept by PartCAD from then on.

**Nothing here is manufacturable.** These are props and scenes made to be looked at; the package says
`manufacturable: false`, and so does the plugin of what it serves.

Requires PartCAD 0.9.11 or newer: the first release whose `//builtin` has the `usd` part type.

## Listing, searching, building

**Listing and searching download no asset.** `pc list parts` and `pc search parts` are answered from
the directory of each archive openusd.org offers, read with a range request or two and kept for a week
- about 220 KB for the three. Building a prop reads its own files out of its archive, a request each,
and never the archive, once you have accepted Pixar's licence. What a part is made of is fetched when
the part is built - by `pc inspect`, `pc render`, `pc export`, or an assembly that places it - and then
only that asset's own files, and kept.

`pc search parts -k <words>` is answered by the plugin, from the same catalog: a part matches when
every word is in its name, its description, its author, its tags or its package's name, and the ones
whose name matches come first. Each package answers with at most 20, or what `--limit` says (up to
100); search a package and every one below it with `-P '<package>...'`.

## What a part is

Every part here is `type: usd`: PartCAD's own part type for OpenUSD, in its `//builtin`, which reads a
stage with Pixar's USD library (`usd-core`), installed into the sandbox that builds the part and
nowhere else. The plugin's part is the file, and the part type makes the shape of it.

- **The file.** A part's file is a USDZ package of the asset, which the plugin makes when the part is
  built. An asset published as a `.usdz` is served as it is. One published as `.usd`, `.usda` or
  `.usdc` layers is a root layer that names others by relative path - sublayers, references,
  payloads - and the plugin follows those names (in a text layer its `@asset paths@`, in a binary one
  its token table) and packs the root and everything it reaches into a USDZ, root first, as the format
  wants it. Of the files that are not layers, it carries what the part's look is read from (the
  plugin's `looks`): the shaders the layers name, and the images of the colour, roughness and
  metalness - a smaller copy of each where the source keeps one, else each of up to 8 MB - and not
  the normal, height or occlusion maps. `textures` carries every one, as it is. A file an asset names
  that the source does not have is reported, and the asset is served without it.
- **The shape.** What is built is the stage's default prim - what a reference to the asset brings
  in - and every mesh it shows: through native instancing and point instancers, of the purpose asked
  for, visible ones only, in millimetres (by the stage's `metersPerUnit`) with Z up. A cube, sphere,
  cylinder, cone or capsule is meshed; curves, points and volumes are not surfaces, and are left out
  and counted. Up to 20 000 triangles, each triangle is a face, and two that share an edge share it:
  the part is drawn as lines, written to STEP, and made the solid it bounds where it closes. Past
  that, the triangles of each look are one mesh: fast at any size, drawn shaded (`pc render --style
  shaded`) and written as STL, 3MF or glTF, but with no edges for a line drawing. The part is a
  surface as USD describes it - what a renderer draws - and PartCAD says so when it is not a solid.
- **The look.** Each face is in the colour, roughness and metalness its material says - the material
  bound to its mesh, or to the subset of its faces - and as see-through: a colour a texture gives is
  read off the image where the face lies on it. `UsdPreviewSurface`, MaterialX and NVIDIA's OmniPBR,
  OmniGlass and OmniSurface are read, an MDL preset calling one included; a face with no material, or
  none of those, is in its `displayColor`. Each is stated under PartCAD's `usd` convention by the
  material's name, so a package of yours can claim one with a colour, material or finish of its own
  (`ids: {usd: Ceramic}`); one nothing claims is drawn as the stage says, and is display-only. A shaded
  `pc render` draws the roughness and metalness too.
- **The size.** It is what the asset says it is, by its `metersPerUnit`: an asset authored in the
  wrong units comes out as large, or as small, as it says.
- **The other reader.** `reader=cadmpeg` reads the same file with cadmpeg instead, PartCAD's
  converter for CAD formats, which reads USD from its 0.6.8 release on: what a render shows, at the
  stage's static values. It does no point instancer (the City Set's buildings, the chess set's pawns
  are left out), no `purpose` but `render` and no `time` but `default`, and a prim it reads as an
  exact surface (a cube, a sphere) is counted and left out rather than meshed. It is there as a
  second opinion and a fallback; `usd-core` is the reader to use.

Every part takes the part type's parameters, in its name (`King;purpose=proxy`) or in the `with` of
an enrich of it:

| Parameter | Default | What it is |
| --- | --- | --- |
| `reader` | `usd-core` | What reads the stage: `usd-core`, or `cadmpeg` (see above). |
| `prim` | the default prim | Build only what is under this prim; `/` is the whole stage. |
| `purpose` | `render` | `render`: what a final render draws; `proxy`: the stand-ins a viewer draws; `all`: both, and guides. |
| `surface` | `auto` | `faces`: a face per triangle; `mesh`: a mesh per colour; `auto`: `faces` up to 20 000 triangles. |
| `time` | `default` | The time code to read animated geometry at, skinning a character to it. `default` is what a viewer opens the stage at (its start time code, else its earliest sample), unposed. |
| `maxTriangles` | 5000000 | The most triangles the part may be: a scene of more is refused, saying so. |

PartCAD's own documentation of the part type is
[the `usd` part type](https://partcad.readthedocs.io/en/latest/config_parts.html#usd-files).

The whole kitchen is 537 thousand triangles in 138 colours, 5.8 by 4.5 by 3.2 metres, and a prop a
few hundred to a few thousand. The City Set is about 49 million once its instances are placed: past
the default, and past what is sensible to build into one part - build a `prim` of it, or raise
`maxTriangles` on a machine with the memory for it. HumanFemale's walk runs from time code 101 to 129,
and her idle (`keepAlive`) over a range of its own; outside its range, an animation leaves her in her
bind pose.

## Parameters of the plugin

| Parameter | Default | What it is |
| --- | --- | --- |
| `accept_license` | `false` | Whether you accept Pixar's USD Asset End User License Agreement. Nothing is fetched until you do. Yours alone: set it in `~/.partcad/config.yaml`. |
| `looks` | `true` | Whether a part's USDZ carries what its look is read from: the images of its colour, roughness and metalness, each of up to 8 MB. Of these assets, only HumanFemale has any; the rest are drawn in their `displayColor`. |
| `textures` | `false` | Whether a part's USDZ carries every texture its layers name, each as it is: to open it complete in another USD application. |
| `max_size_mb` | `512` | The most a part's USDZ may be, in MB. An asset found to be larger is refused, saying so, before the rest of it is fetched. |

The last two may also be set in a package of your own, as an enrich of the plugin and a package it
serves:

```yaml
repositories:
  textured_repo:
    type: enrich
    source: //pub/collection/openusd/pixar:pixar_repo
    with:
      textures: true
dependencies:
  pixar_textured:
    type: external
    plugin: :textured_repo
```

## Caching

The plugin keeps what openusd.org answered under `~/.cache/partcad-openusd-pixar/` (or
`$PARTCAD_OPENUSD_PIXAR_CACHE`): each archive's directory for a week, and each file read out of an
archive for good. No archive is downloaded whole: openusd.org takes range requests, so a prop costs the
files it is made of, a request each, and the whole kitchen the files of all its props. A request that
came to nothing is remembered for a while too, so that a refused run is not repeated in full by the
next: a 404 for a day, anything else for five minutes. Delete the directory to start over. PartCAD
keeps every answer the plugin gives, files included.

Every request says what it is: `User-Agent: Mozilla/5.0 (compatible; PartCAD-openusd-pixar/<version>;
+https://github.com/partcad/partcad-collection-openusd-pixar)`.

## Status

Run against openusd.org: all three archives answer range requests, and listing the three packages
reads their directories (8 requests, 218 KB); every prop of the Kitchen Set, the kitchen itself, the
City Set and HumanFemale - standing, and walking at her time codes - were packed by the plugin and
read back by the part type with usd-core 26.11.

With the licence accepted, drawn in their looks (`pc render -t png --style shaded`): the Kitchen Set's
props - the bowl, the chair, the fridge with its notes, the kettle - and the whole kitchen (537
thousand triangles) in the colours their `displayColor` gives, and HumanFemale in her textures,
standing and walking at time code 115.

Through PartCAD's own `usd` part type, run from the change that adds it to `//builtin` before its
release, with all six `partcad-collection-openusd-*` packages in one workspace: `pc list packages -r`
listed their 17 packages, and `pc search parts -P '<workspace>...'` answered across all of them in
about two seconds, each collection searching its own catalog; `pc info` of the TeaKettle without the
licence accepted was refused, saying how to accept it; with it accepted, the parts above were built
and drawn.

## Layout

| Path | Purpose |
| --- | --- |
| `partcad.yaml` | `//pub/collection/openusd/pixar`; the `assets` external dependency and the `pixar_repo` repository that serves it. |
| `pixar_repo.py` | The repository plugin: where Pixar keeps its assets. |
| `usd_assets.py` | What every OpenUSD collection plugin shares, byte for byte: following a USD asset's layers, packing a USDZ, reading remote archives, buckets and listings a piece at a time, searching a catalog, the keys PartCAD asks. |
| `shared.sha256` | The digests of the shared files and their tests. They are the same in every `partcad-collection-openusd-*` repository - pixar, usd-wg, apple, nvidia, aswf-dpel and disney-moana - and a test fails when one here differs: change them in all of them. |
| `test_*.py` | The tests. Nothing in them touches the network. |

```shell
python -m pytest
```

When what the plugin answers changes - here or in `usd_assets.py` - raise `CACHE_VERSION` in
`pixar_repo.py`: PartCAD keys everything it caches of this package on it, and an unchanged version
is answered from what it cached before.

## Licensing

The code here is Apache-2.0 (`LICENSE`). The assets are Pixar's, under the
[USD Asset End User License Agreement](https://openusd.org/release/dl_kitchen_set.html): "Copyright ©
Disney/Pixar"; the Kitchen Set was modelled by Christina Faraj after concept art by Paul Felix. Nothing
of them is in this repository.
