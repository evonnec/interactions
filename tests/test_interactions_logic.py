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

class TestRankSeverity:

    def test_rank_severity(self):
        first_major = Interaction(drugs=[], severity='major', description='1 major')
        first_moderate = Interaction(drugs=[], severity='moderate', description='1 moderate')
        first_minor = Interaction(drugs=[], severity='minor', description='1 minor')

        second_major = Interaction(drugs=[], severity='major', description='2 major')
        second_moderate = Interaction(drugs=[], severity='moderate', description='2 moderate')
        second_minor = Interaction(drugs=[], severity='minor', description='2 minor')

        interactions = [
            first_major,
            first_moderate,
            first_minor,
            second_major,
            second_moderate,
            second_minor,
        ]
        result = sorted(interactions, reverse=True)
        expected_result = [
            first_major,
            second_major,
            first_moderate,
            second_moderate,
            first_minor,
            second_minor,
        ]
        assert result == expected_result