# Utilities to create various random data

import numpy as np
import ipf


def uniform(shape: list[int], seed: int = 42) -> tuple[np.ndarray, list[np.ndarray]]:
    """Creates uniform random data of the specified shape and associated marginals

    Args:
        shape: The shape of the output data
        seed: The seed for the random number generator. Default value of 42 for
            consistent outputs

    Returns:
        (1) The uniform random data of the specified shape
        (2) The marginals associated with the data
    """
    generator = np.random.default_rng(seed)

    # Create our random data
    data = generator.uniform(low=0.25, high=1, size=shape)

    # Assuming the average value of every cell is 10, create random marginals
    total = 10 * np.prod(shape)
    marginals = []
    for size in shape:
        marginal = generator.uniform(0.5, 1, size)
        marginal = (marginal * total / marginal.sum()).round(0).astype(int)
        marginal[0] = total - marginal[1:].sum()
        marginals.append(marginal)
    return ipf.ipf_numpy(data, marginals), marginals


def low_skewed(
    shape: list[int], seed: int = 42, low_threshold: float = 0.1, frac: float = 0.8
) -> tuple[np.ndarray, list[np.ndarray]]:
    """Creates low skewed random data of the specified shape and associated marginals

    Low-skewed data is created by first drawing data from the uniform distribution
    between zero and one. Then, "frac" percentage of values above "low_threshold" are
    replaced with values drawn from the uniform distribution between zero and
    "low_threshold". Functionally, a little over "frac" values will be under the
    threshold, while all other values are in the "low_threshold" to one range.

    Args:
        shape: The shape of the output data
        seed: The seed for the random number generator. Default value of 42 for
            consistent outputs
        low_threshold: TODO
        frac: TODO

    Returns:
        (1) The low-skewed random data of the specified shape
        (2) The marginals associated with the data
    """
    generator = np.random.default_rng(seed)

    # Create our random data
    data = generator.uniform(low=0, high=1, size=shape)
    mask = (data > 0.1) & ~(generator.random(size=shape) > 0.8)
    data[mask] = generator.uniform(low=0, high=0.1, size=np.sum(mask))

    # Assuming the average value of every cell is 10, create random marginals
    total = 10 * np.prod(shape)
    marginals = []
    for size in shape:
        marginal = generator.uniform(0.5, 1, size)
        marginal = (marginal * total / marginal.sum()).round(0).astype(int)
        marginal[0] = total - marginal[1:].sum()
        marginals.append(marginal)
    return ipf.ipf_numpy(data, marginals), marginals


def sparse(
    shape: list[int], seed: int = 42, frac: float = 0.7
) -> tuple[np.ndarray, list[np.ndarray]]:
    """

    Args:
        shape: The shape of the output data
        seed: The seed for the random number generator. Default value of 42 for
            consistent outputs
        frac: TODO

    Returns:
        (1) The random sparse data of the specified shape
        (2) The marginals associated with the data
    """
    generator = np.random.default_rng(seed)

    # Create our random data
    data, _ = uniform(shape)
    mask = ~(generator.random(size=shape) > frac)
    data[mask] = 0

    # Re-do marginals
    marginals = []
    for dim in range(len(shape)):
        missing_dim = tuple(d for d in range(len(shape)) if d != dim)
        marginals.append(data.sum(axis=missing_dim).round(0).astype(int))

    # Fix marginals not summing to the same value
    first_marginal_sum = marginals[0].sum()
    for dim in range(1, len(shape)):
        diff = marginals[dim].sum() - first_marginal_sum
        if diff != 0:
            marginals[dim][np.argmax(marginals[dim])] -= diff

    # Re-do IPF before returning the data
    return ipf.ipf_numpy(data, marginals), marginals
