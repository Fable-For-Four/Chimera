import copy

import pytest

from engine.challenge import ATTACK, BACKUP, OWNER, challenge, split_rest


def step(stage, confidence, source="priya.s", inferred=False):
    return {"stage": stage, "confidence": confidence, "from": source, "inferred": inferred}


CHAIN = [
    step("Initial access", 82, source="203.0.113.47"),
    step("Privilege escalation", 70),
    step("Lateral movement", 60, source="svc-backup"),
    step("Collection", 90, source="svc-backup"),
    step("Exfiltration", 88, source="FIN-SRV-02"),
]
SERVICE_ACCOUNTS = {"svc-backup"}


def shares(hypotheses):
    return {h["name"]: h["share"] for h in hypotheses}


def test_attack_takes_the_chain_confidence_and_the_rest_is_split_by_what_each_explains():
    hypotheses, result = challenge(CHAIN, 87, SERVICE_ACCOUNTS)
    assert [h["name"] for h in hypotheses] == [ATTACK, OWNER, BACKUP]
    assert shares(hypotheses) == {ATTACK: 87, OWNER: 6, BACKUP: 7}
    assert result == "2 tested, both weaker"


@pytest.mark.parametrize("confidence", [0, 1, 33, 50, 87, 99, 100])
def test_shares_always_add_to_100(confidence):
    hypotheses, _ = challenge(CHAIN, confidence, SERVICE_ACCOUNTS)
    assert sum(h["share"] for h in hypotheses) == 100
    assert all(h["share"] >= 0 for h in hypotheses)


def test_out_of_range_confidence_is_clamped():
    assert shares(challenge(CHAIN, 140, SERVICE_ACCOUNTS)[0])[ATTACK] == 100
    assert shares(challenge(CHAIN, -5, SERVICE_ACCOUNTS)[0])[ATTACK] == 0


def test_backup_job_explains_nothing_when_a_person_did_the_collection():
    hypotheses, _ = challenge(CHAIN, 87, set())
    assert shares(hypotheses) == {ATTACK: 87, OWNER: 13, BACKUP: 0}
    backup = hypotheses[2]
    assert backup["fits"] == []
    assert "Cannot explain the collection" in backup["breaks"]


def test_split_is_even_when_neither_explanation_explains_anything():
    chain = [step("Privilege escalation", 70), step("Exfiltration", 80)]
    hypotheses, _ = challenge(chain, 75, SERVICE_ACCOUNTS)
    assert shares(hypotheses) == {ATTACK: 75, OWNER: 13, BACKUP: 12}


def test_fits_and_breaks_are_plain_phrases_from_the_stages():
    hypotheses, _ = challenge(CHAIN, 87, SERVICE_ACCOUNTS)
    attack, owner, backup = hypotheses
    assert attack["fits"] == ["All five steps, in order"]
    assert attack["breaks"] == []
    assert owner["fits"] == ["Explains the initial access"]
    assert owner["breaks"] == [
        "Cannot explain the privilege escalation",
        "Cannot explain the lateral movement",
        "Cannot explain the collection",
        "Cannot explain the exfiltration",
    ]
    assert backup["fits"] == ["Explains the collection"]
    assert len(backup["breaks"]) == 4


def test_result_line_names_an_explanation_that_is_not_weaker():
    chain = [step("Initial access", 90), step("Exfiltration", 20)]
    hypotheses, result = challenge(chain, 30, SERVICE_ACCOUNTS)
    assert shares(hypotheses) == {ATTACK: 30, OWNER: 70, BACKUP: 0}
    assert result == f"2 tested, {OWNER.lower()} is not weaker"


def test_result_line_when_neither_is_weaker():
    chain = [step("Initial access", 50), step("Collection", 50, source="svc-backup")]
    _, result = challenge(chain, 20, SERVICE_ACCOUNTS)
    assert result == "2 tested, neither is weaker"


@pytest.mark.parametrize("confidence,expected", [(86.5, 87), (87.5, 88), (86.4, 86)])
def test_a_half_confidence_rounds_up(confidence, expected):
    assert shares(challenge(CHAIN, confidence, SERVICE_ACCOUNTS)[0])[ATTACK] == expected


def test_an_inferred_collection_is_not_explained_by_the_backup_job():
    chain = [
        step("Initial access", 82),
        step("Collection", 41, source="svc-backup", inferred=True),
        step("Exfiltration", 88),
    ]
    backup = challenge(chain, 70, SERVICE_ACCOUNTS)[0][2]
    assert backup["share"] == 0
    assert backup["fits"] == []


def test_attack_fits_says_how_many_steps_were_inferred():
    chain = [
        step("Initial access", 82),
        step("Privilege escalation", 41, inferred=True),
        step("Lateral movement", 60),
    ]
    attack = challenge(chain, 70, SERVICE_ACCOUNTS)[0][0]
    assert attack["fits"] == [
        "All three steps, in order",
        "One of them inferred, not seen in the logs",
    ]


