import json
import itertools

"""
Number of medications per line between 1 and 20 
Number of lines per execution between 1 and 10,000
"""

_INTERACTIONS = None

def retrieve_interactions():
    """
    retrieve json, use global
    """
    global _INTERACTIONS
    if _INTERACTIONS is None:
        with open('interactions.json') as f:
            retrieved_interactions = json.load(f)
        return retrieved_interactions
    else:
        return _INTERACTIONS

# read standard input in, parse line
def input_query(drugs_input):
    pass
# handle drugs not found -- are drugs from input in json? if not, remove from list to form combinations
# in this example, handle case where one or no drugs in json.
def drugs_found(json_blob, input_blob):
    pass
# combinations from 1 to 20, use itertools, return all 2-drug combinations and severities and descriptions
def form_combinations(json_blob, query):
    pass
# rank severities but keep order from the existing json. 
def rank_severities(combo_blob):
    pass
# export standard output, by line, write to output
def output_data(interaction_blob):
    pass
# accumulate results per line and perform all necessary functions in order to take in input and generate output
def interactions(input):
    pass

class TestLogic:

    def case_one(self):
        """
        this case returns the result of the combination of sildenafil and tamsulosin
        """
        input_case_one = 'sildenafil tamsulosin valaciclovir'
        assert interactions(input_case_one) == 'MODERATE: Sildenafil may potentiate the hypotensive effect of alpha blockers, resulting in symptomatic hypotension in some patients.'

    def case_two(self):
        """
        this case `ibuprofen` is not a drug in the json
        """
        input_case_two = 'sildenafil ibuprofen'
        assert interactions(input_case_two) == 'No interaction'

    def case_three(self):
        """
        this case returns the first major severity found which is between valaciclovir and doxepin
        """
        input_case_three = 'valaciclovir doxepin ticlopidine ibuprofen'
        assert interactions(input_case_three) == 'MAJOR: Valaciclovir may decrease the excretion rate of Doxepin which could result in a higher serum level.'