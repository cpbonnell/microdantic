__version__ = "0.1.0-rc2"


def xxhash32(data, seed=0):
    """
    Optimized xxHash implementation for MicroPython.

    See reference implementation on GitHub:
    https://github.com/Cyan4973/xxHash
    """

    PRIME1 = 2654435761
    PRIME2 = 2246822519
    PRIME3 = 3266489917
    PRIME4 = 668265263
    PRIME5 = 374761393

    def rotl32(x, r):
        """Rotate left (circular shift) for 32-bit values."""
        return ((x << r) & 0xFFFFFFFF) | (x >> (32 - r))

    length = len(data)
    h32 = (seed + PRIME5 + length) & 0xFFFFFFFF  # Base hash initialization

    # Process 4-byte chunks
    i = 0
    while i + 4 <= length:
        k1 = (
            data[i] | (data[i + 1] << 8) | (data[i + 2] << 16) | (data[i + 3] << 24)
        ) & 0xFFFFFFFF
        k1 = (k1 * PRIME3) & 0xFFFFFFFF
        k1 = rotl32(k1, 17)
        k1 = (k1 * PRIME4) & 0xFFFFFFFF
        h32 ^= k1
        h32 = rotl32(h32, 19)
        h32 = (h32 * PRIME1 + PRIME4) & 0xFFFFFFFF
        i += 4

    # Process remaining 1-3 bytes
    if i < length:
        if length - i == 3:
            h32 ^= data[i + 2] << 16
        if length - i >= 2:
            h32 ^= data[i + 1] << 8
        if length - i >= 1:
            h32 ^= data[i]
            h32 = (h32 * PRIME5) & 0xFFFFFFFF
            h32 = rotl32(h32, 11)
            h32 = (h32 * PRIME1) & 0xFFFFFFFF

    # Final mix
    h32 ^= h32 >> 15
    h32 = (h32 * PRIME2) & 0xFFFFFFFF
    h32 ^= h32 >> 13
    h32 = (h32 * PRIME3) & 0xFFFFFFFF
    h32 ^= h32 >> 16

    return h32


class Validations:
    class BaseValidator:

        def validate(self, value):
            raise NotImplementedError

        @property
        def custom_error_message(self):
            return f"Value failed validation {self}"

        def __call__(self, value):
            return value is None or self.validate(value)

    class NotNull(BaseValidator):
        def __call__(self, value):
            """Overrides parent class method"""
            return value is not None

        @property
        def custom_error_message(self):
            return "Value must not be None"

    class IsType(BaseValidator):
        def __init__(self, data_type):
            self.data_type = data_type

        @property
        def custom_error_message(self):
            return f"Value must be of type {self.data_type}"

        def validate(self, value):
            return isinstance(value, self.data_type)

    class GreaterThan(BaseValidator):
        def __init__(self, minimum):
            self.minimum = minimum

        @property
        def custom_error_message(self):
            return f"Value must be greater than {self.minimum}"

        def validate(self, value):
            return value > self.minimum

    class LessThan(BaseValidator):
        def __init__(self, maximum):
            self.maximum = maximum

        @property
        def custom_error_message(self):
            return f"Value must be less than {self.maximum}"

        def validate(self, value):
            return value < self.maximum

    class UserSuppliedLambda(BaseValidator):
        def __init__(self, lambda_function, error_text=None):
            self.lambda_function = lambda_function
            self.error_text = error_text

        @property
        def custom_error_message(self):
            if self.error_text:
                return self.error_text
            return f"Value must pass the user-supplied lambda function"

        def validate(self, value):
            return self.lambda_function(value)


class Field:
    def __init__(
        self,
        data_type: type,
        default=None,
        validations: None | list[callable] = None,
        required: bool = False,
    ):
        # Check the validations parameter and assign it
        if validations is None:
            validations = list()
        elif isinstance(validations, list):
            assert all(callable(v) for v in validations)
            validations = [
                Validations.UserSuppliedLambda(v)
                for v in validations
                if not isinstance(v, Validations.BaseValidator)
            ]
        else:
            raise ValueError("Validations must be a list of callables or None")

        # Validators from the base parameters
        self._validations = list()
        self._validations.append(Validations.IsType(data_type))
        if required:
            self._validations.append(Validations.NotNull())

        # Add all other validators
        self._validations.extend(validations)

        # Check the default parameter and assign it
        self.default = default

        # Store our other parameters
        self.data_type = data_type
        self.private_name = None

    def _assert_all_validations(self, value):
        error_messages = list()
        for validation in self._validations:
            if not validation(value):
                if hasattr(validation, "custom_error_message"):
                    error_messages.append(validation.custom_error_message)
                else:
                    error_messages.append(
                        f"Value {value} failed validation {validation}"
                    )

        if len(error_messages) > 0:
            raise ValueError(
                "Failed the following validations: \n-- " + "\n-- ".join(error_messages)
            )

    def __set_name__(self, owner, name):
        self.private_name = f"_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self

        if not hasattr(instance, self.private_name) and self.default is not None:
            setattr(instance, self.private_name, self.default)

        return getattr(instance, self.private_name)

    def __set__(self, instance, value):
        setattr(instance, self.private_name, value)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.data_type})"


class BaseModel:

    @classmethod
    def register_class(cls):
        """
        Call this method immediately after defining a new child class.

        This is necessary because MicroPython does not support metaclasses, and
        so any custom behavior needs to be in a function that is invoked
        explicitly. MicroPython also does not (yet) do all of the normal magic
        around class definition, so we have to do some of the work ourselves.
        """

        # Look over the class dictionary and create Field objects for any
        # attributes that are not already Fields.
        # NOTE: Some iterations of MicroPython (like Circuit Python) do not
        # have the __annotations__ attribute, so we have to use __dict__
        # instead, and infer the type from the value supplied as a default.
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

    def __init__(self, **kwargs):
        for field_name, value in kwargs.items():
            setattr(self, field_name, value)
