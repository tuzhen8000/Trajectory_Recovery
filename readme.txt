This project includes 4 source code files:

1. generateAggregateMobility.py
Function: adding missing points by linear interpolation, and generate aggregated mobility data.

2. intradayRecovery.py
Function: recover intraday individual trajectories from an aggregated dataset by exploiting trajectory continuity.

3. interdayRecovery.py
Function: recover interday individual trajectories by exploiting trajectory daily regularity and uniqueness.

5. computeAccuracy.py
Function: calculate the recovery accuracy and recover error.

All work contained in this package is licensed under the Apache License, Version 2.0. See the include LICENSE file.



Input files:

***Originial trajectory is stored in three files. The sequence of visited base stations <original_base>, the sequence of visiting time <original_time>, and the location of base stations <Baselocation>.***
	1. original_base
	format:
	<#1 baseID of #1 user> <#2 baseID of #1 user> <#3 baseID of #1 user> ...
	<#1 baseID of #2 user> <#2 baseID of #2 user> <#3 baseID of #2 user> ...
	...

	2. original_time:
	format (each time slot corresponding to 30 minutes):
	<#1 timeslotID of #1 user> <#2 timeslotID of #1 user> <#3 timeslotID of #1 user> ...
	<#1 timeslotID of #2 user> <#2 timeslotID of #2 user> <#3 timeslotID of #2 user> ...
	...

	3. Baselocation
	format:
	<longitude of #1 baseID> <latitude of #1 baseID>
	<longitude of #2 baseID> <latitude of #2 baseID>
	...
	
***Pre-calculated information***
	5. baseDistance.pkl:
	A dict, for example there is M unique baseIDs then there are (M-1)*M/2 items
	data[base1-1][base2-1] = dist means the spatial distance between base1 and base2 
	base1(int) should be smaller than base2(int)
	
	6. nextBase.pkl
	A dict, for example there is M unique baseIDs then there are (M-1)*M items
	data[base1-1][base2-1] = base3 means base1 -> base2 -> base3
	when in neighboring two timeslots the records are [base1,base2], then in next timeslot the predicted record is base3
	according to our mobility model 

