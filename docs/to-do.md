+ repo setup & dependencies;

+ app + db setup:
    + project config;

    + db setup;
        + container;
        + db setup;
        + db model; // select correct data types
        + migration;
        + data injection script;
        
    + app:
        + validators;
        + route handlers;
        + db repository;
        + app setup;
        + elastic service stub;
    
    + tests:
        + fixtures & helpers:
            + test db + migrations;
            + data generator + db operations;
            + elastic service mock;
            + app / test client;
        + test cases:
            + config validation;
            + db tests; // migration ladder, required tables exist after a migration
            + app routes tests:     // app + db interaction, elastic is mocked
                + search endpoint;
                + delete endpoint;


- elastic:
    + container; // configure elastic & update project config
    - index creation:
        ? dynamic: strict;
        ? number of shards / replicas
    - data injection script;
    - implement elastic service;

    - tests:
        - elastic service tests:
            - search;
            - delete;
        - app routes handle elastic errors gracefully;


? dev container & volume names
- change port numbers;
- deployment with Docker Compose;

- readme & API schema:
    - list decisions made:
        - search path: api -> elastic (for matching indices) -> api -> postgres (for 20 rows with full data);
        - matching rows are sorted by date DESC;
        - created_at is converted to UTC;
        - rubrics type is TEXT[];
        - /search endpoint:
            - accepts a query as URL param;
            ? finds exact match;
