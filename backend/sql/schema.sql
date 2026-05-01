-- MySQL 8 schema for HCP CRM persistence.
CREATE DATABASE IF NOT EXISTS hcp_crm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hcp_crm;

CREATE TABLE IF NOT EXISTS interaction (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    public_id VARCHAR(64) NOT NULL UNIQUE,
    rep_id VARCHAR(100) NOT NULL,
    hcp_external_id VARCHAR(100) NULL,
    hcp_name VARCHAR(255) NULL,
    interaction_type VARCHAR(32) NOT NULL,
    occurred_at DATETIME NULL,
    sentiment VARCHAR(20) NOT NULL DEFAULT 'neutral',
    summary TEXT NULL,
    topics_discussed TEXT NULL,
    outcomes TEXT NULL,
    follow_up_actions TEXT NULL,
    ai_suggested_follow_ups JSON NULL,
    chat_transcript JSON NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'logged',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_interaction_rep_time (rep_id, occurred_at)
);

CREATE TABLE IF NOT EXISTS interaction_attendee (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    interaction_id BIGINT NOT NULL,
    attendee_name VARCHAR(255) NOT NULL,
    CONSTRAINT fk_attendee_interaction
        FOREIGN KEY (interaction_id) REFERENCES interaction(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interaction_material (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    interaction_id BIGINT NOT NULL,
    catalog_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    CONSTRAINT fk_material_interaction
        FOREIGN KEY (interaction_id) REFERENCES interaction(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interaction_sample (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    interaction_id BIGINT NOT NULL,
    sku VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    CONSTRAINT fk_sample_interaction
        FOREIGN KEY (interaction_id) REFERENCES interaction(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interaction_revision (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    interaction_id BIGINT NOT NULL,
    revision_no INT NOT NULL,
    changed_by VARCHAR(100) NOT NULL,
    change_reason TEXT NULL,
    diff_json JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_revision (interaction_id, revision_no),
    CONSTRAINT fk_revision_interaction
        FOREIGN KEY (interaction_id) REFERENCES interaction(id) ON DELETE CASCADE
);
