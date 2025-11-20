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


    # Trong file qadr/protocol.py

    # ... (các phần import và __init__ giữ nguyên) ...

    # Trong file qadr/protocol.py

    # ... (các phần import và __init__ giữ nguyên) ...

    def run_slot_reservation(self) -> bool:
        """
        Executes the iterative slot reservation phase. (Version 2 - Simplified & Corrected)
        """
        print("\n--- Starting Slot Reservation Phase ---")
        
        pending_participants = self.participants.copy()
        successful_participants = []
        occupied_slots = set()

        max_rounds = self.num_participants * 2
        
        for round_num in range(1, max_rounds + 1):
            self.reservation_rounds += 1
            print(f"\nRound {round_num}: {len(pending_participants)} participants pending.")
            
            if not pending_participants:
                break # All participants are successful

            # 1. Determine available slots for this round
            available_slots = [i for i in range(self.num_slots) if i not in occupied_slots]
            if len(available_slots) < len(pending_participants):
                 print(f"Error: Not enough available slots ({len(available_slots)}) for pending participants ({len(pending_participants)}).")
                 return False

            # 2. Each pending participant chooses a slot and creates a masked vector
            masked_vectors = []
            for p in tqdm(pending_participants, desc=f"Round {round_num} vector prep"):
                p.reservation_status = ReservationStatus.PENDING # Reset status
                p.generate_new_pseudonym()
                p.chosen_slot_index = np.random.choice(available_slots)
                
                vector = p.create_vector(
                    content=p.pseudonym,
                    vector_length=self.num_slots,
                    slot_len_bytes=constants.PSEUDONYM_LENGTH_BYTES
                )
                masked_vectors.append(p.mask_vector(vector))

            # 3. Service Provider aggregates vectors from PENDING participants only
            public_vector = self.service_provider.aggregate_vectors(masked_vectors)

            # 4. Pending participants verify the result
            next_pending_participants = []
            newly_successful_this_round = []
            for p in pending_participants:
                p.verify_reservation(public_vector, constants.PSEUDONYM_LENGTH_BYTES)
                if p.reservation_status == ReservationStatus.SUCCESSFUL:
                    # Check for a new type of collision: two pending users chose the same available slot
                    if p.chosen_slot_index in occupied_slots:
                        # This should not happen if available_slots logic is correct
                        print(f"CRITICAL LOGIC ERROR: Participant {p.id} chose an already occupied slot {p.chosen_slot_index}.")
                        p.reservation_status = ReservationStatus.COLLIDED
                        next_pending_participants.append(p)
                    else:
                        newly_successful_this_round.append(p)
                        occupied_slots.add(p.chosen_slot_index)
                else: # COLLIDED
                    next_pending_participants.append(p)
            
            successful_participants.extend(newly_successful_this_round)
            pending_participants = next_pending_participants
            
            if not pending_participants:
                print(f"\n--- Slot Reservation Successful in {self.reservation_rounds} rounds! ---")
                # Assign final, compact slot indices for the data submission phase
                successful_participants.sort(key=lambda p: p.id)
                for i, p in enumerate(successful_participants):
                    p.chosen_slot_index = i
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
        # --- SỬA LỖI: Sử dụng tqdm cho self.participants ---
        for p in tqdm(self.participants, desc="Participants submitting data"):
            # Participant uses their successfully reserved slot index which was re-assigned
            # at the end of the reservation phase to be compact (0, 1, ..., n-1)
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
