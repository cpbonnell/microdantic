__version__ = "v0.1.1"
import json


class _SpecialType:
    """
    A base class for special types in Microdantic.
    """

    def __init__(self, *args):
        pass

    # These two methods are required because as of right now I cannot successfully
    # override __instancecheck__ and __subclasscheck__ in a way that works in MicroPython.
    def instancecheck(self, instance) -> bool:
        """Determine if an object is part of this special type."""
        raise NotImplementedError()

    @staticmethod
    def from_square_brackets(param_tuple: tuple):
        """
        Construct an instance of the special type from a tuple of parameters.

        This is used for constructing instances of special types from the _SpecialTypeFacotory
        using square bracket syntax, such as `Union[int, float]`.
        """
        raise NotImplementedError()


class _SpecialTypeFactory:

    def __init__(self, special_type_class):
        assert issubclass(
            special_type_class, _SpecialType
        ), "Special type class must be a subclass of _SpecialType"

        self._special_type_class = special_type_class

    def __getitem__(self, params):
        to_pass = params if isinstance(params, tuple) else (params,)
        return self._special_type_class(*to_pass)


class _Union(_SpecialType):

    def __init__(self, *parameters):
        super().__init__(*parameters)

        for p in parameters:
            if not isinstance(p, type):
                raise ValueError(f"{p} is not a type, it is a {type(p)}.")

        self._allowed_types = parameters

    @property
    def allowed_types(self):
        """The allowed types that make up this union type."""
        return tuple(c for c in self._allowed_types)

    @staticmethod
    def from_square_brackets(param_tuple: tuple):
        return _Union(*param_tuple)

    def instancecheck(self, instance):
        return any(isinstance(instance, t) for t in self._allowed_types)

    def __repr__(self):
        return f"Union[{', '.join([t.__name__ for t in self._allowed_types])}]"


class _Literal(_SpecialType):
    def __init__(self, *parameters):
        super().__init__(*parameters)
        self._allowed_values = parameters

    @classmethod
    def from_square_brackets(cls, param_tuple: tuple):
        return cls(*param_tuple)

    def instancecheck(self, instance):
        return instance in self._allowed_values

    def __repr__(self):
        return f"Literal[{', '.join([repr(v) for v in self._allowed_values])}]"


Union = _SpecialTypeFactory(_Union)
Literal = _SpecialTypeFactory(_Literal)


class Validations:
    """A namespace to hold the various validation classes."""

    class BaseValidator:

        def validate(self, value):
            raise NotImplementedError

        @property
        def custom_error_message(self):
            return f"Value failed validation {self}"

        def __call__(self, value):
            return value is None or self.validate(value)

    class Validator(BaseValidator):
        def __init__(self, validator_function, error_text=None):
            self.validator_function = validator_function
            self.error_text = error_text

        @property
        def custom_error_message(self):
            if self.error_text:
                return self.error_text
            return f"Value must pass the user-supplied lambda function"

        def validate(self, value):
            return self.validator_function(value)

    class NotNull(BaseValidator):
        def __call__(self, value):
            """Overrides parent class method"""
            return value is not None

        @property
        def custom_error_message(self):
            return "Value must not be None"

    class IsType(Validator):
        def __init__(self, data_type: type | _SpecialType):
            if isinstance(data_type, _SpecialType):
                checker = lambda x: data_type.instancecheck(x)
            elif isinstance(data_type, type):
                checker = lambda x: isinstance(x, data_type)
            else:
                raise TypeError(f"Invalid type: {data_type}")

            super().__init__(checker, f"Value must be of type {data_type}")

    class GreaterThan(Validator):
        def __init__(self, minimum):
            super().__init__(
                lambda x: x > minimum, f"Value must be greater than {minimum}"
            )

    class GreaterThanOrEqual(Validator):
        def __init__(selfself, minimum):
            super().__init__(
                lambda x: x >= minimum,
                f"Value must be greater than or equal to {minimum}",
            )

    class LessThan(Validator):
        def __init__(self, maximum):
            super().__init__(
                lambda x: x < maximum, f"Value must be less than {maximum}"
            )

    class LessThanOrEqual(Validator):
        def __init__(self, maximum):
            super().__init__(
                lambda x: x <= maximum, f"Value must be less than or equal to {maximum}"
            )

    class MaxLen(Validator):
        def __init__(self, max_len):
            super().__init__(
                lambda x: len(x) <= max_len,
                f"Value must have length less than or equal to {max_len}",
            )

    class MinLen(Validator):
        def __init__(self, min_len):
            super().__init__(
                lambda x: len(x) >= min_len,
                f"Value must have length greater than or equal to {min_len}",
            )

    class OneOf(Validator):
        def __init__(self, valid_values):
            super().__init__(
                lambda x: x in set(valid_values),
                f"Value must be one of {valid_values}",
            )


