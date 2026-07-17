CREATE DATABASE IF NOT EXISTS complaint_management;

USE complaint_management;

DROP TABLE IF EXISTS users;

CREATE TABLE users(
id INT AUTO_INCREMENT PRIMARY KEY,
name VARCHAR(100),
email VARCHAR(100) UNIQUE,
mobile VARCHAR(15),
password VARCHAR(255),
role ENUM('user','admin') DEFAULT 'user'
);


DROP TABLE IF EXISTS complaints;

CREATE TABLE complaints(
complaint_id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT,
title VARCHAR(150),
category VARCHAR(100),
description TEXT,
priority ENUM('Low','Medium','High','Critical'),
image VARCHAR(255),
status ENUM(
'Pending',
'In Progress',
'Resolved',
'Rejected'
) DEFAULT 'Pending',
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY(user_id)
REFERENCES users(id)
);

