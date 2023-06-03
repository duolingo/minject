from class_for_test import AddToNumber


def test_add_to_number():
    add_to_number = AddToNumber(other_number=100)
    result = add_to_number.add_to_number(50)
    assert result == 150
