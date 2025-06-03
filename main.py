# Main control flow for the SANDAG Estimates Program. For runtime instructions, refer
# to the repository README.md. For methodology and other documentation, refer to the
# Wiki which can be found at https://github.com/SANDAG/Estimates-Program/wiki

###########
# Imports #
###########

import logging

import python.startup as startup
import python.hs_hh as hs_hh
import python.pop_type as pop
import python.ase as ase
import python.hh_characteristics as hh_characteristics

import python.utils as utils

logger = logging.getLogger(__name__)

################
# Control flow #
################

# Run the Startup module first. Since this module contains only year agnostic data, it
# is run outside of the main year loop
if utils.RUN_INSTRUCTIONS["startup"]:
    utils.display_ascii_art("data/welcome.txt")
    logger.info("Main module: Running Startup module...")
    startup.run_startup()

# Loop through the years first
for year in utils.RUN_INSTRUCTIONS["years"]:
    logger.info(f"Main module: Running {year}...")

    # Go through each module in the correct order for the specified year

    # Housing and Households module
    if utils.RUN_INSTRUCTIONS["housing_and_households"]:
        logger.info("Main module: Running Housing and Households module...")
        hs_hh.run_hs_hh(year)

    # Population module
    if utils.RUN_INSTRUCTIONS["population"]:
        logger.info("Main module: Running Population module...")
        pop.run_pop(year)

    # Population by Age/Sex/Ethnicity module
    if utils.RUN_INSTRUCTIONS["population_by_ase"]:
        logger.info("Main module: Running Population by Age/Sex/Ethnicity module...")
        ase.run_ase(year)

    # Household Characteristics module
    if utils.RUN_INSTRUCTIONS["household_characteristics"]:
        logger.info("Main module: Running Household Characteristics module...")
        hh_characteristics.run_hh_characteristics(year)

    # Staging module
    if utils.RUN_INSTRUCTIONS["staging"]:
        logger.info("Main module: Running Staging module...")

    # Diagnostic print for this year
    logger.info(f"Main module: Finished running {year}\n")

# Final print for completion
logger.info("Main module: Completed")
