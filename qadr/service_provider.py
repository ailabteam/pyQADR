# qadr/service_provider.py

"""
This module defines the ServiceProvider class, which acts as the central
aggregator in the QADR protocol.
"""
from typing import List
import numpy as np
import functools

class ServiceProvider:
    """
    Represents the central server that collects and aggregates masked vectors.

    The SP is considered "honest-but-curious": it follows the protocol
    correctly but may try to infer information from the data it observes.
    In this simulation, its role is purely computational.
    """

    def __init__(self):
        """Initializes the ServiceProvider."""
        # The SP is largely stateless for individual rounds.
        pass

    def aggregate_vectors(self, vectors: List[np.ndarray]) -> np.ndarray:
        """
        Aggregates a list of vectors by XORing them all together.

        This is the core function of the DC-Net principle. Since each pad
        is added twice (once by each participant in a pair), they all cancel
        out, leaving the sum of the original unmasked vectors.

        Args:
            vectors (List[np.ndarray]): A list of masked vectors received from
                                       all participants.

        Returns:
            np.ndarray: The final, public aggregated vector.
        """
        if not vectors:
            raise ValueError("Vector list cannot be empty.")

        # Ensure all vectors have the same shape
        first_vector_shape = vectors[0].shape
        if not all(v.shape == first_vector_shape for v in vectors):
            raise ValueError("All vectors must have the same shape for aggregation.")

        # Use functools.reduce for a concise and efficient way to apply
        # the XOR operation cumulatively across all vectors in the list.
        # It's equivalent to:
        # result = vectors[0]
        # for i in range(1, len(vectors)):
        #     result = np.bitwise_xor(result, vectors[i])
        
        aggregated_vector = functools.reduce(np.bitwise_xor, vectors)
        
        return aggregated_vector
