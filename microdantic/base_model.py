class Field:
    """A descriptor that contains information about a field."""

    def __init__(self, data_type: type):
        self.data_type = data_type

    def make_property(self, default_value) -> property:
        assert isinstance(default_value, self.data_type)
        value = default_value
        return property(
            lambda x: value,
        )

    def __repr__(self):
        return f"{self.__class__.__name__}({self.data_type})"


class BaseModel:

    @classmethod
    def __new__(cls, *args, **kwargs):
        print(f"===== Running BaseModel.__new__({args}, {kwargs}) =====")

        obj = super().__new__(cls)
        # TODO: fill in attributes here

        return obj

    def __init__(self, *args, **kwargs):
        print(f"===== Running BaseModel.__init__({args}, {kwargs}) =====")

    @classmethod
    def raw_fields_dict_(cls):
        """Fields and their values as specified by the subclass."""
        return {
            k: v
            for k, v in cls.__dict__.items()
            if isinstance(v, Field) or isinstance(v, type)
        }

    @classmethod
    def fields_dict_(cls) -> dict[str, Field]:
        """Fully instantiated fields for the subclass."""
        actual_fields = dict()
        for name, field in cls.raw_fields_dict_().items():
            if isinstance(field, Field):
                actual_fields[name] = field
            elif isinstance(field, type):
                actual_fields[name] = Field(field)
            else:
                raise ValueError(
                    f"Unexpected field type {field}, should be Field or type"
                )

        return actual_fields
