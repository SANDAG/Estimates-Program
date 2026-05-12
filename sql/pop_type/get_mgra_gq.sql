/*
This query takes SANDAGs GIS team Group Quarters (GQ) point layer and
aggregates to the MGRA level by type. Results are returned as a SELECT
statement for use in a Python utility that generates final results.

Note that the [inputs].[special_mgras] table is used to segment
non-College and non-Military Group Quarters into 
"Group Quarters - Institutional Correctional Facilities"
and "Group Quarters - Other".
*/


SET NOCOUNT ON;
-- Initialize parameters and return table ------------------------------------
DECLARE @run_id INTEGER = :run_id;
DECLARE @year INTEGER = :year;
DECLARE @gis_server NVARCHAR(20) = :gis_server;

-- Build the expected return table MGRA x GQ Type
SELECT
    [mgra].[mgra],
    [jurisdiction],
    [gq_type]
INTO [#tt_shell]
FROM [inputs].[mgra]
INNER JOIN [demographic_warehouse].[dim].[mgra] AS [dw_mgra]
    ON [mgra].[mgra] = [dw_mgra].[mgra]
    AND [dw_mgra].[series] = (SELECT [series] FROM [metadata].[run] WHERE [run_id] = @run_id)
INNER JOIN [demographic_warehouse].[dim].[mgra_xref]
    ON [dw_mgra].[mgra_id] = [mgra_xref].[mgra_id]
    AND [mgra_xref].[xref_year] = @year
CROSS JOIN (
    SELECT [gq_type] FROM (
        VALUES
            ('Group Quarters - College'),
            ('Group Quarters - Military'),
            ('Group Quarters - Institutional Correctional Facilities'),
            ('Group Quarters - Other')
    ) AS [tt] ([gq_type])
) AS [gq_type]
WHERE [run_id] = @run_id


-- Get SANDAG GIS team GQ dataset --------------------------------------------
-- Build the OPENQUERY to the GIS server to get the GQ point data of interest
-- Note the statement stores results in a temporary table for later use
CREATE TABLE [#gq] (
    [id] INT IDENTITY(1,1) NOT NULL,
    [gqMil] INT NOT NULL,
    [gqCivCol] INT NOT NULL,
    [gqOther] INT NOT NULL,
    [Shape] geometry NOT NULL,
    CONSTRAINT [pk_tt_gq] PRIMARY KEY ([id])
)

DECLARE @qry nvarchar(max) = '
    INSERT INTO [#gq]
    SELECT * FROM OPENQUERY([' + @gis_server + '],
    ''SELECT [gqMil], [gqCivCol], [gqOther], [Shape]
      FROM [SPACECORE].[gis].[GROUPQUARTERS]
      WHERE [effectYear] = ' + CONVERT(nvarchar, @year) + ''')
'
EXEC sp_executesql @qry;


-- Aggregate GQ points to MGRAs by type -------------------------------------
SELECT
    @run_id AS [run_id],
    @year AS [year],
    [#tt_shell].[mgra],
    [#tt_shell].[jurisdiction],
    [#tt_shell].[gq_type],
    ISNULL([value], 0) AS [value]
FROM [#tt_shell]
LEFT OUTER JOIN (
    SELECT
        [mgra].[mgra], 
        SUM([gqCivCol]) AS [Group Quarters - College],
        SUM([gqMil]) AS [Group Quarters - Military],
        SUM(
            CASE WHEN [special_mgras].[pop_type] = 'Group Quarters - Institutional Correctional Facilities'
                 THEN [gqOther]
                 ELSE 0 END
        ) AS [Group Quarters - Institutional Correctional Facilities],
        SUM(
            CASE WHEN [special_mgras].[pop_type] != 'Group Quarters - Institutional Correctional Facilities'
                    OR [special_mgras].[pop_type] IS NULL
                 THEN [gqOther]
                 ELSE 0 END
        ) AS [Group Quarters - Other]
    FROM [inputs].[mgra]
    LEFT OUTER JOIN (
        SELECT
            [mgra],
            [pop_type]
        FROM [inputs].[special_mgras]
        WHERE
            @year BETWEEN [start_year] AND [end_year]
            AND [special_mgras].[series] = (SELECT [series] FROM [metadata].[run] WHERE [run_id] = @run_id)
    ) AS [special_mgras]
        ON [mgra].[mgra] = [special_mgras].[mgra]
    INNER JOIN [#gq]
        ON [mgra].[Shape].STIntersects([#gq].[Shape]) = 1
    WHERE [run_id] = @run_id
    GROUP BY [mgra].[mgra]
) AS [pivot]
UNPIVOT (
    [value] FOR [gq_type] IN (
        [Group Quarters - College],
        [Group Quarters - Military],
        [Group Quarters - Institutional Correctional Facilities],
        [Group Quarters - Other]
    )
) AS [unpivot]
    ON [#tt_shell].[mgra] = [unpivot].[mgra]
    AND [#tt_shell].[gq_type] = [unpivot].[gq_type]


-- Clean up ------------------------------------------------------------------
-- Drop the temporary tables
DROP TABLE [#tt_shell]
DROP TABLE [#gq]