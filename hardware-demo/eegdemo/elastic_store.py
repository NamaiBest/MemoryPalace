"""Elastic Cloud Vector DB boundary for captured cognitive moments.

Credentials come only from the process environment.  The store is deliberately
optional: camera capture and local playback must keep working if Elastic is not
configured or temporarily unavailable.
"""
import base64
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_INDEX = "memorypalace-multimodal-moments"
DEFAULT_INFERENCE_ID = ".jina-embeddings-v5-omni-small"
MAX_VIDEO_EMBED_BYTES = 48 * 1024 * 1024


class ElasticError(RuntimeError):
    pass


class ElasticStore:
    def __init__(self, emit, *, url=None, api_key=None, index=None,
                 inference_id=None, dimensions=None):
        self.emit = emit
        self.url = (url if url is not None else os.environ.get("ELASTICSEARCH_URL", "")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("ELASTIC_API_KEY", "")
        self.index = index or os.environ.get("ELASTIC_INDEX", DEFAULT_INDEX)
        self.inference_id = inference_id or os.environ.get(
            "ELASTIC_INFERENCE_ID", DEFAULT_INFERENCE_ID)
        self.dimensions = int(dimensions or os.environ.get("ELASTIC_EMBEDDING_DIMS", "1024"))
        self.ready = False
        self.last_error = None
        self._setup_lock = threading.Lock()

    @property
    def configured(self):
        return bool(self.url and self.api_key)

    def status(self):
        return {
            "configured": self.configured,
            "ready": self.ready,
            "index": self.index,
            "inference_id": self.inference_id,
            "error": self.last_error,
        }

    def _request(self, method, path, body=None, *, allow=(200, 201), timeout=20):
        if not self.configured:
            raise ElasticError("set ELASTICSEARCH_URL and ELASTIC_API_KEY")
        data = None if body is None else json.dumps(body, allow_nan=False).encode()
        request = urllib.request.Request(
            self.url + path,
            data=data,
            method=method,
            headers={
                "Authorization": f"ApiKey {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    payload = response.read()
                    if response.status not in allow:
                        raise ElasticError(f"Elastic returned HTTP {response.status}")
                    return json.loads(payload) if payload else {}
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")[:500]
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise ElasticError(f"Elastic returned HTTP {exc.code}: {detail}") from exc
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                if attempt == 2:
                    reason = getattr(exc, "reason", exc)
                    raise ElasticError(f"Elastic connection failed: {reason}") from exc
            time.sleep(1.5 * (attempt + 1))
        raise ElasticError("Elastic request failed")

    def ensure_ready(self):
        with self._setup_lock:
            self._ensure_ready()

    def _ensure_ready(self):
        if self.ready:
            return
        if not self.configured:
            raise ElasticError("set ELASTICSEARCH_URL and ELASTIC_API_KEY")
        try:
            # Elastic hosts this preconfigured multimodal endpoint, so no separate
            # model credential enters the application or repository.
            self._request(
                "GET",
                "/_inference/embedding/" + urllib.parse.quote(self.inference_id, safe=""),
            )
            mapping = {
                "mappings": {
                    "dynamic": "strict",
                    "properties": {
                        "moment_id": {"type": "keyword"},
                        "recording_id": {"type": "keyword"},
                        "session_id": {"type": "keyword"},
                        "user_id": {"type": "keyword"},
                        "sequence": {"type": "integer"},
                        "timestamp": {"type": "date"},
                        "event_type": {"type": "keyword"},
                        "demo": {"type": "boolean"},
                        "confidence": {"type": "float"},
                        "spike_intensity": {"type": "float"},
                        "spike_confidence": {"type": "float"},
                        "status": {"type": "keyword"},
                        "summary": {"type": "text"},
                        "semantic_title": {"type": "text", "fields": {
                            "keyword": {"type": "keyword", "ignore_above": 128},
                        }},
                        "ai_description": {"type": "text"},
                        "transcript": {"type": "text"},
                        "keywords": {"type": "keyword"},
                        "topics": {"type": "keyword"},
                        "annotation": {"type": "text"},
                        "search_text": {"type": "text"},
                        "embedding_source": {"type": "keyword"},
                        "embedding": {
                            "type": "dense_vector",
                            "dims": self.dimensions,
                            "index": True,
                            "similarity": "cosine",
                        },
                        "media": {
                            "type": "object",
                            "properties": {
                                "thumbnailUrl": {"type": "keyword", "index": False},
                                "videoUrl": {"type": "keyword", "index": False},
                                "alt": {"type": "text", "index": False},
                            },
                        },
                        "context_window": {
                            "type": "object",
                            "properties": {
                                "start": {"type": "date"},
                                "end": {"type": "date"},
                            },
                        },
                        "detector": {"type": "object", "enabled": False},
                        "vision": {"type": "object", "enabled": False},
                    },
                }
            }
            try:
                self._request(
                    "PUT", "/" + urllib.parse.quote(self.index, safe=""), mapping,
                    allow=(200,),
                )
            except ElasticError as exc:
                # resource_already_exists_exception is the expected idempotent case.
                if "resource_already_exists_exception" not in str(exc):
                    raise
            # Existing strict indices need these fields added explicitly. This operation is
            # idempotent and preserves every already-indexed document.
            self._request(
                "PUT", "/" + urllib.parse.quote(self.index, safe="") + "/_mapping",
                {"properties": {
                    "session_id": {"type": "keyword"},
                    "user_id": {"type": "keyword"},
                    "spike_intensity": {"type": "float"},
                    "spike_confidence": {"type": "float"},
                    "ai_description": {"type": "text"},
                    "semantic_title": {"type": "text", "fields": {
                        "keyword": {"type": "keyword", "ignore_above": 128},
                    }},
                    "transcript": {"type": "text"},
                    "keywords": {"type": "keyword"},
                    "topics": {"type": "keyword"},
                    "embedding_source": {"type": "keyword"},
                    "vision": {"type": "object", "enabled": False},
                }}, allow=(200,),
            )
            self.ready = True
            self.last_error = None
            self.emit("elastic_ready", {"index": self.index,
                                        "inference_id": self.inference_id})
        except Exception as exc:
            self.last_error = str(exc)[:500]
            raise

    @staticmethod
    def _embedding(response):
        values = (response.get("embeddings") or response.get("embedding")
                  or response.get("text_embedding")
                  or response.get("data") or [])
        if isinstance(values, list) and values:
            item = values[0]
            if isinstance(item, dict):
                vector = item.get("embedding") or item.get("predicted_value")
                if isinstance(vector, list):
                    return vector
        raise ElasticError("Elastic inference response did not contain an embedding")

    def embed_text(self, text):
        response = self._request(
            "POST",
            "/_inference/embedding/" + urllib.parse.quote(self.inference_id, safe=""),
            {"input": [text]},
        )
        vector = self._embedding(response)
        if len(vector) != self.dimensions:
            raise ElasticError(
                f"Jina returned {len(vector)} dimensions; expected {self.dimensions}")
        return vector

    def embed_video(self, path):
        size = path.stat().st_size
        if size > MAX_VIDEO_EMBED_BYTES:
            raise ElasticError(
                f"video is {size} bytes; multimodal embedding limit is "
                f"{MAX_VIDEO_EMBED_BYTES} bytes")
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        suffix = path.suffix.lower()
        mime = "video/quicktime" if suffix == ".mov" else "video/mp4"
        response = self._request(
            "POST",
            "/_inference/embedding/" + urllib.parse.quote(self.inference_id, safe=""),
            {"input": [{"content": [{
                "type": "video",
                "format": "base64",
                "value": f"data:{mime};base64,{encoded}",
            }]}]},
            timeout=120,
        )
        vector = self._embedding(response)
        if len(vector) != self.dimensions:
            raise ElasticError(
                f"Jina returned {len(vector)} dimensions; expected {self.dimensions}")
        return vector

    @staticmethod
    def searchable_text(moment):
        return "\n".join(part for part in (
            moment.get("summary", ""),
            moment.get("semanticTitle", ""),
            moment.get("aiDescription", ""),
            moment.get("annotation", ""),
            moment.get("transcript", ""),
            " ".join(moment.get("keywords", [])),
            " ".join(moment.get("topics", [])),
            moment.get("eventType", ""),
        ) if part)

    def index_moment(self, moment, media_path=None):
        self.ensure_ready()
        text = self.searchable_text(moment)
        embedding_source = "text"
        if media_path is not None and media_path.is_file() \
                and media_path.suffix.lower() in (".mp4", ".mov"):
            try:
                embedding = self.embed_video(media_path)
                embedding_source = "video"
            except (ElasticError, OSError) as exc:
                self.emit("elastic_video_embedding_fallback", {
                    "moment": moment["id"], "error": str(exc)[:500],
                })
                embedding = self.embed_text(text)
        else:
            embedding = self.embed_text(text)
        document = {
            "moment_id": moment["id"],
            "recording_id": moment.get("recordingId"),
            "session_id": moment.get("sessionId"),
            "user_id": moment.get("userId"),
            "sequence": moment["sequence"],
            "timestamp": moment["timestamp"],
            "event_type": moment["eventType"],
            "demo": bool(moment.get("demo")),
            "confidence": moment["confidence"],
            "spike_intensity": moment.get("spikeIntensity", moment["confidence"]),
            "spike_confidence": moment.get("spikeConfidence", moment["confidence"]),
            "status": moment.get("status", "candidate"),
            "summary": moment.get("summary", ""),
            "semantic_title": moment.get("semanticTitle", ""),
            "ai_description": moment.get("aiDescription", moment.get("summary", "")),
            "transcript": moment.get("transcript", ""),
            "keywords": moment.get("keywords", []),
            "topics": moment.get("topics", []),
            "annotation": moment.get("annotation", ""),
            "search_text": text,
            "embedding": embedding,
            "embedding_source": embedding_source,
            "media": moment.get("media", {}),
            "context_window": moment.get("contextWindow", {}),
            "detector": moment.get("detector"),
            "vision": moment.get("vision"),
        }
        result = self._request(
            "PUT",
            "/" + urllib.parse.quote(self.index, safe="") + "/_doc/"
            + urllib.parse.quote(moment["id"], safe="") + "?refresh=wait_for",
            document,
        )
        self.emit("elastic_moment_indexed", {"moment": moment["id"], "index": self.index})
        return result

    def search(self, query, limit=20, event_type=None, min_intensity=None,
               max_intensity=None, date_from=None, date_to=None, session_id=None,
               user_id=None, sort="relevance"):
        self.ensure_ready()
        query = query.strip()
        filters = []
        if event_type:
            filters.append({"term": {"event_type": event_type}})
        if min_intensity is not None or max_intensity is not None:
            bounds = {}
            if min_intensity is not None:
                bounds["gte"] = min_intensity
            if max_intensity is not None:
                bounds["lte"] = max_intensity
            filters.append({"range": {"spike_intensity": bounds}})
        if date_from is not None or date_to is not None:
            date_bounds = {}
            if date_from is not None:
                date_bounds["gte"] = date_from
            if date_to is not None:
                date_bounds["lte"] = date_to
            filters.append({"range": {"timestamp": date_bounds}})
        if session_id:
            filters.append({"term": {"session_id": session_id}})
        if user_id:
            filters.append({"term": {"user_id": user_id}})
        lexical = ({
            "multi_match": {
                "query": query,
                "fields": ["semantic_title^5", "summary^4", "ai_description^3", "transcript^3",
                           "annotation^2", "search_text", "keywords^2", "topics^2",
                           "event_type"],
            }
        } if query else {"match_all": {}})
        if filters:
            lexical = {"bool": {"must": lexical, "filter": filters}}
        body = {"size": limit, "_source": {"excludes": ["embedding"]}}
        if query:
            knn = {
                "field": "embedding",
                "query_vector": self.embed_text(query),
                "k": limit,
                "num_candidates": max(50, limit * 5),
            }
            if filters:
                knn["filter"] = filters
            body["retriever"] = {"rrf": {
                "retrievers": [{"standard": {"query": lexical}}, {"knn": knn}],
                "rank_window_size": max(50, limit), "rank_constant": 60,
            }}
        else:
            body["query"] = lexical
        if sort == "time":
            body["sort"] = [{"timestamp": "asc"}]
        elif sort == "intensity":
            body["sort"] = [{"spike_intensity": "desc"}, {"timestamp": "asc"}]
        elif sort != "relevance":
            raise ValueError("sort must be relevance, time or intensity")
        response = self._request(
            "POST", "/" + urllib.parse.quote(self.index, safe="") + "/_search", body)
        hits = response.get("hits", {}).get("hits", [])
        moments = []
        for hit in hits:
            source = hit.get("_source", {})
            moments.append({
                "id": source.get("moment_id"),
                "recordingId": source.get("recording_id"),
                "sessionId": source.get("session_id"),
                "userId": source.get("user_id"),
                "sequence": source.get("sequence"),
                "timestamp": source.get("timestamp"),
                "eventType": source.get("event_type"),
                "demo": source.get("demo", False),
                "confidence": source.get("confidence", 0.5),
                "spikeIntensity": source.get("spike_intensity",
                                              source.get("confidence", 0.5)),
                "spikeConfidence": source.get("spike_confidence",
                                               source.get("confidence", 0.5)),
                "status": source.get("status", "candidate"),
                "summary": source.get("summary", ""),
                "semanticTitle": source.get("semantic_title", ""),
                "aiDescription": source.get("ai_description", ""),
                "transcript": source.get("transcript", ""),
                "keywords": source.get("keywords", []),
                "topics": source.get("topics", []),
                "annotation": source.get("annotation", ""),
                "media": source.get("media", {}),
                "contextWindow": source.get("context_window", {}),
                "detector": source.get("detector"),
                "elasticScore": hit.get("_score"),
            })
        if sort == "time":
            moments.sort(key=lambda item: item.get("timestamp", ""))
        elif sort == "intensity":
            moments.sort(key=lambda item: (-item.get("spikeIntensity", 0),
                                           item.get("timestamp", "")))
        return moments
