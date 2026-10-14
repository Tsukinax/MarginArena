"""The Evolus kit's promises, checked against a fake Evolus API at the network edge.

`plan` only reads: it must never create, change or delete anything in the user's workspace, and its report must
never contain a key. `apply` creates what MarginArena needs, once: run it again and nothing new is created.
"""

import json
import re

import evolus_kit
import httpx

ENV = {
    "EVOLUS_API_KEY": "app-key-SECRET-1234567890",
    "EVOLUS_APPLICATION_ID": "app-id-42",
    "EVOLUS_USER_API_KEY": "user-key-SECRET-0987654321",
}


CATALOG = {
    "steps": [
        {"key": "Script", "type": 19, "title": "Run a script", "parts": 2},
        {"key": "PhoneCall", "type": 15, "title": "Call a number", "parts": 1},
    ],
    "topics": [{"key": "placeholders", "title": "Placeholders", "parts": 1}],
}


def fake_evolus(seen: list[httpx.Request]):
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/workflows/step-catalog"):
            return httpx.Response(200, json=CATALOG)
        if "/workflows/step-catalog/" in request.url.path:
            return httpx.Response(200, text="# Step docs\nFields: ...")
        return httpx.Response(
            200, json=[{"id": "x1", "name": "Something already there"}]
        )

    return httpx.MockTransport(handle)


def test_plan_only_reads_the_workspace():
    seen: list[httpx.Request] = []

    evolus_kit.plan(ENV, transport=fake_evolus(seen))

    assert seen, "plan should look at the workspace"
    assert {r.method for r in seen} == {"GET"}


def test_plan_reads_every_part_of_the_docs_for_the_steps_apply_uses():
    seen: list[httpx.Request] = []

    answers = evolus_kit.plan(ENV, transport=fake_evolus(seen))

    docs = {
        (r.url.path.rsplit("/", 1)[-1], r.url.params["part"])
        for r in seen
        if "/workflows/step-catalog/" in r.url.path
    }
    assert docs == {("Script", "1"), ("Script", "2"), ("placeholders", "1")}
    assert answers["step docs"]["Script#2"] == "# Step docs\nFields: ..."


def test_plan_never_prints_a_key(capsys):
    evolus_kit.plan(ENV, transport=fake_evolus([]))

    printed = capsys.readouterr().out
    assert "SECRET" not in printed


class FakeWorkspace:
    """Knowledge libraries as the real API answered on 15 Oct: GET lists, POST returns the new id."""

    def __init__(self):
        self.libraries = [{"id": "sys-1", "name": "InfiniteCurveMemory1 (2)"}]
        self.documents: dict[str, list[dict]] = {}
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/api/v1")
        docs = re.fullmatch(r"/memories/([^/]+)/documents", path)
        if request.method == "GET" and path == "/memories":
            return httpx.Response(200, json=self.libraries)
        if request.method == "POST" and path == "/memories/simple":
            library = {
                "id": f"lib-{len(self.libraries)}",
                **json.loads(request.content),
            }
            self.libraries.append(library)
            return httpx.Response(200, json=library)
        if docs and request.method == "GET":
            return httpx.Response(200, json=self.documents.get(docs[1], []))
        if docs and request.method == "POST":
            name = re.search(rb'filename="([^"]+)"', request.content)[1].decode()
            self.documents.setdefault(docs[1], []).append({"title": name})
            return httpx.Response(201, json={"title": name})
        return httpx.Response(404, json={"title": "Not Found"})

    def writes(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.method != "GET"]


def apply(workspace: FakeWorkspace, tmp_path) -> dict:
    return evolus_kit.apply(
        ENV, transport=httpx.MockTransport(workspace.handle), env_file=tmp_path / ".env"
    )


def test_apply_creates_the_library_and_uploads_every_document_in_english(tmp_path):
    workspace = FakeWorkspace()

    ids = apply(workspace, tmp_path)

    created = [r for r in workspace.writes() if r.url.path.endswith("/memories/simple")]
    uploads = [r for r in workspace.writes() if r.url.path.endswith("/documents")]
    assert [json.loads(r.content)["name"] for r in created] == [evolus_kit.LIBRARY]
    assert {r.url.params["language"] for r in uploads} == {"en"}
    assert sorted(d["title"] for d in workspace.documents[ids["library"]]) == [
        "hydralab-reseller-agreement.md",
        "shopee-th-fees-and-campaigns.md",
    ]
    assert all("X-User-ApiKey" in r.headers for r in workspace.writes())
    assert f"EVOLUS_LIBRARY_ID={ids['library']}" in (tmp_path / ".env").read_text()


def test_apply_twice_creates_nothing_new_and_leaves_other_libraries_alone(tmp_path):
    workspace = FakeWorkspace()
    apply(workspace, tmp_path)
    writes_after_first_run = len(workspace.writes())

    apply(workspace, tmp_path)

    assert len(workspace.writes()) == writes_after_first_run
    assert {r.method for r in workspace.requests} == {"GET", "POST"}
    assert workspace.libraries[0] == {"id": "sys-1", "name": "InfiniteCurveMemory1 (2)"}


def test_apply_never_prints_a_key(tmp_path, capsys):
    apply(FakeWorkspace(), tmp_path)

    assert "SECRET" not in capsys.readouterr().out
