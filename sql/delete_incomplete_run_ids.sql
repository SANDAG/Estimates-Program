-- SQL script to delete all data associated with incomplete [run_id] values. This SQL script 
-- deletes both data and the corresponding row of [metadata].[run]

-- Get the list of incomplete [run_id] values
SELECT [run_id]
INTO [#to_delete]
FROM [metadata].[run]
WHERE [complete] = 0;

-- Drop all data associated with these [run_id] values. This is specifically ordered so that key 
-- values are dropped last
DELETE FROM [outputs].[ase]
WHERE [run_id] IN (SELECT [run_id] FROM [#to_delete]);
DELETE FROM [outputs].[gq]
WHERE [run_id] IN (SELECT [run_id] FROM [#to_delete]);
DELETE FROM [outputs].[hh]
WHERE [run_id] IN (SELECT [run_id] FROM [#to_delete]);
DELETE FROM [outputs].[hh_characteristics]
WHERE [run_id] IN (SELECT [run_id] FROM [#to_delete]);
DELETE FROM [outputs].[hhp]
WHERE [run_id] IN (SELECT [run_id] FROM [#to_delete]);
DELETE FROM [outputs].[hs]
WHERE [run_id] IN (SELECT [run_id] FROM [#to_delete]);
DELETE FROM [inputs].[controls_ase]
WHERE [run_id] IN (SELECT [run_id] FROM [#to_delete]);
DELETE FROM [inputs].[controls_city]
WHERE [run_id] IN (SELECT [run_id] FROM [#to_delete]);
DELETE FROM [inputs].[controls_tract]
WHERE [run_id] IN (SELECT [run_id] FROM [#to_delete]);
DELETE FROM [inputs].[mgra]
WHERE [run_id] IN (SELECT [run_id] FROM [#to_delete]);

-- Drop all metadata associated with these [run_id] values
DELETE FROM [metadata].[run]
WHERE [run_id] IN (SELECT [run_id] FROM [#to_delete]);
