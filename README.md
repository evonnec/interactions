# Interactions

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