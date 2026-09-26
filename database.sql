CREATE DATABASE IF NOT EXISTS robofleet;
USE robofleet;

CREATE TABLE IF NOT EXISTS robots (
    robot_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    location VARCHAR(50) DEFAULT 'A1',
    battery INT DEFAULT 100,
    status VARCHAR(20) DEFAULT 'Available',
    health_score INT DEFAULT 100,
    current_task_id INT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id INT AUTO_INCREMENT PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,
    source VARCHAR(50),
    destination VARCHAR(50),
    priority INT DEFAULT 3,
    deadline INT DEFAULT 60,
    status VARCHAR(20) DEFAULT 'Pending',
    assigned_robot INT NULL
);

CREATE TABLE IF NOT EXISTS resources (
    resource_id INT AUTO_INCREMENT PRIMARY KEY,
    resource_name VARCHAR(50) UNIQUE NOT NULL,
    occupied_by INT NULL,
    status VARCHAR(20) DEFAULT 'Free'
);

CREATE TABLE IF NOT EXISTS task_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT,
    robot_id INT,
    action VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS failures (
    failure_id INT AUTO_INCREMENT PRIMARY KEY,
    robot_id INT,
    reason VARCHAR(100),
    recovered_task INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO resources(resource_name) VALUES
('Charging Station 1'),
('Warehouse Gate'),
('Loading Dock');

INSERT INTO robots(name, location, battery, status, health_score)
SELECT 'Robot-1','A1',90,'Available',95
WHERE NOT EXISTS (SELECT 1 FROM robots WHERE name='Robot-1');

INSERT INTO robots(name, location, battery, status, health_score)
SELECT 'Robot-2','B2',65,'Available',88
WHERE NOT EXISTS (SELECT 1 FROM robots WHERE name='Robot-2');

INSERT INTO robots(name, location, battery, status, health_score)
SELECT 'Robot-3','C3',40,'Available',72
WHERE NOT EXISTS (SELECT 1 FROM robots WHERE name='Robot-3');
