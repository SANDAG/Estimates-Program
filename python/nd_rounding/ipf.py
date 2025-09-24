# Testing IPF using Numpy

import timeit

import numpy as np
import ipfn


# Various IPF implementations
def ipf_numpy(
    seed: np.array,
    marginals: list[np.array],
    break_threshold: float = 0.01,
    max_iters: int = 10000,
) -> np.array:

    # Check seed and marginals match
    if len(seed.shape) != len(marginals):
        raise ValueError(
            f"Each dimension of 'seed' must have an associated marginal control ({len(seed.shape)} expected, {len(marginals)} actual)"
        )
    for dim, size in zip(range(len(seed.shape)), seed.shape):
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

    # Check that every non-zero marginal is associated with data that is also non-zero
    for dim in range(len(marginals)):
        missing_dim = tuple(d for d in range(len(marginals)) if d != dim)
        sum_along_axis = seed.sum(axis=missing_dim)
        if np.any((marginals[dim] != 0) & (sum_along_axis == 0)):
            raise ValueError()

    # Run IPF
    axes = np.arange(len(seed.shape))
    for _ in range(max_iters):

        # In this interation of IPF, store the maximum adjustment amount along each
        # dimension
        max_adjustment_factor = np.zeros(len(axes))

        for dim in axes:

            # Compute the current sum of seed data along this dimension
            current_sum = seed.sum(axis=tuple(np.delete(axes, np.where(axes == dim))))

            # Compare the sum with the marginal controls, adjust accordingly
            adjustment_factor = np.divide(
                marginals[dim],
                current_sum,
                out=np.ones_like(current_sum),
                where=current_sum != 0,
            )
            slicer = [None for _ in range(len(axes))]
            slicer[dim] = slice(None, None, None)
            seed = seed * adjustment_factor[tuple(slicer)]

            # Store the adjustment factor so we can break early
            max_adjustment_factor[dim] = np.abs(adjustment_factor - 1).max()

        # If the adjustment factor threshold is passed, stop execution
        if max_adjustment_factor.max() < break_threshold:
            break

    # Return the IPF controlled data
    return seed


# Setup for various test data
def get_data_random(
    shape: list[int], seed: int = 42
) -> tuple[np.array, list[np.array]]:
    generator = np.random.default_rng(seed)

    # Create our random data
    data = generator.uniform(0.25, 1, shape)

    # Assuming the average value of every cell is 10, create random marginals
    total = 10 * np.prod(shape)
    marginals = []
    for size in shape:
        marginal = generator.uniform(0.5, 1, size)
        marginal = (marginal * total / marginal.sum()).round(0).astype(int)
        marginal[0] = total - marginal[1:].sum()
        marginals.append(marginal)
    return data, marginals


# Testing
if __name__ == "__main__":
    n_iterations = 100
    for size in [[2, 5, 10], [20, 2, 7, 24321]]:
        seed, marginals = get_data_random(size)
        print(f"Testing IPF ({size} size, {n_iterations} iterations)")
        print(
            "\t",
            timeit.timeit(
                lambda: ipf_numpy(seed=seed, marginals=marginals), number=n_iterations
            ),
        )
        print(
            "\t",
            timeit.timeit(
                lambda: ipfn.ipfn.ipfn(
                    original=seed,
                    aggregates=marginals,
                    dimensions=[[n] for n in range(len(size))],
                    convergence_rate=0.01,
                ).iteration(),
                number=n_iterations,
            ),
        )
        print()
