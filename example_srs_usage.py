"""Example usage of the SRSTracker class."""
from srs_tracker import SRSTracker

def main():
    # Initialize the tracker
    with SRSTracker() as tracker:
        # Add some initial collocations on day 1
        print("Adding initial collocations...")
        tracker.add_collocations(["special plants", "heavy rain", "strong coffee"], day=1)
        
        # Get due collocations on day 1 (should be empty since we just added them)
        print("\nDue on day 1:")
        for colloc in tracker.get_due_collocations():
            print(f"- {colloc.text} (next review: day {colloc.next_review_day})")
        
        # Simulate waiting until day 2
        print("\nDay 2: Reviewing collocations...")
        due = tracker.get_due_collocations(day=2)
        for colloc in due:
            print(f"Reviewing: {colloc.text}")
            # Mark as reviewed by adding them again
            tracker.add_collocations([colloc.text], day=2)
        
        # Check next review dates
        print("\nNext review dates after day 2:")
        for text, colloc in tracker.collocations.items():
            print(f"- {text}: next review on day {colloc.next_review_day}")

if __name__ == "__main__":
    main()
