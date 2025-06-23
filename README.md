# Microdantic

Microdantic is a pure python library with similar functionality to Pydantic, but
compatible with MicroPython / CircuitPython, and usable on embedded devices.

## Why Microdantic?

Pydantic is a wonderful library for data validation, serialization, and
deserialization. It is heavily used in the software industry for ensuring that
parties communicating over the internet can agree on and enforce data contracts.

Even though the library is extremely fast, it is too large to be included on
small devices (like Arduino), and makes use of some metaprogramming features not
available on MicroPython or CircuitPython. So it is not suitable as a tool for
enforcing data contracts over IoT networks such as BlueTooth or USB connections.

Enter Microdantic! Microdantic is intended to be a small, no-dependencies
library written in a style of Python compatible with MicroPython, CircuitPython,
and CPython. It replicates much of the core functionality and syntax of Pydantic
in a form that is deployable with Python projects running on small
microcontroller devices. And since Microdantic fits in a single file, it is 
easy to include as a dependency, even on CircuitPython projects that do not 
have a package manager.

Using Microdantic, developers can write data models to be shared between a fleet
of microcontrollers, a Python gateway app running on a RaspberryPi, and AWS
Lambda functions running in the cloud, confident that the contract will be
interpreted identically on all parts of the distributed application.

Microdantic is thoroughly tested, and all checks are run on both CPython running
on an x86 processor, as well as CircuitPython running on an Arduino.

## Getting Started

To include Microdantic as a dependency in a CPython project, you can add it
directly from the GitHub URL:

```shell
# Using pip
pip install git+https://github.com/username/repository.git

# Using Poetry
poetry add --git https://github.com/myusername/myrepository.git

# Using UV
uv add git+https://github.com/encode/httpx
```

