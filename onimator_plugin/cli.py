#!/usr/bin/env python3
import sys

def main():
    print("Welcome to the Onimator Plugin CLI Tool!")
    print("Please choose an operation:")
    print("1. Update Sources")
    print("2. Schedule Content")
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == "1":
        from update_sources.update_targets import main as update_sources_main
        update_sources_main()
    elif choice == "2":
        from content_scheduler.post_inserter import main as schedule_content_main
        schedule_content_main()
    else:
        print("Invalid selection. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()

