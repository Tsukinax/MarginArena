"""The Evolus kit's promises, checked against a fake Evolus API at the network edge.

`plan` only reads: it must never create, change or delete anything in the user's workspace, and its report must
never contain a key.
"""

import evolus_kit
import httpx

ENV = {
    "EVOLUS_API_KEY": "app-key-SECRET-1234567890",
    "EVOLUS_APPLICATION_ID": "app-id-42",
    "EVOLUS_USER_API_KEY": "user-key-SECRET-0987654321",
}


def fake_evolus(seen: list[httpx.Request]):
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200, json=[{"id": "x1", "name": "Something already there"}]
        )

    return httpx.MockTransport(handle)


def test_plan_only_reads_the_workspace():
    seen: list[httpx.Request] = []

    evolus_kit.plan(ENV, transport=fake_evolus(seen))

    assert seen, "plan should look at the workspace"
    assert {r.method for r in seen} == {"GET"}


def test_plan_never_prints_a_key(capsys):
    evolus_kit.plan(ENV, transport=fake_evolus([]))

    printed = capsys.readouterr().out
    assert "SECRET" not in printed
