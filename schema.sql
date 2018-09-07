CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(100) NOT NULL,
    level INTEGER NOT NULL
    -- 0: superuser
    -- 1: user
);