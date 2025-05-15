/*
Calculate San Diego County age/sex/ethnicity distribution for group quarters
population by type using the 5-year ACS PUMS.

TODO: 2010-2011 have no [DIS] field which makes the 'Group Quarters - Other'
type basically non-existent and the 'Group Quarters - Institutional
Correctional Facilities' type contain a large segment of elderly persons. It
may be prudent to use the 2012 dataset for 2010-2011 distributions. For now,
this results in a divide by zero error for 2010 and unreasonable values for
2011.

Notes:
    (1) The 'Group Quarters - College' and 'Group Quarters - Military' types
may contain both institutional and non-institutional group quarters as they
are solely defined by the [SCHG] and [ESR] fields, respectively.
    (2) The 'Group Quarters - Institutional Correctional Facilities' type
consists of all non-disabled institutional group quarters where persons are
10 years of age or older.
    (3) The 'Group Quarters - Other' type are the leftovers, consisting of all
disabled institutional group quarters, non-institutional group quarters not
defined previously as College or Military group quarters, and non-disabled
institutional group quarters where persons are under 10 years of age.
    (4) The 1997 OMB SP15 race/ethnicity categories are used so the
'Some Other Race alone' category is removed.
    (5) The [SCHG] field changes values after 2011.
    (6) The [DIS] field exists only after 2011.
    (7) The [RELP] field exists from 2010-2018 but changes values in 2010 and
2011 before remaining consistent from 2012-2018 and subsequently being replaced
by the [RELSHIPP] field.
*/
SET NOCOUNT ON;

-- Initialize parameters -----------------------------------------------------
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;


