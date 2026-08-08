#  To-Do
+ add a tag;
+ update existing project:
    + replace exception handlers with an error middleware;
    + refactor ElasticService and move out documents functionality;
    + move search endpoint into documents' router;

+ add Elastic migrations definition (move out of service);

+ full-text search on another dataset:
    + `blogposts` dataset and index:
        + several indexed fields (title, text, tags, timestamp);
        + models and ES migration;
        + data generation script (with Faker);
        + ingestion script;

    + skip creating a DB session for `blogposts`;
    + skip creating a mock DB in `blogposts` tests;

    + add endpoints for blogposts:
        + create;
        + read;
        + update:
            + partial;
            x optimistic (if_seq_no + if_primary_term);     // does not add any protection when running multiple update statements (main index + text chunks with vector fields)
        + delete;

        + full-text search:
            + search by multiple fields;
                + case insensitive;     // default analyzer provides case insensitivity
                x use different rules;
                x use a more specific set of analyzers;
            + filter by time;
            + order by time desc;
            + limit + pagination;

        + prefix search on tags:
            + add search_as_you_type mapping on tags;
            + implement search:
                + normalize query (replace word separators in query with underscores, remove non-alphanum chars);
                + implement prefix search which returns unique tags matching the query;

    + test ES setup:
        + add test curl commands for blogposts routes;
        + save generated blogposts to json;
        + migration upgrade & data deletion;
        + documents ingestion;
        + blogposts ingestion;

+ aggregations:
    // https://www.elastic.co/docs/explore-analyze/query-filter/aggregations/tutorial-analyze-ecommerce-data-with-aggregations-using-query-dsl
    + sales dataset:
        + date, region, product, units_sold, price, revenue;
        + models;
        + service and migration script;
        + ingestion script;

    + route handlers which return aggregated data:
        + total sales by month and region;     // with filters for min and max dates, product and region
        + top n products by revenue grouped by region;    // nested aggregation; allow period and region filters
        + group sales by units_sold intervals of 10 (1-10, 11-20, ...) and calculate revenue; allow period, region and product filters

- vector search:
    + architecture:
        x nested dense_vector; // not implemented in ES 7.17
        + two indices:
            + blogposts (existing + title_vector: dense_vector, 768, cosine);
            + blogposts_text_chunks (new, each doc = one text chunk):
                + fields: blogpost_id, chunk_index, chunk_text, chunk_vector;
            + chunk collapse at search: max score per blogpost_id;
            + fusion:
                + linear score combination (α·title_knn + β·max_chunk_score [+ γ·bm25]);
                x RRF;  // not implemented in ES 7.17
        
    + embedding approach:
        + Ollama container with an embedding model, chunking is done on the side of main service;
        x separate HTTP service (FastAPI + Semantic Transformers, handles both chunking and embedding);
        x other;
    
    + update config:
        + add ollama_host, ollama_port, ollama_model to Config + .env;  // also network and batch settings
    
    + add Ollama container:
        + model nomic-embed-text, host and port from config, volume for model cache;
        + additional options;   // use CPU, 2 cores max, limit cache size
        + pin container and model versions;

    + embedding function:
        + BlogpostsEmbeddings.get_embeddings():
            + accepts `blogpost_id`, `title` and `text` (both optional);
            + gets embedding for `title`, if provided (separate request);
            + chunks `text` via RecursiveCharacterTextSplitter (langchain-text-splitters):
                + splits into chunks with 512 tokens size + 52 tokens overlap;
                + uses tokenizer to evalute chunk size;
                + returns a list of Pydantic models which can be dumped into a new index;
                + requests embeddings for chunks in batches of up to 10, sequentially;
            + returns None for omitted args;
    
    + integrate embedding processing, pt. 1:
        + index_blogposts:
            + each post gets embeddings before async_bulk;
            + insert into 2 indices;
    
    + migration script (r_0005_blogpost_vectors):
        + upgrade:
            x create blogposts_v3 with title_vector field (dense_vector, 384, cosine, hnsw);    // explore other possible settings before implementing
            + create blogposts_v3 with title_vector field;  // dense_vector, 384 dims, hnsw & metrics are not present in ES 7
            + reindex _v2 → _v3 (existing data without vectors);
            + swap alias, delete _v2;
            + create blogpost_chunks index (blogpost_id, chunk_idx, chunk_text, chunk_vector);
            + for existing posts:
                + generate embeddings;
                + update title_vector;
                + index chunks;
                
        + downgrade:
            + reindex _v3 → _v2 (vectors are lost), swap alias, delete _v3 and blogpost_chunks;
    
    + integrate embedding processing, pt. 2:
        + error middleware:
            + network errors when calling embedding model → 503;
            + explore Ollama SDK to decide which error to catch in middleware + Ollama's or custom app-level exception;     // app-level

        + CRUD integration:
            + create:
                + embeddings generated before indexing;
                + insert into 2 indices;
            + update:
                - embeddings recomputed only for fields present in PATCH body;
                + update title_vector, if `title` is modified;
                + delete + insert new chunks, if `text` is modified;
            + delete:
                + delete from both indices;

    - ingest_blogposts.py:
        - check if reducing default post count and text size is needed;
    
    - print current progress in migration and ingestion scripts;

    - new endpoints (no min_time/max_time/tags filters):
        - GET /blogposts/vector_search?q=...;  // ANN + chunk collapse + linear fusion
        - GET /blogposts/hybrid_search?q=...;  // same + BM25 multi_match   // TODO specify FTS + vector fusion logic

    - tests:
        - update config tests;
        - mock embeddings via random vectors for existing tests;
        - migration tests;
        - new route handler tests;
        - functional tests for getting embeddings and handling Ollama network errors;
        ? search quality tests;
    
    ? update README.md with info on when embedding container is required;

