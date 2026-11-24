import importlib
import importlib.machinery
import sys
import types

import pytest


@pytest.fixture
def workspace_client_calls(monkeypatch):
    calls = []

    class FakeQueryResult:
        def as_dict(self):
            return {
                "manifest": {"columns": [{"name": "id"}, {"name": "text"}, {"name": "score"}]},
                "result": {"data_array": [["doc-1", "hello", 0.9]]},
            }

    class FakeWorkspaceClient:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            self.vector_search_indexes = types.SimpleNamespace(query_index=lambda **_: FakeQueryResult())

    for name in ("databricks", "databricks.sdk"):
        module = types.ModuleType(name)
        module.__spec__ = importlib.machinery.ModuleSpec(name, None)
        monkeypatch.setitem(sys.modules, name, module)
    sys.modules["databricks.sdk"].WorkspaceClient = FakeWorkspaceClient

    databricks_rm = importlib.import_module("dspy.retrievers.databricks_rm")
    monkeypatch.setattr(databricks_rm, "_databricks_sdk_installed", True)
    for name in ("DATABRICKS_TOKEN", "DATABRICKS_HOST", "DATABRICKS_CLIENT_ID", "DATABRICKS_CLIENT_SECRET"):
        monkeypatch.delenv(name, raising=False)
    return databricks_rm.DatabricksRM, calls


def test_service_principal_auth_uses_databricks_endpoint(workspace_client_calls):
    databricks_rm_cls, calls = workspace_client_calls
    retriever = databricks_rm_cls(
        databricks_index_name="my_index",
        databricks_endpoint="https://my-workspace.cloud.databricks.com",
        databricks_client_id="client-id",
        databricks_client_secret="client-secret",
    )

    result = retriever("hello")

    assert result.docs == ["hello"]
    assert calls == [
        {
            "host": "https://my-workspace.cloud.databricks.com",
            "client_id": "client-id",
            "client_secret": "client-secret",
        }
    ]


def test_token_auth_uses_databricks_endpoint(workspace_client_calls):
    databricks_rm_cls, calls = workspace_client_calls
    retriever = databricks_rm_cls(
        databricks_index_name="my_index",
        databricks_endpoint="https://my-workspace.cloud.databricks.com",
        databricks_token="token",
    )

    retriever("hello")

    assert calls == [{"host": "https://my-workspace.cloud.databricks.com", "token": "token"}]
