USE DATABASE TFS_NEXT_MOVE;
USE SCHEMA CORE;

-- Replace the earlier fixture with exactly three Guardian personas.
DELETE FROM SERVICE_HISTORY WHERE VEHICLE_ID IN (
  'vehicle-001', 'guardian-camry-alex', 'guardian-camry-covered', 'guardian-camry-limited'
);
DELETE FROM CONTRACT WHERE PROFILE_ID IN ('rav4-lease-001', 'alex', 'covered', 'limited');
DELETE FROM VEHICLE WHERE PROFILE_ID IN ('rav4-lease-001', 'alex', 'covered', 'limited');
DELETE FROM MOBILITY_PREFERENCE WHERE PROFILE_ID IN ('rav4-lease-001', 'alex', 'covered', 'limited');
DELETE FROM CUSTOMER WHERE PROFILE_ID IN ('rav4-lease-001', 'alex', 'covered', 'limited');
DELETE FROM VEHICLE_TELEMETRY WHERE VEHICLE_ID IN (
  'guardian-camry-alex', 'guardian-camry-covered', 'guardian-camry-limited'
);

INSERT INTO CUSTOMER (
  PROFILE_ID, REGION, BUDGET_MONTHLY, CASH_RESERVE, SIMULATED, FIRST_NAME, INITIALS,
  PROFILE_LABEL, SERVICE_COVERAGE_LIMIT, PROTECTED_CASH_RESERVE
) VALUES
  ('alex','Austin, TX',550,7000,TRUE,'Alex Morgan','AM','Alex · no coverage',0,2000),
  ('covered','Austin, TX',550,7000,TRUE,'Jordan Lee','JL','Jordan · $1,000 coverage',1000,2000),
  ('limited','Austin, TX',550,2800,TRUE,'Sam Rivera','SR','Sam · limited cash',0,2000);

INSERT INTO VEHICLE (VEHICLE_ID,PROFILE_ID,MODEL_YEAR,MAKE,MODEL,TRIM,CURRENT_MILEAGE) VALUES
  ('guardian-camry-alex','alex',2018,'Toyota','Camry','SE',78000),
  ('guardian-camry-covered','covered',2019,'Toyota','Camry','LE',69000),
  ('guardian-camry-limited','limited',2017,'Toyota','Camry','XLE',92000);

INSERT INTO CONTRACT (
  CONTRACT_ID,PROFILE_ID,VEHICLE_ID,CONTRACT_TYPE,MONTHLY_PAYMENT,PAYOFF_AMOUNT,CONTRACT_VERSION
) VALUES
  ('guardian-contract-alex','alex','guardian-camry-alex','CASH',0,0,'guardian-synthetic-v1'),
  ('guardian-contract-covered','covered','guardian-camry-covered','CASH',0,0,'guardian-synthetic-v1'),
  ('guardian-contract-limited','limited','guardian-camry-limited','CASH',0,0,'guardian-synthetic-v1');

INSERT INTO SERVICE_HISTORY (SERVICE_ID,VEHICLE_ID,SERVICE_DATE,MILEAGE,SERVICE_TYPE,COST,NOTES) VALUES
  ('guardian-service-alex-1','guardian-camry-alex','2026-08-15',76500,'Inspection',0,'Brake service recommended; synthetic record.'),
  ('guardian-service-covered-1','guardian-camry-covered','2026-09-02',68400,'Diagnostic',125,'Repair eligible for $1,000 synthetic coverage.'),
  ('guardian-service-limited-1','guardian-camry-limited','2026-07-20',90800,'Inspection',0,'Brake and tire work recommended; synthetic record.');

INSERT INTO VEHICLE_TELEMETRY (
  VEHICLE_ID, CAPTURED_AT, ODOMETER_MILES, TIRE_PRESSURE_PSI, BATTERY_TYPE,
  BATTERY_HEALTH_PERCENT, BATTERY_VOLTAGE, STATE_OF_CHARGE_PERCENT,
  ESTIMATED_RANGE_MILES, EQUIVALENT_FULL_CYCLES, SIMULATED
) SELECT column1, column2::TIMESTAMP_TZ, column3, PARSE_JSON(column4), column5,
         column6, column7, column8, column9, column10, TRUE
FROM VALUES
  ('guardian-camry-alex','2026-10-25 09:15:00 -0500',78000,'{"front_left":34,"front_right":34,"rear_left":33,"rear_right":33}','12V',82,12.5,NULL,NULL,NULL),
  ('guardian-camry-covered','2026-10-25 09:17:00 -0500',69000,'{"front_left":35,"front_right":35,"rear_left":34,"rear_right":34}','12V',91,12.7,NULL,NULL,NULL),
  ('guardian-camry-limited','2026-10-25 09:20:00 -0500',92000,'{"front_left":31,"front_right":33,"rear_left":32,"rear_right":32}','12V',68,12.2,NULL,NULL,NULL);

SELECT c.PROFILE_ID, c.FIRST_NAME, c.PROFILE_LABEL, c.SERVICE_COVERAGE_LIMIT,
       c.CASH_RESERVE, c.PROTECTED_CASH_RESERVE, v.MODEL_YEAR, v.MODEL,
       COUNT(sh.SERVICE_ID) AS SERVICE_EVENTS
FROM CUSTOMER c
JOIN VEHICLE v USING (PROFILE_ID)
LEFT JOIN SERVICE_HISTORY sh USING (VEHICLE_ID)
WHERE c.PROFILE_ID IN ('alex', 'covered', 'limited')
GROUP BY ALL ORDER BY c.PROFILE_ID;
