class Field:

    def __init__(
        self,
        data_type: type,
        default=None,
        validations: None | list[callable] = None,
        required: bool = False,
    ):
        # validations is a list of callables that take a single argument and return a boolean
        self._validations = validations if validations is not None else list()

        real_data_type = data_type if required else data_type | None
        self._validations.append(lambda x: isinstance(x, real_data_type))

        # If we have a default, ensure it is valid and store it
        self._assert_all_validations(default)
        self.default = default

        # Store our other parameters
        self.data_type = data_type
        self.private_name = None

    def _assert_all_validations(self, value):
        for validation in self._validations:
            if not validation(value):
                raise ValueError(f"Value {value} failed validation {validation}")

    def __set_name__(self, owner, name):
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


class BaseModelMeta(type):
    def __new__(mcls, name, bases, namespace):
        print(
            f"""
            Running BaseModelMeta.__new__()
            mcsl: {mcls}
            name: {name}
            bases: {bases}
            namespace: {namespace}
            """.strip()
        )
        # Gather any type hints the user wrote (e.g. `x: int`, `y: str`)
        annotations = namespace.get("__annotations__", {})

        for attr_name, attr_type in annotations.items():
            # If the user hasn't already provided a custom descriptor
            # for in the class body, insert a Field descriptor with the
            # user specified type as the dtype, and the user specified
            # value as the default value for the field.
            user_supplied_value = namespace.get(attr_name, None)
            if not isinstance(user_supplied_value, Field):
                namespace[attr_name] = Field(
                    data_type=attr_type, default=user_supplied_value
                )

        # Create the new class object
        cls = super().__new__(mcls, name, bases, namespace)
        return cls


class BaseModel(metaclass=BaseModelMeta):
    """
    Any class inheriting from BaseModel will have all type-annotated
    fields automatically converted into Field descriptors.
    """

    def __init__(self, **kwargs):
        for field_name, value in kwargs.items():
            setattr(self, field_name, value)

    def model_dump(self) -> dict:
        """
        Serialize the model to a dictionary.

        If a field value is another BaseModel, recursively call model_dump() on it.
        """
        output = {}
        # You can either iterate over __annotations__ or check class dict for Field objects
        for field_name, descriptor in self.__class__.__dict__.items():
            if isinstance(descriptor, Field):
                value = getattr(self, field_name)
                # Check for nested BaseModel objects
                if isinstance(value, BaseModel):
                    output[field_name] = value.model_dump()
                else:
                    output[field_name] = value
        return output
