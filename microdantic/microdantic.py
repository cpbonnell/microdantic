__version__ = "0.1.0-rc7"
import json


class Validations:
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
        def __init__(self, data_type):
            super().__init__(
                lambda x: isinstance(x, data_type), f"Value must be of type {data_type}"
            )

    class GreaterThan(Validator):
        def __init__(self, minimum):
            super().__init__(
                lambda x: x > minimum, f"Value must be greater than {minimum}"
            )

    class LessThan(Validator):
        def __init__(self, maximum):
            super().__init__(
                lambda x: x < maximum, f"Value must be less than {maximum}"
            )

    class MaxLen(Validator):
        def __init__(self, max_len):
            super().__init__(
                lambda x: len(x) <= max_len,
                f"Value must have length less than {max_len}",
            )

    class OneOf(Validator):
        def __init__(self, valid_values):
            super().__init__(
                lambda x: x in set(valid_values),
                f"Value must be one of {valid_values}",
            )


class ValidationError(Exception):
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


# TODO: Add a custom Union class that can be used in the Field class to
#       specify multiple valid types for a field. MicroPython does not
#       support the typing module, so we have to implement this ourselves.

# TODO: Use the Union class to implement the "discriminated union" feature
#       from Pydantic. This will allow us to have a field that can be one of
#       several different types, and the type is determined by the value of
#       another field in the model. This will also require implementation of
#       Literal and Enum classes to support the feature.


class Field:
    def __init__(
        self,
        data_type: type,
        default=None,
        validations: None | list[callable] = None,
        required: bool = True,
        min_value=None,
        max_value=None,
        max_len=None,
        one_of=None,
    ):
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

        if min_value is not None:
            self._validations.append(Validations.GreaterThan(min_value))

        if max_value is not None:
            self._validations.append(Validations.LessThan(max_value))

        if max_len is not None:
            self._validations.append(Validations.MaxLen(max_len))

        if one_of is not None:
            self._validations.append(Validations.OneOf(one_of))

        # Add all other validators
        self._validations.extend(validations)

        # Note: We do, in fact, want to assert all validations against
        # the default value if one is supplied. But if no default
        # value is supplied, then we don't want to enforce the NotNull
        # constraint until the owner class is instantiated.
        if default is not None:
            self._assert_all_validations(default)
        self.default = default

        # Store our other parameters
        self.data_type = data_type
        self.name = None
        self.private_name = None

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


class BaseModel:

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
        causing any issues (unless you are doing fancy metaprogramming of your
        own that is messing with Microdantic's internals).
        """

        # Look over the class dictionary and create Field objects for any
        # attributes that are not already Fields.
        # NOTE: Some iterations of MicroPython (like Circuit Python) do not
        # have the __annotations__ attribute, so we have to use __dict__
        # instead. This means that we have to infer the data type from the
        # value supplied as a default, rather than from the fields annotated
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
                all_field_names.append(name)

        # Reliably automating the struct packing process requires a
        # consistent ordering of the fields, so we determine a fixed
        # order here and store it in the class.
        # TODO: In the future we might construct a struct format string
        #       here, but for now we just store the order of the fields.
        cls.__field_names__ = tuple(sorted(all_field_names))

    @classmethod
    def get_field_descriptor(cls, field_name):
        return cls.__dict__[field_name]

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
        for field_name in self.__field_names__:
            descriptor = self.get_field_descriptor(field_name)

            if isinstance(descriptor, Field):
                value = getattr(self, field_name)

                # If the value is itself something that can be dumped, then
                # recursively call its model_dump method to get the serialized value.
                if isinstance(value, BaseModel):
                    output[field_name] = value.model_dump()
                else:
                    output[field_name] = value

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
        for field_name in cls.__field_names__:
            descriptor = cls.get_field_descriptor(field_name)
            if field_name in data and issubclass(descriptor.data_type, BaseModel):
                data[field_name] = descriptor.data_type.model_validate(data[field_name])

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
