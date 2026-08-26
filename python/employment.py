# Container for the Employment module. See the Estimates-Program wiki page for more details
# https://github.com/SANDAG/Estimates-Program/wiki/Employment

import functools

import numpy as np
import pandas as pd
import sqlalchemy as sql

import python.tests as tests
import python.utils as utils

generator = np.random.default_rng(utils.RANDOM_SEED)


def run_employment(year: int, debug: bool):
    """Control function to create jobs data by industry_code at the MGRA level.

    Get the LEHD LODES data, aggregate to the MGRA level using the block to MGRA
    crosswalk, then apply control totals from the BLS QCEW using integerization.

    Functionality is split apart for code encapsulation (function inputs not included):
        _get_jobs_inputs - Get all input data related to jobs, including LODES data,
            block to MGRA crosswalk, and control totals from the BLS QCEW. Then process
            the LODES data to the MGRA level by industry_code.
        _validate_jobs_inputs - Validate the input tables from the above function
        _create_jobs_output - Apply control totals to employment data using
            utils.integerize_1d() and create output table
        _validate_jobs_outputs - Validate the output table from the above function
        _insert_jobs - Store input and output data related to jobs to the database.

    Args:
        year: estimates year
    """
    # Calculate regional jobs controls by SANDAG employment category
    controls_inputs = _get_controls_inputs(year)
    _validate_controls_inputs(controls_inputs)

    controls_outputs = _create_controls_outputs(controls_inputs, year)
    _validate_controls_outputs(controls_outputs)

    _insert_controls(controls_outputs, debug)

    # Calculate MGRA level jobs by SANDAG employment category
    jobs_inputs = _get_jobs_inputs(year)
    _validate_jobs_inputs(jobs_inputs)

    jobs_outputs = _create_jobs_output(jobs_inputs, year)
    _validate_jobs_outputs(jobs_outputs)

    _insert_jobs(jobs_outputs, debug)


