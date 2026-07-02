+ repo setup & dependencies;

- app + db setup:
    - project config;
    - db setup;
        - container;
        - db model; // select correct data types
        - migration;
        - data injection script;
        
    - app:
        - validators;
        - route handlers;
        - db repository;
        - app setup;
        - elastic service stub;
    
    - tests:
        - config validation;
        - db tests:
            - migration ladder;
        - fixtures:
            - test db + migrations;
            - data generator + db operations;
            - elastic service mock;
            - app / test client;
        - app routes tests:     // app + db interaction, elastic is mocked
            - search endpoint;
            - delete endpoint;

- elastic:
    - container;
    - index creation;
    - data injection script;
    - implement elastic service;

    - tests:
        - elastic service tests:
            - search;
            - delete;
        - app routes handle elastic errors gracefully;

- deployment with Docker Compose;

- readme & API schema:
    - list decisions made:
        - search path: api -> elastic (for matching indices) -> api -> postgres (for 20 rows with full data);
        - matching rows are sorted by date DESC;
