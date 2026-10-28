from mindspar.opponent import parse


def test_three_lines_in_chinese():
    move = parse("答案：1657\n把握：3\n理由：47 × 38 = 1786，減 129。")
    assert (move.answer, move.wager, move.well_formed) == ("1657", 3, True)
    assert move.reason.startswith("47")


def test_three_lines_in_english_with_markdown():
    move = parse("**Answer:** (8 - 2) × 4\n**Confidence:** 2\n- Reason: 6 × 4 = 24")
    assert move.answer == "(8 - 2) × 4"
    assert move.wager == 2
    assert move.reason == "6 × 4 = 24"
    assert move.well_formed


def test_a_missing_confidence_bets_one():
    move = parse("Answer: Cara")
    assert (move.answer, move.wager, move.well_formed) == ("Cara", 1, False)


def test_no_labels_takes_the_whole_reply():
    move = parse("星期五")
    assert (move.answer, move.wager, move.well_formed) == ("星期五", 1, False)


def test_thinking_left_in_the_text_is_dropped():
    move = parse("<think>maybe 12, no 13</think>\nAnswer: 13\nConfidence: 3\nReason: counted twice")
    assert move.answer == "13"
    assert move.wager == 3


def test_the_first_answer_line_wins():
    move = parse("答案：12\n把握：2\n答案：13")
    assert move.answer == "12"


def test_what_the_ai_wrote_is_kept_as_written():
    move = parse("答案：81\n把握：３\n理由：這是 4², 5², 6² 的平方數")
    assert move.wager == 3
    assert "4², 5²" in move.reason
