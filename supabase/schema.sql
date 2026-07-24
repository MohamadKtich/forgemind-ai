-- ForgeMind AI PostgreSQL schema
-- Generated from SQLAlchemy models. Review before production use.


CREATE TABLE factories (
	id SERIAL NOT NULL,
	name VARCHAR(120) NOT NULL,
	location VARCHAR(180) NOT NULL,
	timezone VARCHAR(80) NOT NULL,
	target_oee FLOAT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
)

;


CREATE TABLE integration_logs (
	id SERIAL NOT NULL,
	source VARCHAR(80) NOT NULL,
	event_type VARCHAR(80) NOT NULL,
	payload JSON NOT NULL,
	success BOOLEAN NOT NULL,
	message TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
)

;


CREATE TABLE users (
	id SERIAL NOT NULL,
	full_name VARCHAR(120) NOT NULL,
	email VARCHAR(180) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	role VARCHAR(40) NOT NULL,
	active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	last_login_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id)
)

;


CREATE TABLE app_settings (
	id SERIAL NOT NULL,
	key VARCHAR(100) NOT NULL,
	value JSON NOT NULL,
	description VARCHAR(255) NOT NULL,
	updated_by INTEGER,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_app_setting_key UNIQUE (key),
	FOREIGN KEY(updated_by) REFERENCES users (id)
)

;