class ValidationError(Exception):
    """
    A custom exception class that displays  clear messages when validation fails.

    If the error is raised, it will display a separate line item for each of the validations
    that failed, making it easier for a user to determine why a given value was rejected for a field.
    """

    def __init__(self, validation_messages: list[str], field_name: str, new_value):
        error_text = "The following validations failed"

        if field_name and new_value:
            error_text += f" when attempting to assign the value '{new_value}' to field '{field_name}':"
        else:
            error_text += ":"

        for validation_message in validation_messages:
            error_text += "\n-- " + validation_message

        self.message = error_text

    def __str__(self):
        return self.message


def _is_discriminated_match(
    discriminator_name: str, discriminator_value: str, candidate_type: type
) -> bool:
    """
    Determine if the candidate type matches the discriminator signature.

    :param discriminator_name: The name of the discriminator field.
    :param discriminator_value: The value of the discriminator field in the data being parsed.
    :param candidate_type: The candidate type being evaluated.
    """
    # Check to see if the candidate type has a field with the discriminator name
    if not (hasattr(candidate_type, discriminator_name)):
        return False

    # Check to see if the field with the discriminator name is a Field descriptor object
    discriminator_field_descriptor = getattr(candidate_type, discriminator_name)
    if not isinstance(discriminator_field_descriptor, Field):
        return False

    # Check to see if the field with the discriminator name is a Literal, and if the value
    # of the discriminator field matches the discriminator value
    if not isinstance(discriminator_field_descriptor.data_type, _Literal):
        return False

    if discriminator_field_descriptor.data_type.instancecheck(discriminator_value):
        return True

    return False


