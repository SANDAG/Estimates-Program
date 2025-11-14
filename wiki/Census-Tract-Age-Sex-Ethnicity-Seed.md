# Inputs

| Input                                        | Module Source  | Usage                                                             |
|----------------------------------------------|----------------|-------------------------------------------------------------------| 
| Census tract population by age/sex/ethnicity | External (ACS) | Used as seed data in IPF procedure to generate census tract population by age/sex/ethnicity |
| Census tract population by age/sex | External (ACS) | Age/sex controls used in IPF procedure to generate census tract population by age/sex/ethnicity |
| Census tract population by ethnicity | External (ACS) | Ethnicity controls used in IPF procedure to generate census tract population by age/sex/ethnicity |

## Census tract population by age/sex/ethnicity
Initial seed data for the [iterative proportional fitting](https://en.wikipedia.org/wiki/Iterative_proportional_fitting) (IPF) procedure is provided by a combination of eight 5-year American Community Survey (ACS) tables. These are not used directly for census tract population by age/sex/ethnicity as each race category includes both Hispanic and Non-Hispanic unless otherwise noted. Additionally, age categories for the ethnicity tables are reported at too aggregate a level for direct use in SANDAG's Estimates Program, so the B01001 table is used to naively split aggregate categories into more granular groups. These shortcomings make the data unfit for direct use but adequate enough to serve as initial seed data in an IPF procedure.
1. [B01001 | SEX BY AGE](https://data.census.gov/table/ACSDT5Y2020.B01001?q=B01001)
2. [B01001B | SEX BY AGE (BLACK OR AFRICAN AMERICAN ALONE)](https://data.census.gov/table/ACSDT5Y2020.B01001B?q=B01001B)
3. [B01001C | SEX BY AGE (AMERICAN INDIAN AND ALASKA NATIVE ALONE)](https://data.census.gov/table/ACSDT5Y2020.B01001C?q=B01001C)
4. [B01001D | SEX BY AGE (ASIAN ALONE)](https://data.census.gov/table/ACSDT5Y2020.B01001D?q=B01001D)
5. [B01001E | SEX BY AGE (NATIVE HAWAIIAN AND OTHER PACIFIC ISLANDER ALONE)](https://data.census.gov/table/ACSDT5Y2020.B01001E?q=B01001E)
6. [B01001G | SEX BY AGE (TWO OR MORE RACES)](https://data.census.gov/table/ACSDT5Y2020.B01001G?q=B01001G)
7. [B01001H | SEX BY AGE (WHITE ALONE, NOT HISPANIC OR LATINO)](https://data.census.gov/table/ACSDT5Y2020.B01001H?q=B01001H)
8. [B01001I | SEX BY AGE (HISPANIC OR LATINO)](https://data.census.gov/table/ACSDT5Y2020.B01001I?q=B01001I)

## Census tract population by age/sex
The [B01001 | SEX BY AGE](https://data.census.gov/table/ACSDT5Y2020.B01001?q=B01001) 5-year ACS table provides census tract population by age and sex.

## Census tract population by ethnicity
The [B03002 | SEX BY AGE](https://data.census.gov/table/ACSDT5Y2020.B03002?q=B03002) 5-year ACS table provides census tract population by ethnicity. This table includes Hispanic/Non-Hispanic designations within each race.

# Outputs
This process has no direct outputs. Census tract seed data by age/sex/ethnicity is generated using an IPF procedure and fed directly to the next step in the process of generating population by age/sex/ethnicity by housing type in each MGRA.