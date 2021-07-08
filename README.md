# Interactions  
  
### Context  
The company platform enables physicians to diagnose patients and prescribe medications for many common conditions. When prescribing medications, the physicians are constantly looking for a risk known as a drug interaction, which occurs when a patient's response to a drug is affected by factors such as food, supplements, environmental factors, other drugs or disease.  
  
At the company, we dedicate ourselves to ensuring the safety of our patients. Before prescribing any medication, we ask patients to tell us any other drugs they’re currently taking, which allows our physicians to find any potential risks the patient may face by introducing a new medication.  
  
### Problem
Given a file containing a list of drug-drug interactions, write a command line program that accepts a space-separated list of drugs per line and determines if there is a risk of interaction between any drugs in the list.
 
If there are multiple interactions detected for a single line of input, the program should return the most severe interaction. If there are multiple interactions of the same severity, the program should return the interaction that appears first in the interactions.json file.  
  
The program should read its input from STDIN and write its output to STDOUT, where each line of input should generate a line of output in the same order, and with the following format:  
`{SEVERITY}: {interaction message}`  
  
Note: it is important that the program does not output anything other than the result matching the pattern above (such as debugging information). See the examples below for more detail.  
  
#### Examples  
  
Note: all examples are based on the interactions.json file included with this description.

##### Input  
(each line represents one line of input)  

`sildenafil tamsulosin valaciclovir`  
`sildenafil ibuprofen`  
`valaciclovir doxepin ticlopidine ibuprofen`  
  
#### Output  
(order should match the input above)  

`MODERATE: Sildenafil may potentiate the hypotensive effect of alpha blockers, resulting in symptomatic hypotension in some patients.`  
`No interaction`  
`MAJOR: Valaciclovir may decrease the excretion rate of Doxepin which could result in a higher serum level.`  

#### Constraints
Number of medications per line between 1 and 20 Number of lines per execution between 1 and 10,000

## Setup
This requires Python 3.
To install this package, run `pip install .`

## How to use Interactions
Interactions must be run from a directory that includes `interactions.json`
Inputs can be saved in a text file that is piped in to the function `interactions` so:
`interactions < input.txt`
The function will then print out the interaction severity and description that is the highest severity first listed in the file `interactions.json`

## Included Tests
Additionally, there are tests for the interactions logic and for the loading of the json file.
To run the tests, do 
`pip install pytest`
and run `pytest`

## Next Steps
If I had time, I'd add tests for the cli layer.