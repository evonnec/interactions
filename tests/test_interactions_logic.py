from interactions.lib.interactions_logic import Interaction, Severity, find_interactions

SILDENAFIL_TAMSULOSIN = Interaction(
    drugs=("sildenafil", "tamsulosin"),
    severity=Severity.MODERATE,
    description=(
        "Sildenafil may potentiate the hypotensive effect of alpha blockers, "
        "resulting in symptomatic hypotension in some patients."
    ),
)


class TestFindInteractions:
    def test_drug_not_found(self) -> None:
        result = find_interactions(interactions=[], drugs={"acetaminophen"})
        assert result == []

    def test_interaction_found(self) -> None:
        result = find_interactions(
            interactions=[SILDENAFIL_TAMSULOSIN], drugs={"sildenafil", "tamsulosin"}
        )
        assert result == [SILDENAFIL_TAMSULOSIN]

    def test_only_one_drug_matches(self) -> None:
        result = find_interactions(interactions=[SILDENAFIL_TAMSULOSIN], drugs={"sildenafil"})
        assert result == []

    def test_match_and_others(self) -> None:
        interaction = Interaction(
            drugs=("foo", "bar"),
            severity=Severity.MODERATE,
            description="Disaster.",
        )
        result = find_interactions(interactions=[interaction], drugs={"foo", "bar", "baz"})
        assert result == [interaction]


class TestRankSeverity:
    def test_severity_ordering(self) -> None:
        assert Severity.MAJOR > Severity.MODERATE > Severity.MINOR

    def test_parse(self) -> None:
        assert Severity.parse("major") is Severity.MAJOR
        assert Severity.parse("moderate") is Severity.MODERATE
        assert Severity.parse("minor") is Severity.MINOR

    def test_rank_severity(self) -> None:
        first_major = Interaction(drugs=(), severity=Severity.MAJOR, description="1 major")
        first_moderate = Interaction(drugs=(), severity=Severity.MODERATE, description="1 moderate")
        first_minor = Interaction(drugs=(), severity=Severity.MINOR, description="1 minor")

        second_major = Interaction(drugs=(), severity=Severity.MAJOR, description="2 major")
        second_moderate = Interaction(
            drugs=(), severity=Severity.MODERATE, description="2 moderate"
        )
        second_minor = Interaction(drugs=(), severity=Severity.MINOR, description="2 minor")

        interactions = [
            first_major,
            first_moderate,
            first_minor,
            second_major,
            second_moderate,
            second_minor,
        ]
        # Most severe first; ties keep their original (file) order.
        result = sorted(interactions, key=lambda i: i.severity, reverse=True)
        assert result == [
            first_major,
            second_major,
            first_moderate,
            second_moderate,
            first_minor,
            second_minor,
        ]
