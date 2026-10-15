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
    """The parts of the Evolus API apply uses, with the shapes known so far: lists come back as JSON arrays, and a
    created library or workflow answers with its "id", a created agent with its "agentId" (as a public ACT III repo
    reads them)."""

    def __init__(self):
        self.libraries = [{"id": "sys-1", "name": "InfiniteCurveMemory1 (2)"}]
        self.documents: dict[str, list[dict]] = {}
        self.agents: list[dict] = []
        self.agent_memories: dict[str, list[str]] = {}
        self.structures: dict[str, list[dict]] = {}
        self.workflows: list[dict] = []
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/api/v1")
        method = request.method
        body = (
            json.loads(request.content)
            if request.headers.get("content-type") == "application/json"
            else None
        )
        docs = re.fullmatch(r"/memories/([^/]+)/documents", path)
        agent_memories = re.fullmatch(r"/agents/([^/]+)/memories", path)
        structures = re.fullmatch(r"/agents/([^/]+)/json", path)
        workflow = re.fullmatch(r"/workflows/([^/]+)", path)
        steps = re.fullmatch(r"/workflows/([^/]+)/steps", path)
        if method == "GET" and path == "/memories":
            return httpx.Response(200, json=self.libraries)
        if method == "POST" and path == "/memories/simple":
            library = {"id": f"lib-{len(self.libraries)}", **body}
            self.libraries.append(library)
            return httpx.Response(200, json=library)
        if docs and method == "GET":
            return httpx.Response(200, json=self.documents.get(docs[1], []))
        if docs and method == "POST":
            name = re.search(rb'filename="([^"]+)"', request.content)[1].decode()
            self.documents.setdefault(docs[1], []).append({"title": name})
            return httpx.Response(201, json={"title": name})
        if method == "GET" and path == "/agents":
            return httpx.Response(200, json=self.agents)
        if method == "POST" and path == "/agents":
            agent = {"agentId": f"agent-{len(self.agents) + 1}", **body}
            self.agents.append(agent)
            return httpx.Response(200, json={"agentId": agent["agentId"]})
        if structures and method == "GET":
            return httpx.Response(200, json=self.structures.get(structures[1], []))
        if structures and method == "POST":
            made = {
                "id": f"structure-{sum(map(len, self.structures.values())) + 1}",
                **body,
            }
            self.structures.setdefault(structures[1], []).append(made)
            return httpx.Response(200, json=made)
        if agent_memories and method == "GET":
            ids = self.agent_memories.get(agent_memories[1], [])
            rows = [{"agentId": agent_memories[1], "memoryId": i} for i in ids]
            return httpx.Response(200, json=rows)
        if agent_memories and method == "POST":
            self.agent_memories.setdefault(agent_memories[1], []).append(
                body["memoryId"]
            )
            return httpx.Response(200, json={})
        if method == "GET" and path == "/workflows/step-catalog":
            types = {"AgentCall": 1, "CreateFile": 5, "Output": 14, "Script": 19}
            return httpx.Response(
                200, json={"steps": [{"key": k, "type": n} for k, n in types.items()]}
            )
        if method == "POST" and steps and not isinstance(body.get("stepType"), int):
            # The real API (15 Oct): "enum fields take their numeric value".
            return httpx.Response(
                400, json={"title": "The request is invalid", "status": 400}
            )
        if method == "GET" and path == "/workflows":
            return httpx.Response(
                200, json=[{k: w[k] for k in ("id", "name")} for w in self.workflows]
            )
        if method == "POST" and path == "/workflows":
            flow = {"id": f"wf-{len(self.workflows) + 1}", **body, "steps": []}
            self.workflows.append(flow)
            return httpx.Response(200, json={"id": flow["id"]})
        if workflow and method == "GET":
            flow = next(w for w in self.workflows if w["id"] == workflow[1])
            return httpx.Response(200, json=flow)
        if steps and method == "POST":
            flow = next(w for w in self.workflows if w["id"] == steps[1])
            flow["steps"].append({"id": f"step-{len(flow['steps']) + 1}", **body})
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"title": "Not Found"})

    def writes(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.method != "GET"]


