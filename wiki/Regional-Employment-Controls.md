# Inputs

| Input                                                            | Module Source                           | Usage                                                                        |
|------------------------------------------------------------------|-----------------------------------------|------------------------------------------------------------------------------|
| BLS QCEW Quarterly and Annual Averages                           | External (BLS QCEW)                     | Used to create regional employment controls by SANDAG employment category    |
| Point geometry active-duty military counts                       | SANDAG GIS EMPCORE                      | Aggregated regionally to create active-duty military employment control      |
| Point geometry employment by ownership and industry              | External (CA EDD)                       | Used to create initial seed values in suppressed categories                   |


## BLS QCEW Quarterly and Annual Averages (`[inputs].[controls_jobs]`)
The [Bureau of Labor Statistics (BLS) Quarterly Census of Employment and Wages (QCEW)](https://www.bls.gov/cew/additional-resources/open-data/) provides regional employment controls by ownership and industry that are aggregated to SANDAG employment categories. For additional documentation regarding how SANDAG loads and stores BLS QCEW data see the private SANDAG repository [here](https://github.com/SANDAG/BLS).
The SANDAG Economics Team employment categories are custom-built from a combination of ownership and industry codes. Note the use of industry code "GOV" as the Government ownership categories include all NAICS codes excepting 61, 62, 71, 721, 722. The two-digit NAICS code category of 92 is not provided and is wrapped into the Government ownership categories. The two-digit NAICS code category of 99 is excluded altogether.
| ownership_title  | industry_code |
|----------------- | ------------- |
| Private | 11 |
| Private | 21 |
| Private | 22 |
| Private | 23 |
| Private | 31-33 |
| Private | 42 |
| Private | 44-45 |
| Private | 48-49 |
| Private | 51 |
| Private | 52 |
| Private | 53 |
| Private | 54 |
| Private | 55 |
| Private | 56 |
| Total Covered | 61 |
| Total Covered | 62 |
| Total Covered | 71 |
| Total Covered | 721 |
| Total Covered | 722 |
| Private | 81 |
| Federal Government | GOV |
| Federal Government | MIL |
| State Government | GOV |
| Local Government | GOV |

### Methodology for 2022+
For years 2022 to present, the BLS QCEW quarterly and annual datasets are able to be used directly to create regional employment controls by SANDAG employment categories. For SANDAG employment categories not directly derived from published BLS QCEW annual averages we use summations of monthly employment totals published quarterly to aggregate into SANDAG employment categories and perform averaging and integerization at the final reporting step per guidance received from BLS QCEW staff.  This is also mentioned in item #9 on the QCEW [Questions and Answers](https://www.bls.gov/cew/questions-and-answers.htm) page. These are all the SANDAG employment categories that combine ownership and/or industry categories.

For SANDAG employment categories that are directly derived from published BLS QCEW annual averages, we use those numbers directly as they are calculated by the BLS using unreleased microdata that is more accurate than the rounded quarterly monthly data. These are all the "Private" ownership only categories SANDAG produces.

### Methodology for 2010-2021
For years prior to 2022, the BLS QCEW quarterly and annual datasets contain suppressed values at aggregation levels needed to produce SANDAG employment categories. As such, they are unable to be used directly and a methodology is applied to estimate suppressed values within the BLS QCEW annual dataset. Once all required suppressed values are estimated, the ownership and industry values are aggregated into SANDAG employment categories.

To account for suppressed values, the following methodology is used:

1. Get annual BLS QCEW aggregation level 72 (Domain) by Ownership
    - This aggregation level has been confirmed to not be suppressed for years 2010-2021 in San Diego County

2. Get annual BLS QCEW aggregation level 73 (Supersector) by Ownership
    - Fill in suppressed values with initial estimates using aggregated values from the point geometry employment by ownership and industry CA EDD dataset. **Note: this is only an initial seed value and is not used as the final value.**
    - Subtract non-suppressed Supersector by Ownership from Domain by Ownership to get differences due to suppression
    - Scale and integerize the suppressed Supersector by Ownership categories to match the differences due to suppression

3. Repeat this process for the annual BLS QCEW aggregation level 74 (NAICS Sector) by Ownership using the output from (2)

4. Repeat this process for the annual BLS QCEW aggregation level 75 (NAICS 3-digit) just for NAICS Sector 72 by Ownership using the output from (3) to split into 721/722 NAICS 3-digit sectors

An in-depth example is provided in the private SANDAG repository [here](https://github.com/SANDAG/BLS/issues/58).

## Point geometry active-duty military counts (`[inputs].[controls_jobs]`)
For active-duty military counts, the counts are taken as-is at the MGRA level and no regional controls are applied, although the regional total is added to the `[inputs].[controls_jobs]` table. Military employment is assigned to "Federal Government" ownership and given industry code "MIL", as no 2-digit NAICS category is appropriate to assign.

## Point geometry employment by ownership and industry
Confidential point geometry employment by ownership and industry is provided to SANDAG by the California Employment Development Department (CA EDD). This dataset is only used to create initial seed values for suppressed categories in the BLS QCEW and is **NOT used to create employment/jobs counts**. See private SANDAG repository [EMPCORE](https://github.com/SANDAG/EMPCORE).

# Outputs

## Regional Employment Controls (`[inputs].[controls_jobs]`)

Regional employment/jobs by SANDAG employment category. Calculated using the regional BLS QCEW controls supplemented with active-duty military counts.

Each row of this table contains the following information:

| Column             | Description                                                                                                                                         |
|--------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| `[run_id]`         | Estimates run identifier                                                                                                                            |
| `[year]`           | Year within estimates run                                                                                                                           |
| `[ownership_title]` | Ownership categories (Total Covered, Private, Federal Government, Local Government, State Government)                                           |
| `[industry_code]`  | Two-digit NAICS industry sector (excepting split of 72 into 721 and 722) with "MIL" and "GOV" added for military and aggregate government ownership |
| `[value]`          | Number of jobs                                                                                                                                      |