class Field:
    def __init__(
        self,
        data_type: type | _SpecialType,
        default=None,
        *,
        validations: None | list[callable] = None,
        required: bool = True,
        gt=None,
        ge=None,
        lt=None,
        le=None,
        min_length=None,
        max_length=None,
        one_of=None,
        discriminator: str = None,
    ):
        """
        A descriptor class for defining fields in a BaseModel.

        :param data_type: type. A runtime enforced type annotation.
        :param default: any. Default value for the field.
        :param validations: list of callables. A list of user-defined validation functions.
        :param required: bool. If True, the field is required and cannot be None.
        :param gt: any. Greater than constraint.
        :param ge: any. Greater than or equal to constraint.
        :param lt: any. Less than constraint.
        :param le: any. Less than or equal to constraint.
        :param min_length: int. Minimum length constraint.
        :param max_length: int. Maximum length constraint.
        :param one_of: list. A list of valid values for the field.
        :param discriminator: str. The name of the discriminator field for discriminated unions.
        """
        # Check the validations parameter and assign it
        if validations is None:
            validations = list()
        elif isinstance(validations, list):
            assert all(callable(v) for v in validations)
            validations = [
                (
                    v
                    if isinstance(v, Validations.BaseValidator)
                    else Validations.Validator(v)
                )
                for v in validations
            ]
        else:
            raise ValueError("Validations must be a list of callables or None")

        # Validators from the base parameters
        self._validations = list()
        self._validations.append(Validations.IsType(data_type))

        if required:
            self._validations.append(Validations.NotNull())

        if gt is not None:
            self._validations.append(Validations.GreaterThan(gt))

        if gt is not None:
            self._validations.append(Validations.GreaterThanOrEqual(ge))

        if lt is not None:
            self._validations.append(Validations.LessThan(lt))

        if le:
            self._validations.append(Validations.LessThanOrEqual(le))

        if min_length is not None:
            self._validations.append(Validations.MinLen(min_length))

        if max_length is not None:
            self._validations.append(Validations.MaxLen(max_length))

        if one_of is not None:
            self._validations.append(Validations.OneOf(one_of))

        # Add all other validators
        self._validations.extend(validations)

        # If the field is a discriminated union, do some setup for later convenience
        if isinstance(data_type, _Union) and discriminator:
            self._discriminator = discriminator
        else:
            self._discriminator = None

        # Note: We defer validation of the default value until class registration,
        # since we don't have access to the field name until that point.
        self.default = default

        # Store our other parameters
        self.data_type = data_type
        self.name = None
        self.private_name = None

    @property
    def discriminator(self):
        return self._discriminator

    def _assert_all_validations(self, value):
        validation_messages = list()
        for validation in self._validations:
            if not validation(value):
                if hasattr(validation, "custom_error_message"):
                    validation_messages.append(validation.custom_error_message)
                else:
                    validation_messages.append(
                        f"Value {value} failed validation {validation}"
                    )

        if len(validation_messages) > 0:
            raise ValidationError(validation_messages, self.name, value)

    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f"_{name}"

        # Check to see if we can make this a discriminated union with extra info from the owner class
        # (that is, if the field is a Union that is not already discriminated, and the owner class has a
        # __base_model_class_name__ attribute). This is a bit of a hack, but it's the best way I can think
        # of to do this without a metaclass
        if (
            isinstance(self.data_type, _Union)
            and not self.discriminator
            and hasattr(owner, "__base_model_class_name__")
            and getattr(owner, "__base_model_class_name__") is True
        ):
            self._discriminator = "__base_model_class_name__"

    def __get__(self, instance, owner):
        if instance is None:
            return self

        if not hasattr(instance, self.private_name) and self.default is not None:
            setattr(instance, self.private_name, self.default)

        return getattr(instance, self.private_name)

    def __set__(self, instance, value):
        self._assert_all_validations(value)
        setattr(instance, self.private_name, value)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.data_type})"

    def parse_dict(self, data: dict):
        """
        Parse a dictionary and return an element that is suitable for assignment to the field.

        :param data: A dict, typically from a nested JSON object.
        """

        # 1. If the dtype of this field is dict, then return the dict unchanged
        if self.data_type == dict:
            return data

        # 2. If the dtype of this field is a BaseModel, then hydrate and return that type
        if isinstance(self.data_type, type) and issubclass(self.data_type, BaseModel):
            return self.data_type.model_validate(data)

        # 3. If the dtype is a self-discriminated union, see if the dict has the class name serialized
        if (
            isinstance(self.data_type, _Union)
            and not self.discriminator
            and "__base_model_class_name__" in data
        ):
            # Iterate through the allowed types until we find one that matches the dict's signature
            class_name_signature = data["__base_model_class_name__"]

            for allowed_type in self.data_type.allowed_types:
                if (
                    isinstance(allowed_type, type)
                    and issubclass(allowed_type, BaseModel)
                    and allowed_type.__name__ == class_name_signature
                ):
                    return allowed_type.model_validate(data)

        # 4. If the dtype is a literal-discriminated union, look for a class that matches the
        #    discriminator to hydrate and return
        if (
            isinstance(self.data_type, _Union)
            and self.discriminator
            and self.discriminator in data
        ):
            discriminator_value_in_data = data[self.discriminator]
            for candidate_type in self.data_type.allowed_types:
                if (
                    isinstance(candidate_type, type)
                    and issubclass(candidate_type, BaseModel)
                    and _is_discriminated_match(
                        self.discriminator, discriminator_value_in_data, candidate_type
                    )
                ):
                    return candidate_type.model_validate(data)

        # If no possible parse options can be found, raise and let the user sort it out
        raise ValueError(f"Cannot parse dict for field of type {self.data_type}")

        return None


