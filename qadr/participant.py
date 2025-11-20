# qadr/participant.py

"""
This module defines the Participant class, representing a single user in the
QADR network.
"""

import os
from enum import Enum, auto
from typing import List, Optional

import numpy as np

from qadr import constants
from crypto.qs_prf import qs_prf
from simulators.qkd_network_simulator import QKDNetwork

class ReservationStatus(Enum):
    """Enumeration for the participant's status during slot reservation."""
    PENDING = auto()      # Has not yet attempted or is in a collided state
    SUCCESSFUL = auto()   # Has successfully reserved a slot
    COLLIDED = auto()     # Attempted to reserve a slot but a collision occurred

class Participant:
    """
    Represents a single participant in the anonymous data reporting protocol.

    Each participant has a unique ID, holds a message to be sent, and manages
    its state throughout the protocol execution.
    """

    def __init__(self, p_id: int, all_participant_ids: List[int], qkd_network: QKDNetwork):
        """
        Initializes a Participant.

        Args:
            p_id (int): The unique identifier for this participant.
            all_participant_ids (List[int]): A list of all participant IDs in the
                                             current protocol run.
            qkd_network (QKDNetwork): The simulated QKD network instance to get keys from.
        """
        self.id: int = p_id
        self.message: bytes = os.urandom(constants.DEFAULT_MESSAGE_LENGTH_BYTES)
        
        # Other participants' IDs are needed to generate masking pads
        self.other_participant_ids: List[int] = [pid for pid in all_participant_ids if pid != self.id]
        self.qkd_network: QKDNetwork = qkd_network

        # State for slot reservation
        self.reservation_status: ReservationStatus = ReservationStatus.PENDING
        self.pseudonym: Optional[bytes] = None
        self.chosen_slot_index: Optional[int] = None

    def generate_new_pseudonym(self) -> None:
        """Generates a new, random pseudonym for the slot reservation phase."""
        self.pseudonym = os.urandom(constants.PSEUDONYM_LENGTH_BYTES)
        
    def choose_slot(self, num_available_slots: int) -> int:
        """

        Randomly selects a slot index.

        Args:
            num_available_slots (int): The total number of slots available (m).

        Returns:
            int: The chosen slot index.
        """
        self.chosen_slot_index = np.random.randint(0, num_available_slots)
        return self.chosen_slot_index

    def create_vector(self, content: bytes, vector_length: int, slot_len_bytes: int) -> np.ndarray:
        """
        Creates a numpy vector with the given content placed in the chosen slot.

        Args:
            content (bytes): The payload to place in the slot (e.g., pseudonym or message).
            vector_length (int): The total number of slots in the vector (m).
            slot_len_bytes (int): The size of each slot in bytes.

        Returns:
            np.ndarray: A 1D numpy array of uint8 representing the vector.
        """
        if self.chosen_slot_index is None:
            raise RuntimeError("Must choose a slot before creating a vector.")
        
        total_vector_size_bytes = vector_length * slot_len_bytes
        # Initialize a vector of zeros
        vector = np.zeros(total_vector_size_bytes, dtype=np.uint8)
        
        # Convert content to numpy array
        content_array = np.frombuffer(content, dtype=np.uint8)
        
        # Calculate start and end positions for the content
        start_index = self.chosen_slot_index * slot_len_bytes
        end_index = start_index + len(content_array)

        # Place the content into the vector
        vector[start_index:end_index] = content_array
        
        return vector

    def mask_vector(self, vector: np.ndarray) -> np.ndarray:
        """
        Masks a vector by XORing it with pads generated from shared QKD keys.

        Args:
            vector (np.ndarray): The original, unmasked vector.

        Returns:
            np.ndarray: The masked vector, ready for submission.
        """
        masked_vector = vector.copy()
        
        for other_pid in self.other_participant_ids:
            # Retrieve the shared key
            shared_key = self.qkd_network.get_key(self.id, other_pid)
            
            # Generate the pseudorandom pad using the QS-PRF
            pad_bytes = qs_prf(shared_key, len(masked_vector))
            pad_array = np.frombuffer(pad_bytes, dtype=np.uint8)
            
            # Apply the mask using bitwise XOR
            np.bitwise_xor(masked_vector, pad_array, out=masked_vector)
            
        return masked_vector

    def verify_reservation(self, public_vector: np.ndarray, slot_len_bytes: int) -> None:
        """
        Checks the public reservation vector to determine if the slot was won.

        Args:
            public_vector (np.ndarray): The final aggregated vector from the SP.
            slot_len_bytes (int): The size of each slot in bytes.
        """
        if self.chosen_slot_index is None or self.pseudonym is None:
            # This participant didn't participate in this round
            return

        start_index = self.chosen_slot_index * slot_len_bytes
        end_index = start_index + constants.PSEUDONYM_LENGTH_BYTES
        
        # Extract the content from the chosen slot in the public vector
        slot_content = public_vector[start_index:end_index].tobytes()

        if slot_content == self.pseudonym:
            self.reservation_status = ReservationStatus.SUCCESSFUL
            # print(f"Participant {self.id} successfully reserved slot {self.chosen_slot_index}")
        else:
            self.reservation_status = ReservationStatus.COLLIDED
            # print(f"Participant {self.id} detected a collision in slot {self.chosen_slot_index}")