-- Create shell table of required gq type and age/sex/ethnicity categories --- 
DROP TABLE IF EXISTS [#tt_shell];
WITH [gq_type] AS (
    SELECT [gq_type] FROM (
        VALUES
            ('Group Quarters - College'),
            ('Group Quarters - Military'),
            ('Group Quarters - Institutional Correctional Facilities'),
            ('Group Quarters - Other')
    ) AS [tt] ([gq_type])
),
[age_group] AS (
    SELECT [age_group] FROM (
        VALUES
            ('Under 5'),
            ('5 to 9'),
            ('10 to 14'),
            ('15 to 17'),
            ('18 and 19'),
            ('20 to 24'),
            ('25 to 29'),
            ('30 to 34'),
            ('35 to 39'),
            ('40 to 44'),
            ('45 to 49'),
            ('50 to 54'),
            ('55 to 59'),
            ('60 and 61'),
            ('62 to 64'),
            ('65 to 69'),
            ('70 to 74'),
            ('75 to 79'),
            ('80 to 84'),
            ('85 and Older')
    ) AS [tt] ([age_group])
),
[sex] AS (
    SELECT [sex] FROM (VALUES ('Female'), ('Male')) AS [tt] ([sex])
),
[ethnicity] AS (
    SELECT [ethnicity] FROM (
        VALUES
            ('Hispanic'),
            ('Non-Hispanic, White'),
            ('Non-Hispanic, Black'),
            ('Non-Hispanic, American Indian or Alaska Native'),
            ('Non-Hispanic, Asian'),
            ('Non-Hispanic, Hawaiian or Pacific Islander'),
            ('Non-Hispanic, Two or More Races')
    ) AS [tt] ([ethnicity])
)
SELECT [gq_type], [age_group], [sex], [ethnicity]
INTO [#tt_shell]
FROM [gq_type]
CROSS JOIN [age_group]
CROSS JOIN [sex]
CROSS JOIN [ethnicity];


-- Select desired 5-year ACS PUMS --------------------------------------------
-- Build ACS PUMS query based on year
DECLARE @pums_qry nvarchar(max) =
    CASE 
        WHEN @year BETWEEN 2010 AND 2011 THEN 'SELECT [SCHG], [ESR], NULL AS [DIS], [AGEP], [SEX], [HISP], [RAC1P], NULL AS [RELSHIPP], [RELP], [PWGTP] FROM [acs].[pums].[vi_5y_' + CONVERT(nvarchar, @year-4) + '_' + CONVERT(nvarchar, @year) + '_persons_sd]'
        WHEN @year BETWEEN 2012 AND 2018 THEN 'SELECT [SCHG], [ESR], [DIS], [AGEP], [SEX], [HISP], [RAC1P], NULL AS [RELSHIPP], [RELP], [PWGTP] FROM [acs].[pums].[vi_5y_' + CONVERT(nvarchar, @year-4) + '_' + CONVERT(nvarchar, @year) + '_persons_sd]'
        WHEN @year BETWEEN 2019 AND 2023 THEN 'SELECT [SCHG], [ESR], [DIS], [AGEP], [SEX], [HISP], [RAC1P], [RELSHIPP], NULL AS [RELP], [PWGTP] FROM [acs].[pums].[vi_5y_' + CONVERT(nvarchar, @year-4) + '_' + CONVERT(nvarchar, @year) + '_persons_sd]'
    ELSE NULL END;

-- Declare temporary table to receive results of ACS PUMS query
DROP TABLE IF EXISTS [#pums_tbl]
CREATE TABLE [#pums_tbl] (
    [SCHG] VARCHAR(2) NULL,
    [ESR] VARCHAR(1) NULL,
    [DIS] VARCHAR(1) NULL,
    [AGEP] INT NOT NULL,
    [SEX] VARCHAR(1) NOT NULL,
    [HISP] VARCHAR(2) NOT NULL,
    [RAC1P] VARCHAR(1) NOT NULL,
    [RELSHIPP] VARCHAR(2) NULL, 
    [RELP] VARCHAR(2) NULL,  
    [PWGTP] FLOAT NOT NULL
);

-- Insert ACS PUMS query results into table
INSERT INTO [#pums_tbl]
EXECUTE sp_executesql @pums_qry;


-- Calculate age/sex/ethnicity distributions from 5-year ACS PUMS ------------
with [acs_data] AS (
    SELECT  
        CASE
            WHEN (@year BETWEEN 2010 AND 2011 AND [SCHG] IN ('6', '7'))
                OR (@year BETWEEN 2012 AND 2023 AND [SCHG] IN ('15','16'))
            THEN 'Group Quarters - College'
            WHEN [ESR] IN ('4','5') THEN 'Group Quarters - Military'
            WHEN (@year = 2010 AND [RELP] = '14' AND [AGEP] >= 10)
                OR (@year= 2011 AND [RELP] = '13' AND [AGEP] >= 10)
                OR (@year BETWEEN 2012 AND 2018 AND [RELP] = '16' AND [DIS] = '2' AND [AGEP] >= 10)
                OR (@year BETWEEN 2019 AND 2023 AND [RELSHIPP] = '37' AND [DIS] = '2' AND [AGEP] >= 10)
            THEN 'Group Quarters - Institutional Correctional Facilities'
            ELSE 'Group Quarters - Other'
            END AS [gq_type],
        CASE
            WHEN [AGEP] BETWEEN 0 AND 4 THEN 'Under 5'
            WHEN [AGEP] BETWEEN 5 AND 9 THEN '5 to 9'
            WHEN [AGEP] BETWEEN 10 AND 14 THEN '10 to 14'
            WHEN [AGEP] BETWEEN 15 AND 17 THEN '15 to 17'
            WHEN [AGEP] BETWEEN 18 AND 19 THEN '18 and 19'
            WHEN [AGEP] BETWEEN 20 AND 24 THEN '20 to 24'
            WHEN [AGEP] BETWEEN 25 AND 29 THEN '25 to 29'
            WHEN [AGEP] BETWEEN 30 AND 34 THEN '30 to 34'
            WHEN [AGEP] BETWEEN 35 AND 39 THEN '35 to 39'
            WHEN [AGEP] BETWEEN 40 AND 44 THEN '40 to 44'
            WHEN [AGEP] BETWEEN 45 AND 49 THEN '45 to 49'
            WHEN [AGEP] BETWEEN 50 AND 54 THEN '50 to 54'
            WHEN [AGEP] BETWEEN 55 AND 59 THEN '55 to 59'
            WHEN [AGEP] BETWEEN 60 AND 61 THEN '60 and 61'
            WHEN [AGEP] BETWEEN 62 AND 64 THEN '62 to 64'
            WHEN [AGEP] BETWEEN 65 AND 69 THEN '65 to 69'
            WHEN [AGEP] BETWEEN 70 AND 74 THEN '70 to 74'
            WHEN [AGEP] BETWEEN 75 AND 79 THEN '75 to 79'
            WHEN [AGEP] BETWEEN 80 AND 84 THEN '80 to 84'
            WHEN [AGEP] >= 85 THEN '85 and Older'
            ELSE NULL
        END AS [age_group],
        CASE
            WHEN [sex] = '1' THEN 'Male'
            WHEN [sex] = '2' THEN 'Female'
            ELSE NULL
        END AS [sex],
        CASE
            WHEN [HISP] != '01' THEN 'Hispanic'
            WHEN [RAC1P] = '1' THEN 'Non-Hispanic, White'
            WHEN [RAC1P] = '2' THEN 'Non-Hispanic, Black'
            WHEN [RAC1P] IN ('3','4','5') THEN 'Non-Hispanic, American Indian or Alaska Native'
            WHEN [RAC1P] = '6' THEN 'Non-Hispanic, Asian'
            WHEN [RAC1P] = '7' THEN 'Non-Hispanic, Hawaiian or Pacific Islander'
            WHEN [RAC1P] = '9' THEN 'Non-Hispanic, Two or More Races'
            ELSE NULL
        END AS [ethnicity],
        [PWGTP]
    FROM [#pums_tbl]
    WHERE 
        (@year = 2010 AND [RELP] IN ('14','15'))
        OR (@year = 2011 AND [RELP] IN ('13','14'))
        OR (@year BETWEEN 2012 AND 2018 AND [RELP] IN ('16','17'))
        OR (@year BETWEEN 2019 AND 2023 AND [RELSHIPP] IN ('37','38'))
),
[population] AS (
    SELECT
        @run_id AS [run_id],
        @year AS [year],
        [#tt_shell].[gq_type],
        [#tt_shell].[age_group],
        [#tt_shell].[sex],
        [#tt_shell].[ethnicity],
        SUM(ISNULL([PWGTP], 0)) AS [population]
    FROM [#tt_shell]
    LEFT OUTER JOIN [acs_data]
        ON [#tt_shell].[gq_type] = [acs_data].[gq_type]
        AND [#tt_shell].[age_group] = [acs_data].[age_group]
        AND [#tt_shell].[sex] = [acs_data].[sex]
        AND [#tt_shell].[ethnicity] = [acs_data].[ethnicity]
    GROUP BY
        [#tt_shell].[gq_type],
        [#tt_shell].[age_group],
        [#tt_shell].[sex],
        [#tt_shell].[ethnicity]
)
SELECT
    @run_id AS [run_id],
    @year AS [year],
    [gq_type],
    [age_group],
    [sex],
    [ethnicity],
    1.0 * [population] / SUM([population]) OVER (PARTITION BY [gq_type]) AS [distribution]
FROM [population]