class BaseModel:

    __registered_child_classes__ = dict()
    __auto_serialize_class_name__ = True

    @classmethod
    def register_class(cls):
        """
        Conduct various class setup tasks for the class.

        The method will automatically be invoked the first time an instance
        of the class is created, but it can also be called explicitly if
        you want to ensure that the class is set up before any instances
        are created (for example if the first instance is created in a
        time sensitive event loop).

        This is necessary because MicroPython does not support metaclasses,
        and so any custom class definition behavior needs to be in a function
        that is invoked explicitly. MicroPython also does not (yet) do all the
        normal magic around class definition, so we have to do some of the work
        ourselves.

        This method is idempotent, so it can be called multiple times without
        causing any issues.
        """

        # Look over the class dictionary and create Field objects for any
        # attributes that are not already Fields.
        # NOTE: Some iterations of MicroPython (like Circuit Python) do not
        # have the __annotations__ attribute, so we have to use __dict__
        # instead. This means that we have to infer the data type from the
        # value supplied as a default, rather than from the field's annotated
        # type. This has the side effect of not being able to use the
        # "shorthand syntax" to define fields without a default value (even
        # though such declarations are common in Pydantic). And since we have
        # don't have access to the type annotations, it means that the user
        # could define a field with a default value that is not of the same
        # type as the annotation, and we will still infer that the filed is the
        # same type as the default value, rather than the type of the
        # annotation.
        new_fields = dict()
        for name, field in cls.__dict__.items():
            if not name.startswith("_") and not isinstance(field, Field):
                new_fields[name] = Field(data_type=type(field), default=field)

        for name, field_obj in new_fields.items():
            setattr(cls, name, field_obj)

        # Call the __set_name__ method for each field descriptor, since
        # MicroPython does not do this automatically. This is theoretically
        # on the roadmap for MP, and can be removed once they finally merge
        # the PR that adds this feature.
        all_field_names = list()
        for name, field in cls.__dict__.items():
            if isinstance(field, Field):
                field.__set_name__(cls, name)

                # Note: We do, in fact, want to assert all validations against
                # the default value if one is supplied. But if no default
                # value is supplied, then we don't want to enforce the NotNull
                # constraint until the owner class is instantiated, since this
                # might just be a required field that is not set by default.
                if field.default is not None:
                    # noinspection PyProtectedMember
                    field._assert_all_validations(
                        field.default
                    )  # pylint: disable=protected-access

                all_field_names.append(name)

        # Reliably automating the struct packing process requires a
        # consistent ordering of the fields, so we determine a fixed
        # order here and store it in the class.
        cls.__field_names__ = tuple(sorted(all_field_names))

        # Register the child class with BaseModel
        BaseModel.__registered_child_classes__[cls.__name__] = cls

    @classmethod
    def get_field_descriptor(cls, field_name):
        return cls.__dict__[field_name]

    @classmethod
    def iter_fields(cls):
        for field_name in cls.__field_names__:
            yield field_name, cls.get_field_descriptor(field_name)

    def __init__(self, **kwargs):
        # Check if this class has been registered yet, and if not
        # register it now.
        try:
            self.__field_names__
        except AttributeError:
            self.register_class()

        for field_name in self.__field_names__:
            if field_name in kwargs:
                value = kwargs[field_name]
            else:
                value = self.get_field_descriptor(field_name).default

            setattr(self, field_name, value)

    def __repr__(self):
        field_values = ", ".join(
            f"{field_name}={repr(getattr(self, field_name))}"
            for field_name in self.__field_names__
        )
        return f"{self.__class__.__name__}({field_values})"

    def model_dump(self) -> dict:
        """
        Serialize the model to a dictionary.
        """
        output = dict()
        for field_name, descriptor in self.iter_fields():

            if isinstance(descriptor, Field):
                value = getattr(self, field_name)

                # If the value is itself something that can be dumped, then
                # recursively call its model_dump method to get the serialized value.
                if isinstance(value, BaseModel):
                    output[field_name] = value.model_dump()
                else:
                    output[field_name] = value

        if self.__auto_serialize_class_name__:
            output["__base_model_class_name__"] = self.__class__.__name__

        return output

    @classmethod
    def model_validate(cls, data: dict):
        """
        Validate a dictionary of data against the model's fields and return an instance.

        :param data: A dictionary of data to validate.
        :return: An instance of the model class.
        """

        # If we get nested BaseModel objects, we need to recursively validate them
        # before constructing the instance.
        for field_name, descriptor in cls.iter_fields():
            relevant_data = data.get(field_name)

            if isinstance(relevant_data, list):
                raise ValueError("Nested list fields are not yet supported.")

            elif isinstance(relevant_data, dict):
                # If the field is a nested dict, we delegate parsing to the field descriptor
                # which will determine how to recursively call model_validate based on the
                # correct class
                data[field_name] = descriptor.parse_dict(relevant_data)

            else:
                # If the field is a simple type, we just naively pass it along to
                # the constructor
                pass

        instance = cls(**data)
        return instance

    def model_dump_json(self) -> str:
        """
        Serialize the model to a JSON string.
        """
        return json.dumps(self.model_dump())

    @classmethod
    def model_validate_json(cls, json_string: str):
        """
        Validate a JSON string against the model's fields and return an instance.

        :param json_string: A JSON string of data to validate.
        :return: An instance of the model class.
        """
        return cls.model_validate(json.loads(json_string))

    def model_dump_jsonb(self) -> bytes:
        """
        Serialize the model to a JSON bytes object.
        """
        return self.model_dump_json().encode("utf-8") + b"\n"

    @classmethod
    def model_validate_jsonb(cls, json_bytes: bytes):
        """
        Validate a JSON bytes object against the model's fields and return an instance.

        :param json_bytes: A JSON bytes object of data to validate.
        :return: An instance of the model class.
        """
        return cls.model_validate_json(json_bytes.decode("utf-8"))


def register(class_obj):
    """A decorator to call the register_class method of a class inheriting BaseModel"""
    if not issubclass(class_obj, BaseModel):
        raise TypeError(
            "The register decorator can only be used on classes that inherit from BaseModel"
        )

    class_obj.register_class()
    return class_obj
