/*
For an input MGRA alias from the [GeoAnalyst].[geography].[geography] table,
return the MGRA zones and their shapes.

The @insert_switch parameter acts as a switch where a value of 1 inserts data
to the [inputs].[mgra] table and a value of 0 returns the tabular result set
without the shape attribute. This is used to validate data in Python without
needing to handle the shape attribute.
*/
SET NOCOUNT ON;
DECLARE @insert_switch BIT = :insert_switch;
DECLARE @run_id INTEGER = :run_id;
DECLARE @series INTEGER = :series;


-- Get MGRA data from [GeoAnalyst] and INSERT to temporary table
DROP TABLE IF EXISTS [#inputs_mgra];
SELECT
    @run_id AS [run_id],
    TRY_CONVERT(INTEGER, [zone].[zone]) AS [mgra],
    [zone].[shape]
INTO [#inputs_mgra]
FROM [GeoAnalyst].[geography].[zone]
INNER JOIN [GeoAnalyst].[geography].[geography]
    ON [zone].[geography_id] = [geography].[geography_id]
WHERE [geography].[alias] = 'mgra' + CAST(@series AS NVARCHAR(2))


-- INSERT data into [inputs].[mgra] if @insert switch is set
-- Otherwise return the tabular data only without the shape attribute
IF @insert_switch = 1
BEGIN
    INSERT INTO [inputs].[mgra] (
        [run_id],
        [mgra],
        [shape]
    )
    SELECT
        [run_id],
        [mgra],
        [shape]
    FROM [#inputs_mgra]
    ORDER BY [mgra]
END
ELSE IF @insert_switch = 0
BEGIN
    SELECT
        [run_id],
        [mgra]
    FROM [#inputs_mgra]
    ORDER BY [mgra]
END