from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions
from Content.knowledge_base import BUILTIN_PRODUCTS

logger = logging.getLogger(__name__)



_STOP_WORDS = {
    "з", "зі", "із", "та", "і", "й", "на", "в", "без",
    "порція", "миска", "тарілка", "шматочок", "шматок",
    "г", "гр", "кг", "мл", "л", "ккал", "грам", "штука", "шт",
}
_WEIGHT_RE = re.compile(r"\d+\s*(?:г|гр|кг|мл|л|ккал)\b", re.IGNORECASE)


def _split_into_components(query: str) -> list[str]:
    clean = _WEIGHT_RE.sub(" ", query)
    parts = re.split(
        r"[,;/+&]|\s+(?:з|із|зі|та|і|й|and|with)\s+",
        clean,
        flags=re.IGNORECASE,
    )
    components = []
    for p in parts:
        p = p.strip()
        if p and p.lower() not in _STOP_WORDS and len(p) > 1:
            components.append(p)
    return components or [query]


class NutritionKnowledgeBase:
    COLLECTION_NAME = "nutrition_kb"
    DEFAULT_SIMILARITY_THRESHOLD = 0.30

    def __init__(
        self,
        persist_dir: str = "./nutrition_chroma",
        api_key: Optional[str] = None,
        collection_name: str = COLLECTION_NAME,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ):
        self._persist_dir = persist_dir
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._collection_name = collection_name
        self._threshold = similarity_threshold

        self._client = chromadb.PersistentClient(path=persist_dir)
        self._ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self._api_key,
            model_name="text-embedding-3-small",
        )
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------ #
    #  Пошук                                                               #
    # ------------------------------------------------------------------ #

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not query.strip():
            return []
        try:
            n = min(top_k, self._collection.count() or 1)
            results = self._collection.query(
                query_texts=[query],
                n_results=n,
            )
            items = []
            for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
                score = round(1.0 - dist, 4)
                if score >= self._threshold:
                    items.append({**meta, "score": score})
            return sorted(items, key=lambda x: x["score"], reverse=True)
        except Exception as exc:
            logger.warning("nutrition_kb.search error: %s", exc)
            return []

    def multi_search(self, query: str, top_k_per_component: int = 3) -> list[dict]:
        components = _split_into_components(query)
        all_queries = list(dict.fromkeys(components + [query]))

        seen: dict[str, dict] = {}
        for q in all_queries:
            hits = self.search(q, top_k=top_k_per_component)
            logger.info(
                "nutrition_kb.multi_search subquery=%s n_results=%d hits=%s",
                json.dumps(q, ensure_ascii=False),
                len(hits),
                json.dumps(hits, ensure_ascii=False, default=str),
            )
            for item in hits:
                name = item["name"]
                if name not in seen or item["score"] > seen[name]["score"]:
                    seen[name] = item

        merged = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        logger.info(
            "nutrition_kb.multi_search summary input_query=%s similarity_threshold=%s "
            "top_k_per_component=%d components=%s expanded_queries=%s unique_by_name=%d merged_ranked=%s",
            json.dumps(query, ensure_ascii=False),
            self._threshold,
            top_k_per_component,
            json.dumps(components, ensure_ascii=False),
            json.dumps(all_queries, ensure_ascii=False),
            len(merged),
            json.dumps(merged, ensure_ascii=False, default=str),
        )
        return merged

    def search_by_category(self, query: str, category: str, top_k: int = 5) -> list[dict]:
        if not query.strip():
            return []
        try:
            n = min(top_k, self._collection.count() or 1)
            results = self._collection.query(
                query_texts=[query],
                n_results=n,
                where={"category": category},
            )
            items = []
            for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
                score = round(1.0 - dist, 4)
                if score >= self._threshold:
                    items.append({**meta, "score": score})
            return sorted(items, key=lambda x: x["score"], reverse=True)
        except Exception as exc:
            logger.warning("nutrition_kb.search_by_category error: %s", exc)
            return []

    def get_by_name(self, name: str) -> Optional[dict]:
        try:
            pid = self._make_id(name)
            result = self._collection.get(ids=[pid])
            if result["ids"]:
                return result["metadatas"][0]
            return None
        except Exception:
            return None

    def build(self, products: Optional[list[dict]] = None, clear: bool = False) -> int:
        if clear:
            self._client.delete_collection(self._collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                embedding_function=self._ef,
                metadata={"hnsw:space": "cosine"},
            )

        items = products or BUILTIN_PRODUCTS
        existing_ids = set(self._collection.get()["ids"])

        docs, metas, ids = [], [], []
        for p in items:
            pid = self._make_id(p["name"])
            if pid in existing_ids:
                continue
            docs.append(self._product_to_doc(p))
            metas.append({
                "name": p["name"],
                "calories": float(p["calories"]),
                "protein": float(p["protein"]),
                "fat": float(p["fat"]),
                "carbs": float(p["carbs"]),
                "category": p.get("category", "other"),
                "aliases": p.get("aliases", ""),
            })
            ids.append(pid)

        if docs:
            BATCH = 50
            for i in range(0, len(docs), BATCH):
                self._collection.add(
                    documents=docs[i:i + BATCH],
                    metadatas=metas[i:i + BATCH],
                    ids=ids[i:i + BATCH],
                )
            logger.info("nutrition_kb.build inserted_count=%d", len(docs))
        else:
            logger.info("nutrition_kb.build inserted_count=0 (no new documents)")

        return len(docs)

    def rebuild(self) -> int:
        return self.build(clear=True)

    def add_product(self, product: dict) -> None:
        pid = self._make_id(product["name"])
        self._collection.upsert(
            documents=[self._product_to_doc(product)],
            metadatas=[{
                "name": product["name"],
                "calories": float(product["calories"]),
                "protein": float(product["protein"]),
                "fat": float(product["fat"]),
                "carbs": float(product["carbs"]),
                "category": product.get("category", "other"),
                "aliases": product.get("aliases", ""),
            }],
            ids=[pid],
        )
        logger.info("nutrition_kb.add_product upsert name=%s", product["name"])

    def count(self) -> int:
        return self._collection.count()

    def list_categories(self) -> list[str]:
        try:
            all_metas = self._collection.get()["metadatas"]
            return sorted({m.get("category", "other") for m in all_metas})
        except Exception:
            return []

    @staticmethod
    def _product_to_doc(p: dict) -> str:
        aliases = p.get("aliases", "")
        category = p.get("category", "")
        return (
            f"{p['name']} {aliases}. "
            f"Калорійність: {p['calories']} ккал на 100г. "
            f"Білки: {p['protein']}г, жири: {p['fat']}г, вуглеводи: {p['carbs']}г. "
            f"Категорія: {category}."
        )

    @staticmethod
    def _make_id(name: str) -> str:
        clean = re.sub(r"[^\w\s-]", "", name.lower())
        clean = re.sub(r"\s+", "_", clean.strip())
        return clean[:64]


def init_knowledge_base(
    persist_dir: str = "./nutrition_chroma",
    api_key: Optional[str] = None,
) -> NutritionKnowledgeBase:
    kb = NutritionKnowledgeBase(persist_dir=persist_dir, api_key=api_key)
    was_empty = kb.count() == 0
    added = kb.build()
    if was_empty:
        logger.info("nutrition_kb.init was_empty products_seeded=%d", added)
    elif added:
        logger.info(
            "nutrition_kb.init incremental_add=%d total_count=%d",
            added,
            kb.count(),
        )
    else:
        logger.info("nutrition_kb.init loaded total_count=%d", kb.count())
    return kb