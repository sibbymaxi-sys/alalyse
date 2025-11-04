# test_import.py
print("--- Attempting to import get_system_error_details ---")
try:
    from cs_error_definitions import get_system_error_details
    print("--- SUCCESS! Function imported. ---")
    # Let's try calling it with dummy data
    result_cat, result_msg = get_system_error_details("scs_test.log", "Reported Error - 5 (STAT_VAL_SCS_MACHINE_FAULTCAUSE_ILOCK)")
    print(f"--- Test call result: Category='{result_cat}', Message='{result_msg}' ---")

except ImportError as e:
    print(f"--- IMPORT ERROR: {e} ---")
    print("Check if 'cs_error_definitions.py' exists in this directory.")
except Exception as e_other:
    print(f"--- OTHER ERROR during import (maybe syntax error in cs_error_definitions.py?): {e_other} ---")

input("Press Enter to exit...") # Keep console open