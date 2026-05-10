# CSMA/CA WLAN Simulator

Interactive dashboard for analyzing MAC mechansim.

---

# Project Overview

This project implements a Python-based CSMA/CA WLAN simulator. The simulator analyzes WLAN MAC-layer performance under different contention window configurations and hidden-node scenarios. The dashboard visualizes network statistics including TXOP, successful transmissions, frame error rate (FER), access delay, and CW frequency distribution.

The project aim to understand:

- MAC protocol analysis
- Hidden-node impact
- IEEE 802.11 contention analysis
  

# Dependencies

Install dependencies using:

```bash
pip install streamlit numpy pandas matplotlib
```

# How to run 

```bash
streamlit run csma_ca_performance_dashboard.py
```

If the dashboard does not open automatically, open:
http://localhost:8501

# Dashboard

![Dashboard](screenshots/dashboard_screenshot.jpg)


# User Input Parameters

  The following input parametrs are required to analyze the performance of CSMA/CA. 

## Number of WLAN Nodes

Defines the total number of contending WLAN nodes 

## Number of Hidden Nodes

Defines how many nodes behave as hidden nodes. Hidden nodes:
- do not defer when the channel is busy
- always sense the channel as idle
- may transmit simultaneously with other nodes

## Total Simulation Time Slots

Defines the total duration of the simulation in time slots. Note that Larger simulation times provid better statistical accuracy

## Frame Transmission Slots

Defines the transmission duration of a frame in time slots.


## Minimum Contention Window (CW Min)

Defines the minimum contention window size.

Currently:
- CW Min is fixed at 31

## Maximum Contention Window (CW Max)

Defines the maximum contention window size.

Supported values:
- 63
- 127
- 255
- 511
- 1023

After collisions:
- the contention window increases exponentially
- CW size is limited by CW Max

---

# Current Assumptions

The current simulator assumes:

- Saturated network conditions
- Every node always has frames ready for transmission
- Equal frame transmission duration for all nodes
- Fixed transmission power
- Single shared wireless channel

---

# Planned Extensions

Future versions of the simulator will include:

- Unsaturated traffic models
- Variable frame sizes
- Adaptive transmission power control
- Dynamic carrier sensing threshold adjustment
- Reinforcement learning based channel contention management

## Contact
For enquiries, support, or suggestions, please feel free to contact:

- huseen0207@outlook.com  

