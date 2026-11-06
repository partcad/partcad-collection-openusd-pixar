#
# partcad-openusd-pixar, 2026
#
# Licensed under Apache License, Version 2.0.
#
"""Tests of the Pixar plugin, with openusd.org answered from a table.

The archives have the layout openusd.org's have - 'Kitchen_set/assets/<Name>/'
with a model, its payload and its geometry, a character's folder of layers -
with made-up layers in them. Nothing here touches the network.
"""

import base64
import importlib.util
import io
import os
import re
import runpy
import zipfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN = os.path.join(_HERE, "pixar_repo.py")
_SPEC = importlib.util.spec_from_file_location("pixar_repo_under_test", _PLUGIN)
plugin = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(plugin)
ua = plugin.ua


def _usda(text):
    return ("#usda 1.0\n" + text).encode()


def _zip(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


def _prop(name):
    return {
        "Kitchen_set/assets/%s/%s.usd"
        % (name, name): _usda('def "%s" ( payload = @./%s_payload.usd@ ) {}\n' % (name, name)),
        "Kitchen_set/assets/%s/%s_payload.usd"
        % (name, name): _usda('def "%s" ( references = @./%s.geom.usd@ ) {}\n' % (name, name)),
        "Kitchen_set/assets/%s/%s.geom.usd" % (name, name): _usda("\n"),
    }


KITCHEN = {
    "Kitchen_set/Kitchen_set.usd": _usda(
        'def "Kitchen_set" {\n def "Bowl" ( references = @./assets/Bowl/Bowl.usd@ ) {}\n'
        ' def "Cup" ( references = @./assets/Cup/Cup.usd@ ) {}\n}\n'
    ),
    "Kitchen_set/Kitchen_set_instanced.usd": _usda('def "Kitchen_set" ( references = @./Kitchen_set.usd@ ) {}\n'),
    "Kitchen_set/README.txt": b"readme",
    # What makes the archive large enough for its directory to be a small part of it.
    "Kitchen_set/assets/Bowl/textures/glaze.png": os.urandom(400000),
    "Kitchen_set/LICENSE.txt": b"licence",
    **_prop("Bowl"),
    **_prop("Cup"),
}
SKEL = {
    "UsdSkelExamples/HumanFemale/HumanFemale.usd": _usda(
        'def "HumanFemale" ( references = @./assets/HumanFemale.full.usd@ ) {}\n'
    ),
    "UsdSkelExamples/HumanFemale/HumanFemale.walk.usd": _usda("( subLayers = [@./HumanFemale.usd@] )\n"),
    "UsdSkelExamples/HumanFemale/assets/HumanFemale.full.usd": _usda(
        'def "Body" {\n asset t = @../textures/skin.png@\n}\n'
    ),
    "UsdSkelExamples/HumanFemale/textures/skin.png": b"png",
    "UsdSkelExamples/VERSION.txt": b"1",
}
CITY = {"PointInstancedMedCity/PointInstancedMedCity.usd": _usda('def "MediterraneanHills" {}\n')}
TABLE = {
    plugin.FILES + "Kitchen_set.zip": _zip(KITCHEN),
    plugin.FILES + "UsdSkelExamples.zip": _zip(SKEL),
    plugin.FILES + "PointInstancedMedCity.zip": _zip(CITY),
}


class Wire:
    def __init__(self, table):
        self.table = dict(table)
        self.asked = []

    def __call__(self, url, headers=None, method=None, timeout=120):
        headers = dict(headers or {})
        self.asked.append((url, headers.get("Range")))
        if url not in self.table:
            return ua.Response(404, {}, b"", url)
        body = self.table[url]
        if headers.get("Range"):
            start, end = (int(v) for v in re.match(r"bytes=(\d+)-(\d+)", headers["Range"]).groups())
            end = min(end, len(body) - 1)
            return ua.Response(
                206, {"Content-Range": "bytes %d-%d/%d" % (start, end, len(body))}, body[start : end + 1], url
            )
        return ua.Response(200, {}, body, url)


@pytest.fixture
def pixar(tmp_path, monkeypatch):
    monkeypatch.setenv("PARTCAD_OPENUSD_PIXAR_CACHE", str(tmp_path))

    def make(**parameters):
        made = plugin.Pixar({"parameters": parameters})
        made.http.request = Wire(TABLE)

        def download(url, target, what, timeout=3600):
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
                f.write(TABLE[url])
            return target

        made.http.download = download
        return made

    return make


def test_a_child_package_per_archive(pixar):
    assert pixar().get("deps") == ["city-set", "kitchen-set", "usdskel-examples"]
    assert pixar().get("kitchen-set/meta")["url"] == "https://openusd.org/release/dl_kitchen_set.html"


def test_the_kitchen_is_its_two_scenes_and_its_props(pixar):
    parts = pixar().get("kitchen-set/objects/part")
    assert list(parts) == ["Kitchen_set", "Kitchen_set_instanced", "Bowl", "Cup"]
    assert parts["Bowl"]["type"] == "usd"
    assert parts["Bowl"]["license"] == "LicenseRef-Pixar-USD-Asset-EULA"
    assert "Christina Faraj" in parts["Bowl"]["author"]


def test_a_character_is_each_of_its_top_layers(pixar):
    assert list(pixar().get("usdskel-examples/objects/part")) == ["HumanFemale", "HumanFemale_walk"]
    assert list(pixar().get("city-set/objects/part")) == ["PointInstancedMedCity"]


def test_nothing_is_fetched_until_the_licence_is_accepted(pixar, capsys):
    made = pixar()
    assert ua.serve(made, "kitchen-set/files/Bowl.usdz") is None
    said = capsys.readouterr().err
    assert "USD Asset End User License Agreement" in said
    assert '"//pub/collection/openusd/pixar:pixar_repo":' in said
    assert "accept_license: true" in said


def test_a_prop_is_a_package_of_its_own_layers(pixar):
    data = base64.b64decode(pixar(accept_license=True).get("kitchen-set/files/Bowl.usdz"))
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.namelist() == ["Bowl.usd", "Bowl_payload.usd", "Bowl.geom.usd"]


def test_the_kitchen_is_a_package_of_every_prop_it_places(pixar):
    data = base64.b64decode(pixar(accept_license=True).get("kitchen-set/files/Kitchen_set.usdz"))
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
    assert names[0] == "Kitchen_set.usd"
    assert "assets/Cup/Cup.geom.usd" in names and "README.txt" not in names


def test_textures_only_when_asked_for(pixar):
    plain = base64.b64decode(pixar(accept_license=True).get("usdskel-examples/files/HumanFemale.usdz"))
    with zipfile.ZipFile(io.BytesIO(plain)) as z:
        assert "textures/skin.png" not in z.namelist()
    textured = pixar(accept_license=True, textures=True)
    assert textured.get("usdskel-examples/objects/part/HumanFemale")["path"] == "HumanFemale.textured.usdz"
    data = base64.b64decode(textured.get("usdskel-examples/files/HumanFemale.textured.usdz"))
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.namelist() == ["HumanFemale.usd", "assets/HumanFemale.full.usd", "textures/skin.png"]


def test_listing_and_searching_read_only_the_archive_s_directory(pixar):
    made = pixar()
    assert "Bowl" in made.get("kitchen-set/objects/part")
    assert list(made.get("kitchen-set/search/part?q=bowl")) == ["Bowl"]
    # A probe of a byte, and the directory at the archive's end: never the archive.
    assert all(asked is not None for _, asked in made.http.request.asked)
    size = len(TABLE[plugin.FILES + "Kitchen_set.zip"])
    fetched = sum(int(end) - int(start) + 1 for start, end in
                  (re.match(r"bytes=(\d+)-(\d+)", asked).groups() for _, asked in made.http.request.asked))  # fmt: skip
    assert fetched < size


def test_building_an_asset_fetches_its_own_members_and_no_others(pixar):
    made = pixar(accept_license=True)
    made.get("kitchen-set/objects/part")
    made.http.request.asked.clear()
    made.get("kitchen-set/files/Bowl.usdz")
    assert len(made.http.request.asked) == 3  # Bowl.usd, its payload, its geometry
    # Kept: the kitchen fetches only what the bowl did not.
    again = pixar(accept_license=True)
    again.get("kitchen-set/files/Kitchen_set.usdz")
    # Kitchen_set.usd, and the cup's three: the bowl's three are kept.
    assert len(again.http.request.asked) == 4


def test_it_says_what_it_is():
    assert "PartCAD-openusd-pixar/%d" % plugin.CACHE_VERSION in plugin.Pixar().http.user_agent
    assert "github.com/partcad/partcad-collection-openusd-pixar" in plugin.Pixar().http.user_agent


def test_the_plugin_is_named_as_the_package_declares_it():
    with open(os.path.join(_HERE, "partcad.yaml")) as f:
        text = f.read()
    name = re.search(r"^name: (\S+)", text, re.M).group(1)
    assert re.search(r"^  pixar_repo:\n    type: basic\n    path: pixar_repo.py", text, re.M)
    assert plugin.Pixar.PLUGIN == name + ":pixar_repo"


def test_partcad_runs_it_and_reads_the_answer_from_output(tmp_path, monkeypatch):
    monkeypatch.setenv("PARTCAD_OPENUSD_PIXAR_CACHE", str(tmp_path))
    result = runpy.run_path(_PLUGIN, init_globals={"request": {"key": "meta", "parameters": {}}}, run_name="get")
    assert result["output"]["result"]["manufacturable"] is False
    result = runpy.run_path(
        _PLUGIN, init_globals={"request": {"key": "kitchen-set/objects/partType", "parameters": {}}}, run_name="get"
    )
    assert result["output"]["result"] == {}  # PartCAD's own 'usd' builds the parts
