# Testing space for various n-dimensional rounding algorithms

import functools
import string
import pathlib
import pulp
import time
import numpy as np
import pandas as pd
from unicodedata import category

import ipf
import random_data


# Some file I/O stuff
THIS_FOLDER = pathlib.Path(__file__).parent.resolve()
TEMP_DATA_FOLDER = THIS_FOLDER / "temp_data"
TEMP_DATA_FOLDER.mkdir(parents=False, exist_ok=True)
ACTUAL_DATA_FOLDER = THIS_FOLDER / "post_ipf_actual_data"


def check_input_validity(data: np.ndarray, marginals: list[np.ndarray]):
    """Ensure that input data and marginals are valid

    Args:
        data: The data to check
        marginals: The marginals to check

    Returns:
        None

    Raises:
        ValueError: If the data and marginals have different shapes
        ValueError: If the marginals don't sum to the same value
    """
    # Check seed and marginals match
    if len(data.shape) != len(marginals):
        raise ValueError(
            f"Each dimension of 'seed' must have an associated marginal control ({len(data.shape)} expected, {len(marginals)} actual)"
        )
    for dim, size in zip(range(len(data.shape)), data.shape):
        if len(marginals[dim]) != size:
            raise ValueError(
                f"The '{dim}' dimension of 'seed' is size {size} but the associated marginal control is size {len(marginals[dim])}"
            )

    # Check marginals all sum to the exact same value
    first_sum = marginals[0].sum()
    for dim in range(1, len(marginals)):
        if first_sum != marginals[dim].sum():
            raise ValueError(
                f"Marginals don't sum to the same value (0 marginal sums to {first_sum}, {dim} marginal sums to {marginals[dim].sum()})"
            )


def compute_rounding_error(
    actual: np.ndarray, control: list[np.ndarray]
) -> list[np.ndarray]:
    """Compute the rounding error between actual data and control marginals"""
    rounding_error = []
    for dim in range(len(control)):
        missing_dim = tuple(d for d in range(len(control)) if d != dim)
        rounding_error.append(actual.sum(axis=missing_dim) - control[dim])
    return rounding_error


def check_output_validity(data: np.ndarray, marginals: list[np.ndarray]):
    """

    Args:
        data:
        marginals:

    Returns:

    """
    # Check all rounding error is zero
    rounding_error = np.array(
        [error.sum() for error in compute_rounding_error(data, marginals)]
    )
    if np.any(rounding_error != 0):
        raise ValueError

    # Check for invalid (aka negative, null, or non-integer) values
    if np.any(data < 0):
        raise ValueError
    if np.sum(np.isnan(data)) > 0:
        raise ValueError
    if not np.all(data == np.floor(data)):
        raise ValueError


