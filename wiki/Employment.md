**Note: The employment module is preliminary pending receipt of regional control totals from SANDAG's Economics Team**

# Inputs

| Input                                                            | Module Source                           | Usage                                                                        |
|------------------------------------------------------------------|-----------------------------------------|------------------------------------------------------------------------------| 
| MGRA Geography (`[inputs].[mgra]`)                               | Startup                                 | Used to aggregate points to MGRAs                                            |
| MGRA Cross References                                            | Demographic Warehouse                   | Assists cross reference from census blockgroups to MGRAs                     |
| Point geometry active-duty military counts                       | SANDAG GIS EMPCORE                      | Aggregated to MGRAs to create active-duty military counts                    |
| Point geometry employment by ownership and industry              | External (CA EDD)                       | Used to allocate census block employment to MGRAs                            |
| Census block employment by ownership and industry                | External (Census LEHD LODES)            | Allocated to MGRAs and scaled by regional controls to create employment/jobs |
| Regional employment controls by ownership and industry           | External (BLS QCEW, SANDAG GIS EMPCORE) | Regional controls applied to employment by ownership and industry            |

## MGRA Geography (`[inputs].[mgra]`)
See [Startup](https://github.com/SANDAG/Estimates-Program/wiki/Startup).

## MGRA Cross References
See private SANDAG repository [Demographic Warehouse](https://github.com/SANDAG/demographic-warehouse).

## Point geometry active-duty military counts
Active-duty military counts by installation are published in two primary sources: the Department of Defense [Military One Source](https://www.militaryonesource.mil/) Demographic Profiles from 2010-2019 and the [San Diego Military Advisory Council (SDMAC)](https://sdmac.org/reports/) annual reports from 2018-2020 and in 2025 onwards. For years 2021-2024, where no installation specific data is available, distributions by installation from 2020 are carried forward and controlled to regional totals by service branch published by SDMAC.

A key challenge is that installations, such as Camp Pendleton, span large geographic areas with specific clusters of activity, meaning raw installation totals must be spatially allocated to more realistic on-base locations.

The initial siting and share‑assignment effort was led by SANDAG's transportation modeling team. They reviewed land-use data, aerial imagery, internet sources, and institutional knowledge to identify the MGRAs within each installation that contain offices and other activity centers. They then assigned percent shares of active‑duty personnel to these selected MGRAs, using Series 13 MGRAs, with sitings represented by MGRA centroids. In 2017, SANDAG's GIS team revisited and refined these sitings and assigned shares, incorporating updated land use information and aerial imagery to better reflect on‑base changes over time. Note that this siting process does not assign personnel down to individual buildings; instead, it identifies clusters of buildings and uses the MGRA as a proxy for locating employment, since the MGRA is the most granular geography used by SANDAG. The siting and share-assignment was revisited in 2026 for 2010-2025 data by SANDAG's Estimates & Forecasts team using Series 15 MGRAs, resulting in small adjustments.

## Point geometry employment by ownership and industry
Confidential point geometry employment by ownership and industry is provided to SANDAG by the California Employment Development Department (CA EDD). This dataset is only used to prepare and allocate census block employment by SANDAG employment categories to MGRAs and is <u>**NOT used to create employment/jobs counts**</u>. See private SANDAG repository [EMPCORE](https://github.com/SANDAG/EMPCORE).

## Census block employment by ownership and industry
The [United States Census Bureau Longitudinal Employer-Household Dynamics (LEHD) Origin-Destination Employment Statistics (LODES)](https://lehd.ces.census.gov/data/) dataset provides census block employment by ownership and industry. This dataset requires a split of its block level two-digit NAICS 72 sector, Accommodation and Food Services, into sectors 721 (Accommodation) and 722 (Food Services) using the point geometry employment dataset and is allocated to MGRAs using a combination of the point geometry employment dataset and a simple land area intersection. The allocation process first attempts to allocate from census block to MGRAs using the point geometry employment dataset at the SANDAG employment category level, then using the point geometry employment dataset without taking categories into account, and finally defaulting to the simple land area intersection between census block and MGRAs. This dataset is then scaled to match the regional employment controls by SANDAG employment categories creating employment/jobs by MGRA. See private SANDAG repository [Census-LEHD](https://github.com/SANDAG/Census-LEHD).

## Regional employment controls by ownership and industry (`[inputs].[controls_jobs]`)
For active-duty military counts, the counts are taken as-is at the MGRA level and no regional controls are applied, although the regional total is added to the `[inputs].[controls_jobs]` table. Military employment is assigned to "Federal Government" ownership and given industry code "MIL", as no 2-digit NAICS category is appropriate to assign.

The [Bureau of Labor Statistics (BLS) Quarterly Census of Employment and Wages (QCEW)](https://www.bls.gov/cew/additional-resources/open-data/) annual dataset provides regional employment controls by ownership and industry that are aggregated to SANDAG employment categories. See private SANDAG repository [BLS](https://github.com/SANDAG/BLS).

The SANDAG Economics' Team employment categories are custom-built from a combination of ownership and industry codes. Note the use of industry code "GOV" as the Government ownership categories include all NAICS codes excepting 61, 62, 71, 722, 723. The two-digit NAICS code category of "92" is not provided and is wrapped into the Government ownership categories. The two-digit NAICS code category of "99" is excluded altogether.

ownership_title | industry_code
-- | --
Private | 11
Private | 21
Private | 22
Private | 23
Private | 31-33
Private | 42
Private | 44-45
Private | 48-49
Private | 51
Private | 52
Private | 53
Private | 54
Private | 55
Private | 56
Total Covered | 61
Total Covered | 62
Total Covered | 71
Total Covered | 721
Total Covered | 722
Private | 81
Federal Government | GOV
Federal Government | MIL
State Government | GOV
Local Government | GOV


# Outputs

## Employment/Jobs by Ownership and Industry in each MGRA (`[outputs].[jobs]`)
MGRA employment/jobs by SANDAG employment category. Calculated using the Census LEHD LODES dataset and regional BLS QCEW controls supplemented with active-duty military counts.

Each row of this table contains the following information:

| Column             | Description                                                                                                                                         |
|--------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| `[run_id]`         | Estimates run identifier                                                                                                                            |
| `[year]`           | Year within estimates run                                                                                                                           |
| `[mgra]`           | The Master Geographic Reference Area (MGRA)                                                                                                         |
| `[ownership_category]` | Ownership categories (Total Covered, Private, Federal Government, Local Government, State Government)                                           |
| `[industry_code]`  | Two-digit NAICS industry sector (excepting split of 72 into 721 and 722) with "MIL" and "GOV" added for military and aggregate government ownership |
| `[value]`          | Number of jobs                                                                                                                                      |