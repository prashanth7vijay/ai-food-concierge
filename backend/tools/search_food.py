from __future__ import annotations

from sqlalchemy.orm import Session

from backend.repositories.catalog_repository import CatalogRepository
from backend.schemas.catalog import RecommendationItem, SearchFoodParams
from backend.tools.base import ToolResult, run_tool, validate_params
from backend.tools.embeddings import cosine_similarity, get_embedding_provider
from backend.tools.ranking import explain_reason, rank_items
from backend.utils.mappers import menu_item_to_out


def search_food(db: Session, raw_args: dict) -> ToolResult:
    def _run():
        params: SearchFoodParams = validate_params(SearchFoodParams, raw_args)
        repo = CatalogRepository(db)

        # LEVEL 1: structured SQL filtering (hard constraints). These are
        # never relaxed for the sake of semantic similarity (spec section 10).
        candidates = repo.search(
            max_price=params.max_price,
            min_rating=params.min_rating,
            cuisine=params.cuisine,
            dietary_preference=params.dietary_preference,
            spice_level=params.spice_level,
            text_query=None,  # free-text handled semantically below
            limit=200,  # wide candidate pool; final limit applied after ranking
        )

        # LEVEL 2: semantic similarity over the free-text portion of the
        # query (concepts like "something light for dinner"), computed only
        # over items that already passed the hard SQL filters above.
        semantic_scores: dict[str, float] = {}
        if params.query:
            provider = get_embedding_provider()
            query_vec = provider.embed(params.query)
            for item in candidates:
                item_text = f"{item.name} {item.description} {item.tags}"
                item_vec = item.embedding or provider.embed(item_text)
                semantic_scores[str(item.id)] = cosine_similarity(query_vec, item_vec)

        if not candidates:
            return {"items": [], "candidate_count": 0}

        ranked = rank_items(candidates, params, semantic_scores)[: params.limit]
        recommendations = [
            RecommendationItem(
                item=menu_item_to_out(scored.item),
                score=scored.score,
                reason=explain_reason(scored, params),
                match_breakdown=scored.breakdown,
            )
            for scored in ranked
        ]
        return {
            "items": [r.model_dump(mode="json") for r in recommendations],
            "candidate_count": len(candidates),
        }

    return run_tool("search_food", raw_args, _run)
