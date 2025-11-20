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

    def run_slot_reservation(self) -> bool:
        """
        Executes the iterative slot reservation phase.

        Returns:
            bool: True if reservation was successful, False otherwise.
        """
        print("\n--- Starting Slot Reservation Phase ---")
        
        # --- SỬA LỖI: Bắt đầu từ đây ---
        pending_participants = self.participants.copy()
        successful_participants = []
        
        # Tập hợp các chỉ số slot đã được chiếm thành công
        occupied_slots = set()

        max_rounds = self.num_participants * 2 
        
        for round_num in range(1, max_rounds + 1):
            self.reservation_rounds += 1
            print(f"\nRound {round_num}: {len(pending_participants)} participants pending.")
            
            if not pending_participants:
                break

            # Danh sách các slot còn trống cho vòng này
            available_slots = [i for i in range(self.num_slots) if i not in occupied_slots]
            if not available_slots and pending_participants:
                print("Error: No available slots left but participants are still pending.")
                return False

            # 1. Những người thành công ở vòng trước phải "tham gia" lại
            #    để che mặt nạ, nhưng họ không chọn slot mới.
            masked_vectors = []
            for p in successful_participants:
                # Họ phải tạo lại vector với bút danh cũ và slot cũ để bảo toàn tổng XOR
                # Hoặc một cách đơn giản hơn, ta chỉ cần những người pending tham gia
                # Đây là một điểm tinh tế trong bài báo, chúng ta sẽ chọn cách đơn giản hơn
                # để mô phỏng: Chỉ những người pending mới gửi vector.
                # Bài báo gốc nói "All n participants establish fresh keys and generate new SRMs"
                # để chống traffic analysis. Chúng ta sẽ làm theo cách này.
                pass # Sẽ xử lý tất cả participant ở vòng lặp dưới

            # THE CORRECT APPROACH ACCORDING TO THE PAPER
            # "Successful Participants resubmit their new SRM to the same slot they previously won."
            # "Colliding Participants choose a new random slot from the set of slots that contained '0'"
            all_participants_this_round = self.participants

            masked_vectors = []
            
            # Sử dụng tqdm cho tất cả participants để đồng bộ
            for p in tqdm(all_participants_this_round, desc=f"Round {round_num} vector prep"):
                
                # Logic cho participant đã thành công
                if p.reservation_status == ReservationStatus.SUCCESSFUL:
                    p.generate_new_pseudonym() # Bút danh mới
                    # KHÔNG chọn slot mới, vẫn giữ slot cũ
                
                # Logic cho participant đang chờ hoặc bị va chạm
                else: # PENDING or COLLIDED
                    p.reservation_status = ReservationStatus.PENDING # Reset status
                    p.generate_new_pseudonym()
                    # Chọn từ các slot còn trống
                    chosen_slot = np.random.choice(available_slots)
                    p.chosen_slot_index = chosen_slot

                vector = p.create_vector(
                    content=p.pseudonym,
                    vector_length=self.num_slots,
                    slot_len_bytes=constants.PSEUDONYM_LENGTH_BYTES
                )
                masked_vectors.append(p.mask_vector(vector))


            # 2. Service Provider aggregates the vectors
            public_vector = self.service_provider.aggregate_vectors(masked_vectors)

            # 3. Participants verify the result and update lists for next round
            successful_participants = []
            pending_participants = []
            newly_occupied_slots_this_round = set()

            for p in all_participants_this_round:
                # Chỉ những người chưa thành công mới cần xác minh lại
                if p.reservation_status != ReservationStatus.SUCCESSFUL:
                    p.verify_reservation(public_vector, constants.PSEUDONYM_LENGTH_BYTES)

                if p.reservation_status == ReservationStatus.SUCCESSFUL:
                    successful_participants.append(p)
                    # Thêm slot của người vừa thành công vào tập đã chiếm
                    if p.chosen_slot_index is not None:
                        newly_occupied_slots_this_round.add(p.chosen_slot_index)
                else:
                    pending_participants.append(p)
            
            # Kiểm tra xem có ai vừa chiếm phải slot đã có người chiếm trước đó không
            if not newly_occupied_slots_this_round.isdisjoint(occupied_slots):
                print("CRITICAL ERROR: Slot collision detected with already occupied slots!")
                # Đây là một bug trong logic nếu nó xảy ra
            
            occupied_slots.update(newly_occupied_slots_this_round)

            # --- KẾT THÚC SỬA LỖI ---
            
            if len(successful_participants) == self.num_participants:
                print(f"\n--- Slot Reservation Successful in {self.reservation_rounds} rounds! ---")
                # Gán lại slot index cuối cùng cho giai đoạn data submission
                # Sắp xếp theo ID để đảm bảo thứ tự nhất quán
                successful_participants.sort(key=lambda p: p.id)
                for i, p in enumerate(successful_participants):
                    p.chosen_slot_index = i # Gán slot compact 0, 1, 2, ...
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
