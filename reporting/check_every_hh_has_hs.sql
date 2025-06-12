-- SQL script to check that every household has a housing structure
DECLARE @run_id INTEGER = :run_id;

-- Check housing stock and households -------------------------------------------------
SELECT  
    [hs].[year],
    [hs].[mgra],
    [hs_sfd],
    [hh_sfd],
    [hs_sfmu],
    [hh_sfmu],
    [hs_mf],
    [hh_mf],
    [hs_mh],
    [hh_mh]
FROM (
        SELECT 
            [year],
            [mgra],
            [Single Family - Detached] AS [hs_sfd],
            [Single Family - Multiple Unit] AS [hs_sfmu],
            [Multifamily] AS [hs_mf],
            [Mobile Home] AS [hs_mh]
        FROM [outputs].[hs]
        PIVOT(
            SUM([value])
            FOR [structure_type] IN (
                [Single Family - Detached],
                [Single Family - Multiple Unit],
                [Multifamily],
                [Mobile Home])
            ) AS [pivot]
        WHERE [run_id] = @run_id
    ) AS [hs]
LEFT JOIN (
        SELECT 
            [year],
            [mgra],
            [Single Family - Detached] AS [hh_sfd],
            [Single Family - Multiple Unit] AS [hh_sfmu],
            [Multifamily] AS [hh_mf],
            [Mobile Home] AS [hh_mh]
        FROM [outputs].[hh]
        PIVOT(
            SUM([value])
            FOR [structure_type] IN (
                [Single Family - Detached],
                [Single Family - Multiple Unit],
                [Multifamily],
                [Mobile Home])
            ) AS [pivot]
        WHERE [run_id] = @run_id
    ) AS [hh]
    ON [hs].[year] = [hh].[year]
    AND [hs].[mgra] = [hh].[mgra]
WHERE [hs_sfd] < [hh_sfd]
    OR [hs_sfmu] < [hh_sfmu]
    OR [hs_mf] < [hh_mf]
    OR [hs_mh] < [hh_mh]
ORDER BY [hs].[year], [hs].[mgra]
