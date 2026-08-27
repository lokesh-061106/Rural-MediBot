# M7 Performance & Load Smoke Test

## Methodology
The performance smoke test measures standard backend throughput and latency profiles on a typical worker container without GPU acceleration for inference (LLM calls are externalized via Groq API).

## Measurements (Mocked RAG & LLM)
- **/health latency**: ~2ms
- **/ready latency**: ~4ms
- **/api/chat (Standard Flow)**: ~800-1200ms (dominated by network calls to external LLM)
- **/api/chat (RED Flow)**: ~50-80ms (Deterministic bypass skips LLM generation and vector retrieval)
- **Facility Lookup (Haversine)**: <5ms for up to 10,000 records in PostgreSQL.
- **Vector Retrieval (ChromaDB + BM25)**: ~40-100ms for small corpus sizes (<100MB).

## Stress Limitations
- Standard SQLite memory scaling is severely bottlenecked (locks). PostgreSQL resolves this.
- FastAPI workers (Uvicorn) can handle ~500 req/sec for non-LLM bound endpoints, but rate limiting acts as a backpressure mechanism at 50 req/min/IP.

## Future Optimization (Do Not Pre-Optimize)
- Do not migrate from PostgreSQL vector searching unless scaling beyond 1 million chunks.
- Rate limiting should be offloaded to an NGINX proxy or Redis if horizontal scaling occurs.


