# simulators/qkd_network_simulator.py

"""
This module simulates a fully-connected, peer-to-peer Quantum Key Distribution
(QKD) network.

In a real-world quantum network, establishing these keys would be a complex
physical process. For our simulation, this class abstracts that process away,
focusing on the outcome: providing secure, shared secret keys between any
two participants on demand.
"""

import os
from typing import List, Dict, Tuple
from qadr import constants

class QKDNetwork:
    """
    Manages the generation and storage of pairwise shared secret keys.

    Attributes:
        participant_ids (List[int]): A sorted list of unique participant IDs.
        _keys (Dict[Tuple[int, int], bytes]): A dictionary storing the shared keys.
            The key of the dictionary is a sorted tuple of two participant IDs,
            ensuring that get_key(p1, p2) and get_key(p2, p1) return the same
            secret.
    """

    def __init__(self, participant_ids: List[int]):
        """
        Initializes the QKD network for a given set of participants.

        Args:
            participant_ids (List[int]): A list of unique integer IDs for all
                                         participants in the network.
        """
        if not participant_ids or len(set(participant_ids)) != len(participant_ids):
            raise ValueError("Participant IDs must be a non-empty list of unique integers.")
        
        # Sort IDs for consistent key indexing
        self.participant_ids: List[int] = sorted(participant_ids)
        self._keys: Dict[Tuple[int, int], bytes] = {}
        print("Initializing QKD network and establishing all pairwise keys...")
        self._establish_all_keys()
        print(f"QKD network established for {len(self.participant_ids)} participants. "
              f"Total keys generated: {len(self._keys)}.")

    def _generate_secure_random_key(self) -> bytes:
        """Generates a single cryptographically secure random key."""
        return os.urandom(constants.QKD_KEY_LENGTH_BYTES)

    def _establish_all_keys(self):
        """
        Simulates the establishment of a shared key for every pair of participants.
        
        This is a computationally intensive, one-time setup process.
        """
        num_participants = len(self.participant_ids)
        # Iterate through all unique pairs (i, j) where i < j
        for i in range(num_participants):
            for j in range(i + 1, num_participants):
                p_id1 = self.participant_ids[i]
                p_id2 = self.participant_ids[j]
                
                # The key tuple is always (min_id, max_id) for consistency
                key_tuple = (p_id1, p_id2)
                self._keys[key_tuple] = self._generate_secure_random_key()

    def get_key(self, p_id1: int, p_id2: int) -> bytes:
        """
        Retrieves the pre-established shared secret key between two participants.

        This operation is designed to be highly efficient (O(1) lookup).

        Args:
            p_id1 (int): The ID of the first participant.
            p_id2 (int): The ID of the second participant.

        Returns:
            bytes: The shared secret key.
        
        Raises:
            KeyError: If the key for the given pair of participants does not exist.
            ValueError: If p_id1 and p_id2 are the same.
        """
        if p_id1 == p_id2:
            raise ValueError("A participant cannot have a shared key with itself.")
        
        # Ensure consistent ordering of IDs to match the stored key tuple
        key_tuple = (min(p_id1, p_id2), max(p_id1, p_id2))
        
        try:
            return self._keys[key_tuple]
        except KeyError:
            # This should not happen if initialization is correct
            raise KeyError(f"No shared key found for participants {p_id1} and {p_id2}.")
