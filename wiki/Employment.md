**Note: The employment module is preliminary pending receipt of regional control totals from SANDAG's Economics Team**

# Inputs

| Input                                                            | Module Source                   | Usage                                                                        |
|------------------------------------------------------------------|---------------------------------|------------------------------------------------------------------------------| 
| MGRA Geography (`[inputs].[mgra]`)                               | Startup                         | Used to aggregate points to MGRAs                                            |
| MGRA Cross References                                            | Demographic Warehouse           | Assists cross reference from census blockgroups to MGRAs                     |
| Point geometry active duty military counts                       | SANDAG GIS EMPCORE              | Aggregated to MGRAs to create active duty military counts                    |
| Point geometry employment by ownership and industry              | External (CA EDD)               | Used to allocate census block employment to MGRAs                            |
| Census block employment by ownership and industry                | External (Census LEHD LODES)    | Allocated to MGRAs and scaled by regional controls to create employment/jobs |
| Census block group self employment counts                        | External (ACS)                  | Allocated to MGRAs to create self employment counts                          |
| Population by age/sex/ethnicity in each MGRA (`[outputs].[ase]`) | Population by Age Sex Ethnicity | Used to allocate census block group self employment counts to MGRAs          |
| Regional employment controls by ownership and industry           | External (BLS QCEW)             | Regional controls applied to employment by ownership and industry            |

## MGRA Geography (`[inputs].[mgra]`)
See [Startup](https://github.com/SANDAG/Estimates-Program/wiki/Startup).

## MGRA Cross References
See private SANDAG repository [Demographic Warehouse](https://github.com/SANDAG/demographic-warehouse).

## Point geometry active duty military counts
Active-duty military counts by installation are published in two primary sources: the Department of Defense [Military One Source](https://www.militaryonesource.mil/) Demographic Profiles from 2010-2019 and the [San Diego Military Advisory Council (SDMAC)](https://sdmac.org/reports/) annual reports from 2018-2020 and in 2025 onwards. For years 2021-2024, where no installation specific data is available, distributions by installation from 2020 are carried forward and controlled to regional totals by service branch published by SDMAC.

A key challenge is that installations, such as Camp Pendleton, span large geographic areas with specific clusters of activity, meaning raw installation totals must be spatially allocated to more realistic on-base locations.

The initial siting and share‑assignment effort was led by SANDAG's transportation modeling team. They reviewed land-use data, aerial imagery, internet sources, and institutional knowledge to identify the MGRAs within each installation that contain offices and other activity centers. They then assigned percent shares of active‑duty personnel to these selected MGRAs, using Series 13 MGRAs, with sitings represented by MGRA centroids. In 2017, SANDAG's GIS team revisited and refined these sitings and assigned shares, incorporating updated land use information and aerial imagery to better reflect on‑base changes over time. Note that this siting process does not assign personnel down to individual buildings; instead, it identifies clusters of buildings and uses the MGRA as a proxy for locating employment, since the MGRA is the most granular geography used by SANDAG. The siting and share-assignment was revisited in 2026 for 2010-2025 data by SANDAG's Estimates & Forecasts team using Series 15 MGRAs, resulting in small adjustments.

## Point geometry employment by ownership and industry
Confidential point geometry employment by ownership and industry is provided to SANDAG by the California Employment Development Department (CA EDD). This dataset is only used to prepare and allocate census block employment by ownership and industry to MGRAs and is <u>**NOT used to create employment/jobs counts**</u>. See private SANDAG repository [EMPCORE](https://github.com/SANDAG/EMPCORE).

## Census block employment by ownership and industry
The [United States Census Bureau Longitudinal Employer-Household Dynamics (LEHD) Origin-Destination Employment Statistics (LODES)](https://lehd.ces.census.gov/data/) dataset provides census block employment by ownership and industry. This dataset requires a split of its block level two-digit NAICS 72 sector, Accommodation and Food Services, into sectors 721 (Accommodation) and 722 (Food Services) using the point geometry employment dataset and is allocated to MGRAs using a combination of the point geometry employment dataset and a simple land area intersection. This dataset is then scaled to match the regional employment controls by ownership and industry creating employment/jobs by MGRA. See private SANDAG repository [Census-LEHD](https://github.com/SANDAG/Census-LEHD).

## Census block group self employment counts
Census block group counts of self employed individuals are gotten from the American Community Survey (ACS) table [B24080 | SEX BY CLASS OF WORKER FOR THE CIVILIAN EMPLOYED POPULATION 16 YEARS AND OVER](https://data.census.gov/table/ACSDT5Y2020.B24080?q=B24080) using the total count of *Self-employed in own not incorporated business workers*. The block group counts are allocated to MGRAs using a hierarchy of cross references.

1. The percentage of 18-64 year olds across MGRAs within each blockgroup after removing 'Group Quarters - Institutional Correctional Facilities' and 'Group Quarters - Military' persons from the [Population by Age/Sex/Ethnicity](https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Age-Sex-Ethnicity) module. If no such population exists in the blockgroup the next cross reference in the hierarchy is used.
2. The percentage of all persons across MGRAs within each blockgroup from the [Population by Age/Sex/Ethnicity](https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Age-Sex-Ethnicity) module. If no such population exists in the blockgroup the next cross reference in the hierarchy is used.
3. An equal split across MGRAs within each blockgroup

## Population by age/sex/ethnicity in each MGRA (`[outputs].[ase]`)
See [Population by Age/Sex/Ethnicity](https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Age-Sex-Ethnicity).

## Regional employment controls by ownership and industry (`[inputs].[controls_jobs]`)
The [Bureau of Labor Statistics (BLS) Quarterly Census of Employment and Wages (QCEW)](https://www.bls.gov/cew/additional-resources/open-data/) annual dataset provides regional employment controls by ownership and industry. See private SANDAG repository [BLS](https://github.com/SANDAG/BLS).

# Outputs

## Employment/Jobs by Ownership and Industry in each MGRA (`[outputs].[jobs]`)
MGRA employment/jobs by ownership and industry sector. Calculated using the Census LEHD LODES dataset and regional BLS QCEW controls supplemented with active duty military and self employment counts. Note that as of this time ownership is assumed to be "Total Covered", not applicable to active duty military and self-employment counts, and is not explicitly written to the output table.

Each row of this table contains the following information:

| Column             | Description                                                                                |
|--------------------|--------------------------------------------------------------------------------------------|
| `[run_id]`         | Estimates run identifier                                                                   |
| `[year]`           | Year within estimates run                                                                  |
| `[mgra]`           | The Master Geographic Reference Area (MGRA)                                                |
| `[industry_code]`  | Two-digit NAICS industry sector with "MIL" and "SE" added for military and self-employment |
| `[value]`          | Number of jobs                                                                             |