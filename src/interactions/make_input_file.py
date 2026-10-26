"""Print a large sample input file (1000 identical lines) to STDOUT."""

STRING_OF_DRUGS = (
    "sildenafil tamsulosin nitroglycerin nicotine lovastatin enflurane rescinnamine "
    "enalaprilat nicardipine echinacea norethisterone meloxicam thiamylal benzylpenicillin "
    "guanoxan grepafloxacin lofexidine guanoclor norgestimate cyclopenthiazide"
)


def main() -> None:
    for _ in range(1000):
        print(STRING_OF_DRUGS)


if __name__ == "__main__":
    main()