def _nd_controlling_fuzzy_step(
    rounded_data: np.ndarray,
    rounding_error: list[np.ndarray],
    gen: np.random.Generator,
    frac: float,
):

    # Very useful constant in this function
    n_dims = len(rounding_error)

    # First compute the weights for random choice

    # The weights used to select indicies are the product of the rounding error
    # along each axis. This ensures that the random choice is more likely to choose
    # indicies that need more adjustment, when accounting for all axes
    # The cursed "dim_string"/"subscripts" variable are instructions for the
    # "np.einsum()" function. For example, in three dimensions, it would look like
    # "a,b,c->abc". The string means data from each of "a", "b", and "c" are
    # transformed ("->") to the product of the three ("abc")
    dim_string = string.ascii_lowercase[:n_dims]
    subscripts = f"{','.join(dim_string)}->{dim_string}"
    weights = np.einsum(
        subscripts,
        *rounding_error,
    )

    # Zero out the weights where data is already zero
    zero_data = np.where(rounded_data == 0, 0, 1)
    weights = weights * zero_data

    # Weights must sum to one so we normalize. Additionally, gen.choice only works
    # on one dimensional data, so it must be flattened. Fortunately, Numpy has a
    # ton of functionality for flattening and unflattening ndarrays
    weights = weights / np.sum(weights)
    flat_weight = weights.flatten(order="C")

    # Stop for analysis in case we can't solve
    if np.any(np.isnan(flat_weight)):
        raise ValueError()

    # Select some percentage of indicies to adjust (see function parameters)
    flat_indicies = gen.choice(
        np.prod(rounded_data.shape),
        size=int(np.ceil(int(np.sum(rounding_error[0])) * frac)),
        replace=False,
        p=flat_weight,
    )
    ndarry_indicies = np.unravel_index(flat_indicies, rounded_data.shape, order="C")

    # Get the actual corrections to be made
    corrections = np.zeros(rounded_data.shape)
    np.add.at(corrections, ndarry_indicies, -1)

    # Check the corrections for anything invalid. AKA check for any corrections
    # which overshoot the total amount of rounding error
    for dim in range(n_dims):
        missing_dim = tuple(d for d in range(n_dims) if d != dim)
        overshoot = corrections.sum(axis=missing_dim) + rounding_error[dim]

        if np.any(overshoot < 0):
            # When we randomly overshoot, we get into a somewhat complex routine :(
            for overshoot_index in np.where(overshoot < 0)[0]:

                # The amount to adjust, a helper variable
                to_adj = abs(int(overshoot[overshoot_index]))

                # Slice both weights and corrections along the dimension/index
                # that an overshoot has occurred
                weights_slice = weights.take(indices=overshoot_index, axis=dim)
                corrections_slice = corrections.take(indices=overshoot_index, axis=dim)

                # Get the weights where there are corrections. Since the corrections
                # slice is zero unless there are corrections, multiplying then
                # making it positive functionally finds weights with corrections
                weights_slice = np.abs(corrections_slice * weights_slice)

                # Get the largest weights were there are corrections. Again, we have
                # a Numpy function which only works on flat objects (np.argsort()).
                # Thankfully, Numpy makes working with flat/boxy objects pretty easy
                weights_slice_adj_indicies = weights_slice.flatten(order="C").argsort(
                    kind="stable"
                )[-to_adj:]

                # Transform the flat indicies of the weight slice into ND indicies
                # of the slice
                corrections_slice_adj_indicies = np.unravel_index(
                    weights_slice_adj_indicies, corrections_slice.shape, order="C"
                )

                # Transform the sliced coordinates into indicies in the non-sliced
                # data
                corrections_adj_indicies = (
                    corrections_slice_adj_indicies[:dim]
                    + (np.repeat(overshoot_index, to_adj),)
                    + corrections_slice_adj_indicies[dim:]
                )

                # Execute the adjustment of the corrections
                np.add.at(corrections, corrections_adj_indicies, 1)

    # Apply the corrections and return the data
    rounded_data += corrections
    return rounded_data


def nd_controlling_fuzzy(
    data: np.ndarray,
    marginals: list[np.ndarray],
    seed: int = 42,
    frac: float = 0.5,
) -> np.array:
    """Round the input data such that marginals exact match, using a stochastic method

    Args:
        data: The data to be rounded. This should be the output of an IPF procedure
        marginals: The marginals to control to
        seed: A random seed to ensure reproducibility of the stochastic procedure
        frac: The fraction of total rounding error to correct in each iteration

    Returns:
        The data rounded to match the marginals

    Raises:
        ValueError: If the stochastic procedure runs into a dead end when attempting to
            solve the rounding error
    """

    check_input_validity(data, marginals)

    # The random generator for controlling
    gen = np.random.default_rng(seed)

    # Round all values up and compute various residuals
    rounded_data = np.ceil(data)
    rounding_error = compute_rounding_error(rounded_data, marginals)
    total_rounding_error = int(np.sum(rounding_error[0]))

    # Repeat the fuzzy rounding procedure until all rounding error is gone
    while total_rounding_error > 0:
        rounded_data = _nd_controlling_fuzzy_step(
            rounded_data, rounding_error, gen, frac
        )

        # Recompute rounding error
        rounding_error = compute_rounding_error(rounded_data, marginals)
        total_rounding_error = int(np.sum(rounding_error[0]))

    # Final checks
    if np.sum(compute_rounding_error(rounded_data, marginals)[0]) != 0:
        raise ValueError
    if np.any(np.isnan(rounded_data)):
        raise ValueError
    if np.any(rounded_data < 0):
        raise ValueError

    return rounded_data


