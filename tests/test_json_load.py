from interactions.lib.interactions_logic import (
    Interaction,
    Severity,
    get_interactions,
    load_interactions_from_list,
)


class TestLoadJson:
    def test_load_interactions_from_list(self) -> None:
        example_input = [
            {
                "drugs": ["sildenafil", "tamsulosin"],
                "severity": "moderate",
                "description": "Description 1.",
            },
            {
                "drugs": ["sildenafil", "nitroglycerin"],
                "severity": "major",
                "description": "Description 2.",
            },
        ]

        result = load_interactions_from_list(json_list=example_input)
        expected_result = [
            Interaction(
                drugs=("sildenafil", "tamsulosin"),
                severity=Severity.MODERATE,
                description="Description 1.",
            ),
            Interaction(
                drugs=("sildenafil", "nitroglycerin"),
                severity=Severity.MAJOR,
                description="Description 2.",
            ),
        ]

        assert result == expected_result

    def test_example(self) -> None:
        drugs = {"sildenafil", "tamsulosin", "valaciclovir"}
        expected_result = [
            Interaction(
                drugs=("sildenafil", "tamsulosin"),
                severity=Severity.MODERATE,
                description=(
                    "Sildenafil may potentiate the hypotensive effect of alpha blockers, "
                    "resulting in symptomatic hypotension in some patients."
                ),
            )
        ]
        result = get_interactions(drugs=drugs)
        assert expected_result == result