def test_no_chain_gives_no_hypotheses():
    assert challenge([], 0, SERVICE_ACCOUNTS) == ([], "No chain to challenge")


def test_same_input_gives_same_output():
    assert challenge(CHAIN, 87, SERVICE_ACCOUNTS) == challenge(CHAIN, 87, SERVICE_ACCOUNTS)


def test_each_hypothesis_has_exactly_the_contract_keys():
    hypotheses, _ = challenge(CHAIN, 87, SERVICE_ACCOUNTS)
    for h in hypotheses:
        assert set(h) == {"name", "share", "fits", "breaks"}
        assert isinstance(h["share"], int)
        assert isinstance(h["fits"], list)
        assert isinstance(h["breaks"], list)


def test_an_inferred_step_is_listed_as_something_the_innocent_stories_cannot_explain():
    chain = [
        step("Initial access", 80, source="203.0.113.47"),
        step("Lateral movement", 20, inferred=True),
        step("Exfiltration", 70, source="FIN-SRV-02"),
    ]
    hypotheses, _ = challenge(chain, 70, SERVICE_ACCOUNTS)
    attack, owner, backup = hypotheses
    assert attack["fits"][0] == "All three steps, in order"
    assert "Cannot explain the lateral movement" in owner["breaks"]
    assert "Cannot explain the lateral movement" in backup["breaks"]
    assert sum(h["share"] for h in hypotheses) == 100


def test_duplicate_stages_add_their_confidence_and_are_listed_once():
    chain = [step("Initial access", 40), step("Initial access", 60), step("Exfiltration", 50)]
    hypotheses, _ = challenge(chain, 50, SERVICE_ACCOUNTS)
    assert shares(hypotheses) == {ATTACK: 50, OWNER: 50, BACKUP: 0}
    assert hypotheses[1]["fits"] == ["Explains the initial access"]
    assert hypotheses[1]["breaks"] == ["Cannot explain the exfiltration"]


def test_a_step_without_the_inferred_key_still_works():
    chain = [
        {"stage": "Initial access", "confidence": 60, "from": "1.2.3.4"},
        {"stage": "Collection", "confidence": 40, "from": "svc-backup"},
    ]
    hypotheses, _ = challenge(chain, 80, SERVICE_ACCOUNTS)
    assert shares(hypotheses) == {ATTACK: 80, OWNER: 12, BACKUP: 8}


def test_result_line_names_the_backup_job_when_only_it_is_not_weaker():
    chain = [step("Collection", 90, source="svc-backup"), step("Exfiltration", 20)]
    hypotheses, result = challenge(chain, 30, SERVICE_ACCOUNTS)
    assert shares(hypotheses) == {ATTACK: 30, OWNER: 0, BACKUP: 70}
    assert result == f"2 tested, {BACKUP.lower()} is not weaker"


def test_a_float_confidence_is_rounded_and_shares_still_add_to_100():
    low, _ = challenge(CHAIN, 86.4, SERVICE_ACCOUNTS)
    high, _ = challenge(CHAIN, 86.6, SERVICE_ACCOUNTS)
    assert shares(low)[ATTACK] == 86
    assert shares(high)[ATTACK] == 87
    assert sum(shares(low).values()) == 100
    assert sum(shares(high).values()) == 100
    assert all(isinstance(share, int) for share in shares(high).values())


def test_a_confidence_of_100_leaves_nothing_for_the_other_explanations():
    hypotheses, result = challenge(CHAIN, 100, SERVICE_ACCOUNTS)
    assert shares(hypotheses) == {ATTACK: 100, OWNER: 0, BACKUP: 0}
    assert result == "2 tested, both weaker"


@pytest.mark.parametrize(
    "length,words",
    [(2, "two"), (3, "three"), (4, "four"), (5, "five"), (6, "6"), (12, "12")],
)
def test_step_count_is_spelled_out_up_to_five_and_a_number_after(length, words):
    chain = [step("Initial access", 50)] + [step("Exfiltration", 50)] * (length - 1)
    hypotheses, _ = challenge(chain, 60, SERVICE_ACCOUNTS)
    assert hypotheses[0]["fits"] == [f"All {words} steps, in order"]


def test_the_chain_and_service_accounts_are_not_changed():
    chain = copy.deepcopy(CHAIN)
    accounts = set(SERVICE_ACCOUNTS)
    challenge(chain, 87, accounts)
    assert chain == CHAIN
    assert accounts == SERVICE_ACCOUNTS


def test_a_service_account_list_is_accepted_as_well_as_a_set():
    hypotheses, _ = challenge(CHAIN, 87, ["svc-backup"])
    assert shares(hypotheses) == {ATTACK: 87, OWNER: 6, BACKUP: 7}


@pytest.mark.parametrize(
    "rest,weights,expected",
    [(13, [82, 90], [6, 7]), (13, [0, 0], [7, 6]), (0, [5, 5], [0, 0]), (100, [1, 0], [100, 0])],
)
def test_split_rest_uses_largest_remainder(rest, weights, expected):
    assert split_rest(rest, weights) == expected
