"""
MIT License

Copyright (c) 2025 Christian P. Bonnell

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
===============================================================================

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

import json
import time

from microdantic import (
    BaseModel,
    Field,
    Literal,
    Union,
    ValidationError,
    Validations,
    register,
)


# ========== Overhead Code Used in Tests ==========
@register
class Fruit(BaseModel):
    __auto_serialize_class_name__ = False
    name: str = Field(str)
    quantity = 10
    weight: float = 1.0


@register
class FruitSalad(BaseModel):
    __auto_serialize_class_name__ = False
    ingredient_1 = Field(Fruit)
    ingredient_2 = Field(Fruit)


is_even = Validations.Validator(lambda x: x % 2 == 0, "Value must be even")


@register
class ModelWithValidations(BaseModel):
    __auto_serialize_class_name__ = False
    even_int = Field(int, default=0, validations=[is_even])
    optional_positive_float = Field(
        float, default=1.0, required=False, validations=[Validations.GreaterThan(0)]
    )
    set_of_values = Field(int, default=1, validations=[Validations.OneOf([1, 2, 3])])
    max_len_string = Field(str, default="abc", validations=[Validations.MaxLen(10)])


u = Union[int, float]
l = Literal["apple", "banana"]


@register
class ModelWithSpecialTypes(BaseModel):
    union_field = Field(u)
    literal_field = Field(l)
    string_literal_with_default_field = Field(Literal["apple"], default="apple")
    int_literal_with_default_value = Field(Literal[1], default=1)


@register
class ModelWithDefaultSpecialTypes(BaseModel):
    union_field = Field(u, default=3)
    literal_field = Field(l, default="banana")


@register
class NestedModelA(BaseModel):
    internal_key = Field(Literal["A"], default="A")
    payload = Field(str, default="AAA")


@register
class NestedModelB(BaseModel):
    internal_key = Field(Literal["B"], default="B")
    payload = Field(str, default="BBB")


@register
class ModelWithNestedUnion(BaseModel):
    nested_model = Field(Union[NestedModelA, NestedModelB])


@register
class DiscriminatedModelA(BaseModel):
    __auto_serialize_class_name__ = False
    internal_key = Field(Literal["A"], default="A")
    payload = Field(str, default="AAA")


@register
class DiscriminatedModelB(BaseModel):
    __auto_serialize_class_name__ = False
    internal_key = Field(Literal["B"], default="B")
    payload = Field(str, default="BBB")


@register
class ModelWithDiscriminatedUnion(BaseModel):
    __auto_serialize_class_name__ = False
    nested_model = Field(
        Union[DiscriminatedModelA, DiscriminatedModelB], discriminator="internal_key"
    )


@register
class ModelWithMethod(BaseModel):
    a: int = Field(int)
    b: int = Field(int)

    @property
    def highest(self):
        return max(self.a, self.b)

    def get_highest(self):
        return max(self.a, self.b)


# ========== Test Functions ==========
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

    print("...valid assignments to required_even_int")
    mod.set_of_values = 3
    assert mod.set_of_values == 3
    mod.set_of_values = 2
    assert mod.set_of_values == 2

    print("...valid assignments to max_len_string")
    mod.max_len_string = "a"
    assert mod.max_len_string == "a"
    mod.max_len_string = "abcdefghij"
    assert mod.max_len_string == "abcdefghij"

    VALIDATION_ERROR_PREABLE = "The following validations failed"
    print("...error raised on assignment 'mod.required_even_int = 3.0'")
    try:
        mod.even_int = 3.0
    except ValidationError as e:
        error_text = str(e)
        assert VALIDATION_ERROR_PREABLE in error_text
        assert "-- Value must be of type <class 'int'>" in error_text
        assert "-- Value must be even" in error_text

    print("...error raised on assignment 'mod.required_even_int = None'")
    try:
        mod.even_int = None
    except ValidationError as e:
        error_text = str(e)
        assert VALIDATION_ERROR_PREABLE in error_text
        assert "-- Value must not be None" in error_text

    print("...error raised on assignment 'mod.optional_positive_float = -2'")
    try:
        mod.optional_positive_float = -2
    except ValidationError as e:
        error_text = str(e)
        assert VALIDATION_ERROR_PREABLE in error_text
        assert "-- Value must be of type <class 'float'>" in error_text
        assert "-- Value must be greater than 0" in error_text

    print("...error raised on assignment 'mod.set_of_values = 4'")
    try:
        mod.set_of_values = 4
    except ValidationError as e:
        error_text = str(e)
        assert VALIDATION_ERROR_PREABLE in error_text
        assert "-- Value must be one of" in error_text

    print("...error raised on assignment 'mod.max_len_string = 'abcdefghijk'")
    try:
        mod.max_len_string = "abcdefghijk"
    except ValidationError as e:
        error_text = str(e)
        assert VALIDATION_ERROR_PREABLE in error_text
        assert "-- Value must have length less than or equal to 10" in error_text


def test_repr():
    print("...repr")
    fa = Fruit(name="apple", quantity=5, weight=5.0)
    fb = Fruit(name="banana", quantity=10, weight=1.0)
    assert repr(fa) == "Fruit(name='apple', quantity=5, weight=5.0)"
    assert repr(fb) == "Fruit(name='banana', quantity=10, weight=1.0)"

    fs = FruitSalad(ingredient_1=fa, ingredient_2=fb)
    assert repr(fs) == f"FruitSalad(ingredient_1={repr(fa)}, ingredient_2={repr(fb)})"


def test_serialization_methods():
    # Note: The *_jsonb methods call the *_json methods, which call the
    # base methods. So calling the *_jsonb methods is sufficient to test
    # all serialization methods.

    print("...model_dump")
    f = Fruit(name="apple", quantity=5, weight=5.0)
    jsonb_data = f.model_dump_jsonb()
    data = json.loads(jsonb_data.decode("utf-8"))
    assert data == {"name": "apple", "quantity": 5, "weight": 5.0}

    print("...model_validate")
    ff = Fruit.model_validate_jsonb(jsonb_data)
    assert ff.name == "apple"
    assert ff.quantity == 5
    assert ff.weight == 5.0


def test_recursive_serialization():
    print("...recursive serialization")
    fs = FruitSalad(ingredient_1=Fruit(name="apple"), ingredient_2=Fruit(name="banana"))

    data = fs.model_dump()
    fs2 = FruitSalad.model_validate(data)
    assert isinstance(fs2, FruitSalad)
    assert isinstance(fs2.ingredient_1, Fruit)
    assert isinstance(fs2.ingredient_2, Fruit)
    assert fs2.ingredient_1.name == "apple"
    assert fs2.ingredient_2.name == "banana"


def test_special_types():

    print("...Union")
    assert u.instancecheck(3)
    assert u.instancecheck(3.0)
    assert not u.instancecheck("3")
    assert not u.instancecheck(None)

    print("...Literal")
    assert l.instancecheck("apple")
    assert l.instancecheck("banana")
    assert not l.instancecheck("orange")


def test_special_type_fields():
    print("... special types in field with initial values")

    m = ModelWithSpecialTypes(union_field=3, literal_field="apple")
    assert m.union_field == 3
    assert m.literal_field == "apple"

    print("...special types in field with default values")

    m = ModelWithDefaultSpecialTypes()
    assert m.union_field == 3

    print("...Error when assigning invalid value to Union field")
    incorrect_union_error_raised = False
    try:
        m.union_field = "3"
    except ValidationError as e:
        error_text = str(e)
        assert "-- Value must be of type Union[" in error_text
        incorrect_union_error_raised = True

    assert incorrect_union_error_raised

    print("...Error when assigning invalid value to Literal field")
    incorrect_literal_error_raised = False
    try:
        m.literal_field = "orange"
    except ValidationError as e:
        error_text = str(e)
        assert "-- Value must be of type Literal[" in error_text
        incorrect_literal_error_raised = True

    assert incorrect_literal_error_raised

    print("...Error when defining a literal field with invalid default value")
    invalid_default_literal_error_raised = False
    try:

        @register
        class ModelWithInvalidLiteralDefault(BaseModel):
            literal_field = Field(l, default="orange")

    except ValidationError as e:
        error_text = str(e)
        assert "-- Value must be of type Literal[" in error_text
        invalid_default_literal_error_raised = True

    assert invalid_default_literal_error_raised


def test_nested_union():

    print("...Instantiate nested union")
    ma = ModelWithNestedUnion(nested_model=NestedModelA())
    mb = ModelWithNestedUnion(nested_model=NestedModelB())

    print("...Serialize nested union")
    ma_serialized = ma.model_dump()
    mb_serialized = mb.model_dump()

    print("...Deserialize nested union")
    ma_deserialized = ModelWithNestedUnion.model_validate(ma_serialized)
    mb_deserialized = ModelWithNestedUnion.model_validate(mb_serialized)

    assert isinstance(ma_deserialized.nested_model, NestedModelA)
    assert isinstance(mb_deserialized.nested_model, NestedModelB)


def test_is_discriminated_match():
    from microdantic.microdantic import _is_discriminated_match

    print("...Correctly identify matches")
    assert _is_discriminated_match("internal_key", "A", DiscriminatedModelA)
    assert _is_discriminated_match("internal_key", "B", DiscriminatedModelB)

    print("...Reject match because discriminator value does not match")
    assert not _is_discriminated_match("internal_key", "B", DiscriminatedModelA)

    print("...Reject match because discriminator field is not present")
    assert not _is_discriminated_match("non_existent_key", "A", DiscriminatedModelA)

    print("...Reject match because the discriminator field is not a literal")
    assert not _is_discriminated_match("payload", "AAA", DiscriminatedModelA)


def test_discriminated_union():

    print("...Instantiate discriminated union")
    ma = ModelWithDiscriminatedUnion(nested_model=DiscriminatedModelA())
    mb = ModelWithDiscriminatedUnion(nested_model=DiscriminatedModelB())

    print("...Serialize discriminated union")
    ma_serialized = ma.model_dump()
    mb_serialized = mb.model_dump()

    print("...Deserialize discriminated union")
    ma_deserialized = ModelWithDiscriminatedUnion.model_validate(ma_serialized)
    mb_deserialized = ModelWithDiscriminatedUnion.model_validate(mb_serialized)

    assert isinstance(ma_deserialized.nested_model, DiscriminatedModelA)
    assert isinstance(mb_deserialized.nested_model, DiscriminatedModelB)


def test_auto_discrimination_from_base_model():
    print("...Instantiate nested union")
    ma = ModelWithNestedUnion(nested_model=NestedModelA())
    mb = ModelWithNestedUnion(nested_model=NestedModelB())

    print("...Serialize nested union")
    ma_serialized = ma.model_dump()
    mb_serialized = mb.model_dump()

    print("...Deserialize nested union")
    ma_deserialized = BaseModel.model_validate(ma_serialized)
    mb_deserialized = BaseModel.model_validate(mb_serialized)

    assert isinstance(ma_deserialized.nested_model, NestedModelA)
    assert isinstance(mb_deserialized.nested_model, NestedModelB)


def test_model_with_methods():
    print("...Instantiate model object")
    model = ModelWithMethod(a=2, b=5)

    print("...checking method")
    assert model.get_highest() == 5

    print("...checking property")
    assert model.highest == 5, f"model.highest is {model.highest}"


# ========== Test Execution ==========
def run_tests():
    print("==================== Beginning Test Suite ====================")
    tests_to_run = {
        name: obj for name, obj in globals().items() if name.startswith("test_")
    }

    total_test_time = 0
    for name, executable in tests_to_run.items():
        if not callable(executable):
            print(f"Symbol {name} is not callable. Skipping execution.")

        print(f"===== Running {name} =====")
        start = time.monotonic()
        executable()
        end = time.monotonic()

        total_test_time += end - start
        print(f"...test runtime was {(end-start)*1000:.3f} ms")

    print("==================== Test Suite Complete ====================")
    print(f"Total test time: {total_test_time:.3f} seconds")


if __name__ == "__main__":
    run_tests()