@functools.lru_cache(maxsize=1)
def _get_controls_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Get inputs required to calculate regional jobs controls.

    The inputs required to calculate regional jobs controls by SANDAG employment
    category vary by year. For years prior to 2022, due to suppression in the
    BLS QCEW data, a methodology is used to calculate regional controls that
    requires multiple input datasets from the BLS QCEW and the confidential
    California Employment Development Department (EDD) datasets. For years 2022
    and later, the BLS QCEW data can be used directly to calculate regional controls.
    """
    # Initialize return dictionary
    controls_inputs = {}

    # Years prior to 2022 use methodology to account for suppression
    # And cannot use the BLS QCEW data directly
    if year < 2022:
        queries = {
            "military": {
                "server": utils.GIS_SERVER,
                "query": "employment/get_military_employment.sql",
                "params": {
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "series": utils.SERIES,
                },
            },
            "region_edd": {
                "server": utils.GIS_SERVER,
                "query": "employment/get_region_edd.sql",
                "params": {"year": year, "estimates_server": utils.ESTIMATES_SERVER},
            },
            "qcew_domain": {
                "server": utils.ESTIMATES_SERVER,
                "query": "employment/get_bls_qcew_domain.sql",
                "params": {"year": year},
            },
            "qcew_supersector": {
                "server": utils.ESTIMATES_SERVER,
                "query": "employment/get_bls_qcew_supersector.sql",
                "params": {"year": year},
            },
            "qcew_naics_sector": {
                "server": utils.ESTIMATES_SERVER,
                "query": "employment/get_bls_qcew_naics_sector.sql",
                "params": {"year": year},
            },
            "qcew_naics3": {
                "server": utils.ESTIMATES_SERVER,
                "query": "employment/get_bls_qcew_naics3.sql",
                "params": {"year": year},
            },
        }
    # Years 2022 and later can use the BLS QCEW data directly
    else:
        queries = {
            "military": {
                "server": utils.GIS_SERVER,
                "query": "employment/get_military_employment.sql",
                "params": {
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "series": utils.SERIES,
                },
            },
            "region_qcew": {
                "server": utils.ESTIMATES_SERVER,
                "query": "employment/get_region_qcew.sql",
                "params": {"run_id": utils.RUN_ID, "year": year},
            },
        }

    for dataset_name, query_config in queries.items():
        if query_config["server"] == utils.ESTIMATES_SERVER:
            with utils.ESTIMATES_ENGINE.connect() as con:
                with open(utils.SQL_FOLDER / query_config["query"]) as file:
                    controls_inputs[dataset_name] = utils.read_sql_query_fallback(
                        sql=sql.text(file.read()),
                        con=con,
                        params=query_config["params"],
                    )
        elif query_config["server"] == utils.GIS_SERVER:
            with utils.GIS_ENGINE.connect() as con:
                with open(utils.SQL_FOLDER / query_config["query"]) as file:
                    controls_inputs[dataset_name] = utils.read_sql_query_fallback(
                        sql=sql.text(file.read()),
                        con=con,
                        params=query_config["params"],
                    )

    return controls_inputs


def _validate_controls_inputs(controls_inputs: dict[str, pd.DataFrame]) -> None:
    """Validate the regional jobs controls input data."""
    datasets = {
        "military": {
            "table_name": "Military employment data",
            "row_count": {"key_columns": {"mgra"}},
            "negative": {},
            "null": {},
        },
        "region_edd": {
            "table_name": "Regional EDD data",
            "row_count": {
                "key_columns": {"ownership_title", ("naics3", "naics_sector")}
            },
            "negative": {},
            "null": {"null_ok": {"naics3"}},  # NULLs are allowed in the NAICS3 field
        },
        "region_qcew": {
            "table_name": "Regional BLS QCEW data",
            # Row count validation not performed as the BLS QCEW data
            # Contains only 23 of the 24 employment categories due to military
            "row_count": None,
            "negative": {},
            "null": {},
        },
        "qcew_domain": {
            "table_name": "BLS QCEW domain data",
            "row_count": {"key_columns": {"ownership_title", "domain"}},
            "negative": {},
            "null": {},
        },
        "qcew_supersector": {
            "table_name": "BLS QCEW supersector data",
            "row_count": {"key_columns": {"ownership_title", "supersector"}},
            "negative": {},
            "null": {},
        },
        "qcew_naics_sector": {
            "table_name": "BLS QCEW NAICS sector data",
            "row_count": {"key_columns": {"ownership_title", "naics_sector"}},
            "negative": {},
            "null": {},
        },
        "qcew_naics3": {
            "table_name": "BLS QCEW NAICS 3-digit data",
            "row_count": {"key_columns": {"ownership_title", "naics3"}},
            "negative": {},
            "null": {},
        },
    }

    for dataset, parameters in datasets.items():
        if dataset in controls_inputs:
            tests.validate_data(
                parameters["table_name"],
                controls_inputs[dataset],
                row_count=parameters["row_count"],
                negative=parameters["negative"],
                null=parameters["null"],
            )


def _create_controls_outputs(
    controls_inputs: dict[str, pd.DataFrame], year: int
) -> dict[str, pd.DataFrame]:
    """Create regional jobs controls by SANDAG employment category.

    There are two methodologies. For years prior to 2022, a methodology is
    used to account for suppression in the BLS QCEW data. For years 2022 and
    later, the BLS QCEW data can be used directly. Both methodologies result
    in regional control totals for SANDAG employment categories that are then
    combined with military employment data to create the final regional jobs
    controls.

    Returns:
        A dictionary containing the regional jobs controls by SANDAG employment
            category
    Args:
        controls_inputs: A dictionary containing input DataFrames related to
            regional jobs controls
        year: The year for which to create regional jobs controls
    """
    # For years prior to 2022, use methodology to account for BLS QCEW suppression
    if year < 2022:
        # This function is called multiple times, so in order to have consistent output it
        # needs to use its own random number generator
        local_generator = np.random.default_rng(seed=utils.RANDOM_SEED)

        qcew_domain = controls_inputs["qcew_domain"].copy()
        qcew_supersector = controls_inputs["qcew_supersector"].copy()
        region_edd = controls_inputs["region_edd"].copy()
        qcew_naics_sector = controls_inputs["qcew_naics_sector"].copy()
        qcew_naics3 = controls_inputs["qcew_naics3"].copy()

        # If any BLS QCEW Supersector data is suppressed
        if qcew_supersector["disclosure_code"].isin(["N"]).any():

            # Aggregate Supersector data to aggregation level 72 (Domain) by ownership
            # And subtract aggregated Domain jobs from the aggregation level 72 (Domain) jobs by ownership
            # This provides the total number of jobs that are suppressed within each Domain by ownership
            domain_diff = (
                qcew_domain.merge(
                    qcew_supersector.groupby(["ownership_title", "domain"])["jobs"]
                    .sum()
                    .reset_index(),
                    how="left",
                    on=["ownership_title", "domain"],
                    suffixes=("", "_supersector"),
                )
                .assign(jobs_diff=lambda x: x["jobs"] - x["jobs_supersector"])
                .drop(columns=["jobs", "jobs_supersector"])
            )

            # Merge suppressed Supersector data with aggregated EDD data
            qcew_supersector = qcew_supersector.merge(
                region_edd.groupby(["ownership_title", "supersector"])["jobs"]
                .sum()
                .reset_index(),
                how="left",
                on=["ownership_title", "supersector"],
                suffixes=("", "_edd"),
            )

            # Scale the EDD data to match the differences
            # Between the Domain jobs and the aggregated Supersector jobs
            for ownership in domain_diff["ownership_title"].unique():
                for domain in domain_diff["domain"].unique():
                    # Get the index values of the suppressed Supersector data
                    suppressed_idx = qcew_supersector[
                        (qcew_supersector["ownership_title"] == ownership)
                        & (qcew_supersector["domain"] == domain)
                        & (qcew_supersector["disclosure_code"] == "N")
                    ].index

                    # Replace suppressed values with scaled EDD values
                    # Such that aggregated Supersector jobs to match Domain jobs
                    if not suppressed_idx.empty:
                        qcew_supersector.loc[suppressed_idx, "jobs"] = (
                            utils.integerize_1d(
                                data=qcew_supersector.loc[suppressed_idx, "jobs_edd"],
                                control=domain_diff.loc[
                                    (domain_diff["ownership_title"] == ownership)
                                    & (domain_diff["domain"] == domain),
                                    "jobs_diff",
                                ].values[0],
                                methodology="weighted_random",
                                generator=local_generator,
                            )
                        )

            qcew_supersector.drop(columns=["disclosure_code", "jobs_edd"], inplace=True)

        # If any QCEW NAICS Sector data is suppressed
        if qcew_naics_sector["disclosure_code"].isin(["N"]).any():

            # Aggregate NAICS Sector data to aggregation level 73 (Supersector) by ownership
            # And subtract aggregated Supersector jobs from the aggregation level 73 (Supersector) jobs by ownership
            # This provides the total number of jobs that are suppressed within each Supersector by ownership
            supersector_diff = (
                qcew_supersector.merge(
                    qcew_naics_sector.groupby(["ownership_title", "supersector"])
                    .agg({"jobs": "sum"})
                    .reset_index(),
                    how="left",
                    on=["ownership_title", "supersector"],
                    suffixes=("", "_naics_sector"),
                )
                .assign(jobs_diff=lambda x: x["jobs"] - x["jobs_naics_sector"])
                .drop(columns=["jobs", "jobs_naics_sector"])
            )

            # Merge suppressed NAICS Sector data with EDD data
            qcew_naics_sector = qcew_naics_sector.merge(
                region_edd.groupby(["ownership_title", "naics_sector"])
                .agg({"jobs": "sum"})
                .reset_index(),
                how="left",
                on=["ownership_title", "naics_sector"],
                suffixes=("", "_edd"),
            )

            # Scale the EDD data to match the differences
            # Between the Supersector jobs and the aggregated NAICS Sector jobs
            for ownership in supersector_diff["ownership_title"].unique():
                for supersector in supersector_diff["supersector"].unique():
                    # Get the index values of the suppressed NAICS Sector data
                    suppressed_idx = qcew_naics_sector[
                        (qcew_naics_sector["ownership_title"] == ownership)
                        & (qcew_naics_sector["supersector"] == supersector)
                        & (qcew_naics_sector["disclosure_code"] == "N")
                    ].index

                    # Replace suppressed values with scaled EDD values
                    # Such that aggregated NAICS Sector jobs match Supersector jobs
                    if not suppressed_idx.empty:
                        qcew_naics_sector.loc[suppressed_idx, "jobs"] = (
                            utils.integerize_1d(
                                data=qcew_naics_sector.loc[suppressed_idx, "jobs_edd"],
                                control=supersector_diff.loc[
                                    (supersector_diff["ownership_title"] == ownership)
                                    & (supersector_diff["supersector"] == supersector),
                                    "jobs_diff",
                                ].values[0],
                                methodology="weighted_random",
                                generator=local_generator,
                            )
                        )

        # This section only applies to NAICS Sector 72 and NAICS 3-digit 721 and 722
        # If any NAICS 3-digit data is suppressed
        if qcew_naics3["disclosure_code"].isin(["N"]).any():
            # Aggregate NAICS 3-digit data to aggregation level 74 (NAICS Sector) by ownership
            # And subtract aggregated NAICS Sector jobs from the aggregation level 74 (NAICS Sector) jobs by ownership
            # This provides the total number of jobs that are suppressed within each NAICS Sector by ownership
            naics_sector_diff = (
                qcew_naics_sector.merge(
                    qcew_naics3.groupby(["ownership_title", "naics_sector"])
                    .agg({"jobs": "sum"})
                    .reset_index(),
                    how="left",
                    on=["ownership_title", "naics_sector"],
                    suffixes=("", "_naics3"),
                )
                .assign(jobs_diff=lambda x: x["jobs"] - x["jobs_naics3"])
                .drop(columns=["jobs", "jobs_naics3"])
            )

            # Merge suppressed NAICS 3-digit data with EDD data
            qcew_naics3 = qcew_naics3.merge(
                region_edd.groupby(["ownership_title", "naics3"])
                .agg({"jobs": "sum"})
                .reset_index(),
                how="left",
                on=["ownership_title", "naics3"],
                suffixes=("", "_edd"),
            )

            # Scale the EDD data to match the differences
            # Between the NAICS Sector jobs and the aggregated NAICS 3-digit jobs
            for ownership in naics_sector_diff["ownership_title"].unique():
                for naics_sector in naics_sector_diff["naics_sector"].unique():
                    # Get the index values of the suppressed NAICS Sector data
                    suppressed_idx = qcew_naics3[
                        (qcew_naics3["ownership_title"] == ownership)
                        & (qcew_naics3["naics_sector"] == naics_sector)
                        & (qcew_naics3["disclosure_code"] == "N")
                    ].index

                    # Replace suppressed values with scaled EDD values
                    # Such that aggregated NAICS 3-digit jobs match NAICS Sector jobs
                    if not suppressed_idx.empty:
                        qcew_naics3.loc[suppressed_idx, "jobs"] = utils.integerize_1d(
                            data=qcew_naics3.loc[suppressed_idx, "jobs_edd"],
                            control=naics_sector_diff.loc[
                                (naics_sector_diff["ownership_title"] == ownership)
                                & (naics_sector_diff["naics_sector"] == naics_sector),
                                "jobs_diff",
                            ].values[0],
                            methodology="weighted_random",
                            generator=local_generator,
                        )

        # Combine the NAICS Sector and NAICS 3-digit data
        result_set = (
            pd.concat(
                [
                    qcew_naics_sector.loc[
                        qcew_naics_sector["naics_sector"] != "72"
                    ].rename(columns={"naics_sector": "industry_code"})[
                        ["ownership_title", "industry_code", "jobs"]
                    ],
                    qcew_naics3.rename(columns={"naics3": "industry_code"})[
                        ["ownership_title", "industry_code", "jobs"]
                    ],
                ],
                ignore_index=True,
            )
            .assign(run_id=utils.RUN_ID, year=year)
            .rename(columns={"jobs": "value"})[
                [
                    "run_id",
                    "year",
                    "ownership_title",
                    "industry_code",
                    "value",
                ]
            ]
        )

        # Aggregate to SANDAG employment categories

        # Remove NAICS 99 and Private ownership 92
        result_set = result_set.loc[
            ~(
                (result_set["industry_code"] == "99")
                | (
                    (result_set["ownership_title"] == "Private")
                    & (result_set["industry_code"] == "92")
                )
            )
        ]

        # Following NAICS codes include all ownership categories
        result_set.loc[
            result_set["industry_code"].isin(["61", "62", "71", "721", "722"]),
            "ownership_title",
        ] = "Total Covered"

        # All other NAICS codes are Private only
        # Government ownership is aggregated across NAICS codes
        result_set.loc[
            result_set["ownership_title"].isin(
                ["Federal Government", "State Government", "Local Government"]
            ),
            "industry_code",
        ] = "GOV"

        result_set = (
            result_set.groupby(["run_id", "year", "ownership_title", "industry_code"])[
                "value"
            ]
            .sum()
            .reset_index()
        )

    # For years 2022 and later, use the QCEW data directly
    else:
        result_set = controls_inputs["region_qcew"].copy()

    # Aggregate military employment to the regional level
    military = (
        controls_inputs["military"]
        .groupby(["run_id", "year", "ownership_title", "industry_code"])["value"]
        .sum()
        .reset_index()
    )

    # Combine the regional jobs controls with military employment data and return
    return {
        "results": pd.concat(
            [result_set, military],
            ignore_index=True,
        )
    }


def _validate_controls_outputs(controls_outputs: dict[str, pd.DataFrame]) -> None:
    """Validate the regional jobs controls output data."""
    tests.validate_data(
        "Regional jobs controls by SANDAG employment category",
        controls_outputs["results"],
        row_count={"key_columns": {("ownership_title", "industry_code")}},
        negative={},
        null={},
    )


def _insert_controls(controls_outputs: dict[str, pd.DataFrame], debug: bool) -> None:
    """Insert the regional jobs controls data into the database."""
    # Save locally if in debug mode
    if debug:
        controls_outputs["results"].to_csv(
            utils.DEBUG_OUTPUT_FOLDER / "inputs_controls_jobs.csv", index=False
        )

    # Otherwise, insert to database
    else:
        with utils.ESTIMATES_ENGINE.connect() as con:
            controls_outputs["results"].to_sql(
                name="controls_jobs",
                con=con,
                schema="inputs",
                if_exists="append",
                index=False,
            )


def _get_lodes_data(year: int) -> pd.DataFrame:
    """Retrieve LEHD LODES data for a specified year and split industry_code 72 into
        721 and 722 using split percentages.

    Args:
        year: The year for which to retrieve LEHD LODES data.
    Returns:
        combined LEHD LODES data with naics
    """

    with utils.ESTIMATES_ENGINE.connect() as con:
        with open(utils.SQL_FOLDER / "employment/get_lodes_data.sql") as file:
            lodes_data = utils.read_sql_query_fallback(
                max_lookback=2,
                sql=sql.text(file.read()),
                con=con,
                params={"year": year},
            )

    with utils.GIS_ENGINE.connect() as con:
        with open(utils.SQL_FOLDER / "employment/get_naics72_split.sql") as file:
            split_naics_72 = utils.read_sql_query_fallback(
                max_lookback=2,
                sql=sql.text(file.read()),
                con=con,
                params={"year": year},
            )

    # Split industry_code 72 and combine with other industries
    lodes_72_split = lodes_data.loc[lambda df: df["industry_code"] == "72"].merge(
        split_naics_72, on="block", how="left"
    )

    combined_data = pd.concat(
        [
            lodes_data.loc[lambda df: df["industry_code"] != "72"],
            lodes_72_split.assign(
                industry_code="721", jobs=lambda df: df["jobs"] * df["pct_721"]
            ),
            lodes_72_split.assign(
                industry_code="722", jobs=lambda df: df["jobs"] * df["pct_722"]
            ),
        ],
        ignore_index=True,
    )[["year", "block", "ownership_title", "industry_code", "jobs"]]

    return combined_data


def _aggregate_lodes_to_mgra(
    combined_data: pd.DataFrame, xref: pd.DataFrame, year: int
) -> pd.DataFrame:
    """Aggregate LODES data to MGRA level using allocation percentages.

    This function allocates jobs from Census blocks to MGRAs using distributions from
    the California Employment Development Department (EDD) point-level dataset. Blocks
    with no EDD data available use a simple land area intersection to allocate jobs to
    MGRAs. The allocation first attempts to allocate within SANDAG employment categories
    using EDD data, then falls back to using EDD data without considering categories,
    and finally falls back to using the land area intersection.

    Args:
        combined_data: LODES data with columns: year, block, industry_code, jobs
        xref: Crosswalk with columns: block, mgra, pct_edd_category, pct_edd, pct_area, flag
        year: The year for which to aggregate data

    Returns:
        Aggregated data at MGRA level with columns: run_id, year, mgra,
            ownership_title, industry_code, value
    """
    # Get MGRA data from SQL
    with utils.ESTIMATES_ENGINE.connect() as con:
        mgra_data = pd.read_sql_query(
            sql=sql.text("""
                SELECT DISTINCT [mgra]
                FROM [inputs].[mgra]
                WHERE run_id = :run_id
                ORDER BY [mgra]
                """),
            con=con,
            params={"run_id": utils.RUN_ID},
        )

    jobs = (
        # Get unique SANDAG employment categories and cross join with MGRA data
        mgra_data.merge(
            combined_data[["ownership_title", "industry_code"]]
            .drop_duplicates()
            .reset_index(drop=True),
            how="cross",
        )
        .assign(year=year)
        # Get the LODES data and allocated to MGRAs using the crosswalk and allocation percentages
        .merge(
            combined_data.merge(
                xref, on=["block", "ownership_title", "industry_code"], how="inner"
            )
            .assign(
                value=lambda df: df["jobs"]
                * np.where(
                    df["flag"] == "pct_edd_category",
                    df["pct_edd_category"],
                    np.where(df["flag"] == "pct_edd", df["pct_edd"], df["pct_area"]),
                )
            )
            .groupby(
                ["year", "mgra", "ownership_title", "industry_code"], as_index=False
            )["value"]
            .sum(),
            on=["year", "mgra", "ownership_title", "industry_code"],
            how="left",
        )
        .fillna({"value": 0})
        .assign(run_id=utils.RUN_ID)[
            ["run_id", "year", "mgra", "ownership_title", "industry_code", "value"]
        ]
    )

    return jobs


def _get_jobs_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Get input data related to jobs for a specified year.

    Args:
        year: The year for which to retrieve input data.
    Returns:
        input DataFrames related to jobs.
    """
    # Store results here
    jobs_inputs = {}

    # Get regional employment control totals
    jobs_inputs["control_totals"] = _create_controls_outputs(
        _get_controls_inputs(year), year
    )["results"]

    # Get LEHD LODES data with industry code 72 split into 721 and 722
    jobs_inputs["lodes_data"] = _get_lodes_data(year)

    with utils.GIS_ENGINE.connect() as con:
        # Get crosswalk from Census blocks to MGRAs
        with open(utils.SQL_FOLDER / "employment/xref_block_to_mgra.sql") as file:
            jobs_inputs["xref_block_to_mgra"] = utils.read_sql_query_fallback(
                max_lookback=1,
                sql=sql.text(file.read()),
                con=con,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "estimates_server": utils.ESTIMATES_SERVER,
                    "estimates_database": utils.ESTIMATES_DATABASE,
                },
            )

        # Get military employment at the MGRA level
        with open(utils.SQL_FOLDER / "employment/get_military_employment.sql") as file:
            jobs_inputs["military_emp"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=con,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "series": utils.SERIES,
                },
            )

    return jobs_inputs


