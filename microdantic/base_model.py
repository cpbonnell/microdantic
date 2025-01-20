class Field:

    def __init__(self, data_type: type, validations: None | list[callable] = None):
        self._validations = validations if validations is not None else list()
        self._validations.append(lambda x: isinstance(x, data_type))
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
        else:
            return getattr(instance, self.private_name)

    def __set__(self, instance, value):
        self._assert_all_validations(value)
        setattr(instance, self.private_name, value)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.data_type})"


class BaseModel:

    @classmethod
    def __new__(cls, *args, **kwargs):
        print(f"===== Running BaseModel.__new__({args}, {kwargs}) =====")

        obj = super().__new__(cls)
        for name, field in cls.fields_dict_().items():
            setattr(obj, name, field.make_property(kwargs.get(name)))

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
