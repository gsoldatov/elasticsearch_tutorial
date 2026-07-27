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


+ elastic:
    + container; // configure elastic & update project config
    + index creation; // dynamic: strict; number of replicas
    + data injection script;
    - implement elastic service;

    + tests:
        + elastic service tests:
            + main operations (search, delete);
            + index management (create, delete, index docs)
        + app routes handle elastic errors gracefully;

+ run app in Docker;

+ readme & API schema;