def _validate_jobs_inputs(jobs_inputs: dict[str, pd.DataFrame]) -> None:
    """Validate the jobs input data"""
    # LODES only includes blocks with jobs therefore no row count validation performed
    # https://lehd.ces.census.gov/data/lehd-code-samples/sections/lodes/basic_examples.html
    tests.validate_data(
        "LEHD LODES data",
        jobs_inputs["lodes_data"],
        negative={},
        null={},
    )
    # No row count validation performed as xref is many-to-many
    # NULLs are allowed in the result set
    tests.validate_data(
        "xref_block_to_mgra",
        jobs_inputs["xref_block_to_mgra"],
        negative={},
    )
    tests.validate_data(
        "Military employment data",
        jobs_inputs["military_emp"],
        row_count={"key_columns": {"mgra"}},
        negative={},
        null={},
    )
    tests.validate_data(
        "Jobs control totals",
        jobs_inputs["control_totals"],
        row_count={"key_columns": {("ownership_title", "industry_code")}},
        negative={},
        null={},
    )


def _create_jobs_output(
    jobs_inputs: dict[str, pd.DataFrame], year: int
) -> dict[str, pd.DataFrame]:
    """Apply control totals to employment data using utils.integerize_1d().

    Args:
        jobs_inputs: A dictionary containing input DataFrames related to jobs

    Returns:
        Controlled employment data.
    """
    # Create MGRA level jobs data by combining LODES and military data
    mgra_jobs = pd.concat(
        [
            # Aggregate LODES jobs to MGRA level
            _aggregate_lodes_to_mgra(
                jobs_inputs["lodes_data"], jobs_inputs["xref_block_to_mgra"], year
            ),
            # Include military employment at MGRA level
            jobs_inputs["military_emp"][
                ["run_id", "year", "mgra", "ownership_title", "industry_code", "value"]
            ],
        ],
        ignore_index=True,
    ).sort_values(by=["mgra", "ownership_title", "industry_code"])

    # Create list to store controlled values for each industry
    results = []

    # Apply integerize_1d to each SANDAG employment category
    for ownership_title in mgra_jobs["ownership_title"].unique():
        for industry_code in mgra_jobs["industry_code"].unique():
            # Filter for this ownership_title and industry_code
            mask = mgra_jobs.loc[
                (mgra_jobs["ownership_title"] == ownership_title)
                & (mgra_jobs["industry_code"] == industry_code)
            ]

            # If no records are returned, skip to next iteration
            if mask.empty:
                continue
            else:
                # Get control value and apply integerize_1d
                control_value = (
                    jobs_inputs["control_totals"]
                    .loc[
                        (
                            jobs_inputs["control_totals"]["ownership_title"]
                            == ownership_title
                        )
                        & (
                            jobs_inputs["control_totals"]["industry_code"]
                            == industry_code
                        ),
                        "value",
                    ]
                    .iloc[0]
                )

                results.append(
                    mask.assign(
                        value=utils.integerize_1d(
                            data=mask["value"],
                            control=control_value,
                            methodology="weighted_random",
                            generator=generator,
                        )
                    )
                )

    return {"results": pd.concat(results, ignore_index=True)}


def _validate_jobs_outputs(jobs_outputs: dict[str, pd.DataFrame]) -> None:
    """Validate the jobs output data"""
    tests.validate_data(
        "Controlled jobs data",
        jobs_outputs["results"],
        row_count={"key_columns": {"mgra", ("ownership_title", "industry_code")}},
        negative={},
        null={},
    )


def _insert_jobs(
    jobs_outputs: dict[str, pd.DataFrame],
    debug: bool,
) -> None:
    """Insert output data related to jobs to the database."""

    # Save locally if in debug mode
    if debug:
        jobs_outputs["results"].to_csv(
            utils.DEBUG_OUTPUT_FOLDER / "outputs_jobs.csv", index=False
        )

    # Otherwise, insert to database
    else:
        with utils.ESTIMATES_ENGINE.connect() as con:
            jobs_outputs["results"].to_sql(
                name="jobs", con=con, schema="outputs", if_exists="append", index=False
            )
