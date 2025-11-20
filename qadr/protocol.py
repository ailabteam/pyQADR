# qadr/protocol.py

"""
This module orchestrates the entire Quantum Anonymous Data Reporting protocol,
coordinating the Participants and the Service Provider.
"""

from typing import List, Dict
import math
import numpy as np
from tqdm import tqdm

from qadr import constants
from qadr.participant import Participant, ReservationStatus
from qadr.service_provider import ServiceProvider
from simulators.qkd_network_simulator import QKDNetwork


class QADRProtocol:
    """
    Manages and executes a complete run of the QADR protocol simulation.
    """

    def __init__(self, num_participants: int, slot_participant_ratio: float):
        """
        Initializes the entire protocol setup.

        Args:
            num_participants (int): The number of participants (n).
            slot_participant_ratio (float): The ratio of slots to participants (gamma = m/n).
        """
        print("="*50)
        print(f"Initializing QADR Protocol Simulation...")
        print(f"  - Participants (n): {num_participants}")
        print(f"  - Slot Ratio (gamma): {slot_participant_ratio}")
        
        self.num_participants = num_participants
        self.participant_ids = list(range(num_participants))
        
        # Calculate the number of slots (m)
        self.num_slots = math.ceil(num_participants * slot_participant_ratio)
        print(f"  - Calculated Slots (m): {self.num_slots}")
        print("="*50)

        # 1. Setup Phase
        self.qkd_network = QKDNetwork(self.participant_ids)
        self.participants = [
            Participant(p_id, self.participant_ids, self.qkd_network)
            for p_id in self.participant_ids
        ]
        self.service_provider = ServiceProvider()
        
        # Store results for analysis
        self.reservation_rounds = 0
        self.final_data_vector = None

    def run_slot_reservation(self) -> bool:
        """
        Executes the iterative slot reservation phase.

        Returns:
            bool: True if reservation was successful, False otherwise.
        """
        print("\n--- Starting Slot Reservation Phase ---")
        
        pending_participants = self.participants.copy()
        successful_participants = []
        
        max_rounds = self.num_participants * 2 # A safe limit to prevent infinite loops
        
        for round_num in range(1, max_rounds + 1):
            self.reservation_rounds += 1
            print(f"\nRound {round_num}: {len(pending_participants)} participants pending.")
            
            if not pending_participants:
                break

            # 1. All pending participants choose a slot and create a masked vector
            masked_vectors = []
            for p in tqdm(pending_participants, desc="Participants preparing vectors"):
                p.generate_new_pseudonym()
                p.choose_slot(self.num_slots)
                vector = p.create_vector(
                    content=p.pseudonym,
                    vector_length=self.num_slots,
                    slot_len_bytes=constants.PSEUDONYM_LENGTH_BYTES
                )
                masked_vectors.append(p.mask_vector(vector))

            # 2. Service Provider aggregates the vectors
            public_vector = self.service_provider.aggregate_vectors(masked_vectors)

            # 3. Participants verify the result
            next_pending_participants = []
            for p in pending_participants:
                p.verify_reservation(public_vector, constants.PSEUDONYM_LENGTH_BYTES)
                if p.reservation_status == ReservationStatus.SUCCESSFUL:
                    successful_participants.append(p)
                else: # COLLIDED or still PENDING
                    next_pending_participants.append(p)
            
            pending_participants = next_pending_participants
            
            if len(successful_participants) == self.num_participants:
                print(f"\n--- Slot Reservation Successful in {self.reservation_rounds} rounds! ---")
                return True

        print(f"\n--- Slot Reservation Failed after {max_rounds} rounds. ---")
        return False
        
    def run_data_submission(self) -> bool:
        """
        Executes the final data submission phase after successful slot reservation.
        """
        print("\n--- Starting Data Submission Phase ---")

        if len([p for p in self.participants if p.reservation_status != ReservationStatus.SUCCESSFUL]) > 0:
            print("Cannot run data submission: Not all participants have a reserved slot.")
            return False

        masked_vectors = []
        for p in tqdm(self.participants, desc="Participants submitting data"):
            # Participant uses their successfully reserved slot
            vector = p.create_vector(
                content=p.message,
                vector_length=self.num_participants, # Vector is now compact
                slot_len_bytes=constants.DEFAULT_MESSAGE_LENGTH_BYTES
            )
            masked_vectors.append(p.mask_vector(vector))
            
        # The SP aggregates the data vectors
        self.final_data_vector = self.service_provider.aggregate_vectors(masked_vectors)
        
        print("\n--- Data Submission Complete! ---")
        # In a real scenario, we would now verify the integrity of the final vector
        return True

    def run(self):
        """
        Executes the full QADR protocol.
        """
        if self.run_slot_reservation():
            self.run_data_submission()