def apply(
    workspace: FakeWorkspace,
    tmp_path,
    model: str | None = None,
    fallback: str | None = None,
) -> dict:
    return evolus_kit.apply(
        ENV,
        transport=httpx.MockTransport(workspace.handle),
        env_file=tmp_path / ".env",
        model=model,
        fallback=fallback,
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
    assert f"EVOLUS_LIBRARY_ID={ids['library']}" in (tmp_path / ".env").read_text()


def test_apply_with_our_model_builds_the_campaign_desk_and_the_verdict_workflow(
    tmp_path,
):
    workspace = FakeWorkspace()

    ids = apply(workspace, tmp_path, model="own/Gemma", fallback="own/Qwen")

    agent = workspace.agents[0]
    flow = workspace.workflows[0]
    steps = {s["name"]: s for s in flow["steps"]}
    assert (agent["name"], agent["modelKey"]) == (evolus_kit.AGENT, "own/Gemma")
    assert agent["fallbackModelKeys"] == ["own/Qwen"]
    assert workspace.agent_memories[ids["agent"]] == [ids["library"]]
    assert (flow["name"], flow["isActive"]) == (evolus_kit.WORKFLOW, True)
    assert [s["stepType"] for s in flow["steps"]] == [19, 5, 1, 19, 14]
    assert steps["Approval request"]["agentId"] == ids["agent"]
    assert steps["Assemble the result"]["inputStepIds"] == [
        steps["Split the Verdicts"]["id"],
        steps["Approval request"]["id"],
    ]
    env = (tmp_path / ".env").read_text()
    assert f"EVOLUS_AGENT_ID={ids['agent']}" in env
    assert f"EVOLUS_WORKFLOW_ID={ids['workflow']}" in env


def test_apply_with_our_model_builds_the_campaign_invitation_extractor(tmp_path):
    workspace = FakeWorkspace()

    ids = apply(workspace, tmp_path, model="own/Gemma", fallback="own/Qwen")

    reader = next(a for a in workspace.agents if a["agentId"] == ids["reader"])
    (structure,) = workspace.structures[ids["reader"]]
    assert (reader["name"], reader["isExtractor"], reader["modelKey"]) == (
        evolus_kit.READER,
        True,
        "own/Gemma",
    )
    assert reader["fallbackModelKeys"] == ["own/Qwen"]
    assert structure["id"] == ids["invitation_structure"]
    assert (structure["title"], structure["canUseOCR"]) == ("Campaign Invitation", True)
    assert set(json.loads(structure["structure"])) == {
        "marketplace",
        "campaign",
        "slot",
        "registration_closes",
        "items",
    }
    env = (tmp_path / ".env").read_text()
    assert f"EVOLUS_READER_ID={ids['reader']}" in env
    assert f"EVOLUS_INVITATION_STRUCTURE_ID={ids['invitation_structure']}" in env


def test_apply_twice_creates_nothing_new_and_leaves_other_libraries_alone(tmp_path):
    workspace = FakeWorkspace()
    apply(workspace, tmp_path, model="own/tf-gemma")
    writes_after_first_run = len(workspace.writes())

    apply(workspace, tmp_path, model="own/tf-gemma")

    assert len(workspace.writes()) == writes_after_first_run
    assert {r.method for r in workspace.requests} == {"GET", "POST"}
    assert workspace.libraries[0] == {"id": "sys-1", "name": "InfiniteCurveMemory1 (2)"}


def test_apply_never_prints_a_key(tmp_path, capsys):
    apply(FakeWorkspace(), tmp_path, model="own/tf-gemma")

    assert "SECRET" not in capsys.readouterr().out
