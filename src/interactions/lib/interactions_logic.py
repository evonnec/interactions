
import json

def load_interactions_from_list(json_list):
    result = []
    for item in json_list:
        drugs = item['drugs']
        severity = item['severity']
        description = item['description']
        new_interaction = Interaction(drugs=drugs, severity=severity, description=description)
        result.append(new_interaction)
    return result

def find_interactions(interactions, drugs):
    result = []
    for interaction in interactions:
        if set(interaction.drugs).issubset(drugs):
            result.append(interaction)
    return result

def get_interactions(drugs):
    with open('interactions.json') as f:
        json_list = json.load(f)
    interactions = load_interactions_from_list(json_list)   
    result = find_interactions(interactions=interactions, drugs=drugs) 
    return result


class Interaction:
    def __init__(self, drugs, severity, description):
        self.drugs = drugs
        self.severity = severity
        self.description = description

    def __eq__(self, other):
        if self.drugs == other.drugs and self.severity == other.severity and self.description == other.description:
            return True
        else:
            return False

    def __repr__(self):
        return '<interaction: ' + str(self.drugs) + ', ' + str(self.description) + '>'

    def __lt__(self, other):
        if self.severity == 'major':
            return False
        if other.severity == 'major':
            return True 
        if other.severity == 'moderate' and self.severity == 'minor':
            return True
        return False