def nd_controlling_pulp_solver(
    data: np.ndarray, marginals: list[np.ndarray]
) -> np.ndarray:
    """Round the input data such that marginals exact match, using the PuLP solver

    Args:
        data: The data to be rounded. This should be the output of an IPF procedure
        marginals: The marginals to control to

    Returns:
        The rounded data
    """
    check_input_validity(data, marginals)

    # Very useful constant in this function
    n_dims = len(marginals)

    # Round all values up and compute error
    rounded_data = np.ceil(data)
    rounding_error = compute_rounding_error(rounded_data, marginals)

    # Construct the system of equations (aka the problem) to plug into PuLP
    problem = pulp.LpProblem("test", pulp.LpMinimize)

    # First, loop over all the data, creating PuLP variables for every data point where
    # the following conditions are true:
    # 1. The data point must be non-zero. If the data point is zero, we could decrease
    #    it to a negative value
    # 2. Any rounding error associated with the data point is also non-zero. If all
    #    rounding error is zero, then there is no situation where the data point should
    #    be decreased, so we also shouldn't make a variable

    # WRT point #2, create an ndarray of the same shape of our data that is True if and
    # only if any rounding error is non-zero
    rounding_error_expanded_dim = []
    for dim in range(n_dims):
        missing_dim = tuple(d for d in range(n_dims) if d != dim)
        rounding_error_expanded_dim.append(
            np.expand_dims(rounding_error[dim] != 0, missing_dim)
        )
    has_non_zero_rounding_error = functools.reduce(
        np.logical_or, rounding_error_expanded_dim
    )

    # Combine the result from #2 with the non-zero data points for an ndarray of all
    # valid variables
    valid_variables = has_non_zero_rounding_error & (rounded_data > 0)

    # Now, actually create the variables
    variables_matrix = np.empty_like(rounded_data, dtype=pulp.pulp.LpVariable)
    iterator = np.nditer(valid_variables, flags=["multi_index"])
    for is_valid in iterator:
        if is_valid:
            # According to a test (run only once), using LpBinary is more or less the
            # same for military/prison, but four times slower compared to using
            # LpInteger bounded by [0, min(3, value)] on Other (214 seconds vs 55
            # seconds)

            # # Create a variable under the constraint of LpBinary, which means in the
            # # solution, the variable can only equal zero or one
            # variables_matrix[iterator.multi_index] = pulp.LpVariable(
            #     name=str(iterator.multi_index),
            #     cat=pulp.LpBinary,
            # )

            # Create a variable under the constraint of LpInteger, which means in the
            # solution, the variable can only be an integer. Additionally, lower bound
            # to zero and upper bound to min(3, value). The logic is that a variable
            # with a small value won't be missed if it's set to zero, but we don't want
            # to accidentally zero out large values, so we cap the change at three
            variables_matrix[iterator.multi_index] = pulp.LpVariable(
                name=str(iterator.multi_index),
                lowBound=0,
                upBound=int(np.min((3, rounded_data[iterator.multi_index]))),
                cat=pulp.LpInteger,
            )

    # Now, loop over the marginals, creating equations for each
    for dim in range(n_dims):
        for index in range(len(marginals[dim])):

            # If the marginal is non-zero, then this slice of data has variables which
            # are also non-zero
            if marginals[dim][index] > 0:
                variables_slice = np.take(variables_matrix, indices=index, axis=dim)
                non_zero_variables = variables_slice[variables_slice != None]

                # The sum of the variables must equal to the rounding error of this
                # particular marginal
                equation = (
                    pulp.LpAffineExpression({v: 1 for v in non_zero_variables})
                    == rounding_error[dim][index]
                )

                # Add the equation to the problem
                problem += equation

    # Solve the problem. We use the default built in solver, as some testing has shown
    # that the model construction is the slow part, not the solving. In case you want
    # to test other solvers, take a look at:
    # https://coin-or.github.io/pulp/main/includeme.html#installing-solvers
    problem.solve(pulp.PULP_CBC_CMD(msg=False))

    # Check the status
    if pulp.LpStatus[problem.status] != "Optimal":
        raise ValueError

    # The solution to the problem is stored in the original variables matrix. Convert
    # to a format we can use
    corrections = np.vectorize(lambda var: var.varValue if var is not None else 0)(
        variables_matrix
    )

    # Apply the corrections
    rounded_data = rounded_data - corrections

    # Double check everything worked
    rounding_error = compute_rounding_error(rounded_data, marginals)
    for dim_error in rounding_error:
        if np.sum(dim_error) != 0:
            raise ValueError

    # Return the rounded data
    return rounded_data


