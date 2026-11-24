import importlib
import sys

from dspy.utils.lazy_import import is_available


def test_import_and_query_without_databricks_sdk(monkeypatch):
    # Simulate an environment where no `databricks` package is installed.
    monkeypatch.setitem(sys.modules, "databricks", None)
    monkeypatch.delitem(sys.modules, "dspy.retrievers.databricks_rm", raising=False)
    is_available.cache_clear()

    databricks_rm = importlib.import_module("dspy.retrievers.databricks_rm")
    assert databricks_rm._databricks_sdk_installed is False

    requests_made = []

    class FakeResponse:
        def json(self):
            return {
                "manifest": {"columns": [{"name": "id"}, {"name": "text"}, {"name": "score"}]},
                "result": {"data_array": [["doc-1", "hello", 0.9]]},
            }

    def fake_post(url, json, headers):
        requests_made.append((url, json, headers))
        return FakeResponse()

    monkeypatch.setattr(databricks_rm.requests, "post", fake_post)

    retriever = databricks_rm.DatabricksRM(
        databricks_index_name="my_index",
        databricks_endpoint="https://my-workspace.cloud.databricks.com",
        databricks_token="token",
    )
    result = retriever("hello")

    assert result.docs == ["hello"]
    assert result.doc_ids == ["doc-1"]
    assert (
        requests_made[0][0] == "https://my-workspace.cloud.databricks.com/api/2.0/vector-search/indexes/my_index/query"
    )
    assert requests_made[0][2]["Authorization"] == "Bearer token"