CREATE TABLE assistant_conversations (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	title VARCHAR(180) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;


CREATE TABLE machines (
	id SERIAL NOT NULL,
	factory_id INTEGER NOT NULL,
	code VARCHAR(32) NOT NULL,
	name VARCHAR(120) NOT NULL,
	machine_type VARCHAR(80) NOT NULL,
	manufacturer VARCHAR(100) NOT NULL,
	model_number VARCHAR(100) NOT NULL,
	line_name VARCHAR(100) NOT NULL,
	status VARCHAR(32) NOT NULL,
	age_years FLOAT NOT NULL,
	operating_hours FLOAT NOT NULL,
	tool_wear FLOAT NOT NULL,
	rated_power_kw FLOAT NOT NULL,
	installation_date VARCHAR(20) NOT NULL,
	notes TEXT NOT NULL,
	archived BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(factory_id) REFERENCES factories (id)
)

;


CREATE TABLE production_records (
	id SERIAL NOT NULL,
	factory_id INTEGER NOT NULL,
	line_name VARCHAR(100) NOT NULL,
	product_name VARCHAR(120) NOT NULL,
	planned INTEGER NOT NULL,
	produced INTEGER NOT NULL,
	rejected INTEGER NOT NULL,
	downtime_minutes FLOAT NOT NULL,
	runtime_minutes FLOAT NOT NULL,
	ideal_cycle_seconds FLOAT NOT NULL,
	shift VARCHAR(24) NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(factory_id) REFERENCES factories (id)
)

;


CREATE TABLE reports (
	id SERIAL NOT NULL,
	report_type VARCHAR(60) NOT NULL,
	title VARCHAR(180) NOT NULL,
	file_path VARCHAR(255) NOT NULL,
	period_start VARCHAR(40) NOT NULL,
	period_end VARCHAR(40) NOT NULL,
	generated_by INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(generated_by) REFERENCES users (id)
)

;


CREATE TABLE alerts (
	id SERIAL NOT NULL,
	machine_id INTEGER,
	category VARCHAR(40) NOT NULL,
	severity VARCHAR(24) NOT NULL,
	title VARCHAR(160) NOT NULL,
	message TEXT NOT NULL,
	acknowledged BOOLEAN NOT NULL,
	acknowledged_by INTEGER,
	acknowledged_at TIMESTAMP WITH TIME ZONE,
	read BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(machine_id) REFERENCES machines (id),
	FOREIGN KEY(acknowledged_by) REFERENCES users (id)
)

;


CREATE TABLE assistant_messages (
	id SERIAL NOT NULL,
	conversation_id INTEGER NOT NULL,
	role VARCHAR(20) NOT NULL,
	content TEXT NOT NULL,
	evidence JSON NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(conversation_id) REFERENCES assistant_conversations (id)
)

;


CREATE TABLE device_commands (
	id SERIAL NOT NULL,
	machine_id INTEGER NOT NULL,
	command VARCHAR(80) NOT NULL,
	status VARCHAR(24) NOT NULL,
	payload JSON NOT NULL,
	response JSON NOT NULL,
	issued_by INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(machine_id) REFERENCES machines (id),
	FOREIGN KEY(issued_by) REFERENCES users (id)
)

;


CREATE TABLE inspections (
	id SERIAL NOT NULL,
	machine_id INTEGER,
	product_name VARCHAR(120) NOT NULL,
	batch_code VARCHAR(80) NOT NULL,
	inspection_mode VARCHAR(40) NOT NULL,
	status VARCHAR(24) NOT NULL,
	confidence FLOAT NOT NULL,
	anomaly_score FLOAT NOT NULL,
	defect_types JSON NOT NULL,
	bounding_boxes JSON NOT NULL,
	measurements JSON NOT NULL,
	original_path VARCHAR(255) NOT NULL,
	reference_path VARCHAR(255),
	annotated_path VARCHAR(255) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(machine_id) REFERENCES machines (id)
)

;


CREATE TABLE maintenance_records (
	id SERIAL NOT NULL,
	machine_id INTEGER NOT NULL,
	title VARCHAR(160) NOT NULL,
	action VARCHAR(220) NOT NULL,
	priority VARCHAR(24) NOT NULL,
	status VARCHAR(24) NOT NULL,
	assigned_to VARCHAR(120) NOT NULL,
	scheduled_for VARCHAR(40) NOT NULL,
	cost_estimate FLOAT NOT NULL,
	notes TEXT NOT NULL,
	created_by INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	completed_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(machine_id) REFERENCES machines (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
)

;


CREATE TABLE sensor_readings (
	id SERIAL NOT NULL,
	machine_id INTEGER NOT NULL,
	temperature FLOAT NOT NULL,
	vibration FLOAT NOT NULL,
	pressure FLOAT NOT NULL,
	rpm FLOAT NOT NULL,
	torque FLOAT NOT NULL,
	power FLOAT NOT NULL,
	operating_hours FLOAT NOT NULL,
	tool_wear FLOAT NOT NULL,
	source VARCHAR(40) NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(machine_id) REFERENCES machines (id)
)

;


CREATE TABLE machine_predictions (
	id SERIAL NOT NULL,
	machine_id INTEGER NOT NULL,
	reading_id INTEGER,
	health_score FLOAT NOT NULL,
	failure_probability FLOAT NOT NULL,
	anomaly_score FLOAT NOT NULL,
	remaining_useful_hours FLOAT,
	risk_level VARCHAR(24) NOT NULL,
	likely_issue VARCHAR(120) NOT NULL,
	recommendation TEXT NOT NULL,
	maintenance_priority VARCHAR(24) NOT NULL,
	explanation JSON NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(machine_id) REFERENCES machines (id),
	FOREIGN KEY(reading_id) REFERENCES sensor_readings (id)
)

;

CREATE UNIQUE INDEX ix_factories_name ON factories (name);

CREATE INDEX ix_integration_logs_event_type ON integration_logs (event_type);

CREATE INDEX ix_integration_logs_created_at ON integration_logs (created_at);

CREATE INDEX ix_integration_logs_source ON integration_logs (source);

CREATE INDEX ix_integration_logs_success ON integration_logs (success);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE INDEX ix_users_role ON users (role);

CREATE INDEX ix_users_active ON users (active);

CREATE UNIQUE INDEX ix_app_settings_key ON app_settings (key);

CREATE INDEX ix_assistant_conversations_user_id ON assistant_conversations (user_id);

CREATE UNIQUE INDEX ix_machines_code ON machines (code);

CREATE INDEX ix_machines_factory_id ON machines (factory_id);

CREATE INDEX ix_machines_status ON machines (status);

CREATE INDEX ix_machines_archived ON machines (archived);

CREATE INDEX ix_production_records_factory_id ON production_records (factory_id);

CREATE INDEX ix_production_records_recorded_at ON production_records (recorded_at);

CREATE INDEX ix_reports_created_at ON reports (created_at);

CREATE INDEX ix_reports_report_type ON reports (report_type);

CREATE INDEX ix_alerts_severity ON alerts (severity);

CREATE INDEX ix_alerts_acknowledged ON alerts (acknowledged);

CREATE INDEX ix_alerts_created_at ON alerts (created_at);

CREATE INDEX ix_alerts_machine_id ON alerts (machine_id);

CREATE INDEX ix_alerts_read ON alerts (read);

CREATE INDEX ix_assistant_messages_conversation_id ON assistant_messages (conversation_id);

CREATE INDEX ix_device_commands_machine_id ON device_commands (machine_id);

CREATE INDEX ix_device_commands_status ON device_commands (status);

CREATE INDEX ix_inspections_created_at ON inspections (created_at);

CREATE INDEX ix_inspections_status ON inspections (status);

CREATE INDEX ix_inspections_machine_id ON inspections (machine_id);

CREATE INDEX ix_maintenance_records_status ON maintenance_records (status);

CREATE INDEX ix_maintenance_records_priority ON maintenance_records (priority);

CREATE INDEX ix_maintenance_records_machine_id ON maintenance_records (machine_id);

CREATE INDEX ix_sensor_readings_recorded_at ON sensor_readings (recorded_at);

CREATE INDEX ix_sensor_readings_machine_id ON sensor_readings (machine_id);

CREATE INDEX ix_machine_predictions_machine_id ON machine_predictions (machine_id);

CREATE INDEX ix_machine_predictions_created_at ON machine_predictions (created_at);

CREATE INDEX ix_machine_predictions_risk_level ON machine_predictions (risk_level);
