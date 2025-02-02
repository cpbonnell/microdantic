"""
This is a test suite for microdantic.

It is done as a regular Python script rather than using a testing framework
because the tests need to be easily run on a microcontroller running
MicroPython as well as on a regular computer running CPython.

Embedded Python implementations like Circuit Python often automatically run
a file named main.py when the device is powered on. This makes it easy to
run the tests on a device by simply copying this file together with
microdantic.py to the device. The tests can be run on the host machine by
running `poetry run tests` inside the project directory.
"""

import time

from microdantic import Field, BaseModel, Validations


class Fruit(BaseModel):
    name: str = Field(str)
    quantity = 10
    weight: float = 1.0


Fruit.register_class()

is_even = Validations.UserSuppliedLambda(lambda x: x % 2 == 0, "Value must be even")


class ModelWithValidations(BaseModel):
    even_int = Field(int, default=0, validations=[is_even])
    optional_positive_float = Field(
        float, default=1.0, required=False, validations=[Validations.GreaterThan(0)]
    )


ModelWithValidations.register_class()


def test_construction_and_default_values():
    print("...default apple")
    default_apple = Fruit(name="apple")
    assert default_apple.name == "apple"
    assert default_apple.quantity == 10
    assert default_apple.weight == 1.0
    assert type(default_apple.name) == str
    assert type(default_apple.quantity) == int
    assert type(default_apple.weight) == float

    print("...alternate apple")
    alternate_apple = Fruit(name="apple", quantity=5, weight=5.0)
    assert alternate_apple.name == "apple"
    assert alternate_apple.quantity == 5
    assert alternate_apple.weight == 5.0


def test_validations():

    # Assign some values that should pass validation
    mod = ModelWithValidations()

    print("...valid assignments to required_even_int")
    mod.even_int = 2
    assert mod.even_int == 2
    mod.even_int = -4
    assert mod.even_int == -4

    print("...valid assignments to optional_positive_float")
    mod.optional_positive_float = 3.5
    assert mod.optional_positive_float == 3.5
    mod.optional_positive_float = 0.5
    assert mod.optional_positive_float == 0.5
    mod.optional_positive_float = None
    assert mod.optional_positive_float is None

    print("...error raised on assignment 'mod.required_even_int = 3.0'")
    try:
        mod.even_int = 3.0
    except ValueError as e:
        error_text = e.args[0]
        assert "Failed the following validations:" in error_text
        assert "-- Value must be of type <class 'int'>" in error_text
        assert "-- Value must be even" in error_text

    print("...error raised on assignment 'mod.required_even_int = None'")
    try:
        mod.even_int = None
    except ValueError as e:
        error_text = e.args[0]
        assert "Failed the following validations:" in error_text
        assert "-- Value must not be None" in error_text

    print("...error raised on assignment 'mod.optional_positive_float = -2'")
    try:
        mod.optional_positive_float = -2
    except ValueError as e:
        error_text = e.args[0]
        assert "Failed the following validations:" in error_text
        assert "-- Value must be of type <class 'float'>" in error_text
        assert "-- Value must be greater than 0" in error_text


def run_tests():
    print("==================== Beginning Test Suite ====================")
    tests_to_run = {
        name: obj for name, obj in globals().items() if name.startswith("test_")
    }

    for name, executable in tests_to_run.items():
        if not callable(executable):
            print(f"Symbol {name} is not callable. Skipping execution.")

        print(f"===== Running {name} =====")
        start = time.monotonic()
        executable()
        end = time.monotonic()

        print(f"...test runtime was {(end-start)*1000:.3f} ms")


if __name__ == "__main__":
    run_tests()
