from api.main import get_similarity_score


def test_identical_questions_have_high_similarity():
    assert get_similarity_score("营业时间是什么", "营业时间是什么") > 0.9


def test_similar_questions_score_higher_than_unrelated_questions():
    similar = get_similarity_score("餐厅几点营业", "你们营业时间是什么")
    unrelated = get_similarity_score("餐厅几点营业", "怎么预订座位")

    assert similar > unrelated


def test_empty_questions_do_not_raise_error():
    score = get_similarity_score("", "")

    assert score == 0