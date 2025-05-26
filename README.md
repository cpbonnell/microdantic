from tokenize import endpats

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

Enter Microdantic! Microdantic is intended to be a relatively small library
written in a style of Python compatible with MicroPython, CircuitPython, and
CPython. It replicates much of the core functionality and syntax of Pydantic in
a form that is deployable with Python projects running on small microcontroller
devices.

Using Microdantic, developers can write data models to be shared between a fleet
of microcontrollers, a Python gateway app running on a RaspberryPi, and AWS
Lambda functions running in the cloud, confident that the contract will be
interpreted identically on all parts of the distributed application.

Microdantic is thoroughly tested, and all checks are run on both a CPython
running on an x86 processor, as well as CircuitPython running on an Arduino.

## How this documentation is organized

A high level overview of the sections in this document is useful for quickly
finding the information that is relevant to your needs. The main sections of the
documentation (in order) are:

* **[Tutorials](#tutorials)** - A quick set of steps to accomplish a specific
  common task. Using a tutorial requires little or no prior knowledge of
  `microdantic` or `pydantic`.
* **How-To Guides** - These guides are recipes for using specific parts of
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

## Constrain Field Values
One of the three main goals of a [data contract](#data-contract) is 
specifying what values a field is allowed to have. These are known as "data 
quality constraints". Microdantic provides the `Field` class, which provides 
a number of robust tools for specifying such constraints. These constraints 
are not just polite requests (the way type hints in Python are). Every 
constraint for a field is enforced whenever a new value is assigned to a 
field. If a default value is supplied as part of the field definition, then 
the constraints are enforced on the default value as part of the [class 
registration](#model-class-registration). If any of the constraints fails 
for a value, then Microdantic will raise a `ValidationError` wit ha list of 
all the constraints that failed.

**Type, nullability, and default value**
The first constraint usually placed on a field is a constraint on the data 
type. Microdantic is very strict on the type checking, and will raise an 
error, for example, if you try to assign an integer to a field whose only 
allowable data type is float. If a field may contain values of more than one 
data type, Microdantic provides a built-in `Union` class that can be used to 
specify these values (see the example below). Note, however, that this is 
**not** the same as the `typing.Union` class provided as part of the 
`typing` module of CPython. This is because the `typing` module is not 
provided as part of MicroPython or CircuitPython.

The `Field` class also has a parameter `required` to indicate whether a 
field is allowed to have a value of `None`. By default, all fields are 
required. If a particular field is required, then it must either have a 
default value provided as part of the definition, or else an explicit value 
must always be supplied to the constructor every time an instance of the 
model is instantiated.


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

**Contract as Code**

It completely is possible to write your data contract in a natural language in a
text document, and then have all interested parties write their own logic for
implementing it. Many companies do this, and manage to get by. But this
introduces an unnecessary component of uncertainty (the natural language), and
lots of unnecessary work (implementing contract compliant code for each
application).

However, if a set of tools exists that can be shared across all participating
applications, then the contract can be defined directly in code. This ensures
that the contract is always interpreted in exactly the same way by all actors.
Microdantic was designed with this use case in mind.

Microdantic is writen in pure python, with no dependencies. This means that it
can be included in any number of different applications with no risk of
dependency mismatch. The Python language features used are compatible with all
major flavors of Python (CPython, MicroPython, CircuitPython). Unlike Pydantic,
it also contains no compiled binary code elements. This means that it remains
usable on platforms with non-standard processor architecture, such as embeded
platforms and microcontrollers like Arduino.

This means that data contracts written using Microdantic can be shared across
complex and rich distributed applications. For example, a contract entity could
be generated on an Arduino device running CircuitPython on an Atmel processor,
and sent as a packed binary over a Bluetooth connection to a RaspberryPi gateway
running CPython on an ARM processor. Since it is the same contract, the
RaspberryPi reconstructs the Bluetooth data into an identical Python object,
collates it, and sends it as JSON to a server in the cloud. The FastAPI server
application uses the same contract running CPython on an Intel x86 processor
architecture, so it too reconstructs the identical Python object. From there 
the object could be sent to PyScript web application running in MicroPython 
for display in a dashboard to an end user.

## Model Class Registration
TODO

