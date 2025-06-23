-- scripts/make_regional_views.sql
CREATE OR REPLACE VIEW `fieldsense-optimizer.asco_ml.commodity_prices_all` AS
SELECT * FROM `fieldsense-optimizer.asco_core.commodity_prices_all`;

CREATE OR REPLACE VIEW `fieldsense-optimizer.asco_ml.crude_oil_prices` AS
SELECT * FROM `fieldsense-optimizer.asco_core.crude_oil_prices`;

CREATE OR REPLACE VIEW `fieldsense-optimizer.asco_ml.precip_africa` AS
SELECT * FROM `fieldsense-optimizer.asco_core.precip_africa`;

CREATE OR REPLACE VIEW `fieldsense-optimizer.asco_ml.soil_moist_africa` AS
SELECT * FROM `fieldsense-optimizer.asco_core.soil_moist_africa`;

CREATE OR REPLACE VIEW `fieldsense-optimizer.asco_ml.temp_max_africa` AS
SELECT * FROM `fieldsense-optimizer.asco_core.temp_max_africa`;

CREATE OR REPLACE VIEW `fieldsense-optimizer.asco_ml.acled_events_geo` AS
SELECT * FROM `fieldsense-optimizer.asco_core.acled_events_geo`;

CREATE OR REPLACE VIEW `fieldsense-optimizer.asco_ml.gadm_lvl2_raw` AS
SELECT * FROM `fieldsense-optimizer.asco_core.gadm_lvl2_raw`;