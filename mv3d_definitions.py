# mv3d_definitions.py

# Based on SCS_FAULT_CAUSES.pdf
SCS_FAULT_CODES = {
    0: "NONE // all system are up and operational",
    1: "WAITINGFORDEVICES // waiting for hardware to become available",
    2: "DEVICESUNINITIALIZED // devices are not yet initialized",
    3: "KEYPOWEROFF // power key in off position",
    4: "SDB2_FAULT",
    5: "BIT_FAULT",
    6: "DIAG_FAULT",
    7: "DIAG_POST_TIMEOUT",
    8: "SRC_FAILED",
    9: "ISHWFAULTCONDITION // origin of fault specified in subfields...",
    10: "USERREQUESTED // in response to a desired state change",
    11: "SUBSYSTEMMISSING // not all required subsystems are available",
    12: "PASSTHROUGH",
    13: "DCBOFFSET_FAILURE",
    14: "DARKCAL_REQUESTED",
    15: "ENCODERCNT_EXCEEDED // this is not a fault, but normal operation.",
    16: "ESTOP",
    17: "ILOCK",
    18: "HVPS_RAMPUP",
    19: "STANDBY",
    20: "REBOOT",
    21: "WATCHDOG",
    22: "SYSTIC_FAULT",
    23: "ENCODER_FAULT",
    24: "LIGHT_CURTAIN_FAULT",
    25: "GALIL_FAULT",
    26: "ACUVIM_FAULT",
    27: "YASKAWA_FAULT",
    28: "MFORCE_FAULT",
    29: "UPS_FAULT",
    30: "HVPS_FAULT",
    31: "DCB_FAULT",
    32: "SYSTEM_VERIFY_FAULT",
    33: "BMS_ENTRANCE_BAG_JAM",
    34: "BMS_BHS_FAULT",
    35: "SYSTIC_TIMEOUT",
    36: "SDB2_TIMEOUT",
    37: "DCB_TIMEOUT",
    38: "DPP_RTR_DOWN",
    39: "BMS_RTR_DOWN",
    40: "IAC_RTR_DOWN",
    41: "DPP_OPTSTATE_FAULT",
    42: "IAC_OPTSTATE_FAULT",
    43: "INIT_TIMEOUT_FAULT",
    44: "SEASONING_FAILED",
    45: "TRANSIENTS_FAILED",
    46: "ARRAYTESTS_FAILED",
    47: "BMS_SUBSYS_MISSING",
    48: "IAC_SUBSYS_MISSING",
    49: "DPP_SUBSYS_MISSING",
    50: "DIAGS_SUBSYS_MISSING",
    51: "PLC_CONNECTION_LOSS",
    52: "DPP_HIGH_WATERMARK",
    53: "LIGHTCURTAIN_CHANGED",
    54: "CHILLER_FAULT",
    55: "SYSTEMP_AMBIENT",
    56: "SYSTEMP_INLET_BOX",
    57: "SYSTEM_OUTLET_BOX",
    58: "SYSTEMP_SARCOPHAGUS",
    59: "SYSTEMP_COMPUTER_RACK",
    60: "SYSTEMP_ENCODER_MONITOR"
}

# Based on SCC operating States.pdf
SCS_OPERATING_STATES = {
    0: "NOTREADY", 1: "OPERATIONAL", 2: "FAULT", 3: "REBOOT",
    4: "POWERLOSS", 5: "SHUTDOWN", 6: "STANDBY", 7: "DIAG",
    8: "IDLED", 9: "INITIALIZING", 10: "SRC", 11: "DIEBACK",
    12: "SCANUNBLOCKED", 13: "SCANBLOCKED", 14: "WARM_STANDBY",
    15: "COLD_STANDBY", 16: "RESET", 17: "DIEBACKWAITFORMAINBELTSTOP",
    18: "WAITFORPOSTSTART", 19: "POSTCHECK", 20: "WAITFORSYSTEMINITDONE",
    21: "WAITFORMAINBELTSTART", 22: "PASSTHRU", 23: "HIBERNATE",
    24: "STARTUP", 25: "CONNECTING", 26: "DIEBACK_BHS_FAULT",
    27: "BMS_ENTRANCE_BAG_JAM", 28: "SUBSYS_FAULT", 29: "FLUSH_TUNNEL"
}

# Based on PLC Log Glossary in Troubleshooting guide
TD_CODES = {
    "4": "Properly Tracked Bag",
    "6": "Bag Spacing Error",
    "8": "Entrance Misstrack",
    "9": "Exit Misstrack"
}

# Based on PLC Log Glossary in Troubleshooting guide
SD_CODES = {
    "12": "Machine Clear",
    "13": "Bag Not Analysed (BNA)",
    "14": "Machine Reject",
    "15": "Timeout",
    "21": "Level 2 Operator Reject",
    "22": "Level 2 Operator Clear",
    "25": "Level 2 Operator Timeout",
    "31": "Level 3 Operator Reject",
    "32": "Level 3 Operator Clear",
    "35": "Level 3 Operator Timeout"
}