To use Microdantic on a microcontroller, first make sure that you have set up
your device with [CircuitPython](circuitpython.org). Then copy the
`microdantic.py` file into the root of the device. If you want to save space,
then you can optionally compile `microdantic.py` to a
[.mpy](https://docs.micropython.org/en/latest/reference/mpyfiles.html)
that will load faster consume less memory.

## How this documentation is organized

A high level overview of the sections in this document is useful for quickly
finding the information that is relevant to your needs. The main sections of the
documentation (in order) are:

* **[Tutorials](#tutorials)** - A quick set of steps to accomplish a specific
  common task. Using a tutorial requires little or no prior knowledge of
  `microdantic` or `pydantic`.
* **[How-To Guides](#how-to-guides)** - These guides are recipes for using
  specific parts of
  `microdantic`'s functionality. They guide you through the trade-offs and
  decisions you will need to make, and also how to apply the various features to
  solve specific problems. They require some prior knowledge of
  `microdantic`, and will often compare and contrast how the same thing is
  commonly accomplished in `pydantic`.
* **[Topic Guides](#topic-guides)** - These sections discuss key concepts at a
  fairly high level, and provide useful information about `microdantic`'s
  implementation.
* **Reference Guide** - Complete documentation of all `microdantic`'s classes
  and functions can be found in the docstrings of those entities.
* **Developer Notes** - These are only relevant for contributors making changes
  to Microdantic, or developers reading the source code for detailed insight.
  Since many of the implementation details will seem confusing or even "wrong"
  to developers only used to CPython, some sections of code contain extensive
  comments with a discussion of why an unorthodox approach was chosen for that
  section of code.

# Tutorials

## 1. Define your data contract using a model

The magic of Microdantic all starts with the `BaseModel` class. Any class that
inherits from `BaseModel` will get all the magic functionality included
automatically. Such child classes are generically referred to as **models**.
Then you may declare a set of **fields** that belong to that model. For example,
let's say that we want a model to represent a point in 2-dimensional space, and
we want the default value for both components to be
"0.0". The following code shows how we might define that model and create
several instances of it:

```python
from microdantic import BaseModel


class Point2D(BaseModel):
    x = 0.0
    y = 0.0


# Any field not specified gets the default value
origin = Point2D()
unit_x = Point2D(x=1.0)
unit_y = Point2D(y=1.0)

# The order of parameters doesn't matter
point_a = Point2D(x=5.0, y=-2.0)
point_b = Point2D(y=-2.0, x=5.0)

# Models can be compared
point_a == point_b  # True
point_a == origin  # False

# The value of a field can be changed later on
point_b.y = 10.0
point_a == point_b  # False
```

As you can see, once you define your model by specifying the field names and
defaults, you can create instances by specifying the values you want in any
order to the constructor. Any values you don't specify will be assigned the
default value.

What to read next:

* [Tutorial 2: Constraining field values](#-2-constraining-field-values)

## 2. Constraining field values

Sometimes you may want to restrict the possible values that a field may take.
For example, say that we wanted to use the `Point2D` model from Tutorial 1, but
we wanted to ensure that the point is always in the first quadrant (i.e. the
values of both `x` and `y` are always positive).

Microdantic provides the class `Field` that we can use when defining our fields.
Among other things, the `Field` class allows us to enforce constraints on the
data. If anyone tries to assign a value to that field that violates our
constraint, then Microdantic will raise an error clearly listing what data
constraint the value failed to meet. The following code snippet illustrates
this:

```python
from microdantic import BaseModel, Field


class Point2D(BaseModel):
    x = Field(float, default=0.0, ge=0.0)
    y = Field(float, default=0.0, ge=0.0)


point_a = Point2D()

point_a.x = 3.0  # This will work

point_a.x = -3.0  # This will raise an error

# ValidationError: The following validations failed when attempting to assign 
# the value '-3.0' to field 'x':
# -- Value must be greater than 0.0
```

Since we know that the data contract is enforced at runtime while the data is
being constructed, we can write our code safe in the knowledge that if someone
else sends us a `Point2D` over the network, then that `Point2D` will be
well-behaved and follow the rules we expect it to.

What to read next:

* [Topic Guide: Field Validation](#field-validation)

## 3. Sending data

Microdantic provides a simple way to serialize your data into a format that can
be sent over the network. Most IoT communication channels require your data to
be sent in a binary encoding. The BaseModel class provides a method that writes
out your entire object (a.k.a. "serializes") in JSON format and encodes it in a
byte array. The following code snippet shows an example of sending a `Point2D`
object over a USB connection from an Arduino device using CircuitPython:

```Python
# CircuitPython running on an Arduino device
import usb_cdc
from microdantic import BaseModel, Field


class Point2D(BaseModel):
    x = Field(float, default=0.0, ge=0.0)
    y = Field(float, default=0.0, ge=0.0)


point_a = Point2D(x=3.0, y=4.0)

usb_cdc.data.write(point_a.model_dump_jsonb())
# Note that model_dump_jsonb() will ensure the byte array is terminated with a
# newline character so that the stream can be easily read on the other end
# using readline()

```

Whatever device the arduino is connected to will be able to read the data from
the serial port on the other side and reconstruct the original
`Point2D` object from that data:

```Python
# CPython running a host device
import serial
from microdantic import BaseModel, Field


class Point2D(BaseModel):
    x = Field(float, default=0.0, ge=0.0)
    y = Field(float, default=0.0, ge=0.0)


serial_name = '/dev/ttyUSB0'  # Change this to the name of your serial port
serial_instance = serial.Serial(serial_name, baudrate=115200)

for line in serial_instance.readlines():
    # Read the data from the serial port
    point_a = Point2D.model_validate_jsonb(line)
    print(point_a)

    # Note that in a real application you would need extra logic to check
    # for incomplete or malformed lines
```

# How-To Guides

## Schema Definition

Schemas are defined in Microdantic by deriving classes from the `BaseModel`
class and then defining fields in a similar way to Python's Data Classes, or
Pydantic's similarly named `BaseModel` class. Like Pydantic, model classes can
be nested if your data structure needs to be nested. When your model gets
serialized, all nested model classes will also be recursively serialized. For an
example of this, you may consult the code example in the
*Built-In Value Constraints* section of the
[Constrain Field Values](#constrain-field-values) how-to guide.

## Constrain Field Values

One of the three main goals of a [data contract](#data-contract) is specifying
what values a field is allowed to have. These are known as "data quality
constraints". Microdantic provides the `Field` class, which provides a number of
robust tools for specifying such constraints. These constraints are not just
polite requests (the way type hints in Python are). Every constraint for a field
is enforced whenever a new value is assigned to a field. If a default value is
supplied as part of the field definition, then the constraints are enforced on
the default value as part of
the [class registration](#model-class-registration). If any of the constraints
fails for a value, then Microdantic will raise a `ValidationError` wit ha list
of all the constraints that failed.

**Type, nullability, and default value**
The first constraint usually placed on a field is a constraint on the data type.
Microdantic is very strict on the type checking, and will raise an error, for
example, if you try to assign an integer to a field whose only allowable data
type is float. If a field may contain values of more than one data type,
Microdantic provides a built-in `Union` class that can be used to specify these
values (see the example below). Note, however, that this is
**not** the same as the `typing.Union` class provided as part of the
`typing` module of CPython. This is because the `typing` module is not provided
as part of MicroPython or CircuitPython.

The `Field` class also has a parameter `required` to indicate whether a field is
allowed to have a value of `None`. By default, all fields are required. If a
particular field is required, then it must either have a default value provided
as part of the definition, or else an explicit value must always be supplied to
the constructor every time an instance of the model is instantiated.

**Built-in value constraints**
There are many cases where it is not sufficient to specify only the data type
that a field's values should be constrained to. Often we must constrain values
to a specific range, or a specific set of pre-defined values. The
`Field` class provides fields for many of the most common constraints that are
placed on fields, such as "less than" and "greater than" for numeric values, "
max length" and "min length" for string and list values, and "one of" for
categorical values. You may consult the docstring of the `Field`
class for more information about these constraint parameters, as well as the
example below.

```python
from microdantic import BaseModel, Field


class Color(BaseModel):
    r = Field(int, ge=0, lt=256)
    g = Field(int, ge=0, lt=256)
    b = Field(int, ge=0, lt=256)


class VisualEffect(BaseModel):
    pattern = Field(str, one_of=["steady", "flash", "breathe"])
    primary_color = Field(Color)
    secondary_color = Field(Color, required=False)
    pattern_name = Field(str, min_length=3, max_length=255)

```

**Custom constraints**
If your particular data contract requires more specific logic than what is
supplied by the built-in constraint parameters, it is easy to hook into the
underlying validation logic of the `Field` class. All you need is a Python
function or lambda that takes an instance of a potential value for the field in
question, and returns `True` if that value passes the validation, and
`False` if it fails.

The `Validations` class contains many of the constraints that are used by the
built-in constraint parameters. It also contains a `Validator`
class that can be used with your custom validation logic and a custom error text
to make your validation logic function alongside all the built-in checks.

```python
from microdantic import BaseModel, Field
from microdantic import Validations

is_even = Validations.Validator(
    validator_function=lambda n: n % 2 == 0,
    error_text="Value must be even."
)


class Numbers(BaseModel):
    even_number = Field(int, validations=is_even)
    positive_even_number = Field(
        int,
        validations=[is_even, Validations.GreaterThanOrEqual(0)]
    )
```

# Topic Guides

## Data Contract

**What is a Data Contract**

Understanding the concept of a data contract is helpful for understanding the
best practices for use of the Microdantic library.

A **data contract** is a formal agreement between entities that generate data
(**producers**), and the ones which make use of that data
(**consumers**). While this could in general refer to more business side
concerns like change management processes, service level agreements and
governance metadata, Microdantic is focused only on the parts of a data contract
that are directly involved with producer applications and consumer applications.
This lets us focus our discussion on three specific areas of concern that
Microdantic aims to provide tools for:

1. Schema Definition (names, types, structure)
2. Data Quality Constraints (nullability, valid ranges, shape)
3. Intermediate Representation (JSON, packed binary, dict)

The tool that Microdantic provides for schema definition is the `BaseModel`
class, used as a parent class. Data quality constraints are handled by the
`Field` class, used as field descriptor. Lastly, the intermediate representation
is handled by the various `model_dump_*_()` and `model_validate_*_()`
methods, which are used to serialize and deserialize model classes. Each of
these three tools has its own How-To guide, discussing its specific use for
addressing its area of concern.

## Model Class Registration

This section contains advanced concepts that may be helpful for speed
optimization, but are not needed by most developers.

Most libraries in CPython that need to do some work at the time of a class
definition make use of CPython's rich metaprogramming features. However, Micro
Python does not have these features. Microdantic is able to get around these
language constraints by having model classes "register" themselves in a process
that performs a number of class set-up tasks. If you do not explicitly register
your model class, then the registration will happen automatically the first time
an instance of that model class is instantiated. This ensures that the
metaprogramming tasks needed to finish defining the class happen transparently.

The problem with this approach is that most applications running on embeded
devices using CircuitPython follow a structure where the application has a long
start-up period where all functions and classes are defined, and all resources
are initialized. Then the application enters a time sensitive event loop that
reads sensors and adjusts actuators on the device. Since model class
registration happens at the first instantiation of the class, this means that
the registration often happens not during the long start-up period where one
would expect, but rather during the first few event loops. The problem can be
greatly exacerbated if the application defined a large number of nested model
classes.

If you want to front-load the registration of your model classes to the start-up
portion of your application so that your loops are predictable and your
application remains responsive, Microdantic offers several options. First, there
is a `@register` decorator that can be used on model classes that will ensure
the registration happens immediately with the class definition. Secondly, all
child classes of `BaseModel` have a class method that performs registration when
invoked. Together these tools allow you to time when you would like the
computational overhead to fall.

```python
from microdantic import BaseModel, Field, register


@register
class ModelA(BaseModel):
    foo = Field(str)
    # ModelA is initialized when it is defined. No delay.


class ModelB(BaseModel):
    foo = Field(str)


class ModelC(BaseModel):
    foo = Field(str)


# ModelB is now initialized. Delayed, but still before first instantiation.
ModelB.register_class()

a = ModelA(foo="bar")
b = ModelB(foo="bar")
c = ModelC(foo="bar")  # ModelC is only now initialized implicitly.

```

## Auto-Discrimination from BaseModel

When receiving serialized objects over a newtork connection, it is possible that
the data could represent any one of several different models. Microdantic
provides an auto-discrimination feature, turned on by default. This feature adds
metadata at the base level of the serialized model. This metadata can be used by
Microdantic to automatically determine which model the serialized data should be
re-constituted into.

**Note:** This auto-discrimination is only available if the following conditions
are met:

1. the exact same model definition is used on both the sending and receiving end
   of the connection
2. the model has to be [registered](#model-class-registration)
   before it can be discriminated

Since the auto discrimination is on be default, using it is as trivial as
calling one of the `model_validate_*()` methods on the BaseModel class:

```python
from microdantic import BaseModel, Field, register


@register
class Point2D(BaseModel):
    x = Field(float, default=0.0, ge=0.0)
    y = Field(float, default=0.0, ge=0.0)


original_point = Point2D(x=1.0, y=-1.0)
serialized_point = original_point.model_dump_jsonb()

# Send the serialized model over the network...

reconstructed_point = BaseModel.model_validate_jsonb(serialized_point)
assert isinstance(reconstructed_point, Point2D)
assert reconstructed_point == original_point
```

If you wish to disable auto-discrimination for your model, you may define it
with the class variable `"__auto_serialize_class_name__"` set to `False`.

```python
from microdantic import BaseModel, Field, register


@register
class Point2D(BaseModel):
    """A Point2D model with auto-serialization metadata turned off."""
    __auto_serialize_class_name__ = False
    x = Field(float, default=0.0, ge=0.0)
    y = Field(float, default=0.0, ge=0.0)
```

# License

MIT License

Copyright (c) 2025 Christian P. Bonnell

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
