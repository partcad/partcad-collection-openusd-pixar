#
# partcad-openusd-pixar, 2026
#
# Licensed under Apache License, Version 2.0.
#
"""A PartCAD 'basic' repository plugin that serves Pixar's OpenUSD sample assets as parts.

Published as ``//pub/collection/openusd/pixar/assets``. The assets are the ones
openusd.org offers on its Downloads page, each a zip archive there:

    kitchen-set        the Kitchen Set: the kitchen, as one scene and as its
                       instanced twin, and each of its 76 props
    city-set           the City Set: a city of point instances, as one scene
    usdskel-examples   the UsdSkel examples: HumanFemale, standing, walking and
                       idling (a 'time' poses her)

A child package per archive, a part per asset: ``kitchen-set:Bowl``,
``kitchen-set:Kitchen_set``, ``city-set:PointInstancedMedCity``,
``usdskel-examples:HumanFemale_walk``. Each is ``type: usd``, built by PartCAD's
own part type of that name from a USDZ the plugin packs of the asset's own layers
(see usd_assets.py).

Every archive takes HTTP range requests, so a prop costs its own members, read
out of the archive, and not the archive.

Pixar licenses these under its USD Asset End User License Agreement, behind
an "OK" button on openusd.org: personal, non-commercial testing of USD, and no
more. So nothing is fetched until the user accepts it, as their own parameter
of the plugin (see the README).

PartCAD runs this script once per key (via runpy) with the key in
``request["key"]``; the answer goes in ``output``.
"""

import importlib.util
import os
import posixpath
import sys

# When this plugin's answers stopped meaning what they meant before. PartCAD
# keys everything it caches of this package on it, so raise it with any change
# to what is answered - here, or in usd_assets.py.
#
# v1: Kitchen Set, City Set and UsdSkel examples, as PartCAD 'usd' parts.
# v2: with the files a part's look is read from - its shaders, and its colour and finish
#     images, a smaller copy where the source keeps one ('looks').
CACHE_VERSION = 2


def _shared():
    """usd_assets.py, beside this script, under a name of this plugin's own."""
    name = "_partcad_openusd_pixar_usd_assets"
    if name not in sys.modules:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usd_assets.py")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


ua = _shared()

FILES = "https://openusd.org/files/"
RELEASE = "https://openusd.org/release/"
COPYRIGHT = "Copyright Disney/Pixar"

# Each child package: the archive, the folder everything in it is under, the
# page it is offered on, and what it is.
COLLECTIONS = {
    "kitchen-set": {
        "archive": FILES + "Kitchen_set.zip",
        "prefix": "Kitchen_set",
        "page": RELEASE + "dl_kitchen_set.html",
        "desc": "Pixar's Kitchen Set: a kitchen of 76 props, modelled by Christina Faraj after concept art by "
        "Paul Felix - the kitchen as a scene, and each prop as a part.",
        "author": "Christina Faraj (Pixar), after concept art by Paul Felix",
    },
    "city-set": {
        "archive": FILES + "PointInstancedMedCity.zip",
        "prefix": "PointInstancedMedCity",
        "page": RELEASE + "dl_city_set.html",
        "desc": "Pixar's City Set: a city built of point instances, as one scene.",
    },
    "usdskel-examples": {
        "archive": FILES + "UsdSkelExamples.zip",
        "prefix": "UsdSkelExamples",
        "page": RELEASE + "dl_usdskel_examples.html",
        "desc": "Pixar's UsdSkel examples: HumanFemale, a skinned character, in her bind pose and in two "
        "animations ('time' poses her).",
    },
}

# Of the Kitchen Set's two scenes, what each is.
_SCENES = {
    "Kitchen_set": "The whole kitchen, every prop in place.",
    "Kitchen_set_instanced": "The whole kitchen, its repeated props as USD instances: the same geometry.",
    "PointInstancedMedCity": "The whole city, its buildings point instances.",
    "HumanFemale": "HumanFemale in her bind pose; her 'geometricLOD' variant is 'full' unless the layer says "
    "otherwise.",
    "HumanFemale_walk": "HumanFemale walking: a 'time' between the clip's start and end poses her.",
    "HumanFemale_keepAlive": "HumanFemale idling: a 'time' between the clip's start and end poses her.",
}


class Pixar(ua.Source):
    NAME = "openusd-pixar"
    TITLE = "Pixar"
    URL = RELEASE + "dl_downloads.html"
    DESC = (
        "Pixar's OpenUSD sample assets, from openusd.org: the Kitchen Set, the City Set and the UsdSkel "
        "examples, a child package each and a part per asset."
    )
    LICENSE = "LicenseRef-Pixar-USD-Asset-EULA"
    VERSION = CACHE_VERSION
    REPOSITORY = "partcad-collection-openusd-pixar"
    PLUGIN = "//pub/collection/openusd/pixar:pixar_repo"
    LICENSE_GATE = {
        "name": "USD Asset End User License Agreement",
        "url": RELEASE + "dl_kitchen_set.html",
        "terms": "a temporary, revocable licence for your personal, non-commercial testing of USD; no "
        "production or commercial use, and no distribution of the assets or of anything derived from them",
    }

    def collections(self):
        return {name: ua.Collection(name, spec["desc"], spec["page"]) for name, spec in COLLECTIONS.items()}

    def store(self, collection):
        spec = COLLECTIONS[collection]
        name = spec["archive"].rsplit("/", 1)[1]
        return ua.ZipStore(self.http, spec["archive"], name, prefix=spec["prefix"])

    def assets(self, collection):
        spec = COLLECTIONS.get(collection)
        if spec is None:
            return {}
        store = self.store(collection)
        listing = store.listing()
        found = {}

        def add(id, root, desc, title=None):
            found[ua.safe_id(id)] = ua.Asset(
                id,
                store,
                root,
                title=title or id,
                desc=desc,
                url=spec["page"],
                author=spec.get("author") or COPYRIGHT,
            )

        # The scenes: the layers at the top of the archive (or of a
        # character's folder), which are what the archive is opened by.
        for path in sorted(listing):
            folder, name = posixpath.split(path)
            stem, ext = posixpath.splitext(name)
            if ext.lower() not in (".usd", ".usda", ".usdc", ".usdz"):
                continue
            if folder == "" or (folder.count("/") == 0 and name.startswith(folder + ".")):
                id = stem.replace(".", "_")
                add(id, path, _SCENES.get(id, "A scene of Pixar's %s." % collection))
        # The props: 'assets/<Name>/<Name>.usd', each its own model.
        for path in sorted(listing):
            parts = path.split("/")
            if len(parts) == 3 and parts[0] == "assets" and parts[2] == parts[1] + ".usd":
                add(parts[1], path, "%s, a prop of Pixar's Kitchen Set." % parts[1])
        return found


def get(key):
    return ua.serve(Pixar(globals().get("request")), key)


# Last, so that everything above is defined when PartCAD runs this.
if __name__ == "get":
    output = {"result": get(request["key"])}  # noqa: F821 - injected by the runtime
else:
    output = {}
