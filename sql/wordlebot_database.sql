USE wordlebot;

CREATE TABLE user_data (
    user_id BIGINT PRIMARY KEY,
    user_name VARCHAR(32) NOT NULL,
    avatar VARCHAR(255) NOT NULL
);

CREATE TABLE server_data (
    server_id BIGINT PRIMARY KEY,
    prefix VARCHAR(5) DEFAULT '!',
    wordle_channel_id BIGINT
);

CREATE TABLE server_membership (
    user_id BIGINT NOT NULL,
    server_id BIGINT NOT NULL,
    display_name VARCHAR(32) NOT NULL,
    PRIMARY KEY(user_id, server_id),
    FOREIGN KEY(user_id) REFERENCES user_data(user_id),
    FOREIGN KEY(server_id) REFERENCES server_data(server_id)
);

CREATE TABLE wordle_data (
    user_id BIGINT NOT NULL,
    wordle_id VARCHAR(100) NOT NULL,
    wordle_score VARCHAR(1) NOT NULL,
    wordle_grid VARCHAR(35) NOT NULL,
    wordle_date DATE NOT NULL,
    PRIMARY KEY(user_id, wordle_id),
    FOREIGN KEY(user_id) REFERENCES user_data(user_id)
);

CREATE TABLE wordle_server_membership (
    user_id BIGINT NOT NULL,
    server_id BIGINT NOT NULL,
    wordle_id VARCHAR(100) NOT NULL,
    PRIMARY KEY(user_id, server_id, wordle_id),
    FOREIGN KEY(user_id) REFERENCES user_data(user_id),
    FOREIGN KEY(server_id) REFERENCES server_data(server_id),
    FOREIGN KEY(user_id, wordle_id) REFERENCES wordle_data(user_id, wordle_id)
);
