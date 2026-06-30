-- Initialises all databases required by the NutraTenant platform.
-- Executed once by the postgres container on first boot.

SELECT 'CREATE DATABASE nutratenant_tenant'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nutratenant_tenant')\gexec

SELECT 'CREATE DATABASE nutratenant_lifecycle'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nutratenant_lifecycle')\gexec

SELECT 'CREATE DATABASE nutratenant_provisioning'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nutratenant_provisioning')\gexec
