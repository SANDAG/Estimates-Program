-- Initialize parameters -----------------------------------------------------
DECLARE @run_id integer = :run_id;  

SELECT DISTINCT [mgra]
FROM [EstimatesProgram].[inputs].[mgra]
WHERE run_id = @run_id
ORDER BY [mgra]