? geospatial data;



# Tutorial Plan
- Connection & Index Management:
    Before searching, you must understand how to connect securely and define how data is structured.
    - Secure Client Initialization: Connect using API keys or Basic Authentication, and handle SSL certificates.
    - Explicit Mapping Definition: Create an index with predefined field types (e.g., text for full-text search, keyword for exact filtering, date, and integer).

- Document Lifecycle (CRUD):
    Learn how Elasticsearch handles data ingestion and updates, which differs significantly from traditional SQL databases.
    - Bulk Ingestion: Use helpers.bulk() to efficiently index multiple documents at once instead of making individual API calls.
    - Optimistic Concurrency Control: Practice updating a document using if_seq_no and if_primary_term to prevent overwrite conflicts.
    - Partial Updates: Use the update API to change a single field without re-indexing the entire document.

- Advanced Text Search:
    This is the core strength of Elasticsearch. Cover the exact ways users expect a search bar to behave.
    - Full-Text vs. Exact Match: Compare a match query (tokenized, case-insensitive) against a term query (exact match for IDs or categories).
    - Multi-Field Boosting: Search across titles and descriptions simultaneously using multi_match, giving higher weight (^3) to title matches.
    - Fuzzy & Proximity Searching: Handle typos using fuzziness="AUTO" and find matching phrases even if words are slightly out of order.

- Filtering, Aggregations, & Pagination:
    Search is rarely just a text query; users need to drill down into results.
    - The bool Query: Combine full-text search with strict filters (e.g., "Status must be Active" and "Price must be under $50") using must, should, and filter clauses.
    - Metric & Bucket Aggregations: Generate dynamic sidebar facets (like counting how many items exist per category) and calculate averages (like average price).
    - Search After Pagination: Implement safe, scalable pagination using the search_after parameter instead of deep paging with from and size.

- Hybrid & Vector Search (Modern AI Search):
    Modern applications combine traditional text search with AI-powered semantic understanding.
    - Dense Vector Embeddings: Add a dense_vector field to your mapping to store text embeddings (generated via libraries like SentenceTransformers).
    - k-Nearest Neighbor (kNN) Search: Execute a semantic search to find conceptually similar documents, even if they share zero exact keywords with the query.
    - Reciprocal Rank Fusion (RRF): Combine lexical (BM25) text scores and vector similarity scores into a single, optimized hybrid search result.
