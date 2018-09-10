CREATE TABLE warnings (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    intime VARCHAR NOT NULL,
    outtime VARCHAR NOT NULL,
    image VARCHAR NOT NULL
);