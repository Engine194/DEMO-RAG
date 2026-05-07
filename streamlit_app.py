from __future__ import annotations

import requests
import streamlit as st


API_BASE_DEFAULT = "http://localhost:8010"
STRATEGIES = ["fixed", "overlap", "semantic"]


def post_json(url: str, payload: dict) -> dict:
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def run_query(
    *,
    api_base: str,
    strategy: str,
    query: str,
    top_k: int,
    threshold_enabled: bool,
    threshold: float,
    doc_id: str,
) -> dict:
    payload = {
        "query": query,
        "strategy": strategy,
        "top_k": int(top_k),
        "threshold": threshold if threshold_enabled else None,
        "doc_id": doc_id or None,
    }
    return post_json(f"{api_base}/query", payload)


def render_strategy_result(strategy: str, data: dict) -> None:
    st.markdown(f"### {strategy.upper()}")
    st.caption(f"Returned: {data.get('total_returned', 0)} chunks")
    results = data.get("results", [])
    if not results:
        st.warning("No chunks returned.")
        return

    for item in results:
        st.markdown(
            f"**#{item.get('rank')}** | "
            f"similarity: `{item.get('similarity', 0):.4f}` | "
            f"distance: `{item.get('distance', 0):.4f}`"
        )
        st.code(item.get("text", ""), language="text")
        st.divider()


def fetch_peek_data(api_base: str, strategy: str, limit: int) -> dict:
    resp = requests.get(
        f"{api_base}/debug/chroma/peek",
        params={"strategy": strategy, "limit": limit},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    st.set_page_config(page_title="Chroma Compare UI", layout="wide")
    st.title("Chroma Query Compare")
    st.caption("Goal: query and compare retrieval results across fixed / overlap / semantic.")

    api_base = st.sidebar.text_input("API base URL", value=API_BASE_DEFAULT).rstrip("/")
    st.sidebar.markdown("Swagger: `%s/swagger`" % api_base)
    tab_compare, tab_browse = st.tabs(["Compare Strategies", "Browse By Chunk Type"])

    with tab_compare:
        doc_id = st.text_input("doc_id (optional)", value=st.session_state.get("last_doc_id", ""))
        query = st.text_area("query", value="phat trien san pham nhu nao")

        control_col1, control_col2, control_col3 = st.columns(3)
        with control_col1:
            top_k = st.slider("top_k", min_value=1, max_value=10, value=5)
        with control_col2:
            threshold_enabled = st.checkbox("Use threshold")
        with control_col3:
            threshold = st.slider("threshold", min_value=0.0, max_value=1.0, value=0.75, step=0.01)

        if st.button("Compare 3 Strategies", type="primary", use_container_width=True):
            if not query.strip():
                st.warning("Please input query text.")
                return
            results_by_strategy: dict[str, dict] = {}
            for strategy in STRATEGIES:
                try:
                    results_by_strategy[strategy] = run_query(
                        api_base=api_base,
                        strategy=strategy,
                        query=query,
                        top_k=top_k,
                        threshold_enabled=threshold_enabled,
                        threshold=threshold,
                        doc_id=doc_id,
                    )
                except requests.RequestException as exc:
                    st.error(f"{strategy} query failed: {exc}")
                    return

            col_fixed, col_overlap, col_semantic = st.columns(3)
            with col_fixed:
                render_strategy_result("fixed", results_by_strategy["fixed"])
            with col_overlap:
                render_strategy_result("overlap", results_by_strategy["overlap"])
            with col_semantic:
                render_strategy_result("semantic", results_by_strategy["semantic"])

    with tab_browse:
        st.subheader("Search chunk objects by type")
        browse_col1, browse_col2 = st.columns(2)
        with browse_col1:
            browse_strategy = st.selectbox("strategy", STRATEGIES, key="browse_strategy")
            peek_limit = st.slider("load chunks", min_value=10, max_value=200, value=50, step=10)
        with browse_col2:
            chunk_type = st.selectbox(
                "chunk_type",
                ["all", "heading", "paragraph", "list_item", "table"],
                key="browse_chunk_type",
            )
            keyword = st.text_input("keyword in text (optional)", key="browse_keyword")

        if st.button("Load Chunks", use_container_width=True):
            try:
                data = fetch_peek_data(api_base=api_base, strategy=browse_strategy, limit=peek_limit)
            except requests.RequestException as exc:
                st.error(f"Load chunks failed: {exc}")
                return

            rows = []
            items = data.get("items", []) or []
            if items:
                for item in items:
                    meta = item.get("metadata", {}) or {}
                    rows.append(
                        {
                            "chunk_id": str(item.get("id", "")),
                            "text": str(item.get("document", "")),
                            "metadata": meta,
                            "block_type": str(meta.get("block_type", "")),
                        }
                    )
            else:
                # Backward compatibility for old peek response format.
                ids = data.get("ids", []) or []
                docs = data.get("documents", []) or []
                metas = data.get("metadatas", []) or []
                for idx, chunk_id in enumerate(ids):
                    text = docs[idx] if idx < len(docs) else ""
                    meta = metas[idx] if idx < len(metas) and metas[idx] else {}
                    rows.append(
                        {
                            "chunk_id": chunk_id,
                            "text": text,
                            "metadata": meta,
                            "block_type": str(meta.get("block_type", "")),
                        }
                    )

            if chunk_type != "all":
                rows = [r for r in rows if r["block_type"] == chunk_type]
            if keyword.strip():
                lower_kw = keyword.strip().lower()
                rows = [r for r in rows if lower_kw in r["text"].lower()]

            st.success(f"Found {len(rows)} chunks")
            for row in rows:
                meta = row["metadata"]
                st.markdown(
                    f"**{row['chunk_id']}** | "
                    f"type: `{row['block_type'] or 'unknown'}` | "
                    f"heading: `{meta.get('heading_path', '')}`"
                )
                st.code(row["text"], language="text")
                st.divider()


if __name__ == "__main__":
    main()