def nd_controlling_pulp_solver_2d(
    data: np.ndarray, marginals: list[np.ndarray], solver: str = "PULP_CBC_CMD"
) -> np.ndarray:
    """Round the input data such that marginals exact match, using the PuLP solver

    This function has the additional restriction that data must be exactly two
    dimensional. This reduces the amount of processing necessary in order to create the
    PuLP model, greatly speeding up execution

    Args:
        data: The data to be rounded. This should be the output of an IPF procedure
        marginals: The marginals to control to
        solver: TODO

    Returns:
        The rounded data
    """
    check_input_validity(data, marginals)

    # Additionally ensure that the input data is two dimensional
    if len(data.shape) != 2:
        raise ValueError

    # Validate the solver and make sure it's installed
    if solver not in ["CyLP", "PULP_CBC_CMD", "SCIP_PY", "HiGHS"]:
        raise ValueError("TODO")
    if solver not in pulp.listSolvers(onlyAvailable=True):
        raise ValueError("TODO")

    # Create the solver
    if solver == "CyLP":
        solver = pulp.CYLP(msg=False)
    elif solver == "PULP_CBC_CMD":
        solver = pulp.PULP_CBC_CMD(msg=False)
    elif solver == "SCIP_PY":
        solver = pulp.SCIP(msg=False)
    elif solver == "HiGHS":
        solver = pulp.HiGHS(msg=False)

    # Very useful constant in this function
    n_dims = len(marginals)

    # Round all values up and compute error
    rounded_data = np.ceil(data)
    rounding_error = compute_rounding_error(rounded_data, marginals)

    # Construct the system of equations (aka the problem) to plug into PuLP
    problem = pulp.LpProblem("test", pulp.LpMinimize)

    # First, loop over all the data, creating PuLP variables for every data point where
    # the following conditions are true:
    # 1. The data point must be non-zero. If the data point is zero, we could decrease
    #    it to a negative value
    # 2. Any rounding error associated with the data point is also non-zero. If all
    #    rounding error is zero, then there is no situation where the data point should
    #    be decreased, so we also shouldn't make a variable

    # WRT point #2, create an ndarray of the same shape of our data that is True if and
    # only if any rounding error is non-zero
    rounding_error_expanded_dim = []
    for dim in range(n_dims):
        missing_dim = tuple(d for d in range(n_dims) if d != dim)
        rounding_error_expanded_dim.append(
            np.expand_dims(rounding_error[dim] != 0, missing_dim)
        )
    has_non_zero_rounding_error = functools.reduce(
        np.logical_or, rounding_error_expanded_dim
    )

    # Combine the result from #2 with the non-zero data points for an ndarray of all
    # valid variables
    valid_variables = has_non_zero_rounding_error & (rounded_data > 0)

    # Now, actually create the variables
    variables_matrix = np.empty_like(rounded_data, dtype=pulp.pulp.LpVariable)
    iterator = np.nditer(valid_variables, flags=["multi_index"])
    for is_valid in iterator:
        if is_valid:
            # According to a test (run only once), using LpBinary is more or less the
            # same for military/prison, but four times slower compared to using
            # LpInteger bounded by [0, min(3, value)] on Other (214 seconds vs 55
            # seconds)

            # Create a variable under the constraint of LpBinary, which means in the
            # solution, the variable can only equal zero or one
            # variables_matrix[iterator.multi_index] = pulp.LpVariable(
            #     name=str(iterator.multi_index),
            #     cat=pulp.LpBinary,
            # )

            # Create a variable under the constraint of LpInteger, which means in the
            # solution, the variable can only be an integer. Additionally, lower bound
            # to zero and upper bound to min(3, value). The logic is that a variable
            # with a small value won't be missed if it's set to zero, but we don't want
            # to accidentally zero out large values, so we cap the change at three
            variables_matrix[iterator.multi_index] = pulp.LpVariable(
                name=str(iterator.multi_index),
                lowBound=0,
                upBound=int(np.min((3, rounded_data[iterator.multi_index]))),
                cat=pulp.LpInteger,
            )

    # Now, loop over the marginals, creating equations for each
    for index in range(len(marginals[0])):
        if marginals[0][index] == 0:
            continue
        variables_slice = variables_matrix[index, :]
        non_zero_variables = variables_slice[variables_slice != None]
        problem += (
            pulp.LpAffineExpression({v: 1 for v in non_zero_variables})
            == rounding_error[0][index]
        )
    for index in range(len(marginals[1])):
        if marginals[1][index] == 0:
            continue
        variables_slice = variables_matrix[:, index]
        non_zero_variables = variables_slice[variables_slice != None]
        problem += (
            pulp.LpAffineExpression({v: 1 for v in non_zero_variables})
            == rounding_error[1][index]
        )

    # Solve the problem. We use the default built in solver, as some testing has shown
    # that the model construction is the slow part, not the solving. In case you want
    # to test other solvers, take a look at:
    # https://coin-or.github.io/pulp/main/includeme.html#installing-solvers
    problem.solve(solver)

    # Check the status
    # if pulp.LpStatus[problem.status] != "Optimal":
    #     # raise ValueError
    #     pass

    # The solution to the problem is stored in the original variables matrix. Convert
    # to a format we can use
    corrections = np.vectorize(lambda var: var.varValue if var is not None else 0)(
        variables_matrix
    )

    # Apply the corrections
    rounded_data = rounded_data - corrections

    # Double check everything worked
    rounding_error = compute_rounding_error(rounded_data, marginals)
    for dim_error in rounding_error:
        if np.sum(dim_error) != 0:
            raise ValueError

    # Return the rounded data
    return rounded_data


