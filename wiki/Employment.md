# Inputs

The employment module is broken down into two separate components, the creation of regional employment controls and the allocation of these controls down to the MGRA level. The regional employment controls are briefly mentioned on this page, with its sub-page linked in this section. A description of SANDAG employment categories is provided in that sub-page.

| Input                                                            | Module Source                           | Usage                                                                        |
|------------------------------------------------------------------|-----------------------------------------|------------------------------------------------------------------------------|
| Regional employment controls by ownership and industry           | Employment                              | Regional controls applied to SANDAG employment categories                    |
| MGRA Geography (`[inputs].[mgra]`)                               | Startup                                 | Used to aggregate points to MGRAs                                            |
| MGRA Cross References                                            | Demographic Warehouse                   | Assists cross reference from census blockgroups to MGRAs                     |
| Point geometry active-duty military counts                       | SANDAG GIS EMPCORE                      | Aggregated to MGRAs to create active-duty military counts                    |
| Point geometry employment by ownership and industry              | External (CA EDD)                       | Used to allocate census block employment to MGRAs                            |
| Census block employment by ownership and industry                | External (Census LEHD LODES)            | Allocated to MGRAs and scaled by regional controls to create employment/jobs |


## Regional employment controls by ownership and industry (`[inputs].[controls_jobs]`)
The [Bureau of Labor Statistics (BLS) Quarterly Census of Employment and Wages (QCEW)](https://www.bls.gov/cew/additional-resources/open-data/) provides regional employment controls by ownership and industry that are aggregated to SANDAG employment categories. See the sub-page [Regional employment controls by ownership and industry](https://github.com/SANDAG/Estimates-Program/wiki/Regional-Employment-Controls).

## MGRA Geography (`[inputs].[mgra]`)
See [Startup](https://github.com/SANDAG/Estimates-Program/wiki/Startup).

## MGRA Cross References
See private SANDAG repository [Demographic Warehouse](https://github.com/SANDAG/demographic-warehouse).

## Point geometry active-duty military counts
For active-duty military counts, the counts are taken as-is at the MGRA level and no regional controls are applied, although the regional total is added to the `[inputs].[controls_jobs]` table. Military employment is assigned to "Federal Government" ownership and given industry code "MIL", as no 2-digit NAICS category is appropriate to assign.

Active-duty military counts by installation are published in two primary sources: the Department of Defense [Military One Source](https://www.militaryonesource.mil/) Demographic Profiles from 2010-2019 and the [San Diego Military Advisory Council (SDMAC)](https://sdmac.org/reports/) annual reports from 2018-2020 and in 2025 onwards. For years 2021-2024, where no installation specific data is available, distributions by installation from 2020 are carried forward and controlled to regional totals by service branch published by SDMAC.

A key challenge is that installations, such as Camp Pendleton, span large geographic areas with specific clusters of activity, meaning raw installation totals must be spatially allocated to more realistic on-base locations.

The initial siting and share‑assignment effort was led by SANDAG's transportation modeling team. They reviewed land-use data, aerial imagery, internet sources, and institutional knowledge to identify the MGRAs within each installation that contain offices and other activity centers. They then assigned percent shares of active‑duty personnel to these selected MGRAs, using Series 13 MGRAs, with sitings represented by MGRA centroids. In 2017, SANDAG's GIS team revisited and refined these sitings and assigned shares, incorporating updated land use information and aerial imagery to better reflect on‑base changes over time. Note that this siting process does not assign personnel down to individual buildings; instead, it identifies clusters of buildings and uses the MGRA as a proxy for locating employment, since the MGRA is the most granular geography used by SANDAG. The siting and share-assignment was revisited in 2026 for 2010-2025 data by SANDAG's Estimates & Forecasts team using Series 15 MGRAs, resulting in small adjustments.

## Point geometry employment by ownership and industry
Confidential point geometry employment by ownership and industry is provided to SANDAG by the California Employment Development Department (CA EDD). This dataset is only used to prepare and allocate census block employment by SANDAG employment categories to MGRAs and is **NOT used to create employment/jobs counts**. See private SANDAG repository [EMPCORE](https://github.com/SANDAG/EMPCORE).

## Census block employment by ownership and industry
The [United States Census Bureau Longitudinal Employer-Household Dynamics (LEHD) Origin-Destination Employment Statistics (LODES)](https://lehd.ces.census.gov/data/) dataset provides census block employment by ownership and industry. This dataset requires a split of its block level two-digit NAICS 72 sector, Accommodation and Food Services, into sectors 721 (Accommodation) and 722 (Food Services) using the point geometry employment dataset and is allocated to MGRAs using a combination of the point geometry employment dataset and a simple land area intersection. The allocation process first attempts to allocate from census block to MGRAs using the point geometry employment dataset at the SANDAG employment category level, then using the point geometry employment dataset without taking categories into account, and finally defaulting to the simple land area intersection between census block and MGRAs. This dataset is then scaled to match the regional employment controls by SANDAG employment categories creating employment/jobs by MGRA. See private SANDAG repository [Census-LEHD](https://github.com/SANDAG/Census-LEHD).


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