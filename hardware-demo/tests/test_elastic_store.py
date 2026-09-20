from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eegdemo.elastic_store import ElasticError, ElasticStore


class FakeElastic(ElasticStore):
    def __init__(self):
        self.events = []
        super().__init__(lambda kind, detail: self.events.append((kind, detail)),
                         url="https://example.es.elastic.cloud", api_key="secret",
                         dimensions=3)
        self.calls = []
        self.search_response = {"hits": {"hits": []}}

    def _request(self, method, path, body=None, *, allow=(200, 201), timeout=20):
        self.calls.append((method, path, body))
        if path.endswith("/_search"):
            return self.search_response
        if method == "POST" and path.startswith("/_inference/"):
            return {"embeddings": [{"embedding": [0.1, 0.2, 0.3]}]}
        return {"acknowledged": True}


class ElasticStoreTests(unittest.TestCase):
    def test_unconfigured_store_exposes_no_secret_and_fails_cleanly(self):
        store = ElasticStore(lambda *_: None, url="", api_key="")
        self.assertEqual(store.status()["configured"], False)
        self.assertNotIn("api_key", store.status())
        with self.assertRaisesRegex(ElasticError, "ELASTICSEARCH_URL"):
            store.ensure_ready()

    def test_indexes_jina_embedding_into_dense_vector_document(self):
        store = FakeElastic()
        moment = {
            "id": "capture-123", "recordingId": "recording-1", "sequence": 1,
            "timestamp": "2026-09-19T12:00:00Z", "eventType": "surprise",
            "demo": True, "confidence": 0.8, "summary": "Startled while reading",
            "spikeIntensity": 0.82, "spikeConfidence": 0.91,
            "sessionId": "session-7", "userId": "user-3",
            "semanticTitle": "Reading interrupted by a loud sound",
            "aiDescription": "A startled reading moment", "transcript": "That was loud",
            "keywords": ["reading", "loud"], "topics": ["books"],
            "annotation": "A loud sound", "status": "candidate", "media": {},
            "contextWindow": {"start": "2026-09-19T11:59:50Z",
                              "end": "2026-09-19T12:00:00Z"}, "detector": None,
        }
        store.index_moment(moment)
        document = next(body for method, path, body in store.calls
                        if method == "PUT" and "/_doc/" in path)
        self.assertEqual(document["embedding"], [0.1, 0.2, 0.3])
        self.assertIn("Startled while reading", document["search_text"])
        self.assertIn("That was loud", document["search_text"])
        self.assertEqual(document["semantic_title"], "Reading interrupted by a loud sound")
        self.assertEqual(document["session_id"], "session-7")
        self.assertEqual(document["spike_intensity"], 0.82)
        self.assertIn(("elastic_moment_indexed",
                       {"moment": "capture-123", "index": store.index}), store.events)

    def test_indexes_video_embedding_for_text_to_video_search(self):
        store = FakeElastic()
        moment = {
            "id": "capture-video", "sequence": 1,
            "timestamp": "2026-09-19T12:00:00Z", "eventType": "load",
            "confidence": 0.7, "summary": "A captured scene", "media": {},
            "contextWindow": {},
        }
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "tiny-test-video.mp4"
            video.write_bytes(b"not-a-real-video-but-the-boundary-encodes-bytes")
            store.index_moment(moment, video)
        inference = next(body for method, path, body in store.calls
                         if method == "POST" and path.startswith("/_inference/"))
        content = inference["input"][0]["content"][0]
        self.assertEqual(content["type"], "video")
        self.assertTrue(content["value"].startswith("data:video/mp4;base64,"))
        document = next(body for method, path, body in store.calls
                        if method == "PUT" and "/_doc/" in path)
        self.assertEqual(document["embedding_source"], "video")

    def test_deletes_document_without_touching_media(self):
        store = FakeElastic()
        store.ready = True
        store.delete_moment("capture-123")
        self.assertIn(
            ("DELETE", "/memorypalace-multimodal-moments/_doc/capture-123?refresh=wait_for", None),
            store.calls,
        )
        self.assertIn(("elastic_moment_deleted", {
            "moment": "capture-123", "index": store.index,
        }), store.events)

    def test_search_uses_rrf_to_fuse_bm25_and_knn(self):
        store = FakeElastic()
        store.ready = True
        store.search_response = {"hits": {"hits": [{
            "_score": 0.42,
            "_source": {
                "moment_id": "capture-123", "recording_id": "recording-1",
                "sequence": 1, "timestamp": "2026-09-19T12:00:00Z",
                "event_type": "surprise", "demo": True, "confidence": 0.8,
                "spike_intensity": 0.8, "spike_confidence": 0.9,
                "session_id": "session-7", "user_id": "user-3",
                "status": "candidate", "summary": "Startled while reading",
                "semantic_title": "Reading interrupted by a loud sound",
                "ai_description": "A startled reading moment", "transcript": "That was loud",
                "keywords": ["reading"], "topics": ["books"], "annotation": "", "media": {},
                "context_window": {"start": "2026-09-19T11:59:50Z",
                                   "end": "2026-09-19T12:00:00Z"},
            },
        }]}}
        moments = store.search("surprised by a book", event_type="surprise",
                               min_intensity=0.6, max_intensity=0.84,
                               date_from="2026-09-01T00:00:00Z", session_id="session-7")
        body = next(body for method, path, body in store.calls if path.endswith("/_search"))
        retrievers = body["retriever"]["rrf"]["retrievers"]
        self.assertIn("standard", retrievers[0])
        self.assertEqual(retrievers[1]["knn"]["field"], "embedding")
        self.assertEqual(retrievers[1]["knn"]["filter"][0],
                         {"term": {"event_type": "surprise"}})
        self.assertEqual(retrievers[1]["knn"]["filter"][1],
                         {"range": {"spike_intensity": {"gte": 0.6, "lte": 0.84}}})
        self.assertEqual(retrievers[1]["knn"]["filter"][3],
                         {"term": {"session_id": "session-7"}})
        self.assertEqual(retrievers[1]["knn"]["filter"][-1],
                         {"bool": {"must_not": [{"term": {"status": "deleted"}}]}})
        self.assertEqual(moments[0]["id"], "capture-123")
        self.assertEqual(moments[0]["eventType"], "surprise")
        self.assertEqual(moments[0]["semanticTitle"], "Reading interrupted by a loud sound")
        self.assertEqual(moments[0]["transcript"], "That was loud")


if __name__ == "__main__":
    unittest.main()
