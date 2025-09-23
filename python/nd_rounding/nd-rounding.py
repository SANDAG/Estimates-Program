# Testing space for various n-dimensional rounding algorithms

import string
import pathlib
import pulp
import time
import numpy as np

import random_data


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
    for dim in range(len(marginals)):
        missing_dim = tuple(d for d in range(len(marginals)) if d != dim)
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
        np.prod(data.shape),
        size=int(np.ceil(int(np.sum(rounding_error[0])) * frac)),
        replace=False,
        p=flat_weight,
    )
    ndarry_indicies = np.unravel_index(flat_indicies, data.shape, order="C")

    # Get the actual corrections to be made
    corrections = np.zeros(data.shape)
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

    # Construct the system of equations to plug into PuLP. This is basically impossible
    # to do with the built-in PuLP functions, so we have to construct the model using
    # raw JSON :(
    model = pulp.LpProblem("nd_controlling_pulp_solver", pulp.LpMinimize).to_dict()

    # First, create the parameters (variables) by iterating though all data. The
    # variable name is just the index of the data point in string form. The "cat" or
    # category is "Binary" since the variable can only be zero or one. Zero indicates
    # no change, and one indicates a correction of -1 to the rounded data
    iterator = np.nditer(rounded_data, flags=["multi_index"])
    for _ in iterator:
        var_name = str(iterator.multi_index)
        model["variables"].append({"name": var_name, "cat": "Binary"})

    # Then, create the equations to solve for the correct amount of rounding error

    # First, set up one equation for every non-zero rounding error along each axis.
    # "coefficients" is where we will store the variables which are part of the
    # equation. "constant" is the negative of the rounding error, since PuLP expects
    # the equation to be in the form of "Ax + By + Cz ... = D", where D is the
    # constant. "sense" is 0 since we want an exact match. "pi" is unused and
    # can be set to None
    equations = {}
    for dim in range(n_dims):
        for index in range(data.shape[dim]):
            equations[f"dim:{dim},index:{index}"] = {
                "coefficients": [],
                "constant": -1 * rounding_error[dim][index],
                "pi": None,
                "sense": 0,
            }

    # Then, iterate through all the data again. Each data point is associated with
    # n_dims equations, one for each axis. There are no weights associated with the
    # variables, since we just want to minimize the total number of corrections without
    # any preference for which data points to correct. Thus, the value is one
    iterator = np.nditer(rounded_data, flags=["multi_index"])
    for value in iterator:
        if value > 0:
            for dim in range(n_dims):
                equations[f"dim:{dim},index:{iterator.multi_index[dim]}"][
                    "coefficients"
                ].append({"name": str(iterator.multi_index), "value": 1})

    # Finally, transofrm the equations dictionary into an actual list of the constraints
    for key, value in equations.items():
        value["name"] = key
        model["constraints"].append(value)

    # Create the model and solve. Note, the PULP_CDC_CMD is the default solver included
    # in the library. No other solvers have been installed or tested, but you can
    # easily do so yourself via:
    # https://coin-or.github.io/pulp/main/includeme.html#installing-solvers
    variables, problem = pulp.LpProblem.from_dict(model)
    problem.solve(pulp.PULP_CBC_CMD(msg=False))

    # Check the status
    if pulp.LpStatus[problem.status] != "Optimal":
        raise ValueError

    # Take the solution and convert it from the PuLP format into a Numpy array
    corrections = np.zeros(shape=data.shape)
    for coordinate, variable in variables.items():
        if variable.varValue != 1:
            continue
        corrections[tuple(map(int, coordinate[1:-1].split(", ")))] = variable.varValue

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

    # Some file I/O stuff for temporary files
    THIS_FOLDER = pathlib.Path(__file__).parent.resolve()
    TEMP_DATA_FOLDER = THIS_FOLDER / "temp_data"
    TEMP_DATA_FOLDER.mkdir(parents=False, exist_ok=True)

    # The random generator for controlling
    gen = np.random.default_rng(seed)

    # Round all values up and compute various residuals
    rounded_data = np.ceil(data)
    rounding_error = compute_rounding_error(rounded_data, marginals)
    total_rounding_error = int(np.sum(rounding_error[0]))

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
shape = [5000, 10, 10]

# start_time = time.time()
# data, marginals = random_data.sparse(shape=shape)
# rounded_data = nd_controlling_pulp_solver(data, marginals)
# end_time = time.time()
# print(f"PuLP solver took {end_time - start_time} seconds")

start_time = time.time()
data, marginals = random_data.sparse(shape=shape)
rounded_data = nd_controlling_mixed(data, marginals)
end_time = time.time()
print(f"Mixed sovler took {end_time - start_time} seconds")

start_time = time.time()
data, marginals = random_data.sparse(shape=shape)
rounded_data = nd_controlling_mixed_safe(data, marginals)
end_time = time.time()
print(f"Mixed Safe sovler took {end_time - start_time} seconds")

pass
