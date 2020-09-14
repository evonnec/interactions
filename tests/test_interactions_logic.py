from interactions.lib.interactions_logic import find_interactions, Interaction

class TestFindInteractions:

    def test_drug_not_found(self):
        interactions = []
        drugs = set(['acetaminophen'])
        result = find_interactions(interactions=interactions, drugs=drugs)
        expected = []
        assert result == expected

    def test_interaction_found(self):
        interaction = Interaction(
            drugs=['sildenafil', 'tamsulosin'],
            severity='moderate',
            description="Sildenafil may potentiate the hypotensive effect of alpha blockers, resulting in symptomatic hypotension in some patients.",
        )
        interactions = [interaction]
        drugs = set(['sildenafil', 'tamsulosin'])
        result = find_interactions(interactions=interactions, drugs=drugs)
        expected = [interaction]
        assert result == expected
    
    def test_only_one_drug_matches(self):
        interaction = Interaction(
            drugs=['sildenafil', 'tamsulosin'],
            severity='moderate',
            description="Sildenafil may potentiate the hypotensive effect of alpha blockers, resulting in symptomatic hypotension in some patients.",
        )
        interactions = [interaction]
        drugs = set(['sildenafil'])
        result = find_interactions(interactions=interactions, drugs=drugs)
        expected = []
        assert result == expected

    def test_match_and_others(self):
        interaction = Interaction(
            drugs=['foo', 'bar'],
            severity='moderate',
            description="Disaster.",
        )
        interactions = [interaction]
        drugs = set(['foo', 'bar', 'baz'])
        result = find_interactions(interactions=interactions, drugs=drugs)
        expected = [interaction]
        assert result == expected