def nd_controlling_mixed(
    data: np.ndarray,
    marginals: list[np.ndarray],
    seed: int = 42,
    frac: float = 0.5,
    threshold: int = 1000,
) -> np.ndarray:
    """Round the input data to exactly match marginals, using both fuzzy and PuLP

    Functionally, we use fuzzy methodology until the total rounding error is below
    "threshold", as the fuzzy methodology is extremely fast. After we are below the
    input "threshold", we plug the remaining rounding error and equations into the
    PuLP solver, to hopefully get a complete solution

    Args:
        data: The data to be rounded. This should be the output of an IPF procedure
        marginals: The marginals to control to
        seed: A random seed to ensure reproducibility of the stochastic procedure
        frac: The fraction of total rounding error to correct in each iteration
        threshold: A value of total rounding error below which we switch from using
            the stochastic method to the PuLP solver

    Returns:
        The rounded data which exactly matches marginals
    """

    check_input_validity(data, marginals)

    # The random generator for controlling
    gen = np.random.default_rng(seed)

    # Round all values up and compute various residuals
    rounded_data = np.ceil(data)
    rounding_error = compute_rounding_error(rounded_data, marginals)
    total_rounding_error = int(np.sum(rounding_error[0]))

    # Repeat the fuzzy rounding procedure until we hit the threshold
    while total_rounding_error > threshold:
        rounded_data = _nd_controlling_fuzzy_step(
            rounded_data, rounding_error, gen, frac
        )

        # Recompute rounding error
        rounding_error = compute_rounding_error(rounded_data, marginals)
        total_rounding_error = int(np.sum(rounding_error[0]))

    # Then plug the data into the PuLP solver to finish it off
    rounded_data = nd_controlling_pulp_solver(rounded_data, marginals)

    # Return the rounded data
    return rounded_data


