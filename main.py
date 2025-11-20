# main.py

"""
Main entry point for running a single simulation of the QADR protocol.

This script initializes and runs the protocol with parameters defined in the
`qadr.constants` module or overridden here. It serves as a simple way
to test the end-to-end functionality of the simulation.
"""

import argparse
from qadr.protocol import QADRProtocol
from qadr import constants

def main():
    """
    Parses command-line arguments and runs the QADR simulation.
    """
    # Using argparse to allow for command-line configuration is good practice
    parser = argparse.ArgumentParser(description="Run a QADR protocol simulation.")
    parser.add_argument(
        "-n", "--num_participants",
        type=int,
        default=constants.DEFAULT_NUM_PARTICIPANTS,
        help=f"Number of participants (n). Default: {constants.DEFAULT_NUM_PARTICIPANTS}"
    )
    parser.add_argument(
        "-g", "--gamma",
        type=float,
        default=constants.DEFAULT_SLOT_PARTICIPANT_RATIO,
        help=f"Slot-to-participant ratio (gamma = m/n). Default: {constants.DEFAULT_SLOT_PARTICIPANT_RATIO}"
    )
    args = parser.parse_args()

    # Create an instance of the protocol with the specified parameters
    protocol = QADRProtocol(
        num_participants=args.num_participants,
        slot_participant_ratio=args.gamma
    )

    # Execute the full protocol
    protocol.run()

    # Optional: Basic verification after the run
    if protocol.final_data_vector is not None:
        print("\n--- Basic Verification ---")
        print(f"Simulation finished.")
        print(f"Total reservation rounds: {protocol.reservation_rounds}")
        # In a real test, we would reconstruct the concatenated message string
        # and verify it matches the source messages.
        print("Final vector is available in `protocol.final_data_vector`.")
        print("--- End of Simulation ---")

if __name__ == "__main__":
    # This ensures the main() function is called only when the script is executed directly
    main()
