# Basic Plan
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



#  To-Do
+ add a tag;
+ update existing project:
    + replace exception handlers with an error middleware;
    + refactor ElasticService and move out documents functionality;
    + move search endpoint into documents' router;

+ add Elastic migrations definition (move out of service);

- full-text search on another dataset:    
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
            + optimistic (if_seq_no + if_primary_term);
        + delete;
        
        + full-text search:
            + search by multiple fields;
                + case insensitive;     // default analyzer provides case insensivity
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
    
    - test ES setup:
        - migration upgrade & data deletion;
        - documents ingestion;
        - blogposts ingestiong;
        - add test curl commands for blogposts routes;

- aggregations:
    - add a dataset with metrics and dimensions to filter on;
    - see above
    // https://www.elastic.co/docs/explore-analyze/query-filter/aggregations/tutorial-analyze-ecommerce-data-with-aggregations-using-query-dsl
    ? bool query (`must` + `should` + ???);
    ???

- vector search:
    - see above;
        ? update blogposts index with vector mapping(-s) without recreating index;
        ? hybrid search;
        - ingest data;
        - search data;
        
    
? geospatial data;