def nd_controlling_mixed_safe(
    data: np.ndarray,
    marginals: list[np.ndarray],
    seed: int = 42,
    frac: float = 0.5,
    threshold: int = 1000,
) -> np.ndarray:
    """

    Args:
        data:
        marginals:
        seed:
        frac:
        threshold:

    Returns:

    """

    check_input_validity(data, marginals)

    # The random generator for controlling
    gen = np.random.default_rng(seed)

    # Round all values up and compute various residuals
    rounded_data = np.ceil(data)
    rounding_error = compute_rounding_error(rounded_data, marginals)
    total_rounding_error = int(np.sum(rounding_error[0]))

    # If the total rounding error is already less than the threshold, just plug into the
    # PuLP solver
    if total_rounding_error < threshold:
        return nd_controlling_pulp_solver(data, marginals)

    # Repeat the fuzzy rounding procedure until we either fully solve the integerization
    # or fail
    step = 0
    while total_rounding_error > threshold:

        # Save the data before rounding
        file_path = TEMP_DATA_FOLDER / f"step_{str(step).zfill(2)}.npy"
        np.save(file_path, rounded_data)

        # Attempt to round the data. If it fails, we move on to using the PuLP solver
        try:
            rounded_data = _nd_controlling_fuzzy_step(
                rounded_data, rounding_error, gen, frac
            )
        except ValueError:
            break

        # Recompute rounding error
        rounding_error = compute_rounding_error(rounded_data, marginals)
        total_rounding_error = int(np.sum(rounding_error[0]))

        # Next step
        step += 1

    # If the rounding error is not zero, then the fuzzy controlling didn't work and we
    # need to delegate to PuLP
    if total_rounding_error != 0:
        for back_step in range(step - 1, -1, -1):

            # Get the data associated with this fuzzy step
            file_path = TEMP_DATA_FOLDER / f"step_{str(back_step).zfill(2)}.npy"
            rounded_data = np.load(file_path)

            # See if the PuLP solver can solve the current step
            try:
                rounded_data = nd_controlling_pulp_solver(rounded_data, marginals)
            except ValueError:
                continue

            # The solver worked, so stop looping
            break

    # Final checks
    check_output_validity(rounded_data, marginals)

    # Return the rounded data
    return rounded_data


# Testing
if __name__ == "__main__":
    shape = [24321, 20 * 2 * 7]

    # start_time = time.time()
    # data, marginals = random_data.sparse(shape=[10, 4])
    # rounded_data = nd_controlling_pulp_solver_2d(data, marginals)
    # end_time = time.time()
    # print(f"PuLP solver took {end_time - start_time} seconds")

    # # Running on the AVD using shape = [24321, 20 * 2 * 7] takes 225 seconds
    # start_time = time.time()
    # data, marginals = random_data.sparse(shape=shape)
    # rounded_data = nd_controlling_mixed(data, marginals, threshold=5000)
    # end_time = time.time()
    # print(f"Mixed solver took {end_time - start_time} seconds")
    #
    # # Running on the AVD using shape = [24321, 20 * 2 * 7] takes 271 seconds
    # start_time = time.time()
    # data, marginals = random_data.sparse(shape=shape)
    # rounded_data = nd_controlling_mixed_safe(data, marginals)
    # end_time = time.time()
    # print(f"Mixed Safe solver took {end_time - start_time} seconds")

    # Note, College has an issue where there is at least one marginal greater than zero
    # assoicated with data that is only zero
    for pop_type in [
        # "Group Quarters - College",
        # "Group Quarters - Military",
        # "Group Quarters - Institutional Correctional Facilities",
        "Group Quarters - Other",
        # "Household Population",
    ]:
        # Testing on real data
        data = pd.read_csv(
            ACTUAL_DATA_FOLDER / f"{pop_type}_data.csv",
            index_col=0,
            header=[0, 1, 2],
        ).to_numpy()
        row_controls = pd.read_csv(ACTUAL_DATA_FOLDER / f"{pop_type}_row_controls.csv")[
            "value"
        ].to_numpy()
        column_controls = pd.read_csv(
            ACTUAL_DATA_FOLDER / f"{pop_type}_column_controls.csv"
        )["value"].to_numpy()
        marginals = [row_controls, column_controls]

        # Run through IPF just in case
        post_ipf_data = ipf.ipf_numpy(data, marginals)

        # Run the data through the rounding procedure
        for solver in [
            "CyLP",
            "PULP_CBC_CMD",
            # "SCIP_PY",
            "HiGHS",
        ]:
            start_time = time.time()
            # rounded_data = nd_controlling_mixed_safe(post_ipf_data, marginals)
            # rounded_data = nd_controlling_pulp_solver(post_ipf_data, marginals)
            rounded_data = nd_controlling_pulp_solver_2d(
                post_ipf_data, marginals, solver=solver
            )
            end_time = time.time()
            print(f"{pop_type} using {solver} took {end_time - start_time} seconds")

pass
