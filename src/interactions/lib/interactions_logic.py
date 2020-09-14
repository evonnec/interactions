

def find_interactions(interactions, drugs):
    result = []
    for interaction in interactions:
        if set(interaction.drugs).issubset(drugs):
            result.append(interaction)
    return result

class Interaction:
    def __init__(self, drugs, severity, description):
        self.drugs = drugs
        self.severity = severity
        self.description = description
